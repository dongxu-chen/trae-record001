import numpy as np
import cv2
import os
import time
from cs_reconstruction import (
    RandomSampling,
    GaussianSampling,
    BlockSampling,
    FISTAReconstructor,
    DeepCSProcessor,
    VideoCSProcessor,
    AdaptiveCSProcessor,
    AdaptiveSampling,
    TextureAnalyzer,
    QualityEvaluator,
    ResultVisualizer,
    ImageHandler,
    visualize_adaptive_sampling,
    get_all_sampling_patterns
)


def generate_test_image(size=(64, 64), seed: int = 42):
    np.random.seed(seed)
    h, w = size
    image = np.zeros((h, w), dtype=np.uint8)
    
    num_shapes = np.random.randint(3, 6)
    for _ in range(num_shapes):
        shape_type = np.random.choice(['circle', 'rectangle', 'ellipse', 'line'])
        color = np.random.randint(100, 255)
        
        if shape_type == 'circle':
            center = (np.random.randint(w//6, 5*w//6), np.random.randint(h//6, 5*h//6))
            radius = np.random.randint(min(w, h)//12, min(w, h)//5)
            cv2.circle(image, center, radius, color, -1)
        
        elif shape_type == 'rectangle':
            pt1 = (np.random.randint(0, w//2), np.random.randint(0, h//2))
            pt2 = (pt1[0] + np.random.randint(w//4, w//2), 
                   pt1[1] + np.random.randint(h//4, h//2))
            cv2.rectangle(image, pt1, pt2, color, -1)
        
        elif shape_type == 'ellipse':
            center = (np.random.randint(w//4, 3*w//4), np.random.randint(h//4, 3*h//4))
            axes = (np.random.randint(w//8, w//4), np.random.randint(h//8, h//4))
            angle = np.random.randint(0, 180)
            cv2.ellipse(image, center, axes, angle, 0, 360, color, -1)
        
        else:
            pt1 = (np.random.randint(0, w), np.random.randint(0, h))
            pt2 = (np.random.randint(0, w), np.random.randint(0, h))
            thickness = np.random.randint(2, 5)
            cv2.line(image, pt1, pt2, color, thickness)
    
    image = cv2.GaussianBlur(image.astype(np.float32), (5, 5), 1.0).astype(np.uint8)
    return image


def generate_training_data(num_images: int = 20, size: Tuple[int, int] = (64, 64), 
                          seed: int = 42) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    images = []
    masks = []
    pattern = RandomSampling(seed=seed)
    
    for i in range(num_images):
        img = generate_test_image(size, seed=seed + i)
        mask = pattern.generate_mask(size, 0.3)
        images.append(img)
        masks.append(mask)
    
    return images, masks


def test_deep_cs():
    print("=" * 70)
    print("测试 1: 深度压缩感知 (Deep Compressed Sensing)")
    print("=" * 70)
    
    print("\n正在生成训练数据...")
    train_images, train_masks = generate_training_data(num_images=15, size=(64, 64), seed=42)
    print(f"训练集: {len(train_images)} 张图像")
    
    print("\n正在初始化深度压缩感知模型...")
    deep_processor = DeepCSProcessor(
        in_channels=1, 
        base_channels=16,  # 减小通道数以加快速度
        num_res_blocks=3,
        learning_rate=1e-3
    )
    
    print("\n开始预训练模型...")
    start_time = time.time()
    losses = deep_processor.pretrain(
        train_images, train_masks,
        num_epochs=10,
        verbose=True
    )
    train_time = time.time() - start_time
    print(f"预训练完成，耗时: {train_time:.2f} 秒")
    
    print("\n正在生成测试图像...")
    test_image = generate_test_image((64, 64), seed=100)
    pattern = RandomSampling(seed=42)
    sampling_ratio = 0.3
    
    print(f"\n测试图像尺寸: {test_image.shape[0]}x{test_image.shape[1]}")
    print(f"采样率: {sampling_ratio:.0%}")
    
    print("\n" + "-" * 70)
    print("方法对比: DeepCS vs FISTA")
    print("-" * 70)
    
    result_deep = deep_processor.process(test_image, sampling_ratio, pattern, 
                                        use_fista_init=True)
    result_fista = deep_processor.process_with_fista(test_image, sampling_ratio, pattern)
    
    print(f"\n{'方法':<15} | {'PSNR(dB)':>10} | {'SSIM':>8} | {'时间(s)':>8}")
    print("-" * 55)
    print(f"{'DeepCS':<15} | {result_deep['quality']['PSNR']:>10.2f} | "
          f"{result_deep['quality']['SSIM']:>8.4f} | {result_deep['processing_time']:>8.2f}")
    print(f"{'FISTA':<15} | {result_fista['quality']['PSNR']:>10.2f} | "
          f"{result_fista['quality']['SSIM']:>8.4f} | {result_fista['processing_time']:>8.2f}")
    
    psnr_improvement = result_deep['quality']['PSNR'] - result_fista['quality']['PSNR']
    ssim_improvement = result_deep['quality']['SSIM'] - result_fista['quality']['SSIM']
    
    print(f"\nDeepCS相对FISTA:")
    print(f"  PSNR提升: {psnr_improvement:+.2f} dB ({'+' if psnr_improvement > 0 else ''}{psnr_improvement/result_fista['quality']['PSNR']*100:.1f}%)")
    print(f"  SSIM提升: {ssim_improvement:+.4f} ({'+' if ssim_improvement > 0 else ''}{ssim_improvement/result_fista['quality']['SSIM']*100:.1f}%)")
    
    print("\n生成深度压缩感知对比图...")
    results = [result_fista, result_deep]
    titles = ['FISTA (TV Only)', 'DeepCS (CNN + FISTA)']
    ResultVisualizer.plot_comparison(results, titles, save_path='deep_cs_comparison.png')
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(1, len(losses)+1), losses, 'o-', linewidth=2, markersize=6)
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Training Loss (MSE)')
    ax.set_title('DeepCS Training Loss Curve')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('deep_cs_training_loss.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\n✓ 深度压缩感知测试完成")
    
    return result_deep, result_fista


def test_video_cs():
    print("\n" + "=" * 70)
    print("测试 2: 视频压缩感知 (Video Compressed Sensing)")
    print("=" * 70)
    
    video_processor = VideoCSProcessor(
        tv_weight=0.5,
        temporal_weight=0.3,
        max_iter=80,
        time_limit=10.0
    )
    
    num_frames = 10
    frame_size = (64, 64)
    
    print(f"\n正在生成合成视频 ({num_frames} 帧, {frame_size[0]}x{frame_size[1]})...")
    print("\n运动模式:")
    print("  1. 平移 (Translation)")
    print("  2. 缩放 (Scaling)")
    print("  3. 旋转 (Rotation)")
    
    motion_types = ['translation', 'scaling', 'rotation']
    all_results = {}
    
    for motion_type in motion_types:
        print(f"\n{'-' * 70}")
        print(f"处理运动模式: {motion_type}")
        print("-" * 70)
        
        frames = video_processor.generate_synthetic_video(
            num_frames=num_frames,
            size=frame_size,
            motion_type=motion_type
        )
        
        pattern = RandomSampling(seed=42)
        sampling_ratio = 0.3
        
        print(f"采样率: {sampling_ratio:.0%}")
        print(f"帧间时间约束权重: {video_processor.reconstructor.temporal_weight}")
        
        results = video_processor.process_video(frames, sampling_ratio, pattern)
        all_results[motion_type] = results
        
        avg_psnr = np.mean([r['quality']['PSNR'] for r in results])
        avg_ssim = np.mean([r['quality']['SSIM'] for r in results])
        avg_time = np.mean([r['processing_time'] for r in results])
        
        print(f"\n平均性能:")
        print(f"  平均PSNR: {avg_psnr:.2f} dB")
        print(f"  平均SSIM: {avg_ssim:.4f}")
        print(f"  平均处理时间: {avg_time:.2f} 秒/帧")
        print(f"  总处理时间: {sum(r['processing_time'] for r in results):.2f} 秒")
        
        print(f"\n生成 {motion_type} 视频结果可视化...")
        video_processor.visualize_video_results(
            results, 
            save_path=f'video_cs_{motion_type}.png',
            max_frames=5
        )
        video_processor.plot_video_quality(
            results, 
            save_path=f'video_cs_quality_{motion_type}.png'
        )
        
        if motion_type == 'translation':
            print("\n帧间相关性分析 (前3帧):")
            for i in range(min(3, len(results)-1)):
                corr = np.corrcoef(results[i]['reconstructed'].flatten(), 
                                  results[i+1]['reconstructed'].flatten())[0, 1]
                print(f"  帧 {i} -> 帧 {i+1}: 相关系数 = {corr:.4f}")
    
    print("\n" + "-" * 70)
    print("不同运动模式对比:")
    print("-" * 70)
    print(f"{'运动模式':<15} | {'平均PSNR(dB)':>12} | {'平均SSIM':>10} | {'总时间(s)':>10}")
    print("-" * 65)
    for motion_type, results in all_results.items():
        avg_psnr = np.mean([r['quality']['PSNR'] for r in results])
        avg_ssim = np.mean([r['quality']['SSIM'] for r in results])
        total_time = sum(r['processing_time'] for r in results)
        print(f"{motion_type:<15} | {avg_psnr:>12.2f} | {avg_ssim:>10.4f} | {total_time:>10.2f}")
    
    print("\n✓ 视频压缩感知测试完成")
    
    return all_results


def test_adaptive_sampling():
    print("\n" + "=" * 70)
    print("测试 3: 自适应采样率 (Adaptive Sampling Rate)")
    print("=" * 70)
    
    print("\n正在生成高纹理测试图像...")
    test_image = generate_test_image((128, 128), seed=42)
    
    base_ratio = 0.3
    min_ratio = 0.05
    max_ratio = 0.8
    block_size = 8
    
    print(f"\n配置:")
    print(f"  基础采样率: {base_ratio:.0%}")
    print(f"  最小采样率: {min_ratio:.0%}")
    print(f"  最大采样率: {max_ratio:.0%}")
    print(f"  块大小: {block_size}x{block_size}")
    
    adaptive_processor = AdaptiveCSProcessor(
        base_ratio=base_ratio,
        min_ratio=min_ratio,
        max_ratio=max_ratio,
        block_size=block_size,
        seed=42
    )
    
    print("\n分析图像纹理...")
    texture_map = TextureAnalyzer.compute_texture_map(test_image)
    
    print(f"  纹理均值: {np.mean(texture_map):.4f}")
    print(f"  纹理标准差: {np.std(texture_map):.4f}")
    print(f"  纹理最大值: {np.max(texture_map):.4f}")
    print(f"  纹理最小值: {np.min(texture_map):.4f}")
    
    print("\n高纹理区域检测 (纹理 > 0.7):")
    high_texture = np.sum(texture_map > 0.7) / texture_map.size * 100
    low_texture = np.sum(texture_map < 0.3) / texture_map.size * 100
    print(f"  高纹理区域占比: {high_texture:.1f}%")
    print(f"  低纹理区域占比: {low_texture:.1f}%")
    
    print("\n" + "-" * 70)
    print("采样策略对比: 自适应 vs 均匀")
    print("-" * 70)
    
    comparison = adaptive_processor.compare_sampling(test_image, base_ratio)
    adaptive = comparison['adaptive']
    uniform = comparison['uniform']
    
    print(f"\n{'指标':<20} | {'自适应采样':>15} | {'均匀采样':>15} | {'差异':>10}")
    print("-" * 70)
    print(f"{'实际采样率':<20} | {adaptive['sampling_ratio']:>15.1%} | "
          f"{uniform['sampling_ratio']:>15.1%} | {'':>10}")
    print(f"{'PSNR (dB)':<20} | {adaptive['quality']['PSNR']:>15.2f} | "
          f"{uniform['quality']['PSNR']:>15.2f} | "
          f"{adaptive['quality']['PSNR'] - uniform['quality']['PSNR']:>+10.2f}")
    print(f"{'SSIM':<20} | {adaptive['quality']['SSIM']:>15.4f} | "
          f"{uniform['quality']['SSIM']:>15.4f} | "
          f"{adaptive['quality']['SSIM'] - uniform['quality']['SSIM']:>+.4f}")
    print(f"{'MS-SSIM':<20} | {adaptive['quality']['MS_SSIM']:>15.4f} | "
          f"{uniform['quality']['MS_SSIM']:>15.4f} | "
          f"{adaptive['quality']['MS_SSIM'] - uniform['quality']['MS_SSIM']:>+.4f}")
    print(f"{'处理时间 (s)':<20} | {adaptive['processing_time']:>15.2f} | "
          f"{uniform['processing_time']:>15.2f} | "
          f"{adaptive['processing_time'] - uniform['processing_time']:>+10.2f}")
    
    psnr_gain = (adaptive['quality']['PSNR'] - uniform['quality']['PSNR']) / uniform['quality']['PSNR'] * 100
    ssim_gain = (adaptive['quality']['SSIM'] - uniform['quality']['SSIM']) / uniform['quality']['SSIM'] * 100
    
    print(f"\n自适应采样相对提升:")
    print(f"  PSNR提升: {psnr_gain:+.1f}%")
    print(f"  SSIM提升: {ssim_gain:+.1f}%")
    
    print("\n生成自适应采样可视化...")
    visualize_adaptive_sampling(comparison, save_path='adaptive_sampling_comparison.png')
    
    print("\n不同采样率下的性能对比...")
    ratios = [0.1, 0.2, 0.3, 0.5, 0.7]
    adaptive_results = []
    uniform_results = []
    
    print(f"\n{'采样率':>8} | {'自适应PSNR':>12} | {'均匀PSNR':>10} | {'自适应SSIM':>12} | {'均匀SSIM':>10}")
    print("-" * 70)
    
    for ratio in ratios:
        comp = adaptive_processor.compare_sampling(test_image, ratio)
        adaptive_results.append(comp['adaptive'])
        uniform_results.append(comp['uniform'])
        print(f"{ratio:>8.1%} | {comp['adaptive']['quality']['PSNR']:>12.2f} | "
              f"{comp['uniform']['quality']['PSNR']:>10.2f} | "
              f"{comp['adaptive']['quality']['SSIM']:>12.4f} | "
              f"{comp['uniform']['quality']['SSIM']:>10.4f}")
    
    print("\n生成采样率-质量曲线...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    adaptive_psnrs = [r['quality']['PSNR'] for r in adaptive_results]
    uniform_psnrs = [r['quality']['PSNR'] for r in uniform_results]
    adaptive_ssims = [r['quality']['SSIM'] for r in adaptive_results]
    uniform_ssims = [r['quality']['SSIM'] for r in uniform_results]
    
    axes[0].plot(ratios, adaptive_psnrs, 'o-', linewidth=2, markersize=8, label='Adaptive')
    axes[0].plot(ratios, uniform_psnrs, 's--', linewidth=2, markersize=8, label='Uniform')
    axes[0].set_xlabel('Sampling Ratio')
    axes[0].set_ylabel('PSNR (dB)')
    axes[0].set_title('PSNR vs Sampling Ratio')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    axes[1].plot(ratios, adaptive_ssims, 'o-', linewidth=2, markersize=8, label='Adaptive')
    axes[1].plot(ratios, uniform_ssims, 's--', linewidth=2, markersize=8, label='Uniform')
    axes[1].set_xlabel('Sampling Ratio')
    axes[1].set_ylabel('SSIM')
    axes[1].set_title('SSIM vs Sampling Ratio')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig('adaptive_vs_uniform_curves.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\n✓ 自适应采样率测试完成")
    
    return comparison


def main():
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 5 + "高级压缩感知功能综合测试 - 深度/视频/自适应" + " " * 5 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\n新增功能:")
    print("  1. 深度压缩感知 (DeepCS) - CNN加速图像重建")
    print("  2. 视频压缩感知 (VideoCS) - 帧间时间相关性约束")
    print("  3. 自适应采样率 (Adaptive) - 纹理区高采样，平滑区低采样")
    print()
    
    np.random.seed(42)
    
    try:
        result_deep = test_deep_cs()
        result_video = test_video_cs()
        result_adaptive = test_adaptive_sampling()
        
        print("\n" + "=" * 70)
        print("🎉 所有高级功能测试完成！")
        print("=" * 70)
        
        generated_files = [
            'deep_cs_comparison.png',
            'deep_cs_training_loss.png',
            'video_cs_translation.png',
            'video_cs_quality_translation.png',
            'video_cs_scaling.png',
            'video_cs_quality_scaling.png',
            'video_cs_rotation.png',
            'video_cs_quality_rotation.png',
            'adaptive_sampling_comparison.png',
            'adaptive_vs_uniform_curves.png'
        ]
        
        print("\n生成的结果文件:")
        for f in generated_files:
            if os.path.exists(f):
                size = os.path.getsize(f) / 1024
                print(f"  ✓ {f:<45} ({size:.1f} KB)")
        
        print("\n" + "=" * 70)
        print("📊 性能总结:")
        print("=" * 70)
        print("  深度压缩感知:")
        print(f"    ✓ 纯NumPy CNN实现 (Conv2D + BatchNorm + Residual)")
        print(f"    ✓ 支持训练和推理")
        print(f"    ✓ FISTA初始化加速收敛")
        print()
        print("  视频压缩感知:")
        print(f"    ✓ 光流运动估计 (Farneback算法)")
        print(f"    ✓ 帧间时间相关性约束")
        print(f"    ✓ 运动掩码自适应权重")
        print(f"    ✓ 支持平移/缩放/旋转多种运动模式")
        print()
        print("  自适应采样率:")
        print(f"    ✓ 多尺度纹理分析 (Laplacian + Sobel + 局部方差)")
        print(f"    ✓ 块级自适应采样率分配")
        print(f"    ✓ 纹理区高采样，平滑区低采样")
        print(f"    ✓ 采样预算智能分配")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
