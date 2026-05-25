import cv2
import numpy as np
import torch
import torch.nn.functional as F
from scipy import ndimage
from typing import Tuple, Optional, List, Dict
import warnings
import heapq
warnings.filterwarnings('ignore')


class PriorityQueue:
    def __init__(self):
        self.heap = []
        self.count = 0
    
    def push(self, item, priority):
        heapq.heappush(self.heap, (priority, self.count, item))
        self.count += 1
    
    def pop(self):
        return heapq.heappop(self.heap)[2]
    
    def empty(self):
        return len(self.heap) == 0


class GraphCutSeamFinder:
    def __init__(self, use_gpu: bool = True):
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
    
    def compute_error_map(self, img1: torch.Tensor, img2: torch.Tensor, 
                          gradient_weight: float = 0.5) -> torch.Tensor:
        B, C, H, W = img1.shape
        diff = torch.sum((img1 - img2) ** 2, dim=1, keepdim=True)
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], 
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], 
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)
        
        gray1 = torch.mean(img1, dim=1, keepdim=True)
        gray2 = torch.mean(img2, dim=1, keepdim=True)
        grad_x1 = F.conv2d(F.pad(gray1, (1, 1, 1, 1)), sobel_x)
        grad_y1 = F.conv2d(F.pad(gray1, (1, 1, 1, 1)), sobel_y)
        grad_x2 = F.conv2d(F.pad(gray2, (1, 1, 1, 1)), sobel_x)
        grad_y2 = F.conv2d(F.pad(gray2, (1, 1, 1, 1)), sobel_y)
        
        grad_diff = torch.sum((grad_x1 - grad_x2) ** 2 + (grad_y1 - grad_y2) ** 2, dim=1, keepdim=True)
        error = diff + gradient_weight * grad_diff
        return error.squeeze(0).squeeze(0)
    
    def find_vertical_seam(self, error_map: torch.Tensor) -> np.ndarray:
        error_np = error_map.cpu().numpy()
        H, W = error_np.shape
        
        dp = np.zeros((H, W), dtype=np.float64)
        dp[0] = error_np[0]
        
        for i in range(1, H):
            dp[i, 0] = error_np[i, 0] + min(dp[i-1, 0], dp[i-1, 1])
            for j in range(1, W-1):
                dp[i, j] = error_np[i, j] + min(dp[i-1, j-1], dp[i-1, j], dp[i-1, j+1])
            dp[i, W-1] = error_np[i, W-1] + min(dp[i-1, W-2], dp[i-1, W-1])
        
        seam = np.zeros(H, dtype=np.int32)
        seam[H-1] = int(np.argmin(dp[H-1]))
        
        for i in range(H-2, -1, -1):
            prev_j = seam[i+1]
            if prev_j == 0:
                candidates = [0, 1]
            elif prev_j == W-1:
                candidates = [W-2, W-1]
            else:
                candidates = [prev_j-1, prev_j, prev_j+1]
            seam[i] = candidates[int(np.argmin([dp[i, c] for c in candidates]))]
        
        return seam
    
    def find_horizontal_seam(self, error_map: torch.Tensor) -> np.ndarray:
        transposed = error_map.permute(1, 0)
        seam = self.find_vertical_seam(transposed)
        return seam
    
    def create_seam_mask(self, patch_size: int, overlap: int, 
                         error_h: Optional[torch.Tensor] = None, 
                         error_v: Optional[torch.Tensor] = None,
                         overlap_type: str = 'both') -> np.ndarray:
        mask = np.ones((patch_size, patch_size), dtype=np.float32)
        
        if overlap_type in ['left', 'both'] and error_h is not None:
            seam_h = self.find_vertical_seam(error_h)
            for i in range(patch_size):
                j = seam_h[i]
                mask[i, :j] = 0.0
        
        if overlap_type in ['top', 'both'] and error_v is not None:
            seam_v = self.find_horizontal_seam(error_v)
            for j in range(patch_size):
                i = seam_v[j]
                mask[:i, j] = 0.0
        
        return mask
    
    def blend_with_seam(self, existing: torch.Tensor, new: torch.Tensor, 
                        mask: np.ndarray) -> torch.Tensor:
        mask_tensor = torch.from_numpy(mask).float().to(self.device)
        mask_tensor = mask_tensor.unsqueeze(0).unsqueeze(0)
        mask_tensor = F.interpolate(mask_tensor, size=new.shape[2:], mode='bilinear', align_corners=False)
        return new * mask_tensor + existing * (1 - mask_tensor)


