import os
import glob
import cv2
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple


def load_image(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot load image from {image_path}")
    return img


def save_image(image_path: str, img: np.ndarray) -> None:
    cv2.imwrite(image_path, img)


def get_image_files(input_dir: str, extensions: List[str] = None) -> List[str]:
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(input_dir, f'*{ext}')))
        image_files.extend(glob.glob(os.path.join(input_dir, f'*{ext.upper()}')))
    return sorted(list(set(image_files)))


def estimate_batch_haze_density(dehazer, input_dir: str, 
                                 show_progress: bool = True) -> dict:
    image_files = get_image_files(input_dir)
    if not image_files:
        print(f"No images found in {input_dir}")
        return {}
    haze_densities = {}
    total = len(image_files)
    if show_progress:
        print(f"\nPre-estimating haze density for {total} images...")
    for idx, img_path in enumerate(image_files, 1):
        try:
            img = load_image(img_path)
            if hasattr(dehazer, 'estimate_haze_density'):
                haze_density = dehazer.estimate_haze_density(img)
            else:
                haze_density = 0.5
            haze_densities[img_path] = haze_density
            if show_progress:
                print(f"  [{idx}/{total}] {os.path.basename(img_path)}: "
                      f"haze_density={haze_density:.3f}")
        except Exception as e:
            print(f"Error estimating {img_path}: {str(e)}")
            haze_densities[img_path] = 0.5
    if show_progress and haze_densities:
        values = list(haze_densities.values())
        print(f"\nHaze density statistics:")
        print(f"  Min: {min(values):.3f}, Max: {max(values):.3f}")
        print(f"  Mean: {np.mean(values):.3f}, Median: {np.median(values):.3f}")
    return haze_densities


def batch_dehaze(dehazer, input_dir: str, output_dir: str, 
                 show_progress: bool = True,
                 pre_estimate_haze: bool = True) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    image_files = get_image_files(input_dir)
    if not image_files:
        print(f"No images found in {input_dir}")
        return []
    haze_densities = {}
    if pre_estimate_haze and hasattr(dehazer, 'estimate_haze_density'):
        haze_densities = estimate_batch_haze_density(dehazer, input_dir, show_progress)
    processed_files = []
    total = len(image_files)
    if show_progress:
        print(f"\nProcessing {total} images...")
    for idx, img_path in enumerate(image_files, 1):
        try:
            img = load_image(img_path)
            haze_density = haze_densities.get(img_path, None)
            if hasattr(dehazer, 'dehaze_with_info') and haze_density is not None:
                dehazed, info = dehazer.dehaze_with_info(img)
                info_str = (f"haze={info['haze_density']:.2f}, "
                           f"omega={info['omega']:.2f}, "
                           f"str={info['strength']:.2f}")
            else:
                dehazed = dehazer.dehaze(img, haze_density=haze_density) if haze_density else dehazer.dehaze(img)
                info_str = f"haze={haze_density:.2f}" if haze_density else ""
            filename = os.path.basename(img_path)
            output_path = os.path.join(output_dir, f'dehazed_{filename}')
            save_image(output_path, dehazed)
            processed_files.append(output_path)
            if show_progress:
                print(f"  [{idx}/{total}] {filename} -> {os.path.basename(output_path)} "
                      f"[{info_str}]")
        except Exception as e:
            print(f"Error processing {img_path}: {str(e)}")
    print(f"\nCompleted. Processed {len(processed_files)}/{total} images.")
    return processed_files


def batch_dehaze_with_report(dehazer, input_dir: str, output_dir: str, 
                             show_progress: bool = True) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    image_files = get_image_files(input_dir)
    if not image_files:
        print(f"No images found in {input_dir}")
        return {}
    haze_densities = estimate_batch_haze_density(dehazer, input_dir, show_progress)
    report = {
        'input_dir': input_dir,
        'output_dir': output_dir,
        'total_images': len(image_files),
        'images': []
    }
    processed_files = []
    total = len(image_files)
    if show_progress:
        print(f"\nProcessing {total} images with detailed report...")
    for idx, img_path in enumerate(image_files, 1):
        try:
            img = load_image(img_path)
            haze_density = haze_densities.get(img_path, 0.5)
            if hasattr(dehazer, 'dehaze_with_info'):
                dehazed, info = dehazer.dehaze_with_info(img)
            else:
                dehazed = dehazer.dehaze(img, haze_density=haze_density)
                info = {'haze_density': haze_density}
            filename = os.path.basename(img_path)
            output_path = os.path.join(output_dir, f'dehazed_{filename}')
            save_image(output_path, dehazed)
            processed_files.append(output_path)
            info['input_path'] = img_path
            info['output_path'] = output_path
            report['images'].append(info)
            if show_progress:
                haze = info.get('haze_density', 0)
                strength = info.get('strength', 1.0)
                sky_ratio = info.get('sky_ratio', 0)
                print(f"  [{idx}/{total}] {filename}: haze={haze:.2f}, "
                      f"str={strength:.2f}, sky={sky_ratio:.2f}")
        except Exception as e:
            print(f"Error processing {img_path}: {str(e)}")
    report['processed_count'] = len(processed_files)
    report['success'] = len(processed_files) == total
    return report


