
import numpy as np
from scipy.ndimage import shift, rotate
from phase_correlation import PhaseCorrelationRegistrator

def main():
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

    registrator = PhaseCorrelationRegistrator()

    with open('final_test_result.txt', 'w') as f:
        f.write('Testing subpixel accuracy (Upsample + Parabolic Fit)...\n')
        test_shifts = [(0.1, 0.2), (0.5, -0.3), (1.2, 0.8), (3.7, -2.1), (10.3, -7.9)]
        errors = []
        for true_dx, true_dy in test_shifts:
            target = shift(ref_img, (true_dy, true_dx), order=3)
            dx, dy, _ = registrator.estimate_translation(ref_img, target)
            err = np.sqrt((dx - true_dx)**2 + (dy - true_dy)**2)
            errors.append(err)
            f.write(f'  True ({true_dx:>5.2f}, {true_dy:>5.2f}) -> Est ({dx:>7.4f}, {dy:>7.4f}) -> Err: {err:.4f}\n')

        f.write(f'\nMean error: {np.mean(errors):.4f} pixels\n')
        f.write(f'Max error: {np.max(errors):.4f} pixels\n')
        
        f.write('\nTesting rotation accuracy...\n')
        test_rotations = [5.23, 15.79, 33.45, -12.33]
        rot_errors = []
        for true_rot in test_rotations:
            target = rotate(ref_img, true_rot, reshape=False, order=3, mode='constant', cval=0)
            rot, scale, _ = registrator.estimate_rotation_scale(ref_img, target)
            err = abs(rot - true_rot)
            rot_errors.append(err)
            f.write(f'  True {true_rot:>6.2f}deg -> Est {rot:>7.4f}deg -> Err: {err:.4f}deg\n')
        
        f.write(f'\nMean rotation error: {np.mean(rot_errors):.4f} deg\n')
        f.write(f'Max rotation error: {np.max(rot_errors):.4f} deg\n')
    
    print("Test complete! Results in final_test_result.txt")

if __name__ == "__main__":
    main()
