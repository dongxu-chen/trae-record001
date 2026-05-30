import copy
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from query_analyzer import CauseCategory, DiagnosisResult
from es_collector import SlowQuery

logger = logging.getLogger(__name__)


@dataclass
class IndexAdjustment:
    adjustment_id: str
    name: str
    description: str = ""
    target_causes: List[CauseCategory] = field(default_factory=list)
    settings_changes: Dict[str, Any] = field(default_factory=dict)
    mapping_changes: Dict[str, Any] = field(default_factory=dict)
    estimated_impact: str = ""
    risk_level: str = "low"
    prerequisites: List[str] = field(default_factory=list)
    rollback_steps: List[str] = field(default_factory=list)


@dataclass
class DryRunResult:
    adjustment: IndexAdjustment
    applicable: bool = False
    match_reason: str = ""
    estimated_improvement_pct: float = 0.0
    before_snapshot: Dict[str, Any] = field(default_factory=dict)
    after_simulation: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    simulation_steps: List[str] = field(default_factory=list)


class DryRunEngine:
    def __init__(self):
        self.adjustments = self._build_default_adjustments()

    def evaluate(self, diagnosis: DiagnosisResult,
                 index_settings: Optional[Dict[str, Any]] = None,
                 index_mapping: Optional[Dict[str, Any]] = None) -> List[DryRunResult]:
        results = []
        for adj in self.adjustments:
            result = self._evaluate_adjustment(adj, diagnosis, index_settings, index_mapping)
            results.append(result)
        return results

    def generate_report(self, results: List[DryRunResult]) -> str:
        applicable = [r for r in results if r.applicable]
        lines = [
            "=" * 70,
            "演练模式 (DRY-RUN) 报告 - 索引调整影响评估",
            "=" * 70,
            f"共评估 {len(results)} 项调整方案，其中 {len(applicable)} 项适用",
            "",
        ]

        if not applicable:
            lines.append("当前无适用的索引调整方案。")
            return "\n".join(lines)

        for i, r in enumerate(applicable, 1):
            lines.extend([
                f"--- 方案 {i}: {r.adjustment.name} ---",
                f"适用原因: {r.match_reason}",
                f"风险等级: {r.adjustment.risk_level}",
                f"预估提升: {r.estimated_improvement_pct:.0f}%",
                f"说明: {r.adjustment.description}",
                "",
                "模拟执行步骤:",
            ])
            for step in r.simulation_steps:
                lines.append(f"  → {step}")

            if r.warnings:
                lines.append("")
                lines.append("⚠ 注意事项:")
                for w in r.warnings:
                    lines.append(f"  ⚠ {w}")

            lines.extend([
                "",
                "索引设置变更:",
                f"  {json.dumps(r.adjustment.settings_changes, indent=2, ensure_ascii=False)}",
                "",
                "映射变更:",
                f"  {json.dumps(r.adjustment.mapping_changes, indent=2, ensure_ascii=False)}",
                "",
                "前置条件:",
            ])
            for pre in r.adjustment.prerequisites:
                lines.append(f"  * {pre}")

            lines.extend(["", "回滚步骤:"])
            for rb in r.adjustment.rollback_steps:
                lines.append(f"  ← {rb}")

            lines.append("")

        lines.extend([
            "=" * 70,
            "⚠ 以上为模拟评估结果，未实际修改任何索引。",
            "确认方案后请手动执行或使用 --apply 参数执行。",
            "=" * 70,
        ])
        return "\n".join(lines)

    def _evaluate_adjustment(self, adj: IndexAdjustment, diagnosis: DiagnosisResult,
                             index_settings: Optional[Dict[str, Any]],
                             index_mapping: Optional[Dict[str, Any]]) -> DryRunResult:
        result = DryRunResult(adjustment=adj)

        matched_causes = set(adj.target_causes) & set(diagnosis.causes)
        if not matched_causes:
            result.applicable = False
            result.match_reason = f"当前诊断原因 {diagnosis.causes} 与此方案目标原因 {adj.target_causes} 无交集"
            return result

        result.applicable = True
        result.match_reason = f"匹配原因: {', '.join(c.value for c in matched_causes)}"

        sq = diagnosis.slow_query
        result.before_snapshot = {
            "index": sq.index_name,
            "response_time_ms": sq.response_time_ms,
            "total_shards": sq.total_shards,
            "from_offset": sq.from_offset,
            "size": sq.size,
            "hits_total": sq.hits_total,
            "cache_hit": sq.cache_hit,
        }

        improvement = 0.0
        simulation_steps = []
        warnings = []

        if CauseCategory.DEEP_PAGINATION in matched_causes:
            improvement += 40.0
            simulation_steps.append("模拟: 将 from/size 分页替换为 search_after 游标分页")
            simulation_steps.append("模拟: 移除 from 参数，改用 sort 值游标定位")
            simulation_steps.append("模拟: 协调节点不再需要合并 from×shards 条排序值")
            simulation_steps.append(f"模拟: 内存开销从 O(from × shards) 降至 O(size × shards)")
            if sq.search_type == "dfs_query_then_fetch":
                improvement += 15.0
                simulation_steps.append("模拟: DFS 阶段额外开销一并消除")
                warnings.append("当前使用 dfs_query_then_fetch，切换 search_after 后不再需要 DFS 阶段")

        if CauseCategory.PREFIX_QUERY in matched_causes or CauseCategory.WILDCARD_QUERY in matched_causes:
            improvement += 50.0
            simulation_steps.append("模拟: 为字段添加 edge_ngram 子字段映射")
            simulation_steps.append("模拟: 创建 edge_ngram analyzer (min_gram=2, max_gram=20)")
            simulation_steps.append("模拟: 对新字段执行 update_by_query 重新索引")
            simulation_steps.append("模拟: 查询从 prefix/wildcard 改为 match on edge_ngram 字段")
            simulation_steps.append("模拟: 查询退化为精确 token 匹配 O(1)，不再扫描词典")
            warnings.append("edge_ngram 需要重建索引(_reindex 或 update_by_query)，对大数据量索引耗时较长")
            warnings.append("edge_ngram 会增加索引体积(约为原始 text 索引的 3-5 倍)，请确认磁盘空间充足")
            if index_mapping:
                has_text_fields = self._has_text_fields(index_mapping)
                if has_text_fields:
                    simulation_steps.append("模拟: 检测到现有 text 字段，可添加 multi-field 子字段无需新建索引")

        if CauseCategory.FUZZY_QUERY in matched_causes:
            improvement += 35.0
            simulation_steps.append("模拟: 为模糊搜索字段添加 edge_ngram 或 completion 子字段")
            simulation_steps.append("模拟: fuzzy 查询 → match 查询 on edge_ngram 字段")
            warnings.append("edge_ngram 替代 fuzzy 后搜索行为会变化: 前缀匹配 vs 编辑距离匹配，需业务确认")

        if CauseCategory.CACHE_MISS in matched_causes:
            improvement += 20.0
            simulation_steps.append("模拟: 开启 index.requests.cache.enable=true")
            simulation_steps.append("模拟: 对 size=0 的聚合查询启用请求缓存")
            simulation_steps.append("模拟: 移除查询中的 now/random 等不可缓存函数")
            if index_settings:
                cache_enabled = (index_settings
                                 .get("index", {})
                                 .get("requests", {})
                                 .get("cache", {})
                                 .get("enable", "未检测"))
                if cache_enabled is True:
                    warnings.append("当前索引已开启请求缓存，缓存未命中可能由查询参数动态性导致")
                elif cache_enabled is False:
                    simulation_steps.append("检测到 index.requests.cache.enable=false，模拟开启为 true")

        if CauseCategory.TOO_MANY_SHARDS in matched_causes:
            improvement += 25.0
            simulation_steps.append(f"模拟: 当前 {sq.total_shards} 个分片，使用 shrink API 合并")
            target_shards = max(1, sq.total_shards // 4)
            simulation_steps.append(f"模拟: 目标分片数 {target_shards} (原 {sq.total_shards})")
            simulation_steps.append("模拟: 执行 shrink 前需将索引设为只读")
            simulation_steps.append("模拟: shrink 完成后恢复读写")
            warnings.append("shrink 操作需要先将索引设为只读，期间写入会被拒绝")
            warnings.append("shrink 后索引 UUID 变更，需更新引用")

        if CauseCategory.HIGH_CARDINALITY_AGG in matched_causes:
            improvement += 30.0
            simulation_steps.append("模拟: 在 terms 聚合外层包裹 sampler 聚合")
            simulation_steps.append("模拟: sampler 先采样 top N 文档再执行聚合")
            simulation_steps.append("模拟: 对高频聚合字段创建 rollup job 预聚合")
            warnings.append("sampler 聚合结果为近似值，可能不适用于精确统计场景")

        if CauseCategory.SCRIPT_QUERY in matched_causes:
            improvement += 45.0
            simulation_steps.append("模拟: 分析脚本逻辑，尝试替换为 function_score + field_value_factor")
            simulation_steps.append("模拟: 或使用 runtime fields 在索引时预计算")
            warnings.append("脚本替换方案需根据具体脚本逻辑定制，无法通用自动替换")

        result.estimated_improvement_pct = min(improvement, 90.0)
        result.simulation_steps = simulation_steps
        result.warnings = warnings

        estimated_time = sq.response_time_ms * (1.0 - result.estimated_improvement_pct / 100.0)
        result.after_simulation = {
            "estimated_response_time_ms": round(estimated_time, 1),
            "estimated_improvement_pct": result.estimated_improvement_pct,
        }

        return result

    @staticmethod
    def _has_text_fields(mapping: Dict[str, Any]) -> bool:
        props = mapping.get("mappings", {}).get("properties", {})
        for field_def in props.values():
            if isinstance(field_def, dict) and field_def.get("type") == "text":
                return True
        return False

    def _build_default_adjustments(self) -> List[IndexAdjustment]:
        return [
            IndexAdjustment(
                adjustment_id="DRY_DEEP_PAG_001",
                name="深分页优化: 切换 search_after",
                description="将 from/size 分页替换为 search_after 游标分页，消除深分页开销",
                target_causes=[CauseCategory.DEEP_PAGINATION],
                settings_changes={
                    "说明": "search_after 不需要修改索引设置，只需调整查询方式",
                    "查询模板": {
                        "query": {"match": {"field": "value"}},
                        "size": 50,
                        "sort": [{"field": {"order": "asc"}}, {"_id": {"order": "asc"}}],
                        "search_after": ["上一页最后一条的 sort 值"],
                    },
                },
                estimated_impact="高 (40-55% 响应时间降低)",
                risk_level="low",
                prerequisites=["确认业务可以接受无法跳页的限制", "查询必须包含 sort 子句"],
                rollback_steps=["恢复使用 from/size 分页参数"],
            ),
            IndexAdjustment(
                adjustment_id="DRY_PREFIX_NGRAM_001",
                name="前缀/通配符优化: edge_ngram 索引方案",
                description="为需要前缀搜索的字段添加 edge_ngram 子字段，将 prefix/wildcard 查询改为 match 查询",
                target_causes=[CauseCategory.PREFIX_QUERY, CauseCategory.WILDCARD_QUERY],
                mapping_changes={
                    "示例映射": {
                        "properties": {
                            "title": {
                                "type": "text",
                                "fields": {
                                    "edge_ngram": {
                                        "type": "text",
                                        "analyzer": "edge_ngram_analyzer",
                                    }
                                },
                            }
                        }
                    },
                    "analyzer 定义": {
                        "edge_ngram_analyzer": {
                            "tokenizer": "edge_ngram_tokenizer",
                        },
                        "edge_ngram_tokenizer": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 20,
                            "token_chars": ["letter", "digit"],
                        },
                    },
                },
                estimated_impact="极高 (50-70% 响应时间降低)",
                risk_level="medium",
                prerequisites=[
                    "确认磁盘空间充足 (索引体积预计增长 3-5 倍该字段部分)",
                    "安排低峰期执行 update_by_query 重新索引",
                    "业务方确认前缀匹配的搜索行为符合需求",
                ],
                rollback_steps=[
                    "移除 edge_ngram 子字段映射",
                    "恢复使用 prefix/wildcard 查询",
                    "如已 reindex，删除新索引恢复旧索引",
                ],
            ),
            IndexAdjustment(
                adjustment_id="DRY_FUZZY_NGRAM_001",
                name="模糊查询优化: edge_ngram 替代方案",
                description="使用 edge_ngram 或 completion suggester 替代 fuzzy 查询",
                target_causes=[CauseCategory.FUZZY_QUERY],
                mapping_changes={
                    "edge_ngram 方案": "同 DRY_PREFIX_NGRAM_001 的映射变更",
                    "completion suggester 方案": {
                        "properties": {
                            "title_suggest": {
                                "type": "completion",
                                "contexts": [{"name": "category", "type": "category"}],
                            }
                        }
                    },
                },
                estimated_impact="高 (35-50% 响应时间降低)",
                risk_level="medium",
                prerequisites=[
                    "确认业务可以接受从编辑距离匹配改为前缀匹配的行为变化",
                    "completion suggester 仅适用于搜索建议场景",
                ],
                rollback_steps=["恢复 fuzzy 查询", "移除 edge_ngram/completion 子字段"],
            ),
            IndexAdjustment(
                adjustment_id="DRY_CACHE_001",
                name="缓存优化: 开启请求缓存",
                description="开启索引请求缓存并优化查询以提升缓存命中率",
                target_causes=[CauseCategory.CACHE_MISS],
                settings_changes={
                    "index.requests.cache.enable": True,
                    "index.requests.cache.expire": "6h",
                },
                estimated_impact="中 (20-40% 响应时间降低，仅对重复查询有效)",
                risk_level="low",
                prerequisites=[
                    "确认查询模式包含大量重复查询",
                    "评估缓存内存占用对节点的影响",
                ],
                rollback_steps=["设置 index.requests.cache.enable=false", "清除缓存: POST /index/_cache/clear"],
            ),
            IndexAdjustment(
                adjustment_id="DRY_SHARD_001",
                name="分片优化: shrink API 合并分片",
                description="使用 shrink API 将过多小分片合并为较大分片，减少协调开销",
                target_causes=[CauseCategory.TOO_MANY_SHARDS],
                settings_changes={
                    "步骤": [
                        "1. PUT /index/_settings {\"index.blocks.write\": true}",
                        "2. POST /index/_shrink/target_index {\"settings\": {\"index.number_of_replicas\": 1, \"index.number_of_shards\": 10}}",
                        "3. POST /target_index/_settings {\"index.blocks.write\": false, \"index.blocks.read_only\": false}",
                    ],
                },
                estimated_impact="中 (25-35% 响应时间降低)",
                risk_level="medium",
                prerequisites=[
                    "当前分片数必须是目标分片数的整数倍",
                    "索引必须先设为只读",
                    "所有分片必须在同一节点上(shrink 前提条件)",
                    "安排低峰期执行，shrink 期间索引只读",
                ],
                rollback_steps=[
                    "删除 shrink 后的索引",
                    "恢复原索引读写: PUT /index/_settings {\"index.blocks.write\": false}",
                ],
            ),
            IndexAdjustment(
                adjustment_id="DRY_AGG_001",
                name="聚合优化: sampler 采样 + rollup 预聚合",
                description="使用 sampler 聚合先采样再聚合，或创建 rollup job 预聚合",
                target_causes=[CauseCategory.HIGH_CARDINALITY_AGG],
                settings_changes={
                    "rollup job 示例": {
                        "index_pattern": "index-*",
                        "rollup_index": "index-rollup",
                        "cron": "0 */6 * * *",
                        "groups": {
                            "terms": {"fields": {"brand.keyword": {"terms": {"size": 100}}}},
                        },
                    },
                },
                estimated_impact="中 (30-40% 响应时间降低，结果为近似值)",
                risk_level="low",
                prerequisites=[
                    "业务方可接受聚合结果为采样近似值",
                    "如使用 rollup，需要额外存储空间",
                ],
                rollback_steps=["移除 sampler 聚合包装", "删除 rollup 索引和 job"],
            ),
            IndexAdjustment(
                adjustment_id="DRY_SCRIPT_001",
                name="脚本优化: 替换为 function_score/runtime fields",
                description="分析脚本逻辑并替换为 function_score 或 runtime fields",
                target_causes=[CauseCategory.SCRIPT_QUERY],
                settings_changes={
                    "function_score 替代示例": {
                        "query": {"match": {"field": "value"}},
                        "functions": [{"field_value_factor": {"field": "popularity", "factor": 1.2, "modifier": "sqrt"}}],
                    },
                    "runtime fields 替代示例": {
                        "mappings": {
                            "runtime": {
                                "computed_score": {"type": "double", "script": "emit(doc['field1'].value * doc['field2'].value)"},
                            }
                        }
                    },
                },
                estimated_impact="高 (45-60% 响应时间降低)",
                risk_level="medium",
                prerequisites=["需要根据具体脚本逻辑定制替换方案", "runtime fields 在 7.12+ 版本支持"],
                rollback_steps=["恢复使用 script 查询", "移除 runtime fields 定义"],
            ),
        ]
