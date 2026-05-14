import numpy as np
import matplotlib.pyplot as plt
from typing import Optional
from reconstruction import History


def rmse(x: np.ndarray, y: np.ndarray) -> float:
    """计算均方根误差"""
    return np.sqrt(np.mean((np.abs(x) - np.abs(y)) ** 2))


def psnr_calc(x: np.ndarray, y: np.ndarray) -> float:
    """计算峰值信噪比 (dB)"""
    max_val = np.max(np.abs(x))
    mse_val = np.mean((np.abs(x) - np.abs(y)) ** 2)
    if mse_val == 0:
        return float('inf')
    return 20 * np.log10(max_val / np.sqrt(mse_val))


def display_results(original: np.ndarray, undersampled: np.ndarray, 
                    reconstructed: np.ndarray, mask: np.ndarray,
                    history: Optional[History] = None) -> None:
    """
    显示 MRI 压缩感知重建结果
    
    参数:
        original: 原始图像
        undersampled: 零填充重建图像
        reconstructed: FISTA 重建图像
        mask: 采样掩膜
        history: 迭代历史 (可选)
    """
    fig = plt.figure(figsize=(15, 9))
    
    plt.subplot(2, 4, 1)
    plt.imshow(np.abs(original), cmap='gray')
    plt.axis('image')
    plt.title('原始图像')
    plt.colorbar()
    
    plt.subplot(2, 4, 2)
    plt.imshow(mask, cmap='gray')
    plt.axis('image')
    plt.title(f'采样掩膜 ({np.sum(mask)/mask.size*100:.1f}%)')
    plt.colorbar()
    
    plt.subplot(2, 4, 3)
    plt.imshow(np.abs(undersampled), cmap='gray')
    plt.axis('image')
    plt.title('零填充重建')
    plt.colorbar()
    
    plt.subplot(2, 4, 4)
    plt.imshow(np.abs(reconstructed), cmap='gray')
    plt.axis('image')
    plt.title('FISTA 重建')
    plt.colorbar()
    
    plt.subplot(2, 4, 5)
    diff_undersampled = np.abs(original - undersampled)
    plt.imshow(diff_undersampled, cmap='hot')
    plt.axis('image')
    plt.title(f'零填充误差 (RMSE={rmse(original, undersampled):.4f})')
    plt.colorbar()
    
    plt.subplot(2, 4, 6)
    diff_recon = np.abs(original - reconstructed)
    plt.imshow(diff_recon, cmap='hot')
    plt.axis('image')
    plt.title(f'FISTA 误差 (RMSE={rmse(original, reconstructed):.4f})')
    plt.colorbar()
    
    plt.subplot(2, 4, 7)
    kspace_original = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(original)))
    plt.imshow(np.log(1 + np.abs(kspace_original)), cmap='jet')
    plt.axis('image')
    plt.title('原始 K-space (log)')
    plt.colorbar()
    
    if history is not None and len(history.obj) > 0:
        plt.subplot(2, 4, 8)
        plt.semilogy(history.obj, 'b-', linewidth=1.5)
        plt.grid(True)
        plt.xlabel('迭代次数')
        plt.ylabel('目标函数值')
        plt.title('FISTA 收敛曲线')
    else:
        plt.subplot(2, 4, 8)
        kspace_undersampled = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(undersampled)))
        plt.imshow(np.log(1 + np.abs(kspace_undersampled)), cmap='jet')
        plt.axis('image')
        plt.title('欠采样 K-space (log)')
        plt.colorbar()
    
    plt.suptitle('压缩感知 MRI 重建结果', fontsize=14)
    plt.tight_layout()
    
    print('=' * 40)
    print('重建质量评估:')
    print('-' * 40)
    print(f'零填充 RMSE:  {rmse(original, undersampled):.6f}')
    print(f'FISTA   RMSE:  {rmse(original, reconstructed):.6f}')
    print(f'零填充 PSNR:  {psnr_calc(original, undersampled):.2f} dB')
    print(f'FISTA   PSNR:  {psnr_calc(original, reconstructed):.2f} dB')
    print('=' * 40)
    
    plt.show()
