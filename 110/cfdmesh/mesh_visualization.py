import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from typing import Dict, Optional
from pathlib import Path

from .mesh_quality import MeshQuality


class MeshVisualizer:
    def __init__(self, original_points, original_cells,
                 optimized_points=None, optimized_cells=None):
        self.original_points = original_points
        self.original_cells = original_cells
        self.optimized_points = optimized_points
        self.optimized_cells = optimized_cells

        self.is_2d = self._detect_2d(original_points)
        self.figsize = (16, 10)

    def _detect_2d(self, points) -> bool:
        if points.shape[1] < 3:
            return True
        z_coords = points[:, 2]
        return np.allclose(z_coords, z_coords[0])

    def generate_comparison_report(self, output_path: str = "mesh_optimization_report.png",
                                    quality_before: Optional[Dict] = None,
                                    quality_after: Optional[Dict] = None):
        fig = plt.figure(figsize=self.figsize)
        gs = GridSpec(3, 4, figure=fig)

        ax1 = fig.add_subplot(gs[0:2, 0:2])
        self._plot_mesh(ax1, self.original_points, self.original_cells, "原始网格")

        ax2 = fig.add_subplot(gs[0:2, 2:4])
        if self.optimized_points is not None:
            self._plot_mesh(ax2, self.optimized_points, self.optimized_cells, "优化后网格")

        ax3 = fig.add_subplot(gs[2, 0])
        self._plot_cell_size_distribution(ax3, "单元尺寸分布")

        if quality_before and quality_after:
            ax4 = fig.add_subplot(gs[2, 1])
            self._plot_quality_comparison(ax4, quality_before, quality_after, "非正交度")

            ax5 = fig.add_subplot(gs[2, 2])
            self._plot_quality_comparison(ax5, quality_before, quality_after, "skewness")

            ax6 = fig.add_subplot(gs[2, 3])
            self._plot_quality_comparison(ax6, quality_before, quality_after, "aspect_ratio")

        plt.tight_layout()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(output_file)

    def _plot_mesh(self, ax, points, cells, title):
        if self.is_2d:
            self._plot_2d_mesh(ax, points, cells)
        else:
            self._plot_3d_mesh(ax, points, cells)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)

    def _plot_2d_mesh(self, ax, points, cells):
        for cell_block in cells:
            cell_type = cell_block.type
            for cell in cell_block.data:
                cell_points = points[cell]
                if cell_type == 'triangle':
                    poly = plt.Polygon(cell_points[:, :2], fill=None, edgecolor='steelblue', linewidth=0.8)
                    ax.add_patch(poly)
                elif cell_type == 'quad':
                    poly = plt.Polygon(cell_points[:, :2], fill=None, edgecolor='steelblue', linewidth=0.8)
                    ax.add_patch(poly)

        ax.scatter(points[:, 0], points[:, 1], s=10, c='red', alpha=0.6, zorder=5)

        all_x = points[:, 0]
        all_y = points[:, 1]
        ax.set_xlim(all_x.min() - 0.1 * (all_x.max() - all_x.min()),
                    all_x.max() + 0.1 * (all_x.max() - all_x.min()))
        ax.set_ylim(all_y.min() - 0.1 * (all_y.max() - all_y.min()),
                    all_y.max() + 0.1 * (all_y.max() - all_y.min()))

    def _plot_3d_mesh(self, ax, points, cells):
        for cell_block in cells:
            cell_type = cell_block.type
            for cell in cell_block.data:
                cell_points = points[cell]
                if cell_type in ['triangle', 'quad']:
                    n = len(cell_points)
                    for i in range(n):
                        p1 = cell_points[i]
                        p2 = cell_points[(i + 1) % n]
                        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='steelblue', linewidth=0.8)
                elif cell_type in ['tetra', 'hexahedron']:
                    for i in range(len(cell)):
                        for j in range(i + 1, len(cell)):
                            p1 = points[cell[i]]
                            p2 = points[cell[j]]
                            ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                                   color='steelblue', linewidth=0.5, alpha=0.7)

        ax.scatter(points[:, 0], points[:, 1], s=8, c='red', alpha=0.5, zorder=5)

    def _plot_cell_size_distribution(self, ax, title):
        quality_orig = MeshQuality(self.original_points, self.original_cells)
        metrics_orig = quality_orig.compute_all_metrics()

        sizes = []
        for cell_type, cell_metrics in metrics_orig.items():
            if quality_orig.is_2d and 'area' in cell_metrics:
                sizes.extend(cell_metrics['area'])
            elif not quality_orig.is_2d and 'volume' in cell_metrics:
                sizes.extend(cell_metrics['volume'])

        sizes = np.array(sizes)
        if len(sizes) > 0:
            ax.hist(sizes, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
            ax.set_xlabel('单元尺寸' if quality_orig.is_2d else '单元体积')
            ax.set_ylabel('频数')
            ax.set_title(title, fontsize=10, fontweight='bold')
            ax.grid(True, alpha=0.3)

    def _plot_quality_comparison(self, ax, quality_before, quality_after, metric_name):
        metric_display = {
            'non_orthogonality': '非正交度',
            'skewness': '歪斜度',
            'aspect_ratio': '长宽比'
        }.get(metric_name, metric_name)

        before_values = []
        after_values = []

        for cell_type, stats in quality_before['statistics'].items():
            if metric_name in stats:
                before_values.append(stats[metric_name]['mean'])

        for cell_type, stats in quality_after['statistics'].items():
            if metric_name in stats:
                after_values.append(stats[metric_name]['mean'])

        if before_values and after_values:
            x = np.arange(len(before_values))
            width = 0.35

            bars1 = ax.bar(x - width/2, before_values, width, label='优化前',
                          color='coral', alpha=0.8)
            bars2 = ax.bar(x + width/2, after_values, width, label='优化后',
                          color='forestgreen', alpha=0.8)

            ax.set_ylabel(metric_display)
            ax.set_title(f'{metric_display}对比', fontsize=10, fontweight='bold')
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3, axis='y')

            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}', ha='center', va='bottom', fontsize=8)
            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    def generate_quality_heatmap(self, output_path: str = "quality_heatmap.png"):
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        quality_orig = MeshQuality(self.original_points, self.original_cells)
        metrics_orig = quality_orig.compute_all_metrics()

        self._plot_heatmap(axes[0], self.original_points, self.original_cells,
                          metrics_orig, quality_orig.is_2d, "原始网格质量")

        if self.optimized_points is not None:
            quality_opt = MeshQuality(self.optimized_points, self.optimized_cells)
            metrics_opt = quality_opt.compute_all_metrics()
            self._plot_heatmap(axes[1], self.optimized_points, self.optimized_cells,
                              metrics_opt, quality_opt.is_2d, "优化后网格质量")

        plt.tight_layout()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        return str(output_file)

    def _plot_heatmap(self, ax, points, cells, metrics, is_2d, title):
        metric_values = []
        cell_centers = []

        for cell_type, cell_metrics in metrics.items():
            if 'non_orthogonality' in cell_metrics:
                metric_values.extend(cell_metrics['non_orthogonality'])
            if 'cell_centers' in cell_metrics:
                cell_centers.extend(cell_metrics['cell_centers'])

        if metric_values and cell_centers:
            cell_centers = np.array(cell_centers)
            metric_values = np.array(metric_values)

            scatter = ax.scatter(cell_centers[:, 0], cell_centers[:, 1],
                               c=metric_values, cmap='RdYlGn_r', s=100, alpha=0.8)
            plt.colorbar(scatter, ax=ax, label='非正交度')

        for cell_block in cells:
            for cell in cell_block.data:
                cell_points = points[cell]
                for i in range(len(cell)):
                    p1 = cell_points[i]
                    p2 = cell_points[(i + 1) % len(cell)]
                    ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                           color='gray', linewidth=0.5, alpha=0.5)

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_aspect('equal')

    def generate_text_summary(self, quality_before: Dict, quality_after: Dict) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("           网格优化前后对比报告")
        lines.append("=" * 70)
        lines.append("")

        lines.append("网格规模变化:")
        lines.append(f"  节点数: {quality_before['num_points']} -> {quality_after['num_points']}")
        lines.append(f"  单元数: {quality_before['num_cells']} -> {quality_after['num_cells']}")
        lines.append("")

        lines.append("质量指标变化:")
        lines.append("-" * 50)

        metric_names = {
            'non_orthogonality': '非正交度',
            'skewness': '歪斜度',
            'aspect_ratio': '长宽比'
        }

        for cell_type in quality_before['statistics']:
            lines.append(f"\n  单元类型: {cell_type}")
            stats_before = quality_before['statistics'][cell_type]
            stats_after = quality_after['statistics'].get(cell_type, {})

            for metric, name in metric_names.items():
                if metric in stats_before and metric in stats_after:
                    mean_before = stats_before[metric]['mean']
                    mean_after = stats_after[metric]['mean']
                    improvement = (mean_before - mean_after) / mean_before * 100 if mean_before > 0 else 0

                    lines.append(f"    {name}: {mean_before:.4f} -> {mean_after:.4f} "
                               f"(改进: {improvement:+.2f}%)")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)
