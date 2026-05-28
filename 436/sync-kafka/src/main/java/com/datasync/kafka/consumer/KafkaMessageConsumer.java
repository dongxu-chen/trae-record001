package com.datasync.kafka.consumer;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.util.JsonUtils;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.ByteArrayDeserializer;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;
import java.util.regex.Pattern;

@Slf4j
public class KafkaMessageConsumer {
    private final KafkaConsumer<String, byte[]> consumer;
    private final String datacenterId;
    private final List<String> sourceDatacenterIds;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private ExecutorService executorService;
    private Consumer<List<DataChangeEvent>> eventListener;
    private final long pollTimeoutMs;

    @Builder
    public KafkaMessageConsumer(String bootstrapServers,
                                String groupId,
                                String datacenterId,
                                List<String> sourceDatacenterIds,
                                List<String> topics,
                                String topicPattern,
                                Long pollTimeoutMs,
                                Integer maxPollRecords,
                                Boolean enableAutoCommit,
                                Integer autoCommitIntervalMs,
                                String autoOffsetReset) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName());
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, maxPollRecords != null ? maxPollRecords : 500);
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, enableAutoCommit != null ? enableAutoCommit : false);
        props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, autoCommitIntervalMs != null ? autoCommitIntervalMs : 5000);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, autoOffsetReset != null ? autoOffsetReset : "earliest");
        props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, 30000);
        props.put(ConsumerConfig.HEARTBEAT_INTERVAL_MS_CONFIG, 10000);

        this.consumer = new KafkaConsumer<>(props);
        this.datacenterId = datacenterId;
        this.sourceDatacenterIds = sourceDatacenterIds;
        this.pollTimeoutMs = pollTimeoutMs != null ? pollTimeoutMs : SyncConstants.DEFAULT_POLL_TIMEOUT_MS;

        if (topics != null && !topics.isEmpty()) {
            consumer.subscribe(topics);
        } else if (topicPattern != null) {
            consumer.subscribe(Pattern.compile(topicPattern));
        } else {
            String defaultPattern = buildDefaultTopicPattern();
            consumer.subscribe(Pattern.compile(defaultPattern));
        }
    }

    private String buildDefaultTopicPattern() {
        StringBuilder patternBuilder = new StringBuilder();
        patternBuilder.append(SyncConstants.KAFKA_TOPIC_PREFIX);
        patternBuilder.append("(");
        for (int i = 0; i < sourceDatacenterIds.size(); i++) {
            if (i > 0) {
                patternBuilder.append("|");
            }
            patternBuilder.append(sourceDatacenterIds.get(i));
        }
        patternBuilder.append(")_.*");
        return patternBuilder.toString();
    }

    public void start() {
        if (running.compareAndSet(false, true)) {
            log.info("Starting Kafka message consumer for datacenter: {}", datacenterId);
            executorService = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "kafka-consumer-" + datacenterId);
                t.setDaemon(true);
                return t;
            });
            executorService.submit(this::pollLoop);
            log.info("Kafka message consumer started for datacenter: {}", datacenterId);
        }
    }

    public void stop() {
        if (running.compareAndSet(true, false)) {
            log.info("Stopping Kafka message consumer for datacenter: {}", datacenterId);
            if (executorService != null) {
                executorService.shutdownNow();
            }
            if (consumer != null) {
                consumer.close();
            }
            log.info("Kafka message consumer stopped for datacenter: {}", datacenterId);
        }
    }

    public boolean isRunning() {
        return running.get();
    }

    public void registerListener(Consumer<List<DataChangeEvent>> listener) {
        this.eventListener = listener;
    }

    private void pollLoop() {
        while (running.get()) {
            try {
                ConsumerRecords<String, byte[]> records = consumer.poll(Duration.ofMillis(pollTimeoutMs));

                if (records.isEmpty()) {
                    continue;
                }

                List<DataChangeEvent> events = new ArrayList<>();
                for (ConsumerRecord<String, byte[]> record : records) {
                    try {
                        DataChangeEvent event = parseRecord(record);
                        if (event != null) {
                            events.add(event);
                        }
                    } catch (Exception e) {
                        log.error("Error parsing Kafka record: topic={}, partition={}, offset={}",
                                record.topic(), record.partition(), record.offset(), e);
                    }
                }

                if (!events.isEmpty() && eventListener != null) {
                    eventListener.accept(events);
                }

                consumer.commitSync();
            } catch (Exception e) {
                if (running.get()) {
                    log.error("Error in Kafka poll loop for datacenter: {}", datacenterId, e);
                    try {
                        Thread.sleep(1000);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
    }

    private DataChangeEvent parseRecord(ConsumerRecord<String, byte[]> record) {
        if (record.value() == null) {
            return null;
        }

        DataChangeEvent event = JsonUtils.fromJsonBytes(record.value(), DataChangeEvent.class);

        if (event == null) {
            return null;
        }

        if (datacenterId.equals(event.getSourceDatacenterId())) {
            return null;
        }

        if (sourceDatacenterIds != null && !sourceDatacenterIds.isEmpty()) {
            if (!sourceDatacenterIds.contains(event.getSourceDatacenterId())) {
                return null;
            }
        }

        return event;
    }
}
