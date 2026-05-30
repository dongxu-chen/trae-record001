from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Union

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from config import MultiModalConfig, ReidConfig

logger = logging.getLogger(__name__)


@dataclass
class MultiModalFeature:
    visual_feature: np.ndarray
    gait_feature: np.ndarray | None = None
    color_feature: np.ndarray | None = None
    fused_feature: np.ndarray | None = None
    visual_dim: int = 512
    gait_dim: int = 128
    color_dim: int = 64
    weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "visual_feature": self.visual_feature.tolist(),
            "gait_feature": self.gait_feature.tolist() if self.gait_feature is not None else None,
            "color_feature": self.color_feature.tolist() if self.color_feature is not None else None,
            "fused_feature": self.fused_feature.tolist() if self.fused_feature is not None else None,
            "visual_dim": self.visual_dim,
            "gait_dim": self.gait_dim,
            "color_dim": self.color_dim,
            "weights": self.weights,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MultiModalFeature:
        return cls(
            visual_feature=np.array(data["visual_feature"], dtype=np.float32),
            gait_feature=np.array(data["gait_feature"], dtype=np.float32) if data.get("gait_feature") else None,
            color_feature=np.array(data["color_feature"], dtype=np.float32) if data.get("color_feature") else None,
            fused_feature=np.array(data["fused_feature"], dtype=np.float32) if data.get("fused_feature") else None,
            visual_dim=data.get("visual_dim", 512),
            gait_dim=data.get("gait_dim", 128),
            color_dim=data.get("color_dim", 64),
            weights=data.get("weights", {}),
        )


