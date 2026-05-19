import numpy as np
import torch
from typing import Dict, List, Optional, Any


class Evaluator:
    def __init__(self, num_classes: int = 1):
        self.num_classes = num_classes
        self.reset()

    def reset(self):
        self.tp = 0
        self.fp = 0
        self.fn = 0
        self.tn = 0

    def add_batch(self, pred: np.ndarray, target: np.ndarray, threshold: float = 0.5, 
                  valid_mask: Optional[np.ndarray] = None):
        if isinstance(pred, torch.Tensor):
            pred = pred.cpu().numpy()
        if isinstance(target, torch.Tensor):
            target = target.cpu().numpy()
        if isinstance(valid_mask, torch.Tensor):
            valid_mask = valid_mask.cpu().numpy()
        
        if self.num_classes == 1:
            pred = (pred > threshold).astype(np.uint8)
            target = (target > 0).astype(np.uint8)
        else:
            pred = np.argmax(pred, axis=1)
            target = target.astype(np.uint8)
        
        if valid_mask is not None:
            valid_mask = valid_mask.astype(np.bool_)
            pred = pred[valid_mask]
            target = target[valid_mask]
        
        self.tp += np.sum((pred == 1) & (target == 1))
        self.fp += np.sum((pred == 1) & (target == 0))
        self.fn += np.sum((pred == 0) & (target == 1))
        self.tn += np.sum((pred == 0) & (target == 0))

    def compute_iou(self) -> float:
        intersection = self.tp
        union = self.tp + self.fp + self.fn
        return intersection / (union + 1e-8)

    def compute_precision(self) -> float:
        return self.tp / (self.tp + self.fp + 1e-8)

    def compute_recall(self) -> float:
        return self.tp / (self.tp + self.fn + 1e-8)

    def compute_f1(self) -> float:
        precision = self.compute_precision()
        recall = self.compute_recall()
        return 2 * precision * recall / (precision + recall + 1e-8)

    def compute_accuracy(self) -> float:
        total = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / (total + 1e-8)

    def compute_kappa(self) -> float:
        total = self.tp + self.tn + self.fp + self.fn
        po = (self.tp + self.tn) / (total + 1e-8)
        pe = ((self.tp + self.fp) * (self.tp + self.fn) + 
              (self.fn + self.tn) * (self.fp + self.tn)) / (total * total + 1e-8)
        return (po - pe) / (1 - pe + 1e-8)

    def get_metrics(self) -> Dict[str, float]:
        return {
            'IoU': self.compute_iou(),
            'Precision': self.compute_precision(),
            'Recall': self.compute_recall(),
            'F1': self.compute_f1(),
            'Accuracy': self.compute_accuracy(),
            'Kappa': self.compute_kappa()
        }


