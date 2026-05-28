package com.datasync.bootstrap;

import com.datasync.cdc.CdcConnector;
import com.datasync.conflict.ConflictEngine;
import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.SyncResult;
import com.datasync.common.util.GlobalTransactionManager;
import com.datasync.common.util.HybridLogicalClock;
import com.datasync.coordinator.ZookeeperCoordinator;
import com.datasync.kafka.consumer.KafkaMessageConsumer;
import com.datasync.kafka.producer.KafkaMessageProducer;
import com.datasync.monitor.SyncMonitorService;
import com.datasync.writer.DatabaseWriter;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;

@Slf4j
public class DataSyncOrchestrator {
    private final String datacenterId;
    private final List<CdcConnector> cdcConnectors;
    private final KafkaMessageProducer kafkaProducer;
    private final KafkaMessageConsumer kafkaConsumer;
    private final ConflictEngine conflictEngine;
    private final DatabaseWriter databaseWriter;
    private final ZookeeperCoordinator zkCoordinator;
    private final SyncMonitorService monitorService;
    private final GlobalTransactionManager gtxManager;
    private final HybridLogicalClock hlc;

    private volatile boolean running = false;

    @Builder
    public DataSyncOrchestrator(String datacenterId,
                                List<CdcConnector> cdcConnectors,
                                KafkaMessageProducer kafkaProducer,
                                KafkaMessageConsumer kafkaConsumer,
                                ConflictEngine conflictEngine,
                                DatabaseWriter databaseWriter,
                                ZookeeperCoordinator zkCoordinator,
                                SyncMonitorService monitorService) {
        this.datacenterId = datacenterId;
        this.cdcConnectors = cdcConnectors != null ? cdcConnectors : new ArrayList<>();
        this.kafkaProducer = kafkaProducer;
        this.kafkaConsumer = kafkaConsumer;
        this.conflictEngine = conflictEngine;
        this.databaseWriter = databaseWriter;
        this.zkCoordinator = zkCoordinator;
        this.monitorService = monitorService;
        this.gtxManager = new GlobalTransactionManager(datacenterId, "orchestrator", 100000, 60);
        this.hlc = new HybridLogicalClock(datacenterId);
    }

    @PostConstruct
    public void start() {
        log.info("Starting Data Sync Orchestrator for datacenter: {}", datacenterId);
        running = true;

        if (zkCoordinator != null) {
            try {
                zkCoordinator.start();
            } catch (Exception e) {
                log.error("Failed to start ZooKeeper coordinator", e);
            }
        }

        if (kafkaProducer != null) {
            for (CdcConnector connector : cdcConnectors) {
                connector.registerListener(this::handleCdcEvents);
                connector.start();
            }
        }

        if (kafkaConsumer != null) {
            kafkaConsumer.registerListener(this::handleConsumerEvents);
            kafkaConsumer.start();
        }

        log.info("Data Sync Orchestrator started successfully for datacenter: {}", datacenterId);
    }

    @PreDestroy
    public void stop() {
        log.info("Stopping Data Sync Orchestrator for datacenter: {}", datacenterId);
        running = false;

        for (CdcConnector connector : cdcConnectors) {
            connector.stop();
        }

        if (kafkaConsumer != null) {
            kafkaConsumer.stop();
        }

        if (kafkaProducer != null) {
            kafkaProducer.close();
        }

        if (zkCoordinator != null) {
            zkCoordinator.stop();
        }

        if (databaseWriter != null) {
            databaseWriter.shutdown();
        }

        if (monitorService != null) {
            monitorService.shutdown();
        }

        log.info("Data Sync Orchestrator stopped for datacenter: {}", datacenterId);
    }

    private void handleCdcEvents(List<DataChangeEvent> events) {
        if (!running || kafkaProducer == null) {
            return;
        }

        log.debug("Handling {} CDC events from local database", events.size());
        kafkaProducer.sendBatch(events);
    }

    private void handleConsumerEvents(List<DataChangeEvent> events) {
        if (!running || databaseWriter == null) {
            return;
        }

        log.debug("Handling {} events from Kafka consumer", events.size());

        for (DataChangeEvent event : events) {
            try {
                processEvent(event);
            } catch (Exception e) {
                log.error("Error processing event: eventId={}", event.getEventId(), e);
            }
        }
    }

    private void processEvent(DataChangeEvent event) {
        log.debug("Processing event: eventId={}, globalTxId={}, table={}, operation={}",
                event.getEventId(), event.getGlobalTransactionId(), event.getFullTableName(), event.getOperationType());

        if (isLoopbackEvent(event)) {
            log.debug("Skipping loopback event: eventId={}, globalTxId={}, sourceDatacenter={}",
                    event.getEventId(), event.getGlobalTransactionId(), event.getSourceDatacenterId());
            return;
        }

        if (event.getGlobalTransactionId() != null) {
            boolean isNew = gtxManager.checkAndMarkProcessed(event.getGlobalTransactionId());
            if (!isNew) {
                log.debug("Skipping already processed transaction: eventId={}, globalTxId={}",
                        event.getEventId(), event.getGlobalTransactionId());
                return;
            }
        }

        event.addVisitedDatacenter(datacenterId);

        if (event.getHlcTimestamp() != null && event.getLogicalClock() != null) {
            hlc.receive(event.getHlcTimestamp(), event.getLogicalClock());
        }

        ConflictResult conflictResult = ConflictResult.noConflict();
        if (conflictEngine != null) {
            conflictResult = conflictEngine.checkAndResolve(event);

            if (conflictResult.isHasConflict()) {
                log.info("Conflict detected for event: eventId={}, resolution={}, reason={}",
                        event.getEventId(), conflictResult.getResolution(), conflictResult.getConflictReason());

                if (monitorService != null) {
                    monitorService.recordConflict(event, conflictResult);
                }

                if (conflictResult.getResolution() == ConflictResult.ConflictResolution.APPLY_NEWER
                        && conflictResult.getWinnerEventId() != null
                        && conflictResult.getWinnerEventId().equals(event.getEventId())) {
                    writeEvent(event, conflictResult);
                }
                return;
            }
        }

        writeEvent(event, conflictResult);
    }

    private boolean isLoopbackEvent(DataChangeEvent event) {
        if (event.getSourceDatacenterId() != null && event.getSourceDatacenterId().equals(datacenterId)) {
            return true;
        }
        if (event.hasVisitedDatacenter(datacenterId)) {
            return true;
        }
        if (event.getGlobalTransactionId() != null) {
            return gtxManager.isLoopback(event.getGlobalTransactionId(), datacenterId);
        }
        return false;
    }

    private void writeEvent(DataChangeEvent event, ConflictResult conflictResult) {
        if (databaseWriter == null) {
            return;
        }

        SyncResult result = databaseWriter.write(event);
        result.setConflictResult(conflictResult);

        if (monitorService != null) {
            monitorService.recordSync(event, result);
        }

        if (!result.isSuccess()) {
            log.error("Failed to write event: eventId={}, error={}", event.getEventId(), result.getMessage());
        }
    }

    public boolean isRunning() {
        return running;
    }

    public String getDatacenterId() {
        return datacenterId;
    }
}
