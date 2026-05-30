import os
import numpy as np
from tqdm import tqdm
from config import Config
from data.loader import get_inference_dataloader
from data.transforms import postprocess_batch
from utils.helpers import get_file_list, save_image, generate_output_filename
from .post_processing import (
    postprocess_saliency_map,
    segment_salient_object,
    overlay_saliency,
    apply_mask,
    get_saliency_stats
)


class BatchProcessor:
    def __init__(self, inferencer):
        self.inferencer = inferencer
    
    def process_directory(self, input_dir, output_dir=None, batch_size=None, 
                          threshold=None, edge_refinement=True,
                          refine_method='guided',
                          use_dynamic_batch=True,
                          save_maps=True, save_masks=True, save_segmented=False,
                          save_overlay=False, format='png'):
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        if batch_size is None:
            batch_size = Config.BATCH_SIZE
        if threshold is None:
            threshold = Config.THRESHOLD
        
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = get_file_list(input_dir)
        if not image_paths:
            raise ValueError(f"No images found in directory: {input_dir}")
        
        print(f"Processing {len(image_paths)} images...")
        print(f"Dynamic batch: {'ON' if use_dynamic_batch else 'OFF'}")
        print(f"Refine method: {refine_method}")
        
        if use_dynamic_batch:
            return self._process_directory_dynamic(
                image_paths, output_dir, threshold, edge_refinement,
                refine_method, save_maps, save_masks, save_segmented,
                save_overlay, format
            )
        else:
            return self._process_directory_fixed(
                image_paths, output_dir, batch_size, threshold, edge_refinement,
                refine_method, save_maps, save_masks, save_segmented,
                save_overlay, format
            )
    
    def _process_directory_fixed(self, image_paths, output_dir, batch_size, threshold,
                                  edge_refinement, refine_method, save_maps, save_masks,
                                  save_segmented, save_overlay, format):
        dataloader = get_inference_dataloader(os.path.dirname(image_paths[0]), batch_size=batch_size)
        
        results = []
        
        with tqdm(total=len(image_paths), desc="Processing images") as pbar:
            for batch in dataloader:
                tensors = batch['tensor'].to(self.inferencer.device)
                original_sizes = batch['original_size']
                image_paths_batch = batch['image_path']
                filenames = batch['filename']
                
                with torch.no_grad():
                    outputs = self.inferencer._inference(tensors)
                
                batch_results = postprocess_batch(outputs, original_sizes, threshold)
                
                if edge_refinement and Config.EDGE_THINNING:
                    for i in range(len(batch_results)):
                        original_image = cv2.imread(image_paths_batch[i], cv2.IMREAD_COLOR)
                        original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
                        
                        refined_saliency, refined_mask = postprocess_saliency_map(
                            batch_results[i]['saliency_map'],
                            batch_results[i]['binary_mask'],
                            threshold=threshold,
                            refine_method=refine_method,
                            original_image=original_image
                        )
                        batch_results[i]['saliency_map'] = refined_saliency
                        batch_results[i]['binary_mask'] = refined_mask
                
                for i in range(len(batch_results)):
                    result = batch_results[i]
                    image_path = image_paths_batch[i]
                    filename = filenames[i]
                    name, _ = os.path.splitext(filename)
                    
                    result['image_path'] = image_path
                    result['filename'] = filename
                    
                    original_image = cv2.imread(image_path, cv2.IMREAD_COLOR)
                    original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
                    result['original_image'] = original_image
                    
                    if save_maps:
                        saliency_path = os.path.join(output_dir, f'{name}_saliency.{format}')
                        save_image((result['saliency_map'] * 255).astype(np.uint8), saliency_path)
                        result['saliency_path'] = saliency_path
                    
                    if save_masks:
                        mask_path = os.path.join(output_dir, f'{name}_mask.{format}')
                        save_image((result['binary_mask'] * 255).astype(np.uint8), mask_path)
                        result['mask_path'] = mask_path
                    
                    if save_segmented:
                        seg_result = segment_salient_object(
                            original_image,
                            result['saliency_map'],
                            result['binary_mask']
                        )
                        segmented_path = os.path.join(output_dir, f'{name}_segmented.{format}')
                        save_image(seg_result['segmented_rgb'], segmented_path)
                        result['segmented_path'] = segmented_path
                        result['segmentation'] = seg_result
                    
                    if save_overlay:
                        overlay = overlay_saliency(original_image, result['saliency_map'])
                        overlay_path = os.path.join(output_dir, f'{name}_overlay.{format}')
                        save_image(overlay, overlay_path)
                        result['overlay_path'] = overlay_path
                    
                    result['stats'] = get_saliency_stats(result['saliency_map'], result['binary_mask'])
                    
                    results.append(result)
                
                pbar.update(len(batch_results))
        
        return {
            'total_images': len(results),
            'output_dir': output_dir,
            'results': results
        }
    
    def _process_directory_dynamic(self, image_paths, output_dir, threshold,
                                    edge_refinement, refine_method, save_maps, save_masks,
                                    save_segmented, save_overlay, format):
        from .dynamic_batch import DynamicBatchProcessor
        
        def process_batch(batch_paths):
            batch_results = self.inferencer.predict_batch(
                batch_paths,
                threshold=threshold,
                edge_refinement=edge_refinement,
                refine_method=refine_method,
                dynamic_batch=False
            )
            
            for result, image_path in zip(batch_results, batch_paths):
                filename = os.path.basename(image_path)
                name, _ = os.path.splitext(filename)
                original_image = result['original_image']
                
                result['image_path'] = image_path
                result['filename'] = filename
                
                if save_maps:
                    saliency_path = os.path.join(output_dir, f'{name}_saliency.{format}')
                    save_image((result['saliency_map'] * 255).astype(np.uint8), saliency_path)
                    result['saliency_path'] = saliency_path
                
                if save_masks:
                    mask_path = os.path.join(output_dir, f'{name}_mask.{format}')
                    save_image((result['binary_mask'] * 255).astype(np.uint8), mask_path)
                    result['mask_path'] = mask_path
                
                if save_segmented:
                    seg_result = segment_salient_object(
                        original_image,
                        result['saliency_map'],
                        result['binary_mask']
                    )
                    segmented_path = os.path.join(output_dir, f'{name}_segmented.{format}')
                    save_image(seg_result['segmented_rgb'], segmented_path)
                    result['segmented_path'] = segmented_path
                    result['segmentation'] = seg_result
                
                if save_overlay:
                    overlay = overlay_saliency(original_image, result['saliency_map'])
                    overlay_path = os.path.join(output_dir, f'{name}_overlay.{format}')
                    save_image(overlay, overlay_path)
                    result['overlay_path'] = overlay_path
                
                result['stats'] = get_saliency_stats(result['saliency_map'], result['binary_mask'])
            
            return batch_results
        
        processor = DynamicBatchProcessor(
            process_func=process_batch,
            initial_batch_size=Config.BATCH_SIZE,
            min_batch_size=1,
            max_batch_size=Config.MAX_BATCH_SIZE
        )
        
        results = processor.process(image_paths, show_progress=True)
        
        flat_results = []
        for batch_result in results:
            if batch_result is not None:
                if isinstance(batch_result, list):
                    flat_results.extend(batch_result)
                else:
                    flat_results.append(batch_result)
        
        stats = processor.get_stats()
        batch_history = processor.get_batch_size_history()
        
        print(f"\nDynamic Batch Summary:")
        print(f"  Average batch size: {sum(batch_history) / len(batch_history):.1f}")
        print(f"  Batch size range: {min(batch_history)} - {max(batch_history)}")
        print(f"  Total time: {stats.total_time:.2f}s")
        print(f"  Avg time per image: {stats.avg_time_per_item * 1000:.1f}ms")
        
        return {
            'total_images': len(flat_results),
            'output_dir': output_dir,
            'results': flat_results,
            'dynamic_stats': {
                'total_time': stats.total_time,
                'avg_time_per_item': stats.avg_time_per_item,
                'batch_size_history': batch_history,
                'peak_memory': stats.memory_peak
            }
        }
    
    def process_list(self, image_paths, output_dir=None, batch_size=None,
                     threshold=None, edge_refinement=True,
                     refine_method='guided', use_dynamic_batch=True,
                     save_maps=True, save_masks=True, format='png'):
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        if batch_size is None:
            batch_size = Config.BATCH_SIZE
        if threshold is None:
            threshold = Config.THRESHOLD
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Processing {len(image_paths)} images...")
        print(f"Dynamic batch: {'ON' if use_dynamic_batch else 'OFF'}")
        print(f"Refine method: {refine_method}")
        
        if use_dynamic_batch:
            from .dynamic_batch import DynamicBatchProcessor
            
            def process_batch(batch_paths):
                return self.inferencer.predict_batch(
                    batch_paths,
                    threshold=threshold,
                    edge_refinement=edge_refinement,
                    refine_method=refine_method,
                    dynamic_batch=False
                )
            
            processor = DynamicBatchProcessor(
                process_func=process_batch,
                initial_batch_size=batch_size,
                min_batch_size=1,
                max_batch_size=Config.MAX_BATCH_SIZE
            )
            
            batch_results_list = processor.process(image_paths, show_progress=True)
            
            results = []
            for batch_results in batch_results_list:
                if batch_results is None:
                    continue
                if isinstance(batch_results, list):
                    for result, image_path in zip(batch_results, image_paths):
                        if result is not None:
                            results.append(self._save_result(result, image_path, output_dir, 
                                                          save_maps, save_masks, format))
                else:
                    idx = len(results)
                    if idx < len(image_paths) and batch_results is not None:
                        results.append(self._save_result(batch_results, image_paths[idx], 
                                                      output_dir, save_maps, save_masks, format))
        else:
            results = []
            for i in tqdm(range(0, len(image_paths), batch_size), desc="Processing batches"):
                batch_paths = image_paths[i:i + batch_size]
                batch_results = self.inferencer.predict_batch(
                    batch_paths,
                    threshold=threshold,
                    edge_refinement=edge_refinement,
                    refine_method=refine_method,
                    dynamic_batch=False
                )
                
                for j, result in enumerate(batch_results):
                    if result is not None:
                        image_path = batch_paths[j]
                        results.append(self._save_result(result, image_path, output_dir,
                                                      save_maps, save_masks, format))
        
        return {
            'total_images': len(results),
            'output_dir': output_dir,
            'results': results
        }
    
    def _save_result(self, result, image_path, output_dir, save_maps, save_masks, format):
        filename = os.path.basename(image_path)
        name, _ = os.path.splitext(filename)
        
        result['image_path'] = image_path
        result['filename'] = filename
        
        if save_maps:
            saliency_path = os.path.join(output_dir, f'{name}_saliency.{format}')
            save_image((result['saliency_map'] * 255).astype(np.uint8), saliency_path)
            result['saliency_path'] = saliency_path
        
        if save_masks:
            mask_path = os.path.join(output_dir, f'{name}_mask.{format}')
            save_image((result['binary_mask'] * 255).astype(np.uint8), mask_path)
            result['mask_path'] = mask_path
        
        result['stats'] = get_saliency_stats(result['saliency_map'], result['binary_mask'])
        return result
    
    def process_with_custom_function(self, input_dir, output_dir=None, 
                                      custom_func=None, **kwargs):
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        
        batch_result = self.process_directory(
            input_dir,
            output_dir=output_dir,
            **kwargs
        )
        
        if custom_func is not None:
            for result in batch_result['results']:
                custom_func(result, output_dir)
        
        return batch_result
    
    def generate_comparison_grid(self, input_dir, output_dir=None, 
                                  num_samples=5, cols=4):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = get_file_list(input_dir)[:num_samples]
        results = self.inferencer.predict_batch(image_paths)
        
        rows = len(results)
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4))
        
        if rows == 1:
            axes = axes.reshape(1, -1)
        
        for i, result in enumerate(results):
            original = result['original_image']
            saliency = result['saliency_map']
            mask = result['binary_mask']
            
            overlay = overlay_saliency(original, saliency)
            segmented = apply_mask(original, mask)
            
            axes[i, 0].imshow(original)
            axes[i, 0].set_title('Original')
            axes[i, 0].axis('off')
            
            axes[i, 1].imshow(saliency, cmap='gray')
            axes[i, 1].set_title('Saliency Map')
            axes[i, 1].axis('off')
            
            axes[i, 2].imshow(mask, cmap='gray')
            axes[i, 2].set_title('Binary Mask')
            axes[i, 2].axis('off')
            
            axes[i, 3].imshow(overlay)
            axes[i, 3].set_title('Overlay')
            axes[i, 3].axis('off')
        
        plt.tight_layout()
        grid_path = os.path.join(output_dir, 'comparison_grid.png')
        plt.savefig(grid_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        return grid_path


import torch
import cv2
