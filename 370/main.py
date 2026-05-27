"""
遥感图像变化检测 - 主入口脚本
功能：
1. 模型训练
2. 变化检测推理
3. 后处理（二值化、分类、统计）
4. 可视化（混淆矩阵、结果图）
支持SIFT配准、加权损失、地理变换面积计算
"""

import os
import argparse
import numpy as np
import torch
from sklearn.metrics import classification_report, cohen_kappa_score, accuracy_score
from tqdm import tqdm

from config import (
    MODEL_CONFIG, TRAIN_CONFIG, CLASS_NAMES,
    INPUT_IMAGE_1, INPUT_IMAGE_2, LABEL_IMAGE,
    OUTPUT_DIR, CHECKPOINT_DIR, PIXEL_SIZE
)
from data_loader import read_geotiff, write_geotiff
from models.unet import UNet
from train import train_main, load_checkpoint
from inference import load_model, predict_whole_image, predict_with_tta
from post_process import (
    generate_binary_map, morphological_refine,
    classify_change_types, compute_area_statistics,
    compute_class_area_statistics, generate_color_map
)
from visualization import (
    plot_training_curves, plot_confusion_matrix,
    plot_change_detection_results, plot_area_statistics,
    plot_region_size_distribution, plot_overlay_on_image
)


def run_training(args):
    print("=" * 50)
    print("开始训练变化检测模型")
    print("=" * 50)

    image1_path = args.image1 or INPUT_IMAGE_1
    image2_path = args.image2 or INPUT_IMAGE_2
    label_path = args.label or LABEL_IMAGE

    if not os.path.exists(image1_path):
        print(f"错误: 影像1不存在: {image1_path}")
        return
    if not os.path.exists(image2_path):
        print(f"错误: 影像2不存在: {image2_path}")
        return
    if not os.path.exists(label_path):
        print(f"错误: 标签影像不存在: {label_path}")
        return

    model, history = train_main(
        image1_path, image2_path, label_path,
        use_registration=args.registration
    )

    curves_path = os.path.join(OUTPUT_DIR, 'training_curves.png')
    plot_training_curves(history, save_path=curves_path)

    print("\n训练完成!")


