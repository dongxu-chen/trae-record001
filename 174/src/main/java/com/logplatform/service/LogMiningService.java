package com.logplatform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import com.fasterxml.jackson.databind.JsonNode;
import com.logplatform.model.LogCluster;
import com.logplatform.model.LogEntry;
import com.logplatform.model.LogTemplate;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class LogMiningService {

    private final ElasticsearchClient elasticsearchClient;

    @Value("${mining.similarity-threshold:0.75}")
    private double similarityThreshold;

    @Value("${mining.analysis-window-hours:1}")
    private int analysisWindowHours;

    @Value("${mining.max-clusters:100}")
    private int maxClusters;

    @Value("${mining.max-templates:50}")
    private int maxTemplates;

    private final Map<String, LogTemplate> templates = new ConcurrentHashMap<>();
    private final List<LogCluster> clusters = Collections.synchronizedList(new ArrayList<>());
    private volatile long lastAnalysisTime = 0;

    @Scheduled(fixedDelayString = "${mining.interval-minutes:5}000")
    public void runAnalysis() {
        log.info("Starting log mining analysis...");
        try {
            List<LogEntry> recentLogs = fetchRecentLogs();
            if (!recentLogs.isEmpty()) {
                analyzeLogPatterns(recentLogs);
                updateTemplates(recentLogs);
                lastAnalysisTime = System.currentTimeMillis();
                log.info("Log mining completed: {} templates, {} clusters", templates.size(), clusters.size());
            }
        } catch (Exception e) {
            log.error("Log mining failed", e);
        }
    }

    private List<LogEntry> fetchRecentLogs() throws Exception {
        String startTime = Instant.now().minus(analysisWindowHours, ChronoUnit.HOURS).toString();

        SearchRequest request = SearchRequest.of(s -> s
                .index("unified-logs-*")
                .query(q -> q
                        .range(r -> r
                                .field("@timestamp")
                                .gte(co.elastic.clients.elasticsearch._types.FieldValue.of(startTime))))
                .sort(sort -> sort.field(f -> f
                        .field("@timestamp")
                        .order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)))
                .size(5000));

        SearchResponse<JsonNode> response = elasticsearchClient.search(request, JsonNode.class);

        List<LogEntry> logs = new ArrayList<>();
        for (Hit<JsonNode> hit : response.hits().hits()) {
            LogEntry entry = new LogEntry();
            entry.setId(hit.id());
            if (hit.source() != null) {
                JsonNode source = hit.source();
                entry.setMessage(source.has("message") ? source.get("message").asText() : "");
                entry.setAppName(source.has("appName") ? source.get("appName").asText() : "");
                entry.setLevel(source.has("level") ? source.get("level").asText() : "");
                if (source.has("@timestamp")) {
                    try {
                        entry.setTimestamp(Instant.parse(source.get("@timestamp").asText()));
                    } catch (Exception ignored) {}
                }
            }
            logs.add(entry);
        }
        return logs;
    }

    public void analyzeLogPatterns(List<LogEntry> logs) {
        List<LogCluster> newClusters = new ArrayList<>();

        for (LogEntry logEntry : logs) {
            String message = logEntry.getMessage();
            if (message == null || message.trim().isEmpty()) continue;

            boolean clustered = false;
            for (LogCluster cluster : newClusters) {
                if (cluster.addLogIfSimilar(logEntry, similarityThreshold)) {
                    clustered = true;
                    break;
                }
            }

            if (!clustered && newClusters.size() < maxClusters) {
                newClusters.add(LogCluster.create(logEntry));
            }
        }

        newClusters.sort((c1, c2) -> Integer.compare(c2.getSize(), c1.getSize()));

        synchronized (clusters) {
            clusters.clear();
            clusters.addAll(newClusters);
        }
    }

    public void updateTemplates(List<LogEntry> logs) {
        for (LogEntry logEntry : logs) {
            String message = logEntry.getMessage();
            if (message == null || message.trim().isEmpty()) continue;

            boolean matched = false;
            for (LogTemplate template : templates.values()) {
                if (template.matches(message)) {
                    template.incrementCount();
                    template.addSample(message);
                    if (logEntry.getAppName() != null && !template.getAffectedServices().contains(logEntry.getAppName())) {
                        template.getAffectedServices().add(logEntry.getAppName());
                    }
                    matched = true;
                    break;
                }
            }

            if (!matched && templates.size() < maxTemplates) {
                LogTemplate newTemplate = LogTemplate.createFromMessage(message);
                if (logEntry.getAppName() != null) {
                    newTemplate.getAffectedServices().add(logEntry.getAppName());
                }
                templates.put(newTemplate.getTemplateId(), newTemplate);
            }
        }
    }

    public List<LogTemplate> getTopTemplates(int limit) {
        return templates.values().stream()
                .sorted((t1, t2) -> Long.compare(t2.getOccurrenceCount(), t1.getOccurrenceCount()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<LogCluster> getTopClusters(int limit) {
        synchronized (clusters) {
            return clusters.stream()
                    .sorted((c1, c2) -> Integer.compare(c2.getSize(), c1.getSize()))
                    .limit(limit)
                    .collect(Collectors.toList());
        }
    }

    public List<LogTemplate> getTemplatesByCategory(String category) {
        return templates.values().stream()
                .filter(t -> category.equalsIgnoreCase(t.getCategory()))
                .collect(Collectors.toList());
    }

    public Map<String, Object> getMiningStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("templateCount", templates.size());
        stats.put("clusterCount", clusters.size());
        stats.put("lastAnalysisTime", lastAnalysisTime);

        Map<String, Long> categoryCounts = new HashMap<>();
        for (LogTemplate template : templates.values()) {
            String category = template.getCategory() != null ? template.getCategory() : "OTHER";
            categoryCounts.merge(category, template.getOccurrenceCount(), Long::sum);
        }
        stats.put("categoryDistribution", categoryCounts);

        long totalOccurrences = templates.values().stream()
                .mapToLong(LogTemplate::getOccurrenceCount)
                .sum();
        stats.put("totalOccurrences", totalOccurrences);

        return stats;
    }

    public void processRealtimeLog(LogEntry logEntry) {
        if (logEntry == null || logEntry.getMessage() == null) return;

        for (LogTemplate template : templates.values()) {
            if (template.matches(logEntry.getMessage())) {
                template.incrementCount();
                if (logEntry.getAppName() != null && !template.getAffectedServices().contains(logEntry.getAppName())) {
                    template.getAffectedServices().add(logEntry.getAppName());
                }
                return;
            }
        }
    }
}
