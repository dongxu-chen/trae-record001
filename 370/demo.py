"""
演示脚本 - 增强版
展示SIFT配准、加权损失权重计算、地理变换面积统计
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


def demo_enhanced():
    print("=" * 60)
    print("遥感图像变化检测 - 增强功能演示")
    print("=" * 60)

    image1_path = 'data/time1.tif'
    image2_path = 'data/time2.tif'

    if not os.path.exists(image1_path):
        print("错误: 测试数据不存在，请先运行: python generate_test_data.py")
        return

    print("\n[1] 读取TIFF影像...")
    img1, proj, geotransform, w, h, bands = read_geotiff(image1_path)
    img2, _, _, _, _, _ = read_geotiff(image2_path)
    print(f"    时相1: {img1.shape}, 时相2: {img2.shape}")

    if geotransform:
        print(f"    地理变换参数: {geotransform}")
        pixel_width, pixel_height = compute_pixel_area_from_geotransform(geotransform)
        print(f"    像素实际大小: {pixel_width:.4f} x {pixel_height:.4f}")
        print(f"    像素实际面积: {pixel_width * pixel_height:.4f} 平方单位")
    else:
        print("    无地理变换参数，使用默认像素大小")
        pixel_width, pixel_height = PIXEL_SIZE, PIXEL_SIZE

    print("\n[2] SIFT特征点配准演示...")
    try:
        import cv2
        from registration import ImageRegistration

        registrar = ImageRegistration(feature_type='SIFT', max_features=2000)
        registered_img2, reg_status = registrar.register_images(img1, img2)

        print(f"    配准状态: {reg_status.get('status', 'unknown')}")
        if reg_status.get('status') == 'success':
            print(f"    特征点数(图1): {reg_status.get('num_keypoints_img1', 0)}")
            print(f"    特征点数(图2): {reg_status.get('num_keypoints_img2', 0)}")
            print(f"    匹配数: {reg_status.get('num_matches', 0)}")
            print(f"    内点数: {reg_status.get('num_inliers', 0)}")
            print(f"    变换类型: {reg_status.get('transform_type', 'unknown')}")
            img2_for_use = registered_img2
        else:
            print(f"    配准失败: {reg_status.get('reason', 'unknown')}")
            img2_for_use = img2
    except ImportError:
        print("    OpenCV未安装，跳过配准演示")
        print("    安装命令: pip install opencv-python")
        img2_for_use = img2
    except Exception as e:
        print(f"    配准异常: {e}")
        img2_for_use = img2

    print("\n[3] 计算简单差分变化图...")
    diff = np.abs(img1 - img2_for_use)
    diff_mean = np.mean(diff, axis=0)
    threshold = np.median(diff_mean) + 0.5 * np.std(diff_mean)
    simple_change = (diff_mean > threshold).astype(np.uint8)

    print("\n[4] 形态学精炼...")
    binary_map = morphological_refine(simple_change, min_size=64, min_hole_size=256)

    print("\n[5] 变化类型分类...")
    type_map = classify_change_types(binary_map, img1, img2_for_use)

    print("\n[6] 地理变换面积统计...")
    area_stats = compute_area_statistics(binary_map, pixel_size=None, geotransform=geotransform)
    class_stats = compute_class_area_statistics(type_map, pixel_size=None, geotransform=geotransform)

    print("\n[7] 保存结果...")
    results_dir = os.path.join(OUTPUT_DIR, 'demo_results_enhanced')
    os.makedirs(results_dir, exist_ok=True)

    write_geotiff(os.path.join(results_dir, 'binary_demo.tif'), binary_map.astype(np.float32))
    write_geotiff(os.path.join(results_dir, 'type_demo.tif'), type_map.astype(np.float32))

    color_map = generate_color_map(type_map)
    color_3ch = np.transpose(color_map, (2, 0, 1))
    write_geotiff(os.path.join(results_dir, 'color_demo.tif'), color_3ch.astype(np.float32))

    print("\n" + "=" * 60)
    print("统计结果 (使用地理变换参数)")
    print("=" * 60)
    print(f"总像素数: {area_stats['total_pixels']}")
    print(f"变化像素数: {area_stats['changed_pixels']}")
    print(f"变化比例: {area_stats['change_ratio']*100:.2f}%")

    if geotransform:
        print(f"\n像素实际面积: {area_stats['pixel_area']:.4f} 平方单位")
        print(f"总变化面积: {area_stats['changed_area']:.4f} 平方单位")
        print(f"总图像面积: {area_stats['total_area']:.4f} 平方单位")
    else:
        print(f"\n无地理变换参数")
        print(f"默认像素面积: {PIXEL_SIZE} 像素²")
        print(f"总变化面积: {area_stats['changed_area']:.4f} 像素²")

    print(f"\n变化区域数量: {area_stats.get('num_regions', 0)}")
    if 'mean_region_area' in area_stats:
        area_unit = "平方单位" if geotransform else "像素²"
        print(f"平均变化区域面积: {area_stats['mean_region_area']:.4f} {area_unit}")
        print(f"最小变化区域面积: {area_stats['min_region_area']:.4f} {area_unit}")
        print(f"最大变化区域面积: {area_stats['max_region_area']:.4f} {area_unit}")

    print("\n各类变化统计:")
    for class_name, stats in class_stats.items():
        area_unit = "平方单位" if geotransform else "像素²"
        print(f"  {class_name}: {stats['pixel_count']} 像素, "
              f"{stats['area']:.4f} {area_unit}, 占比 {stats['ratio']*100:.2f}%")

    print("\n" + "=" * 60)
    print("加权损失权重计算演示")
    print("=" * 60)
    class_counts = {}
    for i, name in enumerate(CLASS_NAMES):
        count = np.sum(type_map == i)
        class_counts[i] = count
        print(f"  {name}: {count} 像素")

    total = sum(class_counts.values())
    print(f"\n总像素: {total}")
    print("\n类别权重 (逆频率加权):")
    for i, name in enumerate(CLASS_NAMES):
        if class_counts[i] > 0:
            weight = total / (len(CLASS_NAMES) * class_counts[i])
            weight = min(weight, 10.0)
            print(f"  {name}: {weight:.4f}")
        else:
            print(f"  {name}: 10.0000 (默认最大权重)")

    print(f"\n结果保存于: {results_dir}")
    print("\n增强功能演示完成!")


if __name__ == '__main__':
    demo_enhanced()
