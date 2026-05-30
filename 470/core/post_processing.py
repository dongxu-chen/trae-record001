import cv2
import numpy as np
from config import Config
from utils.helpers import min_max_normalize


def refine_edges(saliency_map, binary_mask, kernel_size=None, iterations=2):
    if kernel_size is None:
        kernel_size = Config.MORPH_KERNEL_SIZE
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    refined_mask = cv2.morphologyEx(
        binary_mask.astype(np.uint8), 
        cv2.MORPH_CLOSE, 
        kernel, 
        iterations=iterations
    )
    refined_mask = cv2.morphologyEx(
        refined_mask, 
        cv2.MORPH_OPEN, 
        kernel, 
        iterations=iterations
    )
    
    refined_mask = cv2.GaussianBlur(
        refined_mask.astype(np.float32), 
        (5, 5), 
        0
    )
    refined_mask = (refined_mask > 0.5).astype(np.float32)
    
    contours, _ = cv2.findContours(
        refined_mask.astype(np.uint8), 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    if contours:
        for contour in contours:
            epsilon = 0.001 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            cv2.drawContours(refined_mask, [approx], 0, 1, thickness=cv2.FILLED)
    
    refined_saliency = saliency_map * refined_mask
    refined_saliency = min_max_normalize(refined_saliency)
    
    return refined_saliency, refined_mask


def segment_salient_object(original_image, saliency_map, binary_mask, threshold=None):
    if threshold is None:
        threshold = Config.THRESHOLD
    
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    
    mask_3ch = np.stack([binary_mask] * 3, axis=-1)
    
    segmented = original_image.astype(np.float32) * mask_3ch
    
    alpha_channel = (binary_mask * 255).astype(np.uint8)
    
    if original_image.shape[2] == 3:
        bgr = cv2.cvtColor(original_image, cv2.COLOR_RGB2BGR)
        bgra = np.dstack([bgr, alpha_channel])
    else:
        bgra = original_image.copy()
        bgra[..., -1] = alpha_channel
    
    contours, _ = cv2.findContours(
        binary_mask.astype(np.uint8), 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    bounding_boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area > 100:
            bounding_boxes.append({
                'bbox': (x, y, w, h),
                'area': area,
                'centroid': (x + w // 2, y + h // 2)
            })
    
    bounding_boxes.sort(key=lambda x: x['area'], reverse=True)
    
    return {
        'segmented_rgb': segmented.astype(np.uint8),
        'segmented_bgra': bgra,
        'alpha_mask': alpha_channel,
        'contours': contours,
        'bounding_boxes': bounding_boxes,
        'num_objects': len(bounding_boxes)
    }


def apply_mask(original_image, mask, apply_type='segment', background_color=(0, 0, 0)):
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    
    if len(mask.shape) == 2:
        mask_3ch = np.stack([mask] * 3, axis=-1)
    else:
        mask_3ch = mask
    
    if apply_type == 'segment':
        result = original_image.astype(np.float32) * mask_3ch
    elif apply_type == 'blur_background':
        blurred = cv2.GaussianBlur(original_image, (31, 31), 0)
        result = original_image.astype(np.float32) * mask_3ch + \
                 blurred.astype(np.float32) * (1 - mask_3ch)
    elif apply_type == 'color_background':
        bg = np.full_like(original_image, background_color, dtype=np.float32)
        result = original_image.astype(np.float32) * mask_3ch + bg * (1 - mask_3ch)
    else:
        raise ValueError(f"Unknown apply_type: {apply_type}")
    
    return result.astype(np.uint8)


def overlay_saliency(original_image, saliency_map, alpha=0.5, colormap=cv2.COLORMAP_JET):
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    
    saliency_normalized = (saliency_map * 255).astype(np.uint8)
    saliency_colored = cv2.applyColorMap(saliency_normalized, colormap)
    saliency_colored = cv2.cvtColor(saliency_colored, cv2.COLOR_BGR2RGB)
    
    overlay = cv2.addWeighted(original_image, 1 - alpha, saliency_colored, alpha, 0)
    
    return overlay


def extract_boundary(binary_mask, thickness=1):
    mask_uint8 = binary_mask.astype(np.uint8)
    
    edges = cv2.Canny(mask_uint8 * 255, 0, 255)
    
    if thickness > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (thickness, thickness))
        edges = cv2.dilate(edges, kernel, iterations=1)
    
    return (edges / 255).astype(np.float32)


def draw_boundaries(original_image, binary_mask, color=(255, 0, 0), thickness=2):
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    
    boundary = extract_boundary(binary_mask, thickness=1)
    
    result = original_image.copy()
    result[boundary > 0] = color
    
    return result


def postprocess_saliency_map(saliency_map, binary_mask, threshold=None, refine=True,
                              refine_method='guided', original_image=None,
                              guided_radius=15, guided_eps=1e-3):
    if threshold is None:
        threshold = Config.THRESHOLD
    
    if refine:
        if refine_method == 'guided' and original_image is not None:
            try:
                from .guided_filter import guided_edge_refinement
                saliency_map, binary_mask = guided_edge_refinement(
                    saliency_map, binary_mask, original_image,
                    radius=guided_radius, eps=guided_eps, threshold=threshold
                )
            except ImportError:
                saliency_map, binary_mask = refine_edges(saliency_map, binary_mask)
        else:
            saliency_map, binary_mask = refine_edges(saliency_map, binary_mask)
    
    saliency_map = min_max_normalize(saliency_map)
    
    return saliency_map, binary_mask


def get_saliency_stats(saliency_map, binary_mask):
    stats = {
        'mean_saliency': float(saliency_map.mean()),
        'max_saliency': float(saliency_map.max()),
        'min_saliency': float(saliency_map.min()),
        'std_saliency': float(saliency_map.std()),
        'mask_area_ratio': float(binary_mask.mean()),
        'mask_pixel_count': int(binary_mask.sum()),
        'total_pixels': int(binary_mask.size)
    }
    
    return stats