def visualize_results(original: np.ndarray, dehazed: np.ndarray, 
                      transmission: np.ndarray = None,
                      save_path: str = None, figsize: Tuple[int, int] = (15, 5)) -> None:
    original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    dehazed_rgb = cv2.cvtColor(dehazed, cv2.COLOR_BGR2RGB)
    if transmission is not None:
        fig, axes = plt.subplots(1, 3, figsize=figsize)
        axes[0].imshow(original_rgb)
        axes[0].set_title('Hazy Image')
        axes[0].axis('off')
        axes[1].imshow(transmission, cmap='gray')
        axes[1].set_title('Transmission Map')
        axes[1].axis('off')
        axes[2].imshow(dehazed_rgb)
        axes[2].set_title('Dehazed Image')
        axes[2].axis('off')
    else:
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].imshow(original_rgb)
        axes[0].set_title('Hazy Image')
        axes[0].axis('off')
        axes[1].imshow(dehazed_rgb)
        axes[1].set_title('Dehazed Image')
        axes[1].axis('off')
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Comparison saved to {save_path}")
    plt.show()


def create_synthetic_hazy_image(clear_img: np.ndarray, 
                                haze_level: float = 0.6,
                                atmospheric_light: int = 220) -> np.ndarray:
    clear_float = clear_img.astype(np.float32) / 255.0
    atmospheric = np.ones_like(clear_float) * (atmospheric_light / 255.0)
    transmission = 1.0 - haze_level
    hazy = clear_float * transmission + atmospheric * (1 - transmission)
    hazy = np.clip(hazy * 255, 0, 255).astype(np.uint8)
    return hazy


def adjust_brightness_contrast(img: np.ndarray, 
                               brightness: int = 0, 
                               contrast: int = 0) -> np.ndarray:
    img = img.astype(np.int32)
    img = img * (1 + contrast / 100.0) + brightness
    img = np.clip(img, 0, 255).astype(np.uint8)
    return img


def calculate_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr


