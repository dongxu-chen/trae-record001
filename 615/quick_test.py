import sys
sys.path.insert(0, '.')

import numpy as np
from scipy.ndimage import shift
from phase_correlation import PhaseCorrelationRegistrator

print("Starting test...")
sys.stdout.flush()

np.random.seed(42)
size = 256
x = np.linspace(-4, 4, size)
y = np.linspace(-4, 4, size)
X, Y = np.meshgrid(x, y)
img = np.zeros((size, size))
for i in range(15):
    cx = np.random.uniform(-3, 3)
    cy = np.random.uniform(-3, 3)
    sigma = np.random.uniform(0.05, 0.25)
    img += np.exp(-((X - cx)**2 + (Y - cy)**2) / (2 * sigma**2))
img = (img - img.min()) / (img.max() - img.min()) * 255
ref_img = img.astype(np.float32)

print("Creating registrator...")
sys.stdout.flush()

registrator = PhaseCorrelationRegistrator()

print('Testing subpixel accuracy (Parabolic + Gaussian Fit)...')
sys.stdout.flush()

test_shifts = [(0.1, 0.2), (0.5, -0.3), (1.2, 0.8), (3.7, -2.1), (10.3, -7.9)]
errors = []
for true_dx, true_dy in test_shifts:
    target = shift(ref_img, (true_dy, true_dx), order=3)
    dx, dy, _ = registrator.estimate_translation(ref_img, target)
    err = np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2)
    errors.append(err)
    print(f'  True ({true_dx:>5.2f}, {true_dy:>5.2f}) -> Est ({dx:>7.4f}, {dy:>7.4f}) -> Err: {err:.4f}')
    sys.stdout.flush()

print(f'\nMean error: {np.mean(errors):.4f} pixels')
print(f'Max error: {np.max(errors):.4f} pixels')
print("Test complete!")
