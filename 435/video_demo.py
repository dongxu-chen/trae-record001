import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from config import Config
from video import (
    VideoRainRemover, RainEstimator, RainFogEnhancer,
    add_fog, add_rain_fog
)
from models import build_model

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False


def demo_rain_estimation():
    print("=" * 60)
    print("雨量估计演示")
    print("=" * 60)
    
    estimator = RainEstimator()
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        print("Sample image not found. Creating synthetic test image...")
        from main import generate_sample_image
        generate_sample_image(sample_path)
    
    image = cv2.imread(sample_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    intensities = ['none', 'light', 'medium', 'heavy']
    results = []
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    for i, intensity in enumerate(intensities):
        if intensity == 'none':
            test_image = image_rgb.copy()
        else:
            from data import RainSynthesizer
            rain_synth = RainSynthesizer(intensity=intensity)
            test_image = (rain_synth(image_rgb) * 255).astype(np.uint8)
        
        result = estimator.estimate(test_image, return_visualization=True)
        
        results.append({
            'true_intensity': intensity,
            'estimated': result.intensity.value,
            'score': result.rain_score,
            'confidence': result.confidence
        })
        
        ax = axes[i // 2, i % 2]
        ax.imshow(result.visualization)
        ax.set_title(f'真实: {intensity} | 估计: {result.intensity.value}\n'
                    f'得分: {result.rain_score:.3f}, 置信度: {result.confidence:.2f}')
        ax.axis('off')
    
    plt.tight_layout()
    save_path = 'results/rain_estimation_demo.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\n雨量估计结果已保存: {save_path}")
    plt.close()
    
    print("\n估计结果汇总:")
    for r in results:
        match = "✓" if r['true_intensity'] == r['estimated'] else "✗"
        print(f"  {match} 真实: {r['true_intensity']:6s} → 估计: {r['estimated']:6s} "
              f"(得分: {r['score']:.3f}, 置信度: {r['confidence']:.2f})")
    
    return results


def demo_rain_fog_enhancement():
    print("\n" + "=" * 60)
    print("雨雾联合增强演示")
    print("=" * 60)
    
    model = build_model('resnet')
    enhancer = RainFogEnhancer(model=model, device=Config.DEVICE)
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        from main import generate_sample_image
        generate_sample_image(sample_path)
    
    image = cv2.imread(sample_path)
    
    scenarios = [
        ('原始图像', lambda x: x),
        ('有雨无雾', lambda x: cv2.cvtColor(
            (add_rain_fog(x, rain_intensity='medium', fog_density=0.0)), 
            cv2.COLOR_BGR2RGB) if len(x.shape)==3 else x),
        ('无雨有雾', lambda x: add_fog(x, density=0.4)),
        ('雨雾混合', lambda x: add_rain_fog(x, rain_intensity='medium', fog_density=0.4))
    ]
    
    fig, axes = plt.subplots(4, 3, figsize=(15, 16))
    
    for i, (scenario_name, degrade_func) in enumerate(scenarios):
        degraded = degrade_func(image.copy())
        
        result = enhancer.process_image(degraded, remove_rain=True, remove_fog=True, enhance=True)
        
        axes[i, 0].imshow(cv2.cvtColor(degraded, cv2.COLOR_BGR2RGB) if len(degraded.shape)==3 else degraded)
        axes[i, 0].set_title(f'{scenario_name}')
        axes[i, 0].axis('off')
        
        axes[i, 1].imshow(cv2.cvtColor(result.fog_removed, cv2.COLOR_BGR2RGB))
        axes[i, 1].set_title(f'去雾后\n雾密度: {result.fog_density:.2f}')
        axes[i, 1].axis('off')
        
        axes[i, 2].imshow(cv2.cvtColor(result.enhanced_image, cv2.COLOR_BGR2RGB))
        axes[i, 2].set_title(f'增强结果\n雨强: {result.rain_intensity}')
        axes[i, 2].axis('off')
    
    plt.tight_layout()
    save_path = 'results/rain_fog_enhancement_demo.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\n雨雾联合增强结果已保存: {save_path}")
    plt.close()


def demo_video_processing_info():
    print("\n" + "=" * 60)
    print("视频去雨功能说明")
    print("=" * 60)
    
    print("""
视频去雨模块特性:
-------------------
1. 帧间时序一致性 (Temporal Consistency)
   - 维护时序缓冲区，平滑多帧去雨结果
   - 减少闪烁现象
   - 可配置时序窗口大小 (默认: 3帧)

2. 光流估计支持
   - Farneback 密集光流
   - DIS 光流 (如果可用)
   - 支持帧间warping

3. 视频处理流程:
   Input Video → 逐帧预处理 → 深度残差去雨网络 
   → 时序平滑 → 逐帧后处理 → Output Video

4. 合成雨纹视频演示:
   - 可自动合成带雨纹的视频
   - 输出: 原始视频 + 带雨视频 + 去雨视频
    """)
    
    print("使用示例:")
    print("  from video import VideoRainRemover")
    print("  remover = VideoRainRemover(checkpoint_path='checkpoints/best_model.pth')")
    print("  remover.process_video('input.mp4', 'output_derained.mp4')")
    print("  remover.process_video_with_synthetic_rain('input.mp4', 'demo.mp4', intensity='medium')")


def create_demo_video(output_dir: str = 'results', num_frames: int = 50):
    print("\n" + "=" * 60)
    print("创建演示视频")
    print("=" * 60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    width, height = 640, 480
    fps = 10
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    demo_video_path = os.path.join(output_dir, 'demo_video.mp4')
    out = cv2.VideoWriter(demo_video_path, fourcc, fps, (width, height))
    
    print(f"生成 {num_frames} 帧演示视频...")
    
    for frame_idx in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        sky_gradient = np.linspace(100, 200, height).reshape(-1, 1)
        frame[:, :, 0] = sky_gradient
        frame[:, :, 1] = sky_gradient + 30
        frame[:, :, 2] = 255
        
        sun_x = width // 2 + int(np.sin(frame_idx * 0.1) * 100)
        sun_y = height // 3
        cv2.circle(frame, (sun_x, sun_y), 30, (255, 255, 0), -1)
        
        for cloud_idx in range(3):
            cloud_x = (frame_idx * 2 + cloud_idx * 200) % width
            cloud_y = 80 + cloud_idx * 40
            cv2.ellipse(frame, (cloud_x, cloud_y), (60, 25), 0, 0, 360, (255, 255, 255), -1)
        
        frame[height//2:, :, 0] = 34
        frame[height//2:, :, 1] = 139
        frame[height//2:, :, 2] = 34
        
        cv2.putText(frame, f"Frame: {frame_idx+1}/{num_frames}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"演示视频已保存: {demo_video_path}")
    
    return demo_video_path


def demo_rain_fog_scene_comparison():
    print("\n" + "=" * 60)
    print("雨雾混合场景对比演示")
    print("=" * 60)
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        from main import generate_sample_image
        generate_sample_image(sample_path)
    
    image = cv2.imread(sample_path)
    
    enhancer = RainFogEnhancer(model=None, device=Config.DEVICE)
    
    scenarios = []
    
    for rain_level in ['none', 'light', 'medium', 'heavy']:
        for fog_level in [0.0, 0.2, 0.4, 0.6]:
            if rain_level == 'none' and fog_level == 0:
                degraded = image.copy()
            elif rain_level == 'none':
                degraded = add_fog(image, density=fog_level)
            else:
                degraded = add_rain_fog(image, rain_intensity=rain_level, fog_density=fog_level)
            
            result = enhancer.process_image(degraded, remove_rain=True, remove_fog=True, enhance=True)
            
            scenarios.append({
                'rain': rain_level,
                'fog': fog_level,
                'input': degraded,
                'output': result.enhanced_image,
                'rain_intensity': result.rain_intensity,
                'fog_density': result.fog_density
            })
    
    print(f"已生成 {len(scenarios)} 种雨雾混合场景")
    print("示例场景:")
    for i, s in enumerate(scenarios[:4]):
        print(f"  场景{i+1}: 雨={s['rain']}, 雾={s['fog']:.1f} "
              f"→ 估计雨强: {s['rain_intensity']}, 估计雾密度: {s['fog_density']:.2f}")
    
    return scenarios


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='视频去雨与雨雾增强演示')
    parser.add_argument('--mode', type=str, default='all',
                       choices=['all', 'rain_estimation', 'rain_fog', 'video_info', 
                                'create_video', 'scenarios'])
    
    args = parser.parse_args()
    
    if args.mode in ['all', 'rain_estimation']:
        demo_rain_estimation()
    
    if args.mode in ['all', 'rain_fog']:
        demo_rain_fog_enhancement()
    
    if args.mode in ['all', 'video_info']:
        demo_video_processing_info()
    
    if args.mode in ['all', 'create_video']:
        create_demo_video()
    
    if args.mode in ['scenarios']:
        demo_rain_fog_scene_comparison()
    
    print("\n" + "=" * 60)
    print("所有演示完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
