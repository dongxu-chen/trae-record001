package com.dlq.platform.es.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOptions;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch._types.query_dsl.RangeQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.TermQuery;
import co.elastic.clients.elasticsearch.core.ReindexRequest;
import co.elastic.clients.elasticsearch.core.ReindexResponse;
import co.elastic.clients.elasticsearch.core.SearchRequest;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.core.search.TotalHits;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.ArchiveRequest;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.constants.EsIndexConstants;
import com.dlq.platform.es.repository.DeadLetterRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ArchiveService {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final DateTimeFormatter MONTH_FORMATTER = DateTimeFormatter.ofPattern("yyyyMM");

    private final ElasticsearchClient elasticsearchClient;
    private final DeadLetterRepository deadLetterRepository;

    public boolean archiveByConditions(ArchiveRequest request) {
        try {
            String archiveIndex = generateMonthlyArchiveIndex(request.getArchiveMonth());
            ensureArchiveIndexExists(archiveIndex);

            List<String> ids = findIdsByConditions(request);

            if (ids.isEmpty()) {
                log.info("No messages found to archive for conditions: {}", request);
                return true;
            }

            boolean success = deadLetterRepository.batchArchive(ids, archiveIndex);

            if (success) {
                log.info("Successfully archived {} messages to index: {}", ids.size(), archiveIndex);
            }

            return success;
        } catch (Exception e) {
            log.error("Failed to archive messages by conditions: {}", request, e);
            return false;
        }
    }

    public boolean archiveByIds(List<String> ids, String archiveMonth) {
        try {
            String archiveIndex = generateMonthlyArchiveIndex(archiveMonth);
            ensureArchiveIndexExists(archiveIndex);

            boolean success = deadLetterRepository.batchArchive(ids, archiveIndex);

            if (success) {
                log.info("Successfully archived {} messages to index: {}", ids.size(), archiveIndex);
            }

            return success;
        } catch (Exception e) {
            log.error("Failed to archive messages by ids: {}", ids, e);
            return false;
        }
    }

    public boolean restore(String id, String archiveIndex) {
        try {
            Query query = Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_ID)
                            .value(FieldValue.of(id))
                    ))
            );

            ReindexRequest request = ReindexRequest.of(b -> b
                    .source(s -> s
                            .index(archiveIndex)
                            .query(query)
                    )
                    .dest(d -> d
                            .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    )
                    .conflicts("proceed")
                    .refresh(true)
            );

            ReindexResponse response = elasticsearchClient.reindex(request);

            if (response.created() > 0 || response.updated() > 0) {
                deleteFromArchive(id, archiveIndex);
                deadLetterRepository.updateStatus(id, ProcessStatusEnum.PENDING);
                log.info("Successfully restored message id: {} from archive index: {}", id, archiveIndex);
                return true;
            }

            return false;
        } catch (Exception e) {
            log.error("Failed to restore message id: {} from archive index: {}", id, archiveIndex, e);
            return false;
        }
    }

    public boolean batchRestore(List<String> ids, String archiveIndex) {
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
                            .index(archiveIndex)
                            .query(query)
                    )
                    .dest(d -> d
                            .index(EsIndexConstants.INDEX_DEAD_LETTER)
                    )
                    .conflicts("proceed")
                    .refresh(true)
            );

            ReindexResponse response = elasticsearchClient.reindex(request);

            if (response.created() > 0 || response.updated() > 0) {
                for (String id : ids) {
                    deleteFromArchive(id, archiveIndex);
                    deadLetterRepository.updateStatus(id, ProcessStatusEnum.PENDING);
                }
                log.info("Successfully restored {} messages from archive index: {}", ids.size(), archiveIndex);
                return true;
            }

            return false;
        } catch (Exception e) {
            log.error("Failed to batch restore {} messages from archive index: {}", ids.size(), archiveIndex, e);
            return false;
        }
    }

    public Page<DeadLetterMessage> searchArchive(String archiveIndex, DeadLetterQueryDTO query) {
        try {
            int pageNum = query.getPageNum() != null ? query.getPageNum() : 1;
            int pageSize = query.getPageSize() != null ? query.getPageSize() : 10;
            int from = (pageNum - 1) * pageSize;

            Query esQuery = buildArchiveQuery(query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(archiveIndex)
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
            log.error("Failed to search archive index: {}", archiveIndex, e);
            throw new RuntimeException("Failed to search archive", e);
        }
    }

    public long countArchive(String archiveIndex, DeadLetterQueryDTO query) {
        try {
            Query esQuery = buildArchiveQuery(query);

            SearchRequest request = SearchRequest.of(b -> b
                    .index(archiveIndex)
                    .query(esQuery)
                    .size(0)
                    .trackTotalHits(t -> t.enabled(true))
            );

            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);

            TotalHits totalHits = response.hits().total();
            return totalHits != null ? totalHits.value() : 0;
        } catch (Exception e) {
            log.error("Failed to count archive index: {}", archiveIndex, e);
            throw new RuntimeException("Failed to count archive", e);
        }
    }

    private String generateMonthlyArchiveIndex(String monthStr) {
        String suffix;
        if (monthStr != null && !monthStr.trim().isEmpty()) {
            suffix = monthStr;
        } else {
            suffix = YearMonth.now().format(MONTH_FORMATTER);
        }
        return EsIndexConstants.getArchiveIndex(suffix);
    }

    private void ensureArchiveIndexExists(String indexName) throws Exception {
        boolean exists = elasticsearchClient.indices()
                .exists(b -> b.index(indexName))
                .value();

        if (!exists) {
            elasticsearchClient.indices().create(b -> b
                    .index(indexName)
                    .settings(s -> s
                            .numberOfShards("3")
                            .numberOfReplicas("1")
                            .refreshInterval("30s")
                    )
            );
            log.info("Created archive index: {}", indexName);
        }
    }

    private List<String> findIdsByConditions(ArchiveRequest request) throws Exception {
        List<Query> filterClauses = new ArrayList<>();

        if (request.getMqType() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_MQ_TYPE)
                            .value(FieldValue.of(request.getMqType().name()))
                    ))
            ));
        }

        if (request.getDeadReasonType() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_DEAD_REASON_TYPE)
                            .value(FieldValue.of(request.getDeadReasonType().name()))
                    ))
            ));
        }

        if (request.getProcessStatus() != null) {
            filterClauses.add(Query.of(q -> q
                    .term(TermQuery.of(t -> t
                            .field(EsIndexConstants.FIELD_PROCESS_STATUS)
                            .value(FieldValue.of(request.getProcessStatus().name()))
                    ))
            ));
        }

        if (request.getStartTime() != null || request.getEndTime() != null) {
            RangeQuery.Builder rangeBuilder = RangeQuery.of(r -> r
                    .field(EsIndexConstants.FIELD_CREATE_TIME)
            )._toBuilder();

            if (request.getStartTime() != null) {
                rangeBuilder.gte(JsonData.of(request.getStartTime().format(DATE_FORMATTER)));
            }
            if (request.getEndTime() != null) {
                rangeBuilder.lte(JsonData.of(request.getEndTime().format(DATE_FORMATTER)));
            }

            filterClauses.add(Query.of(q -> q.range(rangeBuilder.build())));
        }

        Query esQuery = Query.of(q -> q
                .bool(BoolQuery.of(b -> b.filter(filterClauses)))
        );

        SearchRequest searchRequest = SearchRequest.of(b -> b
                .index(EsIndexConstants.INDEX_DEAD_LETTER)
                .query(esQuery)
                .size(request.getBatchSize() != null ? request.getBatchSize() : 1000)
                .source(s -> s.filter(f -> f.includes(EsIndexConstants.FIELD_ID)))
        );

        SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(searchRequest, DeadLetterMessage.class);

        return response.hits().hits().stream()
                .map(Hit::id)
                .collect(Collectors.toList());
    }

    private void deleteFromArchive(String id, String archiveIndex) throws Exception {
        elasticsearchClient.delete(b -> b
                .index(archiveIndex)
                .id(id)
                .refresh(true)
        );
    }

    public Map<String, Object> searchArchive(DeadLetterQueryDTO query, String archiveIndex) {
        Map<String, Object> result = new java.util.HashMap<>();
        try {
            String index = archiveIndex != null ? archiveIndex : EsIndexConstants.INDEX_ARCHIVE_PREFIX + "*";
            Page<DeadLetterMessage> page = searchArchive(index, query);
            result.put("success", true);
            result.put("list", page.getContent());
            result.put("total", page.getTotalElements());
            result.put("pageNum", query.getPageNum());
            result.put("pageSize", query.getPageSize());
            result.put("pages", page.getTotalPages());
        } catch (Exception e) {
            log.error("Failed to search archive", e);
            result.put("success", false);
            result.put("message", e.getMessage());
        }
        return result;
    }

    public DeadLetterMessage getArchivedById(String id, String archiveIndex) {
        try {
            String index = archiveIndex != null ? archiveIndex : EsIndexConstants.INDEX_ARCHIVE_PREFIX + "*";
            SearchRequest request = SearchRequest.of(b -> b
                    .index(index)
                    .query(q -> q
                            .term(TermQuery.of(t -> t
                                    .field(EsIndexConstants.FIELD_ID)
                                    .value(FieldValue.of(id))
                            ))
                    )
            );
            SearchResponse<DeadLetterMessage> response = elasticsearchClient.search(request, DeadLetterMessage.class);
            return response.hits().hits().stream()
                    .findFirst()
                    .map(Hit::source)
                    .orElse(null);
        } catch (Exception e) {
            log.error("Failed to get archived message by id: {}", id, e);
            return null;
        }
    }

    public List<Map<String, Object>> listArchiveIndexes(String prefix, Boolean includeStats) {
        List<Map<String, Object>> result = new ArrayList<>();
        try {
            String indexPattern = (prefix != null ? prefix : EsIndexConstants.INDEX_ARCHIVE_PREFIX) + "*";
            var indices = elasticsearchClient.indices().get(b -> b.index(indexPattern));

            for (var entry : indices.result().entrySet()) {
                Map<String, Object> indexInfo = new java.util.HashMap<>();
                indexInfo.put("name", entry.getKey());
                indexInfo.put("health", entry.getValue().health() != null ? entry.getValue().health().jsonValue() : "unknown");
                indexInfo.put("status", entry.getValue().status() != null ? entry.getValue().status().jsonValue() : "unknown");
                indexInfo.put("uuid", entry.getValue().settings().get("index.uuid"));

                if (Boolean.TRUE.equals(includeStats)) {
                    try {
                        var stats = elasticsearchClient.indices().stats(b -> b.index(entry.getKey()));
                        indexInfo.put("docCount", stats.primaries().docs() != null ? stats.primaries().docs().count() : 0);
                        indexInfo.put("sizeInBytes", stats.primaries().store() != null ? stats.primaries().store().sizeInBytes() : 0);
                    } catch (Exception e) {
                        log.warn("Failed to get stats for index: {}", entry.getKey(), e);
                    }
                }
                result.add(indexInfo);
            }
        } catch (Exception e) {
            log.error("Failed to list archive indexes", e);
        }
        return result;
    }

    private Query buildArchiveQuery(DeadLetterQueryDTO query) {
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

        return Query.of(q -> q
                .bool(BoolQuery.of(b -> b.filter(filterClauses)))
        );
    }
}
