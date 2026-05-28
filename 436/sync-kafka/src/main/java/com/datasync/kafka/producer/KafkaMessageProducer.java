package com.datasync.kafka.producer;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.util.JsonUtils;
import com.datasync.kafka.channel.TableChannelManager;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.serialization.ByteArraySerializer;
import org.apache.kafka.common.serialization.StringSerializer;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.Future;

@Slf4j
public class KafkaMessageProducer {
    private final KafkaProducer<String, byte[]> producer;
    private final String topicPrefix;
    private final String datacenterId;
    private final TableChannelManager channelManager;
    private final boolean useChannelRouting;

    @Builder
    public KafkaMessageProducer(String bootstrapServers,
                                String topicPrefix,
                                String datacenterId,
                                String acks,
                                Integer retries,
                                Integer batchSize,
                                Long lingerMs,
                                Long bufferMemory,
                                TableChannelManager channelManager) {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, acks != null ? acks : "all");
        props.put(ProducerConfig.RETRIES_CONFIG, retries != null ? retries : 3);
        props.put(ProducerConfig.BATCH_SIZE_CONFIG, batchSize != null ? batchSize : 16384);
        props.put(ProducerConfig.LINGER_MS_CONFIG, lingerMs != null ? lingerMs : 1);
        props.put(ProducerConfig.BUFFER_MEMORY_CONFIG, bufferMemory != null ? bufferMemory : 33554432L);
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");

        this.producer = new KafkaProducer<>(props);
        this.topicPrefix = topicPrefix != null ? topicPrefix : SyncConstants.KAFKA_TOPIC_PREFIX;
        this.datacenterId = datacenterId;
        this.channelManager = channelManager;
        this.useChannelRouting = channelManager != null;
    }

    public Future<RecordMetadata> send(DataChangeEvent event) {
        String topic = resolveTopic(event);
        byte[] value = JsonUtils.toJsonBytes(event);
        String key = buildMessageKey(event);

        ProducerRecord<String, byte[]> record = new ProducerRecord<>(topic, key, value);

        log.debug("Sending event to Kafka: topic={}, key={}, eventId={}", topic, key, event.getEventId());
        return producer.send(record, (metadata, exception) -> {
            if (exception != null) {
                log.error("Failed to send event to Kafka: eventId={}", event.getEventId(), exception);
            } else {
                log.debug("Event sent successfully: eventId={}, partition={}, offset={}",
                        event.getEventId(), metadata.partition(), metadata.offset());
            }
        });
    }

    public void sendBatch(List<DataChangeEvent> events) {
        Map<String, List<DataChangeEvent>> topicBatches = new HashMap<>();
        for (DataChangeEvent event : events) {
            String topic = resolveTopic(event);
            topicBatches.computeIfAbsent(topic, k -> new ArrayList<>()).add(event);
        }

        for (Map.Entry<String, List<DataChangeEvent>> entry : topicBatches.entrySet()) {
            String topic = entry.getKey();
            for (DataChangeEvent event : entry.getValue()) {
                byte[] value = JsonUtils.toJsonBytes(event);
                String key = buildMessageKey(event);
                ProducerRecord<String, byte[]> record = new ProducerRecord<>(topic, key, value);
                producer.send(record, (metadata, exception) -> {
                    if (exception != null) {
                        log.error("Failed to send event to Kafka: topic={}, eventId={}", topic, event.getEventId(), exception);
                    }
                });
            }
        }
        producer.flush();
    }

    private String resolveTopic(DataChangeEvent event) {
        if (useChannelRouting) {
            return channelManager.getTopicForEvent(event);
        }
        return buildTopic(event.getFullTableName());
    }

    private String buildTopic(String tableName) {
        return topicPrefix + datacenterId + "_" + tableName.replace(".", "_");
    }

    private String buildMessageKey(DataChangeEvent event) {
        if (event.getBusinessKey() != null && !event.getBusinessKey().isEmpty()) {
            return event.getSourceDatacenterId() + "_" + event.getBusinessKey();
        }
        if (event.getPrimaryKeys() != null && !event.getPrimaryKeys().isEmpty()) {
            StringBuilder keyBuilder = new StringBuilder();
            keyBuilder.append(event.getSourceDatacenterId()).append("_");
            for (String pk : event.getPrimaryKeys()) {
                if (!event.getRowDataList().isEmpty()) {
                    Object pkValue = event.getRowDataList().get(0).getAfterValue(pk);
                    if (pkValue == null) {
                        pkValue = event.getRowDataList().get(0).getBeforeValue(pk);
                    }
                    if (pkValue != null) {
                        keyBuilder.append(pkValue).append("_");
                    }
                }
            }
            return keyBuilder.toString();
        }
        return event.getEventId();
    }

    public void flush() {
        producer.flush();
    }

    public void close() {
        log.info("Closing Kafka producer");
        producer.close();
    }
}
