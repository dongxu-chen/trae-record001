import os
import sys
import argparse
import numpy as np
import cv2
import torch
import matplotlib.pyplot as plt
from matplotlib import rcParams

from config import Config
from data import RainSynthesizer, RandomRainSynthesizer
from models import build_model
from utils import calculate_psnr, calculate_ssim
from train import load_checkpoint
from test import derain_image, visualize_results, compare_intensities, batch_test

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False


def generate_sample_image(save_path: str, size: tuple = (256, 256)):
    h, w = size
    image = np.zeros((h, w, 3), dtype=np.uint8)
    
    image[:h//3, :] = [135, 206, 235]
    image[h//3:2*h//3, :] = [34, 139, 34]
    image[2*h//3:, :] = [139, 69, 19]
    
    for _ in range(5):
        x = np.random.randint(0, w)
        y = np.random.randint(h//3, 2*h//3)
        r = np.random.randint(20, 50)
        color = np.random.randint(100, 255, size=3).tolist()
        cv2.circle(image, (x, y), r, color, -1)
    
    for _ in range(10):
        x1 = np.random.randint(0, w)
        y1 = np.random.randint(2*h//3, h)
        x2 = x1 + np.random.randint(-30, 30)
        y2 = y1 + np.random.randint(-20, 20)
        color = np.random.randint(50, 150, size=3).tolist()
        cv2.line(image, (x1, y1), (x2, y2), color, 3)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    print(f"Sample image generated: {save_path}")
    return image


def demo_synthetic_data():
    print("=" * 60)
    print("合成雨纹数据生成演示")
    print("=" * 60)
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        clean_image = generate_sample_image(sample_path)
    else:
        clean_image = cv2.imread(sample_path)
        clean_image = cv2.cvtColor(clean_image, cv2.COLOR_BGR2RGB)
        clean_image = cv2.resize(clean_image, Config.IMAGE_SIZE)
    
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    
    axes[0].imshow(clean_image)
    axes[0].set_title('原始图像', fontsize=12)
    axes[0].axis('off')
    
    intensities = ['light', 'medium', 'heavy']
    for i, intensity in enumerate(intensities, 1):
        synthesizer = RainSynthesizer(intensity=intensity)
        rainy_image = synthesizer(clean_image)
        rainy_image = (rainy_image * 255).astype(np.uint8)
        
        psnr = calculate_psnr(
            torch.from_numpy(rainy_image.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0),
            torch.from_numpy(clean_image.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        )
        
        axes[i].imshow(rainy_image)
        axes[i].set_title(f'{intensity}雨\nPSNR: {psnr:.2f}dB', fontsize=12)
        axes[i].axis('off')
    
    plt.tight_layout()
    save_path = 'results/synthetic_rain_demo.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Rain synthesis demo saved: {save_path}")
    plt.close()


def demo_untrained_model():
    print("\n" + "=" * 60)
    print("未训练模型去雨演示")
    print("=" * 60)
    
    device = Config.DEVICE
    print(f"Using device: {device}")
    
    model = build_model('resnet')
    print(f"Model loaded: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M parameters")
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        generate_sample_image(sample_path)
    
    print("\nTesting on different rain intensities...")
    all_results = compare_intensities(model, sample_path, save_dir='results/untrained_demo')
    
    print("\nUntrained model results:")
    for results in all_results:
        psnr_gain = results['psnr_output'] - results['psnr_input']
        ssim_gain = results['ssim_output'] - results['ssim_input']
        print(f"  {results['intensity']:8s}: PSNR gain = {psnr_gain:+.2f}dB, SSIM gain = {ssim_gain:+.4f}")


def demo_with_checkpoint(checkpoint_path: str = None):
    print("\n" + "=" * 60)
    print("训练后模型去雨演示")
    print("=" * 60)
    
    device = Config.DEVICE
    model = build_model('resnet')
    
    if checkpoint_path is None:
        checkpoint_path = os.path.join(Config.CHECKPOINT_DIR, 'best_model.pth')
    
    if os.path.exists(checkpoint_path):
        print(f"Loading checkpoint from: {checkpoint_path}")
        model, _, epoch, metrics = load_checkpoint(model, None, checkpoint_path)
        print(f"Checkpoint epoch: {epoch}")
        print(f"Checkpoint metrics: {metrics}")
    else:
        print(f"Warning: Checkpoint not found at {checkpoint_path}")
        print("Using untrained model for demonstration...")
    
    sample_path = 'data/test/sample.jpg'
    if not os.path.exists(sample_path):
        generate_sample_image(sample_path)
    
    all_results = compare_intensities(model, sample_path, save_dir='results/trained_demo')
    
    print("\nTrained model results:")
    for results in all_results:
        psnr_gain = results['psnr_output'] - results['psnr_input']
        ssim_gain = results['ssim_output'] - results['ssim_input']
        print(f"  {results['intensity']:8s}: PSNR gain = {psnr_gain:+.2f}dB, SSIM gain = {ssim_gain:+.4f}")


def run_full_demo():
    print("=" * 60)
    print("单图像去雨算法 - 完整演示")
    print("=" * 60)
    
    print("\n1. 生成合成雨纹数据...")
    demo_synthetic_data()
    
    print("\n2. 未训练模型去雨演示...")
    demo_untrained_model()
    
    checkpoint_path = os.path.join(Config.CHECKPOINT_DIR, 'best_model.pth')
    if os.path.exists(checkpoint_path):
        print("\n3. 训练后模型去雨演示...")
        demo_with_checkpoint(checkpoint_path)
    else:
        print("\n3. 跳过训练后模型演示（未找到checkpoint）")
        print("   请先运行 'python train.py' 训练模型")
    
    print("\n" + "=" * 60)
    print("演示完成！结果保存在 results/ 目录下")
    print("=" * 60)


def demo_gan_training():
    print("\n" + "=" * 60)
    print("GAN对抗训练演示")
    print("=" * 60)
    
    print("\n功能说明:")
    print("  - 使用判别器网络进行对抗训练，缩小合成与真实雨纹的域差异")
    print("  - 大雨样本使用边缘保持损失，保留纹理细节")
    print("  - 训练命令: python train_gan.py")
    print("\nGAN训练特性:")
    print("  1. 判别器类型: PatchGAN / RainGAN / DomainGAN")
    print("  2. 损失函数: LSGAN / Vanilla GAN / WGAN-GP")
    print("  3. 边缘保持: Sobel算子计算边缘损失")
    print("  4. 大雨优化: 额外的HeavyRainLoss包含TV正则化")


def demo_edge_loss_comparison():
    print("\n" + "=" * 60)
    print("边缘保持损失对比演示")
    print("=" * 60)
    
    from utils import EdgeAwareLoss, LaplacianEdgeLoss
    
    print("\n可用的边缘损失函数:")
    print("  1. EdgeAwareLoss (Sobel算子): 检测图像边缘，最小化预测与真实边缘的差异")
    print("  2. LaplacianEdgeLoss (Laplacian算子): 使用二阶导数检测边缘")
    print("  3. CombinedLossWithEdge: MSE + L1 + 边缘损失的组合")
    print("  4. HeavyRainLoss: 专为大雨设计，包含MSE + 边缘 + TV正则化")
    
    print("\n损失权重配置 (config.py):")
    print(f"  - PIXEL_LOSS_WEIGHT = {Config.PIXEL_LOSS_WEIGHT}")
    print(f"  - EDGE_LOSS_WEIGHT = {Config.EDGE_LOSS_WEIGHT}")
    print(f"  - TV_LOSS_WEIGHT = {Config.TV_LOSS_WEIGHT}")
    print(f"  - ADV_LOSS_WEIGHT = {Config.ADV_LOSS_WEIGHT}")


def demo_video_derain():
    print("\n" + "=" * 60)
    print("视频去雨模块演示")
    print("=" * 60)
    
    from video_demo import demo_video_processing_info, create_demo_video
    demo_video_processing_info()
    
    print("\n是否创建演示视频? (y/n)")
    try:
        choice = input().strip().lower()
        if choice == 'y' or choice == 'yes':
            create_demo_video()
    except:
        print("跳过视频创建")


def demo_rain_estimation():
    print("\n" + "=" * 60)
    print("雨量估计演示")
    print("=" * 60)
    
    from video_demo import demo_rain_estimation
    demo_rain_estimation()


def demo_rain_fog_enhance():
    print("\n" + "=" * 60)
    print("雨雾联合增强演示")
    print("=" * 60)
    
    from video_demo import demo_rain_fog_enhancement
    demo_rain_fog_enhancement()


def demo_video_all():
    print("\n" + "=" * 60)
    print("视频增强综合演示")
    print("=" * 60)
    
    from video_demo import main as video_demo_main
    video_demo_main()


def main():
    parser = argparse.ArgumentParser(description='单图像去雨算法演示')
    parser.add_argument('--mode', type=str, default='demo',
                        choices=['demo', 'train', 'train_gan', 'test', 'synthetic', 'untrained', 
                                 'trained', 'gan_info', 'edge_loss', 'evaluate',
                                 'video_derain', 'rain_estimation', 'rain_fog', 'video_all'],
                        help='运行模式')
    parser.add_argument('--checkpoint', type=str, default=None,
                        help='模型checkpoint路径')
    parser.add_argument('--test_dir', type=str, default='data/test',
                        help='测试图像目录')
    parser.add_argument('--intensity', type=str, default='medium',
                        choices=['light', 'medium', 'heavy'],
                        help='雨纹强度')
    
    args = parser.parse_args()
    
    if args.mode == 'demo':
        run_full_demo()
    elif args.mode == 'train':
        from train import main as train_main
        train_main()
    elif args.mode == 'train_gan':
        from train_gan import main as gan_train_main
        gan_train_main()
    elif args.mode == 'test':
        model = build_model('resnet')
        if args.checkpoint and os.path.exists(args.checkpoint):
            model, _, _, _ = load_checkpoint(model, None, args.checkpoint)
        batch_test(model, args.test_dir)
    elif args.mode == 'synthetic':
        demo_synthetic_data()
    elif args.mode == 'untrained':
        demo_untrained_model()
    elif args.mode == 'trained':
        demo_with_checkpoint(args.checkpoint)
    elif args.mode == 'gan_info':
        demo_gan_training()
    elif args.mode == 'edge_loss':
        demo_edge_loss_comparison()
    elif args.mode == 'evaluate':
        from evaluate import demo_subjective_evaluation, demo_comprehensive_evaluation
        demo_subjective_evaluation()
        demo_comprehensive_evaluation()
    elif args.mode == 'video_derain':
        demo_video_derain()
    elif args.mode == 'rain_estimation':
        demo_rain_estimation()
    elif args.mode == 'rain_fog':
        demo_rain_fog_enhance()
    elif args.mode == 'video_all':
        demo_video_all()


if __name__ == '__main__':
    main()
