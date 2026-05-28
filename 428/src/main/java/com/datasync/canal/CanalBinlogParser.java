package com.datasync.canal;

import com.alibaba.otter.canal.protocol.CanalEntry;
import com.datasync.model.RowData;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class CanalBinlogParser {

    public List<RowData> parse(CanalEntry.Entry entry, CanalEntry.RowChange rowChange) {
        List<RowData> result = new ArrayList<>();

        String database = entry.getHeader().getSchemaName();
        String table = entry.getHeader().getTableName();
        long executeTime = entry.getHeader().getExecuteTime();
        String binlogFileName = entry.getHeader().getLogfileName();
        long binlogPosition = entry.getHeader().getLogfileOffset();
        long serverId = entry.getHeader().getServerId();

        RowData.EventType eventType = convertEventType(rowChange.getEventType());

        if (eventType == null) {
            return result;
        }

        for (CanalEntry.RowData rowData : rowChange.getRowDatasList()) {
            Map<String, Object> beforeData = null;
            Map<String, Object> afterData = null;
            Map<String, RowData.ColumnInfo> columnInfoMap = new LinkedHashMap<>();

            if (!rowData.getBeforeColumnsList().isEmpty()) {
                beforeData = new LinkedHashMap<>();
                for (CanalEntry.Column column : rowData.getBeforeColumnsList()) {
                    beforeData.put(column.getName(), parseValue(column));
                    columnInfoMap.put(column.getName(), buildColumnInfo(column));
                }
            }

            if (!rowData.getAfterColumnsList().isEmpty()) {
                afterData = new LinkedHashMap<>();
                for (CanalEntry.Column column : rowData.getAfterColumnsList()) {
                    afterData.put(column.getName(), parseValue(column));
                    if (!columnInfoMap.containsKey(column.getName())) {
                        columnInfoMap.put(column.getName(), buildColumnInfo(column));
                    }
                }
            }

            RowData data = RowData.builder()
                    .database(database)
                    .table(table)
                    .eventType(eventType)
                    .beforeData(beforeData)
                    .afterData(afterData)
                    .columns(columnInfoMap)
                    .timestamp(executeTime)
                    .binlogFileName(binlogFileName)
                    .binlogPosition(binlogPosition)
                    .serverId(serverId)
                    .tableId(String.valueOf(entry.getHeader().getTableId()))
                    .build();

            result.add(data);
        }

        return result;
    }

    private RowData.EventType convertEventType(CanalEntry.EventType canalEventType) {
        switch (canalEventType) {
            case INSERT:
                return RowData.EventType.INSERT;
            case UPDATE:
                return RowData.EventType.UPDATE;
            case DELETE:
                return RowData.EventType.DELETE;
            case CREATE:
                return RowData.EventType.CREATE;
            case ALTER:
                return RowData.EventType.ALTER;
            case DROP:
                return RowData.EventType.DROP;
            case TRUNCATE:
                return RowData.EventType.TRUNCATE;
            case RENAME:
                return RowData.EventType.RENAME;
            case CINDEX:
                return RowData.EventType.CINDEX;
            case DINDEX:
                return RowData.EventType.DINDEX;
            case QUERY:
                return RowData.EventType.QUERY;
            default:
                return null;
        }
    }

    private RowData.ColumnInfo buildColumnInfo(CanalEntry.Column column) {
        return RowData.ColumnInfo.builder()
                .name(column.getName())
                .mysqlType(column.getMysqlType())
                .isKey(column.getIsKey())
                .isNullable(column.getIsNull())
                .index(column.getIndex())
                .build();
    }

    private Object parseValue(CanalEntry.Column column) {
        if (column.getIsNull()) {
            return null;
        }

        String value = column.getValue();
        String mysqlType = column.getMysqlType().toLowerCase();

        try {
            if (mysqlType.contains("int") || mysqlType.contains("bit")) {
                if (mysqlType.contains("bigint")) {
                    return Long.parseLong(value);
                } else if (mysqlType.contains("tinyint") || mysqlType.contains("bit")) {
                    return Integer.parseInt(value) == 1;
                } else {
                    return Integer.parseInt(value);
                }
            } else if (mysqlType.contains("float") || mysqlType.contains("double")) {
                return Double.parseDouble(value);
            } else if (mysqlType.contains("decimal")) {
                return new java.math.BigDecimal(value);
            } else if (mysqlType.contains("date") || mysqlType.contains("time")
                    || mysqlType.contains("year")) {
                return value;
            } else if (mysqlType.contains("blob") || mysqlType.contains("binary")) {
                return com.alibaba.otter.canal.common.utils.ByteUtils.stringToBytes(value);
            } else if (mysqlType.contains("json")) {
                return value;
            } else {
                return value;
            }
        } catch (Exception e) {
            log.warn("Failed to parse value for column: {}, type: {}, value: {}",
                    column.getName(), mysqlType, value);
            return value;
        }
    }
}
