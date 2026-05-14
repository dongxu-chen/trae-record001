import numpy as np
from typing import Tuple, Optional


def pad_image_symmetric(img: np.ndarray, pre_r: int, post_r: int, 
                        pre_c: int, post_c: int) -> np.ndarray:
    """对称边界延拓"""
    rows, cols = img.shape
    total_r = rows + pre_r + post_r
    total_c = cols + pre_c + post_c
    result = np.zeros((total_r, total_c), dtype=img.dtype)
    
    r_orig = np.arange(total_r) - pre_r
    r_idx = np.where(r_orig < 0, -r_orig, 
                     np.where(r_orig >= rows, 2 * rows - r_orig - 1, r_orig))
    
    c_orig = np.arange(total_c) - pre_c
    c_idx = np.where(c_orig < 0, -c_orig, 
                     np.where(c_orig >= cols, 2 * cols - c_orig - 1, c_orig))
    
    rr, cc = np.meshgrid(r_idx, c_idx, indexing='ij')
    result = img[rr, cc]
    return result


def pad_image_periodic(img: np.ndarray, pre_r: int, post_r: int, 
                       pre_c: int, post_c: int) -> np.ndarray:
    """周期边界延拓"""
    rows, cols = img.shape
    r_idx = np.mod(np.arange(rows + pre_r + post_c) - pre_r, rows)
    c_idx = np.mod(np.arange(cols + pre_c + post_c) - pre_c, cols)
    rr, cc = np.meshgrid(r_idx, c_idx, indexing='ij')
    return img[rr, cc]


def pad_image(img: np.ndarray, target_rows: int, target_cols: int, 
              pad_mode: str = 'symmetric') -> np.ndarray:
    """将图像延拓到目标尺寸"""
    rows, cols = img.shape
    
    pad_rows_before = (target_rows - rows) // 2
    pad_rows_after = target_rows - rows - pad_rows_before
    pad_cols_before = (target_cols - cols) // 2
    pad_cols_after = target_cols - cols - pad_cols_before
    
    if pad_mode == 'symmetric':
        return pad_image_symmetric(img, pad_rows_before, pad_rows_after, 
                                   pad_cols_before, pad_cols_after)
    elif pad_mode == 'periodic':
        return pad_image_periodic(img, pad_rows_before, pad_rows_after, 
                                  pad_cols_before, pad_cols_after)
    elif pad_mode == 'zero':
        return np.pad(img, [[pad_rows_before, pad_rows_after], 
                           [pad_cols_before, pad_cols_after]], 
                     mode='constant', constant_values=0)
    else:
        return pad_image_symmetric(img, pad_rows_before, pad_rows_after, 
                                   pad_cols_before, pad_cols_after)


def wavelet_forward(img: np.ndarray, level: int = 3, 
                    pad_mode: str = 'symmetric') -> Tuple[np.ndarray, dict]:
    """二维 Haar 小波前向变换"""
    rows, cols = img.shape
    img = img.astype(np.float64)
    
    pad_rows = int(np.ceil(rows / (2 ** level)) * (2 ** level))
    pad_cols = int(np.ceil(cols / (2 ** level)) * (2 ** level))
    
    meta = {
        'original_size': [rows, cols],
        'padded_size': [pad_rows, pad_cols],
        'pad_mode': pad_mode,
        'level': level
    }
    
    if pad_rows != rows or pad_cols != cols:
        img_padded = pad_image(img, pad_rows, pad_cols, pad_mode)
    else:
        img_padded = img
    
    coeff = img_padded.copy()
    
    for l in range(level):
        r = pad_rows // (2 ** l)
        c = pad_cols // (2 ** l)
        
        block = coeff[:r, :c]
        
        if r % 2 == 1:
            if pad_mode == 'symmetric':
                block = np.concatenate([block, np.flipud(block[-1:, :])], axis=0)
            elif pad_mode == 'periodic':
                block = np.concatenate([block, block[:1, :]], axis=0)
            else:
                block = np.concatenate([block, np.zeros((1, c))], axis=0)
            r = r + 1
            
        if c % 2 == 1:
            if pad_mode == 'symmetric':
                block = np.concatenate([block, np.fliplr(block[:, -1:])], axis=1)
            elif pad_mode == 'periodic':
                block = np.concatenate([block, block[:, :1]], axis=1)
            else:
                block = np.concatenate([block, np.zeros((r, 1))], axis=1)
            c = c + 1
        
        row_even = block[0::2, :]
        row_odd = block[1::2, :]
        
        row_low = (row_even + row_odd) / np.sqrt(2)
        row_high = (row_even - row_odd) / np.sqrt(2)
        
        col_even_low = row_low[:, 0::2]
        col_odd_low = row_low[:, 1::2]
        col_even_high = row_high[:, 0::2]
        col_odd_high = row_high[:, 1::2]
        
        LL = (col_even_low + col_odd_low) / np.sqrt(2)
        LH = (col_even_low - col_odd_low) / np.sqrt(2)
        HL = (col_even_high + col_odd_high) / np.sqrt(2)
        HH = (col_even_high - col_odd_high) / np.sqrt(2)
        
        r2, c2 = LL.shape
        
        coeff[:r2, :c2] = LL
        coeff[:r2, c2:2*c2] = LH
        coeff[r2:2*r2, :c2] = HL
        coeff[r2:2*r2, c2:2*c2] = HH
    
    return coeff, meta


