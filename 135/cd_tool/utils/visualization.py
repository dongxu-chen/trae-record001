import torch
import torch.nn as nn
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict


class AttentionVisualizer:
    def __init__(self, model: nn.Module, device: Optional[torch.device] = None):
        self.model = model
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.model.eval()
        self.attention_maps = defaultdict(list)
        self.hooks = []
        
    def _get_attention_hook(self, name: str):
        def hook(module, input, output):
            if isinstance(output, tuple):
                output = output[0]
            if len(output.shape) == 4:
                att_map = output.mean(dim=1, keepdim=True)
            elif len(output.shape) == 3:
                att_map = output.mean(dim=-1, keepdim=True)
                att_map = att_map.unsqueeze(1)
            else:
                return
            self.attention_maps[name].append(att_map.detach().cpu())
        return hook
    
    def register_attention_hooks(self, target_layers: Optional[List[str]] = None):
        self._remove_hooks()
        self.attention_maps.clear()
        
        for name, module in self.model.named_modules():
            if target_layers is None or any(target in name for target in target_layers):
                if 'attention' in name.lower() or 'attn' in name.lower() or 'boundary' in name.lower():
                    hook = module.register_forward_hook(self._get_attention_hook(name))
                    self.hooks.append(hook)
    
    def _remove_hooks(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks.clear()
    
    @torch.no_grad()
    def get_attention_maps(self, 
                          image1: torch.Tensor, 
                          image2: torch.Tensor,
                          target_layers: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
        self.register_attention_hooks(target_layers)
        x = torch.cat([image1, image2], dim=1).to(self.device)
        _ = self.model(x)
        self._remove_hooks()
        
        result = {}
        for name, maps in self.attention_maps.items():
            if maps:
                stacked = torch.cat(maps, dim=0)
                result[name] = stacked.squeeze().numpy()
        return result
    
    def visualize_heatmap(self, 
                         attention_map: np.ndarray,
                         original_image: Optional[np.ndarray] = None,
                         colormap: int = cv2.COLORMAP_JET,
                         alpha: float = 0.6) -> np.ndarray:
        if len(attention_map.shape) == 3:
            attention_map = attention_map.mean(axis=0)
        
        att_norm = (attention_map - attention_map.min()) / (attention_map.max() - attention_map.min() + 1e-8)
        att_heatmap = (att_norm * 255).astype(np.uint8)
        att_heatmap = cv2.applyColorMap(att_heatmap, colormap)
        
        if original_image is not None:
            if len(original_image.shape) == 2:
                original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2BGR)
            elif original_image.shape[2] == 4:
                original_image = cv2.cvtColor(original_image, cv2.COLOR_BGRA2BGR)
            
            if original_image.dtype != np.uint8:
                original_image = (original_image * 255).astype(np.uint8)
            
            if original_image.shape[:2] != att_heatmap.shape[:2]:
                original_image = cv2.resize(original_image, (att_heatmap.shape[1], att_heatmap.shape[0]))
            
            blended = cv2.addWeighted(original_image, 1 - alpha, att_heatmap, alpha, 0)
            return blended
        
        return att_heatmap
    
    def visualize_all_layers(self,
                           image1: torch.Tensor,
                           image2: torch.Tensor,
                           original_image: Optional[np.ndarray] = None,
                           nrow: int = 3) -> np.ndarray:
        att_maps = self.get_attention_maps(image1, image2)
        
        visualizations = []
        for name, att_map in att_maps.items():
            if len(att_map.shape) > 2:
                att_map = att_map[0]
            vis = self.visualize_heatmap(att_map, original_image)
            visualizations.append((name, vis))
        
        if not visualizations:
            return np.zeros((100, 100, 3), dtype=np.uint8)
        
        h, w = visualizations[0][1].shape[:2]
        ncol = (len(visualizations) + nrow - 1) // nrow
        
        grid = np.zeros((h * nrow, w * ncol, 3), dtype=np.uint8)
        
        for idx, (name, vis) in enumerate(visualizations):
            i = idx // ncol
            j = idx % ncol
            grid[i*h:(i+1)*h, j*w:(j+1)*w] = vis
            cv2.putText(grid, name.split('.')[-1][:15], 
                       (j*w + 5, i*h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        
        return grid
    
    def get_grad_cam(self,
                    image1: torch.Tensor,
                    image2: torch.Tensor,
                    target_layer: str,
                    class_idx: Optional[int] = None) -> np.ndarray:
        self.model.zero_grad()
        
        x = torch.cat([image1, image2], dim=1).to(self.device)
        x.requires_grad_(True)
        
        target_module = None
        for name, module in self.model.named_modules():
            if name == target_layer:
                target_module = module
                break
        
        if target_module is None:
            raise ValueError(f"Layer {target_layer} not found")
        
        activations = []
        gradients = []
        
        def forward_hook(module, input, output):
            activations.append(output.detach())
        
        def backward_hook(module, grad_in, grad_out):
            gradients.append(grad_out[0].detach())
        
        f_hook = target_module.register_forward_hook(forward_hook)
        b_hook = target_module.register_backward_hook(backward_hook)
        
        output = self.model(x)
        
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()
        
        target = output[:, class_idx, :, :].mean()
        target.backward()
        
        f_hook.remove()
        b_hook.remove()
        
        act = activations[0]
        grad = gradients[0]
        
        weights = grad.mean(dim=(2, 3), keepdim=True)
        cam = (weights * act).sum(dim=1).squeeze().cpu().numpy()
        
        cam = np.maximum(cam, 0)
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        
        return cam
    
    def save_visualization(self, vis: np.ndarray, path: str):
        cv2.imwrite(path, vis)
