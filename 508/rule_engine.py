import logging
import operator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from query_analyzer import CauseCategory, DiagnosisResult
from es_collector import SlowQuery

logger = logging.getLogger(__name__)


class RuleOperator(Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    CONTAINS = "contains"


OP_MAP: Dict[RuleOperator, Callable] = {
    RuleOperator.GT: operator.gt,
    RuleOperator.GTE: operator.ge,
    RuleOperator.LT: operator.lt,
    RuleOperator.LTE: operator.le,
    RuleOperator.EQ: operator.eq,
    RuleOperator.NEQ: operator.ne,
    RuleOperator.IN: lambda a, b: a in b,
    RuleOperator.CONTAINS: lambda a, b: b in a,
}


@dataclass
class RuleCondition:
    field: str
    operator: RuleOperator
    value: Any

    def evaluate(self, context: Dict[str, Any]) -> bool:
        actual = self._resolve_field(context)
        if actual is None:
            return False
        try:
            return OP_MAP[self.operator](actual, self.value)
        except (TypeError, KeyError) as e:
            logger.debug("Rule condition evaluation failed: %s", e)
            return False

    def _resolve_field(self, context: Dict[str, Any]) -> Any:
        parts = self.field.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current


@dataclass
class Rule:
    rule_id: str
    name: str
    description: str = ""
    conditions: List[RuleCondition] = field(default_factory=list)
    cause: Optional[CauseCategory] = None
    suggestion: str = ""
    severity_override: Optional[str] = None
    enabled: bool = True

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if not self.enabled:
            return False
        return all(cond.evaluate(context) for cond in self.conditions)


@dataclass
class RuleMatch:
    rule: Rule
    context: Dict[str, Any]


class RuleEngine:
    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()

    def add_rule(self, rule: Rule):
        self.rules.append(rule)
        logger.info("Added rule: %s (%s)", rule.name, rule.rule_id)

    def remove_rule(self, rule_id: str):
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

    def evaluate(self, slow_query: SlowQuery, diagnosis: DiagnosisResult) -> List[RuleMatch]:
        context = self._build_context(slow_query, diagnosis)
        matches = []
        for rule in self.rules:
            if rule.evaluate(context):
                matches.append(RuleMatch(rule=rule, context=context))
                if rule.cause and rule.cause not in diagnosis.causes:
                    diagnosis.causes.append(rule.cause)
                if rule.suggestion and rule.suggestion not in diagnosis.suggestions:
                    diagnosis.suggestions.append(rule.suggestion)
                if rule.severity_override:
                    diagnosis.severity = rule.severity_override
        return matches

    def _build_context(self, sq: SlowQuery, diag: DiagnosisResult) -> Dict[str, Any]:
        return {
            "query": {
                "response_time_ms": sq.response_time_ms,
                "from_offset": sq.from_offset,
                "size": sq.size,
                "total_offset": sq.from_offset + sq.size,
                "hits_total": sq.hits_total,
                "total_shards": sq.total_shards,
                "successful_shards": sq.successful_shards,
                "search_type": sq.search_type,
                "cache_hit": sq.cache_hit,
                "index_name": sq.index_name,
            },
            "diagnosis": {
                "causes": [c.value for c in diag.causes],
                "cause_count": len(diag.causes),
                "severity": diag.severity,
            },
        }

    def _load_default_rules(self):
        self.add_rule(Rule(
            rule_id="RULE_DEEP_PAG_001",
            name="深度分页告警",
            description="查询偏移量超过10000的深分页",
            conditions=[
                RuleCondition(field="query.total_offset", operator=RuleOperator.GT, value=10000),
            ],
            cause=CauseCategory.DEEP_PAGINATION,
            suggestion="检测到深度分页(偏移>10000)，强烈建议切换到 search_after 分页方式。"
                       "ES 在 from+size 超过 index.max_result_window 时会拒绝查询，"
                       "即使未超过，深分页也会导致协调节点需要合并大量数据。",
            severity_override="critical",
        ))

        self.add_rule(Rule(
            rule_id="RULE_DEEP_PAG_002",
            name="中等深度分页",
            description="查询偏移量超过5000但未超过10000",
            conditions=[
                RuleCondition(field="query.total_offset", operator=RuleOperator.GT, value=5000),
                RuleCondition(field="query.total_offset", operator=RuleOperator.LTE, value=10000),
            ],
            cause=CauseCategory.DEEP_PAGINATION,
            suggestion="检测到中等深度分页(偏移5000-10000)，建议使用 search_after 分页。"
                       "当 from 值较大时，ES 需要在每个分片上取 from+size 条数据再合并排序。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_SLOW_001",
            name="极慢查询",
            description="响应时间超过30秒的查询",
            conditions=[
                RuleCondition(field="query.response_time_ms", operator=RuleOperator.GT, value=30000),
            ],
            severity_override="critical",
            suggestion="查询响应超过30秒，属于极慢查询。请优先排查: (1) 是否有深分页; "
                       "(2) 是否有大范围聚合; (3) 集群资源是否充足; (4) 是否有热点分片。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_SLOW_002",
            name="慢查询",
            description="响应时间超过10秒的查询",
            conditions=[
                RuleCondition(field="query.response_time_ms", operator=RuleOperator.GT, value=10000),
                RuleCondition(field="query.response_time_ms", operator=RuleOperator.LTE, value=30000),
            ],
            severity_override="high",
            suggestion="查询响应超过10秒，建议: (1) 添加更精确的过滤条件; "
                       "(2) 使用 _source 过滤减少返回字段; (3) 评估是否需要全部结果。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_SHARD_001",
            name="分片数过多",
            description="查询涉及超过100个分片",
            conditions=[
                RuleCondition(field="query.total_shards", operator=RuleOperator.GT, value=100),
            ],
            cause=CauseCategory.TOO_MANY_SHARDS,
            suggestion="查询涉及超过100个分片，协调节点开销巨大。"
                       "建议: (1) 使用 routing 减少分片扫描; (2) 合并小索引; "
                       "(3) 使用索引模板控制分片数; (4) 使用 shrink API 合并分片。",
            severity_override="high",
        ))

        self.add_rule(Rule(
            rule_id="RULE_CACHE_001",
            name="缓存未命中",
            description="查询未命中请求缓存",
            conditions=[
                RuleCondition(field="query.cache_hit", operator=RuleOperator.EQ, value=False),
            ],
            cause=CauseCategory.CACHE_MISS,
            suggestion="查询未命中请求缓存。检查: (1) 是否使用了 now/rand 等不可缓存函数; "
                       "(2) 索引是否开启了 request cache; (3) 查询的 size 是否为0(仅聚合); "
                       "(4) 是否频繁刷新导致缓存失效。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_LARGE_RESULT_001",
            name="大结果集",
            description="单次查询返回超过1000条文档",
            conditions=[
                RuleCondition(field="query.size", operator=RuleOperator.GT, value=1000),
            ],
            suggestion="单次查询请求 {query.size} 条文档，大量结果集传输消耗带宽。"
                       "建议: (1) 减小 size 参数; (2) 使用 scroll API 批量获取; "
                       "(3) 使用 _source 过滤只返回必要字段。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_MULTI_CAUSE_001",
            name="多原因慢查询",
            description="同时存在多个慢查询原因",
            conditions=[
                RuleCondition(field="diagnosis.cause_count", operator=RuleOperator.GTE, value=3),
            ],
            severity_override="critical",
            suggestion="检测到3个及以上慢查询原因叠加，性能问题严重。"
                       "建议按优先级依次优化: 深分页 > 脚本查询 > 模糊/通配符/前缀 > 聚合 > 缓存。",
        ))

        self.add_rule(Rule(
            rule_id="RULE_PREFIX_001",
            name="前缀匹配查询",
            description="查询中包含 prefix 子句",
            conditions=[
                RuleCondition(field="diagnosis.causes", operator=RuleOperator.CONTAINS, value="prefix_query"),
            ],
            cause=CauseCategory.PREFIX_QUERY,
            suggestion="检测到 prefix 查询，prefix query 在未优化字段上执行倒排词典扫描。"
                       "强烈建议改用 edge_ngram 索引方案: "
                       "(1) 添加 edge_ngram 子字段映射; "
                       "(2) 查询改为 match on edge_ngram 字段; "
                       "(3) 性能可提升数十倍。",
        ))
