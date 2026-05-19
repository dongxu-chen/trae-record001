package com.logplatform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.indices.CreateIndexRequest;
import co.elastic.clients.elasticsearch.indices.ExistsRequest;
import co.elastic.clients.elasticsearch.indices.PutIndexTemplateRequest;
import co.elastic.clients.json.JsonData;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logplatform.config.IkAnalyzerConfig;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class IndexManagementService {

    private final ElasticsearchClient elasticsearchClient;
    private final ObjectMapper objectMapper;
    private final IkAnalyzerConfig ikAnalyzerConfig;

    @PostConstruct
    public void init() {
        try {
            createLogIndexTemplate();
            createTodayIndex();
        } catch (Exception e) {
            log.error("Failed to initialize index management", e);
        }
    }

    private void createLogIndexTemplate() throws Exception {
        String templateName = "unified-logs-template";

        Map<String, Object> settings = new HashMap<>();
        settings.put("number_of_shards", 3);
        settings.put("number_of_replicas", 1);
        settings.put("refresh_interval", "5s");
        settings.put("index.codec", "best_compression");
        settings.put("index.mapping.total_fields.limit", 2000);

        Map<String, Object> analysis = buildAnalysisConfig();
        if (!analysis.isEmpty()) {
            settings.put("analysis", analysis);
        }

        Map<String, Object> mappings = new HashMap<>();
        mappings.put("dynamic_templates", buildDynamicTemplates());
        mappings.put("properties", buildProperties());

        PutIndexTemplateRequest request = PutIndexTemplateRequest.of(b -> b
                .name(templateName)
                .indexPatterns("unified-logs-*")
                .settings(s -> s
                        .numberOfShards("3")
                        .numberOfReplicas("1")
                        .refreshInterval(r -> r.time("5s"))
                        .otherSettings(JsonData.of(analysis))
                )
                .mappings(m -> m
                        .dynamicTemplates(dynamicTemplates())
                        .properties(properties())
                )
        );

        try {
            elasticsearchClient.indices().putIndexTemplate(request);
            log.info("Index template created with IK analyzer: {}", templateName);
        } catch (Exception e) {
            log.warn("Index template may already exist: {}", templateName, e);
        }
    }

    private Map<String, Object> buildAnalysisConfig() {
        Map<String, Object> analysis = new HashMap<>();

        Map<String, Object> analyzer = new HashMap<>();
        analyzer.put("ik_smart", Map.of(
                "type", "custom",
                "tokenizer", "ik_smart",
                "filter", Arrays.asList("synonym_filter", "stop_filter")
        ));
        analyzer.put("ik_max_word", Map.of(
                "type", "custom",
                "tokenizer", "ik_max_word",
                "filter", Arrays.asList("synonym_filter", "stop_filter")
        ));
        analyzer.put("ik_search", Map.of(
                "type", "custom",
                "tokenizer", "ik_smart",
                "filter", Arrays.asList("synonym_filter", "stop_filter")
        ));
        analysis.put("analyzer", analyzer);

        Map<String, Object> filter = new HashMap<>();
        filter.put("synonym_filter", Map.of(
                "type", "synonym",
                "synonyms_path", "analysis/synonyms.txt",
                "expand", true,
                "lenient", true
        ));
        filter.put("stop_filter", Map.of(
                "type", "stop",
                "stopwords_path", "analysis/stopwords.txt"
        ));
        analysis.put("filter", filter);

        return analysis;
    }

    private List<Map<String, Object>> buildDynamicTemplates() {
        List<Map<String, Object>> templates = new ArrayList<>();
        templates.add(Map.of(
                "strings", Map.of(
                        "match_mapping_type", "string",
                        "mapping", Map.of(
                                "type", "keyword",
                                "ignore_above", 256
                        )
                )
        ));
        return templates;
    }

    private Map<String, Object> buildProperties() {
        Map<String, Object> properties = new HashMap<>();
        properties.put("@timestamp", Map.of("type", "date"));
        properties.put("message", Map.of(
                "type", "text",
                "analyzer", "ik_max_word",
                "search_analyzer", "ik_search",
                "term_vector", "with_positions_offsets"
        ));
        properties.put("appName", Map.of("type", "keyword"));
        properties.put("level", Map.of("type", "keyword"));
        properties.put("logger", Map.of("type", "keyword"));
        properties.put("thread", Map.of("type", "keyword"));
        properties.put("stackTrace", Map.of(
                "type", "text",
                "analyzer", "ik_smart",
                "index_options", "offsets"
        ));
        properties.put("host", Map.of("type", "keyword"));
        properties.put("ip", Map.of("type", "ip"));
        properties.put("traceId", Map.of("type", "keyword"));
        return properties;
    }

    private List<co.elastic.clients.elasticsearch._types.mapping.DynamicTemplate> dynamicTemplates() {
        return List.of(
                co.elastic.clients.elasticsearch._types.mapping.DynamicTemplate.of(dt -> dt
                        .name("strings")
                        .pathMatch("*")
                        .mapping(m -> m
                                .keyword(k -> k.ignoreAbove(256))
                        )
                )
        );
    }

    private Map<String, co.elastic.clients.elasticsearch._types.mapping.Property> properties() {
        Map<String, co.elastic.clients.elasticsearch._types.mapping.Property> props = new HashMap<>();

        props.put("@timestamp", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.date(d -> d)));

        props.put("message", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.text(t -> t
                        .analyzer("ik_max_word")
                        .searchAnalyzer("ik_search")
                        .termVector(co.elastic.clients.elasticsearch._types.mapping.TermVectorOption.WithPositionsOffsets)
                )));

        props.put("appName", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));
        props.put("level", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));
        props.put("logger", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));
        props.put("thread", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));

        props.put("stackTrace", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.text(t -> t
                        .analyzer("ik_smart")
                        .indexOptions(co.elastic.clients.elasticsearch._types.mapping.IndexOptions.Offsets)
                )));

        props.put("host", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));
        props.put("ip", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.ip(i -> i)));
        props.put("traceId", co.elastic.clients.elasticsearch._types.mapping.Property.of(
                p -> p.keyword(k -> k)));

        return props;
    }

    private void createTodayIndex() throws Exception {
        String todayIndex = "unified-logs-" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy.MM.dd"));

        boolean exists = elasticsearchClient.indices().exists(
                ExistsRequest.of(b -> b.index(todayIndex))).value();

        if (!exists) {
            elasticsearchClient.indices().create(
                    CreateIndexRequest.of(b -> b.index(todayIndex)));
            log.info("Created today's index: {}", todayIndex);
        }
    }

    public void createIndexForDate(LocalDate date) throws Exception {
        String indexName = "unified-logs-" + date.format(DateTimeFormatter.ofPattern("yyyy.MM.dd"));
        boolean exists = elasticsearchClient.indices().exists(
                ExistsRequest.of(b -> b.index(indexName))).value();

        if (!exists) {
            elasticsearchClient.indices().create(
                    CreateIndexRequest.of(b -> b.index(indexName)));
            log.info("Created index: {}", indexName);
        }
    }
}
