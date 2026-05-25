"""构建时间预测模块 - 预测构建时间并模拟优化效果"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from colorama import Fore, Style
from dockerfile_parser import DockerfileParser, LayerInfo, StageInfo
from optimizer import Optimizer, OptimizationSuggestion


@dataclass
class LayerBuildTime:
    layer: LayerInfo
    estimated_seconds: float
    cached_seconds: float
    explanation: str


@dataclass
class BuildTimePrediction:
    total_estimated_seconds: float
    total_cached_seconds: float
    layer_times: List[LayerBuildTime] = field(default_factory=list)
    optimization_impact: Dict[str, float] = field(default_factory=dict)
    parallel_possible: bool = False
    parallel_savings: float = 0.0


class BuildTimePredictor:
    def __init__(self, parser: DockerfileParser, optimizer: Optional[Optimizer] = None):
        self.parser = parser
        self.optimizer = optimizer
        self.original_prediction: Optional[BuildTimePrediction] = None
        self.optimized_prediction: Optional[BuildTimePrediction] = None
        self._predict()

    def _predict(self):
        """执行构建时间预测"""
        self.original_prediction = self._predict_build_time()

        if self.optimizer:
            self._simulate_optimizations()

    def _predict_build_time(self) -> BuildTimePrediction:
        """预测构建时间"""
        prediction = BuildTimePrediction(
            total_estimated_seconds=0.0,
            total_cached_seconds=0.0
        )

        for stage in self.parser.stages:
            for layer in stage.layers:
                layer_time = self._estimate_layer_time(layer)
                prediction.layer_times.append(layer_time)
                prediction.total_estimated_seconds += layer_time.estimated_seconds
                prediction.total_cached_seconds += layer_time.cached_seconds

        prediction.parallel_possible, prediction.parallel_savings = self._assess_parallel_potential()

        return prediction

    def _estimate_layer_time(self, layer: LayerInfo) -> LayerBuildTime:
        """估算单层构建时间（秒）"""
        base_times = {
            'FROM': 5.0,
            'RUN': 30.0,
            'COPY': 10.0,
            'ADD': 15.0,
            'CMD': 0.5,
            'ENTRYPOINT': 0.5,
            'ENV': 0.5,
            'ARG': 0.5,
            'WORKDIR': 0.5,
            'EXPOSE': 0.5,
            'LABEL': 0.5,
            'USER': 0.5,
            'VOLUME': 0.5,
            'HEALTHCHECK': 0.5,
            'SHELL': 0.5,
            'STOPSIGNAL': 0.5,
        }

        base_time = base_times.get(layer.instruction, 1.0)
        multiplier = 1.0
        explanation = f"{layer.instruction} 基础时间"

        if layer.instruction == 'RUN':
            multiplier, explanation = self._calculate_run_multiplier(layer.value)
        elif layer.instruction in ['COPY', 'ADD']:
            multiplier, explanation = self._calculate_copy_multiplier(layer)

        estimated = base_time * multiplier
        cached = 0.5 if layer.instruction in ['FROM', 'RUN', 'COPY', 'ADD'] else 0.1

        return LayerBuildTime(
            layer=layer,
            estimated_seconds=estimated,
            cached_seconds=cached,
            explanation=explanation
        )

    def _calculate_run_multiplier(self, value: str) -> Tuple[float, str]:
        """计算RUN命令的时间乘数"""
        value_lower = value.lower()
        multiplier = 1.0
        factors = []

        if 'apt-get install' in value_lower or 'apt install' in value_lower:
            multiplier *= 2.0
            factors.append("apt包安装")

        if 'pip install' in value_lower:
            multiplier *= 2.5
            factors.append("pip包安装")

        if 'npm install' in value_lower or 'yarn install' in value_lower:
            multiplier *= 4.0
            factors.append("npm/yarn包安装")

        if 'npm run build' in value_lower or 'yarn build' in value_lower:
            multiplier *= 3.0
            factors.append("项目构建")

        if 'make' in value_lower or 'cmake' in value_lower or 'gcc' in value_lower:
            multiplier *= 5.0
            factors.append("编译")

        if 'curl' in value_lower or 'wget' in value_lower:
            multiplier *= 1.5
            factors.append("网络下载")

        if 'apt-get update' in value_lower:
            multiplier *= 1.3
            factors.append("包索引更新")

        explanation = "基础运行" if not factors else ', '.join(factors)
        return multiplier, explanation

    def _calculate_copy_multiplier(self, layer: LayerInfo) -> Tuple[float, str]:
        """计算COPY/ADD命令的时间乘数"""
        multiplier = 1.0
        factors = []

        if layer.context_files:
            file_count = len(layer.context_files)
            if file_count > 10:
                multiplier *= 3.0
                factors.append(f"{file_count}个文件")
            elif file_count > 5:
                multiplier *= 2.0
                factors.append(f"{file_count}个文件")

            for f in layer.context_files:
                if '*' in f:
                    multiplier *= 1.5
                    factors.append("通配符匹配")
                    break

        if layer.cross_stage_dependency:
            multiplier *= 0.8
            factors.append("跨阶段复制(本地)")

        explanation = "文件复制" if not factors else ', '.join(factors)
        return multiplier, explanation

    def _assess_parallel_potential(self) -> Tuple[bool, float]:
        """评估并行构建潜力"""
        if len(self.parser.stages) < 2:
            return False, 0.0

        independent_stages = 0
        sequential_time = 0.0

        for stage in self.parser.stages:
            if not stage.dependent_stages:
                independent_stages += 1
            stage_time = sum(
                self._estimate_layer_time(layer).estimated_seconds
                for layer in stage.layers
            )
            sequential_time += stage_time

        if independent_stages >= 2:
            parallel_time = sequential_time / min(independent_stages, 3)
            savings = sequential_time - parallel_time
            return True, savings

        return False, 0.0

    def _simulate_optimizations(self):
        """模拟优化后的构建时间"""
        if not self.optimizer:
            return

        impact = {}
        total_savings = 0.0

        for suggestion in self.optimizer.suggestions:
            savings = self._calculate_suggestion_savings(suggestion)
            impact[suggestion.title] = savings
            total_savings += savings

        self.original_prediction.optimization_impact = impact

        optimized_total = self.original_prediction.total_estimated_seconds - total_savings
        self.optimized_prediction = BuildTimePrediction(
            total_estimated_seconds=max(optimized_total, self.original_prediction.total_cached_seconds),
            total_cached_seconds=self.original_prediction.total_cached_seconds,
            layer_times=self.original_prediction.layer_times,
            optimization_impact=impact
        )

    def _calculate_suggestion_savings(self, suggestion: OptimizationSuggestion) -> float:
        """计算单个优化建议的时间节省"""
        savings = 0.0

        if '合并' in suggestion.title and 'RUN' in suggestion.title:
            savings = 3.0
        elif '合并' in suggestion.title and 'COPY' in suggestion.title:
            savings = 2.0
        elif '顺序' in suggestion.title or '频率' in suggestion.title:
            savings = 5.0 * (suggestion.cache_improvement or 0.1)
        elif '清理' in suggestion.title:
            savings = 1.0
        elif '多阶段' in suggestion.title:
            savings = 30.0
        elif '共享' in suggestion.title:
            savings = (suggestion.incremental_savings or 0) / (1024 * 1024) * 0.5

        return savings

    @staticmethod
    def format_time(seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        elif seconds < 3600:
            return f"{seconds / 60:.1f} 分钟"
        else:
            return f"{seconds / 3600:.2f} 小时"

    def get_speedup_percentage(self) -> float:
        """获取加速百分比"""
        if not self.original_prediction or not self.optimized_prediction:
            return 0.0

        original = self.original_prediction.total_estimated_seconds
        optimized = self.optimized_prediction.total_estimated_seconds

        if original == 0:
            return 0.0

        return (original - optimized) / original * 100

    def print_time_report(self):
        """打印构建时间预测报告"""
        print("\n" + "=" * 80)
        print("⏱️  构建时间预测")
        print("=" * 80)

        if not self.original_prediction:
            print("无预测数据")
            return

        orig = self.original_prediction

        print(f"\n【原始构建预测】")
        print("-" * 80)
        print(f"   无缓存构建: {self.format_time(orig.total_estimated_seconds)}")
        print(f"   全缓存构建: {self.format_time(orig.total_cached_seconds)}")

        if orig.parallel_possible:
            print(f"   并行构建可节省: {self.format_time(orig.parallel_savings)}")

        print(f"\n【各层耗时明细】")
        print("-" * 80)

        for i, stage in enumerate(self.parser.stages):
            stage_name = stage.name or f"stage-{i}"
            stage_times = [lt for lt in orig.layer_times
                           if lt.layer.stage_index == i]
            stage_total = sum(lt.estimated_seconds for lt in stage_times)

            print(f"\n   阶段 {i}: {stage_name} ({self.format_time(stage_total)})")

            for lt in stage_times:
                layer = lt.layer
                time_str = self.format_time(lt.estimated_seconds)
                print(f"     层 {layer.layer_index:2d} | {layer.instruction:10s} | "
                      f"{time_str:>12s} | {lt.explanation}")

        if self.optimized_prediction and self.original_prediction.optimization_impact:
            print(f"\n【优化效果模拟】")
            print("-" * 80)

            speedup = self.get_speedup_percentage()
            opt = self.optimized_prediction

            print(f"   优化后预计: {self.format_time(opt.total_estimated_seconds)} "
                  f"({Fore.GREEN if speedup > 0 else Fore.RED}+{speedup:.1f}% 加速{Style.RESET_ALL})")

            print(f"\n   各项优化贡献:")
            for title, savings in orig.optimization_impact.items():
                if savings > 0:
                    print(f"     ✓ {title}: 节省 {self.format_time(savings)}")

        print("\n" + "=" * 80)
