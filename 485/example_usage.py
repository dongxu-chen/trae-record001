import cv2
import numpy as np
from motion_deblur import MotionDeblur


def print_quality_scores(quality: dict, name: str):
    print(f"\n=== {name} Quality Scores ===")
    print(f"Sharpness:     {quality['sharpness']:.2f}")
    print(f"Contrast:      {quality['contrast']:.2f}")
    print(f"Noise Level:   {quality['noise_level']:.2f}")
    print(f"Ringing Level: {quality['ringing_level']:.4f}")
    print(f"BRISQUE Score: {quality['brisque_score']:.2f}")
    print(f"NIQE Score:    {quality['niqe_score']:.2f}")
    print(f"Overall Score: {quality['overall_score']:.2f}")
    print(f"Quality Level: {quality['quality_level']}")


def example_1_variable_motion_blur():
    print("=" * 60)
    print("Example 1: Variable/Accelerated Motion Blur")
    print("=" * 60)
    
    deblur = MotionDeblur()
    
    test_image = np.zeros((400, 500, 3), dtype=np.uint8)
    test_image[:] = [200, 200, 200]
    cv2.rectangle(test_image, (50, 50), (150, 150), (255, 0, 0), -1)
    cv2.circle(test_image, (350, 100), 50, (0, 255, 0), -1)
    cv2.rectangle(test_image, (150, 250), (400, 350), (0, 0, 255), -1)
    cv2.putText(test_image, 'VARIABLE', (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    kernel_var = deblur.generate_variable_motion_kernel(
        start_length=10, end_length=35,
        start_angle=0, end_angle=45,
        num_segments=15
    )
    blurred_var = deblur.apply_motion_blur(test_image, kernel_var)
    
    kernel_acc = deblur.generate_accelerated_motion_kernel(
        init_length=5, acceleration=0.3,
        angle=30, duration=25
    )
    blurred_acc = deblur.apply_motion_blur(test_image, kernel_acc)
    
    kernel_rot = deblur.generate_rotation_motion_kernel(
        max_radius=30, start_angle=0, end_angle=30,
        center_offset=(20, 0)
    )
    blurred_rot = deblur.apply_motion_blur(test_image, kernel_rot)
    
    deblurred_var = deblur.wiener_deblur(blurred_var, kernel_var)
    deblurred_acc = deblur.wiener_deblur(blurred_acc, kernel_acc)
    deblurred_rot = deblur.wiener_deblur(blurred_rot, kernel_rot)
    
    cv2.imwrite('var_original.png', test_image)
    cv2.imwrite('var_blurred.png', blurred_var)
    cv2.imwrite('var_deblurred.png', deblurred_var)
    cv2.imwrite('acc_blurred.png', blurred_acc)
    cv2.imwrite('acc_deblurred.png', deblurred_acc)
    cv2.imwrite('rot_blurred.png', blurred_rot)
    cv2.imwrite('rot_deblurred.png', deblurred_rot)
    
    print("Variable motion blur types:")
    print("- Variable length/angle blur (10→35 px, 0→45°)")
    print("- Accelerated motion blur (a=0.3)")
    print("- Rotational motion blur (0→30°, r=30)")
    print("\nSaved: var_*.png, acc_*.png, rot_*.png")
    print()


def example_2_spatially_varying_blur():
    print("=" * 60)
    print("Example 2: Spatially Varying Motion Blur")
    print("=" * 60)
    
    deblur = MotionDeblur()
    
    test_image = np.zeros((400, 500, 3), dtype=np.uint8)
    test_image[:] = [150, 150, 150]
    for i in range(5):
        cv2.circle(test_image, (50 + i * 100, 100 + (i % 2) * 200), 
                   30 + i * 5, (50 * i, 100 + 30 * i, 255 - 50 * i), -1)
    
    params_list = [
        (15, 0), (20, 15), (25, 30), (30, 45)
    ]
    kernel_map = deblur.generate_piecewise_linear_kernels(
        test_image.shape, params_list, grid_size=(2, 2)
    )
    
    blurred_sv = deblur.apply_spatially_varying_blur(test_image, kernel_map)
    
    deblurred_sv = deblur.deblur_spatially_varying(
        blurred_sv, kernel_map, method='wiener', grid_size=(2, 2)
    )
    
    cv2.imwrite('sv_original.png', test_image)
    cv2.imwrite('sv_blurred.png', blurred_sv)
    cv2.imwrite('sv_deblurred.png', deblurred_sv)
    
    print("Spatially varying blur with 2x2 grid:")
    print("- Top-left:     15px, 0°")
    print("- Top-right:    20px, 15°")
    print("- Bottom-left:  25px, 30°")
    print("- Bottom-right: 30px, 45°")
    print("\nSaved: sv_*.png")
    print()


def example_3_blind_deconvolution_optimized():
    print("=" * 60)
    print("Example 3: Optimized Blind Deconvolution")
    print("=" * 60)
    
    deblur = MotionDeblur()
    
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    test_image[:] = [180, 180, 180]
    cv2.rectangle(test_image, (50, 50), (150, 150), (255, 0, 0), -1)
    cv2.circle(test_image, (280, 120), 45, (0, 255, 0), -1)
    
    true_length = 22
    true_angle = 40
    kernel_true = deblur.generate_motion_kernel(true_length, true_angle)
    blurred = deblur.apply_motion_blur(test_image, kernel_true)
    
    noise = np.random.normal(0, 3, blurred.shape).astype(np.float32)
    blurred_noisy = np.clip(blurred.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    
    deblurred_adaptive, kernel_adaptive = deblur.blind_deconvolution(
        blurred_noisy, iterations=20, kernel_size=27,
        adaptive=True, regularization=1e-4, damping=0.2
    )
    
    deblurred_naive, kernel_naive = deblur.blind_deconvolution(
        blurred_noisy, iterations=20, kernel_size=27,
        adaptive=False
    )
    
    cv2.imwrite('bd_original.png', test_image)
    cv2.imwrite('bd_blurred.png', blurred_noisy)
    cv2.imwrite('bd_adaptive.png', deblurred_adaptive)
    cv2.imwrite('bd_naive.png', deblurred_naive)
    
    print("Blind deconvolution comparison:")
    print(f"True kernel: length={true_length}, angle={true_angle}")
    print("\nEstimated kernels:")
    print(f"- Adaptive init: sum={kernel_adaptive.sum():.4f}, max={kernel_adaptive.max():.4f}")
    print(f"- Naive init:    sum={kernel_naive.sum():.4f}, max={kernel_naive.max():.4f}")
    print("\nSaved: bd_*.png")
    print()


def example_4_no_reference_quality_assessment():
    print("=" * 60)
    print("Example 4: No-Reference Image Quality Assessment")
    print("=" * 60)
    
    deblur = MotionDeblur()
    
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    test_image[:] = [200, 200, 200]
    cv2.rectangle(test_image, (80, 80), (180, 180), (255, 0, 0), -1)
    cv2.circle(test_image, (280, 130), 50, (0, 255, 0), -1)
    cv2.putText(test_image, 'QUALITY', (60, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
    
    kernel = deblur.generate_motion_kernel(length=25, angle=30)
    blurred = deblur.apply_motion_blur(test_image, kernel)
    
    deblurred_good = deblur.wiener_deblur(blurred, kernel, K=0.01)
    
    deblurred_bad = deblur.wiener_deblur(blurred, kernel, K=0.0001)
    
    deblurred_suppressed = deblur.suppress_ringing(blurred, kernel, method='bilateral')
    deblurred_suppressed = deblur.wiener_deblur(deblurred_suppressed, kernel, K=0.0001)
    
    quality_orig = deblur.evaluate_overall_quality(test_image)
    quality_blur = deblur.evaluate_overall_quality(blurred)
    quality_good = deblur.evaluate_overall_quality(deblurred_good)
    quality_bad = deblur.evaluate_overall_quality(deblurred_bad)
    quality_supp = deblur.evaluate_overall_quality(deblurred_suppressed)
    
    print_quality_scores(quality_orig, "Original")
    print_quality_scores(quality_blur, "Blurred")
    print_quality_scores(quality_good, "Good Deblur (K=0.01)")
    print_quality_scores(quality_bad, "Bad Deblur (K=0.0001, ringing)")
    print_quality_scores(quality_supp, "With Ringing Suppression")
    
    cv2.imwrite('qa_original.png', test_image)
    cv2.imwrite('qa_blurred.png', blurred)
    cv2.imwrite('qa_good.png', deblurred_good)
    cv2.imwrite('qa_bad.png', deblurred_bad)
    cv2.imwrite('qa_suppressed.png', deblurred_suppressed)
    
    print("\nSaved: qa_*.png")
    print()


def example_5_combined_pipeline():
    print("=" * 60)
    print("Example 5: Complete End-to-End Pipeline")
    print("=" * 60)
    
    deblur = MotionDeblur()
    
    test_image = np.zeros((400, 500, 3), dtype=np.uint8)
    test_image[:] = [200, 200, 200]
    cv2.rectangle(test_image, (50, 50), (150, 150), (255, 100, 100), -1)
    cv2.circle(test_image, (350, 120), 55, (100, 255, 100), -1)
    cv2.rectangle(test_image, (120, 240), (380, 360), (100, 100, 255), -1)
    cv2.putText(test_image, 'PIPELINE', (80, 310), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    
    true_length = 28
    true_angle = 50
    kernel_true = deblur.generate_motion_kernel(true_length, true_angle)
    blurred = deblur.apply_motion_blur(test_image, kernel_true)
    
    noise = np.random.normal(0, 4, blurred.shape).astype(np.float32)
    blurred = np.clip(blurred.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    
    print("Step 1: Estimate motion parameters (Radon transform)")
    est_length, est_angle = deblur.estimate_motion_parameters(blurred)
    print(f"   True: length={true_length}, angle={true_angle}")
    print(f"   Est:  length={est_length:.1f}, angle={est_angle:.1f}")
    
    print("\nStep 2: Estimate noise level (autocorrelation)")
    est_kernel = deblur.generate_motion_kernel(int(est_length), est_angle)
    K_auto = deblur.estimate_noise_autocorrelation(blurred, est_kernel)
    print(f"   Auto K = {K_auto:.4f}")
    
    print("\nStep 3: Apply ringing suppression (bilateral filter)")
    blurred_supp = deblur.suppress_ringing(blurred, est_kernel, method='bilateral')
    
    print("\nStep 4: Wiener deblurring with adaptive K")
    deblurred = deblur.wiener_deblur(blurred_supp, est_kernel, K=K_auto)
    
    print("\nStep 5: Quality assessment")
    q_orig = deblur.evaluate_overall_quality(test_image)
    q_blur = deblur.evaluate_overall_quality(blurred)
    q_deblur = deblur.evaluate_overall_quality(deblurred)
    
    print(f"   Original overall score: {q_orig['overall_score']:.2f} ({q_orig['quality_level']})")
    print(f"   Blurred overall score:  {q_blur['overall_score']:.2f} ({q_blur['quality_level']})")
    print(f"   Deblurred overall score:{q_deblur['overall_score']:.2f} ({q_deblur['quality_level']})")
    
    improvement = q_deblur['overall_score'] - q_blur['overall_score']
    print(f"\nQuality improvement: +{improvement:.2f} points")
    
    cv2.imwrite('pipeline_original.png', test_image)
    cv2.imwrite('pipeline_blurred.png', blurred)
    cv2.imwrite('pipeline_deblurred.png', deblurred)
    
    print("\nSaved: pipeline_*.png")
    print()


def run_all_examples():
    example_1_variable_motion_blur()
    example_2_spatially_varying_blur()
    example_3_blind_deconvolution_optimized()
    example_4_no_reference_quality_assessment()
    example_5_combined_pipeline()
    
    print("=" * 60)
    print("All advanced examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_examples()