class PerClassEvaluator:
    def __init__(self, num_classes: int, class_names: Optional[List[str]] = None):
        self.num_classes = num_classes
        self.class_names = class_names or [f'class_{i}' for i in range(num_classes)]
        self.reset()

    def reset(self):
        self.confusion_matrix = np.zeros((self.num_classes, self.num_classes), dtype=np.int64)
        self.per_image_stats = []

    def add_batch(self, pred: np.ndarray, target: np.ndarray, threshold: float = 0.5,
                  valid_mask: Optional[np.ndarray] = None, image_ids: Optional[List[str]] = None):
        if isinstance(pred, torch.Tensor):
            pred = pred.cpu().numpy()
        if isinstance(target, torch.Tensor):
            target = target.cpu().numpy()
        if isinstance(valid_mask, torch.Tensor):
            valid_mask = valid_mask.cpu().numpy()
        
        batch_size = pred.shape[0] if len(pred.shape) > 3 else 1
        
        if self.num_classes == 1:
            pred = (pred > threshold).astype(np.uint8)
            target = (target > 0).astype(np.uint8)
            pred = pred.reshape(batch_size, -1)
            target = target.reshape(batch_size, -1)
        else:
            pred = np.argmax(pred, axis=1)
            target = target.astype(np.uint8).reshape(batch_size, -1)
            pred = pred.reshape(batch_size, -1)
        
        if valid_mask is not None:
            valid_mask = valid_mask.astype(np.bool_).reshape(batch_size, -1)
        else:
            valid_mask = np.ones_like(pred, dtype=np.bool_)
        
        for i in range(batch_size):
            p = pred[i][valid_mask[i]]
            t = target[i][valid_mask[i]]
            
            cm_image = np.zeros((self.num_classes, self.num_classes), dtype=np.int64)
            for p_cls in range(self.num_classes):
                for t_cls in range(self.num_classes):
                    cm_image[t_cls, p_cls] += np.sum((p == p_cls) & (t == t_cls))
            
            self.confusion_matrix += cm_image
            
            if image_ids and i < len(image_ids):
                image_metrics = self._compute_single_image_metrics(cm_image)
                image_metrics['image_id'] = image_ids[i]
                self.per_image_stats.append(image_metrics)

    def _compute_single_image_metrics(self, cm: np.ndarray) -> Dict[str, Any]:
        per_class_iou = []
        for i in range(self.num_classes):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            iou = tp / (tp + fp + fn + 1e-8)
            per_class_iou.append(iou)
        
        return {
            'per_class_iou': per_class_iou,
            'mIoU': np.mean(per_class_iou),
            'worst_class_idx': np.argmin(per_class_iou),
            'worst_class_iou': np.min(per_class_iou)
        }

    def get_class_metrics(self) -> Dict[str, Any]:
        per_class_iou = []
        per_class_precision = []
        per_class_recall = []
        per_class_f1 = []
        per_class_support = []
        
        for i in range(self.num_classes):
            tp = self.confusion_matrix[i, i]
            fp = self.confusion_matrix[:, i].sum() - tp
            fn = self.confusion_matrix[i, :].sum() - tp
            support = self.confusion_matrix[i, :].sum()
            
            iou = tp / (tp + fp + fn + 1e-8)
            precision = tp / (tp + fp + 1e-8)
            recall = tp / (tp + fn + 1e-8)
            f1 = 2 * precision * recall / (precision + recall + 1e-8)
            
            per_class_iou.append(iou)
            per_class_precision.append(precision)
            per_class_recall.append(recall)
            per_class_f1.append(f1)
            per_class_support.append(support)
        
        iou_threshold = 0.5
        poor_classes = [
            {
                'class_idx': i,
                'class_name': self.class_names[i],
                'IoU': per_class_iou[i],
                'Precision': per_class_precision[i],
                'Recall': per_class_recall[i],
                'F1': per_class_f1[i],
                'support': per_class_support[i]
            }
            for i in range(self.num_classes)
            if per_class_iou[i] < iou_threshold
        ]
        
        poor_classes.sort(key=lambda x: x['IoU'])
        
        return {
            'confusion_matrix': self.confusion_matrix.tolist(),
            'class_names': self.class_names,
            'per_class_iou': per_class_iou,
            'per_class_precision': per_class_precision,
            'per_class_recall': per_class_recall,
            'per_class_f1': per_class_f1,
            'per_class_support': per_class_support,
            'mIoU': np.mean(per_class_iou),
            'mPrecision': np.mean(per_class_precision),
            'mRecall': np.mean(per_class_recall),
            'mF1': np.mean(per_class_f1),
            'worst_classes': poor_classes,
            'worst_class_idx': np.argmin(per_class_iou),
            'worst_class_name': self.class_names[np.argmin(per_class_iou)],
            'worst_class_iou': np.min(per_class_iou)
        }

    def get_worst_images(self, top_k: int = 10) -> List[Dict[str, Any]]:
        sorted_images = sorted(self.per_image_stats, key=lambda x: x['mIoU'])
        return sorted_images[:top_k]

    def print_summary(self):
        metrics = self.get_class_metrics()
        
        print("\n" + "=" * 80)
        print("PER-CLASS EVALUATION SUMMARY")
        print("=" * 80)
        
        print(f"\n{'Class':<20} {'IoU':<10} {'Precision':<12} {'Recall':<10} {'F1':<10} {'Support':<10}")
        print("-" * 80)
        
        for i, name in enumerate(metrics['class_names']):
            print(f"{name:<20} {metrics['per_class_iou'][i]:<10.4f} "
                  f"{metrics['per_class_precision'][i]:<12.4f} "
                  f"{metrics['per_class_recall'][i]:<10.4f} "
                  f"{metrics['per_class_f1'][i]:<10.4f} "
                  f"{metrics['per_class_support'][i]:<10}")
        
        print("-" * 80)
        print(f"{'Mean':<20} {metrics['mIoU']:<10.4f} "
              f"{metrics['mPrecision']:<12.4f} "
              f"{metrics['mRecall']:<10.4f} "
              f"{metrics['mF1']:<10.4f}")
        
        print("\n" + "-" * 80)
        print("CLASSES WITH LOW IoU (< 0.5):")
        print("-" * 80)
        
        if metrics['worst_classes']:
            for cls in metrics['worst_classes']:
                print(f"  {cls['class_name']}: IoU = {cls['IoU']:.4f}, "
                      f"Support = {cls['support']}, Issues: Low IoU")
        else:
            print("  All classes have IoU >= 0.5!")
        
        print("\n" + "=" * 80 + "\n")


def compute_confusion_matrix(pred: np.ndarray, target: np.ndarray, 
                             num_classes: int = 1, threshold: float = 0.5) -> np.ndarray:
    if isinstance(pred, torch.Tensor):
        pred = pred.cpu().numpy()
    if isinstance(target, torch.Tensor):
        target = target.cpu().numpy()
    if num_classes == 1:
        pred = (pred > threshold).astype(np.uint8).flatten()
        target = (target > 0).astype(np.uint8).flatten()
        num_classes = 2
    else:
        pred = np.argmax(pred, axis=1).flatten()
        target = target.flatten()
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for p, t in zip(pred, target):
        cm[t, p] += 1
    return cm


def compute_class_metrics(cm: np.ndarray) -> Dict[str, List[float]]:
    num_classes = cm.shape[0]
    ious = []
    precisions = []
    recalls = []
    f1s = []
    for i in range(num_classes):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        iou = tp / (tp + fp + fn + 1e-8)
        precision = tp / (tp + fp + 1e-8)
        recall = tp / (tp + fn + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        ious.append(iou)
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
    return {
        'IoU': ious,
        'Precision': precisions,
        'Recall': recalls,
        'F1': f1s,
        'mIoU': np.mean(ious),
        'mF1': np.mean(f1s)
    }
