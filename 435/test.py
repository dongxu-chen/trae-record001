import os
import cv2
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Dict
import matplotlib.pyplot as plt
from matplotlib import rcParams

from config import Config
from data import RainSynthesizer
from models import build_model
from utils import calculate_psnr, calculate_ssim
from train import load_checkpoint

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False


def preprocess_image(image: np.ndarray) -> torch.Tensor:
    if image.dtype != np.float32:
        image = image.astype(np.float32) / 255.0
    
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    image = cv2.resize(image, Config.IMAGE_SIZE)
    
    tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
    return tensor


def postprocess_tensor(tensor: torch.Tensor) -> np.ndarray:
    image = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    image = np.clip(image, 0, 1)
    image = (image * 255).astype(np.uint8)
    return image


def derain_image(model: nn.Module, image_path: str, intensity: str = 'medium') -> Dict:
    device = Config.DEVICE
    
    clean_image = cv2.imread(image_path)
    if clean_image is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    clean_rgb = cv2.cvtColor(clean_image, cv2.COLOR_BGR2RGB)
    clean_rgb = cv2.resize(clean_rgb, Config.IMAGE_SIZE)
    
    rain_synthesizer = RainSynthesizer(intensity=intensity)
    rainy_image = rain_synthesizer(clean_rgb)
    
    clean_tensor = torch.from_numpy(clean_rgb.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0).to(device)
    rainy_tensor = torch.from_numpy(rainy_image).permute(2, 0, 1).unsqueeze(0).to(device)
    
    model.eval()
    with torch.no_grad():
        derained_tensor = model(rainy_tensor)
    
    derained_image = postprocess_tensor(derained_tensor)
    rainy_image_vis = (rainy_image * 255).astype(np.uint8)
    
    psnr_input = calculate_psnr(rainy_tensor, clean_tensor)
    ssim_input = calculate_ssim(rainy_tensor, clean_tensor)
    psnr_output = calculate_psnr(derained_tensor, clean_tensor)
    ssim_output = calculate_ssim(derained_tensor, clean_tensor)
    
    return {
        'clean': clean_rgb,
        'rainy': rainy_image_vis,
        'derained': derained_image,
        'psnr_input': psnr_input,
        'ssim_input': ssim_input,
        'psnr_output': psnr_output,
        'ssim_output': ssim_output,
        'intensity': intensity
    }


def visualize_results(results: Dict, save_path: str = None, show: bool = True):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    axes[0].imshow(results['clean'])
    axes[0].set_title('原始清晰图像', fontsize=14)
    axes[0].axis('off')
    
    axes[1].imshow(results['rainy'])
    axes[1].set_title(f'雨纹图像 ({results["intensity"]})\nPSNR: {results["psnr_input"]:.2f}dB, SSIM: {results["ssim_input"]:.4f}', fontsize=14)
    axes[1].axis('off')
    
    axes[2].imshow(results['derained'])
    axes[2].set_title(f'去雨结果\nPSNR: {results["psnr_output"]:.2f}dB, SSIM: {results["ssim_output"]:.4f}', fontsize=14)
    axes[2].axis('off')
    
    psnr_gain = results['psnr_output'] - results['psnr_input']
    ssim_gain = results['ssim_output'] - results['ssim_input']
    
    fig.suptitle(f'单图像去雨结果 - 雨强: {results["intensity"]}\n'
                 f'PSNR提升: {psnr_gain:.2f}dB, SSIM提升: {ssim_gain:.4f}', 
                 fontsize=16, y=1.02)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Results saved to: {save_path}")
    
    if show:
        plt.show()
    
    plt.close()


