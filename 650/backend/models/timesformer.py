from typing import Dict, List, Tuple, Optional

import torch
import numpy as np
import torch.nn.functional as F
from torchvision import transforms

try:
    from pytorchvideo.models import create_video_classifier
    from pytorchvideo.models.head import create_res_basic_head
    PYTORCHVIDEO_AVAILABLE = True
except ImportError:
    PYTORCHVIDEO_AVAILABLE = False

from .base import BaseActionRecognizer


class TimeSformerRecognizer(BaseActionRecognizer):
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

    def load_model(self, model_path: Optional[str] = None) -> None:
        if not PYTORCHVIDEO_AVAILABLE:
            raise ImportError(
                "pytorchvideo is not installed. Please install it with: pip install pytorchvideo"
            )

        try:
            self.model_path = model_path or "kinetics400"

            self.model = create_video_classifier(
                model_name="timesformer",
                model_num_class=self._num_classes,
                input_clip_length=self.num_frames,
                input_crop_size=self.frame_size,
                head_pool_kernel_size=(self.num_frames // 4, 7, 7),
                dropout_rate=0.5,
            )

            if model_path and model_path != "kinetics400":
                state_dict = torch.load(model_path, map_location=self.device)
                if "state_dict" in state_dict:
                    state_dict = state_dict["state_dict"]
                self.model.load_state_dict(state_dict)

            self.model = self.model.to(self.device)
            self.model.eval()

            if self.fp16:
                self.model = self.model.half()

            self._is_loaded = True

        except ImportError as e:
            raise RuntimeError(f"Failed to load TimeSformer model dependencies: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load TimeSformer model: {e}")

    def preprocess(self, frames: List[np.ndarray]) -> torch.Tensor:
        self._validate_frames(frames, self.num_frames)

        frames = frames[: self.num_frames]
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

        clip_tensor = torch.stack(processed_frames, dim=1)
        clip_tensor = clip_tensor.unsqueeze(0)

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
                logits = self.model(clip_tensor)

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
                logits = self.model(clip_tensor)

            predictions = self._get_top_k_predictions(logits, top_k=5)
            all_probs = self.get_all_probabilities(logits)

            return predictions, all_probs

        except Exception as e:
            raise RuntimeError(f"Prediction failed: {e}")
