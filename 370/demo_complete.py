"""
完整功能演示脚本
展示所有增强功能：时序分析、语义变化检测、报告生成
"""

import os
import sys
import numpy as np

from data_loader import read_geotiff, write_geotiff, normalize_image
from post_process import (
    generate_binary_map, morphological_refine,
    classify_change_types, compute_area_statistics,
    compute_class_area_statistics, generate_color_map,
    compute_pixel_area_from_geotransform
)
from config import CLASS_NAMES, CLASS_COLORS, OUTPUT_DIR, PIXEL_SIZE
from registration import ImageRegistration
from semantic_change import (
    SemanticChangeDetector, detect_semantic_changes,
    SEMANTIC_CHANGE_TYPES, SEMANTIC_CHANGE_COLORS
)
from temporal_analysis import TemporalChangeAnalyzer
from report_generator import generate_full_report


def demo_all_features():
    print("=" * 70)
    print("遥感图像变化检测 - 完整增强功能演示")
    print("=" * 70)

    image1_path = 'data/time_2020.tif'
    image2_path = 'data/time_2024.tif'
    multitemporal_pattern = 'data/time_*.tif'

    if not os.path.exists(image1_path):
        print("\n正在生成多时相测试数据...")
        from generate_multitemporal_data import create_multitemporal_data
        create_multitemporal_data('data', 512, 512, 5)

    print("\n" + "=" * 70)
    print("[1] 图像读取与预处理")
    print("=" * 70)
    img1, proj, geotransform, w, h, bands = read_geotiff(image1_path)
    img2, _, _, _, _, _ = read_geotiff(image2_path)
    print(f"  时相1: {img1.shape}, 时相2: {img2.shape}")

    if geotransform:
        print(f"  地理变换参数: {geotransform}")
        pixel_width, pixel_height = compute_pixel_area_from_geotransform(geotransform)
        print(f"  像素实际大小: {pixel_width:.4f} x {pixel_height:.4f}")
        print(f"  像素实际面积: {pixel_width * pixel_height:.4f} 平方单位")
    else:
        print("  无地理变换参数")
        pixel_width, pixel_height = PIXEL_SIZE, PIXEL_SIZE

    print("\n" + "=" * 70)
    print("[2] SIFT特征点配准 + RANSAC几何验证")
    print("=" * 70)
    try:
        import cv2
        registrar = ImageRegistration(feature_type='SIFT', max_features=2000)
        registered_img2, reg_status = registrar.register_images(img1, img2)

        print(f"  配准状态: {reg_status.get('status', 'unknown')}")
        if reg_status.get('status') == 'success':
            print(f"  特征点数(图1): {reg_status.get('num_keypoints_img1', 0)}")
            print(f"  特征点数(图2): {reg_status.get('num_keypoints_img2', 0)}")
            print(f"  匹配数: {reg_status.get('num_matches', 0)}")
            print(f"  内点数: {reg_status.get('num_inliers', 0)}")
            print(f"  变换类型: {reg_status.get('transform_type', 'unknown')}")
            img2_for_use = registered_img2
        else:
            print(f"  配准失败: {reg_status.get('reason', 'unknown')}")
            img2_for_use = img2
    except ImportError:
        print("  OpenCV未安装，跳过配准")
        img2_for_use = img2
    except Exception as e:
        print(f"  配准异常: {e}")
        img2_for_use = img2

    print("\n" + "=" * 70)
    print("[3] 变化检测与形态学后处理")
    print("=" * 70)
    diff = np.abs(img1 - img2_for_use)
    diff_mean = np.mean(diff, axis=0)
    threshold = np.median(diff_mean) + 0.5 * np.std(diff_mean)
    simple_change = (diff_mean > threshold).astype(np.uint8)
    binary_map = morphological_refine(simple_change, min_size=64, min_hole_size=256)
    type_map = classify_change_types(binary_map, img1, img2_for_use)
    print(f"  变化像素数: {np.sum(binary_map)}")
    print(f"  变化比例: {np.sum(binary_map) / binary_map.size * 100:.2f}%")

    print("\n" + "=" * 70)
    print("[4] 语义变化检测（新建/拆除/翻新识别）")
    print("=" * 70)
    pixel_area = pixel_width * pixel_height
    detector = SemanticChangeDetector()
    semantic_map = detector.classify_semantic_change(img1, img2_for_use, binary_map)
    semantic_regions = detector.extract_change_regions(
        semantic_map, img1, img2_for_use, pixel_area,
        min_region_size=50
    )
    semantic_summary = detector.summarize_semantic_changes(semantic_regions)

    print(f"  总语义变化区域数: {semantic_summary['total_regions']}")
    print("\n  按类型统计:")
    for t in SEMANTIC_CHANGE_TYPES[1:]:
        count = semantic_summary['by_type_count'][t]
        area = semantic_summary['by_type_area'][t]
        if count > 0:
            print(f"    📍 {t}: {count} 个区域, 总面积 {area:.4f}")

    print("\n  TOP 3 最大变化区域:")
    regions_sorted = sorted(semantic_regions, key=lambda r: r.area_pixels, reverse=True)[:3]
    for i, r in enumerate(regions_sorted):
        print(f"    {i+1}. {r.semantic_type} - 面积: {r.area_pixels} 像素, 置信度: {r.confidence:.3f}")

    print("\n" + "=" * 70)
    print("[5] 地理变换面积统计")
    print("=" * 70)
    area_stats = compute_area_statistics(
        binary_map, pixel_size=None, geotransform=geotransform
    )
    class_stats = compute_class_area_statistics(
        type_map, pixel_size=None, geotransform=geotransform
    )

    if geotransform:
        print(f"  像素实际面积: {area_stats['pixel_area']:.6f} 平方单位")
        print(f"  总变化面积: {area_stats['changed_area']:.4f} 平方单位")
        print(f"  总图像面积: {area_stats['total_area']:.4f} 平方单位")
    else:
        print(f"  像素面积: {PIXEL_SIZE} 像素平方")
        print(f"  总变化面积: {area_stats['changed_area']:.4f} 像素平方")

    print("\n  各类变化面积:")
    for class_name, stats in class_stats.items():
        area_unit = "平方单位" if geotransform else "像素平方"
        if stats['pixel_count'] > 0:
            print(f"    {class_name}: {stats['area']:.4f} {area_unit} ({stats['ratio']*100:.2f}%)")

    print("\n" + "=" * 70)
    print("[6] 多时相时序变化分析")
    print("=" * 70)
    try:
        import glob
        image_paths = sorted(glob.glob(multitemporal_pattern))
        dates = [os.path.basename(p).replace('time_', '').replace('.tif', '') for p in image_paths]

        print(f"  发现 {len(image_paths)} 个时相影像: {dates}")

        analyzer = TemporalChangeAnalyzer(image_paths, dates)
        temporal_summary = analyzer.summarize_changes()
        temporal_metrics = analyzer.compute_temporal_metrics()

        print(f"  发生变化像素数: {temporal_summary.get('pixels_with_changes', 0):,}")
        print(f"  平均变化强度: {temporal_summary.get('mean_change_intensity', 0):.4f}")
        print(f"  最大变化频率: {temporal_summary.get('max_change_frequency', 0)}")

        if 'ndvi_trend' in temporal_metrics:
            print(f"  NDVI增加像素: {temporal_summary.get('ndvi_increasing_pixels', 0):,}")
            print(f"  NDVI减少像素: {temporal_summary.get('ndvi_decreasing_pixels', 0):,}")

        temporal_dir = os.path.join(OUTPUT_DIR, 'demo_temporal')
        analyzer.save_temporal_metrics(temporal_dir)

    except Exception as e:
        print(f"  时序分析跳过: {e}")
        temporal_summary = None

    print("\n" + "=" * 70)
    print("[7] 生成变化检测报告")
    print("=" * 70)
    results_dir = os.path.join(OUTPUT_DIR, 'demo_complete')
    os.makedirs(results_dir, exist_ok=True)

    semantic_dir = os.path.join(results_dir, 'semantic')
    os.makedirs(semantic_dir, exist_ok=True)

    color_map = generate_color_map(type_map)
    color_3ch = np.transpose(color_map, (2, 0, 1))

    write_geotiff(os.path.join(results_dir, 'binary_map.tif'), binary_map.astype(np.float32))
    write_geotiff(os.path.join(results_dir, 'type_map.tif'), type_map.astype(np.float32))
    write_geotiff(os.path.join(results_dir, 'color_map.tif'), color_3ch.astype(np.float32))

    print("  生成HTML/Markdown报告...")
    report_path = generate_full_report(
        OUTPUT_DIR,
        img1, img2_for_use,
        binary_map, type_map, semantic_map,
        area_stats, class_stats,
        semantic_regions, semantic_summary,
        temporal_summary
    )

    print(f"  ✅ 报告已生成: {report_path}")

    print("\n" + "=" * 70)
    print("🎉 所有增强功能演示完成!")
    print("=" * 70)
    print("\n📁 输出文件:")
    print(f"  - 变化检测结果: {results_dir}/")
    if temporal_summary:
        print(f"  - 时序分析结果: {temporal_dir}/")
    print(f"  - 完整报告: {os.path.dirname(report_path)}/")
    print("\n🚀 使用命令:")
    print("  基础推理: python main.py infer --image1 data/time1.tif --image2 data/time2.tif")
    print("  语义检测: python main.py semantic --image1 data/time_2020.tif --image2 data/time_2024.tif --generate-report")
    print("  时序分析: python main.py temporal --generate-report")
    print("  带配准推理: python main.py infer --registration --tta")


if __name__ == '__main__':
    demo_all_features()
