package com.dlq.platform.es.repository.impl;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.BulkRequest;
import co.elastic.clients.elasticsearch.core.BulkResponse;
import co.elastic.clients.elasticsearch.core.DeleteRequest;
import co.elastic.clients.elasticsearch.core.DeleteResponse;
import co.elastic.clients.elasticsearch.core.GetRequest;
import co.elastic.clients.elasticsearch.core.GetResponse;
import co.elastic.clients.elasticsearch.core.IndexRequest;
import co.elastic.clients.elasticsearch.core.IndexResponse;
import co.elastic.clients.elasticsearch.core.ReindexRequest;
import co.elastic.clients.elasticsearch.core.ReindexResponse;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.UpdateRequest;
import co.elastic.clients.elasticsearch.core.UpdateResponse;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.core.search.TotalHits;
import co.elastic.clients.elasticsearch.core.search.TotalHitsRelation;
import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.Refresh;
import co.elastic.clients.elasticsearch._types.SortOptions;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch._types.query_dsl.RangeQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.TermQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.MatchQuery;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.constants.EsIndexConstants;
import com.dlq.platform.es.entity.ElasticDeadLetterMessage;
import com.dlq.platform.es.repository.DeadLetterRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@Slf4j
@Repository
@RequiredArgsConstructor
public class DeadLetterRepositoryImpl implements DeadLetterRepository {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final ElasticsearchClient elasticsearchClient;

