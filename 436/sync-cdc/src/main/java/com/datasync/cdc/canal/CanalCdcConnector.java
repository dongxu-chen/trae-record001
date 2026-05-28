package com.datasync.cdc.canal;

import com.alibaba.otter.canal.client.CanalConnector;
import com.alibaba.otter.canal.client.CanalConnectors;
import com.alibaba.otter.canal.protocol.CanalEntry;
import com.alibaba.otter.canal.protocol.Message;
import com.datasync.cdc.CdcConnector;
import com.datasync.common.enums.DatabaseType;
import com.datasync.common.enums.OperationType;
import com.datasync.common.model.ColumnMetaData;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.RowData;
import com.datasync.common.util.GlobalTransactionManager;
import com.datasync.common.util.HybridLogicalClock;
import com.datasync.common.util.IdGenerator;
import lombok.extern.slf4j.Slf4j;

import java.net.InetSocketAddress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

@Slf4j
public class CanalCdcConnector implements CdcConnector {
    private final CanalConnectorConfig config;
    private CanalConnector connector;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private ExecutorService executorService;
    private Consumer<List<DataChangeEvent>> eventListener;
    private final HybridLogicalClock hlc;
    private final GlobalTransactionManager gtxManager;

    public CanalCdcConnector(CanalConnectorConfig config) {
        this.config = config;
        this.hlc = new HybridLogicalClock(config.getConnectorId());
        this.gtxManager = new GlobalTransactionManager(config.getDatacenterId(), config.getConnectorId(), 100000, 60);
    }

