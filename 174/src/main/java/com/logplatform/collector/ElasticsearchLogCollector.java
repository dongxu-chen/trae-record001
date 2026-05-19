package com.logplatform.collector;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logplatform.config.LogCollectorProperties;
import com.logplatform.model.LogEntry;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "log.collector.elasticsearch", name = "enabled", havingValue = "true")
public class ElasticsearchLogCollector implements LogCollector {

    private final LogCollectorProperties properties;
    private final ElasticsearchClient elasticsearchClient;
    private final ObjectMapper objectMapper;
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final Map<String, String> lastTimestamps = new ConcurrentHashMap<>();
    private volatile boolean running = false;
    private LogHandler logHandler;

    @Override
    public String getName() {
        return "ElasticsearchLogCollector";
    }

    @PostConstruct
    @Override
    public void start() {
        if (running) return;
        running = true;

        scheduler.scheduleAtFixedRate(this::collectFromElasticsearch, 0, 30, TimeUnit.SECONDS);

        log.info("ElasticsearchLogCollector started");
    }

    @PreDestroy
    @Override
    public void stop() {
        running = false;
        scheduler.shutdown();
        log.info("ElasticsearchLogCollector stopped");
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    private void collectFromElasticsearch() {
        for (LogCollectorProperties.ElasticsearchIndex index : properties.getElasticsearch().getIndices()) {
            try {
                collectFromIndex(index);
            } catch (Exception e) {
                log.error("Error collecting from Elasticsearch index: {}", index.getName(), e);
            }
        }
    }

    private void collectFromIndex(LogCollectorProperties.ElasticsearchIndex index) throws Exception {
        String lastTimestamp = lastTimestamps.getOrDefault(index.getName(), "now-1h");

        SearchRequest request = SearchRequest.of(s -> s
                .index(index.getName())
                .query(q -> q
                        .range(r -> r
                                .field("@timestamp")
                                .gt(co.elastic.clients.elasticsearch._types.FieldValue.of(lastTimestamp))))
                .sort(sort -> sort.field(f -> f.field("@timestamp").order(co.elastic.clients.elasticsearch._types.SortOrder.Asc)))
                .size(1000));

        SearchResponse<JsonNode> response = elasticsearchClient.search(request, JsonNode.class);

        String newLastTimestamp = lastTimestamp;
        for (Hit<JsonNode> hit : response.hits().hits()) {
            LogEntry entry = convertToLogEntry(hit.source(), index);
            if (entry != null) {
                if (logHandler != null) {
                    logHandler.onLog(entry);
                }
                if (entry.getTimestamp() != null) {
                    newLastTimestamp = entry.getTimestamp().toString();
                }
            }
        }

        if (!newLastTimestamp.equals(lastTimestamp)) {
            lastTimestamps.put(index.getName(), newLastTimestamp);
        }
    }

    private LogEntry convertToLogEntry(JsonNode source, LogCollectorProperties.ElasticsearchIndex index) {
        if (source == null) return null;

        LogEntry entry = new LogEntry();

        if (source.has("@timestamp")) {
            try {
                entry.setTimestamp(Instant.parse(source.get("@timestamp").asText()));
            } catch (Exception e) {
                entry.setTimestamp(Instant.now());
            }
        }

        entry.setAppName(source.has("appName") ? source.get("appName").asText() : index.getAlias());
        entry.setLevel(source.has("level") ? source.get("level").asText() : null);
        entry.setLogger(source.has("logger") ? source.get("logger").asText() : null);
        entry.setThread(source.has("thread") ? source.get("thread").asText() : null);
        entry.setMessage(source.has("message") ? source.get("message").asText() : source.toString());
        entry.setStackTrace(source.has("stackTrace") ? source.get("stackTrace").asText() : null);
        entry.setHost(source.has("host") ? source.get("host").asText() : null);
        entry.setIp(source.has("ip") ? source.get("ip").asText() : null);
        entry.setTraceId(source.has("traceId") ? source.get("traceId").asText() : null);

        return entry;
    }

    @Override
    public void collect(List<LogEntry> logs) {
    }

    public void setLogHandler(LogHandler handler) {
        this.logHandler = handler;
    }
}
