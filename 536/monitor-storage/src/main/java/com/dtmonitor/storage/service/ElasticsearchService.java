package com.dtmonitor.storage.service;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.elasticsearch.action.bulk.BulkRequest;
import org.elasticsearch.action.bulk.BulkResponse;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.xcontent.XContentType;
import org.elasticsearch.index.query.BoolQueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.aggregations.AggregationBuilders;
import org.elasticsearch.search.aggregations.bucket.terms.Terms;
import org.elasticsearch.search.aggregations.metrics.ValueCount;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.elasticsearch.search.sort.SortOrder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
public class ElasticsearchService {

    private static final String INDEX_PREFIX = "dtm-transaction-";
    private static final DateTimeFormatter INDEX_FORMATTER = DateTimeFormatter.ofPattern("yyyy.MM.dd");

    private final RestHighLevelClient esClient;
    private final ObjectMapper objectMapper;

    @Value("${elasticsearch.index.shards:1}")
    private int numberOfShards;

    @Value("${elasticsearch.index.replicas:0}")
    private int numberOfReplicas;

    public ElasticsearchService(RestHighLevelClient esClient, ObjectMapper objectMapper) {
        this.esClient = esClient;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void init() {
        ensureIndexExists(todayIndex());
    }

    public void indexTransaction(GlobalTransaction transaction) {
        try {
            String indexName = resolveIndex(transaction.getBeginTime());
            ensureIndexExists(indexName);

            String json = objectMapper.writeValueAsString(toMap(transaction));
            IndexRequest request = new IndexRequest(indexName)
                    .id(transaction.getXid())
                    .source(json, XContentType.JSON);

            esClient.index(request, RequestOptions.DEFAULT);
            log.debug("Indexed transaction {} to ES index {}", transaction.getXid(), indexName);
        } catch (IOException e) {
            log.error("Failed to index transaction: {}", transaction.getXid(), e);
        }
    }

    public void bulkIndexTransactions(List<GlobalTransaction> transactions) {
        if (transactions == null || transactions.isEmpty()) return;

        try {
            BulkRequest bulkRequest = new BulkRequest();
            for (GlobalTransaction tx : transactions) {
                String indexName = resolveIndex(tx.getBeginTime());
                ensureIndexExists(indexName);

                String json = objectMapper.writeValueAsString(toMap(tx));
                IndexRequest request = new IndexRequest(indexName)
                        .id(tx.getXid())
                        .source(json, XContentType.JSON);
                bulkRequest.add(request);
            }

            BulkResponse response = esClient.bulk(bulkRequest, RequestOptions.DEFAULT);
            if (response.hasFailures()) {
                log.warn("Bulk indexing has failures: {}", response.buildFailureMessage());
            }
        } catch (IOException e) {
            log.error("Failed to bulk index transactions", e);
        }
    }

    public Page<GlobalTransaction> searchTransactions(TransactionMode mode, TransactionStatus status,
                                                      String applicationId, LocalDateTime startTime,
                                                      LocalDateTime endTime, Pageable pageable) {
        try {
            SearchRequest searchRequest = new SearchRequest(INDEX_PREFIX + "*");
            SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();

            BoolQueryBuilder boolQuery = QueryBuilders.boolQuery();
            if (mode != null) {
                boolQuery.filter(QueryBuilders.termQuery("mode", mode.name()));
            }
            if (status != null) {
                boolQuery.filter(QueryBuilders.termQuery("status", status.name()));
            }
            if (applicationId != null && !applicationId.isEmpty()) {
                boolQuery.filter(QueryBuilders.termQuery("applicationId", applicationId));
            }
            if (startTime != null || endTime != null) {
                boolQuery.filter(QueryBuilders.rangeQuery("beginTime")
                        .gte(startTime != null ? startTime.toString() : null)
                        .lte(endTime != null ? endTime.toString() : null));
            }

            sourceBuilder.query(boolQuery);
            sourceBuilder.from((int) pageable.getOffset());
            sourceBuilder.size(pageable.getPageSize());
            sourceBuilder.sort("beginTime", SortOrder.DESC);

            searchRequest.source(sourceBuilder);
            SearchResponse response = esClient.search(searchRequest, RequestOptions.DEFAULT);

            List<GlobalTransaction> results = new ArrayList<>();
            Arrays.stream(response.getHits().getHits())
                    .forEach(hit -> {
                        try {
                            GlobalTransaction tx = objectMapper.readValue(
                                    hit.getSourceAsString(), GlobalTransaction.class);
                            results.add(tx);
                        } catch (IOException e) {
                            log.error("Failed to parse ES hit", e);
                        }
                    });

            long total = response.getHits().getTotalHits().value;
            return new PageImpl<>(results, pageable, total);
        } catch (IOException e) {
            log.error("Failed to search transactions from ES", e);
            return Page.empty(pageable);
        }
    }

    public Map<String, Long> aggregateByStatus() {
        try {
            SearchRequest searchRequest = new SearchRequest(INDEX_PREFIX + "*");
            SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
            sourceBuilder.size(0);
            sourceBuilder.aggregation(AggregationBuilders.terms("status_agg").field("status"));

            searchRequest.source(sourceBuilder);
            SearchResponse response = esClient.search(searchRequest, RequestOptions.DEFAULT);

            Map<String, Long> result = new LinkedHashMap<>();
            Terms terms = response.getAggregations().get("status_agg");
            for (Terms.Bucket bucket : terms.getBuckets()) {
                result.put(bucket.getKeyAsString(), bucket.getDocCount());
            }
            return result;
        } catch (IOException e) {
            log.error("Failed to aggregate by status", e);
            return Collections.emptyMap();
        }
    }

    public Map<String, Long> aggregateByMode() {
        try {
            SearchRequest searchRequest = new SearchRequest(INDEX_PREFIX + "*");
            SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
            sourceBuilder.size(0);
            sourceBuilder.aggregation(AggregationBuilders.terms("mode_agg").field("mode"));

            searchRequest.source(sourceBuilder);
            SearchResponse response = esClient.search(searchRequest, RequestOptions.DEFAULT);

            Map<String, Long> result = new LinkedHashMap<>();
            Terms terms = response.getAggregations().get("mode_agg");
            for (Terms.Bucket bucket : terms.getBuckets()) {
                result.put(bucket.getKeyAsString(), bucket.getDocCount());
            }
            return result;
        } catch (IOException e) {
            log.error("Failed to aggregate by mode", e);
            return Collections.emptyMap();
        }
    }

    public long countByStatus(TransactionStatus status) {
        try {
            SearchRequest searchRequest = new SearchRequest(INDEX_PREFIX + "*");
            SearchSourceBuilder sourceBuilder = new SearchSourceBuilder();
            sourceBuilder.size(0);
            sourceBuilder.query(QueryBuilders.termQuery("status", status.name()));

            searchRequest.source(sourceBuilder);
            SearchResponse response = esClient.search(searchRequest, RequestOptions.DEFAULT);
            return response.getHits().getTotalHits().value;
        } catch (IOException e) {
            log.error("Failed to count by status from ES", e);
            return 0;
        }
    }

    private void ensureIndexExists(String indexName) {
        try {
            GetIndexRequest getIndexRequest = new GetIndexRequest(indexName);
            boolean exists = esClient.indices().exists(getIndexRequest, RequestOptions.DEFAULT);
            if (!exists) {
                CreateIndexRequest createRequest = new CreateIndexRequest(indexName);
                String mapping = "{\n" +
                        "  \"mappings\": {\n" +
                        "    \"properties\": {\n" +
                        "      \"xid\": { \"type\": \"keyword\" },\n" +
                        "      \"applicationId\": { \"type\": \"keyword\" },\n" +
                        "      \"transactionServiceGroup\": { \"type\": \"keyword\" },\n" +
                        "      \"mode\": { \"type\": \"keyword\" },\n" +
                        "      \"status\": { \"type\": \"keyword\" },\n" +
                        "      \"beginTime\": { \"type\": \"date\", \"format\": \"yyyy-MM-dd'T'HH:mm:ss\" },\n" +
                        "      \"endTime\": { \"type\": \"date\", \"format\": \"yyyy-MM-dd'T'HH:mm:ss\" },\n" +
                        "      \"timeoutMs\": { \"type\": \"long\" },\n" +
                        "      \"traceId\": { \"type\": \"keyword\" },\n" +
                        "      \"remark\": { \"type\": \"text\" },\n" +
                        "      \"rollbackReason\": { \"type\": \"text\" }\n" +
                        "    }\n" +
                        "  },\n" +
                        "  \"settings\": {\n" +
                        "    \"number_of_shards\": " + numberOfShards + ",\n" +
                        "    \"number_of_replicas\": " + numberOfReplicas + "\n" +
                        "  }\n" +
                        "}";
                createRequest.source(mapping, XContentType.JSON);
                esClient.indices().create(createRequest, RequestOptions.DEFAULT);
                log.info("Created ES index: {}", indexName);
            }
        } catch (IOException e) {
            log.error("Failed to ensure ES index exists: {}", indexName, e);
        }
    }

    private String todayIndex() {
        return INDEX_PREFIX + LocalDateTime.now().format(INDEX_FORMATTER);
    }

    private String resolveIndex(LocalDateTime time) {
        if (time == null) return todayIndex();
        return INDEX_PREFIX + time.format(INDEX_FORMATTER);
    }

    private Map<String, Object> toMap(GlobalTransaction tx) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("xid", tx.getXid());
        map.put("applicationId", tx.getApplicationId());
        map.put("transactionServiceGroup", tx.getTransactionServiceGroup());
        map.put("mode", tx.getMode() != null ? tx.getMode().name() : null);
        map.put("status", tx.getStatus() != null ? tx.getStatus().name() : null);
        map.put("beginTime", tx.getBeginTime() != null ? tx.getBeginTime().toString() : null);
        map.put("endTime", tx.getEndTime() != null ? tx.getEndTime().toString() : null);
        map.put("timeoutMs", tx.getTimeoutMs());
        map.put("traceId", tx.getTraceId());
        map.put("remark", tx.getRemark());
        map.put("rollbackReason", tx.getRollbackReason());
        return map;
    }
}
