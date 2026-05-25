"""
Tiny Re-ID feature extractor used by :class:`DeepSORTTracker`.

The architecture is a small ResNet-like network that produces a
``feature_dim``-dimensional L2-normalised embedding for a ``(128, 64)``
RGB crop.  Weights are randomly initialized; in production the user
should fine-tune or load a checkpoint via :meth:`EmbeddingExtractor.load_state_dict`.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class _Residual(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # pragma: no cover
        residual = x
        y = F.relu(self.bn1(self.conv1(x)), inplace=True)
        y = self.bn2(self.conv2(y))
        return F.relu(y + residual, inplace=True)


class EmbeddingExtractor(nn.Module):
    """
    Lightweight CNN that maps an RGB crop to an L2-normalised embedding.

    Parameters
    ----------
    input_h, input_w:
        Expected input size (default 128 x 64).
    feature_dim:
        Embedding dimensionality.
    """

    def __init__(
        self,
        input_h: int = 128,
        input_w: int = 64,
        feature_dim: int = 128,
    ) -> None:
        super().__init__()
        self.input_h = input_h
        self.input_w = input_w
        self.feature_dim = feature_dim

        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )
        self.layer1 = nn.Sequential(_Residual(64), _Residual(64))
        self.layer2 = nn.Sequential(
            nn.Conv2d(64, 128, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            _Residual(128),
        )
        self.layer3 = nn.Sequential(
            nn.Conv2d(128, 256, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            _Residual(256),
        )
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(256, feature_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # pragma: no cover
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.pool(x).flatten(1)
        x = self.fc(x)
        return F.normalize(x, p=2, dim=1)
