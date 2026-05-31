
import sys
sys.path.insert(0, '.')

import numpy as np
from scipy.ndimage import shift, rotate, gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from phase_correlation import PhaseCorrelationRegistrator
from cross_modal_registration import CrossModalRegistrator
from video_stabilization import VideoStabilizer
from visualization import RegistrationVisualizer
from quality_metrics import RegistrationQualityEvaluator


def generate_test_image(size=256):
    np.random.seed(42)
    x = np.linspace(-4, 4, size)
    y = np.linspace(-4, 4, size)
    X, Y = np.meshgrid(x, y)
    img = np.zeros((size, size))
    for i in range(20):
        cx = np.random.uniform(-3, 3)
        cy = np.random.uniform(-3, 3)
        sigma = np.random.uniform(0.05, 0.3)
        amplitude = np.random.uniform(0.5, 1.5)
        img += amplitude * np.exp(-((X - cx)**2 + (Y - cy)**2) / (2 * sigma**2))
    img = (img - img.min()) / (img.max() - img.min()) * 255
    return img.astype(np.float32)


def simulate_optical_infrared(ref_img):
    optical = ref_img.copy()
    
    infrared = gaussian_filter(ref_img, sigma=1.5)
    
    infrared = infrared + np.random.normal(0, 5, infrared.shape)
    
    infrared = 0.7 * infrared + 30
    
    return optical, infrared


def simulate_shaky_video(ref_img, num_frames=50):
    frames = []
    np.random.seed(123)
    
    cum_dx = 0
    cum_dy = 0
    cum_angle = 0
    
    for i in range(num_frames):
        jitter_dx = np.random.normal(0, 2.0)
        jitter_dy = np.random.normal(0, 2.0)
        jitter_angle = np.random.normal(0, 0.5)
        
        cum_dx += jitter_dx
        cum_dy += jitter_dy
        cum_angle += jitter_angle
        
        cum_dx = np.clip(cum_dx, -20, 20)
        cum_dy = np.clip(cum_dy, -20, 20)
        cum_angle = np.clip(cum_angle, -10, 10)
        
        frame_rotated = rotate(ref_img, cum_angle, reshape=False, order=3, mode='constant', cval=0)
        frame = shift(frame_rotated, (cum_dy, cum_dx), order=3, mode='constant', cval=0)
        
        frames.append(frame.astype(np.float32))
    
    return frames