    @Override
    public void start() {
        if (running.compareAndSet(false, true)) {
            log.info("Starting Canal CDC connector: {}", config.getConnectorId());
            connector = CanalConnectors.newSingleConnector(
                    new InetSocketAddress(config.getHostname(), config.getPort()),
                    config.getDestination(),
                    config.getUsername(),
                    config.getPassword()
            );
            connector.connect();
            connector.subscribe(config.getSubscribeFilter());
            connector.rollback();

            executorService = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "canal-connector-" + config.getConnectorId());
                t.setDaemon(true);
                return t;
            });
            executorService.submit(this::pollLoop);
            log.info("Canal CDC connector started: {}", config.getConnectorId());
        }
    }

    @Override
    public void stop() {
        if (running.compareAndSet(true, false)) {
            log.info("Stopping Canal CDC connector: {}", config.getConnectorId());
            if (executorService != null) {
                executorService.shutdownNow();
            }
            if (connector != null) {
                connector.disconnect();
            }
            log.info("Canal CDC connector stopped: {}", config.getConnectorId());
        }
    }

    @Override
    public boolean isRunning() {
        return running.get();
    }

    @Override
    public void registerListener(Consumer<List<DataChangeEvent>> listener) {
        this.eventListener = listener;
    }

    @Override
    public String getConnectorId() {
        return config.getConnectorId();
    }

    @Override
    public String getDatabaseId() {
        return config.getDatabaseId();
    }

    private void pollLoop() {
        while (running.get()) {
            try {
                Message message = connector.getWithoutAck(config.getBatchSize(), config.getPollTimeoutMs());
                long batchId = message.getId();
                int size = message.getEntries().size();

                if (batchId == -1 || size == 0) {
                    Thread.sleep(100);
                    continue;
                }

                List<DataChangeEvent> events = parseMessage(message);
                if (!events.isEmpty() && eventListener != null) {
                    eventListener.accept(events);
                }

                connector.ack(batchId);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Error in Canal poll loop for connector: {}", config.getConnectorId(), e);
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private List<DataChangeEvent> parseMessage(Message message) {
        List<DataChangeEvent> events = new ArrayList<>();
        for (CanalEntry.Entry entry : message.getEntries()) {
            if (entry.getEntryType() == CanalEntry.EntryType.TRANSACTIONBEGIN ||
                    entry.getEntryType() == CanalEntry.EntryType.TRANSACTIONEND) {
                continue;
            }

            if (entry.getEntryType() != CanalEntry.EntryType.ROWDATA) {
                continue;
            }

            try {
                CanalEntry.RowChange rowChange = CanalEntry.RowChange.parseFrom(entry.getStoreValue());
                DataChangeEvent event = buildEvent(entry, rowChange);
                if (event != null) {
                    events.add(event);
                }
            } catch (Exception e) {
                log.error("Error parsing Canal entry", e);
            }
        }
        return events;
    }

    private DataChangeEvent buildEvent(CanalEntry.Entry entry, CanalEntry.RowChange rowChange) {
        CanalEntry.EventType eventType = rowChange.getEventType();
        if (eventType == CanalEntry.EventType.QUERY || eventType == CanalEntry.EventType.RENAME) {
            return null;
        }

        String schemaName = entry.getHeader().getSchemaName();
        String tableName = entry.getHeader().getTableName();
        long executeTime = entry.getHeader().getExecuteTime();

        Map<String, ColumnMetaData> columnMetaData = new HashMap<>();
        List<String> primaryKeys = new ArrayList<>();

        if (!rowChange.getRowDatasList().isEmpty()) {
            CanalEntry.RowData firstRow = rowChange.getRowDatasList().get(0);
            List<CanalEntry.Column> columns = !firstRow.getAfterColumnsList().isEmpty()
                    ? firstRow.getAfterColumnsList()
                    : firstRow.getBeforeColumnsList();

            for (int i = 0; i < columns.size(); i++) {
                CanalEntry.Column col = columns.get(i);
                ColumnMetaData meta = ColumnMetaData.builder()
                        .columnName(col.getName())
                        .columnType(col.getSqlType())
                        .columnTypeName(col.getMysqlType())
                        .isPrimaryKey(col.getIsKey())
                        .isNullable(!col.getIsKey())
                        .ordinalPosition(i)
                        .build();
                columnMetaData.put(col.getName(), meta);
                if (col.getIsKey()) {
                    primaryKeys.add(col.getName());
                }
            }
        }

        List<RowData> rowDataList = new ArrayList<>();
        String businessKey = null;
        Long businessVersion = null;

        for (CanalEntry.RowData rowData : rowChange.getRowDatasList()) {
            RowData data = new RowData();

            for (CanalEntry.Column col : rowData.getBeforeColumnsList()) {
                data.addBeforeColumn(col.getName(), col.getValue());
            }

            for (CanalEntry.Column col : rowData.getAfterColumnsList()) {
                data.addAfterColumn(col.getName(), col.getValue());
            }

            rowDataList.add(data);

            if (config.getBusinessKeyColumn() != null && businessKey == null) {
                Object keyValue = data.getAfterValue(config.getBusinessKeyColumn());
                if (keyValue != null) {
                    businessKey = String.valueOf(keyValue);
                }
            }

            if (config.getVersionColumn() != null && businessVersion == null) {
                Object versionValue = data.getAfterValue(config.getVersionColumn());
                if (versionValue != null) {
                    try {
                        businessVersion = Long.parseLong(String.valueOf(versionValue));
                    } catch (NumberFormatException ignored) {
                    }
                }
            }
        }

        HybridLogicalClock.HlcTimestamp hlcNow = hlc.now();
        String globalTxId = gtxManager.generateGlobalTransactionId(businessKey);

        return DataChangeEvent.builder()
                .eventId(IdGenerator.generateEventId())
                .globalTransactionId(globalTxId)
                .visitedDatacenters(new ArrayList<>(Collections.singletonList(config.getDatacenterId())))
                .sourceDatacenterId(config.getDatacenterId())
                .sourceDatabaseId(config.getDatabaseId())
                .sourceDatabaseType(DatabaseType.MYSQL)
                .schemaName(schemaName)
                .tableName(tableName)
                .operationType(mapOperationType(eventType))
                .timestamp(System.currentTimeMillis())
                .executionTime(executeTime)
                .hlcTimestamp(hlcNow.getPhysicalTime())
                .logicalClock(hlcNow.getLogicalTime())
                .wallClock(System.currentTimeMillis())
                .primaryKeys(primaryKeys)
                .columnMetaData(columnMetaData)
                .rowDataList(rowDataList)
                .businessKey(businessKey)
                .businessVersion(businessVersion)
                .syncTimestamp(System.currentTimeMillis())
                .build();
    }

    private OperationType mapOperationType(CanalEntry.EventType eventType) {
        switch (eventType) {
            case INSERT:
                return OperationType.INSERT;
            case UPDATE:
                return OperationType.UPDATE;
            case DELETE:
                return OperationType.DELETE;
            case CREATE:
            case ALTER:
            case DROP:
            case TRUNCATE:
                return OperationType.DDL;
            default:
                throw new IllegalArgumentException("Unsupported event type: " + eventType);
        }
    }
}
