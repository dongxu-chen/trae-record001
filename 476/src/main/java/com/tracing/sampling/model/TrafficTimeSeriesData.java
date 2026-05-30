package com.tracing.sampling.model;

import java.util.LinkedList;
import java.util.Queue;

public class TrafficTimeSeriesData {
    
    private final Queue<TimeWindowData> dataPoints;
    private final int maxDataPoints;
    private long totalRequests;
    private long totalErrors;
    private long totalLatency;

    public TrafficTimeSeriesData(int maxDataPoints) {
        this.maxDataPoints = maxDataPoints;
        this.dataPoints = new LinkedList<>();
        this.totalRequests = 0;
        this.totalErrors = 0;
        this.totalLatency = 0;
    }

    public synchronized void addDataPoint(TimeWindowData data) {
        if (dataPoints.size() >= maxDataPoints) {
            TimeWindowData removed = dataPoints.poll();
            if (removed != null) {
                totalRequests -= removed.requestCount;
                totalErrors -= removed.errorCount;
                totalLatency -= removed.totalLatency;
            }
        }
        dataPoints.add(data);
        totalRequests += data.requestCount;
        totalErrors += data.errorCount;
        totalLatency += data.totalLatency;
    }

    public synchronized double getAverageRequestsPerSecond() {
        if (dataPoints.isEmpty()) {
            return 0.0;
        }
        long totalWindowSeconds = 0;
        for (TimeWindowData data : dataPoints) {
            totalWindowSeconds += data.windowDurationSeconds;
        }
        return totalWindowSeconds > 0 ? (double) totalRequests / totalWindowSeconds : 0.0;
    }

    public synchronized double getErrorRate() {
        return totalRequests > 0 ? (double) totalErrors / totalRequests : 0.0;
    }

    public synchronized long getAverageLatency() {
        return totalRequests > 0 ? totalLatency / totalRequests : 0;
    }

    public synchronized int getDataPointCount() {
        return dataPoints.size();
    }

    public synchronized TimeWindowData getLatestDataPoint() {
        if (dataPoints.isEmpty()) {
            return null;
        }
        return ((LinkedList<TimeWindowData>) dataPoints).getLast();
    }

    public static class TimeWindowData {
        private final long timestamp;
        private final long windowDurationSeconds;
        private final long requestCount;
        private final long errorCount;
        private final long totalLatency;

        public TimeWindowData(long timestamp, long windowDurationSeconds, 
                              long requestCount, long errorCount, long totalLatency) {
            this.timestamp = timestamp;
            this.windowDurationSeconds = windowDurationSeconds;
            this.requestCount = requestCount;
            this.errorCount = errorCount;
            this.totalLatency = totalLatency;
        }

        public long getTimestamp() {
            return timestamp;
        }

        public long getWindowDurationSeconds() {
            return windowDurationSeconds;
        }

        public long getRequestCount() {
            return requestCount;
        }

        public long getErrorCount() {
            return errorCount;
        }

        public long getTotalLatency() {
            return totalLatency;
        }

        public double getRequestsPerSecond() {
            return windowDurationSeconds > 0 ? (double) requestCount / windowDurationSeconds : 0.0;
        }

        public double getErrorRate() {
            return requestCount > 0 ? (double) errorCount / requestCount : 0.0;
        }

        public long getAverageLatency() {
            return requestCount > 0 ? totalLatency / requestCount : 0;
        }
    }
}