def wavelet_inverse(coeff: np.ndarray, level: int = 3, 
                    meta: Optional[dict] = None) -> np.ndarray:
    """二维 Haar 小波逆变换"""
    if meta is not None:
        rows_full = meta['padded_size'][0]
        cols_full = meta['padded_size'][1]
        original_rows = meta['original_size'][0]
        original_cols = meta['original_size'][1]
    else:
        rows_full, cols_full = coeff.shape
        original_rows, original_cols = rows_full, cols_full
    
    img = coeff.astype(np.float64).copy()
    
    for l in range(level - 1, -1, -1):
        r2 = rows_full // (2 ** (l + 1))
        c2 = cols_full // (2 ** (l + 1))
        
        LL = img[:r2, :c2]
        LH = img[:r2, c2:2*c2]
        HL = img[r2:2*r2, :c2]
        HH = img[r2:2*r2, c2:2*c2]
        
        col_even_low = (LL + LH) / np.sqrt(2)
        col_odd_low = (LL - LH) / np.sqrt(2)
        col_even_high = (HL + HH) / np.sqrt(2)
        col_odd_high = (HL - HH) / np.sqrt(2)
        
        row_low = np.zeros((2 * r2, c2), dtype=np.float64)
        row_low[0::2, :] = col_even_low
        row_low[1::2, :] = col_odd_low
        
        row_high = np.zeros((2 * r2, c2), dtype=np.float64)
        row_high[0::2, :] = col_even_high
        row_high[1::2, :] = col_odd_high
        
        row_even = (row_low + row_high) / np.sqrt(2)
        row_odd = (row_low - row_high) / np.sqrt(2)
        
        block = np.zeros((2 * r2, 2 * c2), dtype=np.float64)
        block[0::2, :] = row_even
        block[1::2, :] = row_odd
        
        img[:2*r2, :2*c2] = block
    
    if meta is not None and (original_rows < rows_full or original_cols < cols_full):
        pad_rows_before = (rows_full - original_rows) // 2
        pad_cols_before = (cols_full - original_cols) // 2
        img = img[pad_rows_before:pad_rows_before+original_rows, 
                  pad_cols_before:pad_cols_before+original_cols]
    
    return img


def wavelet(x: np.ndarray, mode: str, level: int = 3, 
            pad_mode: str = 'symmetric') -> Tuple[np.ndarray, Optional[dict]]:
    """
    二维 Haar 小波变换封装函数
    
    参数:
        x: 输入图像
        mode: 'forward' 或 'inverse'
        level: 分解层数
        pad_mode: 边界延拓模式 'symmetric', 'periodic', 'zero'
    
    返回:
        前向变换: (coeff, meta)
        逆变换: (recon, None)
    """
    if mode.lower() == 'forward':
        return wavelet_forward(x, level, pad_mode)
    elif mode.lower() == 'inverse':
        return wavelet_inverse(x, level), None
    else:
        raise ValueError("mode must be 'forward' or 'inverse'")
