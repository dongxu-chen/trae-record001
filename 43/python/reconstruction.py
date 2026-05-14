import numpy as np
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from wavelet import wavelet_forward, wavelet_inverse


@dataclass
class History:
    obj: np.ndarray
    error: np.ndarray
    L: np.ndarray


def soft_threshold(x: np.ndarray, thresh: float) -> np.ndarray:
    """软阈值算子"""
    return np.sign(x) * np.maximum(np.abs(x) - thresh, 0)


def compute_gradient(x: np.ndarray, y: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """计算数据保真项的梯度"""
    F_x = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(x)))
    residual = mask * F_x - y
    grad = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(mask * residual)))
    return np.real(grad)


def compute_data_fidelity(x: np.ndarray, y: np.ndarray, mask: np.ndarray) -> float:
    """计算数据保真项"""
    F_x = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(x)))
    return 0.5 * np.sum(np.abs(mask.flatten() * F_x.flatten() - y.flatten()) ** 2)


def compute_objective(x: np.ndarray, y: np.ndarray, mask: np.ndarray, 
                      lambda_: float, wavelet_level: int,
                      pad_mode: str = 'symmetric') -> float:
    """计算目标函数值"""
    data_term = compute_data_fidelity(x, y, mask)
    coeff, _ = wavelet_forward(x, wavelet_level, pad_mode)
    reg_term = lambda_ * np.sum(np.abs(coeff.flatten()))
    return data_term + reg_term


def reconstruction(kspace_undersampled: np.ndarray, mask: np.ndarray,
                   options: Optional[Dict[str, Any]] = None
                   ) -> Tuple[np.ndarray, History]:
    """
    基于 FISTA 的压缩感知 MRI 图像重建
    
    最小化问题: 0.5*||M·F·x - y||_2^2 + lambda*||W·x||_1
    
    参数:
        kspace_undersampled: 欠采样 k-space 数据
        mask: 采样掩膜
        options: 参数字典
            'lambda': L1 正则化参数 (默认 0.01)
            'max_iter': 最大迭代次数 (默认 100)
            'tol': 收敛阈值 (默认 1e-6)
            'wavelet_level': 小波分解层数 (默认 3)
            'verbose': 是否显示迭代信息 (默认 True)
            'use_backtracking': 是否使用回溯线搜索 (默认 True)
            'L_min': 最小 Lipschitz 常数估计 (默认 1e-3)
            'L_max': 最大 Lipschitz 常数估计 (默认 1e3)
            'pad_mode': 边界延拓模式 (默认 'symmetric')
    
    返回:
        x_recon: 重建图像
        history: 迭代历史记录
    """
    if options is None:
        options = {}
    
    lambda_ = options.get('lambda', 0.01)
    max_iter = options.get('max_iter', 100)
    tol = options.get('tol', 1e-6)
    wavelet_level = options.get('wavelet_level', 3)
    verbose = options.get('verbose', True)
    use_backtracking = options.get('use_backtracking', True)
    L_min = options.get('L_min', 1e-3)
    L_max = options.get('L_max', 1e3)
    pad_mode = options.get('pad_mode', 'symmetric')
    
    y = kspace_undersampled
    rows, cols = y.shape
    
    L = 1.0
    
    x = np.zeros((rows, cols), dtype=np.float64)
    x_prev = x.copy()
    t = 1.0
    
    obj_history = np.zeros(max_iter)
    error_history = np.zeros(max_iter)
    L_history = np.zeros(max_iter)
    
    grad_prev = None
    x_prev2 = None
    
    for k in range(max_iter):
        
        w = x + ((t - 1) / (t + 1)) * (x - x_prev)
        
        grad = compute_gradient(w, y, mask)
        
        if k > 0 and grad_prev is not None and x_prev2 is not None:
            s = w.flatten() - x_prev2.flatten()
            y_grad = grad.flatten() - grad_prev.flatten()
            s_norm_sq = np.sum(np.abs(s) ** 2)
            if s_norm_sq > 1e-15:
                L_bb = np.abs(np.sum(np.conj(y_grad) * s)) / s_norm_sq
                L_bb = max(L_min, min(L_max, L_bb))
                L = 0.5 * L + 0.5 * L_bb
        
        if use_backtracking:
            eta = 1.5
            max_backtrack = 10
            f_w = compute_data_fidelity(w, y, mask)
            grad_w = grad
            
            for bt in range(max_backtrack):
                y_step = w - (1.0 / L) * grad_w
                
                coeff, meta = wavelet_forward(y_step, wavelet_level, pad_mode)
                coeff_thresh = soft_threshold(coeff, lambda_ / L)
                x_candidate = wavelet_inverse(coeff_thresh, wavelet_level, meta)
                
                f_x = compute_data_fidelity(x_candidate, y, mask)
                
                diff = x_candidate.flatten() - w.flatten()
                q = f_w + np.real(np.sum(np.conj(grad_w.flatten()) * diff)) + \
                    (L / 2) * np.sum(np.abs(diff) ** 2)
                
                if f_x <= q + 1e-10 * max(1, abs(f_w)):
                    break
                L = min(L_max, L * eta)
            
            x_new = x_candidate
        else:
            y_step = w - (1.0 / L) * grad
            coeff, meta = wavelet_forward(y_step, wavelet_level, pad_mode)
            coeff_thresh = soft_threshold(coeff, lambda_ / L)
            x_new = wavelet_inverse(coeff_thresh, wavelet_level, meta)
        
        t_new = (1.0 + np.sqrt(1 + 4 * t ** 2)) / 2
        
        if k > 0:
            x_norm = np.linalg.norm(x.flatten())
            if x_norm > 0:
                error_history[k] = np.linalg.norm(x_new.flatten() - x.flatten()) / x_norm
            else:
                error_history[k] = np.linalg.norm(x_new.flatten() - x.flatten())
            if error_history[k] < tol and verbose:
                print(f'Converged at iteration {k+1}')
                break
        
        x_prev2 = w.copy()
        grad_prev = grad.copy()
        
        x_prev = x.copy()
        x = x_new.copy()
        t = t_new
        
        obj_history[k] = compute_objective(x, y, mask, lambda_, wavelet_level, pad_mode)
        L_history[k] = L
        
        if verbose and (k + 1) % 10 == 0:
            print(f'Iter {k+1:4d}: Objective = {obj_history[k]:.6e}, '
                  f'Rel. Change = {error_history[k]:.2e}, L = {L:.2e}')
    
    history = History(
        obj=obj_history[:k+1], 
        error=error_history[:k+1],
        L=L_history[:k+1]
    )
    x_recon = x
    
    return x_recon, history
