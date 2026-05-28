import torch
import torch.nn.functional as F
import numpy as np
import cv2


def normalize_flow(flow):
    flow_norm = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
    flow_norm = torch.clamp(flow_norm, min=1e-6)
    return flow / flow_norm, flow_norm


def resize_flow(flow, new_h, new_w):
    old_h, old_w = flow.shape[2], flow.shape[3]
    flow_resized = F.interpolate(flow, size=(new_h, new_w), mode='bilinear', align_corners=False)
    flow_resized[:, 0] *= (new_w / old_w)
    flow_resized[:, 1] *= (new_h / old_h)
    return flow_resized


def bilinear_warp(image, flow):
    B, C, H, W = image.size()
    
    y_grid, x_grid = torch.meshgrid(torch.arange(H, device=image.device), 
                                   torch.arange(W, device=image.device),
                                   indexing='ij')
    x_grid = x_grid.float().unsqueeze(0).unsqueeze(0)
    y_grid = y_grid.float().unsqueeze(0).unsqueeze(0)
    
    x_new = x_grid + flow[:, 0:1, :, :]
    y_new = y_grid + flow[:, 1:2, :, :]
    
    x_new = 2.0 * x_new / (W - 1) - 1.0
    y_new = 2.0 * y_new / (H - 1) - 1.0
    
    grid = torch.cat([x_new, y_new], dim=1).permute(0, 2, 3, 1)
    
    warped = F.grid_sample(image, grid, mode='bilinear', padding_mode='border', align_corners=True)
    
    return warped


def warp_flow(flow, warp_flow_field):
    return bilinear_warp(flow, warp_flow_field)


def compute_flow_consistency(flow_forward, flow_backward):
    flow_forward_warped = warp_flow(flow_forward, flow_backward)
    flow_backward_warped = warp_flow(flow_backward, flow_forward)
    
    diff_forward = torch.sum((flow_forward + flow_backward_warped) ** 2, dim=1, keepdim=True)
    diff_backward = torch.sum((flow_backward + flow_forward_warped) ** 2, dim=1, keepdim=True)
    
    consistency_map = torch.max(diff_forward, diff_backward)
    return consistency_map


def compute_occlusion_mask_advanced(flow_forward, flow_backward, threshold=0.01, edge_aware=True):
    B, _, H, W = flow_forward.shape
    
    consistency = compute_flow_consistency(flow_forward, flow_backward)
    
    flow_norm_forward = torch.sum(flow_forward ** 2, dim=1, keepdim=True)
    flow_norm_backward = torch.sum(flow_backward ** 2, dim=1, keepdim=True)
    max_flow_norm = torch.max(flow_norm_forward, flow_norm_backward)
    
    normalized_consistency = consistency / (max_flow_norm + threshold)
    
    occlusion_mask = (normalized_consistency > threshold).float()
    
    if edge_aware:
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], 
                               dtype=torch.float32, device=flow_forward.device).view(1, 1, 3, 3)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], 
                               dtype=torch.float32, device=flow_forward.device).view(1, 1, 3, 3)
        
        gray_forward = torch.mean(flow_norm_forward, dim=1, keepdim=True)
        edge_x = F.conv2d(gray_forward, sobel_x, padding=1)
        edge_y = F.conv2d(gray_forward, sobel_y, padding=1)
        edge_mag = torch.sqrt(edge_x ** 2 + edge_y ** 2)
        edge_mag = edge_mag / (edge_mag.max() + 1e-6)
        
        edge_region = (edge_mag > 0.3).float()
        occlusion_mask = torch.clamp(occlusion_mask - edge_region * 0.5, min=0.0)
    
    return occlusion_mask


def compute_occlusion_mask(flow_forward, flow_backward, threshold=0.01):
    return compute_occlusion_mask_advanced(flow_forward, flow_backward, threshold, edge_aware=False)


