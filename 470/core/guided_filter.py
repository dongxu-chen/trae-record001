import numpy as np
import cv2
from typing import Tuple


def box_filter(img: np.ndarray, r: int) -> np.ndarray:
    return cv2.boxFilter(img, -1, (r * 2 + 1, r * 2 + 1), normalize=False)


def guided_filter(guide: np.ndarray, target: np.ndarray, radius: int = 15, 
                  eps: float = 1e-6) -> np.ndarray:
    guide = guide.astype(np.float32)
    target = target.astype(np.float32)
    
    if guide.ndim == 3 and target.ndim == 2:
        target = np.stack([target] * 3, axis=-1)
    elif guide.ndim == 2 and target.ndim == 3:
        guide = np.stack([guide] * 3, axis=-1)
    
    if guide.ndim == 3:
        results = []
        for c in range(target.shape[-1]):
            result = _guided_filter_single(guide[..., c], target[..., c], radius, eps)
            results.append(result)
        return np.stack(results, axis=-1)
    else:
        return _guided_filter_single(guide, target, radius, eps)


def _guided_filter_single(guide: np.ndarray, target: np.ndarray, 
                          radius: int, eps: float) -> np.ndarray:
    h, w = guide.shape
    
    N = box_filter(np.ones((h, w), dtype=np.float32), radius)
    
    mean_I = box_filter(guide, radius) / N
    mean_p = box_filter(target, radius) / N
    
    mean_Ip = box_filter(guide * target, radius) / N
    cov_Ip = mean_Ip - mean_I * mean_p
    
    mean_II = box_filter(guide * guide, radius) / N
    var_I = mean_II - mean_I * mean_I
    
    a = cov_Ip / (var_I + eps)
    b = mean_p - a * mean_I
    
    mean_a = box_filter(a, radius) / N
    mean_b = box_filter(b, radius) / N
    
    q = mean_a * guide + mean_b
    
    return q


def guided_filter_color(guide_rgb: np.ndarray, target: np.ndarray, 
                         radius: int = 15, eps: float = 1e-6) -> np.ndarray:
    guide_rgb = guide_rgb.astype(np.float32)
    target = target.astype(np.float32)
    
    if target.ndim == 2:
        target = np.expand_dims(target, axis=-1)
    
    h, w = guide_rgb.shape[:2]
    N = box_filter(np.ones((h, w), dtype=np.float32), radius)
    
    mean_I = np.zeros((3, h, w), dtype=np.float32)
    for c in range(3):
        mean_I[c] = box_filter(guide_rgb[..., c], radius) / N
    
    mean_p = np.zeros((target.shape[-1], h, w), dtype=np.float32)
    for c in range(target.shape[-1]):
        mean_p[c] = box_filter(target[..., c], radius) / N
    
    mean_Ip = np.zeros((3, target.shape[-1], h, w), dtype=np.float32)
    for c in range(3):
        for d in range(target.shape[-1]):
            mean_Ip[c, d] = box_filter(guide_rgb[..., c] * target[..., d], radius) / N
    
    cov_Ip = mean_Ip - mean_I[:, None, :, :] * mean_p[None, :, :, :]
    
    mean_II = np.zeros((3, 3, h, w), dtype=np.float32)
    for c in range(3):
        for d in range(3):
            mean_II[c, d] = box_filter(guide_rgb[..., c] * guide_rgb[..., d], radius) / N
    
    var_I = mean_II - mean_I[:, None, :, :] * mean_I[None, :, :, :]
    
    eps_mat = eps * np.eye(3, dtype=np.float32)
    
    a = np.zeros((3, target.shape[-1], h, w), dtype=np.float32)
    b = np.zeros((target.shape[-1], h, w), dtype=np.float32)
    
    for y in range(h):
        for x in range(w):
            Sigma = var_I[:, :, y, x] + eps_mat
            Sigma_inv = np.linalg.inv(Sigma)
            for d in range(target.shape[-1]):
                cov = cov_Ip[:, d, y, x]
                a[:, d, y, x] = Sigma_inv @ cov
                b[d, y, x] = mean_p[d, y, x] - a[:, d, y, x] @ mean_I[:, y, x]
    
    mean_a = np.zeros_like(a)
    mean_b = np.zeros_like(b)
    
    for c in range(3):
        for d in range(target.shape[-1]):
            mean_a[c, d] = box_filter(a[c, d], radius) / N
    
    for d in range(target.shape[-1]):
        mean_b[d] = box_filter(b[d], radius) / N
    
    q = np.zeros_like(target)
    for d in range(target.shape[-1]):
        q[..., d] = np.sum(mean_a[:, d] * guide_rgb.transpose(2, 0, 1), axis=0) + mean_b[d]
    
    if q.shape[-1] == 1:
        q = q.squeeze(-1)
    
    return q


