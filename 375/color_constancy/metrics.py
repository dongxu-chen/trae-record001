import numpy as np
import cv2
from scipy import spatial


def angular_error(est_illuminant, gt_illuminant, degrees=True):
    """
    Calculate angular error between estimated and ground truth illuminants.
    
    Args:
        est_illuminant: Estimated illuminant (3,) or (N, 3)
        gt_illuminant: Ground truth illuminant (3,) or (N, 3)
        degrees: If True, return degrees, else radians
    
    Returns:
        error: Angular error in degrees or radians
    """
    est = np.array(est_illuminant, dtype=np.float32)
    gt = np.array(gt_illuminant, dtype=np.float32)
    
    if est.ndim == 1:
        est = est.reshape(1, 3)
    if gt.ndim == 1:
        gt = gt.reshape(1, 3)
    
    est_norm = est / (np.linalg.norm(est, axis=1, keepdims=True) + 1e-8)
    gt_norm = gt / (np.linalg.norm(gt, axis=1, keepdims=True) + 1e-8)
    
    dot_product = np.sum(est_norm * gt_norm, axis=1)
    dot_product = np.clip(dot_product, -1.0, 1.0)
    
    error = np.arccos(dot_product)
    
    if degrees:
        error = np.degrees(error)
    
    if error.size == 1:
        return error[0]
    return error


def mean_angular_error(errors):
    """
    Calculate mean angular error.
    
    Args:
        errors: Array of angular errors
    
    Returns:
        mae: Mean angular error
    """
    return np.mean(errors)


def median_angular_error(errors):
    """
    Calculate median angular error.
    
    Args:
        errors: Array of angular errors
    
    Returns:
        median: Median angular error
    """
    return np.median(errors)


def trimean_angular_error(errors):
    """
    Calculate trimean of angular errors (robust measure of central tendency).
    Trimean = (Q1 + 2*Q2 + Q3) / 4
    
    Args:
        errors: Array of angular errors
    
    Returns:
        trimean: Trimean of angular errors
    """
    q1 = np.percentile(errors, 25)
    q2 = np.percentile(errors, 50)
    q3 = np.percentile(errors, 75)
    return (q1 + 2 * q2 + q3) / 4


def best_25_percentile(errors):
    """
    Calculate mean of best 25% errors.
    
    Args:
        errors: Array of angular errors
    
    Returns:
        best25: Mean of best 25% errors
    """
    sorted_errors = np.sort(errors)
    n = len(sorted_errors)
    best = sorted_errors[:int(n * 0.25)]
    return np.mean(best)


def worst_25_percentile(errors):
    """
    Calculate mean of worst 25% errors.
    
    Args:
        errors: Array of angular errors
    
    Returns:
        worst25: Mean of worst 25% errors
    """
    sorted_errors = np.sort(errors)
    n = len(sorted_errors)
    worst = sorted_errors[-int(n * 0.25):]
    return np.mean(worst)


