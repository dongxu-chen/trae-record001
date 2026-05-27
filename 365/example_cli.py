import numpy as np
import cv2
import os
import glob
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
from hdr_core import (
    CameraResponseCalculator,
    HDRComposer,
    ToneMapper,
    ImageAligner,
    GhostRemoval,
    AdaptiveHDRComposer,
    ResponseCurveLibrary,
    get_response_curve_library,
    compute_response_curve,
    create_hdr,
    tone_map,
    align_images
)


def load_images_from_folder(folder: str):
    image_files = sorted(glob.glob(os.path.join(folder, "img_*.png")))
    if not image_files:
        image_files = sorted(glob.glob(os.path.join(folder, "*.jpg")) +
                            glob.glob(os.path.join(folder, "*.png")))
    
    images = []
    exposures = []
    
    for f in image_files:
        img = cv2.imread(f)
        if img is None:
            continue
        
        exp = None
        basename = os.path.basename(f)
        if "exp_" in basename:
            try:
                exp_str = basename.split("exp_")[1].split(".png")[0]
                exp = float(exp_str)
            except (IndexError, ValueError):
                pass
        
        if exp is None:
            exp = 1.0 / 1000
        
        images.append(img)
        exposures.append(exp)
        print(f"加载: {basename}, 曝光: {exp:.6f}s")
    
    return images, np.array(exposures, dtype=np.float64)


