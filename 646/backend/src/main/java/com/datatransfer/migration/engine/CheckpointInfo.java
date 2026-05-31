package com.datatransfer.migration.engine;

public class CheckpointInfo {
    private String positionType;
    private String positionValue;
    private long processedRecords;

    public CheckpointInfo() {
    }

    public CheckpointInfo(String positionType, String positionValue, long processedRecords) {
        this.positionType = positionType;
        this.positionValue = positionValue;
        this.processedRecords = processedRecords;
    }

    public String getPositionType() { return positionType; }
    public void setPositionType(String positionType) { this.positionType = positionType; }

    public String getPositionValue() { return positionValue; }
    public void setPositionValue(String positionValue) { this.positionValue = positionValue; }

    public long getProcessedRecords() { return processedRecords; }
    public void setProcessedRecords(long processedRecords) { this.processedRecords = processedRecords; }
}
