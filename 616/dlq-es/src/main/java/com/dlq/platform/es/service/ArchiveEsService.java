package com.dlq.platform.es.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.*;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.ArchiveRequest;
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
public class ArchiveEsService {

    private final ElasticsearchClient esClient;
    private final ElasticsearchConfig esConfig;

    public void archive(DeadLetterMessage message) {
        try {
            message.setProcessStatus(ProcessStatusEnum.ARCHIVED);
            message.setUpdateTime(LocalDateTime.now());

            esClient.index(i -> i
                    .index(esConfig.getArchiveIndex())
                    .id(message.getId())
                    .document(message));

            esClient.delete(d -> d
                    .index(esConfig.getDeadLetterIndex())
                    .id(message.getId()));

            log.info("归档死信消息成功, id: {}", message.getId());
        } catch (Exception e) {
            log.error("归档死信消息失败, id: {}", message.getId(), e);
            throw new RuntimeException("归档死信消息失败", e);
        }
    }

    public void archiveBatch(List<DeadLetterMessage> messages) {
        if (messages == null || messages.isEmpty()) {
            return;
        }
        try {
            LocalDateTime now = LocalDateTime.now();
            List<BulkOperation> archiveOperations = new ArrayList<>();
            List<BulkOperation> deleteOperations = new ArrayList<>();

            for (DeadLetterMessage message : messages) {
                message.setProcessStatus(ProcessStatusEnum.ARCHIVED);
                message.setUpdateTime(now);

                archiveOperations.add(BulkOperation.of(b -> b
                        .index(i -> i
                                .index(esConfig.getArchiveIndex())
                                .id(message.getId())
                                .document(message))));

                deleteOperations.add(BulkOperation.of(b -> b
                        .delete(d -> d
                                .index(esConfig.getDeadLetterIndex())
                                .id(message.getId()))));
            }

            List<BulkOperation> allOperations = new ArrayList<>();
            allOperations.addAll(archiveOperations);
            allOperations.addAll(deleteOperations);

            BulkResponse response = esClient.bulk(b -> b.operations(allOperations));
            if (response.errors()) {
                log.error("批量归档存在错误");
            }

            log.info("批量归档完成, 总数: {}", messages.size());
        } catch (Exception e) {
            log.error("批量归档失败", e);
            throw new RuntimeException("批量归档失败", e);
        }
    }

    public List<DeadLetterMessage> findArchiveByIds(List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return Collections.emptyList();
        }
        try {
            MgetResponse<DeadLetterMessage> response = esClient.mget(m -> m
                            .index(esConfig.getArchiveIndex())
                            .ids(ids),
                    DeadLetterMessage.class);
            return response.docs().stream()
                    .filter(doc -> doc.result().found())
                    .map(doc -> doc.result().source())
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("查询归档消息失败", e);
            throw new RuntimeException("查询归档消息失败", e);
        }
    }

    public Map<String, Object> queryArchive(ArchiveRequest request, int pageNum, int pageSize) {
        try {
            int from = (pageNum - 1) * pageSize;

            SearchResponse<DeadLetterMessage> response = esClient.search(s -> {
                s.index(esConfig.getArchiveIndex())
                        .from(from)
                        .size(pageSize)
                        .sort(so -> so.field(f -> f.field("createTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));
                buildArchiveQuery(s, request);
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
            log.error("查询归档列表失败", e);
            throw new RuntimeException("查询归档列表失败", e);
        }
    }

    public List<DeadLetterMessage> findExpiredArchive(int days) {
        try {
            LocalDateTime expireTime = LocalDateTime.now().minusDays(days);

            SearchResponse<DeadLetterMessage> response = esClient.search(s -> s
                            .index(esConfig.getArchiveIndex())
                            .size(10000)
                            .query(q -> q
                                    .range(r -> r
                                            .field("createTime")
                                            .lte(JsonData.of(expireTime.toString())))),
                    DeadLetterMessage.class);

            return response.hits().hits().stream()
                    .map(Hit::source)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("查询过期归档消息失败", e);
            throw new RuntimeException("查询过期归档消息失败", e);
        }
    }

    public void restore(List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return;
        }
        try {
            List<DeadLetterMessage> messages = findArchiveByIds(ids);
            if (messages.isEmpty()) {
                return;
            }

            LocalDateTime now = LocalDateTime.now();
            List<BulkOperation> restoreOperations = new ArrayList<>();
            List<BulkOperation> deleteOperations = new ArrayList<>();

            for (DeadLetterMessage message : messages) {
                message.setProcessStatus(ProcessStatusEnum.PENDING);
                message.setUpdateTime(now);

                restoreOperations.add(BulkOperation.of(b -> b
                        .index(i -> i
                                .index(esConfig.getDeadLetterIndex())
                                .id(message.getId())
                                .document(message))));

                deleteOperations.add(BulkOperation.of(b -> b
                        .delete(d -> d
                                .index(esConfig.getArchiveIndex())
                                .id(message.getId()))));
            }

            List<BulkOperation> allOperations = new ArrayList<>();
            allOperations.addAll(restoreOperations);
            allOperations.addAll(deleteOperations);

            esClient.bulk(b -> b.operations(allOperations));
            log.info("归档恢复完成, 总数: {}", ids.size());
        } catch (Exception e) {
            log.error("归档恢复失败", e);
            throw new RuntimeException("归档恢复失败", e);
        }
    }

    public void deleteExpiredArchive(int days) {
        try {
            LocalDateTime expireTime = LocalDateTime.now().minusDays(days);

            esClient.deleteByQuery(d -> d
                    .index(esConfig.getArchiveIndex())
                    .query(q -> q
                            .range(r -> r
                                    .field("createTime")
                                    .lte(JsonData.of(expireTime.toString())))));

            log.info("清理过期归档数据完成, 保留天数: {}", days);
        } catch (Exception e) {
            log.error("清理过期归档数据失败", e);
            throw new RuntimeException("清理过期归档数据失败", e);
        }
    }

    private void buildArchiveQuery(SearchRequest.Builder s, ArchiveRequest request) {
        List<co.elastic.clients.elasticsearch._types.query_dsl.Query> queries = new ArrayList<>();

        if (request.getMessageIds() != null && !request.getMessageIds().isEmpty()) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .terms(t -> t.field("id.keyword").terms(te -> te.value(request.getMessageIds().stream()
                            .map(co.elastic.clients.json.JsonData::of)
                            .collect(Collectors.toList()))))));
        }
        if (request.getMqType() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("mqType").value(request.getMqType().name()))));
        }
        if (StringUtils.hasText(request.getTopic())) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .match(m -> m.field("topic").query(request.getTopic()))));
        }
        if (request.getProcessStatus() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .term(t -> t.field("processStatus").value(request.getProcessStatus().getCode()))));
        }
        if (request.getStartTime() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .range(r -> r
                            .field("createTime")
                            .gte(JsonData.of(request.getStartTime().toString())))));
        }
        if (request.getEndTime() != null) {
            queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                    .range(r -> r
                            .field("createTime")
                            .lte(JsonData.of(request.getEndTime().toString())))));
        }

        if (!queries.isEmpty()) {
            s.query(q -> q.bool(b -> b.must(queries)));
        }
    }
}
