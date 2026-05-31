from typing import Dict, List, Tuple, Optional

import torch
import numpy as np
from torchvision import transforms

try:
    from transformers import (
        VideoMAEForVideoClassification,
        VideoMAEImageProcessor,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from .base import BaseActionRecognizer


class VideoMAERecognizer(BaseActionRecognizer):
    def __init__(
        self,
        device: str = "cpu",
        class_names: Optional[Dict[int, str]] = None,
        confidence_threshold: float = 0.5,
        fp16: bool = False,
        multi_label: bool = True,
        num_frames: int = 16,
        frame_size: int = 224,
        mean: Tuple[float, float, float] = (0.45, 0.45, 0.45),
        std: Tuple[float, float, float] = (0.225, 0.225, 0.225),
    ) -> None:
        super().__init__(device, class_names, confidence_threshold, fp16, multi_label)
        self.num_frames: int = num_frames
        self.frame_size: int = frame_size
        self.mean: Tuple[float, float, float] = mean
        self.std: Tuple[float, float, float] = std
        self._num_classes: int = len(self.class_names) if self.class_names else 400
        self._processor: Optional[VideoMAEImageProcessor] = None

    def load_model(self, model_path: Optional[str] = None) -> None:
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers is not installed. Please install it with: pip install transformers"
            )

        try:
            self.model_path = model_path or "MCG-NJU/videomae-base-finetuned-kinetics400"

            id2label = {str(k): v for k, v in self.class_names.items()} if self.class_names else None
            label2id = {v: str(k) for k, v in self.class_names.items()} if self.class_names else None

            self._processor = VideoMAEImageProcessor.from_pretrained(
                self.model_path if self.model_path.startswith("MCG-NJU") else "MCG-NJU/videomae-base-finetuned-kinetics400"
            )

            self.model = VideoMAEForVideoClassification.from_pretrained(
                self.model_path,
                num_labels=self._num_classes,
                id2label=id2label,
                label2id=label2id,
                ignore_mismatched_sizes=True,
            )

            self.model = self.model.to(self.device)
            self.model.eval()

            if self.fp16:
                self.model = self.model.half()

            self._is_loaded = True

        except ImportError as e:
            raise RuntimeError(f"Failed to load VideoMAE model dependencies: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load VideoMAE model: {e}")

    def preprocess(self, frames: List[np.ndarray]) -> torch.Tensor:
        self._validate_frames(frames, self.num_frames)

        frames = frames[: self.num_frames]

        if self._processor is not None:
            frames_rgb = [frame[:, :, ::-1] for frame in frames]
            inputs = self._processor(
                list(frames_rgb),
                return_tensors="pt",
                sampling_rate=2,
                num_frames=self.num_frames,
            )
            clip_tensor = inputs["pixel_values"]
        else:
            processed_frames: List[torch.Tensor] = []
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((self.frame_size, self.frame_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=self.mean, std=self.std),
            ])

            for frame in frames:
                frame_rgb = frame[:, :, ::-1].copy()
                frame_tensor = transform(frame_rgb)
                processed_frames.append(frame_tensor)

            clip_tensor = torch.stack(processed_frames, dim=0)
            clip_tensor = clip_tensor.unsqueeze(0)
            clip_tensor = clip_tensor.permute(0, 2, 1, 3, 4)

        if self.fp16:
            clip_tensor = clip_tensor.half()

        return clip_tensor

    def predict(
        self, clip_tensor: torch.Tensor
    ) -> List[Tuple[str, float, int]]:
        if not self._is_loaded or self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() first.")

        try:
            clip_tensor = clip_tensor.to(self.device)

            with torch.no_grad():
                outputs = self.model(pixel_values=clip_tensor)
                logits = outputs.logits

            return self._get_top_k_predictions(logits, top_k=5)

        except Exception as e:
            raise RuntimeError(f"Prediction failed: {e}")

    def predict_with_probs(
        self, clip_tensor: torch.Tensor
    ) -> Tuple[List[Tuple[str, float, int]], np.ndarray]:
        if not self._is_loaded or self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() first.")

        try:
            clip_tensor = clip_tensor.to(self.device)

            with torch.no_grad():
                outputs = self.model(pixel_values=clip_tensor)
                logits = outputs.logits

            predictions = self._get_top_k_predictions(logits, top_k=5)
            all_probs = self.get_all_probabilities(logits)

            return predictions, all_probs

        except Exception as e:
            raise RuntimeError(f"Prediction failed: {e}")
