import os
import glob
import numpy as np
from PIL import Image
from phase_correlation import PhaseCorrelationRegistrator
from quality_metrics import RegistrationQualityEvaluator
import json
import csv


class BatchRegistrator:
    def __init__(self):
        self.registrator = PhaseCorrelationRegistrator()
        self.evaluator = RegistrationQualityEvaluator()
        self.results = []

    def load_image(self, filepath):
        img = Image.open(filepath)
        img_array = np.array(img)
        if len(img_array.shape) == 3:
            img_array = np.mean(img_array, axis=2)
        return img_array.astype(np.float32)

    def load_batch_from_directory(self, directory, pattern='*.png'):
        file_pattern = os.path.join(directory, pattern)
        file_paths = sorted(glob.glob(file_pattern))
        return file_paths

    def register_batch(self, ref_image_path, target_image_paths, output_dir=None):
        ref_img = self.load_image(ref_image_path)
        self.results = []

        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for idx, target_path in enumerate(target_image_paths):
            print(f"Processing image {idx + 1}/{len(target_image_paths)}: {os.path.basename(target_path)}")
            
            target_img = self.load_image(target_path)
            
            result = self.registrator.register(ref_img, target_img)
            
            quality = self.evaluator.evaluate_all(ref_img, result['transformed'])
            
            result_dict = {
                'index': idx,
                'reference': os.path.basename(ref_image_path),
                'target': os.path.basename(target_path),
                'translation_x': float(result['translation'][0]),
                'translation_y': float(result['translation'][1]),
                'rotation': float(result['rotation']),
                'scale': float(result['scale']),
                'quality': quality
            }
            self.results.append(result_dict)

            if output_dir:
                output_filename = f"registered_{idx:04d}_{os.path.basename(target_path)}"
                output_path = os.path.join(output_dir, output_filename)
                
                transformed_img = Image.fromarray(
                    np.clip(result['transformed'], 0, 255).astype(np.uint8)
                )
                transformed_img.save(output_path)

        return self.results

    def register_series(self, image_paths, output_dir=None):
        if len(image_paths) < 2:
            raise ValueError("At least 2 images required for series registration")

        self.results = []
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        ref_img = self.load_image(image_paths[0])
        
        if output_dir:
            output_filename = f"registered_0000_{os.path.basename(image_paths[0])}"
            output_path = os.path.join(output_dir, output_filename)
            Image.fromarray(ref_img.astype(np.uint8)).save(output_path)

        for idx in range(1, len(image_paths)):
            print(f"Processing image {idx}/{len(image_paths) - 1}: {os.path.basename(image_paths[idx])}")
            
            target_img = self.load_image(image_paths[idx])
            
            result = self.registrator.register(ref_img, target_img)
            
            quality = self.evaluator.evaluate_all(ref_img, result['transformed'])
            
            result_dict = {
                'index': idx,
                'reference': os.path.basename(image_paths[0]),
                'target': os.path.basename(image_paths[idx]),
                'translation_x': float(result['translation'][0]),
                'translation_y': float(result['translation'][1]),
                'rotation': float(result['rotation']),
                'scale': float(result['scale']),
                'quality': quality
            }
            self.results.append(result_dict)

            if output_dir:
                output_filename = f"registered_{idx:04d}_{os.path.basename(image_paths[idx])}"
                output_path = os.path.join(output_dir, output_filename)
                
                transformed_img = Image.fromarray(
                    np.clip(result['transformed'], 0, 255).astype(np.uint8)
                )
                transformed_img.save(output_path)

        return self.results

    def save_results_json(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {filepath}")

    def save_results_csv(self, filepath):
        if not self.results:
            print("No results to save")
            return

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            header = [
                'index', 'reference', 'target',
                'translation_x', 'translation_y', 'rotation', 'scale',
                'ncc', 'ssim', 'mse', 'rmse', 'psnr',
                'mutual_information', 'correlation_coefficient', 'gradient_similarity'
            ]
            writer.writerow(header)
            
            for result in self.results:
                row = [
                    result['index'],
                    result['reference'],
                    result['target'],
                    result['translation_x'],
                    result['translation_y'],
                    result['rotation'],
                    result['scale'],
                    result['quality']['ncc'],
                    result['quality']['ssim'],
                    result['quality']['mse'],
                    result['quality']['rmse'],
                    result['quality']['psnr'],
                    result['quality']['mutual_information'],
                    result['quality']['correlation_coefficient'],
                    result['quality']['gradient_similarity']
                ]
                writer.writerow(row)
        
        print(f"Results saved to {filepath}")

    def get_summary_statistics(self):
        if not self.results:
            return None

        translations_x = [r['translation_x'] for r in self.results]
        translations_y = [r['translation_y'] for r in self.results]
        rotations = [r['rotation'] for r in self.results]
        scales = [r['scale'] for r in self.results]
        ncc_values = [r['quality']['ncc'] for r in self.results]
        ssim_values = [r['quality']['ssim'] for r in self.results]

        return {
            'count': len(self.results),
            'translation_x': {
                'mean': np.mean(translations_x),
                'std': np.std(translations_x),
                'min': np.min(translations_x),
                'max': np.max(translations_x)
            },
            'translation_y': {
                'mean': np.mean(translations_y),
                'std': np.std(translations_y),
                'min': np.min(translations_y),
                'max': np.max(translations_y)
            },
            'rotation': {
                'mean': np.mean(rotations),
                'std': np.std(rotations),
                'min': np.min(rotations),
                'max': np.max(rotations)
            },
            'scale': {
                'mean': np.mean(scales),
                'std': np.std(scales),
                'min': np.min(scales),
                'max': np.max(scales)
            },
            'ncc': {
                'mean': np.mean(ncc_values),
                'std': np.std(ncc_values)
            },
            'ssim': {
                'mean': np.mean(ssim_values),
                'std': np.std(ssim_values)
            }
        }
