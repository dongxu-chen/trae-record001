package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Checkpoint implements Serializable {

    private static final long serialVersionUID = 1L;

    private String destination;

    private long createTime;

    private long updateTime;

    private Map<String, TableCheckpoint> tableCheckpoints = new ConcurrentHashMap<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableCheckpoint implements Serializable {
        private static final long serialVersionUID = 1L;
        private String database;
        private String table;
        private String binlogFileName;
        private long binlogPosition;
        private long timestamp;
        private long lastSyncCount;
        private String status;
        private Map<String, Object> extra;
    }

    public void updateTableCheckpoint(String database, String table,
                                      String binlogFileName, long binlogPosition, long timestamp) {
        TableCheckpoint checkpoint = tableCheckpoints.computeIfAbsent(database + "." + table,
                k -> new TableCheckpoint());
        checkpoint.setDatabase(database);
        checkpoint.setTable(table);
        checkpoint.setBinlogFileName(binlogFileName);
        checkpoint.setBinlogPosition(binlogPosition);
        checkpoint.setTimestamp(timestamp);
        checkpoint.setLastSyncCount(checkpoint.getLastSyncCount() + 1);
    }

    public TableCheckpoint getTableCheckpoint(String database, String table) {
        return tableCheckpoints.get(database + "." + table);
    }
}
