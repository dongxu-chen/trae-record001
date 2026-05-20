import torch
import torch.nn as nn
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict
from abc import ABC, abstractmethod


class QueryStrategy(ABC):
    @abstractmethod
    def __call__(self, predictions: torch.Tensor) -> np.ndarray:
        pass


class EntropySampling(QueryStrategy):
    def __call__(self, predictions: torch.Tensor) -> np.ndarray:
        if predictions.shape[1] == 1:
            p = torch.sigmoid(predictions)
            entropy = - (p * torch.log(p + 1e-8) + (1 - p) * torch.log(1 - p + 1e-8))
        else:
            p = torch.softmax(predictions, dim=1)
            entropy = -torch.sum(p * torch.log(p + 1e-8), dim=1)
        
        uncertainty = entropy.mean(dim=(1, 2)).cpu().numpy()
        return uncertainty


class MarginSampling(QueryStrategy):
    def __call__(self, predictions: torch.Tensor) -> np.ndarray:
        if predictions.shape[1] == 1:
            p = torch.sigmoid(predictions)
            margin = torch.abs(2 * p - 1)
            uncertainty = 1 - margin.mean(dim=(1, 2)).cpu().numpy()
        else:
            p = torch.softmax(predictions, dim=1)
            sorted_p, _ = torch.sort(p, dim=1, descending=True)
            margin = sorted_p[:, 0] - sorted_p[:, 1]
            uncertainty = 1 - margin.mean(dim=(1, 2)).cpu().numpy()
        return uncertainty


class LeastConfidence(QueryStrategy):
    def __call__(self, predictions: torch.Tensor) -> np.ndarray:
        if predictions.shape[1] == 1:
            p = torch.sigmoid(predictions)
            confidence = torch.max(p, 1 - p)
            uncertainty = 1 - confidence.mean(dim=(1, 2)).cpu().numpy()
        else:
            p = torch.softmax(predictions, dim=1)
            confidence, _ = torch.max(p, dim=1)
            uncertainty = 1 - confidence.mean(dim=(1, 2)).cpu().numpy()
        return uncertainty


class VariationRatio(QueryStrategy):
    def __call__(self, predictions: torch.Tensor) -> np.ndarray:
        if predictions.shape[1] == 1:
            p = torch.sigmoid(predictions)
            mode_pred = (p > 0.5).float()
            confidence = torch.where(mode_pred == 1, p, 1 - p)
            ratio = 1 - confidence.mean(dim=(1, 2)).cpu().numpy()
        else:
            p = torch.softmax(predictions, dim=1)
            confidence, _ = torch.max(p, dim=1)
            ratio = 1 - confidence.mean(dim=(1, 2)).cpu().numpy()
        return ratio


class BALDDropout(QueryStrategy):
    def __init__(self, n_passes: int = 10):
        self.n_passes = n_passes
    
    def __call__(self, model: nn.Module, x: torch.Tensor) -> np.ndarray:
        model.train()
        predictions = []
        
        with torch.no_grad():
            for _ in range(self.n_passes):
                pred = model(x)
                if pred.shape[1] == 1:
                    pred = torch.sigmoid(pred)
                else:
                    pred = torch.softmax(pred, dim=1)
                predictions.append(pred)
        
        predictions = torch.stack(predictions, dim=0)
        mean_pred = predictions.mean(dim=0)
        
        if mean_pred.shape[1] == 1:
            entropy = - (mean_pred * torch.log(mean_pred + 1e-8) + 
                        (1 - mean_pred) * torch.log(1 - mean_pred + 1e-8))
        else:
            entropy = -torch.sum(mean_pred * torch.log(mean_pred + 1e-8), dim=1)
        
        expected_entropy = -torch.mean(
            torch.sum(predictions * torch.log(predictions + 1e-8), dim=1),
            dim=0
        )
        
        bald = entropy - expected_entropy
        uncertainty = bald.mean(dim=(1, 2)).cpu().numpy()
        
        return uncertainty


