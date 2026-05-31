package com.dlq.platform.es.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOptions;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.aggregations.Aggregation;
import co.elastic.clients.elasticsearch._types.aggregations.HistogramAggregation;
import co.elastic.clients.elasticsearch._types.aggregations.LongTermsAggregation;
import co.elastic.clients.elasticsearch._types.aggregations.TermsAggregation;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.MatchQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.MultiMatchQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch._types.query_dsl.RangeQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.TermQuery;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.core.search.TotalHits;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.es.constants.EsIndexConstants;
import com.dlq.platform.es.dto.DeadLetterAggregationDTO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterSearchService {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final String AGG_REASON_TYPE = "agg_by_reason_type";
    private static final String AGG_BY_TIME = "agg_by_time";
    private static final String AGG_BY_MQ_TYPE = "agg_by_mq_type";

    private final ElasticsearchClient elasticsearchClient;

    public Page<DeadLetterMessage> fullTextSearch(String keyword, DeadLetterQueryDTO query) {
        try {
            int pageNum = query.getPageNum() != null ? query.getPageNum() : 1;
            int pageSize = query.getPageSize() != null ? query.getPageSize() : 10;
            int from = (pageNum - 1) * pageSize;

            Query esQuery = buildFullTextQuery(keyword, query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .query(esQuery)
                    .from(from)
                    .size(pageSize)
                    .sort(SortOptions.of(s -> s
                            .field(f -> f
                                    .field(EsIndexConstants.FIELD_CREATE_TIME)
                                    .order(SortOrder.Desc)
                            )
                    ))
                    .trackTotalHits(t -> t.enabled(true))
            );

            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);

            List<DeadLetterMessage> content = response.hits().hits().stream()
                    .map(Hit::source)
                    .collect(Collectors.toList());

            TotalHits totalHits = response.hits().total();
            long total = totalHits != null ? totalHits.value() : 0;

            Pageable pageable = PageRequest.of(pageNum - 1, pageSize);
            return new PageImpl<>(content, pageable, total);
        } catch (Exception e) {
            log.error("Failed to perform full text search with keyword: {}", keyword, e);
            throw new RuntimeException("Failed to perform full text search", e);
        }
    }

    public Page<DeadLetterMessage> searchByConditions(DeadLetterQueryDTO query) {
        try {
            int pageNum = query.getPageNum() != null ? query.getPageNum() : 1;
            int pageSize = query.getPageSize() != null ? query.getPageSize() : 10;
            int from = (pageNum - 1) * pageSize;

            Query esQuery = buildConditionQuery(query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .query(esQuery)
                    .from(from)
                    .size(pageSize)
                    .sort(SortOptions.of(s -> s
                            .field(f -> f
                                    .field(EsIndexConstants.FIELD_CREATE_TIME)
                                    .order(SortOrder.Desc)
                            )
                    ))
                    .trackTotalHits(t -> t.enabled(true))
            );

            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);

            List<DeadLetterMessage> content = response.hits().hits().stream()
                    .map(Hit::source)
                    .collect(Collectors.toList());

            TotalHits totalHits = response.hits().total();
            long total = totalHits != null ? totalHits.value() : 0;

            Pageable pageable = PageRequest.of(pageNum - 1, pageSize);
            return new PageImpl<>(content, pageable, total);
        } catch (Exception e) {
            log.error("Failed to search dead letter messages by conditions", e);
            throw new RuntimeException("Failed to search dead letter messages by conditions", e);
        }
    }

    public DeadLetterAggregationDTO aggregate(DeadLetterQueryDTO query) {
        try {
            Query esQuery = buildConditionQuery(query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .query(esQuery)
                    .size(0)
                    .aggregations(AGG_REASON_TYPE, buildReasonTypeAggregation())
                    .aggregations(AGG_BY_TIME, buildTimeAggregation(query))
                    .aggregations(AGG_BY_MQ_TYPE, buildMqTypeAggregation())
            );

            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);

            DeadLetterAggregationDTO aggregationDTO = new DeadLetterAggregationDTO();

            if (response.aggregations() != null) {
                if (response.aggregations().get(AGG_REASON_TYPE) != null) {
                    List<DeadLetterAggregationDTO.ReasonTypeBucket> reasonTypeBuckets = response.aggregations()
                            .get(AGG_REASON_TYPE)
                            .lterms()
                            .buckets()
                            .array()
                            .stream()
                            .map(bucket -> DeadLetterAggregationDTO.ReasonTypeBucket.builder()
                                    .reasonType(bucket.key().stringValue())
                                    .count(bucket.docCount())
                                    .build())
                            .collect(Collectors.toList());
                    aggregationDTO.setReasonTypeStats(reasonTypeBuckets);
                }

                if (response.aggregations().get(AGG_BY_TIME) != null) {
                    List<DeadLetterAggregationDTO.TimeBucket> timeBuckets = response.aggregations()
                            .get(AGG_BY_TIME)
                            .histogram()
                            .buckets()
                            .array()
                            .stream()
                            .map(bucket -> {
                                long timestamp = bucket.key().longValue();
                                String timeStr = formatTimestamp(timestamp);
                                return DeadLetterAggregationDTO.TimeBucket.builder()
                                        .time(timeStr)
                                        .count(bucket.docCount())
                                        .build();
                            })
                            .collect(Collectors.toList());
                    aggregationDTO.setTimeStats(timeBuckets);
                }

                if (response.aggregations().get(AGG_BY_MQ_TYPE) != null) {
                    List<DeadLetterAggregationDTO.MqTypeBucket> mqTypeBuckets = response.aggregations()
                            .get(AGG_BY_MQ_TYPE)
                            .lterms()
                            .buckets()
                            .array()
                            .stream()
                            .map(bucket -> DeadLetterAggregationDTO.MqTypeBucket.builder()
                                    .mqType(bucket.key().stringValue())
                                    .count(bucket.docCount())
                                    .build())
                            .collect(Collectors.toList());
                    aggregationDTO.setMqTypeStats(mqTypeBuckets);
                }
            }

            return aggregationDTO;
        } catch (Exception e) {
            log.error("Failed to aggregate dead letter messages", e);
            throw new RuntimeException("Failed to aggregate dead letter messages", e);
        }
    }

    public Page<DeadLetterMessage> search(String keyword, DeadLetterQueryDTO query) {
        if (keyword != null && !keyword.trim().isEmpty()) {
            return fullTextSearch(keyword, query);
        }
        return searchByConditions(query);
    }

    private Query buildFullTextQuery(String keyword, DeadLetterQueryDTO query) {
        List<Query> mustClauses = new ArrayList<>();
        List<Query> filterClauses = new ArrayList<>();

        if (keyword != null && !keyword.trim().isEmpty()) {
            Query multiMatchQuery = Query.of(q -> q
                    .multiMatch(MultiMatchQuery.of(m -> m
                            .query(keyword)
                            .fields(EsIndexConstants.FIELD_MESSAGE_BODY, EsIndexConstants.FIELD_DEAD_REASON)
                            .analyzer(EsIndexConstants.ANALYZER_IK_SMART)
                            .type(co.elastic.clients.elasticsearch._types.query_dsl.MultiMatchQueryType.BestFields)
                    ))
            );
            mustClauses.add(multiMatchQuery);
        }

        addConditionFilters(query, filterClauses);

        BoolQuery.Builder boolBuilder = BoolQuery.of(b -> b
                .must(mustClauses)
                .filter(filterClauses)
        )._toBuilder();

        return Query.of(q -> q.bool(boolBuilder.build()));
    }

    private Query buildConditionQuery(DeadLetterQueryDTO query) {
        List<Query> filterClauses = new ArrayList<>();
        addConditionFilters(query, filterClauses);

        BoolQuery.Builder boolBuilder = BoolQuery.of(b -> b
                .filter(filterClauses)
        )._toBuilder();

        return Query.of(q -> q.bool(boolBuilder.build()));
    }

    private void addConditionFilters(DeadLetterQueryDTO query, List<Query> filterClauses) {
        if (query.getMqType() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_MQ_TYPE)
                            .value(FieldValue.of(query.getMqType().name()))
                    ))
            ));
        }

        if (query.getDeadReasonType() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_DEAD_REASON_TYPE)
                            .value(FieldValue.of(query.getDeadReasonType().name()))
                    ))
            ));
        }

        if (query.getProcessStatus() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_PROCESS_STATUS)
                            .value(FieldValue.of(query.getProcessStatus().name()))
                    ))
            ));
        }

        if (query.getTopic() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_TOPIC)
                            .value(FieldValue.of(query.getTopic()))
                    ))
            ));
        }

        if (query.getQueueName() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_QUEUE_NAME)
                            .value(FieldValue.of(query.getQueueName()))
                    ))
            ));
        }

        if (query.getStartTime() != null || query.getEndTime() != null) {
            RangeQuery.Builder rangeBuilder = RangeQuery.of(r -> r
                    .field(EsIndexConstants.FIELD_CREATE_TIME)
            )._toBuilder();

            if (query.getStartTime() != null) {
                rangeBuilder.gte(JsonData.of(query.getStartTime().format(DATE_FORMATTER)));
            }
            if (query.getEndTime() != null) {
                rangeBuilder.lte(JsonData.of(query.getEndTime().format(DATE_FORMATTER)));
            }

            filterClauses.add(Query.of(q -> q.range(rangeBuilder.build())));
        }
    }

    private Aggregation buildReasonTypeAggregation() {
        return Aggregation.of(a -> a
                .lterms(LongTermsAggregation.of(t -> t
                        .field(EsIndexConstants.FIELD_DEAD_REASON_TYPE)
                        .size(100)
                ))
        );
    }

    private Aggregation buildTimeAggregation(DeadLetterQueryDTO query) {
        long interval = calculateInterval(query);

        return Aggregation.of(a -> a
                .histogram(HistogramAggregation.of(h -> h
                        .field(EsIndexConstants.FIELD_CREATE_TIME)
                        .interval((double) interval)
                        .format("yyyy-MM-dd HH:mm:ss")
                        .minDocCount(0)
                ))
        );
    }

    private Aggregation buildMqTypeAggregation() {
        return Aggregation.of(a -> a
                .lterms(LongTermsAggregation.of(t -> t
                        .field(EsIndexConstants.FIELD_MQ_TYPE)
                        .size(100)
                ))
        );
    }

    private long calculateInterval(DeadLetterQueryDTO query) {
        long defaultInterval = 3600000L;

        if (query.getStartTime() != null && query.getEndTime() != null) {
            long startMillis = query.getStartTime().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
            long endMillis = query.getEndTime().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
            long diff = endMillis - startMillis;

            if (diff <= 86400000L) {
                return 3600000L;
            } else if (diff <= 604800000L) {
                return 86400000L;
            } else {
                return 86400000L * 7;
            }
        }

        return defaultInterval;
    }

    private String formatTimestamp(long timestamp) {
        return LocalDateTime.ofInstant(
                java.time.Instant.ofEpochMilli(timestamp),
                ZoneId.systemDefault()
        ).format(DATE_FORMATTER);
    }
}
