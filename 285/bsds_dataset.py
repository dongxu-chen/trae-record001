import os
import glob
import cv2
import numpy as np
import scipy.io as sio


class BSDS500:
    def __init__(self, root_dir='BSDS500'):
        self.root_dir = root_dir
        self.images_dir = os.path.join(root_dir, 'images')
        self.ground_truth_dir = os.path.join(root_dir, 'groundTruth')
        
    def load_image(self, image_id, split='val'):
        image_path = os.path.join(self.images_dir, split, f'{image_id}.jpg')
        if not os.path.exists(image_path):
            image_path = os.path.join(self.images_dir, split, f'{image_id}.png')
        return cv2.imread(image_path)
    
    def load_ground_truth(self, image_id, split='val'):
        gt_path = os.path.join(self.ground_truth_dir, split, f'{image_id}.mat')
        if os.path.exists(gt_path):
            mat_data = sio.loadmat(gt_path)
            gt_segmentations = mat_data['groundTruth'][0]
            boundaries = []
            for seg in gt_segmentations:
                boundaries.append(seg[0][0][1])
            return np.stack(boundaries, axis=0)
        else:
            gt_path_png = os.path.join(self.ground_truth_dir, split, f'{image_id}.png')
            if os.path.exists(gt_path_png):
                gt = cv2.imread(gt_path_png, cv2.IMREAD_GRAYSCALE)
                return gt[np.newaxis, ...]
        return None
    
    def get_image_ids(self, split='val'):
        image_dir = os.path.join(self.images_dir, split)
        if not os.path.exists(image_dir):
            return []
        image_files = glob.glob(os.path.join(image_dir, '*.jpg')) + \
                      glob.glob(os.path.join(image_dir, '*.png'))
        return sorted([os.path.splitext(os.path.basename(f))[0] for f in image_files])
    
    def get_all_splits(self):
        splits = []
        if os.path.exists(self.images_dir):
            splits = [d for d in os.listdir(self.images_dir) 
                     if os.path.isdir(os.path.join(self.images_dir, d))]
        return splits
    
    def create_synthetic_bsds(self, output_dir='BSDS500', num_images=10):
        os.makedirs(output_dir, exist_ok=True)
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(output_dir, 'images', split), exist_ok=True)
            os.makedirs(os.path.join(output_dir, 'groundTruth', split), exist_ok=True)
        
        image_ids = []
        for i in range(num_images):
            img_id = f'syn_{i:04d}'
            image_ids.append(img_id)
            
            for split in ['train', 'val', 'test']:
                if split == 'train' and i < int(num_images * 0.6):
                    pass
                elif split == 'val' and int(num_images * 0.6) <= i < int(num_images * 0.8):
                    pass
                elif split == 'test' and i >= int(num_images * 0.8):
                    pass
                else:
                    continue
                
                size = np.random.randint(300, 500)
                image = np.ones((size, size, 3), dtype=np.uint8) * 240
                
                num_shapes = np.random.randint(3, 8)
                gt = np.zeros((size, size), dtype=np.uint8)
                
                for _ in range(num_shapes):
                    shape_type = np.random.choice(['rect', 'circle', 'line'])
                    color = np.random.randint(30, 100)
                    
                    if shape_type == 'rect':
                        x1, y1 = np.random.randint(20, size-100, 2)
                        w, h = np.random.randint(50, 150, 2)
                        x2, y2 = x1 + w, y1 + h
                        cv2.rectangle(image, (x1, y1), (x2, y2), (color, color, color), 2)
                        cv2.rectangle(gt, (x1, y1), (x2, y2), 1, 2)
                    
                    elif shape_type == 'circle':
                        cx, cy = np.random.randint(50, size-50, 2)
                        r = np.random.randint(30, 80)
                        cv2.circle(image, (cx, cy), r, (color, color, color), 2)
                        cv2.circle(gt, (cx, cy), r, 1, 2)
                    
                    elif shape_type == 'line':
                        x1, y1 = np.random.randint(20, size-20, 2)
                        x2, y2 = np.random.randint(20, size-20, 2)
                        cv2.line(image, (x1, y1), (x2, y2), (color, color, color), 2)
                        cv2.line(gt, (x1, y1), (x2, y2), 1, 2)
                
                image = cv2.GaussianBlur(image, (3, 3), 0.5)
                noise = np.random.normal(0, 5, image.shape).astype(np.int16)
                image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                
                cv2.imwrite(os.path.join(output_dir, 'images', split, f'{img_id}.jpg'), image)
                cv2.imwrite(os.path.join(output_dir, 'groundTruth', split, f'{img_id}.png'), gt * 255)
        
        print(f"合成BSDS500风格数据集已创建: {output_dir}")
        print(f"包含 {num_images} 张图片，分布在 train/val/test 中")
        return output_dir

    def check_dataset(self):
        print("=" * 60)
        print("BSDS500 数据集检查")
        print("=" * 60)
        
        if not os.path.exists(self.root_dir):
            print(f"数据集目录不存在: {self.root_dir}")
            return False
        
        splits = self.get_all_splits()
        if not splits:
            print("未找到任何数据分割目录")
            return False
        
        total_images = 0
        for split in splits:
            image_ids = self.get_image_ids(split)
            print(f"  {split:>6}: {len(image_ids)} 张图片")
            total_images += len(image_ids)
        
        print(f"\n总计: {total_images} 张图片")
        return total_images > 0


class BSDSMetrics:
    @staticmethod
    def boundary_detection_ods(pred, gts, threshold=None):
        if threshold is not None:
            pred_binary = (pred > threshold).astype(np.float64)
        else:
            pred_binary = pred.astype(np.float64)
        
        best_f1 = 0
        best_precision = 0
        best_recall = 0
        
        for gt in gts:
            gt_binary = (gt > 0.1).astype(np.float64)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            gt_dilated = cv2.dilate(gt_binary, kernel)
            
            tp = np.sum(pred_binary * gt_dilated)
            fp = np.sum(pred_binary * (1 - gt_dilated))
            fn = np.sum(gt_binary * (1 - cv2.dilate(pred_binary, kernel)))
            
            precision = tp / (tp + fp + 1e-10)
            recall = tp / (tp + fn + 1e-10)
            f1 = 2 * precision * recall / (precision + recall + 1e-10)
            
            if f1 > best_f1:
                best_f1 = f1
                best_precision = precision
                best_recall = recall
        
        return {
            'precision': best_precision,
            'recall': best_recall,
            'f1': best_f1
        }
    
    @staticmethod
    def compute_bsds_metrics(pred_edges, gt_boundaries, tolerance=2):
        pred = pred_edges.astype(np.float64) / 255.0
        
        if gt_boundaries.ndim == 2:
            gt_boundaries = gt_boundaries[np.newaxis, ...]
        
        gts = []
        for gt in gt_boundaries:
            gt_norm = gt.astype(np.float64)
            if gt_norm.max() > 1:
                gt_norm = gt_norm / 255.0
            gts.append(gt_norm)
        
        return BSDSMetrics.boundary_detection_ods(pred, gts)
    
    @staticmethod
    def accumulate_metrics(metrics_list):
        if not metrics_list:
            return {}
        
        avg_precision = np.mean([m['precision'] for m in metrics_list])
        avg_recall = np.mean([m['recall'] for m in metrics_list])
        avg_f1 = np.mean([m['f1'] for m in metrics_list])
        
        return {
            'avg_precision': avg_precision,
            'avg_recall': avg_recall,
            'avg_f1': avg_f1,
            'num_images': len(metrics_list)
        }
