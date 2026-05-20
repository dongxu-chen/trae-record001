import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class QualityReport:
    DEFAULT_THRESHOLDS = {
        "non_orthogonality": 70.0,
        "skewness": 50.0,
        "aspect_ratio": 10.0
    }

    def __init__(self, mesh_info: Dict, quality_metrics: Dict, statistics: Dict,
                 histograms: Optional[Dict] = None, is_2d: bool = False):
        self.mesh_info = mesh_info
        self.quality_metrics = quality_metrics
        self.statistics = statistics
        self.histograms = histograms or {}
        self.is_2d = is_2d

    def _generate_histogram_ascii(self, counts: np.ndarray, bin_edges: np.ndarray,
                                   total: int, bar_width: int = 40) -> str:
        lines = []
        max_count = counts.max() if len(counts) > 0 else 1

        for i, count in enumerate(counts):
            bar_len = int(count / max_count * bar_width)
            bar = '█' * bar_len
            percent = (count / total * 100) if total > 0 else 0
            lines.append(
                f"  [{bin_edges[i]:>7.2f}, {bin_edges[i+1]:>7.2f}) "
                f"{bar} {count:>5} ({percent:>5.1f}%)"
            )
        return '\n'.join(lines)

    def generate_text_report(self, thresholds: Optional[Dict] = None) -> str:
        if thresholds is None:
            thresholds = self.DEFAULT_THRESHOLDS

        lines = []
        lines.append("=" * 75)
        lines.append("              CFD 网格质量报告")
        lines.append("=" * 75)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"文件路径: {self.mesh_info.get('file_path', 'N/A')}")
        lines.append(f"网格类型: {'二维 (2D)' if self.is_2d else '三维 (3D)'}")
        lines.append("")

        lines.append("-" * 75)
        lines.append("1. 网格基本信息")
        lines.append("-" * 75)
        lines.append(f"  节点数量: {self.mesh_info.get('num_points', 0)}")
        lines.append(f"  单元总数: {self.mesh_info.get('total_cells', 0)}")
        lines.append("  单元类型统计:")
        for cell_type, count in self.mesh_info.get("cell_types", {}).items():
            lines.append(f"    - {cell_type}: {count} 个")
        lines.append("")

        lines.append("-" * 75)
        lines.append("2. 网格质量统计")
        lines.append("-" * 75)

        metric_names = {
            "area": "面积",
            "volume": "体积",
            "non_orthogonality": "非正交度 (°)",
            "skewness": "歪斜度 (%)",
            "aspect_ratio": "长宽比"
        }

        for cell_type, stats in self.statistics.items():
            lines.append(f"\n  单元类型: {cell_type}")
            lines.append(f"  {'-' * 65}")
            for metric_key, metric_name in metric_names.items():
                if metric_key in stats:
                    s = stats[metric_key]
                    lines.append(f"  {metric_name}:")
                    lines.append(f"    最小值: {s['min']:.6f}")
                    lines.append(f"    最大值: {s['max']:.6f}")
                    lines.append(f"    平均值: {s['mean']:.6f}")
                    lines.append(f"    标准差: {s['std']:.6f}")
                    lines.append(f"    中位数: {s['median']:.6f}")
                    if 'sum' in s:
                        if metric_key == 'area':
                            lines.append(f"    总面积: {s['sum']:.6f}")
                        elif metric_key == 'volume':
                            lines.append(f"    总体积: {s['sum']:.6f}")

                    if metric_key in thresholds and metric_key in self.quality_metrics.get(cell_type, {}):
                        values = self.quality_metrics[cell_type][metric_key]
                        bad_count = np.sum(values > thresholds[metric_key])
                        bad_percent = (bad_count / len(values)) * 100
                        lines.append(
                            f"    超过阈值 ({thresholds[metric_key]}): "
                            f"{bad_count} 个 ({bad_percent:.2f}%)"
                        )
                    lines.append("")

        if self.histograms:
            lines.append("-" * 75)
            lines.append("3. 质量指标分布直方图")
            lines.append("-" * 75)

            hist_names = {
                "area": "面积分布",
                "volume": "体积分布",
                "non_orthogonality": "非正交度分布 (°)",
                "skewness": "歪斜度分布 (%)",
                "aspect_ratio": "长宽比分布"
            }

            for metric_key, hist_data in self.histograms.items():
                if metric_key in hist_names:
                    lines.append(f"\n  {hist_names[metric_key]}:")
                    lines.append(f"  {'-' * 65}")
                    hist_str = self._generate_histogram_ascii(
                        hist_data["counts"],
                        hist_data["bin_edges"],
                        hist_data["total"]
                    )
                    lines.append(hist_str)
                    lines.append("")

        lines.append("-" * 75)
        lines.append("4. 整体质量评估")
        lines.append("-" * 75)
        overall_quality = self._assess_overall_quality(thresholds)
        lines.append(f"  整体质量评级: {overall_quality}")
        lines.append("")

        lines.append("-" * 75)
        lines.append("5. 改进建议")
        lines.append("-" * 75)
        for suggestion in self._generate_suggestions(thresholds):
            lines.append(f"  - {suggestion}")
        lines.append("")

        lines.append("=" * 75)
        lines.append("报告结束")
        lines.append("=" * 75)

        return '\n'.join(lines)

    def save_report(self, output_path: str, thresholds: Optional[Dict] = None) -> None:
        report_text = self.generate_text_report(thresholds)
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report_text, encoding='utf-8')

    def _assess_overall_quality(self, thresholds: Dict) -> str:
        bad_total = 0
        total_cells = 0

        for cell_type, metrics in self.quality_metrics.items():
            for metric_key, values in metrics.items():
                if metric_key == "cell_centers" or metric_key in ["area", "volume"]:
                    continue
                if metric_key in thresholds:
                    bad_total += np.sum(values > thresholds[metric_key])
                    total_cells += len(values)

        if total_cells == 0:
            return "无法评估"

        bad_ratio = bad_total / total_cells

        if bad_ratio < 0.01:
            return "优秀 (A) ★★★★★"
        elif bad_ratio < 0.05:
            return "良好 (B) ★★★★☆"
        elif bad_ratio < 0.15:
            return "合格 (C) ★★★☆☆"
        elif bad_ratio < 0.30:
            return "较差 (D) ★★☆☆☆"
        else:
            return "不合格 (F) ★☆☆☆☆"

    def _generate_suggestions(self, thresholds: Dict) -> list:
        suggestions = []

        for cell_type, metrics in self.quality_metrics.items():
            for metric_key, values in metrics.items():
                if metric_key == "cell_centers" or metric_key in ["area", "volume"]:
                    continue
                if metric_key in thresholds:
                    bad_ratio = np.sum(values > thresholds[metric_key]) / len(values)
                    if bad_ratio > 0.05:
                        if metric_key == "non_orthogonality":
                            suggestions.append(
                                f"{cell_type} 单元非正交度问题较严重 ({bad_ratio * 100:.1f}%)，"
                                f"建议进行光顺处理或局部重构"
                            )
                        elif metric_key == "skewness":
                            suggestions.append(
                                f"{cell_type} 单元歪斜度问题较严重 ({bad_ratio * 100:.1f}%)，"
                                f"建议优化网格拓扑结构"
                            )
                        elif metric_key == "aspect_ratio":
                            suggestions.append(
                                f"{cell_type} 单元长宽比过大 ({bad_ratio * 100:.1f}%)，"
                                f"建议调整局部网格尺寸"
                            )

        if not suggestions:
            suggestions.append("网格质量良好，无需特殊处理")

        return suggestions

    def export_csv(self, output_path: str) -> None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write("cell_type,cell_index,")
            if self.is_2d:
                f.write("area,")
            else:
                f.write("volume,")
            f.write("non_orthogonality,skewness,aspect_ratio\n")

            for cell_type, metrics in self.quality_metrics.items():
                num_cells = len(metrics.get("non_orthogonality", []))
                for i in range(num_cells):
                    non_orth = metrics["non_orthogonality"][i] if "non_orthogonality" in metrics else ""
                    skew = metrics["skewness"][i] if "skewness" in metrics else ""
                    aspect = metrics["aspect_ratio"][i] if "aspect_ratio" in metrics else ""

                    if self.is_2d:
                        area = metrics["area"][i] if "area" in metrics else ""
                        f.write(f"{cell_type},{i},{area},{non_orth},{skew},{aspect}\n")
                    else:
                        volume = metrics["volume"][i] if "volume" in metrics else ""
                        f.write(f"{cell_type},{i},{volume},{non_orth},{skew},{aspect}\n")

    def export_histogram_csv(self, output_path: str) -> None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        hist_names = {
            "area": "面积",
            "volume": "体积",
            "non_orthogonality": "非正交度",
            "skewness": "歪斜度",
            "aspect_ratio": "长宽比"
        }

        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write("metric,bin_start,bin_end,count,percentage\n")
            for metric_key, hist_data in self.histograms.items():
                name = hist_names.get(metric_key, metric_key)
                total = hist_data["total"]
                for i in range(len(hist_data["counts"])):
                    count = hist_data["counts"][i]
                    percent = (count / total * 100) if total > 0 else 0
                    f.write(
                        f"{name},{hist_data['bin_edges'][i]:.6f},"
                        f"{hist_data['bin_edges'][i+1]:.6f},{count},{percent:.2f}\n"
                    )