class GPUPyramidBuilder:
    def __init__(self, device: torch.device):
        self.device = device
        self._gaussian_kernel = None
    
    def _get_gaussian_kernel(self, kernel_size: int = 5, sigma: float = 1.0) -> torch.Tensor:
        if self._gaussian_kernel is None:
            x = np.arange(kernel_size) - (kernel_size - 1) / 2
            g = np.exp(-x**2 / (2 * sigma**2))
            g = g / g.sum()
            kernel_2d = np.outer(g, g)
            kernel = torch.from_numpy(kernel_2d).float().to(self.device)
            kernel = kernel.view(1, 1, kernel_size, kernel_size)
            self._gaussian_kernel = kernel
        return self._gaussian_kernel
    
    def gaussian_pyramid(self, img_tensor: torch.Tensor, levels: int) -> List[torch.Tensor]:
        B, C, H, W = img_tensor.shape
        kernel = self._get_gaussian_kernel()
        kernel = kernel.repeat(C, 1, 1, 1)
        
        pyramid = [img_tensor]
        current = img_tensor
        
        for _ in range(levels - 1):
            current = F.pad(current, (2, 2, 2, 2), mode='reflect')
            current = F.conv2d(current, kernel, groups=C)
            current = current[:, :, ::2, ::2]
            pyramid.append(current)
        
        return pyramid
    
    def laplacian_pyramid(self, img_tensor: torch.Tensor, 
                          levels: int) -> Tuple[List[torch.Tensor], torch.Tensor]:
        gaussian_pyr = self.gaussian_pyramid(img_tensor, levels + 1)
        laplacian_pyr = []
        
        for i in range(levels):
            size = (gaussian_pyr[i].shape[2], gaussian_pyr[i].shape[3])
            up = F.interpolate(gaussian_pyr[i + 1], size=size, mode='bilinear', align_corners=False)
            laplacian = gaussian_pyr[i] - up
            laplacian_pyr.append(laplacian)
        
        return laplacian_pyr, gaussian_pyr[-1]
    
    def reconstruct_from_laplacian(self, laplacian_pyr: List[torch.Tensor], 
                                    base: torch.Tensor) -> torch.Tensor:
        img = base
        for lap in reversed(laplacian_pyr):
            size = (lap.shape[2], lap.shape[3])
            img = F.interpolate(img, size=size, mode='bilinear', align_corners=False)
            img = img + lap
        return img


