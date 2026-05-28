import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple


def generate_anisotropic_kernel_grid(flow: torch.Tensor, kernel_size: int = 11, 
                                      strength: float = 1.0) -> torch.Tensor:
    B, _, H, W = flow.shape
    device = flow.device
    
    flow_mag = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
    flow_dir = flow / (flow_mag + 1e-6)
    
    center = kernel_size // 2
    y, x = torch.meshgrid(torch.arange(kernel_size, device=device) - center,
                         torch.arange(kernel_size, device=device) - center,
                         indexing='ij')
    
    y = y.view(1, 1, kernel_size, kernel_size).expand(B, H * W, kernel_size, kernel_size)
    x = x.view(1, 1, kernel_size, kernel_size).expand(B, H * W, kernel_size, kernel_size)
    
    flow_dir_x = flow_dir[:, 0].view(B, H * W, 1, 1)
    flow_dir_y = flow_dir[:, 1].view(B, H * W, 1, 1)
    
    proj = x * flow_dir_x + y * flow_dir_y
    perp_dist = torch.abs(x * flow_dir_y - y * flow_dir_x)
    
    length = flow_mag.view(B, H * W, 1, 1) * strength
    length = torch.clamp(length, min=1.0, max=kernel_size / 2)
    
    sigma_perp = 1.0
    sigma_parallel = torch.clamp(length * 0.5, min=1.0)
    
    gauss_parallel = torch.exp(-(proj ** 2) / (2 * sigma_parallel ** 2))
    gauss_perp = torch.exp(-(perp_dist ** 2) / (2 * sigma_perp ** 2))
    
    length_mask = (torch.abs(proj) <= length).float()
    
    kernel = gauss_parallel * gauss_perp * length_mask
    
    kernel_sum = kernel.sum(dim=(-1, -2), keepdim=True) + 1e-6
    kernel = kernel / kernel_sum
    
    return kernel


def apply_anisotropic_motion_blur(image: torch.Tensor, flow: torch.Tensor,
                                   kernel_size: int = 11, strength: float = 1.0,
                                   threshold: float = 5.0) -> torch.Tensor:
    B, C, H, W = image.shape
    device = image.device
    
    flow_mag = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
    motion_mask = (flow_mag > threshold).float()
    
    if motion_mask.sum() == 0:
        return image
    
    kernel_grid = generate_anisotropic_kernel_grid(flow, kernel_size, strength)
    
    pad = kernel_size // 2
    image_padded = F.pad(image, (pad, pad, pad, pad), mode='reflect')
    
    patches = F.unfold(image_padded, kernel_size=kernel_size, padding=0, stride=1)
    patches = patches.view(B, C, kernel_size * kernel_size, H, W)
    patches = patches.permute(0, 1, 3, 4, 2).contiguous()
    patches = patches.view(B, C * H * W, kernel_size * kernel_size)
    
    kernel_flat = kernel_grid.view(B, H * W, kernel_size * kernel_size)
    
    result = torch.zeros(B, C, H, W, device=device)
    
    for c in range(C):
        c_patches = patches[:, c * H * W:(c + 1) * H * W, :]
        c_blurred = torch.bmm(c_patches, kernel_flat.transpose(1, 2))
        c_blurred = c_blurred.diagonal(dim1=1, dim2=2).view(B, H, W)
        result[:, c, :, :] = c_blurred
    
    result = image * (1 - motion_mask) + result * motion_mask
    
    return result


def generate_motion_blur_kernel(flow: torch.Tensor, kernel_size: int = 11, strength: float = 1.0) -> torch.Tensor:
    return generate_anisotropic_kernel_grid(flow, kernel_size, strength)


def apply_motion_blur(image: torch.Tensor, flow: torch.Tensor, 
                     kernel_size: int = 11, strength: float = 1.0,
                     threshold: float = 5.0) -> torch.Tensor:
    return apply_anisotropic_motion_blur(image, flow, kernel_size, strength, threshold)


def apply_motion_blur_simple(image: torch.Tensor, flow: torch.Tensor,
                            kernel_size: int = 11, strength: float = 1.0,
                            threshold: float = 5.0) -> torch.Tensor:
    return apply_anisotropic_motion_blur(image, flow, kernel_size, strength, threshold)


def apply_motion_blur_optimized(image: torch.Tensor, flow: torch.Tensor,
                                kernel_size: int = 11, strength: float = 1.0,
                                threshold: float = 5.0, tile_size: int = 64) -> torch.Tensor:
    B, C, H, W = image.shape
    device = image.device
    
    flow_mag = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
    if flow_mag.mean() < threshold:
        return image
    
    result = torch.zeros_like(image)
    
    for y in range(0, H, tile_size):
        for x in range(0, W, tile_size):
            y_end = min(y + tile_size, H)
            x_end = min(x + tile_size, W)
            
            tile_image = image[:, :, y:y_end, x:x_end]
            tile_flow = flow[:, :, y:y_end, x:x_end]
            
            tile_blurred = apply_anisotropic_motion_blur(
                tile_image, tile_flow, kernel_size, strength, threshold
            )
            
            result[:, :, y:y_end, x:x_end] = tile_blurred
    
    return result


def apply_motion_blur_pyramid(image: torch.Tensor, flow: torch.Tensor,
                              kernel_size: int = 11, strength: float = 1.0,
                              threshold: float = 5.0) -> torch.Tensor:
    B, C, H, W = image.shape
    device = image.device
    
    flow_mag = torch.sqrt(flow[:, 0:1] ** 2 + flow[:, 1:2] ** 2)
    motion_mask = (flow_mag > threshold).float()
    
    blurred = image.clone()
    
    num_levels = 3
    for level in range(num_levels):
        scale = 1.0 / (2 ** level)
        if min(H, W) * scale < kernel_size:
            continue
        
        scaled_H = max(1, int(H * scale))
        scaled_W = max(1, int(W * scale))
        
        scaled_image = F.interpolate(image, size=(scaled_H, scaled_W), mode='bilinear', align_corners=False)
        scaled_flow = F.interpolate(flow, size=(scaled_H, scaled_W), mode='bilinear', align_corners=False)
        scaled_flow[:, 0] *= scale
        scaled_flow[:, 1] *= scale
        
        scaled_blurred = apply_anisotropic_motion_blur(
            scaled_image, scaled_flow, kernel_size, strength, threshold
        )
        
        upscaled = F.interpolate(scaled_blurred, size=(H, W), mode='bilinear', align_corners=False)
        
        level_mask = (motion_mask > (level + 1) / num_levels).float()
        blurred = blurred * (1 - level_mask) + upscaled * level_mask
    
    result = image * (1 - motion_mask) + blurred * motion_mask
    
    return result