def run_inference(args):
    print("=" * 50)
    print("开始变化检测推理")
    print("=" * 50)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    image1_path = args.image1 or INPUT_IMAGE_1
    image2_path = args.image2 or INPUT_IMAGE_2
    checkpoint_path = args.checkpoint or os.path.join(CHECKPOINT_DIR, 'best_model.pth')

    if not os.path.exists(image1_path):
        print(f"错误: 影像1不存在: {image1_path}")
        return
    if not os.path.exists(image2_path):
        print(f"错误: 影像2不存在: {image2_path}")
        return

    if args.registration:
        try:
            from registration import register_image_pair
            print("执行图像配准...")
            registered_img2_path = image2_path.replace('.tif', '_registered.tif')
            _, reg_status = register_image_pair(
                image1_path, image2_path,
                output_path=registered_img2_path,
                method='SIFT'
            )
            if reg_status.get('status') == 'success':
                image2_path = registered_img2_path
                print(f"配准成功，使用配准后影像: {registered_img2_path}")
            else:
                print(f"配准失败: {reg_status.get('reason', 'unknown')}")
        except Exception as e:
            print(f"配准异常: {e}")

    model = load_model(checkpoint_path, device)

    print("\n运行变化检测推理...")
    if args.tta:
        change_map, change_prob, dataset = predict_with_tta(
            model, image1_path, image2_path, device
        )
    else:
        change_map, change_prob, dataset = predict_whole_image(
            model, image1_path, image2_path, device
        )

    print("\n后处理...")
    binary_map = generate_binary_map(change_map, change_prob, prob_threshold=0.5)
    binary_map = morphological_refine(binary_map, min_size=64, min_hole_size=256)

    type_map = classify_change_types(binary_map, dataset.image1, dataset.image2)

    color_map = generate_color_map(type_map)

    print("\n计算统计信息...")
    geotransform = dataset.geotransform if hasattr(dataset, 'geotransform') else None
    area_stats = compute_area_statistics(
        binary_map, pixel_size=None, geotransform=geotransform
    )
    class_stats = compute_class_area_statistics(
        type_map, pixel_size=None, geotransform=geotransform
    )

    print("\n保存结果...")
    results_dir = os.path.join(OUTPUT_DIR, 'detection_results')
    os.makedirs(results_dir, exist_ok=True)

    binary_path = os.path.join(results_dir, 'change_binary.tif')
    write_geotiff(binary_path, binary_map.astype(np.float32),
                  dataset.projection, dataset.geotransform, dtype=1)

    type_path = os.path.join(results_dir, 'change_types.tif')
    write_geotiff(type_path, type_map.astype(np.float32),
                  dataset.projection, dataset.geotransform, dtype=1)

    color_path = os.path.join(results_dir, 'change_types_color.tif')
    color_3ch = np.transpose(color_map, (2, 0, 1))
    write_geotiff(color_path, color_3ch.astype(np.float32),
                  dataset.projection, dataset.geotransform, dtype=1)

    prob_path = os.path.join(results_dir, 'change_probability.tif')
    write_geotiff(prob_path, change_prob.astype(np.float32),
                  dataset.projection, dataset.geotransform, dtype=6)

    print("\n生成可视化结果...")
    results_img_path = os.path.join(results_dir, 'detection_visualization.png')
    plot_change_detection_results(
        dataset.image1, dataset.image2, binary_map, type_map,
        change_prob, save_path=results_img_path
    )

    area_img_path = os.path.join(results_dir, 'area_statistics.png')
    plot_area_statistics(area_stats, class_stats, save_path=area_img_path)

    region_img_path = os.path.join(results_dir, 'region_size_distribution.png')
    plot_region_size_distribution(area_stats, save_path=region_img_path)

    overlay_img_path = os.path.join(results_dir, 'change_overlay.png')
    plot_overlay_on_image(dataset.image2, binary_map, save_path=overlay_img_path)

    print("\n语义变化检测...")
    semantic_dir = os.path.join(results_dir, 'semantic')
    from semantic_change import detect_semantic_changes
    pixel_area = area_stats.get('pixel_area', 1.0)
    semantic_results = detect_semantic_changes(
        image1_path, image2_path, binary_map,
        semantic_dir, pixel_area=pixel_area,
        min_region_size=50
    )
    semantic_map = semantic_results['semantic_map']
    semantic_regions = semantic_results['regions']
    semantic_summary = semantic_results['summary']

    print("\n生成变化检测报告...")
    from report_generator import generate_full_report
    report_path = generate_full_report(
        OUTPUT_DIR,
        dataset.image1, dataset.image2,
        binary_map, type_map, semantic_map,
        area_stats, class_stats,
        semantic_regions, semantic_summary
    )

    print("\n" + "=" * 50)
    print("变化检测统计结果")
    print("=" * 50)
    print(f"总像素数: {area_stats['total_pixels']}")
    print(f"变化像素数: {area_stats['changed_pixels']}")
    print(f"未变化像素数: {area_stats['unchanged_pixels']}")
    print(f"变化比例: {area_stats['change_ratio']:.4f} ({area_stats['change_ratio']*100:.2f}%)")

    if geotransform:
        print(f"\n地理变换参数: {geotransform}")
        print(f"像素大小: {area_stats.get('pixel_width', 1.0):.4f} x {area_stats.get('pixel_height', 1.0):.4f}")
        print(f"像素实际面积: {area_stats.get('pixel_area', 1.0):.4f} 平方单位")
        print(f"总变化面积: {area_stats['changed_area']:.4f} 平方单位")
        print(f"总图像面积: {area_stats['total_area']:.4f} 平方单位")
    else:
        print(f"\n无地理变换参数，使用默认像素大小: {PIXEL_SIZE}")
        print(f"总变化面积: {area_stats['changed_area']:.4f} 像素²")

    print(f"变化区域数量: {area_stats.get('num_regions', 0)}")
    if 'mean_region_area' in area_stats:
        print(f"平均变化区域面积: {area_stats['mean_region_area']:.4f}")
        print(f"最小变化区域面积: {area_stats['min_region_area']:.4f}")
        print(f"最大变化区域面积: {area_stats['max_region_area']:.4f}")

    print("\n各类变化统计:")
    for class_name, stats in class_stats.items():
        area_unit = "平方单位" if geotransform else "像素²"
        print(f"  {class_name}: {stats['pixel_count']} 像素, "
              f"{stats['area']:.4f} {area_unit}, 占比 {stats['ratio']*100:.2f}%")

    print(f"\n结果保存于: {results_dir}")
    print("推理完成!")

    return {
        'binary_map': binary_map,
        'type_map': type_map,
        'change_prob': change_prob,
        'area_stats': area_stats,
        'class_stats': class_stats,
        'dataset': dataset,
        'geotransform': geotransform
    }


