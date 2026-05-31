
import sys
sys.path.insert(0, '.')

import numpy as np
from scipy.ndimage import shift, rotate, gaussian_filter

print("Testing cross-modal registration fix...")

from cross_modal_registration import CrossModalRegistrator

np.random.seed(42)
size = 256
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
ref_img = img.astype(np.float32)

optical = ref_img.copy()
infrared = gaussian_filter(ref_img, sigma=1.5)
infrared = infrared + np.random.normal(0, 5, infrared.shape)
infrared = 0.7 * infrared + 30

true_dx = 3.5
true_dy = -2.3
true_angle = 5.7

infrared_shifted = shift(infrared, (true_dy, true_dx), order=3, mode='constant', cval=0)
infrared_transformed = rotate(infrared_shifted, true_angle, reshape=False, order=3, mode='constant', cval=0)

registrator = CrossModalRegistrator()

print("\nTest 1: Phase-only method")
result = registrator.register(optical, infrared_transformed, method='phase')
dx, dy = result['translation']
angle = result['rotation']
print(f"  True: dx={true_dx:.2f}, dy={true_dy:.2f}, angle={true_angle:.2f}°")
print(f"  Est:  dx={dx:.2f}, dy={dy:.2f}, angle={angle:.2f}°")
print(f"  Translation error: {np.sqrt((dx-true_dx)**2 + (dy-true_dy)**2):.4f}")
print(f"  Rotation error: {abs(angle-true_angle):.4f}°")
print(f"  MI: {result['quality']['mutual_information']:.4f}")

print("\nTest 2: Feature-only method")
try:
    result = registrator.register(optical, infrared_transformed, method='feature')
    dx, dy = result['translation']
    angle = result['rotation']
    print(f"  True: dx={true_dx:.2f}, dy={true_dy:.2f}, angle={true_angle:.2f}°")
    print(f"  Est:  dx={dx:.2f}, dy={dy:.2f}, angle={angle:.2f}°")
    print(f"  Translation error: {np.sqrt((dx-true_dx)**2 + (dy-true_dy)**2):.4f}")
    print(f"  Rotation error: {abs(angle-true_angle):.4f}°")
except Exception as e:
    print(f"  Feature method failed: {e}")

print("\nTest 3: Hybrid method")
result = registrator.register_multimodal(optical, infrared_transformed)
dx, dy = result['translation']
angle = result['rotation']
print(f"  True: dx={true_dx:.2f}, dy={true_dy:.2f}, angle={true_angle:.2f}°")
print(f"  Est:  dx={dx:.2f}, dy={dy:.2f}, angle={angle:.2f}°")
print(f"  Translation error: {np.sqrt((dx-true_dx)**2 + (dy-true_dy)**2):.4f}")
print(f"  Rotation error: {abs(angle-true_angle):.4f}°")
print(f"  Quality metrics:")
print(f"    NCC: {result['quality']['ncc']:.4f}")
print(f"    SSIM: {result['quality']['ssim']:.4f}")
print(f"    MI: {result['quality']['mutual_information']:.4f}")
print(f"    Gradient Similarity: {result['quality']['gradient_similarity']:.4f}")

print("\nCross-modal fix test complete!")