def example_full_pipeline():
    print("=" * 60)
    print("HDR 图像处理完整流程示例")
    print("=" * 60)
    
    test_folder = "test_images"
    
    if not os.path.exists(test_folder) or len(glob.glob(os.path.join(test_folder, "*.png"))) < 2:
        print("\n未找到测试图像，正在生成...")
        from generate_test_images import generate_test_sequence
        exposure_times = [1.0 / 2000, 1.0 / 1000, 1.0 / 500, 1.0 / 250, 1.0 / 125]
        generate_test_sequence(test_folder, exposure_times=exposure_times)
    
    print(f"\n从 {test_folder} 加载图像...")
    images, exposures = load_images_from_folder(test_folder)
    
    if len(images) < 2:
        print("错误: 需要至少2张图像")
        return
    
    print(f"\n加载了 {len(images)} 张图像")
    print(f"图像尺寸: {images[0].shape}")
    print(f"曝光时间范围: {exposures.min():.6f} ~ {exposures.max():.6f} 秒")
    
    print("\n" + "-" * 60)
    print("步骤 0: SIFT 图像配准 (可选)")
    print("-" * 60)
    
    aligner = ImageAligner(max_features=5000)
    print("  执行 SIFT 特征匹配配准...")
    aligned_images = aligner.align_images(images, reference_idx=0)
    print("  图像配准完成")
    
    print("\n" + "-" * 60)
    print("步骤 1: 计算相机响应曲线 (加权最小二乘 + 正则化)")
    print("-" * 60)
    
    calc = CameraResponseCalculator(
        num_samples=100, smoothness=100.0,
        regularization=1.0, max_iter=10
    )
    response_curves = []
    num_channels = images[0].shape[2]
    
    for c in range(num_channels):
        print(f"  计算通道 {c} ({'BGR'[c]}) 的响应曲线...")
        channel_images = [img[:, :, c] for img in aligned_images]
        g, _ = calc.solve_response_curve(channel_images, exposures)
        response_curves.append(g)
    
    print("  响应曲线计算完成 (使用加权最小二乘 + Tikhonov 正则化)")
    
    print("\n" + "-" * 60)
    print("步骤 2: 合成 HDR 图像")
    print("-" * 60)
    
    composer = HDRComposer()
    hdr = composer.compose(aligned_images, exposures, response_curves)
    print(f"HDR 图像尺寸: {hdr.shape}")
    print(f"HDR 数值范围: {hdr.min():.6e} ~ {hdr.max():.6e}")
    
    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)
    
    hdr_path = os.path.join(output_folder, "result.hdr")
    cv2.imwrite(hdr_path, hdr)
    print(f"HDR 图像已保存: {hdr_path}")
    
    print("\n" + "-" * 60)
    print("步骤 3: 色调映射 (含高光压缩)")
    print("-" * 60)
    
    mapper = ToneMapper()
    
    print("\n  Reinhard 色调映射 + 高光压缩...")
    reinhard_result = mapper.reinhard(
        hdr, key=0.18,
        highlight_compression=0.3,
        highlight_threshold=0.8
    )
    reinhard_path = os.path.join(output_folder, "reinhard_result.png")
    cv2.imwrite(reinhard_path, reinhard_result)
    print(f"    已保存: {reinhard_path}")
    
    print("\n  Filmic (ACES) 色调映射 + 高光压缩...")
    filmic_result = mapper.filmic(
        hdr, exposure=1.0, contrast=1.1, saturation=1.0,
        highlight_compression=0.4,
        highlight_threshold=0.85
    )
    filmic_path = os.path.join(output_folder, "filmic_result.png")
    cv2.imwrite(filmic_path, filmic_result)
    print(f"    已保存: {filmic_path}")
    
    print("\n  Gamma 色调映射 + 高光压缩...")
    gamma_result = mapper.gamma_correction(
        hdr, gamma=2.2,
        highlight_compression=0.2,
        highlight_threshold=0.8
    )
    gamma_path = os.path.join(output_folder, "gamma_result.png")
    cv2.imwrite(gamma_path, gamma_result)
    print(f"    已保存: {gamma_path}")
    
    print("\n" + "-" * 60)
    print("步骤 4: 生成可视化结果")
    print("-" * 60)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    colors = ['b', 'g', 'r']
    labels = ['Blue', 'Green', 'Red']
    for c in range(num_channels):
        axes[0, 0].plot(np.arange(256), response_curves[c], 
                        color=colors[c], label=labels[c], linewidth=2)
    axes[0, 0].set_xlabel('像素值 Z')
    axes[0, 0].set_ylabel('log 曝光量 X')
    axes[0, 0].set_title('相机响应曲线')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    mid_idx = len(images) // 2
    mid_img = cv2.cvtColor(images[mid_idx], cv2.COLOR_BGR2RGB)
    axes[0, 1].imshow(mid_img)
    axes[0, 1].set_title(f'输入 LDR (中间曝光)\nExp: {exposures[mid_idx]:.4f}s')
    axes[0, 1].axis('off')
    
    log_hdr = np.log(hdr + 1e-8)
    log_hdr_rgb = cv2.cvtColor(log_hdr, cv2.COLOR_BGR2RGB)
    log_hdr_norm = (log_hdr_rgb - log_hdr_rgb.min()) / (log_hdr_rgb.max() - log_hdr_rgb.min())
    axes[0, 2].imshow(log_hdr_norm)
    axes[0, 2].set_title('HDR 对数显示')
    axes[0, 2].axis('off')
    
    axes[1, 0].imshow(cv2.cvtColor(reinhard_result, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title('Reinhard 色调映射')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(cv2.cvtColor(filmic_result, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title('Filmic (ACES) 色调映射')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(cv2.cvtColor(gamma_result, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title('Gamma 色调映射')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    comparison_path = os.path.join(output_folder, "comparison.png")
    plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"对比图已保存: {comparison_path}")
    
    fig2, ax = plt.subplots(figsize=(10, 5))
    for i, exp in enumerate(exposures):
        img_gray = cv2.cvtColor(images[i], cv2.COLOR_BGR2GRAY)
        hist, bins = np.histogram(img_gray.flatten(), bins=64, range=(0, 256), density=True)
        ax.plot(bins[:-1], hist, label=f'Exp: {exp:.4f}s', alpha=0.7)
    ax.set_xlabel('像素值')
    ax.set_ylabel('归一化频率')
    ax.set_title('输入 LDR 图像直方图对比')
    ax.legend()
    ax.grid(True, alpha=0.3)
    hist_path = os.path.join(output_folder, "input_histograms.png")
    plt.savefig(hist_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"输入直方图已保存: {hist_path}")
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"所有结果保存在: {os.path.abspath(output_folder)}")
    print("=" * 60)


def example_quick_api():
    print("\n" + "=" * 60)
    print("快捷 API 示例")
    print("=" * 60)
    
    test_folder = "test_images"
    
    if not os.path.exists(test_folder) or len(glob.glob(os.path.join(test_folder, "*.png"))) < 2:
        print("\n未找到测试图像，正在生成...")
        from generate_test_images import generate_test_sequence
        exposure_times = [1.0 / 2000, 1.0 / 1000, 1.0 / 500, 1.0 / 250, 1.0 / 125]
        generate_test_sequence(test_folder, exposure_times=exposure_times)
    
    images, exposures = load_images_from_folder(test_folder)
    
    response_curves = compute_response_curve(images, exposures)
    hdr = create_hdr(images, exposures, response_curves)
    result = tone_map(hdr, method='reinhard', key=0.18)
    
    output_folder = "output_quick"
    os.makedirs(output_folder, exist_ok=True)
    
    cv2.imwrite(os.path.join(output_folder, "quick_result.hdr"), hdr)
    cv2.imwrite(os.path.join(output_folder, "quick_result.png"), result)
    
    print(f"快捷处理完成，结果保存在: {os.path.abspath(output_folder)}")


def example_advanced_pipeline():
    print("\n" + "=" * 60)
    print("HDR 高级处理流程示例 (鬼影检测 + 自适应合成 + 曲线库)")
    print("=" * 60)
    
    test_folder = "test_images"
    
    if not os.path.exists(test_folder) or len(glob.glob(os.path.join(test_folder, "*.png"))) < 2:
        print("\n未找到测试图像，正在生成...")
        from generate_test_images import generate_test_sequence
        exposure_times = [1.0 / 2000, 1.0 / 1000, 1.0 / 500, 1.0 / 250, 1.0 / 125]
        generate_test_sequence(test_folder, exposure_times=exposure_times)
    
    print(f"\n从 {test_folder} 加载图像...")
    images, exposures = load_images_from_folder(test_folder)
    
    if len(images) < 2:
        print("错误: 需要至少2张图像")
        return
    
    print(f"加载了 {len(images)} 张图像")
    
    print("\n" + "-" * 60)
    print("步骤 1: SIFT 图像配准")
    print("-" * 60)
    aligner = ImageAligner(max_features=5000)
    aligned_images = aligner.align_images(images, reference_idx=0)
    print("  图像配准完成")
    
    print("\n" + "-" * 60)
    print("步骤 2: 鬼影检测与移除")
    print("-" * 60)
    ghost_remover = GhostRemoval(threshold=25.0, min_ghost_size=100)
    cleaned_images, ghost_masks = ghost_remover.detect_and_remove(
        aligned_images, exposures, reference_idx=0
    )
    total_ghost_pixels = sum(np.sum(mask) for mask in ghost_masks)
    print(f"  检测到鬼影像素总数: {total_ghost_pixels}")
    
    print("\n" + "-" * 60)
    print("步骤 3: 响应曲线库匹配")
    print("-" * 60)
    library = get_response_curve_library()
    print(f"  可用曲线: {library.list_curves()}")
    
    temp_curves = compute_response_curve(cleaned_images, exposures)
    
    best_names = []
    for c in range(len(temp_curves)):
        name, dist = library.match_curve(temp_curves[c])
        best_names.append(name)
        print(f"  通道 {c} ({'BGR'[c]}): 最佳匹配 = {name}, 距离 = {dist:.4f}")
    
    curve_name = max(set(best_names), key=best_names.count)
    print(f"  使用曲线: {curve_name}")
    response_curves = library.get_curves_for_rgb(curve_name)
    
    print("\n" + "-" * 60)
    print("步骤 4: 亮度自适应 HDR 合成")
    print("-" * 60)
    adaptive_composer = AdaptiveHDRComposer(
        block_size=32, overlap=16,
        contrast_weight=1.0, saturation_weight=1.0,
        well_exposedness_weight=1.0
    )
    
    weight_maps = []
    for img in cleaned_images:
        wm = adaptive_composer.compute_weight_map(img)
        weight_maps.append(wm)
    
    print(f"  权重图尺寸: {weight_maps[0].shape}")
    print(f"  权重范围: [{min(wm.min() for wm in weight_maps):.4f}, {max(wm.max() for wm in weight_maps):.4f}]")
    
    hdr = adaptive_composer.compose(cleaned_images, exposures, response_curves)
    print(f"  HDR 图像尺寸: {hdr.shape}")
    print(f"  HDR 数值范围: {hdr.min():.6e} ~ {hdr.max():.6e}")
    
    print("\n" + "-" * 60)
    print("步骤 5: 色调映射 (含高光压缩)")
    print("-" * 60)
    
    output_folder = "output_advanced"
    os.makedirs(output_folder, exist_ok=True)
    
    cv2.imwrite(os.path.join(output_folder, "advanced_result.hdr"), hdr)
    
    for method in ['reinhard', 'filmic', 'gamma']:
        if method == 'reinhard':
            result = tone_map(hdr, method='reinhard', highlight_compression=0.4, highlight_threshold=0.8)
        elif method == 'filmic':
            result = tone_map(hdr, method='filmic', highlight_compression=0.5, highlight_threshold=0.85)
        else:
            result = tone_map(hdr, method='gamma', highlight_compression=0.3, highlight_threshold=0.8)
        
        path = os.path.join(output_folder, f"{method}_result.png")
        cv2.imwrite(path, result)
        print(f"  {method} 色调映射已保存: {path}")
    
    print("\n" + "-" * 60)
    print("步骤 6: 生成可视化结果")
    print("-" * 60)
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    
    mid_idx = len(cleaned_images) // 2
    axes[0, 0].imshow(cv2.cvtColor(cleaned_images[mid_idx], cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title('去鬼影后图像 (中间)')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(ghost_masks[mid_idx], cmap='Reds')
    axes[0, 1].set_title('鬼影掩码')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(weight_maps[mid_idx], cmap='hot')
    axes[0, 2].set_title('自适应权重图')
    axes[0, 2].axis('off')
    
    colors = ['b', 'g', 'r']
    for c in range(3):
        axes[0, 3].plot(np.arange(256), response_curves[c], color=colors[c], label=f'Channel {c}')
    axes[0, 3].set_title(f'响应曲线 ({curve_name})')
    axes[0, 3].legend()
    axes[0, 3].grid(True, alpha=0.3)
    
    reinhard_img = cv2.imread(os.path.join(output_folder, "reinhard_result.png"))
    axes[1, 0].imshow(cv2.cvtColor(reinhard_img, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title('Reinhard + 高光压缩')
    axes[1, 0].axis('off')
    
    filmic_img = cv2.imread(os.path.join(output_folder, "filmic_result.png"))
    axes[1, 1].imshow(cv2.cvtColor(filmic_img, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title('Filmic + 高光压缩')
    axes[1, 1].axis('off')
    
    gamma_img = cv2.imread(os.path.join(output_folder, "gamma_result.png"))
    axes[1, 2].imshow(cv2.cvtColor(gamma_img, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title('Gamma + 高光压缩')
    axes[1, 2].axis('off')
    
    log_hdr = np.log(hdr + 1e-8)
    log_hdr_rgb = cv2.cvtColor(log_hdr, cv2.COLOR_BGR2RGB)
    log_hdr_norm = (log_hdr_rgb - log_hdr_rgb.min()) / (log_hdr_rgb.max() - log_hdr_rgb.min())
    axes[1, 3].imshow(log_hdr_norm)
    axes[1, 3].set_title('HDR 对数显示')
    axes[1, 3].axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "advanced_comparison.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\n" + "=" * 60)
    print(f"高级处理完成! 结果保存在: {os.path.abspath(output_folder)}")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            example_quick_api()
        elif sys.argv[1] == "advanced":
            example_advanced_pipeline()
    else:
        example_full_pipeline()