def run_evaluation(args):
    print("=" * 50)
    print("开始模型评估")
    print("=" * 50)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    image1_path = args.image1 or INPUT_IMAGE_1
    image2_path = args.image2 or INPUT_IMAGE_2
    label_path = args.label or LABEL_IMAGE
    checkpoint_path = args.checkpoint or os.path.join(CHECKPOINT_DIR, 'best_model.pth')

    if not os.path.exists(label_path):
        print(f"错误: 标签影像不存在: {label_path}")
        return

    label, _, _, _, _, _ = read_geotiff(label_path)
    if label.shape[0] == 1:
        label = label.squeeze(0)

    results = run_inference(args)
    if results is None:
        return

    type_map = results['type_map']

    valid_mask = label >= 0
    y_true = label[valid_mask].flatten().astype(int)
    y_pred = type_map[valid_mask].flatten().astype(int)

    min_len = min(len(y_true), len(y_pred))
    y_true = y_true[:min_len]
    y_pred = y_pred[:min_len]

    print("\n" + "=" * 50)
    print("评估指标")
    print("=" * 50)

    overall_acc = accuracy_score(y_true, y_pred)
    print(f"总体准确率: {overall_acc:.4f}")

    kappa = cohen_kappa_score(y_true, y_pred)
    print(f"Kappa系数: {kappa:.4f}")

    print("\n分类报告:")
    report = classification_report(
        y_true, y_pred,
        target_names=CLASS_NAMES[:len(np.unique(y_true))],
        zero_division=0
    )
    print(report)

    cm_path = os.path.join(OUTPUT_DIR, 'confusion_matrix.png')
    plot_confusion_matrix(y_true, y_pred, CLASS_NAMES, save_path=cm_path)

    print(f"\n混淆矩阵已保存: {cm_path}")
    print("评估完成!")


def run_temporal_analysis(args):
    print("=" * 60)
    print("多时相变化时序分析")
    print("=" * 60)

    from temporal_analysis import run_temporal_analysis

    if args.images:
        image_paths = args.images
    else:
        import glob
        default_pattern = 'data/time*.tif'
        image_paths = sorted(glob.glob(default_pattern))
        if not image_paths:
            print(f"错误: 未找到多时相影像，默认模式: {default_pattern}")
            print("请使用 --images 参数指定影像路径列表")
            return

    dates = args.dates if args.dates else None

    if dates and len(dates) != len(image_paths):
        print(f"错误: 日期数量 ({len(dates)}) 与影像数量 ({len(image_paths)}) 不匹配")
        return

    print(f"发现 {len(image_paths)} 个时相影像:")
    for i, (path, date) in enumerate(zip(image_paths, dates if dates else range(len(image_paths)))):
        date_str = date if isinstance(date, str) else f"T{i}"
        print(f"  {i+1}. [{date_str}] {path}")

    temporal_output = os.path.join(OUTPUT_DIR, 'temporal_results')
    os.makedirs(temporal_output, exist_ok=True)

    analyzer, summary = run_temporal_analysis(image_paths, temporal_output, dates)

    if args.generate_report:
        print("\n生成时序分析报告...")
        from report_generator import ChangeDetectionReport

        report = ChangeDetectionReport(OUTPUT_DIR, project_name="多时相变化时序分析")

        temporal_content = f"""
| 指标 | 数值 |
|------|------|
| 时相数量 | {summary.get('num_time_points', 0)} |
| 影像尺寸 | {summary.get('image_size', (0,0))[0]} x {summary.get('image_size', (0,0))[1]} |
| 总像素数 | {summary.get('total_pixels', 0):,} |
| 发生变化像素数 | {summary.get('pixels_with_changes', 0):,} |
| 平均变化强度 | {summary.get('mean_change_intensity', 0):.4f} |
| 最大变化频率 | {summary.get('max_change_frequency', 0)} |
| NDVI增加像素 | {summary.get('ndvi_increasing_pixels', 0):,} |
| NDVI减少像素 | {summary.get('ndvi_decreasing_pixels', 0):,} |
"""
        temporal_img = report.generate_temporal_chart(summary)
        report.add_section("1. 多时相变化时序分析摘要", temporal_content, [temporal_img])

        report.generate_html_report()
        report.generate_markdown_report()

    print("\n多时相时序分析完成!")