def resize_image(img: np.ndarray, max_size: int = 1024) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_size:
        return img
    scale = max_size / max(h, w)
    new_h = int(h * scale)
    new_w = int(w * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def calculate_edge_density(img: np.ndarray, threshold: int = 30) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    edge_magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    edge_count = np.sum(edge_magnitude > threshold)
    total_pixels = gray.shape[0] * gray.shape[1]
    return edge_count / total_pixels


def calculate_visible_edge_ratio(hazy_img: np.ndarray, dehazed_img: np.ndarray, 
                                 threshold: int = 30) -> dict:
    hazy_density = calculate_edge_density(hazy_img, threshold)
    dehazed_density = calculate_edge_density(dehazed_img, threshold)
    if hazy_density > 0:
        improvement_ratio = dehazed_density / hazy_density
    else:
        improvement_ratio = 1.0
    return {
        'hazy_edge_density': hazy_density,
        'dehazed_edge_density': dehazed_density,
        'edge_improvement_ratio': improvement_ratio,
        'new_visible_edges': dehazed_density - hazy_density
    }


def calculate_contrast(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return np.std(gray)


def calculate_contrast_improvement(hazy_img: np.ndarray, dehazed_img: np.ndarray) -> dict:
    hazy_contrast = calculate_contrast(hazy_img)
    dehazed_contrast = calculate_contrast(dehazed_img)
    if hazy_contrast > 0:
        improvement_ratio = dehazed_contrast / hazy_contrast
    else:
        improvement_ratio = 1.0
    return {
        'hazy_contrast': hazy_contrast,
        'dehazed_contrast': dehazed_contrast,
        'contrast_improvement_ratio': improvement_ratio
    }


def calculate_entropy(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.ravel() / hist.sum()
    hist = hist[hist > 0]
    entropy = -np.sum(hist * np.log2(hist))
    return entropy


def evaluate_dehazing(hazy_img: np.ndarray, dehazed_img: np.ndarray, 
                      clear_img: np.ndarray = None, edge_threshold: int = 30) -> dict:
    metrics = {}
    edge_metrics = calculate_visible_edge_ratio(hazy_img, dehazed_img, edge_threshold)
    metrics.update(edge_metrics)
    contrast_metrics = calculate_contrast_improvement(hazy_img, dehazed_img)
    metrics.update(contrast_metrics)
    metrics['hazy_entropy'] = calculate_entropy(hazy_img)
    metrics['dehazed_entropy'] = calculate_entropy(dehazed_img)
    if metrics['hazy_entropy'] > 0:
        metrics['entropy_improvement_ratio'] = metrics['dehazed_entropy'] / metrics['hazy_entropy']
    else:
        metrics['entropy_improvement_ratio'] = 1.0
    if clear_img is not None:
        metrics['psnr'] = calculate_psnr(clear_img, dehazed_img)
        metrics['ssim'] = calculate_ssim(clear_img, dehazed_img)
    overall_score = (
        edge_metrics['edge_improvement_ratio'] * 0.4 +
        contrast_metrics['contrast_improvement_ratio'] * 0.3 +
        metrics.get('entropy_improvement_ratio', 1.0) * 0.3
    )
    metrics['overall_quality_score'] = overall_score
    return metrics


def calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float64)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY).astype(np.float64)
    mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)
    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2
    sigma1_sq = cv2.GaussianBlur(img1 * img1, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 * img2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return np.mean(ssim_map)


def print_evaluation_report(metrics: dict, title: str = "Dehazing Evaluation") -> None:
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)
    print(f"Edge Density:")
    print(f"  Hazy:    {metrics['hazy_edge_density']:.4f}")
    print(f"  Dehazed: {metrics['dehazed_edge_density']:.4f}")
    print(f"  New Visible Edges: {metrics['new_visible_edges']:.4f}")
    print(f"  Edge Improvement Ratio: {metrics['edge_improvement_ratio']:.2f}x")
    print(f"\nContrast:")
    print(f"  Hazy:    {metrics['hazy_contrast']:.2f}")
    print(f"  Dehazed: {metrics['dehazed_contrast']:.2f}")
    print(f"  Contrast Improvement Ratio: {metrics['contrast_improvement_ratio']:.2f}x")
    print(f"\nEntropy:")
    print(f"  Hazy:    {metrics['hazy_entropy']:.2f}")
    print(f"  Dehazed: {metrics['dehazed_entropy']:.2f}")
    print(f"  Entropy Improvement Ratio: {metrics.get('entropy_improvement_ratio', 1.0):.2f}x")
    if 'psnr' in metrics:
        print(f"\nReference Metrics:")
        print(f"  PSNR: {metrics['psnr']:.2f} dB")
        print(f"  SSIM: {metrics['ssim']:.4f}")
    print(f"\nOverall Quality Score: {metrics['overall_quality_score']:.2f}")
    print("=" * 60 + "\n")


def adaptive_enhance(img: np.ndarray, haze_density: float = None, 
                     strength: float = 0.5) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_float = l.astype(np.float32) / 255.0
    if haze_density is not None:
        clip_limit = 1.0 + haze_density * 2.0
        tile_grid_size = max(4, int(8 - haze_density * 4))
    else:
        clip_limit = 2.0
        tile_grid_size = 8
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    l_enhanced = clahe.apply(l)
    gain = 1.0 + strength * 0.2
    l_enhanced = np.clip(l_enhanced * gain, 0, 255).astype(np.uint8)
    lab_enhanced = cv2.merge((l_enhanced, a, b))
    enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    return enhanced


def dehaze_with_enhancement(dehazer, img: np.ndarray, enhance_strength: float = 0.5,
                            haze_density: float = None) -> tuple:
    if haze_density is None and hasattr(dehazer, 'estimate_haze_density'):
        haze_density = dehazer.estimate_haze_density(img)
    dehazed = dehazer.dehaze(img, haze_density=haze_density)
    if enhance_strength > 0:
        enhanced = adaptive_enhance(dehazed, haze_density, enhance_strength)
    else:
        enhanced = dehazed
    return enhanced, dehazed, haze_density
