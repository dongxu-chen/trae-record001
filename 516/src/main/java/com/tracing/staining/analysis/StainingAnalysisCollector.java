package com.tracing.staining.analysis;

import com.tracing.staining.context.StainingContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

@Slf4j
@Component
public class StainingAnalysisCollector {

    private final Map<String, List<StainingRecord>> recordsByColor = new ConcurrentHashMap<>();

    private final Map<String, List<StainingRecord>> recordsByTraceId = new ConcurrentHashMap<>();

    private final Map<String, List<StainingRecord>> recordsByBizTag = new ConcurrentHashMap<>();

    private final Map<String, List<StainingRecord>> recordsByCrossCloud = new ConcurrentHashMap<>();

    private final Map<String, StainingRecord> inFlightRequests = new ConcurrentHashMap<>();

    private static final int MAX_RECORDS_PER_KEY = 10000;

    public void collectRequest(StainingContext context, String requestUri, String requestMethod) {
        if (context == null || context.getTraceId() == null) {
            return;
        }

        StainingRecord record = StainingRecord.builder()
                .traceId(context.getTraceId())
                .spanId(context.getSpanId())
                .parentSpanId(context.getParentSpanId())
                .stainingColor(context.getStainingColor())
                .userId(context.getUserId())
                .bizType(context.getBizType())
                .bizTag(context.getBizTag())
                .bizTagVersion(context.getBizTagVersion())
                .bizTags(context.getBizTags() != null ? Map.copyOf(context.getBizTags()) : null)
                .requestUri(requestUri)
                .requestMethod(requestMethod)
                .cloudProvider(context.getCloudProvider())
                .cloudRegion(context.getCloudRegion())
                .cloudAZ(context.getCloudAZ())
                .cloudAccountId(context.getCloudAccountId())
                .cloudServiceName(context.getCloudServiceName())
                .originTraceId(context.getOriginTraceId())
                .crossCloudTraceId(context.getCrossCloudTraceId())
                .requestId(context.getRequestId())
                .requestTime(LocalDateTime.now())
                .extraAttributes(context.getExtraAttributes() != null ? Map.copyOf(context.getExtraAttributes()) : null)
                .build();

        inFlightRequests.put(context.getTraceId(), record);
        log.debug("Request collected for analysis: traceId={}, color={}, bizTag={}",
                context.getTraceId(), context.getStainingColor(), context.getBizTag());
    }

    public void collectResponse(String traceId, int httpStatus, String errorMessage) {
        StainingRecord record = inFlightRequests.remove(traceId);
        if (record == null) {
            return;
        }

        record.setResponseTime(LocalDateTime.now());
        record.setHttpStatus(httpStatus);
        record.setErrorMessage(errorMessage);

        if (record.getRequestTime() != null) {
            record.setDurationMs(Duration.between(record.getRequestTime(), record.getResponseTime()).toMillis());
        }

        addToMap(recordsByColor, record.getStainingColor(), record);
        addToMap(recordsByTraceId, record.getTraceId(), record);

        if (record.getBizTag() != null) {
            addToMap(recordsByBizTag, record.getBizTag(), record);
        }

        if (record.getCrossCloudTraceId() != null) {
            addToMap(recordsByCrossCloud, record.getCrossCloudTraceId(), record);
        }

        log.debug("Response collected for analysis: traceId={}, status={}, duration={}ms",
                traceId, httpStatus, record.getDurationMs());
    }

    private void addToMap(Map<String, List<StainingRecord>> map, String key, StainingRecord record) {
        if (key == null) {
            return;
        }
        map.computeIfAbsent(key, k -> new CopyOnWriteArrayList<>());
        List<StainingRecord> list = map.get(key);
        list.add(record);

        while (list.size() > MAX_RECORDS_PER_KEY) {
            list.remove(0);
        }
    }

    public List<StainingRecord> getRecordsByColor(String color) {
        return new ArrayList<>(recordsByColor.getOrDefault(color, Collections.emptyList()));
    }

    public List<StainingRecord> getRecordsByTraceId(String traceId) {
        return new ArrayList<>(recordsByTraceId.getOrDefault(traceId, Collections.emptyList()));
    }

    public List<StainingRecord> getRecordsByBizTag(String bizTag) {
        return new ArrayList<>(recordsByBizTag.getOrDefault(bizTag, Collections.emptyList()));
    }

    public List<StainingRecord> getRecordsByCrossCloudTraceId(String crossCloudTraceId) {
        return new ArrayList<>(recordsByCrossCloud.getOrDefault(crossCloudTraceId, Collections.emptyList()));
    }

    public List<StainingRecord> getAllRecords() {
        return recordsByTraceId.values().stream()
                .flatMap(List::stream)
                .collect(Collectors.toList());
    }

    public Map<String, Long> getCountByColor() {
        return recordsByColor.entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, e -> (long) e.getValue().size()));
    }

    public Map<String, Long> getCountByBizTag() {
        return recordsByBizTag.entrySet().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, e -> (long) e.getValue().size()));
    }

    public Map<String, Long> getCountByCloudRegion() {
        return getAllRecords().stream()
                .filter(r -> r.getCloudRegion() != null)
                .collect(Collectors.groupingBy(StainingRecord::getCloudRegion, Collectors.counting()));
    }

    public List<StainingRecord> getRecordsByUserId(String userId) {
        return getAllRecords().stream()
                .filter(r -> userId.equals(r.getUserId()))
                .collect(Collectors.toList());
    }

    public List<StainingRecord> getRecordsByBizType(String bizType) {
        return getAllRecords().stream()
                .filter(r -> bizType.equals(r.getBizType()))
                .collect(Collectors.toList());
    }

    public long getTotalStainedRequests() {
        return getAllRecords().size();
    }

    public long getCrossCloudRequestCount() {
        return getAllRecords().stream()
                .filter(StainingRecord::isCrossCloud)
                .count();
    }

    public Map<String, Object> getCrossCloudAnalysis() {
        Map<String, Object> analysis = new ConcurrentHashMap<>();
        analysis.put("totalCrossCloudRequests", getCrossCloudRequestCount());
        analysis.put("crossCloudTraceIds", recordsByCrossCloud.keySet());
        analysis.put("uniqueCloudProviders", getAllRecords().stream()
                .map(StainingRecord::getCloudProvider)
                .filter(p -> p != null && !"unknown".equals(p))
                .collect(Collectors.toSet()));
        analysis.put("uniqueCloudRegions", getAllRecords().stream()
                .map(StainingRecord::getCloudRegion)
                .filter(r -> r != null && !"unknown".equals(r))
                .collect(Collectors.toSet()));
        return analysis;
    }

    public void clearAll() {
        recordsByColor.clear();
        recordsByTraceId.clear();
        recordsByBizTag.clear();
        recordsByCrossCloud.clear();
        inFlightRequests.clear();
        log.info("All staining analysis records cleared");
    }
}
