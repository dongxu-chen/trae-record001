import sys
sys.path.insert(0, '.')

import numpy as np
from scipy.ndimage import shift
from scipy.fft import fft2, ifft2, fftshift

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

true_dx, true_dy = 3.7, -2.1
target = shift(ref_img, (true_dy, true_dx), order=3)

# Compute correlation
F_ref = fft2(ref_img)
F_target = fft2(target)

cross_power = np.conj(F_ref) * F_target
cross_power /= (np.abs(cross_power) + 1e-12)

correlation = np.abs(ifft2(cross_power))
correlation = fftshift(correlation)

# Find peak
peak = np.unravel_index(np.argmax(correlation), correlation.shape)
y0, x0 = peak

print(f"True shift: dx={true_dx}, dy={true_dy}")
print(f"Integer peak: y0={y0}, x0={x0}")
print(f"Integer estimate: dx={x0 - size//2}, dy={y0 - size//2}")
print(f"Integer error: {np.sqrt((x0 - size//2 - true_dx)**2 + (y0 - size//2 - true_dy)**2):.4f}")

# Simple 3-point parabolic fit
vy = np.array([
    correlation[y0-1, x0],
    correlation[y0, x0],
    correlation[y0+1, x0]
])
vx = np.array([
    correlation[y0, x0-1],
    correlation[y0, x0],
    correlation[y0, x0+1]
])

def parabolic_max_1d(v):
    a = v[0]
    b = v[1]
    c = v[2]
    denom = a - 2 * b + c
    if abs(denom) < 1e-10:
        return 0.0
    return (a - c) / (2 * denom)

dy_sub = parabolic_max_1d(vy)
dx_sub = parabolic_max_1d(vx)

dy = y0 + dy_sub - size//2
dx = x0 + dx_sub - size//2

print(f"\n3-point parabolic fit:")
print(f"  dy_sub={dy_sub:.6f}, dx_sub={dx_sub:.6f}")
print(f"  Estimated: dx={dx:.4f}, dy={dy:.4f}")
print(f"  Error: {np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2):.4f}")

# 7x7 window 2D parabolic fit on log
window = 3
y_start = y0 - window
y_end = y0 + window + 1
x_start = x0 - window
x_end = x0 + window + 1

roi = correlation[y_start:y_end, x_start:x_end]
max_val = roi.max()
roi_norm = roi / max_val
log_roi = np.log(np.maximum(roi_norm, 0.01) + 1e-10)

ys, xs = np.mgrid[y_start:y_end, x_start:x_end]
ys_flat = ys.flatten().astype(np.float64)
xs_flat = xs.flatten().astype(np.float64)
z_flat = log_roi.flatten().astype(np.float64)

weights = roi_norm.flatten()**2
weights = weights / weights.sum()

A = np.column_stack([
    xs_flat**2, ys_flat**2,
    xs_flat, ys_flat,
    xs_flat * ys_flat,
    np.ones_like(xs_flat)
])

A_weighted = A * np.sqrt(weights[:, np.newaxis])
z_weighted = z_flat * np.sqrt(weights)

coeffs, _, _, _ = np.linalg.lstsq(A_weighted, z_weighted, rcond=None)
a, b, c, d, e, f = coeffs

print(f"\nCoefficients:")
print(f"  a={a:.6e}, b={b:.6e}, c={c:.6e}, d={d:.6e}, e={e:.6e}, f={f:.6e}")

denom = 4 * a * b - e**2
if abs(denom) > 1e-10:
    dx_fit = (d * e - 2 * b * c) / denom
    dy_fit = (c * e - 2 * a * d) / denom
    print(f"\n2D weighted parabolic fit:")
    print(f"  dx_fit={dx_fit:.4f}, dy_fit={dy_fit:.4f}")
    print(f"  Estimated: dx={dx_fit - size//2:.4f}, dy={dy_fit - size//2:.4f}")
    print(f"  Error: {np.sqrt((dx_fit - size//2 - true_dx)**2 + (dy_fit - size//2 - true_dy)**2):.4f}")
    print(f"  Bounds check: x_start+0.5={x_start+0.5} <= dx_fit={dx_fit:.4f} <= x_end-1.5={x_end-1.5}")
    print(f"                y_start+0.5={y_start+0.5} <= dy_fit={dy_fit:.4f} <= y_end-1.5={y_end-1.5}")
else:
    print(f"Denom too small: {denom}")
