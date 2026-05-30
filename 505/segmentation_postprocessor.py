import os
import sys
import glob
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import (Slider, Button, CheckButtons,
                                RadioButtons, TextBox, Cursor)
from matplotlib.path import Path
from matplotlib.patches import Polygon
from scipy import ndimage as ndi
from scipy.ndimage import (binary_fill_holes, binary_opening,
                           binary_closing, distance_transform_edt)
from skimage.morphology import (remove_small_objects, remove_small_holes,
                                disk, binary_dilation, binary_erosion,
                                reconstruction)
from skimage.filters import sobel, scharr
from collections import deque
import warnings
warnings.filterwarnings('ignore')


class SegmentationPostProcessor:
    def __init__(self):
        self.class_colors = None
        self.num_classes = None

    def load_segmentation(self, filepath):
        img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"无法加载图像: {filepath}")
        
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            seg_mask, self.class_colors, self.num_classes = self.rgb_to_mask(img)
        else:
            seg_mask = img
            self.num_classes = len(np.unique(seg_mask))
            self.class_colors = self.generate_colors(self.num_classes)
        
        return seg_mask

    def rgb_to_mask(self, rgb_img):
        pixels = rgb_img.reshape(-1, 3)
        unique_colors = np.unique(pixels, axis=0)
        num_classes = len(unique_colors)
        
        mask = np.zeros(rgb_img.shape[:2], dtype=np.int32)
        for idx, color in enumerate(unique_colors):
            class_mask = np.all(rgb_img == color, axis=-1)
            mask[class_mask] = idx
        
        return mask, unique_colors, num_classes

    def mask_to_rgb(self, mask):
        if self.class_colors is None:
            self.class_colors = self.generate_colors(len(np.unique(mask)))
        
        rgb_img = np.zeros((*mask.shape, 3), dtype=np.uint8)
        for idx in range(len(self.class_colors)):
            class_mask = mask == idx
            rgb_img[class_mask] = self.class_colors[idx]
        
        return rgb_img

    def generate_colors(self, num_classes):
        np.random.seed(42)
        colors = np.random.randint(0, 255, size=(num_classes, 3), dtype=np.uint8)
        colors[0] = [0, 0, 0]
        return colors

    def fill_holes_per_class(self, mask, min_hole_size=0):
        result = np.zeros_like(mask)
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = mask == class_idx
            if min_hole_size > 0:
                filled = remove_small_holes(class_mask, area_threshold=min_hole_size)
            else:
                filled = binary_fill_holes(class_mask)
            result[filled] = class_idx
        return result

    def fill_holes_reconstruction(self, mask, min_hole_size=0, max_hole_size=None):
        result = np.zeros_like(mask)
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.uint8)
            
            inverted = 1 - class_mask
            markers = np.zeros_like(inverted)
            markers[0, :] = inverted[0, :]
            markers[-1, :] = inverted[-1, :]
            markers[:, 0] = inverted[:, 0]
            markers[:, -1] = inverted[:, -1]
            
            reconstructed = reconstruction(markers, inverted, 
                                         method='dilation')
            holes = inverted - reconstructed
            
            if min_hole_size > 0 or max_hole_size is not None:
                labeled_holes, num_holes = ndi.label(holes)
                for hole_idx in range(1, num_holes + 1):
                    hole_mask = labeled_holes == hole_idx
                    hole_size = np.sum(hole_mask)
                    if (min_hole_size > 0 and hole_size < min_hole_size) or \
                       (max_hole_size is not None and hole_size > max_hole_size):
                        holes[hole_mask] = 0
            
            filled = class_mask + holes
            filled = np.clip(filled, 0, 1).astype(bool)
            result[filled] = class_idx
        return result

    def remove_small_regions(self, mask, min_area=50, connectivity=1):
        result = np.copy(mask)
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = mask == class_idx
            cleaned = remove_small_objects(class_mask, min_size=min_area, connectivity=connectivity)
            result[class_mask & ~cleaned] = 0
        return result

    def smooth_edges_morphology(self, mask, kernel_size=3, iterations=1):
        result = np.copy(mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.uint8)
            smoothed = cv2.morphologyEx(class_mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)
            smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_OPEN, kernel, iterations=iterations)
            result[smoothed > 0] = class_idx
        
        return result

    def smooth_edges_adaptive(self, mask, min_object_area=500, max_kernel=7, 
                              edge_preserve=True):
        result = np.zeros_like(mask)
        
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.uint8)
            
            labeled, num_regions = ndi.label(class_mask)
            smoothed_class = np.zeros_like(class_mask, dtype=bool)
            
            for region_idx in range(1, num_regions + 1):
                region_mask = labeled == region_idx
                region_area = np.sum(region_mask)
                
                if region_area >= min_object_area:
                    area_ratio = min(region_area / (min_object_area * 10), 1.0)
                    kernel_size = int(3 + (max_kernel - 3) * area_ratio)
                    if kernel_size % 2 == 0:
                        kernel_size += 1
                    
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                                       (kernel_size, kernel_size))
                    region_uint8 = region_mask.astype(np.uint8)
                    smoothed = cv2.morphologyEx(region_uint8, cv2.MORPH_CLOSE, 
                                                kernel, iterations=1)
                    smoothed = cv2.morphologyEx(smoothed, cv2.MORPH_OPEN, 
                                                kernel, iterations=1)
                    smoothed_class = smoothed_class | (smoothed > 0)
                else:
                    smoothed_class = smoothed_class | region_mask
            
            if edge_preserve:
                edges = self.compute_class_edges(mask)
                edge_mask = edges > 0
                original_edges = class_mask.astype(bool) & edge_mask
                smoothed_class[original_edges] = True
            
            result[smoothed_class] = class_idx
        
        return result

    def compute_class_edges(self, mask):
        edges = np.zeros_like(mask, dtype=np.uint8)
        
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.uint8)
            sobel_x = cv2.Sobel(class_mask, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(class_mask, cv2.CV_64F, 0, 1, ksize=3)
            magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            edges = edges | (magnitude > 0.5).astype(np.uint8)
        
        return edges

    def compute_edge_guidance_map(self, mask, edge_weight=0.5):
        rgb = self.mask_to_rgb(mask)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        
        edges = cv2.Canny(gray, 50, 150)
        edges = (edges > 0).astype(np.float32)
        
        guidance = 1.0 - edge_weight * edges
        return guidance

    def smooth_with_edge_guidance(self, mask, sigma=1.5, edge_threshold=0.3, 
                                  edge_weight=0.7):
        result = np.zeros_like(mask)
        edge_guidance = self.compute_edge_guidance_map(mask, edge_weight=edge_weight)
        class_edges = self.compute_class_edges(mask)
        
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.float32)
            
            blurred = cv2.GaussianBlur(class_mask, (0, 0), sigmaX=sigma)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            dilated = cv2.dilate(class_mask, kernel, iterations=1)
            eroded = cv2.erode(class_mask, kernel, iterations=1)
            boundary = dilated - eroded
            
            local_edge_strength = edge_guidance * (1 - boundary * 0.5)
            smoothed = class_mask * (1 - local_edge_strength) + blurred * local_edge_strength
            
            binary = smoothed > edge_threshold
            
            edge_mask = class_edges > 0
            original_edges = class_mask.astype(bool) & edge_mask
            binary[original_edges] = True
            
            result[binary] = class_idx
        
        return result

    def smooth_edges_gaussian(self, mask, sigma=1.0, threshold=0.5):
        result = np.zeros_like(mask)
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.float32)
            smoothed = cv2.GaussianBlur(class_mask, (0, 0), sigmaX=sigma)
            binary = smoothed > threshold
            result[binary] = class_idx
        return result

    def smooth_edges_distance(self, mask, sigma=1.0):
        result = np.zeros_like(mask)
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = (mask == class_idx).astype(np.uint8)
            dist = cv2.distanceTransform(class_mask, cv2.DIST_L2, 5)
            dist_inv = cv2.distanceTransform(1 - class_mask, cv2.DIST_L2, 5)
            combined = dist - dist_inv
            result[combined > 0] = class_idx
        return result

    def apply_watershed(self, mask, markers=None):
        rgb = self.mask_to_rgb(mask)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        
        if markers is None:
            markers = ndi.label(mask > 0)[0]
        
        ws_result = cv2.watershed(rgb, markers.astype(np.int32))
        result = np.zeros_like(mask)
        
        for class_idx in range(self.num_classes):
            if class_idx == 0:
                continue
            class_mask = mask == class_idx
            for label in np.unique(markers[class_mask]):
                if label == 0:
                    continue
                ws_region = ws_result == label
                if np.mean(class_mask[ws_region]) > 0.5:
                    result[ws_region] = class_idx
        
        return result

    def process(self, mask, config):
        result = np.copy(mask)
        
        if config.get('fill_holes', True):
            hole_method = config.get('hole_method', 'basic')
            hole_size = config.get('min_hole_size', 0)
            max_hole_size = config.get('max_hole_size', None)
            
            if hole_method == 'reconstruction':
                result = self.fill_holes_reconstruction(result, 
                                                        min_hole_size=hole_size,
                                                        max_hole_size=max_hole_size)
            else:
                result = self.fill_holes_per_class(result, min_hole_size=hole_size)
        
        if config.get('remove_small', True):
            min_area = config.get('min_area', 50)
            connectivity = config.get('connectivity', 1)
            result = self.remove_small_regions(result, min_area=min_area, connectivity=connectivity)
        
        smooth_method = config.get('smooth_method', 'none')
        if smooth_method == 'morphology':
            kernel_size = config.get('kernel_size', 3)
            iterations = config.get('iterations', 1)
            result = self.smooth_edges_morphology(result, kernel_size=kernel_size, 
                                                  iterations=iterations)
        elif smooth_method == 'gaussian':
            sigma = config.get('sigma', 1.0)
            threshold = config.get('threshold', 0.5)
            result = self.smooth_edges_gaussian(result, sigma=sigma, threshold=threshold)
        elif smooth_method == 'distance':
            sigma = config.get('sigma', 1.0)
            result = self.smooth_edges_distance(result, sigma=sigma)
        elif smooth_method == 'watershed':
            result = self.apply_watershed(result)
        elif smooth_method == 'adaptive':
            min_object_area = config.get('min_object_area', 500)
            max_kernel = config.get('max_kernel', 7)
            edge_preserve = config.get('edge_preserve', True)
            result = self.smooth_edges_adaptive(result, 
                                                min_object_area=min_object_area,
                                                max_kernel=max_kernel,
                                                edge_preserve=edge_preserve)
        elif smooth_method == 'edge_guided':
            sigma = config.get('sigma', 1.5)
            edge_threshold = config.get('edge_threshold', 0.3)
            edge_weight = config.get('edge_weight', 0.7)
            result = self.smooth_with_edge_guidance(result,
                                                    sigma=sigma,
                                                    edge_threshold=edge_threshold,
                                                    edge_weight=edge_weight)
        
        return result

    def batch_process(self, input_dir, output_dir, config, file_pattern='*.png'):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        file_paths = glob.glob(os.path.join(input_dir, file_pattern))
        results = []
        
        for filepath in file_paths:
            try:
                mask = self.load_segmentation(filepath)
                processed = self.process(mask, config)
                output_rgb = self.mask_to_rgb(processed)
                
                filename = os.path.basename(filepath)
                output_path = os.path.join(output_dir, f"processed_{filename}")
                cv2.imwrite(output_path, cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR))
                
                results.append({
                    'input': filepath,
                    'output': output_path,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'input': filepath,
                    'error': str(e),
                    'success': False
                })
        
        return results

    def evaluate_miou(self, pred_mask, gt_mask, num_classes=None):
        if num_classes is None:
            num_classes = self.num_classes
        
        ious = []
        for cls in range(num_classes):
            pred_inds = pred_mask == cls
            gt_inds = gt_mask == cls
            
            intersection = np.logical_and(pred_inds, gt_inds).sum()
            union = np.logical_or(pred_inds, gt_inds).sum()
            
            if union == 0:
                continue
            ious.append(intersection / union)
        
        if len(ious) == 0:
            return 0.0, []
        
        miou = np.mean(ious)
        return miou, ious

    def evaluate_boundary_fscore(self, pred_mask, gt_mask, tolerance=3, num_classes=None):
        if num_classes is None:
            num_classes = self.num_classes
        
        f_scores = []
        precisions = []
        recalls = []
        
        for cls in range(1, num_classes):
            pred_cls = (pred_mask == cls).astype(np.uint8)
            gt_cls = (gt_mask == cls).astype(np.uint8)
            
            pred_edges = cv2.Canny(pred_cls * 255, 50, 150) > 0
            gt_edges = cv2.Canny(gt_cls * 255, 50, 150) > 0
            
            if np.sum(gt_edges) == 0 and np.sum(pred_edges) == 0:
                continue
            
            dist_pred = cv2.distanceTransform(~pred_edges.astype(np.uint8), cv2.DIST_L2, 5)
            dist_gt = cv2.distanceTransform(~gt_edges.astype(np.uint8), cv2.DIST_L2, 5)
            
            tp = np.sum(np.logical_and(gt_edges, dist_pred <= tolerance))
            fp = np.sum(np.logical_and(pred_edges, dist_gt > tolerance))
            fn = np.sum(np.logical_and(gt_edges, dist_pred > tolerance))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            
            f_scores.append(f_score)
            precisions.append(precision)
            recalls.append(recall)
        
        if len(f_scores) == 0:
            return 0.0, 0.0, 0.0, []
        
        mean_f = np.mean(f_scores)
        mean_p = np.mean(precisions)
        mean_r = np.mean(recalls)
        
        return mean_f, mean_p, mean_r, list(zip(precisions, recalls, f_scores))

    def evaluate_segmentation(self, pred_mask, gt_mask, num_classes=None):
        if num_classes is None:
            num_classes = max(self.num_classes, len(np.unique(gt_mask)))
        
        miou, per_class_iou = self.evaluate_miou(pred_mask, gt_mask, num_classes)
        f_score, precision, recall, per_class_metrics = self.evaluate_boundary_fscore(
            pred_mask, gt_mask, num_classes=num_classes
        )
        
        metrics = {
            'mIoU': miou,
            'per_class_IoU': per_class_iou,
            'boundary_F_score': f_score,
            'boundary_precision': precision,
            'boundary_recall': recall,
            'per_class_boundary_metrics': per_class_metrics
        }
        
        return metrics

    def create_brush_mask(self, shape, points, brush_size=5):
        mask = np.zeros(shape, dtype=np.uint8)
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            cv2.line(mask, (int(x1), int(y1)), (int(x2), int(y2)), 255, brush_size)
        return mask.astype(bool)

    def create_lasso_mask(self, shape, polygon_points):
        if len(polygon_points) < 3:
            return np.zeros(shape, dtype=bool)
        
        mask = np.zeros(shape, dtype=np.uint8)
        polygon = np.array(polygon_points, dtype=np.int32)
        cv2.fillPoly(mask, [polygon], 1)
        return mask.astype(bool)

    def apply_brush_correction(self, mask, points, target_class, brush_size=5, mode='add'):
        brush_mask = self.create_brush_mask(mask.shape, points, brush_size)
        
        corrected = mask.copy()
        if mode == 'add':
            corrected[brush_mask] = target_class
        elif mode == 'remove':
            corrected[brush_mask] = 0
        
        return corrected

    def apply_lasso_correction(self, mask, polygon_points, target_class, mode='add'):
        lasso_mask = self.create_lasso_mask(mask.shape, polygon_points)
        
        corrected = mask.copy()
        if mode == 'add':
            corrected[lasso_mask] = target_class
        elif mode == 'remove':
            corrected[lasso_mask] = 0
        
        return corrected

    def fill_holes_interactive(self, mask, seed_point, target_class=None):
        x, y = seed_point
        if target_class is None:
            target_class = mask[y, x]
        
        if target_class == 0:
            return mask
        
        mask_uint8 = mask.astype(np.uint8)
        flood_mask = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
        flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        
        cv2.floodFill(mask_uint8, flood_mask, (int(x), int(y)), 255, 
                     loDiff=0, upDiff=0, flags=flags)
        
        hole_mask = flood_mask[1:-1, 1:-1] > 0
        
        corrected = mask.copy()
        corrected[hole_mask] = target_class
        
        return corrected

    def temporal_smooth_video_masks(self, masks, window_size=3, alpha=0.5):
        if len(masks) < window_size:
            return masks
        
        num_frames = len(masks)
        smoothed = []
        
        for i in range(num_frames):
            start = max(0, i - window_size // 2)
            end = min(num_frames, i + window_size // 2 + 1)
            
            window_masks = masks[start:end]
            current_mask = masks[i]
            
            if i == 0 or i == num_frames - 1:
                smoothed.append(current_mask.copy())
                continue
            
            vote_mask = np.zeros_like(current_mask)
            
            for cls in range(self.num_classes):
                class_votes = np.zeros_like(current_mask, dtype=np.float32)
                for j, m in enumerate(window_masks):
                    weight = 1.0 if j == (i - start) else alpha
                    class_votes += (m == cls).astype(np.float32) * weight
                vote_mask[class_votes >= (len(window_masks) * alpha / 2)] = cls
            
            edges = self.compute_class_edges(current_mask)
            edge_mask = edges > 0
            vote_mask[edge_mask] = current_mask[edge_mask]
            
            smoothed.append(vote_mask)
        
        return smoothed

    def optical_flow_consistency(self, masks, reference_frame=0):
        if len(masks) < 2:
            return masks
        
        reference_mask = masks[reference_frame]
        reference_rgb = self.mask_to_rgb(reference_mask)
        reference_gray = cv2.cvtColor(reference_rgb, cv2.COLOR_RGB2GRAY)
        
        consistent_masks = [reference_mask.copy()]
        
        for i in range(1, len(masks)):
            current_mask = masks[i]
            current_rgb = self.mask_to_rgb(current_mask)
            current_gray = cv2.cvtColor(current_rgb, cv2.COLOR_RGB2GRAY)
            
            flow = cv2.calcOpticalFlowFarneback(
                reference_gray, current_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            
            h, w = reference_gray.shape
            y_coords, x_coords = np.mgrid[0:h, 0:w]
            
            map_x = (x_coords + flow[..., 0]).astype(np.float32)
            map_y = (y_coords + flow[..., 1]).astype(np.float32)
            
            warped_reference = cv2.remap(
                reference_mask.astype(np.float32), map_x, map_y,
                cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0
            ).astype(np.int32)
            
            consensus = np.zeros_like(current_mask)
            for cls in range(self.num_classes):
                overlap = np.logical_and(current_mask == cls, warped_reference == cls)
                consensus[overlap] = cls
            
            current_edges = self.compute_class_edges(current_mask)
            edge_mask = current_edges > 0
            consensus[edge_mask] = current_mask[edge_mask]
            
            consistent_masks.append(consensus)
        
        return consistent_masks

    def process_video_masks(self, masks, config=None):
        if config is None:
            config = {
                'temporal_window': 3,
                'temporal_alpha': 0.5,
                'use_optical_flow': True,
                'per_frame_postprocess': True
            }
        
        processed_masks = []
        
        if config.get('per_frame_postprocess', True):
            for mask in masks:
                processed = self.process(mask, self.config if hasattr(self, 'config') else {
                    'fill_holes': True,
                    'hole_method': 'reconstruction',
                    'min_hole_size': 50,
                    'remove_small': True,
                    'min_area': 100,
                    'smooth_method': 'edge_guided',
                    'sigma': 1.5,
                    'edge_threshold': 0.3,
                    'edge_weight': 0.7
                })
                processed_masks.append(processed)
        else:
            processed_masks = [m.copy() for m in masks]
        
        if config.get('use_optical_flow', False):
            processed_masks = self.optical_flow_consistency(processed_masks)
        
        window_size = config.get('temporal_window', 3)
        alpha = config.get('temporal_alpha', 0.5)
        processed_masks = self.temporal_smooth_video_masks(
            processed_masks, window_size=window_size, alpha=alpha
        )
        
        return processed_masks

    def load_video_masks(self, input_dir, file_pattern='*.png'):
        file_paths = sorted(glob.glob(os.path.join(input_dir, file_pattern)))
        masks = []
        
        for filepath in file_paths:
            mask = self.load_segmentation(filepath)
            masks.append(mask)
        
        return masks, file_paths

    def save_video_masks(self, masks, output_dir, original_filenames=None):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for i, mask in enumerate(masks):
            output_rgb = self.mask_to_rgb(mask)
            if original_filenames and i < len(original_filenames):
                filename = os.path.basename(original_filenames[i])
            else:
                filename = f'frame_{i:04d}.png'
            
            output_path = os.path.join(output_dir, f'processed_{filename}')
            cv2.imwrite(output_path, cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR))


class PostProcessorGUI:
    def __init__(self, sample_image_path=None):
        self.processor = SegmentationPostProcessor()
        self.original_mask = None
        self.current_mask = None
        self.gt_mask = None
        self.sample_image_path = sample_image_path
        
        self.correction_mode = None
        self.brush_size = 5
        self.target_class = 1
        self.correction_points = []
        self.lasso_points = []
        self.is_drawing = False
        self.history = deque(maxlen=20)
        
        self.video_masks = None
        self.current_frame_idx = 0
        self.video_filenames = None
        
        self.config = {
            'fill_holes': True,
            'hole_method': 'reconstruction',
            'min_hole_size': 50,
            'max_hole_size': 1000,
            'remove_small': True,
            'min_area': 100,
            'connectivity': 1,
            'smooth_method': 'edge_guided',
            'kernel_size': 3,
            'iterations': 1,
            'sigma': 1.5,
            'threshold': 0.5,
            'min_object_area': 500,
            'max_kernel': 7,
            'edge_preserve': True,
            'edge_threshold': 0.3,
            'edge_weight': 0.7,
            'temporal_window': 3,
            'temporal_alpha': 0.5,
            'use_optical_flow': True
        }
        
        self.setup_gui()
        self.setup_events()

    def setup_gui(self):
        self.fig = plt.figure(figsize=(18, 12))
        gs = self.fig.add_gridspec(5, 4, hspace=0.3, wspace=0.25)
        
        self.ax_original = self.fig.add_subplot(gs[:2, 0])
        self.ax_processed = self.fig.add_subplot(gs[:2, 1])
        self.ax_correction = self.fig.add_subplot(gs[:2, 2])
        self.ax_diff = self.fig.add_subplot(gs[:2, 3])
        
        self.ax_original.set_title('原始分割结果', fontsize=11, fontweight='bold')
        self.ax_processed.set_title('后处理结果', fontsize=11, fontweight='bold')
        self.ax_correction.set_title('交互式修正', fontsize=11, fontweight='bold')
        self.ax_diff.set_title('差异对比', fontsize=11, fontweight='bold')
        
        for ax in [self.ax_original, self.ax_processed, self.ax_correction, self.ax_diff]:
            ax.axis('off')
        
        self.setup_controls(gs)
        
        if self.sample_image_path and os.path.exists(self.sample_image_path):
            self.load_image(self.sample_image_path)
        
        self.fig.tight_layout(rect=[0, 0, 1, 0.96])

    def setup_events(self):
        self.fig.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key_press)

    def setup_controls(self, gs):
        control_ax = self.fig.add_subplot(gs[2:, :])
        control_ax.axis('off')
        
        button_width = 0.08
        slider_width = 0.25
        
        y_base = 0.88
        y_step = 0.08
        
        self.ax_check_fill = plt.axes([0.02, y_base, button_width, 0.04])
        self.check_fill = CheckButtons(
            self.ax_check_fill,
            ['孔洞填充'],
            [self.config['fill_holes']]
        )
        self.check_fill.on_clicked(self.update_config)
        
        self.ax_radio_hole = plt.axes([0.12, y_base - 0.03, button_width + 0.04, 0.08])
        self.radio_hole = RadioButtons(
            self.ax_radio_hole,
            ('基本填充', '形态学重建'),
            active=1
        )
        self.radio_hole.on_clicked(self.update_hole_method)
        
        self.ax_hole_slider = plt.axes([0.25, y_base + 0.02, slider_width, 0.025])
        self.slider_hole = Slider(
            self.ax_hole_slider, '最小孔洞',
            0, 500, valinit=self.config['min_hole_size'], valstep=10
        )
        self.slider_hole.on_changed(self.update_config)
        
        self.ax_maxhole_slider = plt.axes([0.53, y_base + 0.02, slider_width, 0.025])
        self.slider_maxhole = Slider(
            self.ax_maxhole_slider, '最大孔洞',
            100, 5000, valinit=self.config['max_hole_size'], valstep=50
        )
        self.slider_maxhole.on_changed(self.update_config)
        
        y_base -= y_step
        
        self.ax_check_small = plt.axes([0.02, y_base, button_width, 0.04])
        self.check_small = CheckButtons(
            self.ax_check_small,
            ['小区域去除'],
            [self.config['remove_small']]
        )
        self.check_small.on_clicked(self.update_config)
        
        self.ax_area_slider = plt.axes([0.12, y_base + 0.01, slider_width, 0.025])
        self.slider_area = Slider(
            self.ax_area_slider, '最小区域',
            10, 1000, valinit=self.config['min_area'], valstep=10
        )
        self.slider_area.on_changed(self.update_config)
        
        y_base -= y_step
        
        self.ax_radio_smooth = plt.axes([0.02, y_base - 0.05, button_width + 0.06, 0.1])
        self.radio_smooth = RadioButtons(
            self.ax_radio_smooth,
            ('无平滑', '形态学', '高斯', '距离场', '分水岭', '自适应', '边缘引导'),
            active=6
        )
        self.radio_smooth.on_clicked(self.update_smooth_method)
        
        self.ax_kernel_slider = plt.axes([0.15, y_base + 0.04, slider_width, 0.025])
        self.slider_kernel = Slider(
            self.ax_kernel_slider, '卷积核',
            3, 15, valinit=self.config['kernel_size'], valstep=2
        )
        self.slider_kernel.on_changed(self.update_config)
        
        self.ax_iter_slider = plt.axes([0.15, y_base + 0.005, slider_width, 0.025])
        self.slider_iter = Slider(
            self.ax_iter_slider, '迭代次数',
            1, 5, valinit=self.config['iterations'], valstep=1
        )
        self.slider_iter.on_changed(self.update_config)
        
        self.ax_sigma_slider = plt.axes([0.15, y_base - 0.03, slider_width, 0.025])
        self.slider_sigma = Slider(
            self.ax_sigma_slider, 'Sigma',
            0.5, 5.0, valinit=self.config['sigma'], valstep=0.1
        )
        self.slider_sigma.on_changed(self.update_config)
        
        self.ax_minobj_slider = plt.axes([0.43, y_base + 0.04, slider_width, 0.025])
        self.slider_minobj = Slider(
            self.ax_minobj_slider, '最小物体面积',
            100, 2000, valinit=self.config['min_object_area'], valstep=50
        )
        self.slider_minobj.on_changed(self.update_config)
        
        self.ax_maxkernel_slider = plt.axes([0.43, y_base + 0.005, slider_width, 0.025])
        self.slider_maxkernel = Slider(
            self.ax_maxkernel_slider, '最大卷积核',
            3, 15, valinit=self.config['max_kernel'], valstep=2
        )
        self.slider_maxkernel.on_changed(self.update_config)
        
        self.ax_edgethresh_slider = plt.axes([0.43, y_base - 0.03, slider_width, 0.025])
        self.slider_edgethresh = Slider(
            self.ax_edgethresh_slider, '边缘阈值',
            0.1, 0.9, valinit=self.config['edge_threshold'], valstep=0.05
        )
        self.slider_edgethresh.on_changed(self.update_config)
        
        self.ax_edgeweight_slider = plt.axes([0.71, y_base + 0.04, slider_width - 0.05, 0.025])
        self.slider_edgeweight = Slider(
            self.ax_edgeweight_slider, '边缘权重',
            0.1, 1.0, valinit=self.config['edge_weight'], valstep=0.05
        )
        self.slider_edgeweight.on_changed(self.update_config)
        
        self.ax_check_edgepreserve = plt.axes([0.71, y_base - 0.02, button_width, 0.04])
        self.check_edgepreserve = CheckButtons(
            self.ax_check_edgepreserve,
            ['边缘保护'],
            [self.config['edge_preserve']]
        )
        self.check_edgepreserve.on_clicked(self.update_config)
        
        y_base -= y_step * 1.2
        
        self.ax_load_btn = plt.axes([0.15, y_base, 0.1, 0.06])
        self.btn_load = Button(self.ax_load_btn, '加载图像', color='lightblue')
        self.btn_load.on_clicked(self.load_image_dialog)
        
        self.ax_save_btn = plt.axes([0.30, y_base, 0.1, 0.06])
        self.btn_save = Button(self.ax_save_btn, '保存结果', color='lightgreen')
        self.btn_save.on_clicked(self.save_result)
        
        self.ax_batch_btn = plt.axes([0.45, y_base, 0.1, 0.06])
        self.btn_batch = Button(self.ax_batch_btn, '批量处理', color='lightyellow')
        self.btn_batch.on_clicked(self.batch_process_dialog)
        
        self.ax_showedge_btn = plt.axes([0.60, y_base, 0.1, 0.06])
        self.btn_showedge = Button(self.ax_showedge_btn, '显示边缘', color='lightgray')
        self.btn_showedge.on_clicked(self.show_edges)
        
        self.ax_reset_btn = plt.axes([0.75, y_base, 0.1, 0.06])
        self.btn_reset = Button(self.ax_reset_btn, '重置参数', color='lightcoral')
        self.btn_reset.on_clicked(self.reset_params)
        
        y_base -= y_step
        
        self.ax_radio_correction = plt.axes([0.02, y_base - 0.02, button_width + 0.08, 0.07])
        self.radio_correction = RadioButtons(
            self.ax_radio_correction,
            ('无', '画笔', '套索', '填充'),
            active=0
        )
        self.radio_correction.on_clicked(self.update_correction_mode)
        
        self.ax_brush_slider = plt.axes([0.15, y_base + 0.02, slider_width * 0.6, 0.025])
        self.slider_brush = Slider(
            self.ax_brush_slider, '画笔大小',
            1, 30, valinit=self.brush_size, valstep=1
        )
        self.slider_brush.on_changed(self.update_brush_size)
        
        self.ax_class_slider = plt.axes([0.15, y_base - 0.02, slider_width * 0.6, 0.025])
        self.slider_class = Slider(
            self.ax_class_slider, '目标类别',
            1, 10, valinit=self.target_class, valstep=1
        )
        self.slider_class.on_changed(self.update_target_class)
        
        self.ax_undo_btn = plt.axes([0.35, y_base, 0.06, 0.06])
        self.btn_undo = Button(self.ax_undo_btn, '撤销', color='#ffcccc')
        self.btn_undo.on_clicked(self.undo_correction)
        
        self.ax_apply_btn = plt.axes([0.43, y_base, 0.06, 0.06])
        self.btn_apply = Button(self.ax_apply_btn, '应用', color='#ccffcc')
        self.btn_apply.on_clicked(self.apply_correction)
        
        self.ax_clear_btn = plt.axes([0.51, y_base, 0.06, 0.06])
        self.btn_clear = Button(self.ax_clear_btn, '清除', color='#ffffcc')
        self.btn_clear.on_clicked(self.clear_correction)
        
        self.ax_eval_btn = plt.axes([0.60, y_base, 0.08, 0.06])
        self.btn_eval = Button(self.ax_eval_btn, '质量评估', color='#cce5ff')
        self.btn_eval.on_clicked(self.evaluate_quality)
        
        self.ax_loadgt_btn = plt.axes([0.70, y_base, 0.08, 0.06])
        self.btn_loadgt = Button(self.ax_loadgt_btn, '加载真值', color='#e5ccff')
        self.btn_loadgt.on_clicked(self.load_ground_truth)
        
        y_base -= y_step
        
        self.ax_loadvideo_btn = plt.axes([0.02, y_base, 0.1, 0.06])
        self.btn_loadvideo = Button(self.ax_loadvideo_btn, '加载视频帧', color='#ffe5cc')
        self.btn_loadvideo.on_clicked(self.load_video_dialog)
        
        self.ax_processvideo_btn = plt.axes([0.14, y_base, 0.1, 0.06])
        self.btn_processvideo = Button(self.ax_processvideo_btn, '处理视频', color='#ccffe5')
        self.btn_processvideo.on_clicked(self.process_video)
        
        self.ax_savevideo_btn = plt.axes([0.26, y_base, 0.1, 0.06])
        self.btn_savevideo = Button(self.ax_savevideo_btn, '保存视频', color='#e5ffcc')
        self.btn_savevideo.on_clicked(self.save_video)
        
        self.ax_frame_slider = plt.axes([0.40, y_base + 0.01, slider_width, 0.03])
        self.slider_frame = Slider(
            self.ax_frame_slider, '帧索引',
            0, 0, valinit=0, valstep=1
        )
        self.slider_frame.on_changed(self.update_frame)
        
        self.ax_temporal_slider = plt.axes([0.70, y_base + 0.02, slider_width * 0.7, 0.025])
        self.slider_temporal = Slider(
            self.ax_temporal_slider, '时间窗口',
            1, 11, valinit=self.config['temporal_window'], valstep=2
        )
        self.slider_temporal.on_changed(self.update_temporal_config)

    def update_config(self, val):
        self.config['fill_holes'] = self.check_fill.get_status()[0]
        self.config['min_hole_size'] = int(self.slider_hole.val)
        self.config['max_hole_size'] = int(self.slider_maxhole.val)
        self.config['remove_small'] = self.check_small.get_status()[0]
        self.config['min_area'] = int(self.slider_area.val)
        self.config['kernel_size'] = int(self.slider_kernel.val)
        self.config['iterations'] = int(self.slider_iter.val)
        self.config['sigma'] = self.slider_sigma.val
        self.config['min_object_area'] = int(self.slider_minobj.val)
        self.config['max_kernel'] = int(self.slider_maxkernel.val)
        self.config['edge_threshold'] = self.slider_edgethresh.val
        self.config['edge_weight'] = self.slider_edgeweight.val
        self.config['edge_preserve'] = self.check_edgepreserve.get_status()[0]
        self.process_and_update()
    
    def update_hole_method(self, label):
        method_map = {
            '基本填充': 'basic',
            '形态学重建': 'reconstruction'
        }
        self.config['hole_method'] = method_map[label]
        self.process_and_update()

    def update_smooth_method(self, label):
        method_map = {
            '无平滑': 'none',
            '形态学': 'morphology',
            '高斯': 'gaussian',
            '距离场': 'distance',
            '分水岭': 'watershed',
            '自适应': 'adaptive',
            '边缘引导': 'edge_guided'
        }
        self.config['smooth_method'] = method_map[label]
        self.process_and_update()
    
    def show_edges(self, event):
        if self.original_mask is None:
            return
        
        edges = self.processor.compute_class_edges(self.original_mask)
        edge_guidance = self.processor.compute_edge_guidance_map(self.original_mask)
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].imshow(edges, cmap='gray')
        axes[0].set_title('类间边界检测', fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        axes[1].imshow(edge_guidance, cmap='jet')
        axes[1].set_title('边缘引导权重图', fontsize=12, fontweight='bold')
        axes[1].axis('off')
        
        plt.tight_layout()
        plt.show()

    def load_image(self, filepath):
        try:
            self.original_mask = self.processor.load_segmentation(filepath)
            self.current_mask = np.copy(self.original_mask)
            self.process_and_update()
        except Exception as e:
            print(f"加载图像失败: {e}")

    def load_image_dialog(self, event):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if filepath:
            self.load_image(filepath)
        root.destroy()

    def save_result(self, event):
        if self.current_mask is None:
            return
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图像", "*.png"), ("JPEG图像", "*.jpg")]
        )
        if filepath:
            output_rgb = self.processor.mask_to_rgb(self.current_mask)
            cv2.imwrite(filepath, cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR))
            print(f"结果已保存至: {filepath}")
        root.destroy()

    def batch_process_dialog(self, event):
        from tkinter import Tk, filedialog, simpledialog
        root = Tk()
        root.withdraw()
        
        input_dir = filedialog.askdirectory(title="选择输入目录")
        if not input_dir:
            root.destroy()
            return
        
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            root.destroy()
            return
        
        pattern = simpledialog.askstring("文件模式", "输入文件匹配模式:", initialvalue="*.png")
        if pattern is None:
            pattern = "*.png"
        
        print(f"开始批量处理...")
        print(f"输入目录: {input_dir}")
        print(f"输出目录: {output_dir}")
        
        results = self.processor.batch_process(input_dir, output_dir, self.config, pattern)
        
        success_count = sum(1 for r in results if r['success'])
        print(f"批量处理完成: 成功 {success_count}/{len(results)} 个文件")
        
        root.destroy()

    def reset_params(self, event):
        self.config = {
            'fill_holes': True,
            'hole_method': 'reconstruction',
            'min_hole_size': 50,
            'max_hole_size': 1000,
            'remove_small': True,
            'min_area': 100,
            'connectivity': 1,
            'smooth_method': 'edge_guided',
            'kernel_size': 3,
            'iterations': 1,
            'sigma': 1.5,
            'threshold': 0.5,
            'min_object_area': 500,
            'max_kernel': 7,
            'edge_preserve': True,
            'edge_threshold': 0.3,
            'edge_weight': 0.7,
            'temporal_window': 3,
            'temporal_alpha': 0.5,
            'use_optical_flow': True
        }
        
        if not self.config['fill_holes']:
            self.check_fill.set_active(0)
        if not self.config['remove_small']:
            self.check_small.set_active(0)
        if not self.config['edge_preserve']:
            self.check_edgepreserve.set_active(0)
        
        self.radio_hole.set_active(1 if self.config['hole_method'] == 'reconstruction' else 0)
        self.radio_smooth.set_active(6)
        self.radio_correction.set_active(0)
        
        self.slider_hole.set_val(self.config['min_hole_size'])
        self.slider_maxhole.set_val(self.config['max_hole_size'])
        self.slider_area.set_val(self.config['min_area'])
        self.slider_kernel.set_val(self.config['kernel_size'])
        self.slider_iter.set_val(self.config['iterations'])
        self.slider_sigma.set_val(self.config['sigma'])
        self.slider_minobj.set_val(self.config['min_object_area'])
        self.slider_maxkernel.set_val(self.config['max_kernel'])
        self.slider_edgethresh.set_val(self.config['edge_threshold'])
        self.slider_edgeweight.set_val(self.config['edge_weight'])
        self.slider_brush.set_val(self.brush_size)
        self.slider_class.set_val(self.target_class)
        self.slider_temporal.set_val(self.config['temporal_window'])
        
        self.correction_mode = None
        self.correction_points = []
        self.lasso_points = []
        self.is_drawing = False
        self.history.clear()
        
        self.process_and_update()

    def update_correction_mode(self, label):
        mode_map = {
            '无': None,
            '画笔': 'brush',
            '套索': 'lasso',
            '填充': 'fill'
        }
        self.correction_mode = mode_map[label]
        self.correction_points = []
        self.lasso_points = []
        self.is_drawing = False
        self.update_display()

    def update_brush_size(self, val):
        self.brush_size = int(val)

    def update_target_class(self, val):
        self.target_class = int(val)

    def update_temporal_config(self, val):
        self.config['temporal_window'] = int(val)

    def on_mouse_press(self, event):
        if event.inaxes != self.ax_correction or self.correction_mode is None:
            return
        
        if event.button == 1:
            self.is_drawing = True
            x, y = event.xdata, event.ydata
            
            if self.correction_mode == 'brush':
                self.correction_points = [(x, y)]
            elif self.correction_mode == 'lasso':
                self.lasso_points = [(x, y)]
            elif self.correction_mode == 'fill':
                self.save_history()
                self.current_mask = self.processor.fill_holes_interactive(
                    self.current_mask, (int(x), int(y)), self.target_class
                )
                self.update_display()
                self.is_drawing = False

    def on_mouse_move(self, event):
        if not self.is_drawing or event.inaxes != self.ax_correction:
            return
        
        x, y = event.xdata, event.ydata
        
        if self.correction_mode == 'brush':
            self.correction_points.append((x, y))
            if len(self.correction_points) >= 2:
                self.save_history()
                self.current_mask = self.processor.apply_brush_correction(
                    self.current_mask, self.correction_points, 
                    self.target_class, self.brush_size, mode='add'
                )
                self.correction_points = [(x, y)]
                self.update_display()
        elif self.correction_mode == 'lasso':
            self.lasso_points.append((x, y))
            self.update_display()

    def on_mouse_release(self, event):
        if not self.is_drawing:
            return
        
        self.is_drawing = False
        
        if self.correction_mode == 'lasso' and len(self.lasso_points) >= 3:
            self.save_history()
            self.current_mask = self.processor.apply_lasso_correction(
                self.current_mask, self.lasso_points, 
                self.target_class, mode='add'
            )
            self.lasso_points = []
            self.update_display()

    def on_key_press(self, event):
        if event.key == 'escape':
            self.correction_mode = None
            self.radio_correction.set_active(0)
            self.correction_points = []
            self.lasso_points = []
            self.update_display()
        elif event.key == 'ctrl+z':
            self.undo_correction(None)

    def save_history(self):
        if self.current_mask is not None:
            self.history.append(self.current_mask.copy())

    def undo_correction(self, event):
        if len(self.history) > 0:
            self.current_mask = self.history.pop()
            self.update_display()

    def apply_correction(self, event):
        if self.current_mask is None:
            return
        self.save_history()
        self.original_mask = self.current_mask.copy()
        self.process_and_update()

    def clear_correction(self, event):
        if self.original_mask is None:
            return
        self.save_history()
        self.current_mask = self.original_mask.copy()
        self.process_and_update()

    def load_ground_truth(self, event):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(
            title="加载真值分割图",
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if filepath:
            self.gt_mask = self.processor.load_segmentation(filepath)
            print(f"真值图已加载: {filepath}")
        root.destroy()

    def evaluate_quality(self, event):
        if self.current_mask is None:
            print("请先加载分割结果")
            return
        
        if self.gt_mask is None:
            print("警告: 未加载真值图，使用原始分割图作为参考")
            gt = self.original_mask
        else:
            gt = self.gt_mask
        
        metrics = self.processor.evaluate_segmentation(self.current_mask, gt)
        
        print("\n" + "=" * 50)
        print("分割质量评估结果")
        print("=" * 50)
        print(f"mIoU:           {metrics['mIoU']:.4f}")
        print(f"边界F-score:    {metrics['boundary_F_score']:.4f}")
        print(f"边界Precision:  {metrics['boundary_precision']:.4f}")
        print(f"边界Recall:     {metrics['boundary_recall']:.4f}")
        print("-" * 50)
        for i, iou in enumerate(metrics['per_class_IoU']):
            print(f"  类别 {i} IoU: {iou:.4f}")
        print("=" * 50 + "\n")
        
        fig, ax = plt.subplots(figsize=(8, 6))
        metrics_text = (
            f"分割质量评估\n\n"
            f"mIoU: {metrics['mIoU']:.4f}\n"
            f"边界F-score: {metrics['boundary_F_score']:.4f}\n"
            f"边界Precision: {metrics['boundary_precision']:.4f}\n"
            f"边界Recall: {metrics['boundary_recall']:.4f}\n\n"
            f"每类IoU:\n"
        )
        for i, iou in enumerate(metrics['per_class_IoU']):
            metrics_text += f"  类别 {i}: {iou:.4f}\n"
        
        ax.text(0.1, 0.5, metrics_text, transform=ax.transAxes, 
                fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax.axis('off')
        plt.tight_layout()
        plt.show()

    def load_video_dialog(self, event):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        input_dir = filedialog.askdirectory(title="选择视频帧目录")
        if not input_dir:
            root.destroy()
            return
        
        pattern = '*.png'
        self.video_masks, self.video_filenames = self.processor.load_video_masks(input_dir, pattern)
        self.current_frame_idx = 0
        
        self.slider_frame.valmax = len(self.video_masks) - 1
        self.slider_frame.ax.set_xlim(0, len(self.video_masks) - 1)
        
        self.original_mask = self.video_masks[0]
        self.current_mask = self.original_mask.copy()
        self.processor.num_classes = len(np.unique(self.original_mask))
        self.processor.class_colors = self.processor.generate_colors(self.processor.num_classes)
        
        self.process_and_update()
        print(f"已加载 {len(self.video_masks)} 帧视频")
        root.destroy()

    def process_video(self, event):
        if self.video_masks is None:
            print("请先加载视频帧")
            return
        
        print("开始处理视频...")
        video_config = {
            'temporal_window': self.config['temporal_window'],
            'temporal_alpha': self.config['temporal_alpha'],
            'use_optical_flow': self.config['use_optical_flow'],
            'per_frame_postprocess': True
        }
        
        self.video_masks = self.processor.process_video_masks(self.video_masks, video_config)
        self.current_mask = self.video_masks[self.current_frame_idx].copy()
        self.update_display()
        print("视频处理完成!")

    def save_video(self, event):
        if self.video_masks is None:
            print("请先处理视频")
            return
        
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if not output_dir:
            root.destroy()
            return
        
        self.processor.save_video_masks(self.video_masks, output_dir, self.video_filenames)
        print(f"视频帧已保存至: {output_dir}")
        root.destroy()

    def update_frame(self, val):
        if self.video_masks is None:
            return
        
        self.current_frame_idx = int(val)
        self.original_mask = self.video_masks[self.current_frame_idx]
        self.current_mask = self.original_mask.copy()
        self.update_display()

    def process_and_update(self):
        if self.original_mask is None:
            return
        
        self.current_mask = self.processor.process(self.original_mask, self.config)
        self.update_display()

    def update_display(self):
        if self.original_mask is None:
            return
        
        original_rgb = self.processor.mask_to_rgb(self.original_mask)
        processed_rgb = self.processor.mask_to_rgb(self.current_mask)
        
        diff = np.any(original_rgb != processed_rgb, axis=-1).astype(np.uint8) * 255
        diff_rgb = np.zeros_like(original_rgb)
        diff_rgb[:, :, 0] = diff
        
        correction_rgb = self.processor.mask_to_rgb(self.current_mask)
        
        self.ax_original.clear()
        self.ax_processed.clear()
        self.ax_correction.clear()
        self.ax_diff.clear()
        
        self.ax_original.imshow(original_rgb)
        title = '原始分割结果'
        if self.video_masks is not None:
            title += f' (帧 {self.current_frame_idx + 1}/{len(self.video_masks)})'
        self.ax_original.set_title(title, fontsize=11, fontweight='bold')
        self.ax_original.axis('off')
        
        self.ax_processed.imshow(processed_rgb)
        self.ax_processed.set_title('后处理结果', fontsize=11, fontweight='bold')
        self.ax_processed.axis('off')
        
        self.ax_correction.imshow(correction_rgb)
        correction_title = '交互式修正'
        if self.correction_mode:
            mode_names = {'brush': '画笔', 'lasso': '套索', 'fill': '填充'}
            correction_title += f' [{mode_names[self.correction_mode]}]'
        self.ax_correction.set_title(correction_title, fontsize=11, fontweight='bold')
        self.ax_correction.axis('off')
        
        if len(self.lasso_points) > 1:
            poly = np.array(self.lasso_points)
            self.ax_correction.plot(poly[:, 0], poly[:, 1], 'w-', linewidth=2, alpha=0.8)
            if len(self.lasso_points) > 2:
                self.ax_correction.fill(poly[:, 0], poly[:, 1], 'w', alpha=0.3)
        
        if len(self.correction_points) > 1:
            pts = np.array(self.correction_points)
            self.ax_correction.plot(pts[:, 0], pts[:, 1], 'y-', linewidth=self.brush_size, alpha=0.6)
        
        self.ax_diff.imshow(diff_rgb)
        self.ax_diff.set_title('差异对比 (红色区域)', fontsize=11, fontweight='bold')
        self.ax_diff.axis('off')
        
        self.fig.canvas.draw_idle()

    def show(self):
        plt.show()


def create_sample_segmentation(output_path='sample_segmentation.png'):
    size = 400
    mask = np.zeros((size, size), dtype=np.int32)
    
    cv2.circle(mask, (100, 100), 60, 1, -1)
    cv2.circle(mask, (100, 100), 20, 0, -1)
    
    cv2.rectangle(mask, (200, 50), (350, 180), 2, -1)
    cv2.rectangle(mask, (240, 80), (270, 120), 0, -1)
    cv2.rectangle(mask, (290, 100), (320, 140), 0, -1)
    
    cv2.ellipse(mask, (150, 300), (80, 50), 30, 0, 360, 3, -1)
    cv2.circle(mask, (150, 300), 25, 0, -1)
    
    for i in range(5):
        x = np.random.randint(50, 350)
        y = np.random.randint(200, 380)
        r = np.random.randint(3, 8)
        cv2.circle(mask, (x, y), r, 1, -1)
    
    for i in range(3):
        x = np.random.randint(50, 350)
        y = np.random.randint(50, 380)
        r = np.random.randint(2, 5)
        cv2.circle(mask, (x, y), r, 2, -1)
    
    processor = SegmentationPostProcessor()
    processor.num_classes = 4
    processor.class_colors = np.array([
        [0, 0, 0],
        [255, 100, 100],
        [100, 255, 100],
        [100, 100, 255]
    ], dtype=np.uint8)
    
    rgb = processor.mask_to_rgb(mask)
    cv2.imwrite(output_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    
    return output_path, processor


def main():
    print("=" * 60)
    print("图像语义分割后处理工具")
    print("=" * 60)
    
    sample_path, _ = create_sample_segmentation()
    print(f"已创建示例图像: {sample_path}")
    
    gui = PostProcessorGUI(sample_image_path=sample_path)
    print("\n启动交互界面...")
    print("操作说明:")
    print("  - 使用滑块调整各种后处理参数")
    print("  - 点击'加载图像'导入自定义分割结果")
    print("  - 点击'保存结果'导出处理后的图像")
    print("  - 点击'批量处理'处理整个目录")
    print("  - 点击'重置参数'恢复默认设置")
    print("=" * 60)
    
    gui.show()


if __name__ == '__main__':
    main()
