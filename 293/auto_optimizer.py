"""自动优化Dockerfile生成器 - 一键应用优化建议"""

import os
import re
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from dockerfile_parser import DockerfileParser, LayerInfo, StageInfo
from optimizer import Optimizer, OptimizationSuggestion, OptimizationSeverity


@dataclass
class AppliedOptimization:
    suggestion: OptimizationSuggestion
    original_lines: List[str]
    optimized_lines: List[str]
    line_number_start: int
    line_number_end: int


class DockerfileAutoOptimizer:
    def __init__(self, dockerfile_path: str, parser: DockerfileParser, optimizer: Optimizer):
        self.dockerfile_path = dockerfile_path
        self.parser = parser
        self.optimizer = optimizer
        self.original_content: str = ""
        self.optimized_content: str = ""
        self.applied_optimizations: List[AppliedOptimization] = []
        self._load_original()

    def _load_original(self):
        """加载原始Dockerfile内容"""
        with open(self.dockerfile_path, 'r', encoding='utf-8') as f:
            self.original_content = f.read()

    def apply_optimizations(self, min_severity: OptimizationSeverity = OptimizationSeverity.LOW) -> int:
        """应用优化建议

        Args:
            min_severity: 最小严重程度，只应用高于等于此级别的优化

        Returns:
            应用的优化数量
        """
        lines = self.original_content.split('\n')

        severity_order = [
            OptimizationSeverity.CRITICAL,
            OptimizationSeverity.HIGH,
            OptimizationSeverity.MEDIUM,
            OptimizationSeverity.LOW
        ]
        min_index = severity_order.index(min_severity)

        applicable = [s for s in self.optimizer.suggestions
                      if severity_order.index(s.severity) <= min_index
                      and s.before_code and s.after_code]

        applicable.sort(key=lambda s: severity_order.index(s.severity))

        for suggestion in applicable:
            applied = self._apply_suggestion(lines, suggestion)
            if applied:
                self.applied_optimizations.append(applied)

        self.optimized_content = '\n'.join(lines)
        return len(self.applied_optimizations)

    def _apply_suggestion(self, lines: List[str], suggestion: OptimizationSuggestion) -> Optional[AppliedOptimization]:
        """应用单个优化建议"""
        before_lines = suggestion.before_code.split('\n')

        start_idx = -1
        for i in range(len(lines)):
            match = True
            for j, before_line in enumerate(before_lines):
                if i + j >= len(lines) or lines[i + j].strip() != before_line.strip():
                    match = False
                    break
            if match:
                start_idx = i
                break

        if start_idx == -1:
            return None

        after_lines = suggestion.after_code.split('\n')

        original = lines[start_idx:start_idx + len(before_lines)]

        lines[start_idx:start_idx + len(before_lines)] = after_lines

        return AppliedOptimization(
            suggestion=suggestion,
            original_lines=original,
            optimized_lines=after_lines,
            line_number_start=start_idx + 1,
            line_number_end=start_idx + len(after_lines)
        )

    def save_optimized(self, output_path: Optional[str] = None, backup: bool = True) -> str:
        """保存优化后的Dockerfile

        Args:
            output_path: 输出路径，默认为原路径加 .optimized
            backup: 是否备份原始文件

        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_path = self.dockerfile_path + '.optimized'

        if backup and os.path.exists(self.dockerfile_path) and output_path != self.dockerfile_path:
            backup_path = self.dockerfile_path + '.bak'
            shutil.copy2(self.dockerfile_path, backup_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.optimized_content)

        return output_path

    def get_diff(self) -> str:
        """获取优化前后的差异"""
        diff_lines = []
        diff_lines.append("--- Original Dockerfile")
        diff_lines.append("+++ Optimized Dockerfile")
        diff_lines.append("")

        orig_lines = self.original_content.split('\n')
        opt_lines = self.optimized_content.split('\n')

        for opt in self.applied_optimizations:
            diff_lines.append(f"@@ 第 {opt.line_number_start}-{opt.line_number_end} 行 @@")
            for line in opt.original_lines:
                diff_lines.append(f"- {line}")
            for line in opt.optimized_lines:
                diff_lines.append(f"+ {line}")
            diff_lines.append("")

        return '\n'.join(diff_lines)

    def print_summary(self):
        """打印优化摘要"""
        print("\n" + "=" * 80)
        print("🔧 自动优化摘要")
        print("=" * 80)

        if not self.applied_optimizations:
            print("\n没有应用任何优化")
            return

        print(f"\n成功应用 {len(self.applied_optimizations)} 项优化:")
        print("-" * 80)

        for i, applied in enumerate(self.applied_optimizations, 1):
            s = applied.suggestion
            severity_icon = {
                OptimizationSeverity.CRITICAL: "🔴",
                OptimizationSeverity.HIGH: "🟠",
                OptimizationSeverity.MEDIUM: "🟡",
                OptimizationSeverity.LOW: "🟢"
            }[s.severity]

            print(f"\n{i}. {severity_icon} {s.title}")
            print(f"   位置: 第 {applied.line_number_start}-{applied.line_number_end} 行")

            if s.estimated_savings:
                from size_analyzer import SizeAnalyzer
                print(f"   节省空间: {SizeAnalyzer.format_size(s.estimated_savings)}")

            if s.cache_improvement:
                print(f"   缓存提升: +{s.cache_improvement:.0%}")

        print("\n" + "=" * 80)

    def generate_optimized_content(self) -> str:
        """生成优化后的内容而不修改文件"""
        self.apply_optimizations()
        return self.optimized_content
