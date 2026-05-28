package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Watermark implements Serializable {

    private static final long serialVersionUID = 1L;

    private Map<String, TableWatermark> tableWatermarks = new ConcurrentHashMap<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TableWatermark implements Serializable {
        private static final long serialVersionUID = 1L;

        private String database;
        private String table;
        private String binlogFileName;
        private long binlogPosition;
        private long timestamp;
        private WatermarkType type;
        private String status;
        private long fullSyncStartTime;
        private long fullSyncEndTime;

        public enum WatermarkType {
            FULL_SYNC_START,
            FULL_SYNC_END,
            INCREMENTAL_START
        }

        public enum Status {
            PENDING,
            RUNNING,
            COMPLETED,
            FAILED
        }
    }

    public void setTableWatermark(String database, String table, TableWatermark watermark) {
        tableWatermarks.put(database + "." + table, watermark);
    }

    public TableWatermark getTableWatermark(String database, String table) {
        return tableWatermarks.get(database + "." + table);
    }

    public boolean isFullSyncCompleted(String database, String table) {
        TableWatermark watermark = getTableWatermark(database, table);
        return watermark != null &&
                TableWatermark.Status.COMPLETED.equals(watermark.getStatus());
    }

    public boolean canStartIncremental(String database, String table) {
        TableWatermark watermark = getTableWatermark(database, table);
        return watermark != null &&
                TableWatermark.Status.COMPLETED.equals(watermark.getStatus()) &&
                watermark.getBinlogFileName() != null;
    }
}
