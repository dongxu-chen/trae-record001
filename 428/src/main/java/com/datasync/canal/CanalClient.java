package com.datasync.canal;

import com.alibaba.otter.canal.client.CanalConnector;
import com.alibaba.otter.canal.client.CanalConnectors;
import com.alibaba.otter.canal.protocol.CanalEntry;
import com.alibaba.otter.canal.protocol.Message;
import com.datasync.config.SyncConfig;
import com.datasync.model.Checkpoint;
import com.datasync.model.RowData;
import com.datasync.service.KafkaProducerService;
import com.datasync.service.MetricsService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.net.InetSocketAddress;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Component
public class CanalClient {

    private final SyncConfig syncConfig;
    private final KafkaProducerService kafkaProducerService;
    private final MetricsService metricsService;
    private final CanalBinlogParser binlogParser;
    private final DDLParser ddlParser;
    private final com.datasync.service.DDLSyncService ddlSyncService;
    private final com.datasync.service.WatermarkManager watermarkManager;

    private CanalConnector connector;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private Thread consumeThread;

    public CanalClient(SyncConfig syncConfig,
                       KafkaProducerService kafkaProducerService,
                       MetricsService metricsService,
                       CanalBinlogParser binlogParser,
                       DDLParser ddlParser,
                       com.datasync.service.DDLSyncService ddlSyncService,
                       com.datasync.service.WatermarkManager watermarkManager) {
        this.syncConfig = syncConfig;
        this.kafkaProducerService = kafkaProducerService;
        this.metricsService = metricsService;
        this.binlogParser = binlogParser;
        this.ddlParser = ddlParser;
        this.ddlSyncService = ddlSyncService;
        this.watermarkManager = watermarkManager;
    }

    @PostConstruct
    public void start() {
        if (SyncConfig.SyncMode.FULL.equals(syncConfig.getMode())) {
            log.info("Sync mode is FULL, skipping canal client start");
            return;
        }

        SyncConfig.CanalConfig canalConfig = syncConfig.getCanal();

        connector = CanalConnectors.newSingleConnector(
                new InetSocketAddress(canalConfig.getHost(), canalConfig.getPort()),
                canalConfig.getDestination(),
                canalConfig.getUsername(),
                canalConfig.getPassword()
        );

        running.set(true);
        consumeThread = new Thread(this::consume, "canal-consumer-thread");
        consumeThread.setDaemon(true);
        consumeThread.start();

        log.info("Canal client started successfully, destination: {}", canalConfig.getDestination());
    }

    @PreDestroy
    public void stop() {
        running.set(false);
        if (connector != null) {
            connector.disconnect();
        }
        if (consumeThread != null) {
            consumeThread.interrupt();
        }
        log.info("Canal client stopped");
    }

    private void consume() {
        int batchSize = syncConfig.getCanal().getBatchSize();

        while (running.get()) {
            try {
                connector.connect();
                connector.subscribe(syncConfig.getCanal().getSubscribeFilter());
                connector.rollback();

                log.info("Canal client connected and subscribed");

                while (running.get()) {
                    Message message = connector.getWithoutAck(batchSize);
                    long batchId = message.getId();
                    int size = message.getEntries().size();

                    if (batchId == -1 || size == 0) {
                        try {
                            Thread.sleep(1000);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    } else {
                        processMessage(message);
                        connector.ack(batchId);
                    }
                }
            } catch (Exception e) {
                log.error("Canal client error, will reconnect after 5s", e);
                metricsService.incrementCanalErrorCount();
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            } finally {
                connector.disconnect();
            }
        }
    }

    private void processMessage(Message message) {
        List<CanalEntry.Entry> entries = message.getEntries();

        for (CanalEntry.Entry entry : entries) {
            if (entry.getEntryType() == CanalEntry.EntryType.TRANSACTIONBEGIN
                    || entry.getEntryType() == CanalEntry.EntryType.TRANSACTIONEND) {
                continue;
            }

            try {
                CanalEntry.RowChange rowChange = CanalEntry.RowChange.parseFrom(entry.getStoreValue());
                CanalEntry.EventType eventType = rowChange.getEventType();

                String database = entry.getHeader().getSchemaName();
                String table = entry.getHeader().getTableName();

                if (eventType == CanalEntry.EventType.QUERY) {
                    processDDLEvent(entry, rowChange, database, table);
                    continue;
                }

                if (eventType == CanalEntry.EventType.RENAME) {
                    continue;
                }

                if (!isTableConfigured(database, table)) {
                    continue;
                }

                if (shouldSkipByWatermark(database, table,
                        entry.getHeader().getLogfileName(),
                        entry.getHeader().getLogfileOffset())) {
                    log.debug("Skipping event before watermark for {}.{}: {}@{}",
                            database, table,
                            entry.getHeader().getLogfileName(),
                            entry.getHeader().getLogfileOffset());
                    continue;
                }

                List<RowData> rowDataList = binlogParser.parse(entry, rowChange);

                for (RowData rowData : rowDataList) {
                    metricsService.incrementBinlogEventCount(rowData.getEventType().name());

                    if (syncConfig.getKafka().isEnabled()) {
                        kafkaProducerService.send(rowData);
                    }
                }

                log.debug("Processed {} rows from {}.{}", rowDataList.size(), database, table);

            } catch (Exception e) {
                log.error("Parse canal entry error", e);
                metricsService.incrementParseErrorCount();
            }
        }
    }

    private boolean isTableConfigured(String database, String table) {
        return syncConfig.getTables().stream()
                .anyMatch(t -> t.getSourceSchema().equals(database)
                        && t.getSourceTable().equals(table));
    }

    private boolean shouldSkipByWatermark(String database, String table,
                                     String binlogFileName, long binlogPosition) {
        return watermarkManager.shouldSkipIncrementalEvent(database, table,
                binlogFileName, binlogPosition);
    }

    private void processDDLEvent(CanalEntry.Entry entry, CanalEntry.RowChange rowChange,
                                 String database, String table) {
        String sql = rowChange.getSql();
        if (sql == null || sql.trim().isEmpty()) {
            return;
        }

        log.debug("Received DDL event: {}.{}, SQL: {}", database, table, sql);

        if (!ddlParser.isDDL(sql)) {
            return;
        }

        String extractedDb = ddlParser.extractDatabase(sql);
        String extractedTable = ddlParser.extractTable(sql);

        if (extractedDb != null) {
            database = extractedDb;
        }
        if (extractedTable != null) {
            table = extractedTable;
        }

        if (!isTableConfigured(database, table)) {
            log.debug("DDL event for non-configured table: {}.{}, skipping", database, table);
            return;
        }

        com.datasync.model.DDLEvent ddlEvent = ddlParser.parse(database, table, sql);
        ddlEvent.setTimestamp(entry.getHeader().getExecuteTime());
        ddlEvent.setBinlogFileName(entry.getHeader().getLogfileName());
        ddlEvent.setBinlogPosition(entry.getHeader().getLogfileOffset());

        log.info("Processing DDL: {} for table {}.{}", ddlEvent.getDdlType(), database, table);
        ddlSyncService.processDDL(ddlEvent);

        metricsService.incrementBinlogEventCount("DDL");
    }

    public Checkpoint getCurrentCheckpoint() {
        Checkpoint checkpoint = new Checkpoint();
        checkpoint.setDestination(syncConfig.getCanal().getDestination());
        return checkpoint;
    }
}
