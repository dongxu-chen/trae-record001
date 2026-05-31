import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
from scipy.ndimage import gaussian_filter1d
import threading


class ClassActivationMapping:
    def __init__(self, target_layer: str = 'features'):
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._hooks = []

    def register_hooks(self, model: nn.Module):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        target_module = None
        for name, module in model.named_modules():
            if name == self.target_layer or self.target_layer in name:
                target_module = module
                break

        if target_module is not None:
            self._hooks.append(target_module.register_forward_hook(forward_hook))
            self._hooks.append(target_module.register_full_backward_hook(backward_hook))

    def remove_hooks(self):
        for hook in self._hooks:
            hook.remove()
        self._hooks = []

    def generate_cam(
        self,
        class_idx: int,
        logits: torch.Tensor,
        spatial_size: Tuple[int, int] = (7, 7)
    ) -> np.ndarray:
        if self.gradients is None or self.activations is None:
            return np.zeros(spatial_size, dtype=np.float32)

        one_hot = torch.zeros_like(logits)
        one_hot[0, class_idx] = 1

        grads = self.gradients
        activations = self.activations

        weights = torch.mean(grads, dim=(2, 3), keepdim=True)
        cam = torch.sum(weights * activations, dim=1)
        cam = F.relu(cam)

        cam = cam.cpu().numpy()[0]
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)

        return cam


