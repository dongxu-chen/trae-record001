package com.sla.monitor.engine;

import lombok.Data;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class CalendarWindowMetrics {

    public enum WindowType {
        CALENDAR_DAY,
        CALENDAR_WEEK,
        CALENDAR_MONTH,
        SLIDING_HOUR,
        SLIDING_DAY
    }

    private final Map<String, CalendarServiceWindow> serviceWindows = new ConcurrentHashMap<>();

    public void recordRequest(String serviceName, long latencyMs, boolean success) {
        serviceWindows.computeIfAbsent(serviceName, k -> new CalendarServiceWindow())
                .recordRequest(latencyMs, success);
    }

    public WindowMetrics getWindowMetrics(String serviceName, WindowType windowType) {
        CalendarServiceWindow window = serviceWindows.get(serviceName);
        return window != null ? window.calculateMetrics(windowType) : new WindowMetrics();
    }

    public Map<WindowType, WindowMetrics> getAllWindowMetrics(String serviceName) {
        CalendarServiceWindow window = serviceWindows.get(serviceName);
        if (window == null) {
            return Collections.emptyMap();
        }
        
        Map<WindowType, WindowMetrics> metrics = new EnumMap<>(WindowType.class);
        for (WindowType type : WindowType.values()) {
            metrics.put(type, window.calculateMetrics(type));
        }
        return metrics;
    }

    public WindowBounds getCurrentWindowBounds(WindowType windowType) {
        return getWindowBounds(windowType, LocalDateTime.now());
    }

    public WindowBounds getWindowBounds(WindowType windowType, LocalDateTime time) {
        LocalDateTime start, end;
        
        switch (windowType) {
            case CALENDAR_DAY:
                start = time.truncatedTo(ChronoUnit.DAYS);
                end = start.plusDays(1);
                break;
            case CALENDAR_WEEK:
                start = time.with(TemporalAdjusters.previousOrSame(java.time.DayOfWeek.MONDAY))
                        .truncatedTo(ChronoUnit.DAYS);
                end = start.plusWeeks(1);
                break;
            case CALENDAR_MONTH:
                start = time.with(TemporalAdjusters.firstDayOfMonth())
                        .truncatedTo(ChronoUnit.DAYS);
                end = start.plusMonths(1);
                break;
            case SLIDING_HOUR:
                end = LocalDateTime.now();
                start = end.minusHours(1);
                break;
            case SLIDING_DAY:
                end = LocalDateTime.now();
                start = end.minusDays(1);
                break;
            default:
                end = LocalDateTime.now();
                start = end.minusHours(1);
        }
        
        return new WindowBounds(start, end, windowType);
    }

    public Set<String> getServiceNames() {
        return serviceWindows.keySet();
    }

    public void cleanupOldData(int retentionDays) {
        LocalDateTime cutoff = LocalDateTime.now().minusDays(retentionDays);
        serviceWindows.values().forEach(window -> window.cleanupOldData(cutoff));
    }

    @Data
    public static class WindowMetrics {
        private long totalRequests = 0;
        private long successfulRequests = 0;
        private long failedRequests = 0;
        private double availability = 100.0;
        private double avgLatencyMs = 0.0;
        private double p50LatencyMs = 0.0;
        private double p95LatencyMs = 0.0;
        private double p99LatencyMs = 0.0;
        private double errorRate = 0.0;
        private LocalDateTime windowStart;
        private LocalDateTime windowEnd;
        private WindowType windowType;
        private long windowDurationMinutes;
        private double windowProgressPercent;
    }

    @Data
    public static class WindowBounds {
        private final LocalDateTime start;
        private final LocalDateTime end;
        private final WindowType type;

        public boolean contains(LocalDateTime time) {
            return !time.isBefore(start) && time.isBefore(end);
        }

        public long getDurationMinutes() {
            return ChronoUnit.MINUTES.between(start, end);
        }

        public double getProgressPercent(LocalDateTime now) {
            if (now.isBefore(start)) return 0.0;
            if (now.isAfter(end)) return 100.0;
            long total = getDurationMinutes();
            long elapsed = ChronoUnit.MINUTES.between(start, now);
            return (elapsed * 100.0) / total;
        }
    }

    private static class CalendarServiceWindow {
        private final List<RequestRecord> records = Collections.synchronizedList(new ArrayList<>());

        void recordRequest(long latencyMs, boolean success) {
            records.add(new RequestRecord(LocalDateTime.now(), latencyMs, success));
        }

        WindowMetrics calculateMetrics(WindowType windowType) {
            WindowBounds bounds = getCurrentWindowBounds(windowType);
            return calculateMetrics(windowType, bounds);
        }

        WindowMetrics calculateMetrics(WindowType windowType, WindowBounds bounds) {
            WindowMetrics metrics = new WindowMetrics();
            metrics.setWindowStart(bounds.getStart());
            metrics.setWindowEnd(bounds.getEnd());
            metrics.setWindowType(windowType);
            metrics.setWindowDurationMinutes(bounds.getDurationMinutes());
            metrics.setWindowProgressPercent(bounds.getProgressPercent(LocalDateTime.now()));

            List<Long> latencies = new ArrayList<>();
            LocalDateTime now = LocalDateTime.now();

            synchronized (records) {
                for (RequestRecord record : records) {
                    if (bounds.contains(record.getTimestamp())) {
                        metrics.setTotalRequests(metrics.getTotalRequests() + 1);
                        if (record.isSuccess()) {
                            metrics.setSuccessfulRequests(metrics.getSuccessfulRequests() + 1);
                        } else {
                            metrics.setFailedRequests(metrics.getFailedRequests() + 1);
                        }
                        latencies.add(record.getLatencyMs());
                    }
                }
            }

            if (metrics.getTotalRequests() > 0) {
                metrics.setAvailability((metrics.getSuccessfulRequests() * 100.0) / metrics.getTotalRequests());
                metrics.setErrorRate((metrics.getFailedRequests() * 100.0) / metrics.getTotalRequests());
                metrics.setAvgLatencyMs(latencies.stream()
                        .mapToLong(Long::longValue)
                        .average()
                        .orElse(0.0));

                Collections.sort(latencies);
                if (!latencies.isEmpty()) {
                    int size = latencies.size();
                    metrics.setP50LatencyMs(latencies.get((int) (size * 0.50)));
                    metrics.setP95LatencyMs(latencies.get(Math.min(size - 1, (int) Math.ceil(size * 0.95) - 1)));
                    metrics.setP99LatencyMs(latencies.get(Math.min(size - 1, (int) Math.ceil(size * 0.99) - 1)));
                }
            }

            return metrics;
        }

        void cleanupOldData(LocalDateTime cutoff) {
            synchronized (records) {
                records.removeIf(record -> record.getTimestamp().isBefore(cutoff));
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