def compute_occlusion_confidence(flow_forward, flow_backward):
    consistency = compute_flow_consistency(flow_forward, flow_backward)
    
    flow_norm = torch.sqrt(torch.sum(flow_forward ** 2, dim=1, keepdim=True) + 
                           torch.sum(flow_backward ** 2, dim=1, keepdim=True))
    
    confidence = torch.exp(-consistency / (flow_norm + 1e-6))
    confidence = torch.clamp(confidence, min=0.0, max=1.0)
    
    return confidence


def fill_occlusion_regions(warped1, warped2, flow_forward, flow_backward, 
                           occlusion_mask, original1, original2, t=0.5):
    confidence = compute_occlusion_confidence(flow_forward, flow_backward)
    
    weight1 = (1 - occlusion_mask) * confidence * (1 - t)
    weight2 = (1 - occlusion_mask) * confidence * t
    
    occluded_weight1 = occlusion_mask * (1 - t) * 0.5
    occluded_weight2 = occlusion_mask * t * 0.5
    
    weight1 = weight1 + occluded_weight1
    weight2 = weight2 + occluded_weight2
    
    original_warped1 = bilinear_warp(original1, flow_forward * t)
    original_warped2 = bilinear_warp(original2, flow_backward * (1 - t))
    
    total_weight = weight1 + weight2 + 1e-6
    
    filled = (weight1 * original_warped1 + weight2 * original_warped2) / total_weight
    
    return filled


def adaptive_blend_frames(warped1, warped2, flow_forward, flow_backward, t=0.5):
    B, C, H, W = warped1.shape
    
    confidence = compute_occlusion_confidence(flow_forward, flow_backward)
    
    flow_mag_forward = torch.sqrt(torch.sum(flow_forward ** 2, dim=1, keepdim=True))
    flow_mag_backward = torch.sqrt(torch.sum(flow_backward ** 2, dim=1, keepdim=True))
    
    reliability1 = 1.0 / (1.0 + flow_mag_forward * 0.1)
    reliability2 = 1.0 / (1.0 + flow_mag_backward * 0.1)
    
    weight1 = (1 - t) * reliability1 * confidence
    weight2 = t * reliability2 * confidence
    
    total_weight = weight1 + weight2 + 1e-6
    
    blended = (weight1 * warped1 + weight2 * warped2) / total_weight
    
    return blended, confidence


def flow_to_image(flow, max_flow=None):
    flow_np = flow.cpu().numpy()
    
    if flow_np.ndim == 4:
        flow_np = flow_np[0]
    
    flow_np = flow_np.transpose(1, 2, 0)
    
    u = flow_np[:, :, 0]
    v = flow_np[:, :, 1]
    
    if max_flow is None:
        max_flow = np.max(np.sqrt(u ** 2 + v ** 2))
        max_flow = max(max_flow, 1e-5)
    
    u = u / max_flow
    v = v / max_flow
    
    hsv = np.zeros((flow_np.shape[0], flow_np.shape[1], 3), dtype=np.uint8)
    hsv[..., 1] = 255
    
    mag, ang = cv2.cartToPolar(u, v)
    hsv[..., 0] = ang * 180 / np.pi / 2
    hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
    
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return rgb


def flow_to_tensor_image(flow, max_flow=None):
    img = flow_to_image(flow, max_flow)
    img = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
    return img.unsqueeze(0)


def gaussian_blur(tensor, kernel_size=5, sigma=1.0):
    B, C, H, W = tensor.shape
    device = tensor.device
    
    x = torch.arange(kernel_size, device=device) - (kernel_size - 1) / 2
    gauss = torch.exp(-(x ** 2) / (2 * sigma ** 2))
    gauss = gauss / gauss.sum()
    
    kernel_x = gauss.view(1, 1, 1, kernel_size).expand(C, 1, 1, kernel_size)
    kernel_y = gauss.view(1, 1, kernel_size, 1).expand(C, 1, kernel_size, 1)
    
    padding = kernel_size // 2
    blurred = F.conv2d(tensor, kernel_x, padding=(0, padding), groups=C)
    blurred = F.conv2d(blurred, kernel_y, padding=(padding, 0), groups=C)
    
    return blurred
