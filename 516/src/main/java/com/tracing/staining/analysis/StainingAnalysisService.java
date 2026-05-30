package com.tracing.staining.analysis;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class StainingAnalysisService {

    private final StainingAnalysisCollector collector;

    public Map<String, Object> getStainingOverview() {
        Map<String, Object> overview = new LinkedHashMap<>();

        overview.put("totalStainedRequests", collector.getTotalStainedRequests());
        overview.put("totalCrossCloudRequests", collector.getCrossCloudRequestCount());
        overview.put("countByColor", collector.getCountByColor());
        overview.put("countByBizTag", collector.getCountByBizTag());
        overview.put("countByCloudRegion", collector.getCountByCloudRegion());

        List<StainingRecord> allRecords = collector.getAllRecords();

        long successCount = allRecords.stream()
                .filter(r -> r.getHttpStatus() != null && r.getHttpStatus() >= 200 && r.getHttpStatus() < 400)
                .count();
        long errorCount = allRecords.stream()
                .filter(r -> r.getHttpStatus() != null && r.getHttpStatus() >= 400)
                .count();

        overview.put("successCount", successCount);
        overview.put("errorCount", errorCount);

        double avgDuration = allRecords.stream()
                .filter(r -> r.getDurationMs() != null)
                .mapToLong(StainingRecord::getDurationMs)
                .average()
                .orElse(0.0);

        overview.put("avgDurationMs", Math.round(avgDuration));

        overview.put("timestamp", LocalDateTime.now().toString());

        log.info("Staining overview generated: total={}, crossCloud={}",
                collector.getTotalStainedRequests(),
                collector.getCrossCloudRequestCount());

        return overview;
    }

    public Map<String, Object> getCrossCloudTraceChain(String crossCloudTraceId) {
        Map<String, Object> result = new LinkedHashMap<>();

        List<StainingRecord> records = collector.getRecordsByCrossCloudTraceId(crossCloudTraceId);

        records.sort(Comparator.comparing(StainingRecord::getRequestTime,
                Comparator.nullsLast(Comparator.naturalOrder())));

        result.put("crossCloudTraceId", crossCloudTraceId);
        result.put("totalHops", records.size());
        result.put("records", records);

        Set<String> cloudProviders = records.stream()
                .map(StainingRecord::getCloudProvider)
                .filter(p -> p != null && !"unknown".equals(p))
                .collect(Collectors.toSet());

        Set<String> cloudRegions = records.stream()
                .map(StainingRecord::getCloudRegion)
                .filter(r -> r != null && !"unknown".equals(r))
                .collect(Collectors.toSet());

        result.put("cloudProvidersTraversed", cloudProviders);
        result.put("cloudRegionsTraversed", cloudRegions);

        String originTraceId = records.stream()
                .map(StainingRecord::getOriginTraceId)
                .filter(id -> id != null)
                .findFirst()
                .orElse(null);

        result.put("originTraceId", originTraceId);

        if (!records.isEmpty()) {
            StainingRecord first = records.get(0);
            StainingRecord last = records.get(records.size() - 1);
            if (first.getRequestTime() != null && last.getResponseTime() != null) {
                long totalDuration = java.time.Duration.between(
                        first.getRequestTime(),
                        last.getResponseTime()).toMillis();
                result.put("totalDurationMs", totalDuration);
            }
        }

        List<Map<String, Object>> hops = new ArrayList<>();
        for (int i = 0; i < records.size(); i++) {
            StainingRecord record = records.get(i);
            Map<String, Object> hop = new LinkedHashMap<>();
            hop.put("hop", i + 1);
            hop.put("traceId", record.getTraceId());
            hop.put("service", record.getCloudServiceName());
            hop.put("cloudProvider", record.getCloudProvider());
            hop.put("cloudRegion", record.getCloudRegion());
            hop.put("requestUri", record.getRequestUri());
            hop.put("httpStatus", record.getHttpStatus());
            hop.put("durationMs", record.getDurationMs());
            hops.add(hop);
        }
        result.put("hops", hops);

        log.info("Cross-cloud trace chain analysis: traceId={}, hops={}", crossCloudTraceId, records.size());

        return result;
    }

    public Map<String, Object> getStainingGroupAnalysis(String groupBy) {
        Map<String, Object> result = new LinkedHashMap<>();

        List<StainingRecord> allRecords = collector.getAllRecords();

        Map<String, List<StainingRecord>> groups;

        switch (groupBy.toLowerCase()) {
            case "color":
                groups = allRecords.stream()
                        .collect(Collectors.groupingBy(
                                r -> r.getStainingColor() != null ? r.getStainingColor() : "unknown"));
                break;
            case "biztag":
                groups = allRecords.stream()
                        .collect(Collectors.groupingBy(
                                r -> r.getBizTag() != null ? r.getBizTag() : "unknown"));
                break;
            case "biztype":
                groups = allRecords.stream()
                        .collect(Collectors.groupingBy(
                                r -> r.getBizType() != null ? r.getBizType() : "unknown"));
                break;
            case "user":
                groups = allRecords.stream()
                        .collect(Collectors.groupingBy(
                                r -> r.getUserId() != null ? r.getUserId() : "unknown"));
                break;
            case "cloud":
                groups = allRecords.stream()
                        .collect(Collectors.groupingBy(
                                r -> r.getCloudProvider() != null ? r.getCloudProvider() : "unknown"));
                break;
            default:
                result.put("error", "Invalid groupBy parameter. Use: color, bizTag, bizType, user, cloud");
                return result;
        }

        Map<String, Map<String, Object>> groupStats = new LinkedHashMap<>();

        for (Map.Entry<String, List<StainingRecord>> entry : groups.entrySet()) {
            Map<String, Object> stats = new LinkedHashMap<>();
            List<StainingRecord> groupRecords = entry.getValue();

            stats.put("count", groupRecords.size());

            long successCount = groupRecords.stream()
                    .filter(r -> r.getHttpStatus() != null && r.getHttpStatus() >= 200 && r.getHttpStatus() < 400)
                    .count();
            long errorCount = groupRecords.stream()
                    .filter(r -> r.getHttpStatus() != null && r.getHttpStatus() >= 400)
                    .count();

            stats.put("successCount", successCount);
            stats.put("errorCount", errorCount);
            stats.put("errorRate", groupRecords.isEmpty() ? 0.0 :
                    String.format("%.2f%%", (errorCount * 100.0 / groupRecords.size()));

            double avgDuration = groupRecords.stream()
                    .filter(r -> r.getDurationMs() != null)
                    .mapToLong(StainingRecord::getDurationMs)
                    .average()
                    .orElse(0.0);
            stats.put("avgDurationMs", Math.round(avgDuration));

            long p95Duration = groupRecords.stream()
                    .filter(r -> r.getDurationMs() != null)
                    .mapToLong(StainingRecord::getDurationMs)
                    .sorted()
                    .skip((long) (groupRecords.size() * 0.95))
                    .findFirst()
                    .orElse(0L);
            stats.put("p95DurationMs", p95Duration);

            groupStats.put(entry.getKey(), stats);
        }

        result.put("groupBy", groupBy);
        result.put("totalGroups", groups.size());
        result.put("groups", groupStats);

        return result;
    }

    public Map<String, Object> getBizTagDistribution() {
        Map<String, Object> result = new LinkedHashMap<>();
        List<StainingRecord> allRecords = collector.getAllRecords();

        Map<String, Long> tagCounts = new LinkedHashMap<>();
        Map<String, Long> tagSuccess = new LinkedHashMap<>();
        Map<String, Long> tagErrors = new LinkedHashMap<>();

        for (StainingRecord record : allRecords) {
            String bizTag = record.getBizTag() != null ? record.getBizTag() : "no-tag";
            tagCounts.merge(bizTag, 1L, Long::sum);

            if (record.getHttpStatus() != null) {
                if (record.getHttpStatus() >= 200 && record.getHttpStatus() < 400) {
                    tagSuccess.merge(bizTag, 1L, Long::sum);
                } else {
                    tagErrors.merge(bizTag, 1L, Long::sum);
                }
            }
        }

        result.put("totalUniqueBizTags", tagCounts.size());
        result.put("tagCounts", tagCounts);
        result.put("tagSuccessCounts", tagSuccess);
        result.put("tagErrorCounts", tagErrors);

        Map<String, Double> tagErrorRates = new LinkedHashMap<>();
        for (Map.Entry<String, Long> entry : tagCounts.entrySet()) {
            long errors = tagErrors.getOrDefault(entry.getKey(), 0L);
            tagErrorRates.put(entry.getKey(),
                    entry.getValue() == 0 ? 0.0 :
                    String.format("%.2f%%", errors * 100.0 / entry.getValue()));
        }
        result.put("tagErrorRates", tagErrorRates);

        List<Map<String, Object>> topTags = tagCounts.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue(Comparator.reverseOrder()))
                .limit(10)
                .map(e -> {
                    Map<String, Object> tagInfo = new LinkedHashMap<>();
                    tagInfo.put("bizTag", e.getKey());
                    tagInfo.put("count", e.getValue());
                    tagInfo.put("successCount", tagSuccess.getOrDefault(e.getKey(), 0L));
                    tagInfo.put("errorCount", tagErrors.getOrDefault(e.getKey(), 0L));
                    tagInfo.put("errorRate", tagErrorRates.get(e.getKey()));
                    return tagInfo;
                })
                .collect(Collectors.toList());

        result.put("topBizTags", topTags);

        return result;
    }

    public List<Map<String, Object>> getSlowRequests(int limit) {
        return collector.getAllRecords().stream()
                .filter(r -> r.getDurationMs() != null)
                .sorted(Comparator.comparing(StainingRecord::getDurationMs,
                        Comparator.reverseOrder()))
                .limit(limit)
                .map(r -> {
                    Map<String, Object> info = new LinkedHashMap<>();
                    info.put("traceId", r.getTraceId());
                    info.put("durationMs", r.getDurationMs());
                    info.put("requestUri", r.getRequestUri());
                    info.put("stainingColor", r.getStainingColor());
                    info.put("bizTag", r.getBizTag());
                    info.put("httpStatus", r.getHttpStatus());
                    info.put("cloudRegion", r.getCloudRegion());
                    return info;
                })
                .collect(Collectors.toList());
    }

    public List<Map<String, Object>> getErrorRequests() {
        return collector.getAllRecords().stream()
                .filter(r -> r.getHttpStatus() != null && r.getHttpStatus() >= 400)
                .map(r -> {
                    Map<String, Object> info = new LinkedHashMap<>();
                    info.put("traceId", r.getTraceId());
                    info.put("httpStatus", r.getHttpStatus());
                    info.put("errorMessage", r.getErrorMessage());
                    info.put("requestUri", r.getRequestUri());
                    info.put("stainingColor", r.getStainingColor());
                    info.put("bizTag", r.getBizTag());
                    info.put("durationMs", r.getDurationMs());
                    return info;
                })
                .collect(Collectors.toList());
    }

    public Map<String, Object> getTraceDetails(String traceId) {
        Map<String, Object> result = new LinkedHashMap<>();

        List<StainingRecord> records = collector.getRecordsByTraceId(traceId);

        if (records.isEmpty()) {
            result.put("error", "No records found for traceId: " + traceId);
            return result;
        }

        result.put("traceId", traceId);
        result.put("records", records);

        StainingRecord first = records.get(0);
        result.put("originTraceId", first.getOriginTraceId());
        result.put("crossCloudTraceId", first.getCrossCloudTraceId());

        if (first.getCrossCloudTraceId() != null) {
            result.put("crossCloudChain", getCrossCloudTraceChain(first.getCrossCloudTraceId()));
        }

        return result;
    }

    public void clearAllData() {
        collector.clearAll();
    }
}
