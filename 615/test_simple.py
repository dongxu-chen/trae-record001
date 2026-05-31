import numpy as np
from scipy.ndimage import shift, rotate
import matplotlib.pyplot as plt
from phase_correlation import PhaseCorrelationRegistrator
from quality_metrics import RegistrationQualityEvaluator


def test_translation_only():
    print("Testing Translation-Only Registration...")
    
    size = 256
    x = np.linspace(-3, 3, size)
    y = np.linspace(-3, 3, size)
    X, Y = np.meshgrid(x, y)
    
    ref_img = np.exp(-(X**2 + Y**2)) * 255
    for i in range(5):
        cx = np.random.uniform(-2, 2)
        cy = np.random.uniform(-2, 2)
        ref_img += 80 * np.exp(-((X-cx)**2 + (Y-cy)**2) / 0.05)
    ref_img += np.random.randn(size, size) * 3
    ref_img = np.clip(ref_img, 0, 255)
    
    true_dx, true_dy = 15.3, -8.7
    target_img = shift(ref_img, (true_dy, true_dx), order=3, mode='constant', cval=0)
    
    print(f"True translation: dx={true_dx}, dy={true_dy}")
    
    registrator = PhaseCorrelationRegistrator(use_gpu=False)
    
    for upsample in [1, 5, 10]:
        dx, dy, corr = registrator.estimate_translation(ref_img, target_img, upsample_factor=upsample)
        error = np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2)
        print(f"  Upsample {upsample:2d}x: dx={dx:7.3f}, dy={dy:7.3f}, error={error:.4f} px")
    
    dx, dy, corr = registrator.estimate_translation(ref_img, target_img, upsample_factor=10)
    registered = shift(target_img, (-dy, -dx), order=3, mode='constant', cval=0)
    
    evaluator = RegistrationQualityEvaluator()
    quality = evaluator.evaluate_all(ref_img, registered)
    
    print(f"\nQuality after registration:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    axes[0, 0].imshow(ref_img, cmap='gray')
    axes[0, 0].set_title('Reference')
    axes[0, 1].imshow(target_img, cmap='gray')
    axes[0, 1].set_title('Target (shifted)')
    axes[1, 0].imshow(registered, cmap='gray')
    axes[1, 0].set_title('Registered')
    axes[1, 1].imshow(corr, cmap='viridis')
    axes[1, 1].set_title('Correlation Peak')
    plt.tight_layout()
    plt.savefig('test_translation.png', dpi=100)
    plt.close()
    
    print("\nSaved test_translation.png")
    return {'translation': (dx, dy), 'transformed': registered}


def test_rotation_only():
    print("\nTesting Rotation-Only Registration...")
    
    size = 256
    x = np.linspace(-3, 3, size)
    y = np.linspace(-3, 3, size)
    X, Y = np.meshgrid(x, y)
    
    ref_img = np.exp(-(X**2 + Y**2)) * 255
    for i in range(3):
        cx = np.random.uniform(-1.5, 1.5)
        cy = np.random.uniform(-1.5, 1.5)
        ref_img += 50 * np.exp(-((X-cx)**2 + (Y-cy)**2) / 0.1)
    ref_img += np.random.randn(size, size) * 3
    ref_img = np.clip(ref_img, 0, 255)
    
    true_rotation = 15.0
    target_img = rotate(ref_img, true_rotation, reshape=False, order=3, mode='constant', cval=0)
    
    print(f"True rotation: {true_rotation}°")
    
    registrator = PhaseCorrelationRegistrator(use_gpu=False)
    rotation, scale, corr_lp = registrator.estimate_rotation_scale(ref_img, target_img)
    print(f"Estimated rotation: {rotation:.2f}°, scale: {scale:.4f}")
    print(f"Rotation error: {abs(rotation - true_rotation):.4f}°")
    
    result = registrator.register(ref_img, target_img, upsample_factor=5)
    
    evaluator = RegistrationQualityEvaluator()
    quality = evaluator.evaluate_all(ref_img, result['transformed'])
    
    print(f"Quality after registration:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(ref_img, cmap='gray')
    axes[0].set_title('Reference')
    axes[1].imshow(target_img, cmap='gray')
    axes[1].set_title(f'Target (rotated {true_rotation}°)')
    axes[2].imshow(result['transformed'], cmap='gray')
    axes[2].set_title('Registered')
    plt.tight_layout()
    plt.savefig('test_rotation.png', dpi=100)
    plt.close()
    
    print("\nSaved test_rotation.png")
    return result


if __name__ == "__main__":
    np.random.seed(42)
    test_translation_only()
    test_rotation_only()
    print("\nAll tests completed!")
