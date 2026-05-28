package com.mqmonitor.common.model;

public class TimeSeriesPoint {
    private long timestamp;
    private double value;

    public TimeSeriesPoint() {}

    public TimeSeriesPoint(long timestamp, double value) {
        this.timestamp = timestamp;
        this.value = value;
    }

    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public double getValue() { return value; }
    public void setValue(double value) { this.value = value; }
}
