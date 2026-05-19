package com.logplatform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import com.fasterxml.jackson.databind.JsonNode;
import com.logplatform.model.LogEntry;
import com.logplatform.model.TraceAnalysisResult;
import com.logplatform.model.TraceCall;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class TraceAnalysisService {

    private final ElasticsearchClient elasticsearchClient;

    @Value("${trace.max-logs:1000}")
    private int maxLogsPerTrace;

    @Value("${trace.default-time-range-hours:24}")
    private int defaultTimeRangeHours;

    public TraceAnalysisResult analyzeTrace(String traceId) {
        return analyzeTrace(traceId, null, null);
    }

    public TraceAnalysisResult analyzeTrace(String traceId, String startTime, String endTime) {
        try {
            List<LogEntry> logs = fetchLogsByTraceId(traceId, startTime, endTime);
            if (logs.isEmpty()) {
                return null;
            }

            TraceCall callTree = TraceCall.buildTree(traceId, logs);
            return TraceAnalysisResult.analyze(callTree);

        } catch (Exception e) {
            log.error("Failed to analyze trace: {}", traceId, e);
            throw new RuntimeException("Trace分析失败: " + e.getMessage(), e);
        }
    }

    public List<LogEntry> fetchLogsByTraceId(String traceId) throws Exception {
        return fetchLogsByTraceId(traceId, null, null);
    }

    public List<LogEntry> fetchLogsByTraceId(String traceId, String startTime, String endTime) throws Exception {
        if (traceId == null || traceId.trim().isEmpty()) {
            return Collections.emptyList();
        }

        String start = startTime;
        String end = endTime;

        if (start == null) {
            start = Instant.now().minus(defaultTimeRangeHours, java.time.temporal.ChronoUnit.HOURS).toString();
        }
        if (end == null) {
            end = Instant.now().toString();
        }

        SearchRequest request = SearchRequest.of(s -> s
                .index("unified-logs-*")
                .query(q -> q
                        .bool(b -> b
                                .must(m -> m.term(t -> t.field("traceId").value(traceId)))
                                .filter(f -> f
                                        .range(r -> r
                                                .field("@timestamp")
                                                .gte(co.elastic.clients.elasticsearch._types.FieldValue.of(start))
                                                .lte(co.elastic.clients.elasticsearch._types.FieldValue.of(end))))
                        )
                )
                .sort(sort -> sort.field(f -> f
                        .field("@timestamp")
                        .order(co.elastic.clients.elasticsearch._types.SortOrder.Asc)))
                .size(maxLogsPerTrace));

        SearchResponse<JsonNode> response = elasticsearchClient.search(request, JsonNode.class);

        List<LogEntry> logs = new ArrayList<>();
        for (Hit<JsonNode> hit : response.hits().hits()) {
            LogEntry entry = parseLogEntry(hit);
            logs.add(entry);
        }

        return logs;
    }

    private LogEntry parseLogEntry(Hit<JsonNode> hit) {
        LogEntry entry = new LogEntry();
        entry.setId(hit.id());

        if (hit.source() != null) {
            JsonNode source = hit.source();

            entry.setAppName(getText(source, "appName"));
            entry.setLevel(getText(source, "level"));
            entry.setLogger(getText(source, "logger"));
            entry.setThread(getText(source, "thread"));
            entry.setMessage(getText(source, "message"));
            entry.setStackTrace(getText(source, "stackTrace"));
            entry.setHost(getText(source, "host"));
            entry.setIp(getText(source, "ip"));
            entry.setTraceId(getText(source, "traceId"));

            JsonNode timestamp = source.get("@timestamp");
            if (timestamp != null && timestamp.isTextual()) {
                try {
                    entry.setTimestamp(Instant.parse(timestamp.asText()));
                } catch (Exception ignored) {}
            }
        }

        return entry;
    }

    private String getText(JsonNode node, String field) {
        JsonNode fieldNode = node.get(field);
        return fieldNode != null ? fieldNode.asText(null) : null;
    }

    public Map<String, Object> searchTraces(String appName, String level, Long minDurationMs,
                                            String startTime, String endTime, int page, int size) throws Exception {
        String start = startTime != null ? startTime :
                Instant.now().minus(defaultTimeRangeHours, java.time.temporal.ChronoUnit.HOURS).toString();
        String end = endTime != null ? endTime : Instant.now().toString();

        SearchRequest request = SearchRequest.of(s -> s
                .index("unified-logs-*")
                .query(q -> q
                        .bool(b -> {
                            if (appName != null) {
                                b.must(m -> m.term(t -> t.field("appName").value(appName)));
                            }
                            if (level != null) {
                                b.must(m -> m.term(t -> t.field("level").value(level.toUpperCase())));
                            }
                            b.filter(f -> f
                                    .range(r -> r
                                            .field("@timestamp")
                                            .gte(co.elastic.clients.elasticsearch._types.FieldValue.of(start))
                                            .lte(co.elastic.clients.elasticsearch._types.FieldValue.of(end))));
                            b.must(m -> m.exists(e -> e.field("traceId")));
                            return b;
                        })
                )
                .aggregations("traces", a -> a
                        .terms(t -> t
                                .field("traceId")
                                .size(size)
                                .order(List.of(co.elastic.clients.elasticsearch._types.aggregations.TermsAggregationOrder.of(
                                        o -> o._count(co.elastic.clients.elasticsearch._types.SortOrder.Desc))))
                        )
                )
                .from(page * size)
                .size(0));

        SearchResponse<JsonNode> response = elasticsearchClient.search(request, JsonNode.class);

        List<Map<String, Object>> traces = new ArrayList<>();
        var termsAgg = response.aggregations().get("traces").sterms();

        for (var bucket : termsAgg.buckets().array()) {
            Map<String, Object> traceInfo = new HashMap<>();
            traceInfo.put("traceId", bucket.key());
            traceInfo.put("logCount", bucket.docCount());
            traces.add(traceInfo);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("traces", traces);
        result.put("total", termsAgg.sumOtherDocCount() + traces.size());
        result.put("page", page);
        result.put("size", size);

        return result;
    }
}
