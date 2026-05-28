package com.datasync.cdc.debezium;

import com.datasync.cdc.CdcConnector;
import com.datasync.common.enums.OperationType;
import com.datasync.common.model.ColumnMetaData;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.RowData;
import com.datasync.common.util.GlobalTransactionManager;
import com.datasync.common.util.HybridLogicalClock;
import com.datasync.common.util.IdGenerator;
import io.debezium.engine.ChangeEvent;
import io.debezium.engine.DebeziumEngine;
import io.debezium.engine.format.Json;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.connect.data.Field;
import org.apache.kafka.connect.data.Schema;
import org.apache.kafka.connect.data.Struct;
import org.apache.kafka.connect.source.SourceRecord;

import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

@Slf4j
public class DebeziumCdcConnector implements CdcConnector {
    private final DebeziumConnectorConfig config;
    private DebeziumEngine<ChangeEvent<SourceRecord, SourceRecord>> engine;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private ExecutorService executorService;
    private Consumer<List<DataChangeEvent>> eventListener;
    private final HybridLogicalClock hlc;
    private final GlobalTransactionManager gtxManager;

    public DebeziumCdcConnector(DebeziumConnectorConfig config) {
        this.config = config;
        this.hlc = new HybridLogicalClock(config.getConnectorId());
        this.gtxManager = new GlobalTransactionManager(config.getDatacenterId(), config.getConnectorId(), 100000, 60);
    }

    @Override
    public void start() {
        if (running.compareAndSet(false, true)) {
            log.info("Starting Debezium CDC connector: {}", config.getConnectorId());

            engine = DebeziumEngine.create(Json.class)
                    .using(config.toProperties())
                    .notifying(this::handleRecords)
                    .build();

            executorService = Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "debezium-connector-" + config.getConnectorId());
                t.setDaemon(true);
                return t;
            });
            executorService.submit(engine);
            log.info("Debezium CDC connector started: {}", config.getConnectorId());
        }
    }

    @Override
    public void stop() {
        if (running.compareAndSet(true, false)) {
            log.info("Stopping Debezium CDC connector: {}", config.getConnectorId());
            if (engine != null) {
                try {
                    engine.close();
                } catch (Exception e) {
                    log.error("Error closing Debezium engine", e);
                }
            }
            if (executorService != null) {
                executorService.shutdownNow();
            }
            log.info("Debezium CDC connector stopped: {}", config.getConnectorId());
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

    private void handleRecords(List<ChangeEvent<SourceRecord, SourceRecord>> records) {
        if (!running.get() || eventListener == null) {
            return;
        }

        try {
            List<DataChangeEvent> events = new ArrayList<>();
            for (ChangeEvent<SourceRecord, SourceRecord> record : records) {
                DataChangeEvent event = parseRecord(record);
                if (event != null) {
                    events.add(event);
                }
            }

            if (!events.isEmpty()) {
                eventListener.accept(events);
            }
        } catch (Exception e) {
            log.error("Error handling Debezium records", e);
        }
    }

    private DataChangeEvent parseRecord(ChangeEvent<SourceRecord, SourceRecord> record) {
        SourceRecord sourceRecord = record.value();
        if (sourceRecord == null || sourceRecord.value() == null) {
            return null;
        }

        Struct value = (Struct) sourceRecord.value();
        Struct source = value.getStruct("source");

        String schemaName = source.getString("db");
        String tableName = source.getString("table");
        Long tsMs = source.getInt64("ts_ms");
        String operation = value.getString("op");

        if (operation == null) {
            return null;
        }

        OperationType operationType = mapOperationType(operation);

        Map<String, ColumnMetaData> columnMetaData = new HashMap<>();
        List<String> primaryKeys = new ArrayList<>();

        Struct before = value.getStruct("before");
        Struct after = value.getStruct("after");

        Schema schema = sourceRecord.valueSchema();
        if (after != null) {
            extractColumnMetaData(after.schema(), columnMetaData, primaryKeys);
        } else if (before != null) {
            extractColumnMetaData(before.schema(), columnMetaData, primaryKeys);
        }

        List<RowData> rowDataList = new ArrayList<>();
        RowData rowData = new RowData();

        if (before != null) {
            for (Field field : before.schema().fields()) {
                rowData.addBeforeColumn(field.name(), before.get(field));
            }
        }

        if (after != null) {
            for (Field field : after.schema().fields()) {
                rowData.addAfterColumn(field.name(), after.get(field));
            }
        }

        rowDataList.add(rowData);

        String businessKey = null;
        Long businessVersion = null;

        if (config.getBusinessKeyColumn() != null) {
            Object keyValue = after != null ? after.get(config.getBusinessKeyColumn()) : null;
            if (keyValue == null && before != null) {
                keyValue = before.get(config.getBusinessKeyColumn());
            }
            if (keyValue != null) {
                businessKey = String.valueOf(keyValue);
            }
        }

        if (config.getVersionColumn() != null) {
            Object versionValue = after != null ? after.get(config.getVersionColumn()) : null;
            if (versionValue == null && before != null) {
                versionValue = before.get(config.getVersionColumn());
            }
            if (versionValue != null) {
                try {
                    businessVersion = ((Number) versionValue).longValue();
                } catch (Exception ignored) {
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
                .sourceDatabaseType(config.getDatabaseType())
                .schemaName(schemaName)
                .tableName(tableName)
                .operationType(operationType)
                .timestamp(System.currentTimeMillis())
                .executionTime(tsMs)
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

    private void extractColumnMetaData(Schema schema, Map<String, ColumnMetaData> columnMetaData, List<String> primaryKeys) {
        int idx = 0;
        for (Field field : schema.fields()) {
            ColumnMetaData meta = ColumnMetaData.builder()
                    .columnName(field.name())
                    .columnType(mapSqlType(field.schema().type()))
                    .columnTypeName(field.schema().type().getName())
                    .columnClassName(field.schema().type().getClass().getName())
                    .isNullable(field.schema().isOptional())
                    .ordinalPosition(idx++)
                    .build();
            columnMetaData.put(field.name(), meta);
        }
    }

    private int mapSqlType(Schema.Type type) {
        switch (type) {
            case INT8:
                return java.sql.Types.TINYINT;
            case INT16:
                return java.sql.Types.SMALLINT;
            case INT32:
                return java.sql.Types.INTEGER;
            case INT64:
                return java.sql.Types.BIGINT;
            case FLOAT32:
                return java.sql.Types.FLOAT;
            case FLOAT64:
                return java.sql.Types.DOUBLE;
            case BOOLEAN:
                return java.sql.Types.BOOLEAN;
            case STRING:
                return java.sql.Types.VARCHAR;
            case BYTES:
                return java.sql.Types.BINARY;
            default:
                return java.sql.Types.OTHER;
        }
    }

    private OperationType mapOperationType(String op) {
        switch (op) {
            case "c":
                return OperationType.INSERT;
            case "u":
                return OperationType.UPDATE;
            case "d":
                return OperationType.DELETE;
            case "r":
                return OperationType.INSERT;
            default:
                throw new IllegalArgumentException("Unknown operation type: " + op);
        }
    }
}