class MultipleInstanceLearningLocalizer:
    def __init__(
        self,
        num_classes: int = 8,
        top_k_instances: int = 3,
        temperature: float = 0.1,
        attention_dim: int = 512
    ):
        self.num_classes = num_classes
        self.top_k_instances = top_k_instances
        self.temperature = temperature
        self.attention_dim = attention_dim

        self.attention_weights = nn.Sequential(
            nn.Linear(attention_dim, attention_dim // 2),
            nn.Tanh(),
            nn.Linear(attention_dim // 2, 1)
        )

        self._instance_scores: deque = deque(maxlen=200)
        self._attention_maps: deque = deque(maxlen=200)

    def compute_instance_scores(
        self,
        features: torch.Tensor,
        video_level_label: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        if features.dim() == 3:
            features = features.unsqueeze(0)

        B, T, D = features.shape

        attention_logits = self.attention_weights(features).squeeze(-1)
        attention_weights = F.softmax(attention_logits / self.temperature, dim=1)

        top_k = min(self.top_k_instances, T)
        top_indices = torch.topk(attention_weights, k=top_k, dim=1)[1]

        top_features = torch.gather(
            features, 1,
            top_indices.unsqueeze(-1).expand(-1, -1, D)
        )

        bag_prediction = torch.mean(top_features, dim=1)

        return bag_prediction, attention_weights

    def select_positive_instances(
        self,
        instance_scores: np.ndarray,
        threshold: float = 0.7,
        min_instances: int = 3
    ) -> List[int]:
        num_instances = len(instance_scores)
        if num_instances == 0:
            return []

        dynamic_threshold = max(
            threshold,
            np.mean(instance_scores) + 0.5 * np.std(instance_scores)
        )

        positive_indices = np.where(instance_scores >= dynamic_threshold)[0].tolist()

        if len(positive_indices) < min_instances:
            positive_indices = np.argsort(instance_scores)[-min_instances:].tolist()

        positive_indices.sort()
        return positive_indices

    def generate_pseudo_labels(
        self,
        instance_scores: np.ndarray,
        video_level_label: int,
        min_length: int = 5,
        max_gap: int = 3
    ) -> List[Dict[str, Any]]:
        if len(instance_scores) == 0:
            return []

        positive_indices = self.select_positive_instances(instance_scores)
        if not positive_indices:
            return []

        segments = []
        current_segment = [positive_indices[0]]

        for idx in positive_indices[1:]:
            if idx - current_segment[-1] <= max_gap:
                current_segment.append(idx)
            else:
                if len(current_segment) >= min_length:
                    segments.append(current_segment)
                current_segment = [idx]

        if len(current_segment) >= min_length:
            segments.append(current_segment)

        pseudo_labels = []
        for seg in segments:
            avg_score = np.mean([instance_scores[i] for i in seg])
            pseudo_labels.append({
                'class_idx': video_level_label,
                'start_idx': seg[0],
                'end_idx': seg[-1],
                'avg_score': float(avg_score),
                'num_instances': len(seg)
            })

        return pseudo_labels

    def update_history(self, instance_score: float, attention_map: Optional[np.ndarray] = None):
        self._instance_scores.append(instance_score)
        if attention_map is not None:
            self._attention_maps.append(attention_map)

    def get_instance_history(self) -> np.ndarray:
        return np.array(self._instance_scores) if self._instance_scores else np.array([])


class TemporalActionProposalNetwork:
    def __init__(
        self,
        num_classes: int = 8,
        feature_dim: int = 512,
        anchor_scales: List[int] = [16, 32, 64, 128],
        anchor_strides: List[int] = [8, 16, 32, 64]
    ):
        self.num_classes = num_classes
        self.feature_dim = feature_dim
        self.anchor_scales = anchor_scales
        self.anchor_strides = anchor_strides

        self._proposals: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def generate_anchors(self, sequence_length: int) -> List[Tuple[int, int]]:
        anchors = []
        for stride in self.anchor_strides:
            for scale in self.anchor_scales:
                for center in range(0, sequence_length, stride):
                    start = max(0, center - scale // 2)
                    end = min(sequence_length - 1, center + scale // 2)
                    if end - start >= 4:
                        anchors.append((start, end))
        return list(set(anchors))

    def score_proposals(
        self,
        anchors: List[Tuple[int, int]],
        confidence_curve: np.ndarray,
        attention_weights: Optional[np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        scored_proposals = []

        for start, end in anchors:
            if end <= start:
                continue

            segment_conf = confidence_curve[start:end + 1]
            if len(segment_conf) == 0:
                continue

            avg_conf = np.mean(segment_conf)
            max_conf = np.max(segment_conf)
            peak_score = np.max(segment_conf) - np.min(segment_conf)

            boundary_score = 0.0
            if start > 0 and end < len(confidence_curve) - 1:
                left_grad = confidence_curve[start] - confidence_curve[start - 1]
                right_grad = confidence_curve[end + 1] - confidence_curve[end]
                boundary_score = (abs(left_grad) + abs(right_grad)) / 2

            attention_bonus = 0.0
            if attention_weights is not None and len(attention_weights) >= end:
                attention_bonus = np.mean(attention_weights[start:end + 1])

            composite_score = (
                0.4 * avg_conf +
                0.3 * max_conf +
                0.2 * peak_score +
                0.1 * boundary_score +
                attention_bonus
            )

            scored_proposals.append({
                'start_idx': start,
                'end_idx': end,
                'avg_confidence': float(avg_conf),
                'max_confidence': float(max_conf),
                'boundary_score': float(boundary_score),
                'composite_score': float(composite_score),
                'duration': end - start + 1
            })

        scored_proposals.sort(key=lambda x: x['composite_score'], reverse=True)
        return scored_proposals

    def nms_proposals(
        self,
        proposals: List[Dict[str, Any]],
        iou_threshold: float = 0.3,
        max_proposals: int = 10
    ) -> List[Dict[str, Any]]:
        if not proposals:
            return []

        proposals = sorted(proposals, key=lambda x: x['composite_score'], reverse=True)
        kept = []

        for prop in proposals:
            overlap_too_high = False
            for kept_prop in kept:
                iou = self._compute_iou(prop, kept_prop)
                if iou > iou_threshold:
                    overlap_too_high = True
                    break
            if not overlap_too_high:
                kept.append(prop)
                if len(kept) >= max_proposals:
                    break

        return kept

    def _compute_iou(self, prop1: Dict[str, Any], prop2: Dict[str, Any]) -> float:
        intersection_start = max(prop1['start_idx'], prop2['start_idx'])
        intersection_end = min(prop1['end_idx'], prop2['end_idx'])

        if intersection_end < intersection_start:
            return 0.0

        intersection = intersection_end - intersection_start + 1
        union = (prop1['end_idx'] - prop1['start_idx'] + 1) + \
                (prop2['end_idx'] - prop2['start_idx'] + 1) - intersection

        return intersection / union if union > 0 else 0.0

    def add_proposal(self, proposal: Dict[str, Any]):
        with self._lock:
            self._proposals.append(proposal)

    def get_proposals(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._proposals)


class WeaklySupervisedLocalizer:
    def __init__(
        self,
        num_classes: int = 8,
        feature_dim: int = 512,
        top_k_instances: int = 3,
        min_segment_length: int = 5,
        history_size: int = 500
    ):
        self.num_classes = num_classes
        self.feature_dim = feature_dim
        self.min_segment_length = min_segment_length

        self.cam = ClassActivationMapping()
        self.mil_localizer = MultipleInstanceLearningLocalizer(
            num_classes=num_classes,
            top_k_instances=top_k_instances,
            attention_dim=feature_dim
        )
        self.proposal_network = TemporalActionProposalNetwork(
            num_classes=num_classes,
            feature_dim=feature_dim
        )

        self._confidence_matrix: deque = deque(maxlen=history_size)
        self._feature_matrix: deque = deque(maxlen=history_size)
        self._timestamp_history: deque = deque(maxlen=history_size)
        self._video_level_labels: Dict[int, int] = {}
        self._lock = threading.Lock()

    def update_with_video_label(
        self,
        features: np.ndarray,
        confidence_curve: np.ndarray,
        video_level_label: int,
        timestamp: float
    ):
        with self._lock:
            self._feature_matrix.append(features)
            self._confidence_matrix.append(confidence_curve)
            self._timestamp_history.append(timestamp)

            if video_level_label not in self._video_level_labels:
                self._video_level_labels[video_level_label] = 0
            self._video_level_labels[video_level_label] += 1

    def localize_from_video_label(
        self,
        video_level_label: int,
        nms_threshold: float = 0.3,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        with self._lock:
            if len(self._confidence_matrix) < 20:
                return []

            conf_matrix = np.array(self._confidence_matrix)
            timestamps = np.array(self._timestamp_history)

            if conf_matrix.ndim == 1:
                class_confidences = conf_matrix
            else:
                class_confidences = conf_matrix[:, video_level_label]

            smoothed_conf = gaussian_filter1d(class_confidences, sigma=2.0)

            sequence_length = len(smoothed_conf)
            anchors = self.proposal_network.generate_anchors(sequence_length)
            scored_proposals = self.proposal_network.score_proposals(
                anchors, smoothed_conf
            )

            filtered_proposals = [
                p for p in scored_proposals
                if p['avg_confidence'] >= min_confidence
            ]

            nms_proposals = self.proposal_network.nms_proposals(
                filtered_proposals,
                iou_threshold=nms_threshold
            )

            results = []
            for prop in nms_proposals:
                start_time = timestamps[prop['start_idx']]
                end_time = timestamps[prop['end_idx']]

                results.append({
                    'class_idx': video_level_label,
                    'start_idx': prop['start_idx'],
                    'end_idx': prop['end_idx'],
                    'start_time': float(start_time),
                    'end_time': float(end_time),
                    'duration': float(end_time - start_time),
                    'avg_confidence': prop['avg_confidence'],
                    'max_confidence': prop['max_confidence'],
                    'composite_score': prop['composite_score'],
                    'method': 'weakly_supervised_mil'
                })

            return results

    def generate_pseudo_ground_truth(
        self,
        video_level_labels: List[int]
    ) -> Dict[str, Any]:
        all_segments = []
        for label in video_level_labels:
            segments = self.localize_from_video_label(label)
            all_segments.extend(segments)

        all_segments.sort(key=lambda x: x['start_time'])

        return {
            'num_segments': len(all_segments),
            'segments': all_segments,
            'video_level_labels': video_level_labels,
            'method': 'weakly_supervised_pseudo_gt'
        }

    def get_attention_map(self, class_idx: int) -> Optional[np.ndarray]:
        with self._lock:
            if len(self._confidence_matrix) == 0:
                return None

            conf_matrix = np.array(self._confidence_matrix)
            if conf_matrix.ndim == 1:
                return conf_matrix

            return conf_matrix[:, class_idx]

    def get_history_size(self) -> int:
        with self._lock:
            return len(self._confidence_matrix)

    def is_ready(self) -> bool:
        return self.get_history_size() >= 20

    def clear_history(self):
        with self._lock:
            self._confidence_matrix.clear()
            self._feature_matrix.clear()
            self._timestamp_history.clear()
            self._video_level_labels.clear()
