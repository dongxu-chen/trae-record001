package com.sla.monitor.engine;

import lombok.Data;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

@Component
public class SlidingWindowMetrics {

    private final Map<String, ServiceMetricsWindow> serviceWindows = new ConcurrentHashMap<>();

    public void recordRequest(String serviceName, long latencyMs, boolean success) {
        serviceWindows.computeIfAbsent(serviceName, k -> new ServiceMetricsWindow())
                .recordRequest(latencyMs, success);
    }

    public WindowMetrics getCurrentWindowMetrics(String serviceName) {
        ServiceMetricsWindow window = serviceWindows.get(serviceName);
        return window != null ? window.calculateMetrics() : new WindowMetrics();
    }

    public Set<String> getServiceNames() {
        return serviceWindows.keySet();
    }

    public void cleanupOldData(int windowSizeMinutes) {
        serviceWindows.values().forEach(window -> window.cleanupOldData(windowSizeMinutes));
    }

    @Data
    public static class WindowMetrics {
        private long totalRequests = 0;
        private long successfulRequests = 0;
        private long failedRequests = 0;
        private double availability = 100.0;
        private double avgLatencyMs = 0.0;
        private double p95LatencyMs = 0.0;
        private double p99LatencyMs = 0.0;
        private double errorRate = 0.0;
    }

    private static class ServiceMetricsWindow {
        private final Deque<RequestRecord> records = new ConcurrentLinkedDeque<>();

        void recordRequest(long latencyMs, boolean success) {
            records.addLast(new RequestRecord(LocalDateTime.now(), latencyMs, success));
        }

        WindowMetrics calculateMetrics() {
            WindowMetrics metrics = new WindowMetrics();
            List<Long> latencies = new ArrayList<>();

            for (RequestRecord record : records) {
                metrics.totalRequests++;
                if (record.isSuccess()) {
                    metrics.successfulRequests++;
                } else {
                    metrics.failedRequests++;
                }
                latencies.add(record.getLatencyMs());
            }

            if (metrics.totalRequests > 0) {
                metrics.availability = (metrics.successfulRequests * 100.0) / metrics.totalRequests;
                metrics.errorRate = (metrics.failedRequests * 100.0) / metrics.totalRequests;
                metrics.avgLatencyMs = latencies.stream()
                        .mapToLong(Long::longValue)
                        .average()
                        .orElse(0.0);

                Collections.sort(latencies);
                if (!latencies.isEmpty()) {
                    int p95Index = (int) Math.ceil(0.95 * latencies.size()) - 1;
                    int p99Index = (int) Math.ceil(0.99 * latencies.size()) - 1;
                    metrics.p95LatencyMs = latencies.get(Math.max(0, p95Index));
                    metrics.p99LatencyMs = latencies.get(Math.max(0, p99Index));
                }
            }

            return metrics;
        }

        void cleanupOldData(int windowSizeMinutes) {
            LocalDateTime cutoff = LocalDateTime.now().minusMinutes(windowSizeMinutes);
            while (!records.isEmpty() && records.peekFirst().getTimestamp().isBefore(cutoff)) {
                records.pollFirst();
            }
        }
    }

    @Data
    private static class RequestRecord {
        private final LocalDateTime timestamp;
        private final long latencyMs;
        private final boolean success;
    }
}
