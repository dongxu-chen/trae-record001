package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TraceCall {

    private String traceId;

    private String spanId;

    private String parentSpanId;

    private String serviceName;

    private String operation;

    private Instant startTime;

    private Instant endTime;

    private long durationMs;

    private String status;

    private List<LogEntry> logs;

    private List<TraceCall> children;

    private int depth;

    public void calculateDuration() {
        if (startTime != null && endTime != null) {
            this.durationMs = Duration.between(startTime, endTime).toMillis();
        }
    }

    public static TraceCall fromLogEntry(LogEntry entry) {
        return TraceCall.builder()
                .traceId(entry.getTraceId())
                .serviceName(entry.getAppName())
                .operation(entry.getLogger() != null ? entry.getLogger() : "unknown")
                .startTime(entry.getTimestamp())
                .status(entry.getLevel())
                .logs(new ArrayList<>(List.of(entry)))
                .children(new ArrayList<>())
                .build();
    }

    public static List<TraceCall> buildCallTree(List<LogEntry> logs) {
        if (logs == null || logs.isEmpty()) return new ArrayList<>();

        logs.sort(Comparator.comparing(LogEntry::getTimestamp));

        List<TraceCall> allCalls = new ArrayList<>();
        java.util.Map<String, TraceCall> callMap = new java.util.HashMap<>();

        for (LogEntry log : logs) {
            TraceCall call = fromLogEntry(log);
            allCalls.add(call);

            if (log.getTraceId() != null) {
                callMap.put(log.getTraceId() + "_" + log.getId(), call);
            }
        }

        return allCalls;
    }

    public static TraceCall buildTree(String traceId, List<LogEntry> logs) {
        if (logs == null || logs.isEmpty()) return null;

        logs.sort(Comparator.comparing(LogEntry::getTimestamp,
                Comparator.nullsFirst(Comparator.naturalOrder())));

        TraceCall root = TraceCall.builder()
                .traceId(traceId)
                .serviceName("ROOT")
                .operation("Trace Root")
                .children(new ArrayList<>())
                .logs(new ArrayList<>())
                .depth(0)
                .build();

        java.util.Map<String, TraceCall> serviceCalls = new java.util.LinkedHashMap<>();

        for (LogEntry log : logs) {
            String serviceName = log.getAppName() != null ? log.getAppName() : "unknown";

            TraceCall serviceCall = serviceCalls.computeIfAbsent(serviceName, name ->
                    TraceCall.builder()
                            .traceId(traceId)
                            .serviceName(name)
                            .logs(new ArrayList<>())
                            .children(new ArrayList<>())
                            .depth(1)
                            .build());

            serviceCall.getLogs().add(log);

            if (serviceCall.getStartTime() == null ||
                (log.getTimestamp() != null && log.getTimestamp().isBefore(serviceCall.getStartTime()))) {
                serviceCall.setStartTime(log.getTimestamp());
            }

            if (serviceCall.getEndTime() == null ||
                (log.getTimestamp() != null && log.getTimestamp().isAfter(serviceCall.getEndTime()))) {
                serviceCall.setEndTime(log.getTimestamp());
            }

            if ("ERROR".equalsIgnoreCase(log.getLevel()) || "FATAL".equalsIgnoreCase(log.getLevel())) {
                serviceCall.setStatus("ERROR");
            } else if (serviceCall.getStatus() == null) {
                serviceCall.setStatus(log.getLevel());
            }
        }

        root.getChildren().addAll(serviceCalls.values());
        root.calculateDuration();

        for (TraceCall child : root.getChildren()) {
            child.calculateDuration();
        }

        if (root.getChildren().size() > 0) {
            root.setStartTime(root.getChildren().get(0).getStartTime());
            root.setEndTime(root.getChildren().get(root.getChildren().size() - 1).getEndTime());
            root.calculateDuration();
        }

        return root;
    }
}
