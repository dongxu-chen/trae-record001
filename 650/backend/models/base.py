from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any

import torch
import numpy as np


class BaseActionRecognizer(ABC):
    def __init__(
        self,
        device: str = "cpu",
        class_names: Optional[Dict[int, str]] = None,
        confidence_threshold: float = 0.5,
        fp16: bool = False,
        multi_label: bool = True,
    ) -> None:
        self.device: torch.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.model_path: str = ""
        self.class_names: Dict[int, str] = class_names or {}
        self.confidence_threshold: float = confidence_threshold
        self.fp16: bool = fp16 and self.device.type == "cuda"
        self.multi_label: bool = multi_label
        self.model: Optional[torch.nn.Module] = None
        self._is_loaded: bool = False

    @abstractmethod
    def load_model(self, model_path: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def predict(
        self, clip_tensor: torch.Tensor
    ) -> List[Tuple[str, float, int]]:
        pass

    @abstractmethod
    def preprocess(self, frames: List[np.ndarray]) -> torch.Tensor:
        pass

    def get_device(self) -> torch.device:
        return self.device

    def get_class_names(self) -> Dict[int, str]:
        return self.class_names

    def is_loaded(self) -> bool:
        return self._is_loaded

    def _validate_frames(self, frames: List[np.ndarray], expected_frames: int) -> None:
        if not frames:
            raise ValueError("Frames list cannot be empty")
        if len(frames) < expected_frames:
            raise ValueError(
                f"Expected at least {expected_frames} frames, got {len(frames)}"
            )
        for i, frame in enumerate(frames):
            if not isinstance(frame, np.ndarray):
                raise ValueError(f"Frame {i} must be a numpy array")
            if frame.ndim != 3:
                raise ValueError(
                    f"Frame {i} must have 3 dimensions (H, W, C), got {frame.ndim}"
                )

    def _get_multi_label_predictions(
        self, logits: torch.Tensor, top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        with torch.no_grad():
            probabilities = torch.sigmoid(logits)

        results: List[Tuple[str, float, int]] = []
        probs_np = probabilities[0].cpu().numpy()

        for class_idx in range(len(probs_np)):
            confidence = float(probs_np[class_idx])
            class_name = self.class_names.get(class_idx, f"class_{class_idx}")
            if confidence >= self.confidence_threshold:
                results.append((class_name, confidence, class_idx))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _get_single_label_predictions(
        self, logits: torch.Tensor, top_k: int = 3
    ) -> List[Tuple[str, float, int]]:
        with torch.no_grad():
            probabilities = torch.softmax(logits, dim=1)
            top_probs, top_indices = torch.topk(probabilities, k=min(top_k, logits.size(1)))

        results: List[Tuple[str, float, int]] = []
        for prob, idx in zip(top_probs[0], top_indices[0]):
            confidence = float(prob.item())
            class_idx = int(idx.item())
            class_name = self.class_names.get(class_idx, f"class_{class_idx}")
            if confidence >= self.confidence_threshold:
                results.append((class_name, confidence, class_idx))

        return results

    def _get_top_k_predictions(
        self, logits: torch.Tensor, top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        if self.multi_label:
            return self._get_multi_label_predictions(logits, top_k)
        else:
            return self._get_single_label_predictions(logits, top_k)

    def get_all_probabilities(self, logits: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            if self.multi_label:
                probabilities = torch.sigmoid(logits)
            else:
                probabilities = torch.softmax(logits, dim=1)
        return probabilities[0].cpu().numpy()
