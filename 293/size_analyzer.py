"""层大小分析模块 - 分析各层大小并提供优化建议"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from dockerfile_parser import DockerfileParser, LayerInfo, StageInfo


@dataclass
class LayerSizeAnalysis:
    layer: LayerInfo
    estimated_size: int
    size_percentage: float
    cumulative_size: int
    category: str
    size_warning: bool = False


class SizeAnalyzer:
    def __init__(self, parser: DockerfileParser):
        self.parser = parser
        self.analysis_results: List[LayerSizeAnalysis] = []
        self._analyze()

    def _analyze(self):
        for stage in self.parser.stages:
            self._analyze_stage(stage)

    def _analyze_stage(self, stage: StageInfo):
        total_size = sum(layer.estimated_size for layer in stage.layers)
        cumulative = 0

        for layer in stage.layers:
            cumulative += layer.estimated_size
            percentage = (layer.estimated_size / total_size * 100) if total_size > 0 else 0

            category = self._categorize_layer(layer)
            warning = self._check_size_warning(layer, percentage)

            self.analysis_results.append(LayerSizeAnalysis(
                layer=layer,
                estimated_size=layer.estimated_size,
                size_percentage=percentage,
                cumulative_size=cumulative,
                category=category,
                size_warning=warning
            ))

    def _categorize_layer(self, layer: LayerInfo) -> str:
        """对层进行分类"""
        categories = {
            'FROM': '基础镜像',
            'RUN': '执行命令',
            'COPY': '文件复制',
            'ADD': '文件添加',
            'CMD': '启动命令',
            'ENTRYPOINT': '入口点',
            'ENV': '环境变量',
            'ARG': '构建参数',
            'WORKDIR': '工作目录',
            'EXPOSE': '端口暴露',
            'LABEL': '标签',
            'USER': '用户设置',
            'VOLUME': '卷',
            'HEALTHCHECK': '健康检查',
            'SHELL': 'Shell设置',
            'STOPSIGNAL': '停止信号',
        }

        return categories.get(layer.instruction, '其他')

    def _check_size_warning(self, layer: LayerInfo, percentage: float) -> bool:
        """检查是否需要发出大小警告"""
        if percentage > 30:
            return True

        if layer.instruction == 'RUN' and layer.estimated_size > 100 * 1024 * 1024:
            if self._contains_package_install(layer.value):
                return True

        return False

    def _contains_package_install(self, value: str) -> bool:
        """检查是否包含包安装"""
        package_patterns = [
            r'apt-get install',
            r'yum install',
            r'pip install',
            r'npm install',
            r'gem install',
        ]

        for pattern in package_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def get_total_size(self, stage_index: Optional[int] = None) -> int:
        """获取总大小"""
        if stage_index is not None:
            return sum(r.estimated_size for r in self.analysis_results
                       if r.layer.stage_index == stage_index)
        return sum(r.estimated_size for r in self.analysis_results)

    def get_largest_layers(self, stage_index: Optional[int] = None, limit: int = 5) -> List[LayerSizeAnalysis]:
        """获取最大的几层"""
        results = self.analysis_results
        if stage_index is not None:
            results = [r for r in results if r.layer.stage_index == stage_index]

        return sorted(results, key=lambda r: r.estimated_size, reverse=True)[:limit]

    def get_size_by_category(self, stage_index: Optional[int] = None) -> Dict[str, int]:
        """按类别获取大小统计"""
        results = self.analysis_results
        if stage_index is not None:
            results = [r for r in results if r.layer.stage_index == stage_index]

        categories: Dict[str, int] = {}
        for result in results:
            categories[result.category] = categories.get(result.category, 0) + result.estimated_size

        return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))

    def get_size_warnings(self) -> List[LayerSizeAnalysis]:
        """获取大小警告"""
        return [r for r in self.analysis_results if r.size_warning]

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """格式化大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def print_size_report(self):
        """打印大小分析报告"""
        print("\n" + "=" * 80)
        print("Dockerfile 镜像大小分析")
        print("=" * 80)

        for i, stage in enumerate(self.parser.stages):
            stage_name = stage.name or f"stage-{i}"
            stage_size = self.get_total_size(i)

            print(f"\n【阶段 {i}: {stage_name}】")
            print("-" * 80)

            stage_results = [r for r in self.analysis_results if r.layer.stage_index == i]

            for result in stage_results:
                layer = result.layer
                size_str = self.format_size(result.estimated_size)
                indicator = " ⚠️" if result.size_warning else ""

                print(f"层 {layer.layer_index:2d} | "
                      f"{layer.instruction:10s} | "
                      f"{size_str:>10s} | "
                      f"{result.size_percentage:5.1f}% | "
                      f"{result.category}{indicator}")

            print(f"\n阶段总大小: {self.format_size(stage_size)}")

        print("\n" + "-" * 80)
        print("按类别统计:")
        print("-" * 80)

        category_sizes = self.get_size_by_category()
        total_size = self.get_total_size()

        for category, size in category_sizes.items():
            percentage = (size / total_size * 100) if total_size > 0 else 0
            print(f"{category:15s} | {self.format_size(size):>10s} | {percentage:5.1f}%")

        largest = self.get_largest_layers(limit=3)
        if largest:
            print("\n" + "-" * 80)
            print("最大的层:")
            print("-" * 80)
            for result in largest:
                layer = result.layer
                print(f"层 {layer.layer_index} ({layer.instruction}): "
                      f"{self.format_size(result.estimated_size)}")

        warnings = self.get_size_warnings()
        if warnings:
            print("\n" + "-" * 80)
            print(f"⚠️  大小警告 ({len(warnings)} 项):")
            print("-" * 80)
            for warning in warnings:
                layer = warning.layer
                print(f"层 {layer.layer_index}: {layer.instruction} - "
                      f"{self.format_size(warning.estimated_size)} "
                      f"(占 {warning.size_percentage:.1f}%)")

        print("\n" + "=" * 80)
        print(f"预估总镜像大小: {self.format_size(total_size)}")
        print("=" * 80)
