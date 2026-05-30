import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from config import Config
from core import SaliencyInferencer, segment_salient_object, overlay_saliency, apply_mask
from utils import save_image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

Config.ensure_dirs()

def example_single_image_demo():
    print("=" * 60)
    print("显著性目标检测 - 单图检测示例")
    print("=" * 60)
    
    inferencer = SaliencyInferencer(model_name='basnet', pretrained=False)
    print(f"\n当前模型: {inferencer.model_name}")
    print(f"设备: {inferencer.device}")
    
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    cv2.circle(test_image, (200, 150), 80, (255, 100, 100), -1)
    cv2.rectangle(test_image, (50, 50), (150, 250), (100, 255, 100), -1)
    test_image_path = os.path.join(Config.INPUT_DIR, 'test_image.png')
    save_image(test_image, test_image_path)
    print(f"\n已创建测试图像: {test_image_path}")
    
    print("\n开始检测...")
    result = inferencer.predict(test_image, threshold=0.5, edge_refinement=True)
    
    print("\n检测完成!")
    print(f"原始图像尺寸: {result['original_size']}")
    print(f"显著图范围: [{result['saliency_map'].min():.4f} - {result['saliency_map'].max():.4f}]")
    
    saliency_gray = (result['saliency_map'] * 255).astype(np.uint8)
    mask_gray = (result['binary_mask'] * 255).astype(np.uint8)
    
    saliency_path = os.path.join(Config.OUTPUT_DIR, 'example_saliency.png')
    mask_path = os.path.join(Config.OUTPUT_DIR, 'example_mask.png')
    
    save_image(saliency_gray, saliency_path)
    save_image(mask_gray, mask_path)
    
    print(f"\n显著图已保存: {saliency_path}")
    print(f"二值掩膜已保存: {mask_path}")
    
    print("\n进行目标分割...")
    seg_result = segment_salient_object(
        result['original_image'],
        result['saliency_map'],
        result['binary_mask']
    )
    
    print(f"检测到 {seg_result['num_objects']} 个显著目标")
    
    segmented_path = os.path.join(Config.OUTPUT_DIR, 'example_segmented.png')
    save_image(seg_result['segmented_rgb'], segmented_path)
    print(f"分割结果已保存: {segmented_path}")
    
    overlay = overlay_saliency(result['original_image'], result['saliency_map'], alpha=0.6)
    overlay_path = os.path.join(Config.OUTPUT_DIR, 'example_overlay.png')
    save_image(overlay, overlay_path)
    print(f"叠加图已保存: {overlay_path}")
    
    print("\n生成对比图...")
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    axes[0, 0].imshow(result['original_image'])
    axes[0, 0].set_title('Original Image')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(result['saliency_map'], cmap='gray')
    axes[0, 1].set_title('Saliency Map')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(result['binary_mask'], cmap='gray')
    axes[0, 2].set_title('Binary Mask')
    axes[0, 2].axis('off')
    
    axes[1, 0].imshow(overlay)
    axes[1, 0].set_title('Overlay')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(seg_result['segmented_rgb'])
    axes[1, 1].set_title('Segmented Object')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(seg_result['alpha_mask'], cmap='gray')
    axes[1, 2].set_title('Alpha Channel')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    comparison_path = os.path.join(Config.OUTPUT_DIR, 'example_comparison.png')
    plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"对比图已保存: {comparison_path}")
    
    print("\n" + "=" * 60)
    print("单图检测示例完成!")
    print("=" * 60)


if __name__ == '__main__':
    example_single_image_demo()