    @Override
    public DeadLetterMessage save(DeadLetterMessage message) {
        try {
            if (message.getCreateTime() == null) {
                message.setCreateTime(LocalDateTime.now());
            }
            message.setUpdateTime(LocalDateTime.now());

            IndexRequest<DeadLetterMessage> request = IndexRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .id(message.getId())
                    .document(message)
                    .refresh(Refresh.True)
            );

            IndexResponse response = elasticsearchClient.index(request);
            log.debug("Saved document with id: {}, result: {}", response.id(), response.result());
            return message;
        } catch (Exception e) {
            log.error("Failed to save dead letter message, id: {}", message.getId(), e);
            throw new RuntimeException("Failed to save dead letter message", e);
        }
    }

    @Override
    public List<DeadLetterMessage> saveBatch(List<DeadLetterMessage> messages) {
        try {
            List<BulkOperation> operations = new ArrayList<>();

            for (DeadLetterMessage message : messages) {
                if (message.getCreateTime() == null) {
                    message.setCreateTime(LocalDateTime.now());
                }
                message.setUpdateTime(LocalDateTime.now());

                BulkOperation operation = BulkOperation.of(b -> b
                        .index(i -> i
                                .index(EsIndexConstants.INDEX_DEAD_LETTER)
                                .id(message.getId())
                                .document(message)
                        )
                );
                operations.add(operation);
            }

            BulkRequest request = BulkRequest.of(b -> b
                    .operations(operations)
                    .refresh(Refresh.True)
            );

            BulkResponse response = elasticsearchClient.bulk(request);

            if (response.errors()) {
                response.items().forEach(item -> {
                    if (item.error() != null) {
                        log.error("Bulk save error for id {}: {}", item.id(), item.error().reason());
                    }
                });
                throw new RuntimeException("Some documents failed to save in batch");
            }

            log.debug("Batch saved {} documents", operations.size());
            return messages;
        } catch (Exception e) {
            log.error("Failed to batch save dead letter messages", e);
            throw new RuntimeException("Failed to batch save dead letter messages", e);
        }
    }

    @Override
    public Optional<DeadLetterMessage> findById(String id) {
        try {
            GetRequest request = GetRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .id(id)
            );

            GetResponse<DeadLetterMessage> response = elasticsearchClient.get(request, DeadLetterMessage.class);

            if (response.found()) {
                return Optional.ofNullable(response.source());
            }
            return Optional.empty();
        } catch (Exception e) {
            log.error("Failed to find dead letter message by id: {}", id, e);
            throw new RuntimeException("Failed to find dead letter message", e);
        }
    }

    @Override
    public Page<DeadLetterMessage> search(DeadLetterQueryDTO query) {
        try {
            int pageNum = query.getPageNum() != null ? query.getPageNum() : 1;
            int pageSize = query.getPageSize() != null ? query.getPageSize() : 10;
            int from = (pageNum - 1) * pageSize;

            Query esQuery = buildQuery(query);

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
            log.error("Failed to search dead letter messages", e);
            throw new RuntimeException("Failed to search dead letter messages", e);
        }
    }

    @Override
    public boolean updateStatus(String id, ProcessStatusEnum status) {
        try {
            Map<String, Object> updateDoc = Map.of(
                    EsIndexConstants.FIELD_PROCESS_STATUS, status,
                    EsIndexConstants.FIELD_UPDATE_TIME, LocalDateTime.now().format(DATE_FORMATTER)
            );

            UpdateRequest<DeadLetterMessage, Map<String, Object>> request = UpdateRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .id(id)
                    .doc(updateDoc)
                    .refresh(Refresh.True)
            );

            UpdateResponse<DeadLetterMessage> response = elasticsearchClient.update(request, DeadLetterMessage.class);
            log.debug("Updated status for id: {}, result: {}", id, response.result());
            return true;
        } catch (Exception e) {
            log.error("Failed to update status for id: {}", id, e);
            return false;
        }
    }

    @Override
    public boolean deleteById(String id) {
        try {
            DeleteRequest request = DeleteRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .id(id)
                    .refresh(Refresh.True)
            );

            DeleteResponse response = elasticsearchClient.delete(request);
            log.debug("Deleted document id: {}, result: {}", id, response.result());
            return true;
        } catch (Exception e) {
            log.error("Failed to delete dead letter message by id: {}", id, e);
            return false;
        }
    }

    @Override
    public long countByQuery(DeadLetterQueryDTO query) {
        try {
            Query esQuery = buildQuery(query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    .query(esQuery)
                    .size(0)
                    .trackTotalHits(t -> t.enabled(true))
            );

            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);

            TotalHits totalHits = response.hits().total();
            return totalHits != null ? totalHits.value() : 0;
        } catch (Exception e) {
            log.error("Failed to count dead letter messages", e);
            throw new RuntimeException("Failed to count dead letter messages", e);
        }
    }

    @Override
    public boolean archive(String id, String archiveIndex) {
        try {
            Query query = Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_ID)
                            .value(FieldValue.of(id))
                    ))
            );

            ReindexRequest request = ReindexRequest.of(b -> b
                    .source(s -> s
                            .index(EsIndexConstants.INDEX_DEAD_LETTER)
                            .query(query)
                    )
                    .dest(d -> d
                            .index(archiveIndex)
                    )
                    .conflicts("proceed")
                    .refresh(true)
            );

            ReindexResponse response = elasticsearchClient.reindex(request);

            if (response.created() > 0 || response.updated() > 0) {
                deleteById(id);
                log.debug("Archived document id: {} to index: {}", id, archiveIndex);
                return true;
            }
            return false;
        } catch (Exception e) {
            log.error("Failed to archive document id: {} to index: {}", id, archiveIndex, e);
            return false;
        }
    }

    @Override
    public boolean batchArchive(List<String> ids, String archiveIndex) {
        try {
            List<FieldValue> idValues = ids.stream()
                    .map(FieldValue::of)
                    .collect(Collectors.toList());

            Query query = Query.of(q -> q
                    .terms(t -> t
                            .field(EsIndexConstants.FIELD_ID)
                            .terms(tt -> tt.value(idValues))
                    )
            );

            ReindexRequest request = ReindexRequest.of(b -> b
                    .source(s -> s
                            .index(EsIndexConstants.INDEX_DEAD_LETTER)
                            .query(query)
                    )
                    .dest(d -> d
                            .index(archiveIndex)
                    )
                    .conflicts("proceed")
                    .refresh(true)
            );

            ReindexResponse response = elasticsearchClient.reindex(request);

            if (response.created() > 0 || response.updated() > 0) {
                for (String id : ids) {
                    deleteById(id);
                }
                log.debug("Batch archived {} documents to index: {}", ids.size(), archiveIndex);
                return true;
            }
            return false;
        } catch (Exception e) {
            log.error("Failed to batch archive {} documents to index: {}", ids.size(), archiveIndex, e);
            return false;
        }
    }

    private Query buildQuery(DeadLetterQueryDTO query) {
        List<Query> mustClauses = new ArrayList<>();
        List<Query> filterClauses = new ArrayList<>();

        if (query.getId() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_ID)
                            .value(FieldValue.of(query.getId()))
                    ))
            ));
        }

        if (query.getMqType() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_MQ_TYPE)
                            .value(FieldValue.of(query.getMqType().name()))
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

        if (query.getMessageId() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_MESSAGE_ID)
                            .value(FieldValue.of(query.getMessageId()))
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

        BoolQuery.Builder boolBuilder = BoolQuery.of(b -> b
                .must(mustClauses)
                .filter(filterClauses)
        )._toBuilder();

        return Query.of(q -> q.bool(boolBuilder.build()));
    }
}