def fast_guided_filter(guide: np.ndarray, target: np.ndarray, radius: int = 15,
                       eps: float = 1e-6, subsample_ratio: int = 4) -> np.ndarray:
    h, w = guide.shape[:2]
    sh, sw = h // subsample_ratio, w // subsample_ratio
    
    if guide.ndim == 3:
        guide_sub = cv2.resize(guide, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        guide_sub = cv2.resize(guide, (sw, sh), interpolation=cv2.INTER_AREA)
    
    if target.ndim == 3:
        target_sub = cv2.resize(target, (sw, sh), interpolation=cv2.INTER_AREA)
    else:
        target_sub = cv2.resize(target, (sw, sh), interpolation=cv2.INTER_AREA)
    
    r_sub = max(radius // subsample_ratio, 1)
    
    if guide.ndim == 3 and target.ndim == 3:
        q_sub = guided_filter_color(guide_sub, target_sub, r_sub, eps)
    elif guide.ndim == 3:
        q_sub = guided_filter(guide_sub, target_sub, r_sub, eps)
    else:
        q_sub = guided_filter(guide_sub, target_sub, r_sub, eps)
    
    if q_sub.ndim == 3:
        q = cv2.resize(q_sub, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        q = cv2.resize(q_sub, (w, h), interpolation=cv2.INTER_LINEAR)
    
    return q


def guided_filter_refine(saliency_map: np.ndarray, guide_image: np.ndarray,
                          radius: int = 15, eps: float = 1e-3,
                          use_color: bool = True, fast: bool = False) -> np.ndarray:
    guide_image = guide_image.astype(np.float32) / 255.0 if guide_image.max() > 1.0 else guide_image
    saliency_map = saliency_map.astype(np.float32)
    
    if fast:
        refined = fast_guided_filter(guide_image, saliency_map, radius, eps)
    else:
        if use_color and guide_image.ndim == 3:
            refined = guided_filter_color(guide_image, saliency_map, radius, eps)
        else:
            if guide_image.ndim == 3:
                guide_gray = cv2.cvtColor(guide_image, cv2.COLOR_RGB2GRAY)
            else:
                guide_gray = guide_image
            refined = guided_filter(guide_gray, saliency_map, radius, eps)
    
    refined = np.clip(refined, 0, 1)
    
    return refined


def soft_threshold_refine(saliency_map: np.ndarray, threshold: float = 0.5,
                           alpha: float = 10.0) -> np.ndarray:
    refined = 1.0 / (1.0 + np.exp(-alpha * (saliency_map - threshold)))
    return refined


def guided_edge_refinement(saliency_map: np.ndarray, binary_mask: np.ndarray,
                            original_image: np.ndarray,
                            radius: int = 15, eps: float = 1e-3,
                            threshold: float = 0.5,
                            use_soft_threshold: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    refined_saliency = guided_filter_refine(
        saliency_map, original_image, radius=radius, eps=eps
    )
    
    if use_soft_threshold:
        refined_saliency = soft_threshold_refine(refined_saliency, threshold)
    
    refined_mask = (refined_saliency > threshold).astype(np.float32)
    
    mask_uint8 = (refined_mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        for contour in contours:
            epsilon = 0.0005 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            cv2.drawContours(refined_mask, [approx], 0, 1, thickness=cv2.FILLED)
    
    refined_saliency = refined_saliency * refined_mask
    
    from utils.helpers import min_max_normalize
    refined_saliency = min_max_normalize(refined_saliency)
    
    return refined_saliency, refined_mask


class GuidedFilterRefiner:
    def __init__(self, radius: int = 15, eps: float = 1e-3,
                 use_color: bool = True, fast: bool = False,
                 use_soft_threshold: bool = True):
        self.radius = radius
        self.eps = eps
        self.use_color = use_color
        self.fast = fast
        self.use_soft_threshold = use_soft_threshold
    
    def refine(self, saliency_map: np.ndarray, binary_mask: np.ndarray,
               original_image: np.ndarray, threshold: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        return guided_edge_refinement(
            saliency_map, binary_mask, original_image,
            radius=self.radius, eps=self.eps,
            threshold=threshold,
            use_soft_threshold=self.use_soft_threshold
        )
    
    def __call__(self, saliency_map: np.ndarray, binary_mask: np.ndarray,
                 original_image: np.ndarray, threshold: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        return self.refine(saliency_map, binary_mask, original_image, threshold)
