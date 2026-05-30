import cv2
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
import os

from config import Config


@dataclass
class HeatmapResult:
    original_image: np.ndarray
    heatmap: np.ndarray
    overlay: np.ndarray
    attention_regions: List[Dict[str, Any]] = field(default_factory=list)
    method: str = 'saliency'
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureMapResult:
    layer_name: str
    feature_maps: np.ndarray
    mean_activation: np.ndarray
    max_activation: np.ndarray
    visualizations: List[np.ndarray] = field(default_factory=list)


@dataclass
class ExplainerResult:
    heatmap_result: HeatmapResult
    feature_maps: List[FeatureMapResult] = field(default_factory=list)
    gradcam_maps: List[FeatureMapResult] = field(default_factory=list)
    attention_stats: Dict[str, Any] = field(default_factory=dict)


class AttentionHeatmap:
    def __init__(self, colormap: int = cv2.COLORMAP_JET, alpha: float = 0.5):
        self.colormap = colormap
        self.alpha = alpha
    
    def generate(self, saliency_map: np.ndarray, original_image: np.ndarray,
                 threshold: float = 0.3, min_region_size: int = 100) -> HeatmapResult:
        if saliency_map.shape[:2] != original_image.shape[:2]:
            saliency_map = cv2.resize(saliency_map, (original_image.shape[1], original_image.shape[0]))
        
        if saliency_map.max() > 1.0:
            saliency_normalized = saliency_map.astype(np.float32) / 255.0
        else:
            saliency_normalized = saliency_map.astype(np.float32)
        
        saliency_uint8 = (saliency_normalized * 255).astype(np.uint8)
        heatmap_colored = cv2.applyColorMap(saliency_uint8, self.colormap)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
        
        if original_image.ndim == 2:
            original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
        elif original_image.shape[2] == 4:
            original_image = cv2.cvtColor(original_image, cv2.COLOR_BGRA2RGB)
        
        if original_image.dtype != np.uint8:
            original_image = (original_image * 255).astype(np.uint8)
        
        overlay = cv2.addWeighted(original_image, 1 - self.alpha, heatmap_colored, self.alpha, 0)
        
        attention_regions = self._extract_attention_regions(
            saliency_normalized, threshold, min_region_size
        )
        
        return HeatmapResult(
            original_image=original_image,
            heatmap=heatmap_colored,
            overlay=overlay,
            attention_regions=attention_regions,
            method='saliency_based',
            parameters={'threshold': threshold, 'alpha': self.alpha, 'colormap': self.colormap}
        )
    
    def _extract_attention_regions(self, saliency_map: np.ndarray, threshold: float,
                                   min_region_size: int) -> List[Dict[str, Any]]:
        binary_mask = (saliency_map > threshold).astype(np.uint8)
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
        
        regions = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_region_size:
                continue
            
            x, y = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
            w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            cx, cy = centroids[i]
            
            region_mask = (labels == i).astype(np.float32)
            region_saliency = saliency_map * region_mask
            mean_attention = region_saliency.sum() / region_mask.sum() if region_mask.sum() > 0 else 0
            max_attention = region_saliency.max()
            
            regions.append({
                'id': i,
                'bbox': (x, y, w, h),
                'center': (cx, cy),
                'area': area,
                'mean_attention': mean_attention,
                'max_attention': max_attention,
                'mask': region_mask
            })
        
        regions.sort(key=lambda r: r['mean_attention'], reverse=True)
        return regions
    
    def generate_multi_scale(self, saliency_map: np.ndarray, original_image: np.ndarray,
                            scales: List[float] = [0.5, 1.0, 1.5],
                            threshold: float = 0.3) -> HeatmapResult:
        h, w = original_image.shape[:2]
        
        combined_heatmap = np.zeros_like(saliency_map, dtype=np.float32)
        
        for scale in scales:
            if scale != 1.0:
                new_h, new_w = int(h * scale), int(w * scale)
                scaled_saliency = cv2.resize(saliency_map, (new_w, new_h))
                scaled_saliency = cv2.resize(scaled_saliency, (w, h))
            else:
                scaled_saliency = saliency_map
            
            combined_heatmap += scaled_saliency
        
        combined_heatmap /= len(scales)
        combined_heatmap = (combined_heatmap - combined_heatmap.min()) / (combined_heatmap.max() - combined_heatmap.min() + 1e-8)
        
        return self.generate(combined_heatmap, original_image, threshold)
    
    def generate_dynamic_heatmap(self, saliency_map: np.ndarray, original_image: np.ndarray,
                                  time_window: int = 5, decay_rate: float = 0.8) -> HeatmapResult:
        if not hasattr(self, '_history'):
            self._history = []
        
        self._history.append(saliency_map.copy())
        if len(self._history) > time_window:
            self._history.pop(0)
        
        if len(self._history) == 1:
            return self.generate(saliency_map, original_image)
        
        weights = np.array([decay_rate ** i for i in range(len(self._history) - 1, -1, -1)])
        weights = weights / weights.sum()
        
        accumulated = np.zeros_like(saliency_map, dtype=np.float32)
        for i, hist in enumerate(self._history):
            accumulated += hist * weights[i]
        
        return self.generate(accumulated, original_image)
    
    def draw_attention_boxes(self, heatmap_result: HeatmapResult,
                             draw_top_k: int = 3,
                             color: Tuple[int, int, int] = (0, 255, 0),
                             thickness: int = 2) -> np.ndarray:
        overlay = heatmap_result.overlay.copy()
        
        for i, region in enumerate(heatmap_result.attention_regions[:draw_top_k]):
            x, y, w, h = region['bbox']
            cx, cy = region['center']
            
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, thickness)
            
            label = f"#{i+1}: {region['mean_attention']:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(overlay, (x, y - text_h - 5), (x + text_w + 5, y), (0, 0, 0), -1)
            cv2.putText(overlay, label, (x + 2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.circle(overlay, (int(cx), int(cy)), 5, color, -1)
        
        return overlay
    
    def create_heatmap_legend(self, width: int = 200, height: int = 30) -> np.ndarray:
        legend = np.zeros((height, width, 3), dtype=np.uint8)
        
        for x in range(width):
            value = x / width
            color = cv2.applyColorMap(np.uint8([[value * 255]]), self.colormap)[0, 0]
            color = cv2.cvtColor(color.reshape(1, 1, 3), cv2.COLOR_BGR2RGB)[0, 0]
            legend[:, x] = color
        
        return legend


class ModelExplainer:
    def __init__(self, model=None):
        self.model = model
        self.heatmap_generator = AttentionHeatmap()
        self._hook_handles = []
        self._feature_maps = {}
    
    def set_model(self, model):
        self.model = model
    
    def _register_hooks(self, target_layers: Optional[List[str]] = None):
        if self.model is None:
            return
        
        self._hook_handles = []
        self._feature_maps = {}
        
        def get_hook(layer_name):
            def hook(module, input, output):
                self._feature_maps[layer_name] = output.detach().cpu().numpy()
            return hook
        
        if target_layers is None:
            for name, module in self.model.named_modules():
                if 'conv' in name.lower() or 'encoder' in name.lower() or 'decoder' in name.lower():
                    handle = module.register_forward_hook(get_hook(name))
                    self._hook_handles.append(handle)
        else:
            for layer_name in target_layers:
                module = self._get_module_by_name(layer_name)
                if module is not None:
                    handle = module.register_forward_hook(get_hook(layer_name))
                    self._hook_handles.append(handle)
    
    def _get_module_by_name(self, name: str):
        if self.model is None:
            return None
        
        modules = dict(self.model.named_modules())
        return modules.get(name)
    
    def _remove_hooks(self):
        for handle in self._hook_handles:
            handle.remove()
        self._hook_handles = []
    
    def explain(self, image: np.ndarray, saliency_map: np.ndarray,
                target_layers: Optional[List[str]] = None,
                use_gradcam: bool = False) -> ExplainerResult:
        heatmap_result = self.heatmap_generator.generate(saliency_map, image)
        
        feature_maps = []
        gradcam_maps = []
        
        if self.model is not None:
            feature_maps = self._extract_feature_maps(image, target_layers)
            
            if use_gradcam:
                gradcam_maps = self._generate_gradcam_maps(image, saliency_map, target_layers)
        
        attention_stats = self._compute_attention_stats(saliency_map, heatmap_result)
        
        return ExplainerResult(
            heatmap_result=heatmap_result,
            feature_maps=feature_maps,
            gradcam_maps=gradcam_maps,
            attention_stats=attention_stats
        )
    
    def _extract_feature_maps(self, image: np.ndarray,
                              target_layers: Optional[List[str]] = None) -> List[FeatureMapResult]:
        try:
            import torch
            from data.transforms import preprocess_image
            
            self._register_hooks(target_layers)
            
            input_tensor = preprocess_image(image)
            if isinstance(input_tensor, np.ndarray):
                input_tensor = torch.from_numpy(input_tensor).unsqueeze(0)
            
            with torch.no_grad():
                _ = self.model(input_tensor)
            
            results = []
            for layer_name, fmaps in self._feature_maps.items():
                fmaps = fmaps[0]
                
                mean_act = fmaps.mean(axis=0)
                max_act = fmaps.max(axis=0)
                
                visualizations = []
                for i in range(min(8, fmaps.shape[0])):
                    fmap = fmaps[i]
                    fmap_norm = (fmap - fmap.min()) / (fmap.max() - fmap.min() + 1e-8)
                    fmap_uint8 = (fmap_norm * 255).astype(np.uint8)
                    fmap_color = cv2.applyColorMap(fmap_uint8, cv2.COLORMAP_VIRIDIS)
                    fmap_color = cv2.cvtColor(fmap_color, cv2.COLOR_BGR2RGB)
                    visualizations.append(fmap_color)
                
                results.append(FeatureMapResult(
                    layer_name=layer_name,
                    feature_maps=fmaps,
                    mean_activation=mean_act,
                    max_activation=max_act,
                    visualizations=visualizations
                ))
            
            self._remove_hooks()
            
            return results
            
        except Exception as e:
            print(f"Feature map extraction failed: {e}")
            return []
    
    def _generate_gradcam_maps(self, image: np.ndarray, saliency_map: np.ndarray,
                                target_layers: Optional[List[str]] = None) -> List[FeatureMapResult]:
        try:
            import torch
            from data.transforms import preprocess_image
            
            results = []
            
            if target_layers is None:
                target_layers = []
                for name, module in self.model.named_modules():
                    if 'encoder' in name.lower() and 'conv' in name.lower():
                        target_layers.append(name)
            
            for target_layer in target_layers[:3]:
                module = self._get_module_by_name(target_layer)
                if module is None:
                    continue
                
                gradients = []
                activations = []
                
                def forward_hook(mod, inp, out):
                    activations.append(out)
                
                def backward_hook(mod, grad_in, grad_out):
                    gradients.append(grad_out[0])
                
                fwd_handle = module.register_forward_hook(forward_hook)
                bwd_handle = module.register_full_backward_hook(backward_hook)
                
                try:
                    input_tensor = preprocess_image(image)
                    if isinstance(input_tensor, np.ndarray):
                        input_tensor = torch.from_numpy(input_tensor).unsqueeze(0)
                    input_tensor.requires_grad = True
                    
                    self.model.zero_grad()
                    output = self.model(input_tensor)
                    
                    if isinstance(output, (list, tuple)):
                        output = output[0]
                    
                    target = output.mean()
                    target.backward()
                    
                    if gradients and activations:
                        grad = gradients[0].detach().cpu().numpy()[0]
                        act = activations[0].detach().cpu().numpy()[0]
                        
                        weights = grad.mean(axis=(1, 2), keepdims=True)
                        cam = (weights * act).sum(axis=0)
                        cam = np.maximum(cam, 0)
                        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
                        
                        cam_resized = cv2.resize(cam, (image.shape[1], image.shape[0]))
                        cam_colored = cv2.applyColorMap((cam_resized * 255).astype(np.uint8), cv2.COLORMAP_JET)
                        cam_colored = cv2.cvtColor(cam_colored, cv2.COLOR_BGR2RGB)
                        
                        mean_act = act.mean(axis=0)
                        max_act = act.max(axis=0)
                        
                        results.append(FeatureMapResult(
                            layer_name=f'gradcam_{target_layer}',
                            feature_maps=act,
                            mean_activation=mean_act,
                            max_activation=max_act,
                            visualizations=[cam_colored]
                        ))
                
                except Exception as e:
                    print(f"GradCAM failed for {target_layer}: {e}")
                
                fwd_handle.remove()
                bwd_handle.remove()
            
            return results
            
        except Exception as e:
            print(f"GradCAM generation failed: {e}")
            return []
    
    def _compute_attention_stats(self, saliency_map: np.ndarray,
                                 heatmap_result: HeatmapResult) -> Dict[str, Any]:
        stats = {
            'mean_attention': float(saliency_map.mean()),
            'max_attention': float(saliency_map.max()),
            'std_attention': float(saliency_map.std()),
            'num_regions': len(heatmap_result.attention_regions),
            'total_attention_area': 0.0,
            'top_regions': []
        }
        
        total_pixels = saliency_map.shape[0] * saliency_map.shape[1]
        
        for region in heatmap_result.attention_regions[:5]:
            area_ratio = region['area'] / total_pixels
            stats['total_attention_area'] += area_ratio
            stats['top_regions'].append({
                'id': region['id'],
                'area_ratio': area_ratio,
                'mean_attention': region['mean_attention'],
                'bbox': region['bbox']
            })
        
        attention_above_threshold = (saliency_map > 0.5).sum() / total_pixels
        stats['attention_above_50'] = float(attention_above_threshold)
        
        entropy = -np.sum(saliency_map * np.log2(saliency_map + 1e-10))
        stats['attention_entropy'] = float(entropy)
        
        return stats
    
    def create_explanation_visualization(self, explainer_result: ExplainerResult,
                                          figsize: Tuple[int, int] = (1200, 800)) -> np.ndarray:
        heatmap = explainer_result.heatmap_result
        annotated = self.heatmap_generator.draw_attention_boxes(heatmap)
        
        main_width = figsize[0] * 2 // 3
        main_height = figsize[1]
        
        annotated_resized = cv2.resize(annotated, (main_width, main_height))
        
        sidebar = np.zeros((main_height, figsize[0] - main_width, 3), dtype=np.uint8)
        
        y_offset = 10
        
        cv2.putText(sidebar, "Attention Stats:", (10, y_offset + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_offset += 30
        
        stats = explainer_result.attention_stats
        cv2.putText(sidebar, f"Mean: {stats['mean_attention']:.3f}", (10, y_offset + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y_offset += 20
        cv2.putText(sidebar, f"Max: {stats['max_attention']:.3f}", (10, y_offset + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y_offset += 20
        cv2.putText(sidebar, f"Regions: {stats['num_regions']}", (10, y_offset + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y_offset += 20
        cv2.putText(sidebar, f"Coverage: {stats['attention_above_50']:.1%}", (10, y_offset + 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        y_offset += 30
        
        if explainer_result.feature_maps:
            cv2.putText(sidebar, "Feature Maps:", (10, y_offset + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset += 25
            
            for fm in explainer_result.feature_maps[:2]:
                if fm.visualizations:
                    viz = fm.visualizations[0]
                    viz_small = cv2.resize(viz, (100, 100))
                    sidebar[y_offset:y_offset+100, 10:110] = viz_small
                    y_offset += 110
        
        combined = np.hstack([annotated_resized, sidebar])
        
        return combined
    
    def save_explanation(self, explainer_result: ExplainerResult, output_dir: str,
                         base_filename: str = 'explanation'):
        os.makedirs(output_dir, exist_ok=True)
        
        from utils.helpers import save_image
        
        overlay_path = os.path.join(output_dir, f'{base_filename}_heatmap_overlay.png')
        save_image(explainer_result.heatmap_result.overlay, overlay_path)
        
        annotated = self.heatmap_generator.draw_attention_boxes(explainer_result.heatmap_result)
        annotated_path = os.path.join(output_dir, f'{base_filename}_annotated.png')
        save_image(annotated, annotated_path)
        
        if explainer_result.feature_maps:
            fm_dir = os.path.join(output_dir, 'feature_maps')
            os.makedirs(fm_dir, exist_ok=True)
            
            for fm in explainer_result.feature_maps:
                safe_name = fm.layer_name.replace('/', '_').replace('.', '_')
                for i, viz in enumerate(fm.visualizations):
                    fm_path = os.path.join(fm_dir, f'{safe_name}_map_{i}.png')
                    save_image(viz, fm_path)
        
        if explainer_result.gradcam_maps:
            gc_dir = os.path.join(output_dir, 'gradcam')
            os.makedirs(gc_dir, exist_ok=True)
            
            for gc in explainer_result.gradcam_maps:
                safe_name = gc.layer_name.replace('/', '_').replace('.', '_')
                for i, viz in enumerate(gc.visualizations):
                    gc_path = os.path.join(gc_dir, f'{safe_name}_{i}.png')
                    save_image(viz, gc_path)
        
        import json
        stats_path = os.path.join(output_dir, f'{base_filename}_stats.json')
        with open(stats_path, 'w') as f:
            json.dump(explainer_result.attention_stats, f, indent=2)


def generate_attention_heatmap(saliency_map: np.ndarray, original_image: np.ndarray,
                               **kwargs) -> HeatmapResult:
    generator = AttentionHeatmap(**{k: v for k, v in kwargs.items() if k in ['colormap', 'alpha']})
    return generator.generate(saliency_map, original_image,
                             **{k: v for k, v in kwargs.items() if k in ['threshold', 'min_region_size']})


def visualize_feature_maps(model, image: np.ndarray, **kwargs) -> List[FeatureMapResult]:
    explainer = ModelExplainer(model)
    return explainer._extract_feature_maps(image, kwargs.get('target_layers'))


def generate_gradcam(model, image: np.ndarray, saliency_map: np.ndarray,
                     **kwargs) -> List[FeatureMapResult]:
    explainer = ModelExplainer(model)
    return explainer._generate_gradcam_maps(image, saliency_map, kwargs.get('target_layers'))


def explain_prediction(model, image: np.ndarray, saliency_map: np.ndarray,
                       **kwargs) -> ExplainerResult:
    explainer = ModelExplainer(model)
    return explainer.explain(image, saliency_map, **kwargs)
