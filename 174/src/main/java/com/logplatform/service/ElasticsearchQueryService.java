package com.logplatform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.*;
import co.elastic.clients.elasticsearch._types.query_dsl.*;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.core.search.HitsMetadata;
import co.elastic.clients.elasticsearch.core.search.Highlight;
import co.elastic.clients.elasticsearch.core.search.HighlightField;
import co.elastic.clients.json.JsonData;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logplatform.model.LogEntry;
import com.logplatform.model.LogQueryRequest;
import com.logplatform.model.LogQueryResult;
import com.logplatform.parser.QueryParserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class ElasticsearchQueryService {

    private final ElasticsearchClient elasticsearchClient;
    private final QueryParserService queryParserService;
    private final ObjectMapper objectMapper;

    @Value("${query.highlight-fragment-size:150}")
    private int fragmentSize;

    @Value("${query.highlight-number-of-fragments:3}")
    private int numberOfFragments;

    @Value("${query.highlight-pre-tag:<mark>}")
    private String preTag;

    @Value("${query.highlight-post-tag:</mark>}")
    private String postTag;

    public LogQueryResult search(LogQueryRequest request) {
        long startTime = System.currentTimeMillis();

        try {
            SearchRequest searchRequest = buildSearchRequest(request);
            SearchResponse<JsonNode> response = elasticsearchClient.search(searchRequest, JsonNode.class);

            List<LogEntry> logs = parseResponse(response);
            long total = response.hits().total() != null ? response.hits().total().value() : 0;
            long took = response.took() != null ? response.took() : 0;

            return LogQueryResult.builder()
                    .total(total)
                    .page(request.getPage())
                    .size(request.getSize())
                    .tookMs(System.currentTimeMillis() - startTime)
                    .logs(logs)
                    .build();

        } catch (Exception e) {
            log.error("Elasticsearch search failed", e);
            throw new RuntimeException("搜索失败: " + e.getMessage(), e);
        }
    }

    private SearchRequest buildSearchRequest(LogQueryRequest request) {
        BoolQuery.Builder boolQuery = QueryBuilders.bool();

        if (request.getQuery() != null && !request.getQuery().trim().isEmpty()) {
            Query parsedQuery = queryParserService.parseQuery(request.getQuery());
            if (parsedQuery != null) {
                boolQuery.must(parsedQuery);
            }
        }

        if (request.getAppName() != null && !request.getAppName().isEmpty()) {
            boolQuery.filter(f -> f.term(t -> t.field("appName").value(request.getAppName())));
        }

        if (request.getLevel() != null && !request.getLevel().isEmpty()) {
            boolQuery.filter(f -> f.term(t -> t.field("level").value(request.getLevel().toUpperCase())));
        }

        if (request.getStartTime() != null || request.getEndTime() != null) {
            RangeQuery.Builder rangeQuery = QueryBuilders.range().field("@timestamp");
            if (request.getStartTime() != null) {
                rangeQuery.gte(FieldValue.of(request.getStartTime()));
            }
            if (request.getEndTime() != null) {
                rangeQuery.lte(FieldValue.of(request.getEndTime()));
            }
            boolQuery.filter(f -> f.range(rangeQuery.build()));
        }

        SearchRequest.Builder builder = new SearchRequest.Builder()
                .index("unified-logs-*")
                .query(q -> q.bool(boolQuery.build()))
                .from(request.getPage() * request.getSize())
                .size(request.getSize())
                .sort(s -> s.field(f -> f
                        .field(request.getSortField() != null ? request.getSortField() : "@timestamp")
                        .order(SortOrder.valueOf(
                                request.getSortOrder() != null && request.getSortOrder().equalsIgnoreCase("asc")
                                        ? "Asc" : "Desc"))));

        if (request.isHighlight()) {
            builder.highlight(buildHighlight());
        }

        return builder.build();
    }

    private Highlight buildHighlight() {
        return Highlight.of(h -> h
                .preTags(preTag)
                .postTags(postTag)
                .fragmentSize(fragmentSize)
                .numberOfFragments(numberOfFragments)
                .fields("*", HighlightField.of(f -> f))
                .requireFieldMatch(false));
    }

    private List<LogEntry> parseResponse(SearchResponse<JsonNode> response) {
        List<LogEntry> logs = new ArrayList<>();

        for (Hit<JsonNode> hit : response.hits().hits()) {
            LogEntry entry = new LogEntry();
            entry.setId(hit.id());

            if (hit.source() != null) {
                JsonNode source = hit.source();

                entry.setTimestamp(parseTimestamp(source));
                entry.setAppName(getTextValue(source, "appName"));
                entry.setLevel(getTextValue(source, "level"));
                entry.setLogger(getTextValue(source, "logger"));
                entry.setThread(getTextValue(source, "thread"));
                entry.setMessage(getTextValue(source, "message"));
                entry.setStackTrace(getTextValue(source, "stackTrace"));
                entry.setHost(getTextValue(source, "host"));
                entry.setIp(getTextValue(source, "ip"));
                entry.setTraceId(getTextValue(source, "traceId"));

                entry.setExtra(objectMapper.convertValue(source, new TypeReference<Map<String, Object>>() {}));
            }

            if (hit.highlight() != null && !hit.highlight().isEmpty()) {
                Map<String, Object> highlight = new HashMap<>();
                hit.highlight().forEach((key, value) -> highlight.put(key, value));
                entry.setHighlight(highlight);
            }

            logs.add(entry);
        }

        return logs;
    }

    private Instant parseTimestamp(JsonNode source) {
        JsonNode timestampNode = source.get("@timestamp");
        if (timestampNode != null && timestampNode.isTextual()) {
            try {
                return Instant.parse(timestampNode.asText());
            } catch (Exception e) {
                log.warn("Failed to parse timestamp: {}", timestampNode.asText());
            }
        }
        return null;
    }

    private String getTextValue(JsonNode node, String field) {
        JsonNode fieldNode = node.get(field);
        return fieldNode != null ? fieldNode.asText(null) : null;
    }

    public long count(LogQueryRequest request) {
        try {
            SearchRequest searchRequest = buildSearchRequest(request);
            SearchResponse<JsonNode> response = elasticsearchClient.search(
                    searchRequest, JsonNode.class);
            return response.hits().total() != null ? response.hits().total().value() : 0;
        } catch (Exception e) {
            log.error("Elasticsearch count failed", e);
            throw new RuntimeException("统计失败: " + e.getMessage(), e);
        }
    }
}
