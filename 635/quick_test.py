import numpy as np
import cv2
from cs_reconstruction import (
    RandomSampling,
    FFTReconstructor,
    CSImageProcessor,
    QualityEvaluator,
    ImageHandler
)

def main():
    print("快速测试 - 压缩感知图像重建系统")
    print("=" * 50)
    
    np.random.seed(42)
    
    h, w = 32, 32
    original = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(original, (w//4, h//4), 5, 200, -1)
    cv2.rectangle(original, (w//2, h//4), (3*w//4, 3*h//4), 150, -1)
    
    print(f"测试图像尺寸: {h}x{w}")
    
    sampling_pattern = RandomSampling()
    reconstructor = FFTReconstructor(tv_weight=0.5, max_iter=50)
    processor = CSImageProcessor(sampling_pattern, reconstructor)
    
    sampling_ratio = 0.3
    print(f"采样率: {sampling_ratio:.1%}")
    
    result = processor.process_image(original, sampling_ratio)
    
    print(f"PSNR: {result['quality']['PSNR']:.2f} dB")
    print(f"SSIM: {result['quality']['SSIM']:.4f}")
    print("=" * 50)
    print("测试完成！系统运行正常。")

if __name__ == "__main__":
    main()
