import numpy as np
from scipy.ndimage import shift, rotate
import matplotlib.pyplot as plt
from phase_correlation import PhaseCorrelationRegistrator
from quality_metrics import RegistrationQualityEvaluator

np.random.seed(42)

size = 256
x = np.linspace(-3, 3, size)
y = np.linspace(-3, 3, size)
X, Y = np.meshgrid(x, y)

ref_img = np.exp(-(X**2 + Y**2)) * 255
ref_img += np.random.randn(size, size) * 5
ref_img = np.clip(ref_img, 0, 255)

true_dx, true_dy = 15.3, -8.7
target_img = shift(ref_img, (true_dy, true_dx), order=3, mode='constant', cval=0)

print(f"True translation applied to ref: shift(ref, ({true_dy}, {true_dx}))")
print(f"This means target = ref shifted by dy={true_dy}, dx={true_dx}")

registrator = PhaseCorrelationRegistrator(use_gpu=False)
dx, dy, corr = registrator.estimate_translation(ref_img, target_img, upsample_factor=5)
print(f"\nPhase correlation detected: dx={dx:.3f}, dy={dy:.3f}")

print(f"\nTo register target back to ref:")
print(f"  We need to shift target by: (-dy, -dx) = ({-dy:.3f}, {-dx:.3f})")
print(f"  Or shift target by: ({-true_dy}, {-true_dx}) = ({-true_dy}, {-true_dx}) (ground truth)")

registered1 = shift(target_img, (-dy, -dx), order=3, mode='constant', cval=0)
registered2 = shift(target_img, (-true_dy, -true_dx), order=3, mode='constant', cval=0)

evaluator = RegistrationQualityEvaluator()
print(f"\nQuality with estimated shift: NCC={evaluator.compute_ncc(ref_img, registered1):.4f}")
print(f"Quality with true shift:      NCC={evaluator.compute_ncc(ref_img, registered2):.4f}")

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes[0, 0].imshow(ref_img, cmap='gray')
axes[0, 0].set_title('Reference')
axes[0, 1].imshow(target_img, cmap='gray')
axes[0, 1].set_title('Target (shifted)')
axes[0, 2].imshow(corr, cmap='viridis')
axes[0, 2].set_title('Correlation')
axes[1, 0].imshow(registered1, cmap='gray')
axes[1, 0].set_title('Registered (estimated)')
axes[1, 1].imshow(registered2, cmap='gray')
axes[1, 1].set_title('Registered (ground truth)')
axes[1, 2].imshow(np.abs(registered1 - registered2), cmap='hot')
axes[1, 2].set_title('Difference')
plt.tight_layout()
plt.savefig('debug_translation.png', dpi=100)
plt.close()
print("\nSaved debug_translation.png")
