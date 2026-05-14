import numpy as np
from typing import Tuple


def bresenham_line(r0: int, c0: int, r1: int, c1: int, 
                   max_r: int, max_c: int) -> np.ndarray:
    """
    Bresenham 直线算法生成从 (r0,c0) 到 (r1,c1) 的像素索引
    返回展平的一维索引数组
    """
    r0 = int(max(0, min(max_r - 1, r0)))
    c0 = int(max(0, min(max_c - 1, c0)))
    r1 = int(max(0, min(max_r - 1, r1)))
    c1 = int(max(0, min(max_c - 1, c1)))
    
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    
    if dr == 0 and dc == 0:
        return np.array([r0 * max_c + c0], dtype=np.int64)
    
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    
    if dr > dc:
        err = dr / 2
    else:
        err = -dc / 2
    
    r, c = r0, c0
    
    max_points = dr + dc + 1
    points = np.zeros((max_points, 2), dtype=np.int64)
    count = 0
    
    while True:
        points[count] = [r, c]
        count += 1
        
        if r == r1 and c == c1:
            break
        
        e2 = err
        
        if e2 > -dr:
            err -= dc
            r += sr
        
        if e2 < dc:
            err += dr
            c += sc
    
    points = points[:count]
    
    valid = (points[:, 0] >= 0) & (points[:, 0] < max_r) & \
            (points[:, 1] >= 0) & (points[:, 1] < max_c)
    points = points[valid]
    
    indices = points[:, 0] * max_c + points[:, 1]
    indices = np.unique(indices)
    
    return indices


def generate_mask(rows: int, cols: int, sampling_ratio: float, 
                  pattern_type: str = 'variable_density',
                  seed: int = 42) -> np.ndarray:
    """生成 k-space 采样掩膜"""
    rng = np.random.RandomState(seed)
    
    if pattern_type == 'random':
        mask = rng.rand(rows, cols) < sampling_ratio
        
    elif pattern_type == 'radial':
        mask = np.zeros((rows, cols), dtype=bool)
        total_samples = rows * cols
        target_samples = int(round(total_samples * sampling_ratio))
        
        center_row = (rows - 1) / 2
        center_col = (cols - 1) / 2
        
        r = min(rows, cols) / 2
        samples_per_spoke = 2 * int(np.floor(r)) + 1
        
        num_spokes = max(1, int(round(target_samples / samples_per_spoke)))
        
        for k in range(num_spokes):
            theta = k * 2 * np.pi / num_spokes
            
            end_col = round(center_col + r * np.cos(theta))
            end_row = round(center_row + r * np.sin(theta))
            
            line_indices = bresenham_line(int(round(center_row)), int(round(center_col)),
                                          int(end_row), int(end_col), rows, cols)
            mask_flat = mask.flatten()
            mask_flat[line_indices] = True
            mask = mask_flat.reshape(rows, cols)
            
            end_col2 = round(center_col - r * np.cos(theta))
            end_row2 = round(center_row - r * np.sin(theta))
            line_indices2 = bresenham_line(int(round(center_row)), int(round(center_col)),
                                           int(end_row2), int(end_col2), rows, cols)
            mask_flat = mask.flatten()
            mask_flat[line_indices2] = True
            mask = mask_flat.reshape(rows, cols)
            
    elif pattern_type == 'variable_density':
        X, Y = np.meshgrid(np.linspace(-1, 1, cols), np.linspace(-1, 1, rows))
        R = np.sqrt(X ** 2 + Y ** 2)
        p = 1.0 - R
        p = np.maximum(p, 0)
        p = p / p.max()
        
        target_count = int(round(rows * cols * sampling_ratio))
        mask = np.zeros((rows, cols), dtype=bool)
        
        center_radius = min(rows, cols) * 0.08
        center_x = cols // 2
        center_y = rows // 2
        
        yy, xx = np.meshgrid(np.arange(rows), np.arange(cols), indexing='ij')
        dist_from_center = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
        mask[dist_from_center <= center_radius] = True
        
        current_count = mask.sum()
        remaining = target_count - current_count
        
        if remaining > 0:
            candidates = np.where(~mask)
            p_candidates = p[candidates]
            if p_candidates.sum() > 0:
                p_candidates = p_candidates / p_candidates.sum()
            
            if len(candidates[0]) > 0:
                num_samples = min(remaining, len(candidates[0]))
                choice_idx = rng.choice(len(candidates[0]), size=num_samples, 
                                       replace=True, p=p_candidates)
                mask_flat = mask.flatten()
                flat_idx = candidates[0][choice_idx] * cols + candidates[1][choice_idx]
                mask_flat[flat_idx] = True
                mask = mask_flat.reshape(rows, cols)
    else:
        raise ValueError(f'Unknown pattern type: {pattern_type}')
    
    return mask.astype(np.float64)


def kspace_simulation(img: np.ndarray, sampling_ratio: float, 
                      pattern_type: str = 'variable_density',
                      seed: int = 42
                      ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    模拟 MRI k-space 欠采样
    
    参数:
        img: 输入图像 (2D 矩阵)
        sampling_ratio: 采样比例 (0 < ratio < 1)
        pattern_type: 采样模式 - 'random', 'radial', 'variable_density'
        seed: 随机数种子
    
    返回:
        kspace_undersampled: 欠采样 k-space 数据
        mask: 采样掩膜 (1=采样, 0=未采样)
        kspace_full: 完全采样的 k-space 数据
    """
    rows, cols = img.shape
    
    kspace_full = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(img)))
    
    mask = generate_mask(rows, cols, sampling_ratio, pattern_type, seed)
    
    kspace_undersampled = kspace_full * mask
    
    return kspace_undersampled, mask, kspace_full
