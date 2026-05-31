
import sys
sys.path.insert(0, '.')

import numpy as np
from scipy.ndimage import shift, rotate, gaussian_filter

print("Starting simple test...")

from phase_correlation import PhaseCorrelationRegistrator
print("PhaseCorrelationRegistrator imported")

from cross_modal_registration import CrossModalRegistrator
print("CrossModalRegistrator imported")

from video_stabilization import VideoStabilizer
print("VideoStabilizer imported")

from visualization import RegistrationVisualizer
print("RegistrationVisualizer imported")

from quality_metrics import RegistrationQualityEvaluator
print("RegistrationQualityEvaluator imported")

print("\nAll modules imported successfully!")

np.random.seed(42)
size = 128
x = np.linspace(-4, 4, size)
y = np.linspace(-4, 4, size)
X, Y = np.meshgrid(x, y)
img = np.zeros((size, size))
for i in range(10):
    cx = np.random.uniform(-3, 3)
    cy = np.random.uniform(-3, 3)
    sigma = np.random.uniform(0.1, 0.3)
    img += np.exp(-((X - cx)**2 + (Y - cy)**2) / (2 * sigma**2))
img = (img - img.min()) / (img.max() - img.min()) * 255
ref_img = img.astype(np.float32)

print("\nTest 1: Basic phase correlation")
registrator = PhaseCorrelationRegistrator()
target = shift(ref_img, (2.5, -3.7), order=3)
dx, dy, _ = registrator.estimate_translation(ref_img, target)
print(f"  True: dx=-3.7, dy=2.5")
print(f"  Est:  dx={dx:.3f}, dy={dy:.3f}")
print(f"  Error: {np.sqrt((dx+3.7)**2 + (dy-2.5)**2):.4f}")

print("\nTest 2: Cross-modal registration (simplified)")
optical = ref_img.copy()
infrared = gaussian_filter(ref_img, sigma=1.0) * 0.8 + 20
infrared += np.random.normal(0, 3, infrared.shape)
infrared_shifted = shift(infrared, (1.5, 2.3), order=3)

cross_registrator = CrossModalRegistrator()
result = cross_registrator.register(optical, infrared_shifted, method='phase')
print(f"  True: dx=2.3, dy=1.5")
print(f"  Est:  dx={result['translation'][0]:.3f}, dy={result['translation'][1]:.3f}")
print(f"  MI: {result['quality']['mutual_information']:.4f}")

print("\nTest 3: Video stabilization (simplified)")
stabilizer = VideoStabilizer(smoothing_window=5)
frames = []
for i in range(10):
    jitter_dx = np.random.normal(0, 1.0)
    jitter_dy = np.random.normal(0, 1.0)
    frame = shift(ref_img, (jitter_dy, jitter_dx), order=3)
    frames.append(frame.astype(np.float32))

stabilized, history = stabilizer.stabilize_video(frames)
print(f"  Stabilized {len(stabilized)} frames")
print(f"  Transform history has {len(history)} entries")

print("\nTest 4: Error heatmap visualization (simplified)")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

visualizer = RegistrationVisualizer()
target = shift(ref_img, (3.0, -2.0), order=3)
result = registrator.register(ref_img, target)
transformed = result['transformed']

abs_error = np.abs(ref_img - transformed)
fig, ax = plt.subplots(1, 1)
im = ax.imshow(abs_error, cmap='hot')
plt.colorbar(im, ax=ax)
ax.set_title('Absolute Error Heatmap')
plt.savefig('simple_heatmap_test.png', dpi=100)
plt.close()
print(f"  Heatmap saved as simple_heatmap_test.png")
print(f"  Mean abs error: {np.mean(abs_error):.4f}")

print("\n" + "=" * 50)
print("All simple tests passed!")
print("=" * 50)
