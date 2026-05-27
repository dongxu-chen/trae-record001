"""
变化检测报告生成模块
输出HTML格式报告，包含变化区域影像和统计图表
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from semantic_change import SEMANTIC_CHANGE_TYPES, SEMANTIC_CHANGE_COLORS
from config import CLASS_NAMES, CLASS_COLORS

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ChangeDetectionReport:
    def __init__(self, output_dir: str, project_name: str = "遥感图像变化检测"):
        self.output_dir = output_dir
        self.project_name = project_name
        self.report_dir = os.path.join(output_dir, 'report')
        self.images_dir = os.path.join(self.report_dir, 'images')
        os.makedirs(self.images_dir, exist_ok=True)

        self.report_data = {
            'project_name': project_name,
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sections': []
        }

    def add_section(self, title: str, content: str, image_paths: List[str] = None):
        section = {
            'title': title,
            'content': content,
            'images': image_paths or []
        }
        self.report_data['sections'].append(section)

    def save_figure(self, fig, filename: str) -> str:
        filepath = os.path.join(self.images_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return f'images/{filename}'

    def generate_overview_chart(self, area_stats: Dict, class_stats: Dict) -> str:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        categories = list(class_stats.keys())
        areas = [class_stats[cat]['area'] for cat in categories]
        ratios = [class_stats[cat]['ratio'] * 100 for cat in categories]

        colors = [tuple(np.array(CLASS_COLORS[i]) / 255.0) for i in range(len(categories))]

        axes[0].barh(categories, areas, color=colors[:len(categories)])
        axes[0].set_xlabel('面积')
        axes[0].set_title('各类变化区域面积统计')
        axes[0].grid(True, alpha=0.3, axis='x')

        axes[1].pie(ratios, labels=categories, colors=colors[:len(categories)],
                    autopct='%1.1f%%', startangle=90)
        axes[1].set_title('各类变化区域面积占比')

        plt.suptitle('变化检测总体统计', fontsize=14)
        plt.tight_layout()

        return self.save_figure(fig, 'overview_chart.png')

    def generate_semantic_chart(self, semantic_summary: Dict) -> str:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        types = SEMANTIC_CHANGE_TYPES[1:]
        counts = [semantic_summary['by_type_count'][t] for t in types]
        areas = [semantic_summary['by_type_area'][t] for t in types]

        colors = [tuple(np.array(SEMANTIC_CHANGE_COLORS[i+1]) / 255.0) for i in range(len(types))]

        axes[0].barh(types, counts, color=colors)
        axes[0].set_xlabel('区域数量')
        axes[0].set_title('语义变化类型数量统计')
        axes[0].grid(True, alpha=0.3, axis='x')

        axes[1].barh(types, areas, color=colors)
        axes[1].set_xlabel('总面积')
        axes[1].set_title('语义变化类型面积统计')
        axes[1].grid(True, alpha=0.3, axis='x')

        plt.suptitle('语义变化检测分析', fontsize=14)
        plt.tight_layout()

        return self.save_figure(fig, 'semantic_chart.png')

    def generate_temporal_chart(self, temporal_summary: Dict) -> str:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        dates = temporal_summary.get('dates', [])
        magnitudes = temporal_summary.get('change_magnitude_over_time', [])

        if dates and magnitudes:
            axes[0, 0].plot(dates[1:], magnitudes, marker='o', linewidth=2, color='red')
            axes[0, 0].set_xlabel('时相')
            axes[0, 0].set_ylabel('变化幅度')
            axes[0, 0].set_title('整体变化幅度时序曲线')
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].tick_params(axis='x', rotation=45)

        stats = ['ndvi_increasing_pixels', 'ndvi_decreasing_pixels', 'ndvi_stable_pixels']
        labels = ['NDVI增加', 'NDVI减少', 'NDVI稳定']
        values = [temporal_summary.get(s, 0) for s in stats]
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']

        axes[0, 1].pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[0, 1].set_title('NDVI变化趋势分布')

        b_stats = ['brightness_increasing_pixels', 'brightness_decreasing_pixels', 'brightness_stable_pixels']
        b_labels = ['亮度增加', '亮度减少', '亮度稳定']
        b_values = [temporal_summary.get(s, 0) for s in b_stats]

        axes[1, 0].pie(b_values, labels=b_labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[1, 0].set_title('亮度变化趋势分布')

        axes[1, 1].text(0.1, 0.9, f'总时相数: {temporal_summary.get("num_time_points", 0)}', transform=axes[1, 1].transAxes, fontsize=12)
        axes[1, 1].text(0.1, 0.8, f'发生变化像素: {temporal_summary.get("pixels_with_changes", 0):,}', transform=axes[1, 1].transAxes, fontsize=12)
        axes[1, 1].text(0.1, 0.7, f'平均变化强度: {temporal_summary.get("mean_change_intensity", 0):.4f}', transform=axes[1, 1].transAxes, fontsize=12)
        axes[1, 1].text(0.1, 0.6, f'最大变化频率: {temporal_summary.get("max_change_frequency", 0)}', transform=axes[1, 1].transAxes, fontsize=12)
        axes[1, 1].set_title('时序分析摘要')
        axes[1, 1].axis('off')

        plt.tight_layout()
        return self.save_figure(fig, 'temporal_chart.png')

    def generate_region_chips(self, image1: np.ndarray, image2: np.ndarray,
                               binary_map: np.ndarray, semantic_map: np.ndarray,
                               regions: List, num_regions: int = 10) -> List[str]:
        chip_paths = []

        regions_sorted = sorted(regions, key=lambda r: r.area_pixels, reverse=True)[:num_regions]

        for idx, region in enumerate(regions_sorted):
            min_row, min_col, max_row, max_col = region.bbox

            padding = 20
            min_row_p = max(0, min_row - padding)
            max_row_p = min(image1.shape[1], max_row + padding)
            min_col_p = max(0, min_col - padding)
            max_col_p = min(image1.shape[2], max_col + padding)

            fig, axes = plt.subplots(2, 2, figsize=(10, 10))

            if image1.shape[0] >= 3:
                img1_chip = np.transpose(image1[:3, min_row_p:max_row_p, min_col_p:max_col_p], (1, 2, 0))
                img2_chip = np.transpose(image2[:3, min_row_p:max_row_p, min_col_p:max_col_p], (1, 2, 0))
            else:
                img1_chip = image1[0, min_row_p:max_row_p, min_col_p:max_col_p]
                img2_chip = image2[0, min_row_p:max_row_p, min_col_p:max_col_p]

            axes[0, 0].imshow(img1_chip)
            axes[0, 0].set_title('时相1')
            axes[0, 0].axis('off')

            axes[0, 1].imshow(img2_chip)
            axes[0, 1].set_title('时相2')
            axes[0, 1].axis('off')

            bin_chip = binary_map[min_row_p:max_row_p, min_col_p:max_col_p]
            axes[1, 0].imshow(bin_chip, cmap='gray')
            axes[1, 0].set_title('变化二值图')
            axes[1, 0].axis('off')

            sem_chip = semantic_map[min_row_p:max_row_p, min_col_p:max_col_p]
            color_chip = np.zeros((sem_chip.shape[0], sem_chip.shape[1], 3), dtype=np.uint8)
            for type_id, color in enumerate(SEMANTIC_CHANGE_COLORS):
                color_chip[sem_chip == type_id] = color
            axes[1, 1].imshow(color_chip)
            axes[1, 1].set_title(f'语义类型: {region.semantic_type}')
            axes[1, 1].axis('off')

            info_text = f"区域 {idx+1}\n类型: {region.semantic_type}\n面积: {region.area_pixels} 像素\n置信度: {region.confidence:.2f}\n"
            info_text += f"NDVI: {region.ndvi_before:.3f} → {region.ndvi_after:.3f}\n"
            info_text += f"亮度: {region.brightness_before:.3f} → {region.brightness_after:.3f}"
            fig.suptitle(info_text, fontsize=10, y=0.98)

            filename = f'region_{idx+1:03d}.png'
            chip_paths.append(self.save_figure(fig, filename))

        return chip_paths

    def generate_overlay_comparison(self, image1: np.ndarray, image2: np.ndarray,
                                     binary_map: np.ndarray, semantic_map: np.ndarray) -> str:
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        if image1.shape[0] >= 3:
            axes[0, 0].imshow(np.transpose(image1[:3], (1, 2, 0)))
            axes[0, 1].imshow(np.transpose(image2[:3], (1, 2, 0)))
        else:
            axes[0, 0].imshow(image1[0], cmap='gray')
            axes[0, 1].imshow(image2[0], cmap='gray')

        axes[0, 0].set_title('时相1影像')
        axes[0, 0].axis('off')
        axes[0, 1].set_title('时相2影像')
        axes[0, 1].axis('off')

        axes[1, 0].imshow(binary_map, cmap='gray')
        axes[1, 0].set_title('变化二值图')
        axes[1, 0].axis('off')

        color_map = np.zeros((semantic_map.shape[0], semantic_map.shape[1], 3), dtype=np.uint8)
        for type_id, color in enumerate(SEMANTIC_CHANGE_COLORS):
            color_map[semantic_map == type_id] = color
        axes[1, 1].imshow(color_map)
        axes[1, 1].set_title('语义变化图')
        axes[1, 1].axis('off')

        legend_handles = [plt.Rectangle((0, 0), 1, 1, color=tuple(np.array(c) / 255.0))
                          for c in SEMANTIC_CHANGE_COLORS]
        fig.legend(legend_handles, SEMANTIC_CHANGE_TYPES,
                   loc='center right', bbox_to_anchor=(1.15, 0.5), fontsize=8)

        plt.tight_layout()
        return self.save_figure(fig, 'overview_comparison.png')

    def generate_html_report(self) -> str:
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.report_data['project_name']} - 检测报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 40px;
            padding: 20px;
            background-color: #fafafa;
            border-radius: 8px;
            border-left: 4px solid #2a5298;
        }}
        .section h2 {{
            color: #1e3c72;
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .section-content {{
            line-height: 1.8;
            margin: 15px 0;
        }}
        .section-content pre {{
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .image-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .image-grid-3 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .image-item {{
            text-align: center;
        }}
        .image-item img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .image-caption {{
            margin-top: 8px;
            font-size: 14px;
            color: #666;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .stats-table th, .stats-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        .stats-table th {{
            background-color: #1e3c72;
            color: white;
        }}
        .stats-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
            margin-top: 40px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 8px;
        }}
        .badge-success {{ background-color: #d4edda; color: #155724; }}
        .badge-warning {{ background-color: #fff3cd; color: #856404; }}
        .badge-info {{ background-color: #d1ecf1; color: #0c5460; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌍 {self.report_data['project_name']}</h1>
            <div class="subtitle">
                📅 报告生成时间: {self.report_data['generation_time']}
            </div>
        </div>
"""

        for section in self.report_data['sections']:
            html_content += f"""
        <div class="section">
            <h2>📊 {section['title']}</h2>
            <div class="section-content">
                {section['content']}
            </div>
"""
            if section['images']:
                if len(section['images']) > 3:
                    html_content += '            <div class="image-grid-3">\n'
                else:
                    html_content += '            <div class="image-grid">\n'

                for img_path in section['images']:
                    img_name = os.path.basename(img_path)
                    html_content += f"""
                <div class="image-item">
                    <img src="{img_path}" alt="{img_name}">
                    <div class="image-caption">{img_name}</div>
                </div>
"""
                html_content += '            </div>\n'

            html_content += '        </div>\n'

        html_content += f"""
        <div class="footer">
            <p>📋 本报告由遥感图像变化检测系统自动生成 | © 2026</p>
        </div>
    </div>
</body>
</html>
"""

        report_path = os.path.join(self.report_dir, 'change_detection_report.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"报告已生成: {report_path}")
        return report_path

    def generate_markdown_report(self) -> str:
        md_content = f"""# {self.report_data['project_name']}

> 📅 报告生成时间: {self.report_data['generation_time']}

---

"""

        for section in self.report_data['sections']:
            md_content += f"""## {section['title']}

{section['content']}

"""
            if section['images']:
                for img_path in section['images']:
                    img_name = os.path.basename(img_path)
                    md_content += f"![{img_name}]({img_path})\n\n"

        report_path = os.path.join(self.report_dir, 'change_detection_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return report_path


def generate_full_report(output_dir: str, image1: np.ndarray, image2: np.ndarray,
                         binary_map: np.ndarray, type_map: np.ndarray, semantic_map: np.ndarray,
                         area_stats: Dict, class_stats: Dict, semantic_regions: List,
                         semantic_summary: Dict, temporal_summary: Dict = None) -> str:
    report = ChangeDetectionReport(output_dir)

    overview_content = f"""
| 指标 | 数值 |
|------|------|
| 总像素数 | {area_stats.get('total_pixels', 0):,} |
| 变化像素数 | {area_stats.get('changed_pixels', 0):,} |
| 未变化像素数 | {area_stats.get('unchanged_pixels', 0):,} |
| 变化比例 | {area_stats.get('change_ratio', 0)*100:.2f}% |
| 变化区域数量 | {area_stats.get('num_regions', 0)} |
| 总变化面积 | {area_stats.get('changed_area', 0):.4f} |
| 平均区域面积 | {area_stats.get('mean_region_area', 0):.4f} |
| 像素实际面积 | {area_stats.get('pixel_area', 1.0):.6f} 平方单位 |
"""
    overview_img = report.generate_overview_chart(area_stats, class_stats)
    report.add_section("1. 变化检测总体概况", overview_content, [overview_img])

    semantic_content = f"""
| 语义类型 | 区域数量 | 总面积 |
|----------|----------|--------|
"""
    for t in SEMANTIC_CHANGE_TYPES[1:]:
        count = semantic_summary['by_type_count'][t]
        area = semantic_summary['by_type_area'][t]
        if count > 0:
            semantic_content += f"| {t} | {count} | {area:.4f} |\n"

    semantic_content += f"""
- 总语义变化区域数: {semantic_summary.get('total_regions', 0)}
- 平均置信度: {semantic_summary.get('mean_confidence', 0):.4f}
- 平均区域面积: {semantic_summary.get('mean_area', 0):.4f}
"""
    semantic_img = report.generate_semantic_chart(semantic_summary)
    report.add_section("2. 语义变化检测分析", semantic_content, [semantic_img])

    if temporal_summary is not None:
        temporal_content = f"""
| 指标 | 数值 |
|------|------|
| 时相数量 | {temporal_summary.get('num_time_points', 0)} |
| 发生变化像素数 | {temporal_summary.get('pixels_with_changes', 0):,} |
| 平均变化强度 | {temporal_summary.get('mean_change_intensity', 0):.4f} |
| 最大变化频率 | {temporal_summary.get('max_change_frequency', 0)} |
| NDVI增加像素 | {temporal_summary.get('ndvi_increasing_pixels', 0):,} |
| NDVI减少像素 | {temporal_summary.get('ndvi_decreasing_pixels', 0):,} |
| NDVI稳定像素 | {temporal_summary.get('ndvi_stable_pixels', 0):,} |
"""
        temporal_img = report.generate_temporal_chart(temporal_summary)
        report.add_section("3. 多时相时序变化分析", temporal_content, [temporal_img])

    overview_compare_img = report.generate_overlay_comparison(image1, image2, binary_map, semantic_map)
    report.add_section("4. 变化影像对比", "多时相影像与变化检测结果对比", [overview_compare_img])

    region_chips = report.generate_region_chips(image1, image2, binary_map, semantic_map, semantic_regions, num_regions=10)
    if region_chips:
        regions_content = "以下为面积最大的10个变化区域的详细影像切片（按面积从大到小排列）。"
        report.add_section("5. 重点变化区域详情", regions_content, region_chips)

    html_path = report.generate_html_report()
    md_path = report.generate_markdown_report()

    print(f"\n📄 HTML报告: {html_path}")
    print(f"📝 Markdown报告: {md_path}")

    return html_path
