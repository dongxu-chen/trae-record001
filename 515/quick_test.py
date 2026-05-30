#!/usr/bin/env python3
import sys
import os
import numpy as np
import cv2
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import (
    correct_fisheye_image,
    estimate_fisheye_params_auto,
    self_calibrate_from_lines,
    detect_line_segments,
    evaluate_calibration_quality,
    BorderHandlingMode,
    FisheyeProjectionType,
    LensConfig,
    LensConfigManager,
    create_default_lens_config,
    BatchProcessor,
    FisheyeCorrector,
    fisheye_to_equirectangular,
    create_vr_panorama,
    evaluate_correction_quality,
    CorrectionMethod,
)


def generate_synthetic_fisheye_with_lines(size=500, fov_degrees=180.0):
    image = np.zeros((size, size, 3), dtype=np.uint8)
    center = (size // 2, size // 2)
    max_r = size // 2 - 20

    for i in range(0, size, 60):
        for j in range(0, size, 60):
            dx = j - center[0]
            dy = i - center[1]
            r = np.sqrt(dx**2 + dy**2)
            if r < max_r and r > 0:
                theta = np.arcsin(r / max_r) * (fov_degrees / 180.0) * np.pi / 2
                r_fisheye = 2.0 * (size / 3.0) * np.sin(theta / 2.0)
                x_f = int(center[0] + r_fisheye * dx / r)
                y_f = int(center[1] + r_fisheye * dy / r)
                color = (200, 200, 200)
                cv2.rectangle(image, (x_f - 6, y_f - 6), (x_f + 6, y_f + 6), color, -1)

    for angle in [0, 45, 90, 135]:
        rad = np.deg2rad(angle)
        for r in np.linspace(30, max_r - 10, 20):
            x = int(center[0] + r * np.cos(rad))
            y = int(center[1] + r * np.sin(rad))
            cv2.circle(image, (x, y), 4, (0, 200, 255), -1)

    cv2.circle(image, center, max_r, (255, 255, 255), 2)
    return image


def main():
    print("=" * 70)
    print("鱼眼图像校正系统 - 新功能验证")
    print("=" * 70)

    image = generate_synthetic_fisheye_with_lines(size=500)

    print("\n" + "=" * 70)
    print("功能1: 基于直线特征的自标定")
    print("=" * 70)

    segments = detect_line_segments(image, min_length=30, max_segments=100)
    print(f"检测到 {len(segments)} 条直线段")
    if len(segments) > 0:
        print(f"最长线段长度: {max(s.length for s in segments):.1f} 像素")
        print(f"最短线段长度: {min(s.length for s in segments):.1f} 像素")

    print("\n正在进行自标定（从直线特征估计参数）...")
    params = self_calibrate_from_lines(
        image,
        min_line_length=40,
        verbose=False,
    )
    print("\n=== 自标定结果 ===")
    print(f"投影类型: {params['projection_type'].value}")
    print(f"FOV: {params['fov_degrees']:.1f}°")
    print(f"中心: ({params['center'][0]:.1f}, {params['center'][1]:.1f})")
    print(f"焦距: {params['focal_length']:.1f}")
    print(f"优化方法: {params['method']}")

    quality = evaluate_calibration_quality(image, params["model"])
    print(f"标定质量评分: {quality['quality_score']:.3f}")
    print(f"平均直线度误差: {quality['mean_error']:.3f} 像素")
    print(f"加权直线度误差: {quality['weighted_error']:.3f} 像素")
    print(f"有效线段数量: {quality['num_segments']}")

    print("\n" + "=" * 70)
    print("功能2: 边界处理模式（裁剪/填充）")
    print("=" * 70)

    corrector = FisheyeCorrector(
        distortion_model=params["model"],
    )

    print("\n--- FULL模式（完整保留，包含黑边） ---")
    corrected_full = corrector.correct(image, handling_mode=BorderHandlingMode.FULL)
    print(f"输入尺寸: {image.shape}")
    print(f"输出尺寸: {corrected_full.shape}")

    print("\n--- CROP模式（裁剪最大有效矩形） ---")
    corrected_crop = corrector.correct(image, handling_mode=BorderHandlingMode.CROP)
    print(f"输入尺寸: {image.shape}")
    print(f"输出尺寸: {corrected_crop.shape}")

    print("\n--- PAD模式（填充保持完整视角） ---")
    corrector.pad_value = (50, 50, 50)
    corrected_pad = corrector.correct(image, handling_mode=BorderHandlingMode.PAD)
    print(f"输入尺寸: {image.shape}")
    print(f"输出尺寸: {corrected_pad.shape}")

    print("\n" + "=" * 70)
    print("功能3: 多镜头参数配置管理")
    print("=" * 70)

    manager = create_default_lens_config()
    print(f"已加载 {len(manager.lenses)} 个默认镜头配置")

    print("\n镜头列表:")
    for name, config in manager.lenses.items():
        print(f"  - {name}: {config.projection_type.value}, FOV={config.fov_degrees}°, f={config.focal_length}")

    print("\n添加自定义镜头配置:")
    custom_lens = LensConfig(
        name="custom_action_cam",
        projection_type=FisheyeProjectionType.EQUISOLID,
        focal_length=150.0,
        center=(320.0, 240.0),
        fov_degrees=180.0,
        distortion_coeffs=[0.0, 0.0, 0.0, 0.0],
        description="GoPro Hero 10 广角模式",
    )
    manager.add_lens(custom_lens)
    print(f"已添加镜头: {custom_lens.name}")

    manager.set_active_lens("custom_action_cam")
    active_lens = manager.get_active_lens()
    print(f"当前活动镜头: {active_lens.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = os.path.join(tmpdir, "lens_config.json")
        manager.save(config_file)
        print(f"\n镜头配置已保存到: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        print(f"配置文件包含 {len(config_data['lenses'])} 个镜头")

        manager2 = LensConfigManager()
        manager2.load(config_file)
        print(f"从配置文件加载了 {len(manager2.lenses)} 个镜头")

        print("\n按文件名匹配镜头测试:")
        test_filenames = [
            "gopro_hero10_img001.jpg",
            "wide_180_landscape.jpg",
            "ultra_wide_220_interior.jpg",
            "unknown_camera_photo.jpg",
        ]
        for fname in test_filenames:
            matched = manager2.get_lens_for_image(fname)
            match_name = matched.name if matched else "未匹配"
            print(f"  {fname:40s} -> {match_name}")

        print("\n" + "=" * 70)
        print("功能4: 批量处理 + 镜头配置")
        print("=" * 70)

        input_dir = os.path.join(tmpdir, "input")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(input_dir)

        for i in range(2):
            img = generate_synthetic_fisheye_with_lines(size=300)
            cv2.imwrite(os.path.join(input_dir, f"lens_a_180_img_{i:03d}.jpg"), img)

        for i in range(2):
            img = generate_synthetic_fisheye_with_lines(size=300)
            cv2.imwrite(os.path.join(input_dir, f"lens_b_220_img_{i:03d}.jpg"), img)

        lens_a = LensConfig(
            name="lens_a_180",
            projection_type=FisheyeProjectionType.EQUISOLID,
            focal_length=120.0,
            center=(150.0, 150.0),
            fov_degrees=180.0,
        )
        lens_b = LensConfig(
            name="lens_b_220",
            projection_type=FisheyeProjectionType.EQUIDISTANT,
            focal_length=100.0,
            center=(150.0, 150.0),
            fov_degrees=220.0,
        )
        manager2.add_lens(lens_a)
        manager2.add_lens(lens_b)

        processor = BatchProcessor(
            lens_config_manager=manager2,
            num_workers=1,
        )
        processor.set_border_mode(BorderHandlingMode.CROP)

        lens_patterns = {
            "lens_a_180": "lens_a",
            "lens_b_220": "lens_b",
        }

        print("\n按镜头分组处理:")
        results = processor.process_groups_by_lens(
            input_dir,
            output_dir,
            lens_name_patterns=lens_patterns,
        )

        print(f"\n共处理 {len(results)} 张图像")
        group_counts = {}
        for r in results:
            group = r.get("lens_group", "unknown")
            group_counts[group] = group_counts.get(group, 0) + 1

        print("各镜头处理数量:")
        for group, count in group_counts.items():
            print(f"  {group}: {count} 张")

    print("\n" + "=" * 70)
    print("功能5: 360度VR展开 - 鱼眼图转等距柱状图")
    print("=" * 70)

    print("\n正在生成等距柱状投影图...")
    equirect = fisheye_to_equirectangular(
        image,
        distortion_model=params["model"],
        output_size=(400, 800),
    )
    print(f"等距柱状图尺寸: {equirect.shape}")

    print("\n正在生成VR全景图（多图像拼接）...")
    vr_images = [
        generate_synthetic_fisheye_with_lines(size=400, fov_degrees=180.0)
        for _ in range(2)
    ]
    vr_panorama = create_vr_panorama(
        vr_images,
        distortion_model=params["model"],
        output_size=(400, 800),
        blend_width=50,
    )
    print(f"VR全景图尺寸: {vr_panorama.shape}")

    print("\n" + "=" * 70)
    print("功能6: 校正质量评估 - 直线度与画幅保留")
    print("=" * 70)

    print("\n正在评估FULL模式校正质量...")
    quality_full = evaluate_correction_quality(image, corrected_full, params["model"])
    print(f"  质量评分: {quality_full['quality_score']:.3f}")
    print(f"  平均直线度误差: {quality_full['mean_straightness_error']:.3f} 像素")
    print(f"  画幅保留比例: {quality_full['frame_retention_ratio']:.3f} ({quality_full['valid_pixels']}/{quality_full['total_pixels']})")
    print(f"  面积比例: {quality_full['area_ratio']:.3f}")
    print(f"  分析线段数: {quality_full['num_segments_analyzed']}")

    print("\n正在评估CROP模式校正质量...")
    quality_crop = evaluate_correction_quality(image, corrected_crop, params["model"])
    print(f"  质量评分: {quality_crop['quality_score']:.3f}")
    print(f"  平均直线度误差: {quality_crop['mean_straightness_error']:.3f} 像素")
    print(f"  画幅保留比例: {quality_crop['frame_retention_ratio']:.3f} ({quality_crop['valid_pixels']}/{quality_crop['total_pixels']})")
    print(f"  面积比例: {quality_crop['area_ratio']:.3f}")

    print("\n正在评估VR模式校正质量...")
    quality_vr = evaluate_correction_quality(image, equirect, params["model"])
    print(f"  质量评分: {quality_vr['quality_score']:.3f}")
    print(f"  平均直线度误差: {quality_vr['mean_straightness_error']:.3f} 像素")
    print(f"  画幅保留比例: {quality_vr['frame_retention_ratio']:.3f}")
    print(f"  面积比例: {quality_vr['area_ratio']:.3f}")

    print("\n" + "=" * 70)
    print("功能7: 视频鱼眼校正 - 帧间参数一致性")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        print("\n正在创建测试视频...")
        test_video = os.path.join(tmpdir, "test_video.mp4")
        output_video = os.path.join(tmpdir, "corrected_video.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(test_video, fourcc, 30.0, (300, 300))
        for i in range(10):
            frame = generate_synthetic_fisheye_with_lines(size=300)
            out.write(frame)
        out.release()
        print(f"测试视频已创建: {test_video}")

        processor = BatchProcessor(
            distortion_model=params["model"],
            num_workers=1,
        )

        print("\n正在处理视频（参数稳定模式）...")
        video_result = processor.process_video(
            test_video,
            output_video,
            auto_params=False,
            stabilize_params=True,
            calibration_frame_interval=5,
            temporal_smoothing=0.9,
        )

        print(f"处理完成:")
        print(f"  总帧数: {video_result['total_frames']}")
        print(f"  处理帧数: {video_result['processed_frames']}")
        print(f"  输出尺寸: {video_result['output_size']}")
        print(f"  参数稳定: {video_result['stabilized']}")
        if "mean_quality_score" in video_result:
            print(f"  平均质量评分: {video_result['mean_quality_score']:.3f}")
        if "params_stability" in video_result:
            print(f"  焦距标准差: {video_result['params_stability']['focal_std']:.3f}")

        print("\n正在处理视频（VR模式）...")
        vr_output_video = os.path.join(tmpdir, "vr_video.mp4")
        vr_result = processor.process_video(
            test_video,
            vr_output_video,
            auto_params=False,
            use_vr_mode=True,
        )
        print(f"VR模式处理完成，输出尺寸: {vr_result['output_size']}")

    os.makedirs("test_output", exist_ok=True)
    cv2.imwrite("test_output/test_fisheye.jpg", image)
    cv2.imwrite("test_output/test_corrected_full.jpg", corrected_full)
    cv2.imwrite("test_output/test_corrected_crop.jpg", corrected_crop)
    cv2.imwrite("test_output/test_corrected_pad.jpg", corrected_pad)
    cv2.imwrite("test_output/test_equirectangular.jpg", equirect)
    cv2.imwrite("test_output/test_vr_panorama.jpg", vr_panorama)

    print("\n" + "=" * 70)
    print("所有新功能验证完成！")
    print("=" * 70)
    print(f"\n测试图像已保存到 test_output/ 目录:")
    print(f"  - test_fisheye.jpg: 原始鱼眼图像")
    print(f"  - test_corrected_full.jpg: FULL模式校正")
    print(f"  - test_corrected_crop.jpg: CROP模式校正")
    print(f"  - test_corrected_pad.jpg: PAD模式校正")
    print(f"  - test_equirectangular.jpg: 等距柱状投影（VR）")
    print(f"  - test_vr_panorama.jpg: VR全景拼接图")
    print("\n[SUCCESS] 所有新功能正常工作！")


if __name__ == "__main__":
    main()
