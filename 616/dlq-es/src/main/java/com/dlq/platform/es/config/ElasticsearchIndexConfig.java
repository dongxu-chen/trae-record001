package com.dlq.platform.es.config;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.indices.CreateIndexRequest;
import co.elastic.clients.elasticsearch.indices.CreateIndexResponse;
import co.elastic.clients.elasticsearch.indices.IndexTemplate;
import co.elastic.clients.elasticsearch.indices.PutIndexTemplateRequest;
import co.elastic.clients.elasticsearch.indices.PutIndexTemplateResponse;
import co.elastic.clients.elasticsearch.indices.ExistsRequest;
import co.elastic.clients.elasticsearch._types.mapping.TypeMapping;
import com.dlq.platform.es.constants.EsIndexConstants;
import com.dlq.platform.es.entity.ElasticDeadLetterMessage;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class ElasticsearchIndexConfig {

    private final ElasticsearchClient elasticsearchClient;

    @PostConstruct
    public void init() {
        try {
            createDeadLetterIndexTemplate();
            createArchiveIndexTemplate();
            ensureIndexExists(EsIndexConstants.INDEX_DEAD_LETTER);
            log.info("Elasticsearch indexes and templates initialized successfully");
        } catch (Exception e) {
            log.error("Failed to initialize Elasticsearch indexes", e);
        }
    }

    private void createDeadLetterIndexTemplate() throws Exception {
        String templateName = "dlq_dead_letter_template";

        PutIndexTemplateRequest request = PutIndexTemplateRequest.of(b -> b
                .name(templateName)
                .indexPatterns(EsIndexConstants.INDEX_DEAD_LETTER)
                .settings(s -> s
                        .numberOfShards("3")
                        .numberOfReplicas("1")
                        .refreshInterval("5s")
                        .analysis(a -> a
                                .analyzer("ik_max_word", an -> an.custom(c -> c.type("ik_max_word")))
                                .analyzer("ik_smart", an -> an.custom(c -> c.type("ik_smart")))
                        )
                )
                .mappings(TypeMapping.of(m -> m
                        .properties(ElasticDeadLetterMessage.getMappings())
                ))
                .version(1L)
        );

        PutIndexTemplateResponse response = elasticsearchClient.indices().putIndexTemplate(request);
        log.info("Created dead letter index template: {}, acknowledged: {}", templateName, response.acknowledged());
    }

    private void createArchiveIndexTemplate() throws Exception {
        String templateName = "dlq_archive_template";

        PutIndexTemplateRequest request = PutIndexTemplateRequest.of(b -> b
                .name(templateName)
                .indexPatterns(EsIndexConstants.INDEX_ARCHIVE_PREFIX + "*")
                .settings(s -> s
                        .numberOfShards("3")
                        .numberOfReplicas("1")
                        .refreshInterval("30s")
                        .analysis(a -> a
                                .analyzer("ik_max_word", an -> an.custom(c -> c.type("ik_max_word")))
                                .analyzer("ik_smart", an -> an.custom(c -> c.type("ik_smart")))
                        )
                )
                .mappings(TypeMapping.of(m -> m
                        .properties(ElasticDeadLetterMessage.getMappings())
                ))
                .version(1L)
        );

        PutIndexTemplateResponse response = elasticsearchClient.indices().putIndexTemplate(request);
        log.info("Created archive index template: {}, acknowledged: {}", templateName, response.acknowledged());
    }

    private void ensureIndexExists(String indexName) throws Exception {
        ExistsRequest existsRequest = ExistsRequest.of(b -> b.index(indexName));
        boolean exists = elasticsearchClient.indices().exists(existsRequest).value();

        if (!exists) {
            Map<String, Object> settings = ElasticDeadLetterMessage.getSettings();

            CreateIndexRequest createRequest = CreateIndexRequest.of(b -> b
                    .index(indexName)
                    .settings(s -> s
                            .numberOfShards(String.valueOf(settings.get("number_of_shards")))
                            .numberOfReplicas(String.valueOf(settings.get("number_of_replicas")))
                            .refreshInterval(String.valueOf(settings.get("refresh_interval")))
                    )
                    .mappings(TypeMapping.of(m -> m
                            .properties(ElasticDeadLetterMessage.getMappings())
                    ))
            );

            CreateIndexResponse response = elasticsearchClient.indices().create(createRequest);
            log.info("Created index: {}, acknowledged: {}", indexName, response.acknowledged());
        } else {
            log.info("Index {} already exists", indexName);
        }
    }
}
