package com.dlq.platform.es.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.*;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.json.JsonData;
import com.dlq.platform.common.dto.AlertRuleDTO;
import com.dlq.platform.common.entity.AlertRule;
import com.dlq.platform.common.enums.AlertLevelEnum;
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
public class AlertEsService {

    private final ElasticsearchClient esClient;
    private final ElasticsearchConfig esConfig;

    public void saveAlertRule(AlertRule rule) {
        try {
            if (rule.getId() == null) {
                rule.setId(UUID.randomUUID().toString().replace("-", ""));
            }
            if (rule.getCreateTime() == null) {
                rule.setCreateTime(LocalDateTime.now());
            }
            rule.setUpdateTime(LocalDateTime.now());

            esClient.index(i -> i
                    .index(esConfig.getAlertRuleIndex())
                    .id(rule.getId())
                    .document(rule));
            log.info("保存告警规则成功, id: {}, name: {}", rule.getId(), rule.getName());
        } catch (Exception e) {
            log.error("保存告警规则失败, name: {}", rule.getName(), e);
            throw new RuntimeException("保存告警规则失败", e);
        }
    }

    public AlertRule findAlertRuleById(String id) {
        try {
            GetResponse<AlertRule> response = esClient.get(g -> g
                            .index(esConfig.getAlertRuleIndex())
                            .id(id),
                    AlertRule.class);
            if (response.found()) {
                return response.source();
            }
            return null;
        } catch (Exception e) {
            log.error("查询告警规则失败, id: {}", id, e);
            throw new RuntimeException("查询告警规则失败", e);
        }
    }

    public List<AlertRule> findAllEnabledAlertRules() {
        try {
            SearchResponse<AlertRule> response = esClient.search(s -> s
                            .index(esConfig.getAlertRuleIndex())
                            .size(1000)
                            .query(q -> q
                                    .term(t -> t
                                            .field("enabled")
                                            .value(true))),
                    AlertRule.class);

            return response.hits().hits().stream()
                    .map(Hit::source)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
        } catch (Exception e) {
            log.error("查询启用的告警规则失败", e);
            throw new RuntimeException("查询启用的告警规则失败", e);
        }
    }

    public Map<String, Object> queryAlertRules(AlertRuleDTO queryDTO) {
        try {
            int pageNum = queryDTO.getPageNum() != null ? queryDTO.getPageNum() : 1;
            int pageSize = queryDTO.getPageSize() != null ? queryDTO.getPageSize() : 20;
            int from = (pageNum - 1) * pageSize;

            SearchResponse<AlertRule> response = esClient.search(s -> {
                s.index(esConfig.getAlertRuleIndex())
                        .from(from)
                        .size(pageSize)
                        .sort(so -> so.field(f -> f.field("createTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));

                List<co.elastic.clients.elasticsearch._types.query_dsl.Query> queries = new ArrayList<>();
                if (StringUtils.hasText(queryDTO.getName())) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .match(m -> m.field("name").query(queryDTO.getName()))));
                }
                if (queryDTO.getEnabled() != null) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .term(t -> t.field("enabled").value(queryDTO.getEnabled()))));
                }
                if (queryDTO.getAlertLevel() != null) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .term(t -> t.field("alertLevel").value(queryDTO.getAlertLevel().name()))));
                }
                if (!queries.isEmpty()) {
                    s.query(q -> q.bool(b -> b.must(queries)));
                }
                return s;
            }, AlertRule.class);

            List<AlertRule> list = response.hits().hits().stream()
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
            log.error("查询告警规则列表失败", e);
            throw new RuntimeException("查询告警规则列表失败", e);
        }
    }

    public void deleteAlertRule(String id) {
        try {
            esClient.delete(d -> d
                    .index(esConfig.getAlertRuleIndex())
                    .id(id));
            log.info("删除告警规则成功, id: {}", id);
        } catch (Exception e) {
            log.error("删除告警规则失败, id: {}", id, e);
            throw new RuntimeException("删除告警规则失败", e);
        }
    }

    public void saveAlertHistory(Map<String, Object> alertHistory) {
        try {
            if (alertHistory.get("id") == null) {
                alertHistory.put("id", UUID.randomUUID().toString().replace("-", ""));
            }
            if (alertHistory.get("createTime") == null) {
                alertHistory.put("createTime", LocalDateTime.now());
            }

            String id = (String) alertHistory.get("id");
            esClient.index(i -> i
                    .index(esConfig.getAlertHistoryIndex())
                    .id(id)
                    .document(alertHistory));
        } catch (Exception e) {
            log.error("保存告警历史失败", e);
        }
    }

    public Map<String, Object> queryAlertHistory(String ruleId, AlertLevelEnum level, LocalDateTime startTime, LocalDateTime endTime, int pageNum, int pageSize) {
        try {
            int from = (pageNum - 1) * pageSize;

            SearchResponse<Map> response = esClient.search(s -> {
                s.index(esConfig.getAlertHistoryIndex())
                        .from(from)
                        .size(pageSize)
                        .sort(so -> so.field(f -> f.field("createTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));

                List<co.elastic.clients.elasticsearch._types.query_dsl.Query> queries = new ArrayList<>();
                if (StringUtils.hasText(ruleId)) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .term(t -> t.field("ruleId.keyword").value(ruleId))));
                }
                if (level != null) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .term(t -> t.field("alertLevel").value(level.name()))));
                }
                if (startTime != null) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .range(r -> r
                                    .field("createTime")
                                    .gte(JsonData.of(startTime.toString())))));
                }
                if (endTime != null) {
                    queries.add(co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q -> q
                            .range(r -> r
                                    .field("createTime")
                                    .lte(JsonData.of(endTime.toString())))));
                }
                if (!queries.isEmpty()) {
                    s.query(q -> q.bool(b -> b.must(queries)));
                }
                return s;
            }, Map.class);

            List<Map<String, Object>> list = response.hits().hits().stream()
                    .map(Hit::source)
                    .filter(Objects::nonNull)
                    .map(m -> (Map<String, Object>) m)
                    .collect(Collectors.toList());

            Map<String, Object> result = new HashMap<>();
            result.put("total", response.hits().total() != null ? response.hits().total().value() : 0);
            result.put("list", list);
            result.put("pageNum", pageNum);
            result.put("pageSize", pageSize);
            return result;
        } catch (Exception e) {
            log.error("查询告警历史失败", e);
            throw new RuntimeException("查询告警历史失败", e);
        }
    }

    public boolean isAlertSilenced(String ruleId, String messageKey, int silentMinutes) {
        try {
            LocalDateTime silentTime = LocalDateTime.now().minusMinutes(silentMinutes);

            SearchResponse<Map> response = esClient.search(s -> s
                            .index(esConfig.getAlertHistoryIndex())
                            .size(1)
                            .query(q -> q
                                    .bool(b -> b
                                            .must(List.of(
                                                    co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q1 -> q1
                                                            .term(t -> t.field("ruleId.keyword").value(ruleId))),
                                                    co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q2 -> q2
                                                            .term(t -> t.field("messageKey.keyword").value(messageKey))),
                                                    co.elastic.clients.elasticsearch._types.query_dsl.Query.of(q3 -> q3
                                                            .range(r -> r
                                                                    .field("createTime")
                                                                    .gte(JsonData.of(silentTime.toString()))))
                                            )))),
                    Map.class);

            return response.hits().total() != null && response.hits().total().value() > 0;
        } catch (Exception e) {
            log.error("检查告警静默状态失败", e);
            return false;
        }
    }
}
