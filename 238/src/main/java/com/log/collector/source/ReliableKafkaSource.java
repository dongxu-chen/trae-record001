package com.log.collector.source;

import com.log.collector.util.BackpressureManager;
import com.log.collector.util.IdempotentManager;
import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.EventDeliveryException;
import org.apache.flume.PollableSource;
import org.apache.flume.conf.Configurable;
import org.apache.flume.event.SimpleEvent;
import org.apache.flume.source.AbstractSource;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.TopicPartition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

public class ReliableKafkaSource extends AbstractSource
        implements Configurable, PollableSource {

    private static final Logger logger = LoggerFactory.getLogger(ReliableKafkaSource.class);

    private KafkaConsumer<String, String> consumer;
    private String topic;
    private String bootstrapServers;
    private String groupId;
    private int maxBatchSize;
    private long pollTimeout;
    private String autoOffsetReset;
    private boolean asyncCommit;
    private long asyncCommitIntervalMs;

    private BackpressureManager backpressureManager;
    private IdempotentManager idempotentManager;
    private boolean enableIdempotent;

    private ExecutorService asyncExecutor;
    private LinkedBlockingQueue<PendingBatch> pendingBatches;
    private final AtomicBoolean isRunning = new AtomicBoolean(false);
    private final AtomicLong totalProcessed = new AtomicLong(0);
    private final AtomicLong totalDeduped = new AtomicLong(0);

    private final AtomicBoolean consumerPaused = new AtomicBoolean(false);
    private long lastBackpressureCheck = 0;
    private static final long BACKPRESSURE_CHECK_INTERVAL_MS = 1000;

    @Override
    public void configure(Context context) {
        bootstrapServers = context.getString("kafka.bootstrap.servers", "localhost:9092");
        topic = context.getString("kafka.topic", "logs");
        groupId = context.getString("kafka.group.id", "log-collector-group");
        maxBatchSize = context.getInteger("max.batch.size", 1000);
        pollTimeout = context.getLong("poll.timeout.ms", 1000L);
        autoOffsetReset = context.getString("auto.offset.reset", "latest");
        asyncCommit = context.getBoolean("async.commit", true);
        asyncCommitIntervalMs = context.getLong("async.commit.interval.ms", 5000L);

        enableIdempotent = context.getBoolean("idempotent.enabled", true);

        double highWatermark = context.getDouble("backpressure.high.watermark", 0.85);
        double lowWatermark = context.getDouble("backpressure.low.watermark", 0.50);
        long minBackpressureMs = context.getLong("backpressure.min.duration.ms", 1000L);
        long maxBackpressureMs = context.getLong("backpressure.max.duration.ms", 30000L);

        backpressureManager = BackpressureManager.getInstance();
        backpressureManager.configure(highWatermark, lowWatermark, minBackpressureMs, maxBackpressureMs);

        if (enableIdempotent) {
            Properties redisProps = new Properties();
            redisProps.setProperty("redis.host", context.getString("redis.host", "localhost"));
            redisProps.setProperty("redis.port", String.valueOf(context.getInteger("redis.port", 6379)));
            redisProps.setProperty("redis.password", context.getString("redis.password", ""));
            redisProps.setProperty("redis.database", String.valueOf(context.getInteger("redis.database", 0)));
            redisProps.setProperty("redis.idempotent.enabled", "true");
            redisProps.setProperty("redis.ttl.seconds", String.valueOf(context.getLong("redis.ttl.seconds", 86400)));
            idempotentManager = IdempotentManager.getInstance(redisProps);
        }

        logger.info("Kafka Source configured - bootstrap: {}, topic: {}, groupId: {}, async: {}, idempotent: {}",
                bootstrapServers, topic, groupId, asyncCommit, enableIdempotent);
    }

    @Override
    public void start() {
        logger.info("Starting ReliableKafkaSource...");

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
                "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
                "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, autoOffsetReset);
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, maxBatchSize);
        props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, "30000");
        props.put(ConsumerConfig.HEARTBEAT_INTERVAL_MS_CONFIG, "10000");
        props.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, "300000");

        consumer = new KafkaConsumer<>(props);
        consumer.subscribe(Collections.singletonList(topic));

        pendingBatches = new LinkedBlockingQueue<>(100);
        asyncExecutor = Executors.newSingleThreadExecutor();
        asyncExecutor.submit(this::asyncOffsetCommitWorker);

        isRunning.set(true);
        logger.info("ReliableKafkaSource started successfully");
        super.start();
    }

    @Override
    public Status process() throws EventDeliveryException {
        if (!isRunning.get()) {
            return Status.BACKOFF;
        }

        checkBackpressure();

        if (backpressureManager.isBackpressureActive()) {
            if (backpressureManager.shouldPause()) {
                pauseConsumer();
                return Status.BACKOFF;
            } else {
                resumeConsumer();
            }
        }

        try {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(pollTimeout));

            if (records.isEmpty()) {
                return Status.BACKOFF;
            }

            List<Event> events = new ArrayList<>();
            Map<TopicPartition, Long> offsetsToCommit = new HashMap<>();
            List<String> idempotentIds = new ArrayList<>();

            for (ConsumerRecord<String, String> record : records) {
                Event event = new SimpleEvent();

                Map<String, String> headers = new HashMap<>();
                headers.put("timestamp", String.valueOf(record.timestamp()));
                headers.put("topic", record.topic());
                headers.put("partition", String.valueOf(record.partition()));
                headers.put("offset", String.valueOf(record.offset()));
                headers.put("key", record.key() != null ? record.key() : "");
                event.setHeaders(headers);

                event.setBody(record.value().getBytes());

                if (enableIdempotent) {
                    String idempotentId = idempotentManager.generateIdempotentId(event);
                    headers.put("idempotent_id", idempotentId);
                    if (idempotentManager.isProcessed(idempotentId)) {
                        totalDeduped.incrementAndGet();
                        continue;
                    }
                    idempotentIds.add(idempotentId);
                }

                events.add(event);

                TopicPartition tp = new TopicPartition(record.topic(), record.partition());
                long currentOffset = offsetsToCommit.getOrDefault(tp, -1L);
                if (record.offset() > currentOffset) {
                    offsetsToCommit.put(tp, record.offset() + 1);
                }
            }

            if (!events.isEmpty()) {
                getChannelProcessor().processEventBatch(events);

                if (enableIdempotent) {
                    for (String id : idempotentIds) {
                        idempotentManager.markProcessedAsync(id);
                    }
                }

                if (asyncCommit) {
                    pendingBatches.offer(new PendingBatch(offsetsToCommit, System.currentTimeMillis()));
                } else {
                    commitOffsets(offsetsToCommit);
                }

                totalProcessed.addAndGet(events.size());
            }

            logger.debug("Processed {} events, deduped: {}", events.size(), totalDeduped.get());
            return Status.READY;

        } catch (Exception e) {
            logger.error("Error processing Kafka messages", e);
            throw new EventDeliveryException("Failed to process Kafka messages", e);
        }
    }

    private void checkBackpressure() {
        long now = System.currentTimeMillis();
        if (now - lastBackpressureCheck < BACKPRESSURE_CHECK_INTERVAL_MS) {
            return;
        }
        lastBackpressureCheck = now;
    }

    private void pauseConsumer() {
        if (consumerPaused.compareAndSet(false, true)) {
            consumer.pause(consumer.assignment());
            logger.info("Kafka consumer paused due to backpressure");
        }
    }

    private void resumeConsumer() {
        if (consumerPaused.compareAndSet(true, false)) {
            consumer.resume(consumer.assignment());
            logger.info("Kafka consumer resumed");
        }
    }

    private void asyncOffsetCommitWorker() {
        logger.info("Async offset commit worker started");

        while (isRunning.get() || !pendingBatches.isEmpty()) {
            try {
                PendingBatch batch = pendingBatches.poll(100, TimeUnit.MILLISECONDS);
                if (batch != null) {
                    commitOffsets(batch.offsets);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.error("Error in async offset commit", e);
            }
        }

        logger.info("Async offset commit worker stopped");
    }

    private void commitOffsets(Map<TopicPartition, Long> offsets) {
        if (!offsets.isEmpty()) {
            try {
                Map<TopicPartition, org.apache.kafka.clients.consumer.OffsetAndMetadata> commitMap = new HashMap<>();
                for (Map.Entry<TopicPartition, Long> entry : offsets.entrySet()) {
                    commitMap.put(entry.getKey(),
                            new org.apache.kafka.clients.consumer.OffsetAndMetadata(entry.getValue()));
                }
                consumer.commitSync(commitMap);
                logger.debug("Committed offsets: {}", offsets);
            } catch (Exception e) {
                logger.warn("Offset commit failed, will retry", e);
            }
        }
    }

    public void triggerBackpressure() {
        backpressureManager.triggerBackpressure();
    }

    public void releaseBackpressure() {
        backpressureManager.releaseBackpressure();
    }

    public boolean isBackpressureActive() {
        return backpressureManager.isBackpressureActive();
    }

    @Override
    public void stop() {
        logger.info("Stopping ReliableKafkaSource...");
        isRunning.set(false);

        if (asyncExecutor != null) {
            asyncExecutor.shutdown();
            try {
                if (!asyncExecutor.awaitTermination(10, TimeUnit.SECONDS)) {
                    asyncExecutor.shutdownNow();
                }
            } catch (InterruptedException e) {
                asyncExecutor.shutdownNow();
            }
        }

        while (!pendingBatches.isEmpty()) {
            PendingBatch batch = pendingBatches.poll();
            if (batch != null) {
                commitOffsets(batch.offsets);
            }
        }

        if (consumer != null) {
            consumer.close();
        }

        if (idempotentManager != null) {
            idempotentManager.close();
        }

        logger.info("ReliableKafkaSource stopped - total processed: {}, total deduped: {}",
                totalProcessed.get(), totalDeduped.get());
        super.stop();
    }

    @Override
    public long getBackOffSleepIncrement() {
        return backpressureManager.isBackpressureActive() ? 5000 : 1000;
    }

    @Override
    public long getMaxBackOffSleepInterval() {
        return backpressureManager.isBackpressureActive() ? 30000 : 10000;
    }

    private static class PendingBatch {
        final Map<TopicPartition, Long> offsets;
        final long createTime;

        PendingBatch(Map<TopicPartition, Long> offsets, long createTime) {
            this.offsets = offsets;
            this.createTime = createTime;
        }
    }
}