def delta_e_ciede2000(img1, img2, mask=None):
    """
    Calculate CIEDE2000 color difference between two images.
    
    Args:
        img1: First image (H, W, 3) BGR uint8
        img2: Second image (H, W, 3) BGR uint8
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        delta_e: Array of ΔE values or mean ΔE
    """
    lab1 = cv2.cvtColor(img1, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab2 = cv2.cvtColor(img2, cv2.COLOR_BGR2LAB).astype(np.float32)
    
    L1, a1, b1 = lab1[:, :, 0], lab1[:, :, 1], lab1[:, :, 2]
    L2, a2, b2 = lab2[:, :, 0], lab2[:, :, 1], lab2[:, :, 2]
    
    kL = 1.0
    kC = 1.0
    kH = 1.0
    
    L1_prime = L1
    L2_prime = L2
    
    C1 = np.sqrt(a1 ** 2 + b1 ** 2)
    C2 = np.sqrt(a2 ** 2 + b2 ** 2)
    C_mean = (C1 + C2) / 2
    
    G = 0.5 * (1 - np.sqrt(C_mean ** 7 / (C_mean ** 7 + 25 ** 7)))
    
    a1_prime = a1 * (1 + G)
    a2_prime = a2 * (1 + G)
    
    C1_prime = np.sqrt(a1_prime ** 2 + b1 ** 2)
    C2_prime = np.sqrt(a2_prime ** 2 + b2 ** 2)
    
    h1_prime = np.arctan2(b1, a1_prime)
    h1_prime[h1_prime < 0] += 2 * np.pi
    h2_prime = np.arctan2(b2, a2_prime)
    h2_prime[h2_prime < 0] += 2 * np.pi
    
    dL_prime = L2_prime - L1_prime
    dC_prime = C2_prime - C1_prime
    
    dh_prime = h2_prime - h1_prime
    dh_prime = np.where(np.abs(dh_prime) > np.pi, 
                        np.where(dh_prime > np.pi, dh_prime - 2 * np.pi, dh_prime + 2 * np.pi),
                        dh_prime)
    dH_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(dh_prime / 2)
    
    L_mean_prime = (L1_prime + L2_prime) / 2
    C_mean_prime = (C1_prime + C2_prime) / 2
    
    h_mean_prime = (h1_prime + h2_prime) / 2
    h_mean_prime = np.where(np.abs(h1_prime - h2_prime) > np.pi,
                            np.where(h1_prime + h2_prime < 2 * np.pi, h_mean_prime + np.pi, h_mean_prime - np.pi),
                            h_mean_prime)
    
    T = 1 - 0.17 * np.cos(h_mean_prime - np.pi / 6) \
        + 0.24 * np.cos(2 * h_mean_prime) \
        + 0.32 * np.cos(3 * h_mean_prime + np.pi / 30) \
        - 0.20 * np.cos(4 * h_mean_prime - 21 * np.pi / 60)
    
    dTheta = 30 * np.pi / 180 * np.exp(-((h_mean_prime - 275 * np.pi / 180) / (25 * np.pi / 180)) ** 2)
    R_C = 2 * np.sqrt(C_mean_prime ** 7 / (C_mean_prime ** 7 + 25 ** 7))
    S_L = 1 + 0.015 * (L_mean_prime - 50) ** 2 / np.sqrt(20 + (L_mean_prime - 50) ** 2)
    S_C = 1 + 0.045 * C_mean_prime
    S_H = 1 + 0.015 * C_mean_prime * T
    R_T = -np.sin(2 * dTheta) * R_C
    
    delta_e = np.sqrt(
        (dL_prime / (kL * S_L)) ** 2 +
        (dC_prime / (kC * S_C)) ** 2 +
        (dH_prime / (kH * S_H)) ** 2 +
        R_T * (dC_prime / (kC * S_C)) * (dH_prime / (kH * S_H))
    )
    
    if mask is not None:
        delta_e = delta_e[mask]
    
    return delta_e


def mean_delta_e(img1, img2, mask=None):
    """
    Calculate mean CIEDE2000 color difference.
    
    Args:
        img1: First image (H, W, 3) BGR uint8
        img2: Second image (H, W, 3) BGR uint8
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        mean_de: Mean ΔE value
    """
    de = delta_e_ciede2000(img1, img2, mask)
    return np.mean(de)


def psnr(img1, img2, mask=None):
    """
    Calculate Peak Signal-to-Noise Ratio (PSNR) between two images.
    
    Args:
        img1: First image (H, W, 3)
        img2: Second image (H, W, 3)
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        psnr_value: PSNR in dB
    """
    img1_f = img1.astype(np.float32)
    img2_f = img2.astype(np.float32)
    
    mse = (img1_f - img2_f) ** 2
    
    if mask is not None:
        mse = mse[mask]
    
    mse = np.mean(mse)
    
    if mse == 0:
        return float('inf')
    
    max_val = 255.0
    psnr_value = 10 * np.log10(max_val ** 2 / mse)
    
    return psnr_value


def ssim(img1, img2, mask=None, window_size=11, k1=0.01, k2=0.03, L=255):
    """
    Calculate Structural Similarity Index (SSIM) between two images.
    
    Args:
        img1: First image (H, W, 3)
        img2: Second image (H, W, 3)
        mask: Optional mask for valid pixels (H, W) bool
        window_size: Gaussian window size
        k1, k2: SSIM parameters
        L: Dynamic range
    
    Returns:
        ssim_value: SSIM index (0-1)
    """
    from scipy.ndimage import gaussian_filter
    
    img1_f = img1.astype(np.float32)
    img2_f = img2.astype(np.float32)
    
    if img1_f.ndim == 3:
        ssim_values = []
        for c in range(3):
            ssim_c = _ssim_single_channel(img1_f[:, :, c], img2_f[:, :, c], 
                                           window_size, k1, k2, L)
            ssim_values.append(ssim_c)
        ssim_map = np.mean(ssim_values, axis=0)
    else:
        ssim_map = _ssim_single_channel(img1_f, img2_f, window_size, k1, k2, L)
    
    if mask is not None:
        ssim_map = ssim_map[mask]
    
    return np.mean(ssim_map)


def _ssim_single_channel(img1, img2, window_size, k1, k2, L):
    """Calculate SSIM for a single channel."""
    from scipy.ndimage import gaussian_filter
    
    sigma = 1.5
    C1 = (k1 * L) ** 2
    C2 = (k2 * L) ** 2
    
    mu1 = gaussian_filter(img1, sigma)
    mu2 = gaussian_filter(img2, sigma)
    
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = gaussian_filter(img1 ** 2, sigma) - mu1_sq
    sigma2_sq = gaussian_filter(img2 ** 2, sigma) - mu2_sq
    sigma12 = gaussian_filter(img1 * img2, sigma) - mu1_mu2
    
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    
    return ssim_map


def evaluate_illuminant_estimation(estimates, ground_truths):
    """
    Comprehensive evaluation of illuminant estimation.
    
    Args:
        estimates: Estimated illuminants (N, 3)
        ground_truths: Ground truth illuminants (N, 3)
    
    Returns:
        metrics: Dictionary of evaluation metrics
    """
    errors = angular_error(estimates, ground_truths)
    
    metrics = {
        'angular_errors': errors,
        'mean': mean_angular_error(errors),
        'median': median_angular_error(errors),
        'trimean': trimean_angular_error(errors),
        'best25': best_25_percentile(errors),
        'worst25': worst_25_percentile(errors),
        'min': np.min(errors),
        'max': np.max(errors),
        'std': np.std(errors)
    }
    
    return metrics


def evaluate_white_balance(corrected_images, reference_images, masks=None):
    """
    Evaluate white balance correction quality.
    
    Args:
        corrected_images: List of corrected images (N)
        reference_images: List of reference/ground truth images (N)
        masks: Optional list of masks (N)
    
    Returns:
        metrics: Dictionary of evaluation metrics
    """
    n = len(corrected_images)
    delta_e_values = []
    psnr_values = []
    ssim_values = []
    
    for i in range(n):
        mask = masks[i] if masks is not None else None
        
        de = mean_delta_e(corrected_images[i], reference_images[i], mask)
        p = psnr(corrected_images[i], reference_images[i], mask)
        s = ssim(corrected_images[i], reference_images[i], mask)
        
        delta_e_values.append(de)
        psnr_values.append(p)
        ssim_values.append(s)
    
    metrics = {
        'delta_e': {
            'values': delta_e_values,
            'mean': np.mean(delta_e_values),
            'median': np.median(delta_e_values),
            'std': np.std(delta_e_values)
        },
        'psnr': {
            'values': psnr_values,
            'mean': np.mean(psnr_values),
            'median': np.median(psnr_values),
            'std': np.std(psnr_values)
        },
        'ssim': {
            'values': ssim_values,
            'mean': np.mean(ssim_values),
            'median': np.median(ssim_values),
            'std': np.std(ssim_values)
        }
    }
    
    return metrics


def evaluate_stability(method, images, masks=None, num_runs=5, perturbation_intensity=0.05):
    """
    Evaluate algorithm stability by measuring output variance under
    small perturbations and repeated runs.
    
    Args:
        method: Illuminant estimation function
        images: List of test images (N)
        masks: Optional list of masks (N)
        num_runs: Number of repeated runs
        perturbation_intensity: Intensity of noise perturbation
    
    Returns:
        stability_metrics: Dictionary containing stability metrics
    """
    n = len(images)
    all_estimates = []
    
    for run in range(num_runs):
        run_estimates = []
        for i, img in enumerate(images):
            mask = masks[i] if masks is not None else None
            
            if run > 0 and perturbation_intensity > 0:
                noise = np.random.normal(0, perturbation_intensity * 255, img.shape).astype(np.float32)
                img_perturbed = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
            else:
                img_perturbed = img
            
            est = method(img_perturbed, mask=mask)
            run_estimates.append(est)
        
        all_estimates.append(np.array(run_estimates))
    
    all_estimates = np.array(all_estimates)
    
    mean_estimates = np.mean(all_estimates, axis=0)
    
    std_estimates = np.std(all_estimates, axis=0)
    mean_std = np.mean(std_estimates, axis=0)
    overall_std = np.mean(mean_std)
    
    angular_errors_between_runs = []
    for r1 in range(num_runs):
        for r2 in range(r1 + 1, num_runs):
            ae = angular_error(all_estimates[r1], all_estimates[r2])
            if np.isscalar(ae):
                angular_errors_between_runs.append(ae)
            else:
                angular_errors_between_runs.extend(ae)
    
    mean_angular_variation = np.mean(angular_errors_between_runs)
    std_angular_variation = np.std(angular_errors_between_runs)
    
    coefficient_of_variation = overall_std / (np.mean(np.linalg.norm(mean_estimates, axis=1)) + 1e-8)
    
    stability_metrics = {
        'num_runs': num_runs,
        'perturbation_intensity': perturbation_intensity,
        'mean_estimates': mean_estimates,
        'std_per_estimate': std_estimates,
        'mean_std_per_channel': mean_std,
        'overall_mean_std': overall_std,
        'mean_angular_variation_deg': mean_angular_variation,
        'std_angular_variation_deg': std_angular_variation,
        'coefficient_of_variation': coefficient_of_variation,
        'all_estimates': all_estimates
    }
    
    return stability_metrics


def delta_e_standard_deviation(img1, img2, mask=None):
    """
    Calculate standard deviation of CIEDE2000 color difference.
    
    Args:
        img1: First image (H, W, 3) BGR uint8
        img2: Second image (H, W, 3) BGR uint8
        mask: Optional mask for valid pixels (H, W) bool
    
    Returns:
        std_de: Standard deviation of ΔE values
        mean_de: Mean ΔE value
        all_de: All ΔE values
    """
    de = delta_e_ciede2000(img1, img2, mask)
    
    std_de = np.std(de)
    mean_de = np.mean(de)
    
    return std_de, mean_de, de


def evaluate_color_difference_stability(corrected_images, reference_images, masks=None):
    """
    Evaluate color difference stability across images.
    
    Args:
        corrected_images: List of corrected images (N)
        reference_images: List of reference/ground truth images (N)
        masks: Optional list of masks (N)
    
    Returns:
        metrics: Dictionary of color difference stability metrics
    """
    n = len(corrected_images)
    
    all_delta_e_means = []
    all_delta_e_stds = []
    all_delta_e_values = []
    
    for i in range(n):
        mask = masks[i] if masks is not None else None
        
        std_de, mean_de, de_values = delta_e_standard_deviation(
            corrected_images[i], reference_images[i], mask
        )
        
        all_delta_e_means.append(mean_de)
        all_delta_e_stds.append(std_de)
        all_delta_e_values.extend(de_values.flatten())
    
    metrics = {
        'delta_e_std_per_image': {
            'values': all_delta_e_stds,
            'mean': np.mean(all_delta_e_stds),
            'median': np.median(all_delta_e_stds),
            'std': np.std(all_delta_e_stds),
            'min': np.min(all_delta_e_stds),
            'max': np.max(all_delta_e_stds)
        },
        'delta_e_mean_per_image': {
            'values': all_delta_e_means,
            'mean': np.mean(all_delta_e_means),
            'std': np.std(all_delta_e_means)
        },
        'overall_delta_e_distribution': {
            'all_values': np.array(all_delta_e_values),
            'mean': np.mean(all_delta_e_values),
            'std': np.std(all_delta_e_values),
            'percentile_5': np.percentile(all_delta_e_values, 5),
            'percentile_95': np.percentile(all_delta_e_values, 95)
        }
    }
    
    return metrics
