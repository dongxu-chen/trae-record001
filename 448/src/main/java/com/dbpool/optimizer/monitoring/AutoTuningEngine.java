package com.dbpool.optimizer.monitoring;

import com.dbpool.optimizer.model.*;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
public class AutoTuningEngine {

    private final PoolMonitorService monitorService;
    private volatile AutoTuningPolicy policy = AutoTuningPolicy.defaultPolicy();
    private volatile long lastTuningTime = 0;

    public AutoTuningEngine(PoolMonitorService monitorService) {
        this.monitorService = monitorService;
    }

    public AutoTuningDecision evaluate() {
        if (!policy.isEnabled()) return null;

        long now = System.currentTimeMillis();
        if (now - lastTuningTime < policy.getCooldownSeconds() * 1000) return null;

        List<PoolMonitorSnapshot> snapshots = monitorService.getRecentSnapshots(policy.getObservationWindowSeconds());
        if (snapshots.size() < 5) return null;

        double avgUtilization = snapshots.stream()
                .mapToDouble(PoolMonitorSnapshot::getUtilization).average().orElse(0.5);
        double maxUtilization = snapshots.stream()
                .mapToDouble(PoolMonitorSnapshot::getUtilization).max().orElse(0.5);
        double avgWaitTime = snapshots.stream()
                .mapToDouble(PoolMonitorSnapshot::getAvgWaitTimeMs).average().orElse(0);
        double maxWaitTime = snapshots.stream()
                .mapToDouble(PoolMonitorSnapshot::getAvgWaitTimeMs).max().orElse(0);
        int avgWaiting = (int) snapshots.stream()
                .mapToInt(PoolMonitorSnapshot::getWaitingThreads).average().orElse(0);
        int maxWaiting = snapshots.stream()
                .mapToInt(PoolMonitorSnapshot::getWaitingThreads).max().orElse(0);
        int totalTimeouts = snapshots.stream()
                .mapToInt(PoolMonitorSnapshot::getConnectionTimeouts).sum();

        int currentPoolSize = monitorService.getDynamicMaxPoolSize();

        if (shouldScaleUp(avgUtilization, maxUtilization, avgWaitTime, avgWaiting, totalTimeouts)) {
            return createScaleUpDecision(currentPoolSize, avgUtilization, maxWaitTime);
        }

        if (shouldScaleDown(avgUtilization, avgWaiting, totalTimeouts)) {
            return createScaleDownDecision(currentPoolSize, avgUtilization);
        }

        if (shouldAdjustMinIdle(avgWaiting, avgUtilization)) {
            return createMinIdleDecision(avgWaiting);
        }

        return null;
    }

    private boolean shouldScaleUp(double avgUtil, double maxUtil, double avgWait,
                                   int avgWaiting, int totalTimeouts) {
        if (avgUtil >= policy.getScaleUpUtilizationThreshold()) return true;
        if (avgWait >= policy.getScaleUpWaitTimeThresholdMs()) return true;
        if (totalTimeouts > 0 && avgUtil > 0.7) return true;
        if (avgWaiting > 3 && maxUtil > 0.8) return true;
        return false;
    }

    private boolean shouldScaleDown(double avgUtil, int avgWaiting, int totalTimeouts) {
        if (avgUtil > policy.getScaleDownUtilizationThreshold()) return false;
        if (avgWaiting > 0) return false;
        if (totalTimeouts > 0) return false;
        return monitorService.getDynamicMaxPoolSize() > policy.getMinPoolSize() + policy.getScaleStepSize();
    }

    private boolean shouldAdjustMinIdle(int avgWaiting, double avgUtil) {
        int currentMinIdle = monitorService.getDynamicMinIdle();
        if (avgWaiting > 2 && avgUtil > 0.6 && currentMinIdle < monitorService.getDynamicMaxPoolSize() / 3) {
            return true;
        }
        if (avgWaiting == 0 && avgUtil < 0.3 && currentMinIdle > 2) {
            return true;
        }
        return false;
    }

    private AutoTuningDecision createScaleUpDecision(int currentSize, double avgUtil, double maxWait) {
        int step = policy.getScaleStepSize();
        if (avgUtil > 0.95) step *= 2;
        int newSize = Math.min(currentSize + step, policy.getMaxPoolSize());

        String reason = String.format("平均利用率 %.1f%% 超过阈值 %.0f%%，最大等待时间 %.1fms",
                avgUtil * 100, policy.getScaleUpUtilizationThreshold() * 100, maxWait);

        double confidence = calculateConfidence(avgUtil, true);

        AutoTuningDecision decision = AutoTuningDecision.builder()
                .timestamp(System.currentTimeMillis())
                .action("SCALE_UP")
                .parameter("maxPoolSize")
                .oldValue(currentSize)
                .newValue(newSize)
                .reason(reason)
                .confidence(confidence)
                .triggerMetric(avgUtil)
                .triggerMetricName("utilization")
                .applied(false)
                .build();

        lastTuningTime = System.currentTimeMillis();
        return decision;
    }

    private AutoTuningDecision createScaleDownDecision(int currentSize, double avgUtil) {
        int step = policy.getScaleStepSize();
        int newSize = Math.max(currentSize - step, policy.getMinPoolSize());

        String reason = String.format("平均利用率 %.1f%% 低于缩容阈值 %.0f%%，可释放多余连接",
                avgUtil * 100, policy.getScaleDownUtilizationThreshold() * 100);

        double confidence = calculateConfidence(1 - avgUtil, false);

        AutoTuningDecision decision = AutoTuningDecision.builder()
                .timestamp(System.currentTimeMillis())
                .action("SCALE_DOWN")
                .parameter("maxPoolSize")
                .oldValue(currentSize)
                .newValue(newSize)
                .reason(reason)
                .confidence(confidence)
                .triggerMetric(avgUtil)
                .triggerMetricName("utilization")
                .applied(false)
                .build();

        lastTuningTime = System.currentTimeMillis();
        return decision;
    }

    private AutoTuningDecision createMinIdleDecision(int avgWaiting) {
        int currentMinIdle = monitorService.getDynamicMinIdle();
        int newMinIdle;

        if (avgWaiting > 2) {
            newMinIdle = Math.min(currentMinIdle + 1, monitorService.getDynamicMaxPoolSize() / 2);
        } else {
            newMinIdle = Math.max(currentMinIdle - 1, 2);
        }

        String reason = avgWaiting > 2
                ? String.format("平均等待线程 %d > 2，增加最小空闲连接以减少冷启动", avgWaiting)
                : "无等待线程，减少最小空闲连接节省资源";

        AutoTuningDecision decision = AutoTuningDecision.builder()
                .timestamp(System.currentTimeMillis())
                .action("ADJUST_MIN_IDLE")
                .parameter("minIdle")
                .oldValue(currentMinIdle)
                .newValue(newMinIdle)
                .reason(reason)
                .confidence(0.7)
                .triggerMetric(avgWaiting)
                .triggerMetricName("waitingThreads")
                .applied(false)
                .build();

        lastTuningTime = System.currentTimeMillis();
        return decision;
    }

    private double calculateConfidence(double metric, boolean isScaleUp) {
        double base = 0.6;
        if (metric > 0.9) base += 0.25;
        else if (metric > 0.8) base += 0.15;
        else if (metric > 0.7) base += 0.05;
        return Math.min(0.95, base);
    }

    public AutoTuningPolicy getPolicy() {
        return policy;
    }

    public void updatePolicy(AutoTuningPolicy newPolicy) {
        this.policy = newPolicy;
    }
}