def run_pipeline(args):
    print("=" * 50)
    print("运行完整流程: 配准 -> 训练 -> 推理 -> 评估")
    print("=" * 50)

    run_training(args)
    results = run_inference(args)
    if results is not None and os.path.exists(args.label or LABEL_IMAGE):
        run_evaluation(args)

    print("\n" + "=" * 50)
    print("完整流程执行完成!")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='遥感图像变化检测系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础功能
  python main.py train --image1 data/time1.tif --image2 data/time2.tif --label data/label.tif
  python main.py infer --image1 data/time1.tif --image2 data/time2.tif --registration --tta
  python main.py eval --image1 data/time1.tif --image2 data/time2.tif --label data/label.tif
  python main.py pipeline --image1 data/time1.tif --image2 data/time2.tif --label data/label.tif --registration

  # 多时相时序分析
  python main.py temporal --images data/time1.tif data/time2.tif data/time3.tif --dates 2020 2022 2024 --generate-report
  python main.py temporal --generate-report

  # 语义变化检测
  python main.py semantic --image1 data/time1.tif --image2 data/time2.tif
        """
    )

    parser.add_argument('mode', choices=['train', 'infer', 'eval', 'pipeline', 'temporal', 'semantic'],
                        help='运行模式: train=训练, infer=推理, eval=评估, pipeline=完整流程, temporal=时序分析, semantic=语义检测')

    parser.add_argument('--image1', type=str, default=None,
                        help='时相1影像路径 (TIFF格式)')
    parser.add_argument('--image2', type=str, default=None,
                        help='时相2影像路径 (TIFF格式)')
    parser.add_argument('--label', type=str, default=None,
                        help='标签影像路径 (TIFF格式, 可选)')
    parser.add_argument('--checkpoint', type=str, default=None,
                        help='模型检查点路径')
    parser.add_argument('--tta', action='store_true', default=False,
                        help='使用测试时增强(TTA)')
    parser.add_argument('--registration', action='store_true', default=False,
                        help='使用SIFT特征点配准')
    parser.add_argument('--output', type=str, default=None,
                        help='输出目录')

    parser.add_argument('--images', type=str, nargs='+', default=None,
                        help='多时相影像路径列表 (按时间顺序排列)')
    parser.add_argument('--dates', type=str, nargs='+', default=None,
                        help='多时相影像对应的日期标签')
    parser.add_argument('--generate-report', action='store_true', default=False,
                        help='生成分析报告 (HTML/Markdown)')

    args = parser.parse_args()

    if args.output:
        global OUTPUT_DIR
        OUTPUT_DIR = args.output
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.mode == 'train':
        run_training(args)
    elif args.mode == 'infer':
        run_inference(args)
    elif args.mode == 'eval':
        run_evaluation(args)
    elif args.mode == 'pipeline':
        run_pipeline(args)
    elif args.mode == 'temporal':
        run_temporal_analysis(args)
    elif args.mode == 'semantic':
        run_semantic_only(args)


def run_semantic_only(args):
    print("=" * 60)
    print("语义变化检测（独立模式）")
    print("=" * 60)

    image1_path = args.image1 or INPUT_IMAGE_1
    image2_path = args.image2 or INPUT_IMAGE_2

    if not os.path.exists(image1_path) or not os.path.exists(image2_path):
        print(f"错误: 影像文件不存在")
        return

    from data_loader import read_geotiff
    from post_process import (
        generate_binary_map, morphological_refine,
        classify_change_types, compute_area_statistics,
        compute_class_area_statistics
    )
    from semantic_change import detect_semantic_changes
    from report_generator import generate_full_report

    img1, proj, gt, w, h, b = read_geotiff(image1_path)
    img2, _, _, _, _, _ = read_geotiff(image2_path)

    print("计算差分变化图...")
    diff = np.abs(img1 - img2)
    diff_mean = np.mean(diff, axis=0)
    threshold = np.median(diff_mean) + 0.5 * np.std(diff_mean)
    simple_change = (diff_mean > threshold).astype(np.uint8)

    print("形态学精炼...")
    binary_map = morphological_refine(simple_change, min_size=64, min_hole_size=256)

    type_map = classify_change_types(binary_map, img1, img2)

    geotransform = gt
    area_stats = compute_area_statistics(
        binary_map, pixel_size=None, geotransform=geotransform
    )
    class_stats = compute_class_area_statistics(
        type_map, pixel_size=None, geotransform=geotransform
    )

    pixel_area = area_stats.get('pixel_area', 1.0)

    print("语义变化检测...")
    semantic_dir = os.path.join(OUTPUT_DIR, 'detection_results', 'semantic')
    semantic_results = detect_semantic_changes(
        image1_path, image2_path, binary_map,
        semantic_dir, pixel_area=pixel_area,
        min_region_size=50
    )

    semantic_map = semantic_results['semantic_map']
    semantic_regions = semantic_results['regions']
    semantic_summary = semantic_results['summary']

    if args.generate_report:
        print("生成检测报告...")
        report_path = generate_full_report(
            OUTPUT_DIR, img1, img2,
            binary_map, type_map, semantic_map,
            area_stats, class_stats,
            semantic_regions, semantic_summary
        )

    print("\n语义变化检测完成!")


if __name__ == '__main__':
    main()
