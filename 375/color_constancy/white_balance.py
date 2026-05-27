import numpy as np
import cv2


def correct_white_balance(image, illuminant, method='vonkries', 
                          chromatic_adaptation='cat02', 
                          target_illuminant=None):
    """
    Apply white balance correction using estimated illuminant.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8 or float32
        illuminant: Estimated illuminant [R, G, B] normalized
        method: Correction method - 'vonkries', 'scaling', or 'sharp'
        chromatic_adaptation: Chromatic adaptation transform - 'cat02', 'bradford', or 'vonkries'
        target_illuminant: Target illuminant [R, G, B], default: equal energy white [1,1,1]
    
    Returns:
        corrected: White balanced image (H, W, 3) in uint8
    """
    img_float = image.astype(np.float32)
    
    if target_illuminant is None:
        target_illuminant = np.ones(3, dtype=np.float32)
    
    src = np.array(illuminant, dtype=np.float32).reshape(3)
    dst = np.array(target_illuminant, dtype=np.float32).reshape(3)
    
    src = src / np.linalg.norm(src)
    dst = dst / np.linalg.norm(dst)
    
    if method == 'scaling':
        scale = dst / (src + 1e-8)
        corrected = img_float * scale.reshape(1, 1, 3)
    
    elif method == 'vonkries':
        M = get_chromatic_adaptation_matrix(chromatic_adaptation)
        M_inv = np.linalg.inv(M)
        
        src_lms = M @ src
        dst_lms = M @ dst
        
        scale = dst_lms / (src_lms + 1e-8)
        
        pixels = img_float.reshape(-1, 3)
        pixels_lms = (M @ pixels.T).T
        pixels_lms = pixels_lms * scale.reshape(1, 3)
        corrected_pixels = (M_inv @ pixels_lms.T).T
        corrected = corrected_pixels.reshape(img_float.shape)
    
    elif method == 'sharp':
        M_sharp = np.array([
            [1.2694, -0.0988, -0.1706],
            [-0.8364, 1.8006, 0.0357],
            [0.0297, -0.0315, 1.0018]
        ], dtype=np.float32)
        M_inv = np.linalg.inv(M_sharp)
        
        src_lms = M_sharp @ src
        dst_lms = M_sharp @ dst
        
        scale = dst_lms / (src_lms + 1e-8)
        
        pixels = img_float.reshape(-1, 3)
        pixels_lms = (M_sharp @ pixels.T).T
        pixels_lms = pixels_lms * scale.reshape(1, 3)
        corrected_pixels = (M_inv @ pixels_lms.T).T
        corrected = corrected_pixels.reshape(img_float.shape)
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    corrected = np.clip(corrected, 0, 255)
    corrected = corrected.astype(np.uint8)
    
    return corrected


def get_chromatic_adaptation_matrix(method='cat02'):
    """
    Get chromatic adaptation transform matrix.
    
    Args:
        method: 'cat02', 'bradford', or 'vonkries'
    
    Returns:
        M: 3x3 chromatic adaptation matrix
    """
    method = method.lower()
    
    if method == 'cat02':
        M = np.array([
            [0.7328, 0.4296, -0.1624],
            [-0.7036, 1.6975, 0.0061],
            [0.0030, 0.0136, 0.9834]
        ], dtype=np.float32)
    
    elif method == 'bradford':
        M = np.array([
            [0.8951, 0.2664, -0.1614],
            [-0.7502, 1.7135, 0.0367],
            [0.0389, -0.0685, 1.0296]
        ], dtype=np.float32)
    
    elif method == 'vonkries':
        M = np.array([
            [0.40024, 0.70760, -0.08081],
            [-0.22630, 1.16532, 0.04570],
            [0.00000, 0.00000, 0.91822]
        ], dtype=np.float32)
    
    else:
        raise ValueError(f"Unknown chromatic adaptation method: {method}")
    
    return M


def simplest_color_balance(image, percentile=1):
    """
    Simplest Color Balance (SCB) - auto white balance by percentile clipping.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8
        percentile: Percentile to clip (default: 1, i.e., 1%-99%)
    
    Returns:
        corrected: White balanced image (H, W, 3) in uint8
    """
    img_float = image.astype(np.float32)
    corrected = np.zeros_like(img_float)
    
    for c in range(3):
        channel = img_float[:, :, c]
        low = np.percentile(channel, percentile)
        high = np.percentile(channel, 100 - percentile)
        
        normalized = (channel - low) / (high - low + 1e-8)
        normalized = np.clip(normalized, 0, 1)
        corrected[:, :, c] = normalized * 255
    
    return corrected.astype(np.uint8)


def gray_world_wb(image):
    """
    Gray World white balance - direct application.
    
    Args:
        image: Input BGR image (H, W, 3) in uint8
    
    Returns:
        corrected: White balanced image (H, W, 3) in uint8
    """
    from .algorithms import gray_world
    illum = gray_world(image)
    return correct_white_balance(image, illum)


def apply_gain(image, gains):
    """
    Apply channel gains to image.
    
    Args:
        image: Input BGR image (H, W, 3)
        gains: RGB gains [R_gain, G_gain, B_gain]
    
    Returns:
        corrected: Gain-applied image (H, W, 3) in uint8
    """
    img_float = image.astype(np.float32)
    gains = np.array(gains, dtype=np.float32).reshape(1, 1, 3)
    corrected = np.clip(img_float * gains, 0, 255)
    return corrected.astype(np.uint8)


def estimate_gains(illuminant, target_illuminant=None):
    """
    Estimate channel gains from illuminant.
    
    Args:
        illuminant: Estimated illuminant [R, G, B]
        target_illuminant: Target illuminant, default: [1,1,1]
    
    Returns:
        gains: RGB gains [R_gain, G_gain, B_gain]
    """
    if target_illuminant is None:
        target = np.ones(3, dtype=np.float32)
    else:
        target = np.array(target_illuminant, dtype=np.float32)
    
    illum = np.array(illuminant, dtype=np.float32)
    gains = target / (illum + 1e-8)
    
    return gains
