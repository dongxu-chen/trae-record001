package com.datasync.service;

import com.datasync.config.SyncConfig;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;
import org.springframework.util.concurrent.ListenableFuture;
import org.springframework.util.concurrent.ListenableFutureCallback;

@Slf4j
@Service
public class KafkaProducerService {

    private final KafkaTemplate<String, RowData> kafkaTemplate;
    private final SyncConfig syncConfig;
    private final MetricsService metricsService;

    public KafkaProducerService(KafkaTemplate<String, RowData> kafkaTemplate,
                                SyncConfig syncConfig,
                                MetricsService metricsService) {
        this.kafkaTemplate = kafkaTemplate;
        this.syncConfig = syncConfig;
        this.metricsService = metricsService;
    }

    public void send(RowData rowData) {
        if (!syncConfig.getKafka().isEnabled()) {
            return;
        }

        String topic = buildTopic(rowData);
        String key = buildKey(rowData);

        ListenableFuture<SendResult<String, RowData>> future = kafkaTemplate.send(topic, key, rowData);

        future.addCallback(new ListenableFutureCallback<SendResult<String, RowData>>() {
            @Override
            public void onSuccess(SendResult<String, RowData> result) {
                log.debug("Sent row data to topic: {}, partition: {}, offset: {}",
                        topic,
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
                metricsService.incrementKafkaSendSuccessCount();
            }

            @Override
            public void onFailure(Throwable ex) {
                log.error("Failed to send row data to topic: {}", topic, ex);
                metricsService.incrementKafkaSendErrorCount();
            }
        });
    }

    private String buildTopic(RowData rowData) {
        return syncConfig.getKafka().getTopicPrefix() + rowData.getDatabase() + "_" + rowData.getTable();
    }

    private String buildKey(RowData rowData) {
        return rowData.getDatabase() + "." + rowData.getTable() + "." +
                (rowData.getEventType() == RowData.EventType.DELETE ?
                        rowData.getBeforeData() : rowData.getAfterData());
    }
}