class PseudoLabeler:
    def __init__(self,
                 model: nn.Module,
                 device: Optional[torch.device] = None,
                 strategy: str = 'entropy',
                 confidence_threshold: float = 0.9,
                 num_passes: int = 10):
        self.model = model
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.model.eval()
        self.confidence_threshold = confidence_threshold
        
        self.strategies = {
            'entropy': EntropySampling(),
            'margin': MarginSampling(),
            'least_confidence': LeastConfidence(),
            'variation_ratio': VariationRatio(),
            'bald': BALDDropout(num_passes)
        }
        self.strategy = self.strategies[strategy]
    
    @torch.no_grad()
    def generate_pseudo_labels(self,
                               image1: torch.Tensor,
                               image2: torch.Tensor,
                               return_uncertainty: bool = False) -> Tuple[torch.Tensor, Optional[np.ndarray]]:
        x = torch.cat([image1, image2], dim=1).to(self.device)
        logits = self.model(x)
        
        if logits.shape[1] == 1:
            pseudo_probs = torch.sigmoid(logits)
            pseudo_labels = (pseudo_probs > 0.5).float()
            confidence = torch.max(pseudo_probs, 1 - pseudo_probs)
        else:
            pseudo_probs = torch.softmax(logits, dim=1)
            pseudo_labels = torch.argmax(pseudo_probs, dim=1, keepdim=True).float()
            confidence, _ = torch.max(pseudo_probs, dim=1, keepdim=True)
        
        confidence_mask = (confidence >= self.confidence_threshold).float()
        pseudo_labels = pseudo_labels * confidence_mask
        
        if return_uncertainty:
            if isinstance(self.strategy, BALDDropout):
                uncertainty = self.strategy(self.model, x)
            else:
                uncertainty = self.strategy(logits)
            return pseudo_labels, uncertainty
        
        return pseudo_labels, None
    
    def select_uncertain_samples(self,
                                image_list: List[Tuple[torch.Tensor, torch.Tensor]],
                                num_samples: int = 10) -> List[int]:
        uncertainties = []
        
        for i, (img1, img2) in enumerate(image_list):
            _, unc = self.generate_pseudo_labels(
                img1.unsqueeze(0), img2.unsqueeze(0), return_uncertainty=True
            )
            uncertainties.append((i, unc[0] if unc is not None else 0))
        
        uncertainties.sort(key=lambda x: x[1], reverse=True)
        selected_indices = [idx for idx, _ in uncertainties[:num_samples]]
        
        return selected_indices
    
    def refine_pseudo_labels(self,
                            pseudo_labels: torch.Tensor,
                            original_image: np.ndarray,
                            min_area: int = 100,
                            use_morphology: bool = True) -> np.ndarray:
        pseudo_np = pseudo_labels.squeeze().cpu().numpy().astype(np.uint8)
        
        if use_morphology:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            pseudo_np = cv2.morphologyEx(pseudo_np, cv2.MORPH_OPEN, kernel)
            pseudo_np = cv2.morphologyEx(pseudo_np, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(pseudo_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        refined = np.zeros_like(pseudo_np)
        
        for cnt in contours:
            if cv2.contourArea(cnt) >= min_area:
                cv2.drawContours(refined, [cnt], -1, 1, -1)
        
        return refined
    
    def save_pseudo_label(self, pseudo_label: np.ndarray, path: str, as_image: bool = True):
        if as_image:
            cv2.imwrite(path, (pseudo_label * 255).astype(np.uint8))
        else:
            np.save(path, pseudo_label)


class ActiveLearningManager:
    def __init__(self,
                 model: nn.Module,
                 labeled_dataset,
                 unlabeled_dataset,
                 device: Optional[torch.device] = None,
                 strategy: str = 'entropy'):
        self.model = model
        self.labeled_dataset = labeled_dataset
        self.unlabeled_dataset = unlabeled_dataset
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.labeler = PseudoLabeler(model, device, strategy)
        self.labeled_indices = set()
    
    def query_and_label(self,
                       num_samples: int = 10,
                       min_confidence: float = 0.8) -> Dict:
        image_pairs = []
        for i in range(len(self.unlabeled_dataset)):
            if i not in self.labeled_indices:
                img1, img2 = self.unlabeled_dataset[i][:2]
                image_pairs.append((img1, img2))
        
        selected_indices = self.labeler.select_uncertain_samples(image_pairs, num_samples)
        
        new_labels = []
        actual_selected = []
        
        for idx in selected_indices:
            if idx not in self.labeled_indices:
                img1, img2 = image_pairs[idx]
                pseudo_label, _ = self.labeler.generate_pseudo_labels(
                    img1.unsqueeze(0), img2.unsqueeze(0)
                )
                
                confidence = pseudo_label.float().mean().item()
                if confidence >= min_confidence:
                    refined_label = self.labeler.refine_pseudo_labels(pseudo_label)
                    new_labels.append({
                        'index': idx,
                        'image1': img1,
                        'image2': img2,
                        'pseudo_label': refined_label,
                        'confidence': confidence
                    })
                    self.labeled_indices.add(idx)
                    actual_selected.append(idx)
        
        return {
            'selected_indices': actual_selected,
            'new_labels': new_labels,
            'total_labeled': len(self.labeled_indices)
        }
    
    def get_training_stats(self) -> Dict:
        return {
            'labeled_count': len(self.labeled_indices),
            'unlabeled_count': len(self.unlabeled_dataset) - len(self.labeled_indices),
            'label_ratio': len(self.labeled_indices) / max(len(self.unlabeled_dataset), 1)
        }
