package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.LinkedHashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RowData implements Serializable {

    private static final long serialVersionUID = 1L;

    private String database;

    private String table;

    private EventType eventType;

    private Map<String, Object> beforeData;

    private Map<String, Object> afterData;

    private Map<String, ColumnInfo> columns;

    private long timestamp;

    private String binlogFileName;

    private long binlogPosition;

    private long serverId;

    private String tableId;

    public enum EventType {
        INSERT,
        UPDATE,
        DELETE,
        CREATE,
        ALTER,
        DROP,
        TRUNCATE,
        RENAME,
        CINDEX,
        DINDEX,
        QUERY
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ColumnInfo implements Serializable {
        private static final long serialVersionUID = 1L;
        private String name;
        private String mysqlType;
        private String clickHouseType;
        private boolean isKey;
        private boolean isNullable;
        private int index;
    }

    public Map<String, Object> getCurrentData() {
        return eventType == EventType.DELETE ? beforeData : afterData;
    }

    public Object getColumnValue(String columnName) {
        Map<String, Object> data = getCurrentData();
        if (data == null) {
            return null;
        }
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(columnName)) {
                return entry.getValue();
            }
        }
        return null;
    }

    public RowData copy() {
        return RowData.builder()
                .database(database)
                .table(table)
                .eventType(eventType)
                .beforeData(beforeData != null ? new LinkedHashMap<>(beforeData) : null)
                .afterData(afterData != null ? new LinkedHashMap<>(afterData) : null)
                .columns(columns != null ? new LinkedHashMap<>(columns) : null)
                .timestamp(timestamp)
                .binlogFileName(binlogFileName)
                .binlogPosition(binlogPosition)
                .serverId(serverId)
                .tableId(tableId)
                .build();
    }
}
