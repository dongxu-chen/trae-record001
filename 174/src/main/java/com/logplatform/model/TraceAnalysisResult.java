package com.logplatform.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Duration;
import java.util.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TraceAnalysisResult {

    private String traceId;

    private long totalDurationMs;

    private int serviceCount;

    private int logCount;

    private int errorCount;

    private int warningCount;

    private String status;

    private TraceCall callTree;

    private List<String> servicePath;

    private Map<String, Long> serviceDurationMap;

    private Map<String, Integer> serviceLogCountMap;

    private List<LogEntry> errorLogs;

    private String bottleneckService;

    public static TraceAnalysisResult analyze(TraceCall callTree) {
        if (callTree == null) return null;

        TraceAnalysisResult result = new TraceAnalysisResult();
        result.setTraceId(callTree.getTraceId());
        result.setCallTree(callTree);

        List<LogEntry> allLogs = new ArrayList<>();
        List<LogEntry> errorLogs = new ArrayList<>();
        Set<String> services = new LinkedHashSet<>();
        Map<String, Long> serviceDuration = new HashMap<>();
        Map<String, Integer> serviceLogCount = new HashMap<>();

        traverseTree(callTree, allLogs, errorLogs, services, serviceDuration, serviceLogCount);

        result.setLogCount(allLogs.size());
        result.setErrorCount((int) errorLogs.stream().filter(l -> "ERROR".equalsIgnoreCase(l.getLevel()) || "FATAL".equalsIgnoreCase(l.getLevel())).count());
        result.setWarningCount((int) errorLogs.stream().filter(l -> "WARN".equalsIgnoreCase(l.getLevel())).count());
        result.setServiceCount(services.size());
        result.setServicePath(new ArrayList<>(services));
        result.setServiceDurationMap(serviceDuration);
        result.setServiceLogCountMap(serviceLogCount);
        result.setErrorLogs(errorLogs);

        if (result.getErrorCount() > 0) {
            result.setStatus("ERROR");
        } else if (result.getWarningCount() > 0) {
            result.setStatus("WARNING");
        } else {
            result.setStatus("SUCCESS");
        }

        if (callTree.getStartTime() != null && callTree.getEndTime() != null) {
            result.setTotalDurationMs(Duration.between(callTree.getStartTime(), callTree.getEndTime()).toMillis());
        }

        String bottleneck = null;
        long maxDuration = 0;
        for (Map.Entry<String, Long> entry : serviceDuration.entrySet()) {
            if (entry.getValue() > maxDuration) {
                maxDuration = entry.getValue();
                bottleneck = entry.getKey();
            }
        }
        result.setBottleneckService(bottleneck);

        return result;
    }

    private static void traverseTree(TraceCall node,
                                     List<LogEntry> allLogs,
                                     List<LogEntry> errorLogs,
                                     Set<String> services,
                                     Map<String, Long> serviceDuration,
                                     Map<String, Integer> serviceLogCount) {
        if (node == null) return;

        if (node.getServiceName() != null && !"ROOT".equals(node.getServiceName())) {
            services.add(node.getServiceName());
        }

        if (node.getLogs() != null) {
            allLogs.addAll(node.getLogs());
            for (LogEntry log : node.getLogs()) {
                if ("ERROR".equalsIgnoreCase(log.getLevel()) ||
                    "WARN".equalsIgnoreCase(log.getLevel()) ||
                    "FATAL".equalsIgnoreCase(log.getLevel())) {
                    errorLogs.add(log);
                }
                if (log.getAppName() != null) {
                    serviceLogCount.merge(log.getAppName(), 1, Integer::sum);
                }
            }
        }

        if (node.getServiceName() != null && node.getDurationMs() > 0 && !"ROOT".equals(node.getServiceName())) {
            serviceDuration.merge(node.getServiceName(), node.getDurationMs(), Long::sum);
        }

        if (node.getChildren() != null) {
            for (TraceCall child : node.getChildren()) {
                traverseTree(child, allLogs, errorLogs, services, serviceDuration, serviceLogCount);
            }
        }
    }
}
