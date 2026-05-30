from __future__ import annotations

import logging
from typing import Union

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image

from config import ReidConfig
from reid_service.domain_adapter import DomainAdapter, AdaptationResult

logger = logging.getLogger(__name__)


class ReidBackbone(nn.Module):
    def __init__(self, backbone_name: str = "resnet50", feature_dim: int = 512):
        super().__init__()
        import torchvision.models as models

        if backbone_name == "resnet50":
            base = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
            in_features = base.fc.in_features
            layers = list(base.children())[:-1]
            self.backbone = nn.Sequential(*layers)
        elif backbone_name == "resnet101":
            base = models.resnet101(weights=models.ResNet101_Weights.DEFAULT)
            in_features = base.fc.in_features
            layers = list(base.children())[:-1]
            self.backbone = nn.Sequential(*layers)
        else:
            raise ValueError(f"Unsupported backbone: {backbone_name}")

        self.fc = nn.Sequential(
            nn.Linear(in_features, feature_dim),
            nn.BatchNorm1d(feature_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        feat = feat.view(feat.size(0), -1)
        feat = self.fc(feat)
        feat = torch.nn.functional.normalize(feat, p=2, dim=1)
        return feat


class ReidFeatureExtractor:
    def __init__(self, config: ReidConfig | None = None):
        self.config = config or ReidConfig()
        self.device = torch.device(
            self.config.device
            if torch.cuda.is_available()
            else "cpu"
        )
        self.model = self._build_model()
        self.transform = self._build_transform()
        self.model.to(self.device)
        self.model.eval()

        self.domain_adapter: DomainAdapter | None = None
        if self.config.use_domain_adaptation:
            self.domain_adapter = DomainAdapter(self.model, self.config)
            logger.info("Domain adaptation enabled")

        logger.info(
            f"ReID extractor initialized: backbone={self.config.model_name}, "
            f"dim={self.config.feature_dim}, device={self.device}"
        )

    def _build_model(self) -> ReidBackbone:
        model = ReidBackbone(
            backbone_name=self.config.model_name,
            feature_dim=self.config.feature_dim,
        )
        if self.config.model_weights_path:
            state_dict = torch.load(
                self.config.model_weights_path,
                map_location=self.device,
                weights_only=True,
            )
            model.load_state_dict(state_dict, strict=False)
            logger.info(f"Loaded weights from {self.config.model_weights_path}")
        return model

    def _build_transform(self) -> T.Compose:
        return T.Compose([
            T.Resize(self.config.input_size),
            T.ToTensor(),
            T.Normalize(mean=self.config.mean, std=self.config.std),
        ])

    def _preprocess(self, image: Union[np.ndarray, Image.Image]) -> torch.Tensor:
        if isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            elif image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
        return self.transform(image)

    @torch.no_grad()
    def extract(self, image: Union[np.ndarray, Image.Image], use_adaptation: bool = True) -> np.ndarray:
        tensor = self._preprocess(image).unsqueeze(0).to(self.device)
        feature = self.model(tensor)
        feature_np = feature.cpu().numpy().flatten()

        if use_adaptation and self.domain_adapter and self.domain_adapter.is_adapted:
            feature_np = self.domain_adapter.feature_level_adaptation(
                feature_np.reshape(1, -1), method="zscore"
            ).flatten()

        return feature_np

    @torch.no_grad()
    def extract_batch(
        self, images: list[Union[np.ndarray, Image.Image]], use_adaptation: bool = True
    ) -> np.ndarray:
        if not images:
            return np.array([], dtype=np.float32)
        tensors = torch.stack(
            [self._preprocess(img) for img in images]
        ).to(self.device)
        features = self.model(tensors)
        features = torch.nn.functional.normalize(features, p=2, dim=1)
        features_np = features.cpu().numpy()

        if use_adaptation and self.domain_adapter and self.domain_adapter.is_adapted:
            features_np = self.domain_adapter.feature_level_adaptation(
                features_np, method="zscore"
            )

        return features_np

    def extract_from_video_frame(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
        use_adaptation: bool = True,
    ) -> np.ndarray:
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
            frame = frame[y1:y2, x1:x2]
        return self.extract(frame, use_adaptation=use_adaptation)

    def fit_source_domain(self, source_features: np.ndarray) -> None:
        if self.domain_adapter:
            self.domain_adapter.compute_domain_stats(source_features, "source")

    def adapt_to_target_domain(
        self,
        target_images: list[np.ndarray],
        source_images: list[np.ndarray] | None = None,
        method: str = "feature",
    ) -> AdaptationResult:
        if not self.domain_adapter:
            return AdaptationResult(
                success=False,
                epochs_trained=0,
                final_loss=0.0,
                message="Domain adaptation not enabled in config",
            )

        if method == "feature":
            target_features = self.extract_batch(target_images, use_adaptation=False)
            self.domain_adapter.compute_domain_stats(target_features, "target")
            self.domain_adapter.is_adapted = True
            return AdaptationResult(
                success=True,
                epochs_trained=0,
                final_loss=0.0,
                message=f"Feature-level adaptation complete with {len(target_images)} samples",
            )

        elif method == "adversarial" and source_images:
            return self.domain_adapter.adversarial_adaptation(
                source_images, target_images
            )

        return AdaptationResult(
            success=False,
            epochs_trained=0,
            final_loss=0.0,
            message=f"Unsupported adaptation method: {method}",
        )

    def incremental_adapt(
        self, new_images: list[np.ndarray], adaptation_strength: float = 0.1
    ) -> None:
        if self.domain_adapter and self.domain_adapter.is_adapted:
            new_features = self.extract_batch(new_images, use_adaptation=False)
            self.domain_adapter.incremental_adapt(new_features, adaptation_strength)

    def reset_adaptation(self) -> None:
        if self.domain_adapter:
            self.domain_adapter.reset_adaptation()
