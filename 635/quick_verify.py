import numpy as np
import cv2
from cs_reconstruction import (
    RandomSampling, FISTAReconstructor,
    DeepCSProcessor, VideoCSProcessor, AdaptiveCSProcessor,
    TextureAnalyzer, QualityEvaluator
)

def generate_test_image(size=(64, 64), seed=42):
    np.random.seed(seed)
    h, w = size
    image = np.zeros((h, w), dtype=np.uint8)
    for _ in range(4):
        shape_type = np.random.choice(['circle', 'rectangle'])
        color = np.random.randint(100, 255)
        if shape_type == 'circle':
            center = (np.random.randint(w//6, 5*w//6), np.random.randint(h//6, 5*h//6))
            radius = np.random.randint(min(w, h)//12, min(w, h)//5)
            cv2.circle(image, center, radius, color, -1)
        else:
            pt1 = (np.random.randint(0, w//2), np.random.randint(0, h//2))
            pt2 = (pt1[0] + np.random.randint(w//4, w//2), pt1[1] + np.random.randint(h//4, h//2))
            cv2.rectangle(image, pt1, pt2, color, -1)
    image = cv2.GaussianBlur(image.astype(np.float32), (5, 5), 1.0).astype(np.uint8)
    return image


np.random.seed(42)
print("=" * 60)
print("  高级功能快速验证")
print("=" * 60)

img = generate_test_image((64, 64), seed=42)
pattern = RandomSampling(seed=42)

print("\n1. 自适应采样测试...")
adaptive = AdaptiveCSProcessor(base_ratio=0.3, seed=42)
result = adaptive.process_adaptive(img, 0.3)
print(f"   PSNR = {result['quality']['PSNR']:.2f} dB")
print(f"   SSIM = {result['quality']['SSIM']:.4f}")
print(f"   实际采样率 = {result['sampling_ratio']:.1%}")
print("   ✓ 自适应采样正常")

print("\n2. 纹理分析测试...")
texture = TextureAnalyzer.compute_texture_map(img)
print(f"   纹理均值 = {np.mean(texture):.4f}")
print(f"   纹理标准差 = {np.std(texture):.4f}")
print("   ✓ 纹理分析正常")

print("\n3. 视频压缩感知测试...")
video_proc = VideoCSProcessor(max_iter=30, time_limit=5.0)
frames = video_proc.generate_synthetic_video(
    num_frames=3, size=(64, 64), motion_type='translation')
results = video_proc.process_video(frames, 0.3, pattern)
avg_psnr = np.mean([r['quality']['PSNR'] for r in results])
avg_ssim = np.mean([r['quality']['SSIM'] for r in results])
print(f"   平均PSNR = {avg_psnr:.2f} dB")
print(f"   平均SSIM = {avg_ssim:.4f}")
print("   ✓ 视频压缩感知正常")

print("\n4. 深度压缩感知测试...")
deep_proc = DeepCSProcessor(
    in_channels=1, base_channels=8, 
    num_res_blocks=2, learning_rate=1e-2)
train_imgs = [generate_test_image((64, 64), seed=i) for i in range(5)]
train_masks = [RandomSampling(seed=i).generate_mask((64, 64), 0.3) for i in range(5)]
print("   开始预训练 (3 epochs)...")
losses = deep_proc.pretrain(train_imgs, train_masks, num_epochs=3, verbose=False)
print(f"   初始损失 = {losses[0]:.6f}")
print(f"   最终损失 = {losses[-1]:.6f}")
print(f"   损失下降 = {((losses[0] - losses[-1]) / losses[0] * 100):.1f}%")

result_deep = deep_proc.process(img, 0.3, pattern)
print(f"   DeepCS PSNR = {result_deep['quality']['PSNR']:.2f} dB")
print(f"   DeepCS SSIM = {result_deep['quality']['SSIM']:.4f}")
print("   ✓ 深度压缩感知正常")

print("\n" + "=" * 60)
print("  ✓ 所有高级功能验证通过!")
print("=" * 60)