def test_cross_modal_registration():
    print("=" * 70)
    print("Test 1: Cross-Modal (Optical-Infrared) Registration")
    print("=" * 70)
    
    ref_img = generate_test_image()
    optical, infrared = simulate_optical_infrared(ref_img)
    
    true_dx = 3.5
    true_dy = -2.3
    true_angle = 5.7
    
    infrared_shifted = shift(infrared, (true_dy, true_dx), order=3, mode='constant', cval=0)
    infrared_transformed = rotate(infrared_shifted, true_angle, reshape=False, order=3, mode='constant', cval=0)
    
    registrator = CrossModalRegistrator()
    
    print("\nPerforming hybrid cross-modal registration...")
    result = registrator.register_multimodal(optical, infrared_transformed)
    
    dx, dy = result['translation']
    angle = result['rotation']
    quality = result['quality']
    
    print(f"\nTrue transform: dx={true_dx:.2f}, dy={true_dy:.2f}, angle={true_angle:.2f}°")
    print(f"Estimated transform: dx={dx:.2f}, dy={dy:.2f}, angle={angle:.2f}°")
    print(f"Translation error: {np.sqrt((dx-true_dx)**2 + (dy-true_dy)**2):.4f} pixels")
    print(f"Rotation error: {abs(angle-true_angle):.4f}°")
    print(f"\nQuality metrics:")
    print(f"  NCC: {quality['ncc']:.4f}")
    print(f"  SSIM: {quality['ssim']:.4f}")
    print(f"  Mutual Information: {quality['mutual_information']:.4f}")
    print(f"  Gradient Similarity: {quality['gradient_similarity']:.4f}")
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes[0, 0].imshow(optical, cmap='gray')
    axes[0, 0].set_title('Optical Image (Reference)')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(infrared_transformed, cmap='gray')
    axes[0, 1].set_title('Infrared Image (Transformed)')
    axes[0, 1].axis('off')
    
    axes[1, 0].imshow(result['transformed'], cmap='gray')
    axes[1, 0].set_title('Registered Infrared Image')
    axes[1, 0].axis('off')
    
    diff = np.abs(optical - result['transformed'])
    im = axes[1, 1].imshow(diff, cmap='hot')
    axes[1, 1].set_title('Difference After Registration')
    axes[1, 1].axis('off')
    plt.colorbar(im, ax=axes[1, 1], fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    plt.savefig('cross_modal_result.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\nCross-modal registration figure saved as 'cross_modal_result.png'")
    
    return result


def test_video_stabilization():
    print("\n" + "=" * 70)
    print("Test 2: Video Stabilization")
    print("=" * 70)
    
    ref_img = generate_test_image(size=200)
    shaky_frames = simulate_shaky_video(ref_img, num_frames=30)
    
    print(f"\nGenerated {len(shaky_frames)} shaky frames")
    
    stabilizer = VideoStabilizer(smoothing_window=15, max_correction=30.0)
    
    print("\nStabilizing video...")
    stabilized_frames, transform_history = stabilizer.stabilize_video(
        shaky_frames, show_progress=True
    )
    
    metrics = stabilizer.get_stability_metrics(transform_history)
    
    print(f"\nStability Metrics:")
    print(f"  Raw translation std: {metrics['raw_translation_std']:.4f} pixels")
    print(f"  Smooth translation std: {metrics['smooth_translation_std']:.4f} pixels")
    print(f"  Translation stability improvement: {metrics['stability_improvement_translation']*100:.2f}%")
    print(f"  Raw rotation std: {metrics['raw_rotation_std']:.4f}°")
    print(f"  Smooth rotation std: {metrics['smooth_rotation_std']:.4f}°")
    print(f"  Rotation stability improvement: {metrics['stability_improvement_rotation']*100:.2f}%")
    
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    
    frame_indices = [0, 10, 20]
    for i, idx in enumerate(frame_indices):
        if idx < len(shaky_frames):
            axes[0, i].imshow(shaky_frames[idx], cmap='gray')
            axes[0, i].set_title(f'Shaky Frame {idx}')
            axes[0, i].axis('off')
            
            axes[1, i].imshow(stabilized_frames[idx], cmap='gray')
            axes[1, i].set_title(f'Stabilized Frame {idx}')
            axes[1, i].axis('off')
            
            diff = np.abs(shaky_frames[idx] - stabilized_frames[idx])
            im = axes[2, i].imshow(diff, cmap='hot')
            axes[2, i].set_title(f'Difference (Frame {idx})')
            axes[2, i].axis('off')
            plt.colorbar(im, ax=axes[2, i], fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    plt.savefig('video_stabilization_result.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\nVideo stabilization figure saved as 'video_stabilization_result.png'")
    
    if len(transform_history) > 0:
        raw_dx = [t['raw_transform'][0] for t in transform_history]
        raw_dy = [t['raw_transform'][1] for t in transform_history]
        smooth_dx = [t['smoothed_transform'][0] for t in transform_history]
        smooth_dy = [t['smoothed_transform'][1] for t in transform_history]
        raw_angle = [t['raw_transform'][2] for t in transform_history]
        smooth_angle = [t['smoothed_transform'][2] for t in transform_history]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        axes[0].plot(raw_dx, label='Raw X', alpha=0.5)
        axes[0].plot(raw_dy, label='Raw Y', alpha=0.5)
        axes[0].plot(smooth_dx, label='Smooth X', linewidth=2)
        axes[0].plot(smooth_dy, label='Smooth Y', linewidth=2)
        axes[0].set_title('Frame-to-Frame Translation')
        axes[0].set_xlabel('Frame')
        axes[0].set_ylabel('Translation (pixels)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        axes[1].plot(raw_angle, label='Raw', alpha=0.5)
        axes[1].plot(smooth_angle, label='Smooth', linewidth=2)
        axes[1].set_title('Frame-to-Frame Rotation')
        axes[1].set_xlabel('Frame')
        axes[1].set_ylabel('Rotation (degrees)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('video_stabilization_plots.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("Stabilization plots saved as 'video_stabilization_plots.png'")
    
    return stabilized_frames, transform_history


def test_error_heatmaps():
    print("\n" + "=" * 70)
    print("Test 3: Registration Error Heatmaps")
    print("=" * 70)
    
    ref_img = generate_test_image()
    
    true_dx = 5.2
    true_dy = -3.7
    true_angle = 8.5
    
    target_shifted = shift(ref_img, (true_dy, true_dx), order=3, mode='constant', cval=0)
    target = rotate(target_shifted, true_angle, reshape=False, order=3, mode='constant', cval=0)
    
    registrator = PhaseCorrelationRegistrator()
    result = registrator.register(ref_img, target)
    
    transformed = result['transformed']
    
    visualizer = RegistrationVisualizer()
    
    print("\nGenerating error heatmap...")
    fig1 = visualizer.plot_error_heatmap(ref_img, target, transformed, window_size=11)
    fig1.savefig('error_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close(fig1)
    print("Error heatmap saved as 'error_heatmap.png'")
    
    print("\nGenerating detailed error analysis...")
    fig2 = visualizer.plot_detailed_error_analysis(ref_img, transformed, window_size=11)
    fig2.savefig('detailed_error_analysis.png', dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print("Detailed error analysis saved as 'detailed_error_analysis.png'")
    
    print("\nGenerating error histogram...")
    fig3 = visualizer.plot_registration_error_histogram(ref_img, target, transformed)
    fig3.savefig('error_histogram.png', dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print("Error histogram saved as 'error_histogram.png'")
    
    print("\nSaving error heatmap data...")
    error_data = visualizer.save_error_heatmap_data(
        ref_img, transformed, 'error_heatmap_data.npz', window_size=11
    )
    print(f"  Mean absolute error: {error_data['mean_abs_error']:.4f}")
    print(f"  Max absolute error: {error_data['max_abs_error']:.4f}")
    print(f"  Mean local MSE: {error_data['mean_local_mse']:.4f}")
    print("Error data saved as 'error_heatmap_data.npz'")
    
    return error_data


def main():
    print("\n" + "#" * 70)
    print("#" + " " * 15 + "NEW FEATURES COMPREHENSIVE TEST" + " " * 16 + "#")
    print("#" * 70)
    
    try:
        cross_modal_result = test_cross_modal_registration()
    except Exception as e:
        print(f"\nCross-modal registration test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        stabilized_frames, transform_history = test_video_stabilization()
    except Exception as e:
        print(f"\nVideo stabilization test failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        error_data = test_error_heatmaps()
    except Exception as e:
        print(f"\nError heatmap test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
