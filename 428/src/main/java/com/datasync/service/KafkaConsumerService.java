package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.listener.AcknowledgingMessageListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Slf4j
@Service
public class KafkaConsumerService {

    private final SyncConfig syncConfig;
    private final ClickHouseWriterService clickHouseWriterService;
    private final CheckpointService checkpointService;
    private final MetricsService metricsService;

    private final Map<String, List<RowData>> batchBuffer = new ConcurrentHashMap<>();

    public KafkaConsumerService(SyncConfig syncConfig,
                                ClickHouseWriterService clickHouseWriterService,
                                CheckpointService checkpointService,
                                MetricsService metricsService) {
        this.syncConfig = syncConfig;
        this.clickHouseWriterService = clickHouseWriterService;
        this.checkpointService = checkpointService;
        this.metricsService = metricsService;
    }

    @KafkaListener(
            topicPattern = "${sync.kafka.topic-prefix}.*",
            containerFactory = "kafkaListenerContainerFactory",
            concurrency = "4"
    )
    public void listen(@Payload List<RowData> records, Acknowledgment acknowledgment) {
        if (records.isEmpty()) {
            acknowledgment.acknowledge();
            return;
        }

        try {
            for (RowData rowData : records) {
                processRowData(rowData);
            }

            flushAllBuffers();
            acknowledgment.acknowledge();

            metricsService.incrementKafkaConsumeSuccessCount(records.size());
            log.debug("Processed {} records from kafka", records.size());

        } catch (Exception e) {
            log.error("Error processing kafka records", e);
            metricsService.incrementKafkaConsumeErrorCount();
            throw e;
        }
    }

    private void processRowData(RowData rowData) {
        String tableKey = rowData.getDatabase() + "." + rowData.getTable();

        batchBuffer.computeIfAbsent(tableKey, k -> new CopyOnWriteArrayList<>())
                .add(rowData);

        List<RowData> buffer = batchBuffer.get(tableKey);
        int batchSize = syncConfig.getClickhouse().getBatchSize();

        if (buffer.size() >= batchSize) {
            flushBuffer(tableKey, buffer);
        }

        metricsService.recordSyncDelay(System.currentTimeMillis() - rowData.getTimestamp());
    }

    private void flushBuffer(String tableKey, List<RowData> buffer) {
        if (buffer.isEmpty()) {
            return;
        }

        try {
            clickHouseWriterService.write(buffer);

            for (RowData rowData : buffer) {
                checkpointService.updateCheckpoint(
                        rowData.getDatabase(),
                        rowData.getTable(),
                        rowData.getBinlogFileName(),
                        rowData.getBinlogPosition(),
                        rowData.getTimestamp()
                );
            }

            log.debug("Flushed {} records for table {}", buffer.size(), tableKey);
        } catch (Exception e) {
            log.error("Failed to flush buffer for table {}", tableKey, e);
            throw e;
        } finally {
            buffer.clear();
        }
    }

    private void flushAllBuffers() {
        for (Map.Entry<String, List<RowData>> entry : batchBuffer.entrySet()) {
            flushBuffer(entry.getKey(), entry.getValue());
        }
    }

    public void flushAll() {
        flushAllBuffers();
    }
}
