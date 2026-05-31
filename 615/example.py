import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import affine_transform, shift, rotate
import os

from phase_correlation import PhaseCorrelationRegistrator
from quality_metrics import RegistrationQualityEvaluator
from visualization import RegistrationVisualizer
from batch_registration import BatchRegistrator


def generate_test_image(size=256):
    x = np.linspace(-4, 4, size)
    y = np.linspace(-4, 4, size)
    X, Y = np.meshgrid(x, y)
    
    img = np.zeros((size, size))
    
    for i in range(8):
        cx = np.random.uniform(-3, 3)
        cy = np.random.uniform(-3, 3)
        sigma = np.random.uniform(0.1, 0.5)
        amplitude = np.random.uniform(0.3, 1.0)
        img += amplitude * np.exp(-((X - cx)**2 + (Y - cy)**2) / (2 * sigma**2))
    
    img += 0.02 * np.random.randn(size, size)
    img = (img - img.min()) / (img.max() - img.min()) * 255
    
    return img.astype(np.float32)


def example_translation_only():
    print("=" * 60)
    print("Example 1: Translation-Only Registration (Subpixel Accuracy")
    print("=" * 60)
    
    ref_img = generate_test_image(256)
    
    true_dx, true_dy = 12.73, -9.42
    target_img = shift(ref_img, (true_dy, true_dx), order=3, mode='constant', cval=0)
    
    print(f"\nTrue translation: dx={true_dx}, dy={true_dy}")
    
    registrator = PhaseCorrelationRegistrator()
    
    errors = []
    for i in range(5):
        dx, dy, _ = registrator.estimate_translation(ref_img, target_img)
        error = np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2)
        errors.append(error)
    
    dx, dy, correlation = registrator.estimate_translation(ref_img, target_img)
    error = np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2)
    
    print(f"\nEstimated: dx={dx:.4f}, dy={dy:.4f}")
    print(f"Error: {error:.4f} pixels")
    
    registered = shift(target_img, (-dy, -dx), order=3, mode='constant', cval=0)
    
    evaluator = RegistrationQualityEvaluator()
    quality = evaluator.evaluate_all(ref_img, registered)
    
    print(f"\nQuality after registration:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    print(f"  PSNR: {quality['psnr']:.2f} dB")
    
    visualizer = RegistrationVisualizer()
    
    fig2 = visualizer.plot_correlation_peak(correlation, dx, dy)
    fig2.savefig('example1_correlation.png', dpi=150, bbox_inches='tight')
    
    fig3 = visualizer.plot_overlay_comparison(ref_img, registered)
    fig3.savefig('example1_overlay.png', dpi=150, bbox_inches='tight')
    
    print("\nFigures saved: example1_correlation.png, example1_overlay.png")
    plt.close('all')


def example_rotation_only():
    print("\n" + "=" * 60)
    print("Example 2: High-Precision Rotation Registration")
    print("=" * 60)
    
    ref_img = generate_test_image(256)
    
    true_rotation = 22.37
    target_img = rotate(ref_img, true_rotation, reshape=False, order=3, mode='constant', cval=0)
    
    print(f"\nTrue rotation: {true_rotation}°")
    
    registrator = PhaseCorrelationRegistrator()
    rotation, scale, corr_lp = registrator.estimate_rotation_scale(ref_img, target_img)
    
    print(f"Estimated rotation: {rotation:.4f}°, scale: {scale:.4f}")
    print(f"Rotation error: {abs(rotation - true_rotation):.4f}°")
    
    registered = rotate(target_img, -rotation, reshape=False, order=3, mode='constant', cval=0)
    
    evaluator = RegistrationQualityEvaluator()
    quality = evaluator.evaluate_all(ref_img, registered)
    
    print(f"\nQuality after registration:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    print(f"  PSNR: {quality['psnr']:.2f} dB")
    
    print("\nHigh-precision rotation registration complete!")
    plt.close('all')


def example_full_registration():
    print("\n" + "=" * 60)
    print("Example 3: Full Registration (Translation + Rotation")
    print("=" * 60)
    
    ref_img = generate_test_image(256)
    
    true_dx, true_dy = 8.51, -5.23
    true_rotation = 15.79
    
    print(f"\nTrue transformation:")
    print(f"  Translation: ({true_dx}, {true_dy})")
    print(f"  Rotation: {true_rotation}°")
    
    target_img = rotate(ref_img, true_rotation, reshape=False, order=3, mode='constant', cval=0)
    target_img = shift(target_img, (true_dy, true_dx), order=3, mode='constant', cval=0)
    
    registrator = PhaseCorrelationRegistrator()
    result = registrator.register(ref_img, target_img)
    
    dx, dy = result['translation']
    rotation = result['rotation']
    scale = result['scale']
    
    print(f"\nEstimated transformation:")
    print(f"  Translation: ({dx:.4f}, {dy:.4f})")
    print(f"  Rotation: {rotation:.4f}°")
    print(f"  Scale: {scale:.4f}")
    
    print(f"\nErrors:")
    print(f"  Translation error: {np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2):.4f} pixels")
    print(f"  Rotation error: {abs(rotation - true_rotation):.4f}°")
    
    evaluator = RegistrationQualityEvaluator()
    quality = evaluator.evaluate_all(ref_img, result['transformed'])
    
    print(f"\nQuality after registration:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    print(f"  PSNR: {quality['psnr']:.2f} dB")
    
    visualizer = RegistrationVisualizer()
    
    fig1 = visualizer.plot_registration_result(
        ref_img, target_img, result['transformed'],
        (dx, dy), rotation, scale, quality
    )
    fig1.savefig('example3_full_registration.png', dpi=150, bbox_inches='tight')
    
    print("\nFigure saved: example3_full_registration.png")
    plt.close('all')


def example_batch_registration():
    print("\n" + "=" * 60)
    print("Example 4: Batch Registration")
    print("=" * 60)
    
    os.makedirs('test_images', exist_ok=True)
    os.makedirs('registered_output', exist_ok=True)
    
    ref_img = generate_test_image(256)
    Image.fromarray(ref_img.astype(np.uint8)).save('test_images/ref_0000.png')
    
    num_images = 5
    print(f"\nGenerating {num_images} test images with random transformations...")
    
    for i in range(num_images):
        dx = np.random.uniform(-15, 15)
        dy = np.random.uniform(-15, 15)
        rot = np.random.uniform(-20, 20)
        
        target_img = rotate(ref_img, rot, reshape=False, order=3, mode='constant', cval=0)
        target_img = shift(target_img, (dy, dx), order=3, mode='constant', cval=0)
        Image.fromarray(target_img.astype(np.uint8)).save(f'test_images/img_{i:04d}.png')
    
    batch_registrator = BatchRegistrator()
    
    target_paths = [f'test_images/img_{i:04d}.png' for i in range(num_images)]
    
    print("\nStarting batch registration...")
    results = batch_registrator.register_batch(
        'test_images/ref_0000.png',
        target_paths,
        output_dir='registered_output'
    )
    
    batch_registrator.save_results_json('registration_results.json')
    batch_registrator.save_results_csv('registration_results.csv')
    
    summary = batch_registrator.get_summary_statistics()
    print(f"\nSummary Statistics:")
    print(f"  Number of images: {summary['count']}")
    print(f"  Mean NCC: {summary['ncc']['mean']:.4f} ± {summary['ncc']['std']:.4f}")
    print(f"  Mean SSIM: {summary['ssim']['mean']:.4f} ± {summary['ssim']['std']:.4f}")
    
    visualizer = RegistrationVisualizer()
    
    fig4 = visualizer.plot_quality_comparison(results)
    if fig4:
        fig4.savefig('batch_quality_comparison.png', dpi=150, bbox_inches='tight')
    
    fig5 = visualizer.plot_transformation_parameters(results)
    if fig5:
        fig5.savefig('batch_transformation_params.png', dpi=150, bbox_inches='tight')
    
    print("\nBatch registration complete!")
    print("Output saved to: registered_output/")
    print("Results saved to: registration_results.json, registration_results.csv")
    plt.close('all')


def main():
    np.random.seed(42)
    
    example_translation_only()
    example_rotation_only()
    example_full_registration()
    example_batch_registration()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
