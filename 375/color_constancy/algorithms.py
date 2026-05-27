import numpy as np
import cv2
from scipy import stats
from scipy.ndimage import gaussian_filter


def gray_world(image, mask=None):
    """
    Gray World Algorithm for illuminant estimation.
    Assumes the average reflectance in a scene is achromatic (gray).
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    img = image.astype(np.float32)
    
    if mask is not None:
        valid_pixels = img[mask]
    else:
        valid_pixels = img.reshape(-1, 3)
    
    means = np.mean(valid_pixels, axis=0)
    
    illuminant = means / np.linalg.norm(means)
    
    return illuminant


def gray_world_block(image, block_size=32, overlap=8, mask=None, sigma=1.5):
    """
    Block-based Local Gray World Algorithm for complex lighting adaptation.
    Divides image into overlapping blocks, estimates illuminant per block,
    and combines using Gaussian weighting.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        block_size: Size of each block (default: 32)
        overlap: Overlap between adjacent blocks (default: 8)
        mask: Optional mask for valid pixels (H, W) bool
        sigma: Gaussian sigma for block weighting (default: 1.5)
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
        block_illuminants: Per-block illuminant estimates for visualization
    """
    img = image.astype(np.float32)
    h, w = img.shape[:2]
    
    step = block_size - overlap
    
    block_illuminants = []
    block_weights = []
    block_centers = []
    
    for y in range(0, h - block_size + 1, step):
        for x in range(0, w - block_size + 1, step):
            block = img[y:y+block_size, x:x+block_size]
            
            if mask is not None:
                block_mask = mask[y:y+block_size, x:x+block_size]
                if np.sum(block_mask) < block_size * block_size * 0.1:
                    continue
                block_pixels = block[block_mask]
            else:
                block_pixels = block.reshape(-1, 3)
            
            if len(block_pixels) < 10:
                continue
            
            block_mean = np.mean(block_pixels, axis=0)
            
            block_std = np.std(block_pixels, axis=0)
            texture_energy = np.sum(block_std)
            weight = 1.0 / (1.0 + texture_energy / 100.0)
            
            brightness = np.mean(block_mean)
            if brightness < 10 or brightness > 245:
                weight *= 0.5
            
            center_y = y + block_size // 2
            center_x = x + block_size // 2
            
            block_illuminants.append(block_mean)
            block_weights.append(weight)
            block_centers.append((center_y, center_x))
    
    if len(block_illuminants) == 0:
        return gray_world(image, mask), None
    
    block_illuminants = np.array(block_illuminants)
    block_weights = np.array(block_weights)
    
    center_y = h // 2
    center_x = w // 2
    spatial_weights = np.exp(-((np.array([c[0] - center_y for c in block_centers]) ** 2 + 
                               np.array([c[1] - center_x for c in block_centers]) ** 2) / 
                              (2 * sigma ** 2 * max(h, w) ** 2)))
    
    combined_weights = block_weights * spatial_weights
    combined_weights = combined_weights / np.sum(combined_weights)
    
    weighted_illuminant = np.sum(block_illuminants * combined_weights[:, np.newaxis], axis=0)
    illuminant = weighted_illuminant / np.linalg.norm(weighted_illuminant)
    
    return illuminant, block_illuminants


def gray_world_multiscale(image, scales=[32, 64, 128], mask=None):
    """
    Multi-scale Block-based Gray World Algorithm.
    Combines estimates at multiple scales for robustness.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        scales: List of block sizes to use (default: [32, 64, 128])
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    h, w = image.shape[:2]
    
    scale_estimates = []
    scale_weights = []
    
    for scale in scales:
        if scale > min(h, w):
            continue
        
        overlap = scale // 4
        est, _ = gray_world_block(image, block_size=scale, overlap=overlap, mask=mask)
        
        img_small = cv2.resize(image, (max(w//4, 32), max(h//4, 32)))
        mask_small = None
        if mask is not None:
            mask_small = cv2.resize(mask.astype(np.uint8), 
                                   (max(w//4, 32), max(h//4, 32))).astype(bool)
        
        std_est = gray_world(img_small, mask_small)
        consistency = 1.0 / (1.0 + angular_error(est, std_est) * 0.1)
        
        scale_estimates.append(est)
        scale_weights.append(consistency * (1.0 / scale))
    
    if len(scale_estimates) == 0:
        return gray_world(image, mask)
    
    scale_estimates = np.array(scale_estimates)
    scale_weights = np.array(scale_weights)
    scale_weights = scale_weights / np.sum(scale_weights)
    
    combined = np.sum(scale_estimates * scale_weights[:, np.newaxis], axis=0)
    illuminant = combined / np.linalg.norm(combined)
    
    return illuminant


def local_white_balance(image, method='gray_world', block_size=64, overlap=16):
    """
    Local White Balance Correction for complex lighting scenarios.
    Applies per-pixel illuminant estimation using local blocks.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8
        method: Method for local estimation - 'gray_world', 'shades_of_gray'
        block_size: Size of local blocks (default: 64)
        overlap: Overlap between blocks (default: 16)
    
    Returns:
        corrected: Locally white balanced image (H, W, 3) in uint8
        illuminant_map: Per-pixel illuminant estimates (H, W, 3)
    """
    from .white_balance import correct_white_balance
    
    img_float = image.astype(np.float32)
    h, w = img_float.shape[:2]
    
    step = block_size - overlap
    
    illuminant_map = np.zeros((h, w, 3), dtype=np.float32)
    weight_map = np.zeros((h, w), dtype=np.float32)
    
    for y in range(0, h - block_size + 1, step):
        for x in range(0, w - block_size + 1, step):
            block = image[y:y+block_size, x:x+block_size]
            
            if method == 'gray_world':
                illum = gray_world(block)
            elif method == 'shades_of_gray':
                illum = shades_of_gray(block, p=6.0)
            else:
                illum = gray_world(block)
            
            gaussian_weight = np.zeros((block_size, block_size), dtype=np.float32)
            cy, cx = block_size // 2, block_size // 2
            sigma = block_size / 4
            for by in range(block_size):
                for bx in range(block_size):
                    gaussian_weight[by, bx] = np.exp(-((by - cy)**2 + (bx - cx)**2) / (2 * sigma**2))
            
            illuminant_map[y:y+block_size, x:x+block_size] += illum.reshape(1, 1, 3) * gaussian_weight[:, :, np.newaxis]
            weight_map[y:y+block_size, x:x+block_size] += gaussian_weight
    
    weight_map[weight_map == 0] = 1e-8
    illuminant_map = illuminant_map / weight_map[:, :, np.newaxis]
    
    norm = np.linalg.norm(illuminant_map, axis=2, keepdims=True)
    norm[norm == 0] = 1e-8
    illuminant_map_normalized = illuminant_map / norm
    
    target = np.ones(3, dtype=np.float32) / np.sqrt(3)
    gains = target / (illuminant_map_normalized + 1e-8)
    
    corrected = img_float * gains
    corrected = np.clip(corrected, 0, 255).astype(np.uint8)
    
    return corrected, illuminant_map_normalized


def angular_error(est_illuminant, gt_illuminant, degrees=True):
    """
    Calculate angular error between two illuminants (helper function).
    """
    est = np.array(est_illuminant, dtype=np.float32)
    gt = np.array(gt_illuminant, dtype=np.float32)
    
    est_norm = est / (np.linalg.norm(est) + 1e-8)
    gt_norm = gt / (np.linalg.norm(gt) + 1e-8)
    
    dot = np.clip(np.sum(est_norm * gt_norm), -1.0, 1.0)
    error = np.arccos(dot)
    
    if degrees:
        error = np.degrees(error)
    
    return error


def perfect_reflection(image, percentile=99, mask=None):
    """
    Perfect Reflection (White Patch) Algorithm for illuminant estimation.
    Assumes the scene contains a perfect white patch that reflects all light.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        percentile: Percentile to use for white point (default: 99)
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    img = image.astype(np.float32)
    
    if mask is not None:
        valid_pixels = img[mask]
    else:
        valid_pixels = img.reshape(-1, 3)
    
    max_vals = np.percentile(valid_pixels, percentile, axis=0)
    
    illuminant = max_vals / np.linalg.norm(max_vals)
    
    return illuminant


def shades_of_gray(image, p=6.0, mask=None):
    """
    Shades of Gray Algorithm for illuminant estimation.
    Generalizes Gray World (p=1) and White Patch (p→∞) using Minkowski norm.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        p: Minkowski norm exponent (default: 6.0)
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    img = image.astype(np.float32)
    
    if mask is not None:
        valid_pixels = img[mask]
    else:
        valid_pixels = img.reshape(-1, 3)
    
    if np.isinf(p):
        minkowski = np.max(valid_pixels, axis=0)
    else:
        minkowski = np.power(np.mean(np.power(valid_pixels, p), axis=0), 1.0 / p)
    
    illuminant = minkowski / np.linalg.norm(minkowski)
    
    return illuminant


def gray_world_weighted(image, sigma=0.2, mask=None):
    """
    Weighted Gray World Algorithm.
    Pixels with chromaticity closer to gray have higher weights.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        sigma: Controls weight decay (default: 0.2)
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    img = image.astype(np.float32)
    
    if mask is not None:
        valid_pixels = img[mask]
    else:
        valid_pixels = img.reshape(-1, 3)
    
    norm = np.linalg.norm(valid_pixels, axis=1, keepdims=True)
    norm[norm == 0] = 1e-8
    normalized = valid_pixels / norm
    
    gray_point = np.ones(3) / np.sqrt(3)
    distances = np.linalg.norm(normalized - gray_point, axis=1)
    weights = np.exp(-distances ** 2 / (2 * sigma ** 2))
    weights = weights / np.sum(weights)
    
    weighted_means = np.sum(valid_pixels * weights[:, np.newaxis], axis=0)
    illuminant = weighted_means / np.linalg.norm(weighted_means)
    
    return illuminant


def gamut_mapping(image, num_bins=32, mask=None):
    """
    Gamut Mapping Algorithm for illuminant estimation.
    Uses the distribution of pixel colors in the chromaticity space.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        num_bins: Number of bins for chromaticity histogram
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        illuminant: Estimated illuminant RGB values [R, G, B] normalized
    """
    img = image.astype(np.float32)
    
    if mask is not None:
        valid_pixels = img[mask]
    else:
        valid_pixels = img.reshape(-1, 3)
    
    sum_rgb = np.sum(valid_pixels, axis=1)
    valid = sum_rgb > 0
    
    chroma_r = valid_pixels[valid, 0] / sum_rgb[valid]
    chroma_g = valid_pixels[valid, 1] / sum_rgb[valid]
    
    hist, r_edges, g_edges = np.histogram2d(chroma_r, chroma_g, bins=num_bins)
    
    r_centers = (r_edges[:-1] + r_edges[1:]) / 2
    g_centers = (g_edges[:-1] + g_edges[1:]) / 2
    r_grid, g_grid = np.meshgrid(r_centers, g_centers)
    
    peak_idx = np.unravel_index(np.argmax(hist), hist.shape)
    peak_r = r_grid[peak_idx]
    peak_g = g_grid[peak_idx]
    peak_b = 1 - peak_r - peak_g
    
    illuminant = np.array([peak_r, peak_g, peak_b])
    illuminant = illuminant / np.linalg.norm(illuminant)
    
    return illuminant
