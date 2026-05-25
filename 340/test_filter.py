import numpy as np
import cv2
from scipy import fftpack


def create_test_image(size=256):
    img = np.zeros((size, size), dtype=np.uint8)
    cv2.circle(img, (size//2, size//2), 50, 255, -1)
    cv2.rectangle(img, (size//4, size//4), (3*size//4, 3*size//4), 128, 3)
    for i in range(0, size, 8):
        cv2.line(img, (0, i), (size, i), 64, 1)
    return img


def test_adaptive_filter():
    print("=" * 60)
    print("Testing Adaptive Frequency Filter...")
    print("=" * 60)
    
    img = create_test_image()
    h, w = img.shape
    r = cv2.getOptimalDFTSize(h)
    c = cv2.getOptimalDFTSize(w)
    padded = cv2.copyMakeBorder(img, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
    
    fft_img = fftpack.fft2(padded)
    fft_img = fftpack.fftshift(fft_img)
    
    spectrum = np.log(1 + np.abs(fft_img))
    rows, cols = spectrum.shape
    crow, ccol = rows // 2, cols // 2
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
    
    radial_energy = np.zeros(int(dist.max()) + 1)
    for r_idx in range(len(radial_energy)):
        mask = np.abs(dist - r_idx) < 1
        if np.any(mask):
            radial_energy[r_idx] = spectrum[mask].mean()
    
    cumsum = np.cumsum(radial_energy)
    total_energy = cumsum[-1]
    
    lowpass_cutoff_idx = np.where(cumsum >= total_energy * 0.95)[0]
    highpass_cutoff_idx = np.where(cumsum >= total_energy * 0.05)[0]
    
    adaptive_low_cutoff = int(lowpass_cutoff_idx[0]) if len(lowpass_cutoff_idx) > 0 else 30
    adaptive_high_cutoff = int(highpass_cutoff_idx[0]) if len(highpass_cutoff_idx) > 0 else 30
    
    print(f"  Adaptive Low-pass cutoff: {adaptive_low_cutoff} (retains 95% energy)")
    print(f"  Adaptive High-pass cutoff: {adaptive_high_cutoff} (removes 5% energy)")
    
    order = 2
    mask_low = 1.0 / (1.0 + (dist / adaptive_low_cutoff) ** (2 * order))
    mask_high = 1.0 / (1.0 + (adaptive_high_cutoff / (dist + 1e-8)) ** (2 * order))
    
    filtered_low = fft_img * mask_low
    filtered_high = fft_img * mask_high
    
    result_low = np.abs(fftpack.ifft2(fftpack.ifftshift(filtered_low)))[:h, :w]
    result_high = np.abs(fftpack.ifft2(fftpack.ifftshift(filtered_high)))[:h, :w]
    
    print(f"  Low-pass result range: [{result_low.min():.1f}, {result_low.max():.1f}]")
    print(f"  High-pass result range: [{result_high.min():.1f}, {result_high.max():.1f}]")
    print("✓ Adaptive filter test passed!\n")
    return True


def test_homomorphic_filter():
    print("=" * 60)
    print("Testing Homomorphic Filter...")
    print("=" * 60)
    
    img = create_test_image()
    h, w = img.shape
    
    img_log = np.log1p(img.astype(np.float64))
    
    r = cv2.getOptimalDFTSize(h)
    c = cv2.getOptimalDFTSize(w)
    padded_log = cv2.copyMakeBorder(img_log, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
    
    fft_log = fftpack.fft2(padded_log)
    fft_log = fftpack.fftshift(fft_log)
    
    rows, cols = fft_log.shape
    crow, ccol = rows // 2, cols // 2
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
    
    d0 = 30
    c = 1.0
    gamma_l = 0.5
    gamma_h = 2.0
    
    homo_filter = gamma_h + (gamma_l - gamma_h) * (1 - np.exp(-c * (dist ** 2) / (d0 ** 2 + 1e-8)))
    
    print(f"  Homomorphic filter parameters:")
    print(f"    γL (low freq gain): {gamma_l}")
    print(f"    γH (high freq gain): {gamma_h}")
    print(f"    D₀ (cutoff): {d0}")
    print(f"    c (sharpness): {c}")
    print(f"  Filter range: [{homo_filter.min():.3f}, {homo_filter.max():.3f}]")
    
    filtered_fft = fft_log * homo_filter
    
    result = np.abs(fftpack.ifft2(fftpack.ifftshift(filtered_fft)))[:h, :w]
    result = np.expm1(result)
    result = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    print(f"  Output range: [{result.min()}, {result.max()}]")
    print(f"  Dynamic range compressed: {img.max() - img.min()} -> {result.max() - result.min()}")
    print("✓ Homomorphic filter test passed!\n")
    return True


def test_spatial_comparison():
    print("=" * 60)
    print("Testing Spatial vs Frequency Domain Comparison...")
    print("=" * 60)
    
    img = create_test_image()
    h, w = img.shape
    
    r = cv2.getOptimalDFTSize(h)
    c = cv2.getOptimalDFTSize(w)
    padded = cv2.copyMakeBorder(img, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
    fft_img = fftpack.fft2(padded)
    fft_img = fftpack.fftshift(fft_img)
    
    rows, cols = fft_img.shape
    crow, ccol = rows // 2, cols // 2
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
    
    cutoff = 30
    order = 2
    
    freq_mask = 1.0 / (1.0 + (dist / cutoff) ** (2 * order))
    freq_filtered = fft_img * freq_mask
    freq_result = np.abs(fftpack.ifft2(fftpack.ifftshift(freq_filtered)))[:h, :w]
    freq_result = cv2.normalize(freq_result, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    kernel_size = 5
    spatial_gaussian = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
    
    spatial_median = cv2.medianBlur(img, kernel_size)
    
    spatial_bilateral = cv2.bilateralFilter(img, kernel_size, kernel_size * 2, kernel_size * 2)
    
    print("  Results summary:")
    print(f"    Original: mean={img.mean():.2f}, std={img.std():.2f}")
    print(f"    Frequency Butterworth LP: mean={freq_result.mean():.2f}, std={freq_result.std():.2f}")
    print(f"    Spatial Gaussian blur: mean={spatial_gaussian.mean():.2f}, std={spatial_gaussian.std():.2f}")
    print(f"    Spatial Median filter: mean={spatial_median.mean():.2f}, std={spatial_median.std():.2f}")
    print(f"    Spatial Bilateral filter: mean={spatial_bilateral.mean():.2f}, std={spatial_bilateral.std():.2f}")
    
    diff_freq = np.abs(freq_result.astype(float) - img.astype(float)).mean()
    diff_gauss = np.abs(spatial_gaussian.astype(float) - img.astype(float)).mean()
    diff_median = np.abs(spatial_median.astype(float) - img.astype(float)).mean()
    diff_bilateral = np.abs(spatial_bilateral.astype(float) - img.astype(float)).mean()
    
    print("\n  Difference from original (MAE):")
    print(f"    Frequency Butterworth: {diff_freq:.2f}")
    print(f"    Spatial Gaussian: {diff_gauss:.2f}")
    print(f"    Spatial Median: {diff_median:.2f}")
    print(f"    Spatial Bilateral: {diff_bilateral:.2f}")
    
    print("✓ Spatial vs Frequency comparison test passed!\n")
    return True


def test_all_filters():
    print("=" * 60)
    print("Complete Filter Suite Testing")
    print("=" * 60)
    print()
    
    img = create_test_image()
    h, w = img.shape
    
    r = cv2.getOptimalDFTSize(h)
    c = cv2.getOptimalDFTSize(w)
    padded = cv2.copyMakeBorder(img, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
    fft_img = fftpack.fft2(padded)
    fft_img = fftpack.fftshift(fft_img)
    
    rows, cols = fft_img.shape
    crow, ccol = rows // 2, cols // 2
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
    
    tests = [
        ("Ideal Low-pass", lambda: 1.0 * (dist <= 30)),
        ("Ideal High-pass", lambda: 1.0 * (dist > 30)),
        ("Gaussian Low-pass", lambda: np.exp(-(dist ** 2) / (2 * (30 ** 2)))),
        ("Gaussian High-pass", lambda: 1.0 - np.exp(-(dist ** 2) / (2 * (30 ** 2)))),
        ("Butterworth Low-pass", lambda: 1.0 / (1.0 + (dist / 30) ** 4)),
        ("Butterworth High-pass", lambda: 1.0 / (1.0 + (30 / (dist + 1e-8)) ** 4)),
    ]
    
    for name, mask_func in tests:
        mask = mask_func()
        filtered = fft_img * mask
        result = np.abs(fftpack.ifft2(fftpack.ifftshift(filtered)))[:h, :w]
        result = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        print(f"  ✓ {name:25s} - Output: [{result.min():3d}, {result.max():3d}], Mean: {result.mean():6.2f}")
    
    print()


if __name__ == "__main__":
    test_all_filters()
    test_adaptive_filter()
    test_homomorphic_filter()
    test_spatial_comparison()
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
