import sys
import cv2
import numpy as np
from motion_deblur import MotionDeblur

deblur = MotionDeblur()

test_image = np.zeros((200, 300, 3), dtype=np.uint8)
test_image[:] = [200, 200, 200]
cv2.rectangle(test_image, (50, 50), (120, 120), (255, 0, 0), -1)
cv2.circle(test_image, (220, 100), 40, (0, 255, 0), -1)

print("Test 1: Variable motion kernel...")
try:
    kernel_var = deblur.generate_variable_motion_kernel(10, 25, 0, 30)
    print(f"  Variable kernel shape: {kernel_var.shape}, sum: {kernel_var.sum():.4f}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 2: Accelerated motion kernel...")
try:
    kernel_acc = deblur.generate_accelerated_motion_kernel(5, 0.2, 30, duration=15)
    print(f"  Accelerated kernel shape: {kernel_acc.shape}, sum: {kernel_acc.sum():.4f}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 3: Apply standard blur...")
try:
    kernel_std = deblur.generate_motion_kernel(20, 45)
    blurred = deblur.apply_motion_blur(test_image, kernel_std)
    print(f"  Blurred image shape: {blurred.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 4: Spatially varying kernel map...")
try:
    params_list = [(10, 0), (15, 15), (20, 30), (25, 45)]
    kernel_map = deblur.generate_piecewise_linear_kernels(test_image.shape, params_list, grid_size=(2, 2))
    print(f"  Kernel map shape: {kernel_map.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 5: Spatially varying blur...")
try:
    blurred_sv = deblur.apply_spatially_varying_blur(test_image, kernel_map)
    print(f"  SV blurred image shape: {blurred_sv.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 6: SV deblur...")
try:
    deblurred_sv = deblur.deblur_spatially_varying(blurred_sv, kernel_map, grid_size=(2, 2))
    print(f"  SV deblurred image shape: {deblurred_sv.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 7: Blind deconvolution (adaptive)...")
try:
    deblurred_bd, kernel_bd = deblur.blind_deconvolution(
        blurred, iterations=10, kernel_size=23, adaptive=True
    )
    print(f"  Blind deconv shape: {deblurred_bd.shape}, kernel shape: {kernel_bd.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 8: Quality assessment...")
try:
    quality = deblur.evaluate_overall_quality(test_image)
    print(f"  Sharpness: {quality['sharpness']:.2f}")
    print(f"  Contrast: {quality['contrast']:.2f}")
    print(f"  Noise: {quality['noise_level']:.2f}")
    print(f"  Ringing: {quality['ringing_level']:.4f}")
    print(f"  BRISQUE: {quality['brisque_score']:.2f}")
    print(f"  NIQE: {quality['niqe_score']:.2f}")
    print(f"  Overall: {quality['overall_score']:.2f} ({quality['quality_level']})")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 9: Wiener with auto K...")
try:
    K_auto = deblur.estimate_noise_autocorrelation(blurred, kernel_std)
    print(f"  Auto K: {K_auto:.4f}")
    deblurred_auto = deblur.wiener_deblur(blurred, kernel_std)
    print(f"  Deblurred shape: {deblurred_auto.shape}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\nTest 10: Parameter estimation...")
try:
    est_len, est_ang = deblur.estimate_motion_parameters(blurred)
    print(f"  Estimated: length={est_len:.1f}, angle={est_ang:.1f}")
    print("  PASSED")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n" + "="*50)
print("All tests completed!")
cv2.imwrite('test_original.png', test_image)
cv2.imwrite('test_blurred.png', blurred)
cv2.imwrite('test_deblurred.png', deblurred_auto)
print("Saved test images.")