def compare_intensities(model: nn.Module, image_path: str, save_dir: str = Config.RESULT_DIR):
    os.makedirs(save_dir, exist_ok=True)
    
    intensities = ['light', 'medium', 'heavy']
    all_results = []
    
    for intensity in intensities:
        results = derain_image(model, image_path, intensity)
        all_results.append(results)
        
        save_path = os.path.join(save_dir, f'derain_{intensity}.png')
        visualize_results(results, save_path, show=False)
    
    fig, axes = plt.subplots(3, 3, figsize=(18, 18))
    
    for i, (intensity, results) in enumerate(zip(intensities, all_results)):
        axes[i, 0].imshow(results['clean'])
        axes[i, 0].set_title('原始清晰图像', fontsize=12)
        axes[i, 0].axis('off')
        
        axes[i, 1].imshow(results['rainy'])
        axes[i, 1].set_title(f'雨纹图像 ({intensity})\nPSNR: {results["psnr_input"]:.2f}dB', fontsize=12)
        axes[i, 1].axis('off')
        
        axes[i, 2].imshow(results['derained'])
        axes[i, 2].set_title(f'去雨结果\nPSNR: {results["psnr_output"]:.2f}dB', fontsize=12)
        axes[i, 2].axis('off')
    
    plt.tight_layout()
    comparison_path = os.path.join(save_dir, 'intensity_comparison.png')
    plt.savefig(comparison_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Comparison saved to: {comparison_path}")
    
    return all_results


def batch_test(model: nn.Module, test_dir: str, save_dir: str = Config.RESULT_DIR):
    os.makedirs(save_dir, exist_ok=True)
    
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    test_images = []
    
    for root, _, files in os.walk(test_dir):
        for file in files:
            if file.lower().endswith(image_extensions):
                test_images.append(os.path.join(root, file))
    
    if len(test_images) == 0:
        print("No test images found.")
        return
    
    print(f"Testing on {len(test_images)} images...")
    
    all_psnr_gains = []
    all_ssim_gains = []
    intensity_metrics = {}
    
    for img_path in test_images:
        for intensity in ['light', 'medium', 'heavy']:
            results = derain_image(model, img_path, intensity)
            
            psnr_gain = results['psnr_output'] - results['psnr_input']
            ssim_gain = results['ssim_output'] - results['ssim_input']
            
            all_psnr_gains.append(psnr_gain)
            all_ssim_gains.append(ssim_gain)
            
            if intensity not in intensity_metrics:
                intensity_metrics[intensity] = {'psnr_gain': [], 'ssim_gain': []}
            intensity_metrics[intensity]['psnr_gain'].append(psnr_gain)
            intensity_metrics[intensity]['ssim_gain'].append(ssim_gain)
            
            img_name = os.path.splitext(os.path.basename(img_path))[0]
            save_path = os.path.join(save_dir, f'{img_name}_{intensity}_result.png')
            visualize_results(results, save_path, show=False)
    
    print("\n=== Test Results ===")
    print(f"Average PSNR Gain: {np.mean(all_psnr_gains):.2f} +/- {np.std(all_psnr_gains):.2f} dB")
    print(f"Average SSIM Gain: {np.mean(all_ssim_gains):.4f} +/- {np.std(all_ssim_gains):.4f}")
    
    print("\nPer-intensity results:")
    for intensity, metrics in intensity_metrics.items():
        print(f"  {intensity:8s} - PSNR Gain: {np.mean(metrics['psnr_gain']):.2f}dB, "
              f"SSIM Gain: {np.mean(metrics['ssim_gain']):.4f}")
    
    return intensity_metrics


def main():
    device = Config.DEVICE
    print(f"Using device: {device}")
    
    model = build_model('resnet')
    
    checkpoint_path = os.path.join(Config.CHECKPOINT_DIR, 'best_model.pth')
    if os.path.exists(checkpoint_path):
        print(f"Loading checkpoint from: {checkpoint_path}")
        model, _, _, metrics = load_checkpoint(model, None, checkpoint_path)
        print(f"Checkpoint metrics: {metrics}")
    else:
        print("Warning: No checkpoint found. Using untrained model.")
    
    test_image_path = 'data/test/sample.jpg'
    if os.path.exists(test_image_path):
        print(f"Testing on sample image: {test_image_path}")
        compare_intensities(model, test_image_path)
    else:
        print(f"Test image not found: {test_image_path}")
        print("Please place test images in data/test/ directory.")


if __name__ == '__main__':
    main()
