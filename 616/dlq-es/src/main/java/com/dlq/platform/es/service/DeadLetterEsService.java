package com.dlq.platform.es.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.*;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.config.ElasticsearchConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterEsService {

    private final ElasticsearchClient esClient;
    private final ElasticsearchConfig esConfig;

    public void save(DeadLetterMessage message) {
        try {
            esClient.index(i -> i
                    .index(esConfig.getDeadLetterIndex())
                    .id(message.getId())
                    .document(message));
            log.debug("保存死信消息成功, id: {}", message.getId());
        } catch (Exception e) {
            log.error("保存死信消息失败, id: {}", message.getId(), e);
            throw new RuntimeException("保存死信消息失败", e);
        }
    }

    public void saveBatch(List<DeadLetterMessage> messages) {
        if (messages == null || messages.isEmpty()) {
            return;
        }
        try {
            List<BulkOperation> operations = messages.stream()
                    .map(msg -> BulkOperation.of(b -> b
                            .index(i -> i
                                    .index(esConfig.getDeadLetterIndex())
                                    .id(msg.getId())
                                    .document(msg))))
                    .collect(Collectors.toList());

            BulkResponse response = esClient.bulk(b -> b.operations(operations));
            if (response.errors()) {
                log.error("批量保存死信消息存在错误, errors: {}", response.items().stream()
                        .filter(item -> item.error() != null)
                        .map(item -> item.error().reason())
                        .collect(Collectors.toList()));
            }
            log.info("批量保存死信消息完成, 总数: {}, 成功: {}",
                    messages.size(),
                    messages.size() - (int) response.items().stream().filter(item -> item.error() != null).count());
        } catch (Exception e) {
            log.error("批量保存死信消息失败", e);
            throw new RuntimeException("批量保存死信消息失败", e);
        }
    }

    public DeadLetterMessage findById(String id) {
        try {
            GetResponse<DeadLetterMessage> response = esClient.get(g -> g
                            .index(esConfig.getDeadLetterIndex())
                            .id(id),
                    DeadLetterMessage.class);
            if (response.found()) {
                return response.source();
            }
            return null;
        } catch (Exception e) {
            log.error("查询死信消息失败, id: {}", id, e);
            throw new RuntimeException("查询死信消息失败", e);
        }
    }

    public List<DeadLetterMessage> findByIds(List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return Collections.emptyList();
        }
        try {
            MgetResponse<DeadLetterMessage> response = esClient.mget(m -> m
                            .index(esConfig.getDeadLetterIndex())
                            .ids(ids),
                    DeadLetterMessage.class);
            return response.docs().stream()
                    .filter(doc -> doc.result().found())
                    .map(doc -> doc.result().source())
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("批量查询死信消息失败", e);
            throw new RuntimeException("批量查询死信消息失败", e);
        }
    }

    public Map<String, Object> query(DeadLetterQueryDTO queryDTO) {
        try {
            int pageNum = queryDTO.getPageNum() != null ? queryDTO.getPageNum() : 1;
            int pageSize = queryDTO.getPageSize() != null ? queryDTO.getPageSize() : 20;
            int from = (pageNum - 1) * pageSize;

            SearchResponse<DeadLetterMessage> response = esClient.search(s -> {
                s.index(esConfig.getDeadLetterIndex())
                        .from(from)
                        .size(pageSize)
                        .sort(so -> so.field(f -> f.field("createTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));

                buildQuery(s, queryDTO);
                return s;
            }, DeadLetterMessage.class);

            List<DeadLetterMessage> list = response.hits().hits().stream()
                    .map(Hit::source)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());

            Map<String, Object> result = new HashMap<>();
            result.put("total", response.hits().total() != null ? response.hits().total().value() : 0);
            result.put("list", list);
            result.put("pageNum", pageNum);
            result.put("pageSize", pageSize);
            return result;
        } catch (Exception e) {
            log.error("查询死信消息列表失败", e);
            throw new RuntimeException("查询死信消息列表失败", e);
        }
    }

    public List<DeadLetterMessage> queryForList(DeadLetterQueryDTO queryDTO) {
        try {
            SearchResponse<DeadLetterMessage> response = esClient.search(s -> {
                s.index(esConfig.getDeadLetterIndex())
                        .size(10000)
                        .sort(so -> so.field(f -> f.field("createTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));
                buildQuery(s, queryDTO);
                return s;
            }, DeadLetterMessage.class);

            return response.hits().hits().stream()
                    .map(Hit::source)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("查询死信消息列表失败", e);
            throw new RuntimeException("查询死信消息列表失败", e);
        }
    }

    public void updateStatus(String id, ProcessStatusEnum status) {
        try {
            Map<String, Object> doc = new HashMap<>();
            doc.put("processStatus", status);
            doc.put("updateTime", LocalDateTime.now());

            esClient.update(u -> u
                            .index(esConfig.getDeadLetterIndex())
                            .id(id)
                            .doc(doc),
                    DeadLetterMessage.class);
            log.debug("更新死信消息状态成功, id: {}, status: {}", id, status);
        } catch (Exception e) {
            log.error("更新死信消息状态失败, id: {}", id, e);
            throw new RuntimeException("更新死信消息状态失败", e);
        }
    }

    public void updateStatusBatch(List<String> ids, ProcessStatusEnum status) {
        if (ids == null || ids.isEmpty()) {
            return;
        }
        try {
            Map<String, Object> doc = new HashMap<>();
            doc.put("processStatus", status);
            doc.put("updateTime", LocalDateTime.now());

            List<BulkOperation> operations = ids.stream()
                    .map(id -> BulkOperation.of(b -> b
                            .update(u -> u
                                    .index(esConfig.getDeadLetterIndex())
                                    .id(id)
                                    .action(a -> a.doc(doc)))))
                    .collect(Collectors.toList());

            esClient.bulk(b -> b.operations(operations));
            log.info("批量更新死信消息状态完成, 总数: {}, status: {}", ids.size(), status);
        } catch (Exception e) {
            log.error("批量更新死信消息状态失败", e);
            throw new RuntimeException("批量更新死信消息状态失败", e);
        }
    }

    public void deleteById(String id) {
        try {
            esClient.delete(d -> d
                    .index(esConfig.getDeadLetterIndex())
                    .id(id));
            log.debug("删除死信消息成功, id: {}", id);
        } catch (Exception e) {
            log.error("删除死信消息失败, id: {}", id, e);
            throw new RuntimeException("删除死信消息失败", e);
        }
    }

    public void deleteByIds(List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return;
        }
        try {
            List<BulkOperation> operations = ids.stream()
                    .map(id -> BulkOperation.of(b -> b
                            .delete(d -> d
                                    .index(esConfig.getDeadLetterIndex())
                                    .id(id))))
                    .collect(Collectors.toList());

            esClient.bulk(b -> b.operations(operations));
            log.info("批量删除死信消息完成, 总数: {}", ids.size());
        } catch (Exception e) {
            log.error("批量删除死信消息失败", e);
            throw new RuntimeException("批量删除死信消息失败", e);
        }
    }

    public Map<String, Object> getStatistics() {
        try {
            Map<String, Object> stats = new HashMap<>();

            SearchResponse<DeadLetterMessage> allResponse = esClient.search(s -> s
                            .index(esConfig.getDeadLetterIndex())
                            .size(0)
                            .aggregations("statusGroup", a -> a
                                    .terms(t -> t.field("processStatus.keyword"))),
                    DeadLetterMessage.class);

            long total = allResponse.hits().total() != null ? allResponse.hits().total().value() : 0;
            stats.put("totalCount", total);

            Map<String, Long> statusCount = new HashMap<>();
            if (allResponse.aggregations() != null) {
                allResponse.aggregations().get("statusGroup").sterms().buckets().array().forEach(bucket -> {
                    statusCount.put(bucket.key().stringValue(), bucket.docCount());
                });
            }
            stats.put("statusDistribution", statusCount);

            LocalDateTime todayStart = LocalDateTime.now().toLocalDate().atStartOfDay();
            SearchResponse<DeadLetterMessage> todayResponse = esClient.search(s -> s
                            .index(esConfig.getDeadLetterIndex())
                            .size(0)
                            .query(q -> q
                                    .range(r -> r
                                            .field("createTime")
                                            .gte(JsonData.of(todayStart.toString())))),
                    DeadLetterMessage.class);
            long todayCount = todayResponse.hits().total() != null ? todayResponse.hits().total().value() : 0;
            stats.put("todayNewCount", todayCount);

            return stats;
        } catch (Exception e) {
            log.error("获取统计信息失败", e);
            throw new RuntimeException("获取统计信息失败", e);
        }
    }

    public boolean existsByMessageId(String messageId) {
        try {
            SearchResponse<DeadLetterMessage> response = esClient.search(s -> s
                            .index(esConfig.getDeadLetterIndex())
                            .size(0)
                            .query(q -> q
                                    .term(t -> t
                                            .field("messageId.keyword")
                                            .value(messageId))),
                    DeadLetterMessage.class);
            return response.hits().total() != null && response.hits().total().value() > 0;
        } catch (Exception e) {
            log.error("检查消息是否存在失败, messageId: {}", messageId, e);
            return false;
        }
    }

    private void buildQuery(SearchRequest.Builder s, DeadLetterQueryDTO queryDTO) {
        List<co.elastic.clients.elasticsearch._types.query_dsl.Query> queries = new ArrayList<>();

        if (queryDTO.getId() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("id").value(queryDTO.getId()))));
        }
        if (queryDTO.getMqType() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("mqType").value(queryDTO.getMqType().name()))));
        }
        if (StringUtils.hasText(queryDTO.getTopic())) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .match(m -> m.field("topic").query(queryDTO.getTopic()))));
        }
        if (StringUtils.hasText(queryDTO.getQueueName())) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .match(m -> m.field("queueName").query(queryDTO.getQueueName()))));
        }
        if (StringUtils.hasText(queryDTO.getMessageId())) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("messageId.keyword").value(queryDTO.getMessageId()))));
        }
        if (queryDTO.getDeadReasonType() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("deadReasonType").value(queryDTO.getDeadReasonType().name()))));
        }
        if (queryDTO.getProcessStatus() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("processStatus").value(queryDTO.getProcessStatus().getCode()))));
        }
        if (queryDTO.getStartTime() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .range(r -> r
                            .field("createTime")
                            .gte(JsonData.of(queryDTO.getStartTime().toString())))));
        }
        if (queryDTO.getEndTime() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .range(r -> r
                            .field("createTime")
                            .lte(JsonData.of(queryDTO.getEndTime().toString())))));
        }

        if (!queries.isEmpty()) {
            s.query(q -> q.bool(b -> b.must(queries)));
        }
    }
}
