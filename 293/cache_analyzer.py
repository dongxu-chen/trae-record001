"""缓存分析模块 - 计算缓存命中概率并分析层依赖关系"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from dockerfile_parser import DockerfileParser, LayerInfo, StageInfo, CrossStageDependency


@dataclass
class CacheAnalysisResult:
    layer: LayerInfo
    cache_hit_probability: float
    cache_break_reasons: List[str] = field(default_factory=list)
    dependencies: List[int] = field(default_factory=list)
    risk_level: str = "low"
    file_churn_weight: float = 0.0
    cross_stage_dependency: Optional[CrossStageDependency] = None
    high_churn_misplaced: bool = False


class CacheAnalyzer:
    def __init__(self, parser: DockerfileParser, context_path: Optional[str] = None):
        self.parser = parser
        self.context_path = context_path or parser.context_path
        self.results: List[CacheAnalysisResult] = []
        self._analyze()

    def _analyze(self):
        for stage in self.parser.stages:
            self._analyze_stage(stage)

    def _analyze_stage(self, stage: StageInfo):
        prev_probability = 1.0
        min_churn_seen_so_far = 1.0

        for layer in stage.layers:
            result = CacheAnalysisResult(
                layer=layer,
                cache_hit_probability=1.0
            )

            result.cache_hit_probability = self._calculate_base_probability(layer)
            result.dependencies = self._find_dependencies(layer, stage.layers)
            result.cross_stage_dependency = layer.cross_stage_dependency
            result.file_churn_weight = self._calculate_file_churn_weight(layer)

            reasons = []

            if layer.cross_stage_dependency:
                dep_stage_name = layer.cross_stage_dependency.from_stage_name
                reasons.append(f"依赖阶段 '{dep_stage_name}' 的构建产物")
                dep_stage_prob = self._get_stage_cache_probability(layer.cross_stage_dependency.from_stage_index)
                result.cache_hit_probability *= dep_stage_prob

            if layer.is_cache_busting and not layer.cross_stage_dependency:
                reasons.append("指令本身会破坏缓存")
                result.cache_hit_probability *= 0.3

            file_churn_risk = self._assess_file_churn_risk(layer)
            if file_churn_risk > 0.5:
                reasons.append(f"上下文文件变更风险高 ({file_churn_risk:.2f})")
                result.cache_hit_probability *= (1 - file_churn_risk * 0.8)

            if result.file_churn_weight > 0 and result.file_churn_weight > min_churn_seen_so_far + 0.2:
                result.high_churn_misplaced = True
                reasons.append(f"高频文件未前置 (当前修改频率: {result.file_churn_weight:.1f})")
                result.cache_hit_probability *= 0.85

            if min_churn_seen_so_far > result.file_churn_weight:
                min_churn_seen_so_far = result.file_churn_weight

            if result.cache_hit_probability > prev_probability:
                result.cache_hit_probability = prev_probability

            if result.cache_hit_probability < 0.3:
                result.risk_level = "high"
            elif result.cache_hit_probability < 0.7:
                result.risk_level = "medium"

            result.cache_break_reasons = reasons
            layer.cache_hit_probability = result.cache_hit_probability
            self.results.append(result)

            prev_probability = result.cache_hit_probability

    def _calculate_base_probability(self, layer: LayerInfo) -> float:
        """计算基础缓存命中概率"""
        base_probs = {
            'FROM': 0.95,
            'RUN': 0.8,
            'COPY': 0.7,
            'ADD': 0.6,
            'CMD': 0.9,
            'ENTRYPOINT': 0.9,
            'ENV': 0.85,
            'ARG': 0.5,
            'WORKDIR': 0.95,
            'EXPOSE': 0.95,
            'LABEL': 0.9,
            'USER': 0.95,
            'VOLUME': 0.95,
            'HEALTHCHECK': 0.9,
            'SHELL': 0.95,
            'STOPSIGNAL': 0.95,
        }

        base_prob = base_probs.get(layer.instruction, 0.7)

        if layer.instruction == 'COPY' or layer.instruction == 'ADD':
            file_count = len(layer.context_files)
            if file_count > 5:
                base_prob *= 0.9
            if file_count > 10:
                base_prob *= 0.8

            if any('*' in f or '?' in f for f in layer.context_files):
                base_prob *= 0.7

        if layer.instruction == 'RUN':
            if self._contains_dynamic_content(layer.value):
                base_prob *= 0.6

            if self._contains_network_requests(layer.value):
                base_prob *= 0.5

        return base_prob

    def _contains_dynamic_content(self, value: str) -> bool:
        """检查是否包含动态内容"""
        dynamic_patterns = [
            r'\$\(.*\)',
            r'`.*`',
            r'curl\s+',
            r'wget\s+',
            r'git\s+clone',
            r'pip\s+install.*--upgrade',
            r'npm\s+install.*latest',
            r'apk\s+add.*--update',
        ]

        for pattern in dynamic_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _contains_network_requests(self, value: str) -> bool:
        """检查是否包含网络请求"""
        network_patterns = [
            r'https?://',
            r'curl\s+',
            r'wget\s+',
            r'git\s+clone',
        ]

        for pattern in network_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _find_dependencies(self, layer: LayerInfo, all_layers: List[LayerInfo]) -> List[int]:
        """查找层依赖关系"""
        dependencies = []

        if layer.instruction in ['COPY', 'ADD']:
            pass

        if layer.instruction == 'RUN':
            for prev in all_layers:
                if prev.layer_index >= layer.layer_index:
                    continue
                if prev.instruction in ['WORKDIR', 'ENV', 'ARG', 'USER']:
                    dependencies.append(prev.layer_index)

        return dependencies

    def _assess_file_churn_risk(self, layer: LayerInfo) -> float:
        """评估文件变更风险"""
        risk_score = 0.0

        if not layer.context_files:
            return risk_score

        for file_pattern in layer.context_files:
            file_risk = self._calculate_file_risk(file_pattern)
            risk_score = max(risk_score, file_risk)

        return min(risk_score, 1.0)

    def _calculate_file_risk(self, file_pattern: str) -> float:
        """计算单个文件的变更风险"""
        if '*' in file_pattern or '?' in file_pattern:
            return 0.8

        high_risk_patterns = [
            'package.json',
            'requirements.txt',
            'pom.xml',
            'build.gradle',
            'Gemfile',
            'go.mod',
            'Cargo.toml',
        ]

        for pattern in high_risk_patterns:
            if pattern.lower() in file_pattern.lower():
                return 0.7

        medium_risk_patterns = [
            '.js', '.ts', '.py', '.java', '.go', '.rs',
            'src/', 'app/', 'lib/',
        ]

        for pattern in medium_risk_patterns:
            if pattern.lower() in file_pattern.lower():
                return 0.5

        return 0.2

    def get_overall_cache_score(self) -> float:
        """获取整体缓存得分"""
        if not self.results:
            return 0.0

        total_prob = 1.0
        for result in self.results:
            total_prob *= result.cache_hit_probability

        return total_prob

    def get_cache_breakers(self) -> List[CacheAnalysisResult]:
        """获取高风险的缓存破坏点"""
        return [r for r in self.results if r.risk_level == "high"]

    def get_results_by_stage(self, stage_index: int) -> List[CacheAnalysisResult]:
        """按阶段获取分析结果"""
        return [r for r in self.results if r.layer.stage_index == stage_index]

    def _calculate_file_churn_weight(self, layer: LayerInfo) -> float:
        """计算文件修改频率权重（0-1，越高表示修改越频繁）"""
        if not layer.file_churn_info:
            return 0.0

        max_churn = max(info.churn_frequency for info in layer.file_churn_info)
        return max_churn

    def _get_stage_cache_probability(self, stage_index: int) -> float:
        """获取指定阶段的缓存概率"""
        if stage_index < 0 or stage_index >= len(self.parser.stages):
            return 0.5

        stage_results = [r for r in self.results if r.layer.stage_index == stage_index]
        if not stage_results:
            return 0.7

        total_prob = 1.0
        for result in stage_results:
            total_prob *= result.cache_hit_probability

        return max(total_prob, 0.3)

    def get_misplaced_high_churn_layers(self) -> List[CacheAnalysisResult]:
        """获取高频文件未前置的层"""
        return [r for r in self.results if r.high_churn_misplaced]

    def get_cross_stage_dependencies(self) -> List[CacheAnalysisResult]:
        """获取所有跨阶段依赖"""
        return [r for r in self.results if r.cross_stage_dependency is not None]

    def print_analysis_report(self):
        """打印分析报告"""
        print("=" * 80)
        print("Dockerfile 缓存分析报告")
        print("=" * 80)

        for i, stage in enumerate(self.parser.stages):
            stage_name = stage.name or f"stage-{i}"
            print(f"\n【阶段 {i}: {stage_name} (基础镜像: {stage.base_image})】")

            if stage.dependent_stages:
                dep_names = [self.parser.stages[idx].name or f"stage-{idx}"
                             for idx in stage.dependent_stages]
                print(f"   依赖阶段: {', '.join(dep_names)}")

            print("-" * 80)

            stage_results = self.get_results_by_stage(i)

            for result in stage_results:
                layer = result.layer
                prob = result.cache_hit_probability
                risk = result.risk_level.upper()

                indicator = "✅" if prob >= 0.7 else ("⚠️" if prob >= 0.3 else "❌")

                churn_info = ""
                if result.file_churn_weight > 0:
                    churn_info = f" | 修改频率: {result.file_churn_weight:.1f}"

                dep_info = ""
                if result.cross_stage_dependency:
                    dep_stage = result.cross_stage_dependency.from_stage_name
                    dep_info = f" | 依赖: {dep_stage}"

                print(f"{indicator} 层 {layer.layer_index:2d} | "
                      f"{layer.instruction:10s} | "
                      f"缓存: {prob:.1%} | "
                      f"风险: {risk:6s}{churn_info}{dep_info}")

                if result.cache_break_reasons:
                    for reason in result.cache_break_reasons:
                        print(f"     → 原因: {reason}")

        misplaced = self.get_misplaced_high_churn_layers()
        if misplaced:
            print("\n" + "-" * 80)
            print(f"⚠️  高频文件顺序问题 ({len(misplaced)} 处):")
            print("-" * 80)
            for result in misplaced:
                layer = result.layer
                stage_name = layer.stage_name or f"stage-{layer.stage_index}"
                print(f"   阶段 '{stage_name}' 层 {layer.layer_index}: 建议将高频文件后置")

        cross_deps = self.get_cross_stage_dependencies()
        if cross_deps:
            print("\n" + "-" * 80)
            print(f"🔗 跨阶段依赖 ({len(cross_deps)} 处):")
            print("-" * 80)
            for result in cross_deps:
                dep = result.cross_stage_dependency
                print(f"   从 '{dep.from_stage_name}' 复制 {dep.source_path} → {dep.dest_path}")

        print("\n" + "=" * 80)
        overall_score = self.get_overall_cache_score()
        print(f"整体缓存得分: {overall_score:.1%}")
        print(f"高风险缓存破坏点: {len(self.get_cache_breakers())} 个")
        print(f"跨阶段依赖数: {len(self.get_cross_stage_dependencies())} 处")
        print("=" * 80)