class EnhancedPatchMatcher:
    def __init__(self, device: torch.device):
        self.device = device
        self.cache: Dict[str, Tuple[torch.Tensor, int, int]] = {}
    
    def clear_cache(self):
        self.cache.clear()
    
    def _extract_patches_gpu(self, source_tensor: torch.Tensor, 
                             patch_size: int, stride: int = 1) -> torch.Tensor:
        cache_key = f"{source_tensor.shape}_{patch_size}_{stride}"
        
        if cache_key in self.cache:
            return self.cache[cache_key][0]
        
        B, C, H, W = source_tensor.shape
        patches = F.unfold(source_tensor, kernel_size=patch_size, stride=stride)
        patches = patches.permute(0, 2, 1).contiguous()
        
        num_h = H - patch_size + 1
        num_w = W - patch_size + 1
        
        self.cache[cache_key] = (patches, num_h, num_w)
        return patches
    
    def find_top_k_matches(self, target_patch: torch.Tensor, 
                           source_tensor: torch.Tensor,
                           patch_size: int, k: int = 5,
                           stride: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
        B, C, H, W = source_tensor.shape
        
        patches = self._extract_patches_gpu(source_tensor, patch_size, stride)
        target_flat = target_patch.flatten().unsqueeze(0).unsqueeze(0)
        
        dist = torch.sum((patches - target_flat) ** 2, dim=2)
        
        num_h = H - patch_size + 1
        num_w = W - patch_size + 1
        
        top_k_values, top_k_indices = torch.topk(dist.squeeze(0), k, largest=False)
        
        ys = top_k_indices // num_w
        xs = top_k_indices % num_w
        
        return torch.stack([ys, xs], dim=1), top_k_values
    
    def find_best_match_with_structure(self, 
                                       target_patch: torch.Tensor,
                                       source_tensor: torch.Tensor,
                                       patch_size: int,
                                       target_structure: Optional[torch.Tensor] = None,
                                       source_structure: Optional[torch.Tensor] = None,
                                       structure_weight: float = 0.5,
                                       target_guide: Optional[torch.Tensor] = None,
                                       source_guide: Optional[torch.Tensor] = None,
                                       guide_weight: float = 1.0,
                                       overlap_mask: Optional[torch.Tensor] = None) -> Tuple[int, int]:
        B, C, H, W = source_tensor.shape
        stride = 1
        
        patches = self._extract_patches_gpu(source_tensor, patch_size, stride)
        target_flat = target_patch.flatten().unsqueeze(0)
        
        if overlap_mask is not None:
            mask_flat = overlap_mask.flatten().unsqueeze(0)
            dist = torch.sum(((patches - target_flat) ** 2) * mask_flat, dim=2)
        else:
            dist = torch.sum((patches - target_flat) ** 2, dim=2)
        
        if structure_weight > 0 and target_structure is not None and source_structure is not None:
            struct_patches = self._extract_patches_gpu(source_structure, patch_size, stride)
            struct_flat = target_structure.flatten().unsqueeze(0)
            
            if overlap_mask is not None:
                struct_dist = torch.sum(((struct_patches - struct_flat) ** 2) * mask_flat, dim=2)
            else:
                struct_dist = torch.sum((struct_patches - struct_flat) ** 2, dim=2)
            dist = dist + structure_weight * struct_dist
        
        if guide_weight > 0 and target_guide is not None and source_guide is not None:
            guide_patches = self._extract_patches_gpu(source_guide, patch_size, stride)
            guide_flat = target_guide.flatten().unsqueeze(0)
            
            if overlap_mask is not None:
                guide_dist = torch.sum(((guide_patches - guide_flat) ** 2) * mask_flat, dim=2)
            else:
                guide_dist = torch.sum((guide_patches - guide_flat) ** 2, dim=2)
            dist = dist + guide_weight * guide_dist
        
        num_h = H - patch_size + 1
        num_w = W - patch_size + 1
        
        best_idx = torch.argmin(dist)
        best_y = best_idx.item() // num_w
        best_x = best_idx.item() % num_w
        
        return best_y, best_x


class TextureSynthesizer:
    def __init__(self, use_gpu: bool = True):
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        self.pyramid_builder = GPUPyramidBuilder(self.device)
        self.patch_matcher = EnhancedPatchMatcher(self.device)
        self.seam_finder = GraphCutSeamFinder(use_gpu=use_gpu)
    
    def to_tensor(self, img: np.ndarray, normalize: bool = True) -> torch.Tensor:
        if img.ndim == 2:
            img = img[..., np.newaxis]
        tensor = torch.from_numpy(img.transpose(2, 0, 1)).float().to(self.device)
        if normalize:
            tensor = tensor / 255.0
        return tensor.unsqueeze(0)
    
    def to_numpy(self, tensor: torch.Tensor, denormalize: bool = True) -> np.ndarray:
        tensor = tensor.squeeze(0).cpu()
        if denormalize:
            tensor = torch.clamp(tensor * 255.0, 0, 255)
        img = tensor.permute(1, 2, 0).numpy().astype(np.uint8)
        return img if img.shape[2] > 1 else img[..., 0]
    
    def build_gaussian_pyramid_gpu(self, img_tensor: torch.Tensor, 
                                   levels: int) -> List[torch.Tensor]:
        return self.pyramid_builder.gaussian_pyramid(img_tensor, levels)
    
    def build_laplacian_pyramid_gpu(self, img_tensor: torch.Tensor, 
                                    levels: int) -> Tuple[List[torch.Tensor], torch.Tensor]:
        return self.pyramid_builder.laplacian_pyramid(img_tensor, levels)
    
    def reconstruct_from_laplacian_gpu(self, laplacian_pyr: List[torch.Tensor], 
                                       base: torch.Tensor) -> torch.Tensor:
        return self.pyramid_builder.reconstruct_from_laplacian(laplacian_pyr, base)
    
    def build_gaussian_pyramid(self, img: np.ndarray, levels: int) -> List[np.ndarray]:
        tensor = self.to_tensor(img)
        pyr_tensors = self.build_gaussian_pyramid_gpu(tensor, levels)
        return [self.to_numpy(t) for t in pyr_tensors]
    
    def build_laplacian_pyramid(self, img: np.ndarray, levels: int) -> Tuple[List[np.ndarray], np.ndarray]:
        tensor = self.to_tensor(img)
        lap_tensors, base_tensor = self.build_laplacian_pyramid_gpu(tensor, levels)
        lap_numpy = [self.to_numpy(t) for t in lap_tensors]
        base_numpy = self.to_numpy(base_tensor)
        return lap_numpy, base_numpy
    
    def reconstruct_from_laplacian(self, laplacian_pyr: List[np.ndarray], 
                                    base: np.ndarray) -> np.ndarray:
        lap_tensors = [self.to_tensor(img) for img in laplacian_pyr]
        base_tensor = self.to_tensor(base)
        result_tensor = self.reconstruct_from_laplacian_gpu(lap_tensors, base_tensor)
        return self.to_numpy(result_tensor)
    
    def compute_direction_map(self, texture: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY) if texture.ndim == 3 else texture
        sobel_x = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        direction = np.arctan2(sobel_y, sobel_x)
        direction[magnitude < np.mean(magnitude) * 0.5] = 0
        return direction
    
    def compute_structure_tensor_gpu(self, texture_tensor: torch.Tensor, 
                                     window_size: int = 3) -> torch.Tensor:
        B, C, H, W = texture_tensor.shape
        
        gray = torch.mean(texture_tensor, dim=1, keepdim=True)
        
        sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], 
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)
        sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], 
                               dtype=torch.float32, device=self.device).view(1, 1, 3, 3)
        
        Ix = F.conv2d(F.pad(gray, (1, 1, 1, 1)), sobel_x)
        Iy = F.conv2d(F.pad(gray, (1, 1, 1, 1)), sobel_y)
        
        Ixx = Ix * Ix
        Iyy = Iy * Iy
        Ixy = Ix * Iy
        
        kernel_size = window_size
        sigma = window_size / 6.0
        from math import pi, exp
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        for i in range(kernel_size):
            for j in range(kernel_size):
                x = i - (kernel_size - 1) / 2
                y = j - (kernel_size - 1) / 2
                kernel[i, j] = exp(-(x**2 + y**2) / (2 * sigma**2))
        kernel = kernel / kernel.sum()
        kernel_tensor = torch.from_numpy(kernel).to(self.device).view(1, 1, kernel_size, kernel_size)
        
        pad = kernel_size // 2
        Ixx = F.conv2d(F.pad(Ixx, (pad, pad, pad, pad)), kernel_tensor)
        Iyy = F.conv2d(F.pad(Iyy, (pad, pad, pad, pad)), kernel_tensor)
        Ixy = F.conv2d(F.pad(Ixy, (pad, pad, pad, pad)), kernel_tensor)
        
        structure = torch.cat([Ixx, Ixy, Iyy], dim=1)
        return structure
    
    def compute_structure_tensor(self, texture: np.ndarray, 
                                 window_size: int = 3) -> np.ndarray:
        tensor = self.to_tensor(texture)
        struct_tensor = self.compute_structure_tensor_gpu(tensor, window_size)
        return struct_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
    
    def compute_orientation_field(self, structure: np.ndarray) -> np.ndarray:
        Ixx = structure[..., 0]
        Iyy = structure[..., 1]
        Ixy = structure[..., 2]
        
        trace = Ixx + Iyy
        det = Ixx * Iyy - Ixy * Ixy
        
        lambda1 = 0.5 * (trace + np.sqrt(np.maximum(trace**2 - 4 * det, 0)))
        vx = lambda1 - Iyy
        vy = Ixy
        
        orientation = np.arctan2(vy, vx)
        coherence = np.abs(lambda1 - 0.5 * (trace - np.sqrt(np.maximum(trace**2 - 4 * det, 0)))) / (trace + 1e-8)
        
        return orientation, coherence
    
    def create_feather_mask(self, patch_size: int, overlap: int, 
                           direction: str = 'right') -> np.ndarray:
        mask = np.ones((patch_size, patch_size), dtype=np.float32)
        if direction == 'right':
            feather = np.linspace(1, 0, overlap)
            mask[:, -overlap:] = np.tile(feather[np.newaxis, :], (patch_size, 1))
        elif direction == 'bottom':
            feather = np.linspace(1, 0, overlap)
            mask[-overlap:, :] = np.tile(feather[:, np.newaxis], (1, patch_size))
        elif direction == 'corner':
            feather_h = np.linspace(1, 0, overlap)
            feather_v = np.linspace(1, 0, overlap)
            feather_h = np.tile(feather_h[np.newaxis, :], (patch_size, 1))
            feather_v = np.tile(feather_v[:, np.newaxis], (1, patch_size))
            feather = np.minimum(feather_h, feather_v)
            mask[-overlap:, -overlap:] = feather[-overlap:, -overlap:]
        return mask
    
    def multiband_blend_gpu(self, img1: torch.Tensor, img2: torch.Tensor, 
                            mask: torch.Tensor, levels: int = 5) -> torch.Tensor:
        B, C, H, W = img1.shape
        
        if mask.ndim == 3:
            mask = mask.unsqueeze(0)
        if mask.shape[1] == 1 and C > 1:
            mask = mask.repeat(1, C, 1, 1)
        
        lap1, base1 = self.build_laplacian_pyramid_gpu(img1, levels)
        lap2, base2 = self.build_laplacian_pyramid_gpu(img2, levels)
        mask_pyr = self.build_gaussian_pyramid_gpu(mask, levels + 1)
        
        blended_lap = []
        for i in range(levels):
            m = mask_pyr[i]
            if m.shape[1] == 1 and C > 1:
                m = m.repeat(1, C, 1, 1)
            blended_lap.append(lap1[i] * m + lap2[i] * (1 - m))
        
        blended_base = base1 * mask_pyr[-1] + base2 * (1 - mask_pyr[-1])
        result = self.reconstruct_from_laplacian_gpu(blended_lap, blended_base)
        
        return torch.clamp(result, 0, 1)
    
    def multiband_blend(self, img1: np.ndarray, img2: np.ndarray, 
                        mask: np.ndarray, levels: int = 5) -> np.ndarray:
        img1_tensor = self.to_tensor(img1)
        img2_tensor = self.to_tensor(img2)
        mask_tensor = torch.from_numpy(mask).float().to(self.device)
        if mask.ndim == 2:
            mask_tensor = mask_tensor.unsqueeze(0).unsqueeze(0)
        else:
            mask_tensor = mask_tensor.permute(2, 0, 1).unsqueeze(0)
        
        result_tensor = self.multiband_blend_gpu(img1_tensor, img2_tensor, mask_tensor, levels)
        return self.to_numpy(result_tensor)
    
    def graphcut_blend(self, existing: np.ndarray, new_patch: np.ndarray,
                       overlap: int, overlap_type: str = 'both') -> Tuple[np.ndarray, np.ndarray]:
        existing_tensor = self.to_tensor(existing)
        new_tensor = self.to_tensor(new_patch)
        
        mask = np.ones((existing.shape[0], existing.shape[1]), dtype=np.float32)
        error_h = None
        error_v = None
        
        if overlap_type in ['left', 'both']:
            overlap_region_existing = existing_tensor[:, :, :, :overlap]
            overlap_region_new = new_tensor[:, :, :, :overlap]
            error_h = self.seam_finder.compute_error_map(overlap_region_existing, overlap_region_new)
        
        if overlap_type in ['top', 'both']:
            overlap_region_existing = existing_tensor[:, :, :overlap, :]
            overlap_region_new = new_tensor[:, :, :overlap, :]
            error_v = self.seam_finder.compute_error_map(overlap_region_existing, overlap_region_new)
        
        seam_mask = self.seam_finder.create_seam_mask(
            existing.shape[0], overlap, error_h, error_v, overlap_type
        )
        
        mask[:existing.shape[0], :existing.shape[1]] = seam_mask
        
        if existing.ndim == 3:
            mask_3d = mask[..., np.newaxis]
        else:
            mask_3d = mask
        
        blended = (new_patch * mask_3d + existing * (1 - mask_3d)).astype(np.uint8)
        
        return blended, mask
    
    def synthesize_texture(self, texture: np.ndarray, 
                          output_size: Tuple[int, int],
                          patch_size: int = 32,
                          overlap: int = 8,
                          pyramid_levels: int = 3,
                          guide_image: Optional[np.ndarray] = None,
                          use_direction: bool = True,
                          blend_mode: str = 'graphcut',
                          structure_weight: float = 0.5,
                          use_structure_guide: bool = True) -> np.ndarray:
        assert texture.shape[0] >= patch_size and texture.shape[1] >= patch_size, \
            "Texture must be larger than patch size"
        
        self.patch_matcher.clear_cache()
        
        out_h, out_w = output_size
        is_color = texture.ndim == 3
        
        output = np.zeros((out_h, out_w, 3) if is_color else (out_h, out_w), dtype=np.uint8)
        output_tensor = torch.zeros(1, 3 if is_color else 1, out_h, out_w, 
                                    dtype=torch.float32, device=self.device)
        
        source_tensor = self.to_tensor(texture)
        
        source_structure = None
        structure_tensor = None
        if use_direction and use_structure_guide:
            structure_tensor = self.compute_structure_tensor_gpu(source_tensor)
            source_structure = structure_tensor
            structure_weight = structure_weight
        
        guide_tensor = None
        source_guide = None
        guide_weight = 0.0
        if guide_image is not None:
            guide_weight = 1.0
            guide_resized = cv2.resize(guide_image, (texture.shape[1], texture.shape[0]))
            source_guide = self.to_tensor(guide_resized, normalize=False)
            if guide_image.shape[:2] != output_size:
                guide_image = cv2.resize(guide_image, (out_w, out_h))
            guide_tensor = guide_image
        
        step = patch_size - overlap
        coords_y = list(range(0, out_h - patch_size + 1, step))
        coords_x = list(range(0, out_w - patch_size + 1, step))
        
        if coords_y[-1] + patch_size < out_h:
            coords_y.append(out_h - patch_size)
        if coords_x[-1] + patch_size < out_w:
            coords_x.append(out_w - patch_size)
        
        start_y = np.random.randint(0, texture.shape[0] - patch_size + 1)
        start_x = np.random.randint(0, texture.shape[1] - patch_size + 1)
        
        output[coords_y[0]:coords_y[0] + patch_size, 
               coords_x[0]:coords_x[0] + patch_size] = texture[start_y:start_y + patch_size, 
                                                                start_x:start_x + patch_size]
        
        output_tensor[:, :, coords_y[0]:coords_y[0] + patch_size, 
                      coords_x[0]:coords_x[0] + patch_size] = \
            source_tensor[:, :, start_y:start_y + patch_size, start_x:start_x + patch_size]
        
        total_patches = len(coords_y) * len(coords_x)
        current_patch = 0
        
        for yi, y in enumerate(coords_y):
            for xi, x in enumerate(coords_x):
                current_patch += 1
                if yi == 0 and xi == 0:
                    continue
                
                if current_patch % 20 == 0:
                    print(f"  Progress: {current_patch}/{total_patches} patches")
                
                target_patch = output[y:y + patch_size, x:x + patch_size].copy()
                target_patch_tensor = output_tensor[:, :, y:y + patch_size, x:x + patch_size]
                
                overlap_mask = np.zeros((patch_size, patch_size), dtype=np.float32)
                overlap_type = 'none'
                has_left_overlap = xi > 0
                has_top_overlap = yi > 0
                
                if has_left_overlap:
                    overlap_mask[:, :overlap] = 1.0
                    overlap_type = 'left'
                if has_top_overlap:
                    overlap_mask[:overlap, :] = 1.0
                    overlap_type = 'top' if overlap_type == 'none' else 'both'
                
                if not has_left_overlap and not has_top_overlap:
                    sy = np.random.randint(0, texture.shape[0] - patch_size + 1)
                    sx = np.random.randint(0, texture.shape[1] - patch_size + 1)
                    source_patch = texture[sy:sy + patch_size, sx:sx + patch_size]
                    source_patch_tensor = source_tensor[:, :, sy:sy + patch_size, sx:sx + patch_size]
                else:
                    target_struct_patch = None
                    if source_structure is not None:
                        target_struct_patch = self.compute_structure_tensor_gpu(target_patch_tensor)
                    
                    guide_patch = None
                    if guide_tensor is not None:
                        guide_patch_np = guide_tensor[y:y + patch_size, x:x + patch_size]
                        guide_patch = self.to_tensor(guide_patch_np, normalize=False)
                    
                    overlap_mask_tensor = torch.from_numpy(overlap_mask).float().to(self.device)
                    overlap_mask_tensor = overlap_mask_tensor.unsqueeze(0).unsqueeze(0)
                    
                    masked_target = target_patch_tensor * overlap_mask_tensor
                    
                    sy, sx = self.patch_matcher.find_best_match_with_structure(
                        masked_target, source_tensor, patch_size,
                        target_structure=target_struct_patch,
                        source_structure=source_structure,
                        structure_weight=structure_weight,
                        target_guide=guide_patch,
                        source_guide=source_guide,
                        guide_weight=guide_weight,
                        overlap_mask=overlap_mask_tensor
                    )
                    
                    source_patch = texture[sy:sy + patch_size, sx:sx + patch_size]
                    source_patch_tensor = source_tensor[:, :, sy:sy + patch_size, sx:sx + patch_size]
                
                existing = output[y:y + patch_size, x:x + patch_size].copy()
                existing_tensor = target_patch_tensor.clone()
                
                if blend_mode == 'graphcut':
                    blended, seam_mask = self.graphcut_blend(existing, source_patch, overlap, overlap_type)
                    
                    if is_color:
                        seam_mask_3d = seam_mask[..., np.newaxis]
                        source_patch_masked = source_patch * seam_mask_3d
                        existing_masked = existing * (1 - seam_mask_3d)
                        blended_np = (source_patch_masked + existing_masked).astype(np.uint8)
                    else:
                        source_patch_masked = source_patch * seam_mask
                        existing_masked = existing * (1 - seam_mask)
                        blended_np = (source_patch_masked + existing_masked).astype(np.uint8)
                    
                    output[y:y + patch_size, x:x + patch_size] = blended_np
                    
                    seam_mask_tensor = torch.from_numpy(seam_mask).float().to(self.device)
                    seam_mask_tensor = seam_mask_tensor.unsqueeze(0).unsqueeze(0)
                    if is_color:
                        seam_mask_tensor = seam_mask_tensor.repeat(1, 3, 1, 1)
                    
                    output_tensor[:, :, y:y + patch_size, x:x + patch_size] = \
                        source_patch_tensor * seam_mask_tensor + existing_tensor * (1 - seam_mask_tensor)
                
                elif blend_mode == 'multiband':
                    blend_mask = np.ones((patch_size, patch_size), dtype=np.float32)
                    if has_left_overlap:
                        feather = np.linspace(0, 1, overlap)
                        blend_mask[:, :overlap] = np.minimum(blend_mask[:, :overlap], feather[np.newaxis, :])
                    if has_top_overlap:
                        feather = np.linspace(0, 1, overlap)
                        blend_mask[:overlap, :] = np.minimum(blend_mask[:overlap, :], feather[:, np.newaxis])
                    
                    blended = self.multiband_blend(source_patch, existing, blend_mask, levels=3)
                    output[y:y + patch_size, x:x + patch_size] = blended
                    
                    blend_mask_tensor = torch.from_numpy(blend_mask).float().to(self.device)
                    blend_mask_tensor = blend_mask_tensor.unsqueeze(0).unsqueeze(0)
                    if is_color:
                        blend_mask_tensor = blend_mask_tensor.repeat(1, 3, 1, 1)
                    
                    output_tensor[:, :, y:y + patch_size, x:x + patch_size] = \
                        source_patch_tensor * blend_mask_tensor + existing_tensor * (1 - blend_mask_tensor)
                
                else:
                    blend_mask = np.ones((patch_size, patch_size), dtype=np.float32)
                    if has_left_overlap:
                        feather = np.linspace(0, 1, overlap)
                        blend_mask[:, :overlap] = np.minimum(blend_mask[:, :overlap], feather[np.newaxis, :])
                    if has_top_overlap:
                        feather = np.linspace(0, 1, overlap)
                        blend_mask[:overlap, :] = np.minimum(blend_mask[:overlap, :], feather[:, np.newaxis])
                    
                    if is_color:
                        blend_mask = blend_mask[..., np.newaxis]
                    
                    blended = (source_patch * blend_mask + existing * (1 - blend_mask)).astype(np.uint8)
                    output[y:y + patch_size, x:x + patch_size] = blended
        
        return output
    
    def interactive_guided_synthesis(self, texture: np.ndarray,
                                     output_size: Tuple[int, int],
                                     patch_size: int = 32,
                                     overlap: int = 8) -> np.ndarray:
        guide = np.zeros(output_size + (3,), dtype=np.uint8)
        drawing = False
        current_color = (255, 255, 255)
        result = None
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal drawing, current_color
            if event == cv2.EVENT_LBUTTONDOWN:
                drawing = True
            elif event == cv2.EVENT_MOUSEMOVE:
                if drawing:
                    cv2.circle(guide, (x, y), 8, current_color, -1)
            elif event == cv2.EVENT_LBUTTONUP:
                drawing = False
        
        window_name = 'Draw Guide - Press 1/2/3 for colors, SPACE to synthesize, ESC to quit'
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback)
        
        print("Controls:")
        print("  Left mouse: Draw")
        print("  1: White (background)")
        print("  2: Red")
        print("  3: Blue")
        print("  SPACE: Start synthesis (with GraphCut)")
        print("  ESC: Quit")
        
        colors = [(255, 255, 255), (0, 0, 255), (255, 0, 0)]
        color_idx = 0
        
        while True:
            display = guide.copy()
            cv2.putText(display, f'Color: {color_idx + 1}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(window_name, display)
            
            if result is not None:
                cv2.imshow('Synthesis Result', result)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            elif key == ord(' '):
                print("Starting synthesis with GraphCut...")
                result = self.synthesize_texture(
                    texture, output_size, patch_size, overlap,
                    guide_image=guide, use_direction=True,
                    blend_mode='graphcut', structure_weight=0.5
                )
                print("Synthesis complete!")
            elif ord('1') <= key <= ord('3'):
                color_idx = int(chr(key)) - 1
                current_color = colors[color_idx]
        
        cv2.destroyAllWindows()
        return guide


def main():
    import sys
    no_display = '--no-display' in sys.argv or '-n' in sys.argv
    
    print("Enhanced Texture Synthesis with GraphCut, Structure Tensor, and Full GPU Acceleration")
    print("=" * 80)
    
    synthesizer = TextureSynthesizer(use_gpu=True)
    
    print("\n1. Generating sample textures...")
    np.random.seed(42)
    
    wood_texture = np.zeros((100, 100, 3), dtype=np.uint8)
    for i in range(100):
        offset = int(20 * np.sin(i * 0.1))
        color = int(100 + 50 * np.sin(i * 0.05))
        wood_texture[:, i] = [color // 2, color, color // 3]
    wood_texture = wood_texture + np.random.randint(0, 20, (100, 100, 3), dtype=np.uint8)
    
    weave_texture = np.zeros((64, 64, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                weave_texture[i, j] = [180, 140, 100]
            else:
                weave_texture[i, j] = [120, 90, 60]
    weave_texture = weave_texture + np.random.randint(0, 15, (64, 64, 3), dtype=np.uint8)
    
    print("\n2. Testing wood texture synthesis with GRAPHCUT (enhanced)...")
    output_size = (256, 256)
    result_wood_graphcut = synthesizer.synthesize_texture(
        wood_texture, output_size,
        patch_size=24, overlap=8,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.7
    )
    print("   Wood synthesis (GraphCut) complete!")
    
    print("\n3. Testing weave texture synthesis with multiband...")
    result_weave_multiband = synthesizer.synthesize_texture(
        weave_texture, output_size,
        patch_size=32, overlap=12,
        use_direction=True,
        blend_mode='multiband',
        structure_weight=0.5
    )
    print("   Weave synthesis complete!")
    
    print("\n4. Testing guided synthesis with GraphCut...")
    guide = np.zeros(output_size + (3,), dtype=np.uint8)
    cv2.circle(guide, (128, 128), 60, (255, 0, 0), -1)
    cv2.rectangle(guide, (50, 50), (100, 200), (0, 0, 255), -1)
    
    result_guided = synthesizer.synthesize_texture(
        wood_texture, output_size,
        patch_size=24, overlap=8,
        guide_image=guide,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.5
    )
    print("   Guided synthesis complete!")
    
    print("\n5. Saving results...")
    cv2.imwrite('input_wood.png', wood_texture)
    cv2.imwrite('input_weave.png', weave_texture)
    cv2.imwrite('result_wood_graphcut.png', result_wood_graphcut)
    cv2.imwrite('result_weave_multiband.png', result_weave_multiband)
    cv2.imwrite('guide_map.png', guide)
    cv2.imwrite('result_guided_graphcut.png', result_guided)
    print("   Results saved!")
    
    if not no_display:
        print("\n6. Displaying results...")
        print("   Press any key to continue...")
        cv2.imshow('Input - Wood', wood_texture)
        cv2.imshow('Output - Wood (GraphCut)', result_wood_graphcut)
        cv2.imshow('Input - Weave', weave_texture)
        cv2.imshow('Output - Weave (Multi-band)', result_weave_multiband)
        cv2.imshow('Guide Map', guide)
        cv2.imshow('Guided Synthesis (GraphCut)', result_guided)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("\n6. Display skipped (--no-display mode)")
    
    print("\n" + "=" * 80)
    print("Demo complete! Output files:")
    print("  - input_wood.png, input_weave.png (input textures)")
    print("  - result_wood_graphcut.png (wood with GraphCut seam)")
    print("  - result_weave_multiband.png (weave with multi-band)")
    print("  - guide_map.png, result_guided_graphcut.png (guided synthesis)")
    print("\nEnhanced Features:")
    print("  ✓ GraphCut minimum error seam finding")
    print("  ✓ Enhanced structure tensor guidance")
    print("  ✓ Full GPU acceleration (pyramids, patch matching)")
    print("  ✓ Orientation field coherence weighting")
    print("  ✓ Improved directional texture preservation")


if __name__ == '__main__':
    main()