class GaitFeatureExtractor:
    def __init__(
        self,
        config: MultiModalConfig | None = None,
        reid_config: ReidConfig | None = None,
    ):
        self.config = config or MultiModalConfig()
        self.reid_config = reid_config or ReidConfig()
        self.device = torch.device(
            self.reid_config.device if torch.cuda.is_available() else "cpu"
        )
        self.model = self._build_model()
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"GaitFeatureExtractor initialized: dim={self.config.gait_feature_dim}")

    def _build_model(self) -> nn.Module:
        class GaitCNN(nn.Module):
            def __init__(self, feature_dim: int = 128):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 32, kernel_size=3, padding=1),
                    nn.BatchNorm2d(32),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(32, 64, kernel_size=3, padding=1),
                    nn.BatchNorm2d(64),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.BatchNorm2d(128),
                    nn.ReLU(),
                    nn.AdaptiveAvgPool2d((1, 1)),
                )
                self.fc = nn.Sequential(
                    nn.Linear(128, feature_dim),
                    nn.BatchNorm1d(feature_dim),
                )

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                feat = self.features(x)
                feat = feat.view(feat.size(0), -1)
                feat = self.fc(feat)
                return F.normalize(feat, p=2, dim=1)

        return GaitCNN(feature_dim=self.config.gait_feature_dim)

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        import torchvision.transforms as T

        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        pil_image = Image.fromarray(image)
        transform = T.Compose([
            T.Resize((128, 64)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return transform(pil_image)

    @torch.no_grad()
    def extract(self, image: Union[np.ndarray, list[np.ndarray]]) -> np.ndarray:
        if isinstance(image, list):
            tensors = torch.stack([self._preprocess(img) for img in image]).to(self.device)
        else:
            tensors = self._preprocess(image).unsqueeze(0).to(self.device)

        features = self.model(tensors)
        return features.cpu().numpy()

    def extract_from_silhouette(self, silhouette: np.ndarray) -> np.ndarray:
        rgb_silhouette = cv2.cvtColor(silhouette, cv2.COLOR_GRAY2RGB) if len(silhouette.shape) == 2 else silhouette
        return self.extract(rgb_silhouette)


class ColorFeatureExtractor:
    def __init__(self, config: MultiModalConfig | None = None):
        self.config = config or MultiModalConfig()
        logger.info(
            f"ColorFeatureExtractor initialized: dim={self.config.color_feature_dim}, "
            f"bins={self.config.color_hist_bins}"
        )

    def extract_hsv_histogram(self, image: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        if image is None or image.size == 0:
            return np.zeros(self.config.color_feature_dim, dtype=np.float32)

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        bins = self.config.color_hist_bins
        hist_h = cv2.calcHist([hsv], [0], mask, [bins[0]], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], mask, [bins[1]], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], mask, [bins[2]], [0, 256])

        if self.config.color_hist_normalize:
            cv2.normalize(hist_h, hist_h, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist_s, hist_s, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist_v, hist_v, 0, 1, cv2.NORM_MINMAX)

        feature = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
        feature = feature.astype(np.float32)

        if len(feature) > self.config.color_feature_dim:
            feature = feature[: self.config.color_feature_dim]
        elif len(feature) < self.config.color_feature_dim:
            padding = np.zeros(self.config.color_feature_dim - len(feature), dtype=np.float32)
            feature = np.concatenate([feature, padding])

        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm

        return feature

    def extract_rgb_histogram(self, image: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        if image is None or image.size == 0:
            return np.zeros(self.config.color_feature_dim, dtype=np.float32)

        bins = self.config.color_hist_bins
        channels = [0, 1, 2]
        ranges = [0, 256, 0, 256, 0, 256]
        hist = cv2.calcHist([image], channels, mask, list(bins), ranges)

        if self.config.color_hist_normalize:
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        feature = hist.flatten().astype(np.float32)

        if len(feature) > self.config.color_feature_dim:
            feature = feature[: self.config.color_feature_dim]
        elif len(feature) < self.config.color_feature_dim:
            padding = np.zeros(self.config.color_feature_dim - len(feature), dtype=np.float32)
            feature = np.concatenate([feature, padding])

        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm

        return feature

    def extract_dominant_colors(self, image: np.ndarray, k: int = 8) -> np.ndarray:
        if image is None or image.size == 0:
            return np.zeros(k * 3, dtype=np.float32)

        pixels = image.reshape(-1, 3).astype(np.float32)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)

        label_counts = np.bincount(labels.flatten(), minlength=k)
        sorted_idx = np.argsort(label_counts)[::-1]

        feature = centers[sorted_idx].flatten().astype(np.float32)
        feature = feature / 255.0

        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm

        return feature

    def extract(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
        method: str = "hsv",
    ) -> np.ndarray:
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            image = image[y1:y2, x1:x2]

        if method == "hsv":
            return self.extract_hsv_histogram(image)
        elif method == "rgb":
            return self.extract_rgb_histogram(image)
        elif method == "dominant":
            return self.extract_dominant_colors(image)
        else:
            hsv = self.extract_hsv_histogram(image)
            rgb = self.extract_rgb_histogram(image)
            dominant = self.extract_dominant_colors(image)
            combined = np.concatenate([hsv, rgb, dominant])
            return combined[: self.config.color_feature_dim]


class AttentionFusionModule(nn.Module):
    def __init__(
        self,
        visual_dim: int = 512,
        gait_dim: int = 128,
        color_dim: int = 64,
        use_gait: bool = True,
        use_color: bool = True,
    ):
        super().__init__()
        self.visual_dim = visual_dim
        self.gait_dim = gait_dim
        self.color_dim = color_dim
        self.use_gait = use_gait
        self.use_color = use_color

        total_dim = visual_dim
        if use_gait:
            total_dim += gait_dim
        if use_color:
            total_dim += color_dim

        self.attention = nn.Sequential(
            nn.Linear(total_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 3 if (use_gait and use_color) else 2),
            nn.Softmax(dim=1),
        )

        self.output_proj = nn.Linear(total_dim, visual_dim)

    def forward(
        self,
        visual: torch.Tensor,
        gait: torch.Tensor | None = None,
        color: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        features = [visual]
        if self.use_gait and gait is not None:
            features.append(gait)
        if self.use_color and color is not None:
            features.append(color)

        concat = torch.cat(features, dim=1)
        weights = self.attention(concat)

        weighted_features = []
        for i, feat in enumerate(features):
            w = weights[:, i : i + 1]
            weighted_features.append(feat * w)

        fused = torch.cat(weighted_features, dim=1)
        fused = self.output_proj(fused)
        fused = F.normalize(fused, p=2, dim=1)

        return fused, weights


class MultiModalFeatureExtractor:
    def __init__(
        self,
        visual_extractor,
        config: MultiModalConfig | None = None,
        reid_config: ReidConfig | None = None,
    ):
        self.config = config or MultiModalConfig()
        self.reid_config = reid_config or ReidConfig()
        self.visual_extractor = visual_extractor
        self.device = torch.device(
            self.reid_config.device if torch.cuda.is_available() else "cpu"
        )

        self.gait_extractor = None
        if self.config.enable_gait_feature:
            self.gait_extractor = GaitFeatureExtractor(self.config, self.reid_config)

        self.color_extractor = None
        if self.config.enable_color_feature:
            self.color_extractor = ColorFeatureExtractor(self.config)

        self.fusion_model = AttentionFusionModule(
            visual_dim=self.reid_config.feature_dim,
            gait_dim=self.config.gait_feature_dim,
            color_dim=self.config.color_feature_dim,
            use_gait=self.config.enable_gait_feature,
            use_color=self.config.enable_color_feature,
        ).to(self.device)
        self.fusion_model.eval()

        logger.info(
            f"MultiModalFeatureExtractor initialized: "
            f"visual={self.reid_config.feature_dim}, "
            f"gait={self.config.enable_gait_feature}({self.config.gait_feature_dim}), "
            f"color={self.config.enable_color_feature}({self.config.color_feature_dim})"
        )

    def set_weights(
        self,
        visual_weight: float | None = None,
        gait_weight: float | None = None,
        color_weight: float | None = None,
    ) -> None:
        if visual_weight is not None:
            self.config.visual_feature_weight = visual_weight
        if gait_weight is not None:
            self.config.gait_feature_weight = gait_weight
        if color_weight is not None:
            self.config.color_feature_weight = color_weight

        logger.info(
            f"Weights updated: visual={self.config.visual_feature_weight:.2f}, "
            f"gait={self.config.gait_feature_weight:.2f}, "
            f"color={self.config.color_feature_weight:.2f}"
        )

    def extract(
        self,
        image: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
        return_all: bool = False,
    ) -> MultiModalFeature | np.ndarray:
        visual_feat = self.visual_extractor.extract(image, bbox=bbox) if bbox else self.visual_extractor.extract(image)

        gait_feat = None
        if self.gait_extractor:
            try:
                gait_image = image[y1:y2, x1:x2] if bbox else image
                gait_feat = self.gait_extractor.extract(gait_image).flatten()
            except Exception as e:
                logger.debug(f"Gait feature extraction failed: {e}")

        color_feat = None
        if self.color_extractor:
            try:
                color_feat = self.color_extractor.extract(image, bbox=bbox)
            except Exception as e:
                logger.debug(f"Color feature extraction failed: {e}")

        fused_feat, weights = self._fuse_features(visual_feat, gait_feat, color_feat)

        weights_dict = {
            "visual": float(weights[0, 0]) if weights.shape[1] > 0 else self.config.visual_feature_weight,
            "gait": float(weights[0, 1]) if weights.shape[1] > 1 else self.config.gait_feature_weight,
            "color": float(weights[0, 2]) if weights.shape[1] > 2 else self.config.color_feature_weight,
        }

        mm_feature = MultiModalFeature(
            visual_feature=visual_feat,
            gait_feature=gait_feat,
            color_feature=color_feat,
            fused_feature=fused_feat,
            visual_dim=self.reid_config.feature_dim,
            gait_dim=self.config.gait_feature_dim,
            color_dim=self.config.color_feature_dim,
            weights=weights_dict,
        )

        if return_all:
            return mm_feature
        return fused_feat

    def extract_batch(
        self,
        images: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int] | None] | None = None,
    ) -> np.ndarray:
        bboxes = bboxes or [None] * len(images)
        features = []
        for img, bbox in zip(images, bboxes):
            feat = self.extract(img, bbox=bbox)
            features.append(feat)
        return np.stack(features)

    @torch.no_grad()
    def _fuse_features(
        self,
        visual: np.ndarray,
        gait: np.ndarray | None = None,
        color: np.ndarray | None = None,
    ) -> tuple[np.ndarray, torch.Tensor]:
        visual_tensor = torch.from_numpy(visual).unsqueeze(0).to(self.device)

        gait_tensor = None
        if gait is not None:
            gait_tensor = torch.from_numpy(gait).unsqueeze(0).to(self.device)

        color_tensor = None
        if color is not None:
            color_tensor = torch.from_numpy(color).unsqueeze(0).to(self.device)

        if self.config.enable_gait_feature and self.config.enable_color_feature:
            fused, weights = self.fusion_model(visual_tensor, gait_tensor, color_tensor)
        elif self.config.enable_gait_feature:
            fused, weights = self.fusion_model(visual_tensor, gait_tensor, None)
        elif self.config.enable_color_feature:
            fused, weights = self.fusion_model(visual_tensor, None, color_tensor)
        else:
            fused = visual_tensor
            weights = torch.tensor([[1.0, 0.0, 0.0]], device=self.device)

        return fused.cpu().numpy().flatten(), weights.cpu()

    def get_config(self) -> dict:
        return {
            "enable_gait": self.config.enable_gait_feature,
            "enable_color": self.config.enable_color_feature,
            "visual_dim": self.reid_config.feature_dim,
            "gait_dim": self.config.gait_feature_dim,
            "color_dim": self.config.color_feature_dim,
            "weights": {
                "visual": self.config.visual_feature_weight,
                "gait": self.config.gait_feature_weight,
                "color": self.config.color_feature_weight,
            },
        }
