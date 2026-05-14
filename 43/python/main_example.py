import numpy as np
from kspace_simulation import kspace_simulation
from reconstruction import reconstruction
from display import display_results


def generate_phantom(N: int) -> np.ndarray:
    """生成 Shepp-Logan 体模图像"""
    X, Y = np.meshgrid(np.linspace(-1, 1, N), np.linspace(-1, 1, N))
    
    ellipses = np.array([
        [1.0,    0.69,   0.92,   0.0,    0.0,    0.0],
        [-0.8,   0.6624, 0.8740, 0.0,   -0.0184, 0.0],
        [-0.2,   0.1100, 0.3100, 0.22,   0.0,    -18],
        [-0.2,   0.1600, 0.4100, -0.22,  0.0,    18],
        [0.1,    0.2100, 0.2500, 0.0,    0.35,   0.0],
        [0.1,    0.0460, 0.0460, 0.0,    0.1,    0.0],
        [0.1,    0.0460, 0.0460, 0.0,   -0.1,    0.0],
        [0.1,    0.0460, 0.0460, -0.08,  -0.605, 0.0],
        [0.1,    0.0230, 0.0230, 0.0,   -0.606, 0.0],
        [0.1,    0.0460, 0.0460, 0.06,  -0.605, 0.0],
    ])
    
    phantom = np.zeros((N, N), dtype=np.float64)
    
    for i in range(ellipses.shape[0]):
        A = ellipses[i, 0]
        a = ellipses[i, 1]
        b = ellipses[i, 2]
        x0 = ellipses[i, 3]
        y0 = ellipses[i, 4]
        phi = ellipses[i, 5] * np.pi / 180
        
        x_rot = (X - x0) * np.cos(phi) + (Y - y0) * np.sin(phi)
        y_rot = -(X - x0) * np.sin(phi) + (Y - y0) * np.cos(phi)
        
        ellipse = ((x_rot / a) ** 2 + (y_rot / b) ** 2) <= 1
        phantom = phantom + A * ellipse
    
    phantom = np.maximum(phantom, 0)
    phantom = phantom / np.max(phantom)
    
    return phantom


def main_example():
    """压缩感知 MRI 重建完整示例"""
    print('=' * 40)
    print('压缩感知 MRI 重建 - FISTA 算法演示')
    print('=' * 40)
    print()
    
    N = 256
    sampling_ratio = 0.3
    pattern_type = 'variable_density'
    
    print('参数设置:')
    print(f'  图像大小: {N} x {N}')
    print(f'  采样率:   {sampling_ratio * 100:.1f}%')
    print(f'  采样模式: {pattern_type}')
    print()
    
    print('步骤 1: 生成模拟 MRI 图像...')
    original = generate_phantom(N)
    print('  完成.')
    print()
    
    print('步骤 2: 模拟 k-space 欠采样...')
    kspace_undersampled, mask, _ = kspace_simulation(original, sampling_ratio, pattern_type)
    actual_ratio = np.sum(mask) / mask.size
    print(f'  实际采样率: {actual_ratio * 100:.1f}%')
    print('  完成.')
    print()
    
    print('步骤 3: 零填充重建 (用于对比)...')
    undersampled_recon = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace_undersampled)))
    print('  完成.')
    print()
    
    print('步骤 4: FISTA 压缩感知重建...')
    options = {
        'lambda': 0.05,
        'max_iter': 150,
        'tol': 1e-5,
        'wavelet_level': 4,
        'verbose': True
    }
    
    x_recon, history = reconstruction(kspace_undersampled, mask, options)
    print('  完成.')
    print()
    
    print('步骤 5: 显示结果...')
    display_results(original, undersampled_recon, x_recon, mask, history)


if __name__ == '__main__':
    main_example()
