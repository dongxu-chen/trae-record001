package com.datasync.monitor;

import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.SyncResult;
import com.datasync.monitor.model.SyncMetrics;
import lombok.Builder;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
public class SyncMonitorService {
    @Getter
    private final String datacenterId;
    @Getter
    private final String nodeId;

    private final SyncMetrics overallMetrics;
    private final Map<String, SyncMetrics> tableMetrics = new ConcurrentHashMap<>();
    private final Map<String, SyncMetrics> sourceMetrics = new ConcurrentHashMap<>();

    private final long latencyAlertThresholdMs;
    private final long errorRateAlertThreshold;
    private ScheduledExecutorService scheduler;

    @Builder
    public SyncMonitorService(String datacenterId,
                              String nodeId,
                              long latencyAlertThresholdMs,
                              long errorRateAlertThreshold,
                              long metricsReportIntervalMs) {
        this.datacenterId = datacenterId;
        this.nodeId = nodeId;
        this.latencyAlertThresholdMs = latencyAlertThresholdMs > 0 ? latencyAlertThresholdMs : 5000;
        this.errorRateAlertThreshold = errorRateAlertThreshold > 0 ? errorRateAlertThreshold : 5;

        this.overallMetrics = SyncMetrics.builder()
                .datacenterId(datacenterId)
                .nodeId(nodeId)
                .status("RUNNING")
                .build();

        if (metricsReportIntervalMs > 0) {
            startMetricsReporter(metricsReportIntervalMs);
        }
    }

    public void recordSync(DataChangeEvent event, SyncResult result) {
        long latency = System.currentTimeMillis() - event.getSyncTimestamp();
        String operationType = event.getOperationType() != null ? event.getOperationType().getName() : "UNKNOWN";

        overallMetrics.recordSync(result.isSuccess(), latency, operationType);

        String tableKey = event.getFullTableName();
        tableMetrics.computeIfAbsent(tableKey, k -> createMetrics()).recordSync(result.isSuccess(), latency, operationType);

        String sourceKey = event.getSourceDatacenterId() + "_" + event.getSourceDatabaseId();
        sourceMetrics.computeIfAbsent(sourceKey, k -> createMetrics()).recordSync(result.isSuccess(), latency, operationType);

        checkAlerts(event, result, latency);
    }

    public void recordConflict(DataChangeEvent event, ConflictResult conflictResult) {
        overallMetrics.recordConflict();

        String tableKey = event.getFullTableName();
        tableMetrics.computeIfAbsent(tableKey, k -> createMetrics()).recordConflict();
    }

    private SyncMetrics createMetrics() {
        return SyncMetrics.builder()
                .datacenterId(datacenterId)
                .nodeId(nodeId)
                .status("RUNNING")
                .build();
    }

    private void checkAlerts(DataChangeEvent event, SyncResult result, long latency) {
        if (latency > latencyAlertThresholdMs) {
            log.warn("High latency alert: eventId={}, latency={}ms, threshold={}ms",
                    event.getEventId(), latency, latencyAlertThresholdMs);
        }

        long totalCount = overallMetrics.getTotalSyncCount().sum();
        if (totalCount > 100) {
            long errorCount = overallMetrics.getFailureCount().sum();
            double errorRate = (double) errorCount / totalCount * 100;
            if (errorRate > errorRateAlertThreshold) {
                log.warn("High error rate alert: errorRate={}%, threshold={}%",
                        String.format("%.2f", errorRate), errorRateAlertThreshold);
            }
        }
    }

    private void startMetricsReporter(long intervalMs) {
        scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "metrics-reporter");
            t.setDaemon(true);
            return t;
        });

        scheduler.scheduleAtFixedRate(this::reportMetrics, intervalMs, intervalMs, TimeUnit.MILLISECONDS);
    }

    public void reportMetrics() {
        long totalCount = overallMetrics.getTotalSyncCount().sum();
        long successCount = overallMetrics.getSuccessCount().sum();
        long failureCount = overallMetrics.getFailureCount().sum();
        long conflictCount = overallMetrics.getConflictCount().sum();
        long avgLatency = overallMetrics.getAvgLatencyMs().get();
        long maxLatency = overallMetrics.getMaxLatencyMs().get();
        long runningTime = System.currentTimeMillis() - overallMetrics.getStartTime().get();

        log.info("Sync Metrics Report - datacenterId={}, nodeId={}", datacenterId, nodeId);
        log.info("  Running Time: {}s", runningTime / 1000);
        log.info("  Total: {}, Success: {}, Failure: {}, Conflict: {}",
                totalCount, successCount, failureCount, conflictCount);
        log.info("  Avg Latency: {}ms, Max Latency: {}ms", avgLatency, maxLatency);
        log.info("  Insert: {}, Update: {}, Delete: {}",
                overallMetrics.getInsertCount().sum(),
                overallMetrics.getUpdateCount().sum(),
                overallMetrics.getDeleteCount().sum());
    }

    public SyncMetrics getOverallMetrics() {
        return overallMetrics;
    }

    public Map<String, SyncMetrics> getTableMetrics() {
        return new ConcurrentHashMap<>(tableMetrics);
    }

    public Map<String, SyncMetrics> getSourceMetrics() {
        return new ConcurrentHashMap<>(sourceMetrics);
    }

    public long getCurrentAvgLatency() {
        return overallMetrics.getAvgLatencyMs().get();
    }

    public long getCurrentMaxLatency() {
        return overallMetrics.getMaxLatencyMs().get();
    }

    public double getSuccessRate() {
        long total = overallMetrics.getTotalSyncCount().sum();
        if (total == 0) {
            return 100.0;
        }
        return (double) overallMetrics.getSuccessCount().sum() / total * 100;
    }

    public void shutdown() {
        if (scheduler != null) {
            scheduler.shutdown();
        }
        overallMetrics.setStatus("STOPPED");
    }
}
