import os
import glob
import cv2
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm

from core.reflectance_remover import ReflectionRemover
from core.evaluator import Evaluator
from config import Config


class BatchProcessor:
    def __init__(self, config: Config, model_path: Optional[str] = None):
        self.config = config
        self.remover = ReflectionRemover(config, model_path)
        self.evaluator = Evaluator(config)
    
    def process_directory(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        polarization_dir: Optional[str] = None,
        ground_truth_dir: Optional[str] = None,
        file_extensions: List[str] = None
    ) -> Dict:
        if output_dir is None:
            output_dir = self.config.inference.output_dir
        
        if file_extensions is None:
            file_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = self._get_image_paths(input_dir, file_extensions)
        
        if len(image_paths) == 0:
            raise ValueError(f"No images found in {input_dir}")
        
        print(f"Found {len(image_paths)} images to process")
        
        all_results = []
        all_metrics = []
        
        for idx, img_path in enumerate(tqdm(image_paths, desc='Processing')):
            try:
                result = self._process_single_image(
                    img_path, output_dir, polarization_dir, ground_truth_dir
                )
                all_results.append(result)
                
                if ground_truth_dir and 'metrics' in result:
                    all_metrics.append(result['metrics'])
                
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                continue
        
        summary = self._generate_summary(all_metrics, output_dir)
        
        return {
            'results': all_results,
            'summary': summary,
            'total_processed': len(all_results),
            'total_failed': len(image_paths) - len(all_results)
        }
    
    def _process_single_image(
        self,
        img_path: str,
        output_dir: str,
        polarization_dir: Optional[str] = None,
        ground_truth_dir: Optional[str] = None
    ) -> Dict:
        filename = os.path.basename(img_path)
        name, ext = os.path.splitext(filename)
        
        image = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not load image: {img_path}")
        
        polarization_image = None
        if polarization_dir:
            pol_path = os.path.join(polarization_dir, filename)
            if os.path.exists(pol_path):
                polarization_image = cv2.imread(pol_path, cv2.IMREAD_COLOR)
        
        result = self.remover.remove_reflection(image, polarization_image)
        
        if self.config.inference.save_all_outputs:
            self._save_outputs(result, output_dir, name, ext)
        else:
            output_path = os.path.join(output_dir, f"{name}_transmission{ext}")
            cv2.imwrite(output_path, cv2.cvtColor(result['transmission'], cv2.COLOR_RGB2BGR))
        
        metrics = None
        if ground_truth_dir:
            gt_path = os.path.join(ground_truth_dir, filename)
            if os.path.exists(gt_path):
                ground_truth = cv2.imread(gt_path, cv2.IMREAD_COLOR)
                ground_truth = cv2.cvtColor(ground_truth, cv2.COLOR_BGR2RGB)
                metrics = self.evaluator.evaluate(result['transmission'], ground_truth, result['input'])
        
        result_dict = {
            'filename': filename,
            'input_path': img_path,
            'output_path': os.path.join(output_dir, f"{name}_transmission{ext}"),
            'metrics': metrics
        }
        
        return result_dict
    
    def _save_outputs(self, result: Dict[str, np.ndarray], output_dir: str, name: str, ext: str):
        subdirs = ['input', 'transmission', 'reflection', 'alpha']
        for subdir in subdirs:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
        
        for key, img in result.items():
            if key == 'alpha':
                output_path = os.path.join(output_dir, key, f"{name}_{key}{ext}")
                cv2.imwrite(output_path, img)
            else:
                output_path = os.path.join(output_dir, key, f"{name}_{key}{ext}")
                cv2.imwrite(output_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    
    def _get_image_paths(self, directory: str, extensions: List[str]) -> List[str]:
        image_paths = []
        for ext in extensions:
            image_paths.extend(glob.glob(os.path.join(directory, ext)))
            image_paths.extend(glob.glob(os.path.join(directory, ext.upper())))
        return sorted(image_paths)
    
    def _generate_summary(self, all_metrics: List[Dict], output_dir: str) -> Dict:
        if not all_metrics:
            return {}
        
        summary = {}
        metric_keys = all_metrics[0].keys()
        
        for key in metric_keys:
            values = [m[key] for m in all_metrics if key in m and m[key] is not None]
            if values:
                summary[key] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'median': float(np.median(values))
                }
        
        if self.config.eval.save_metrics:
            metrics_path = os.path.join(output_dir, 'metrics_summary.json')
            with open(metrics_path, 'w') as f:
                json.dump(summary, f, indent=4)
            print(f"Metrics summary saved to {metrics_path}")
        
        return summary
    
    def process_with_polarization(
        self,
        input_dir: str,
        polarization_dir: str,
        output_dir: Optional[str] = None,
        ground_truth_dir: Optional[str] = None
    ) -> Dict:
        self.config.model.use_polarization = True
        return self.process_directory(
            input_dir, output_dir, polarization_dir, ground_truth_dir
        )
