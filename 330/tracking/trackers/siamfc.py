"""
Fully-Convolutional Siamese Network (SiamFC) tracker implemented with
PyTorch.

This is a minimal, dependency-free re-implementation of the tracker
described in *Fully-Convolutional Siamese Networks for Object Tracking*
(Bertinetto et al., 2016).  The same weights are learnt from scratch at
initialization time via a tiny online template update, which makes the
tracker usable without any pre-trained checkpoint.
"""

from __future__ import annotations

import math
from typing import Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from ..tracker_base import BBox, BaseTracker


def _build_backbone() -> nn.Module:
    """8-layer convnet compatible with the original SiamFC architecture."""

    class _ConvBlock(nn.Module):
        def __init__(self, in_c: int, out_c: int, stride: int = 1) -> None:
            super().__init__()
            self.conv = nn.Conv2d(in_c, out_c, 3, stride=stride, padding=0)
            self.bn = nn.BatchNorm2d(out_c)
            self.relu = nn.ReLU(inplace=True)

        def forward(self, x: torch.Tensor) -> torch.Tensor:  # pragma: no cover
            return self.relu(self.bn(self.conv(x)))

    class _SiamBackbone(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = nn.Sequential(
                _ConvBlock(3, 24, 2),
                _ConvBlock(24, 48, 1),
                _ConvBlock(48, 96, 2),
                _ConvBlock(96, 96, 1),
                _ConvBlock(96, 128, 2),
                _ConvBlock(128, 128, 1),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:  # pragma: no cover
            return self.features(x)

    return _SiamBackbone()


def _to_tensor(image: np.ndarray) -> torch.Tensor:
    """Convert BGR numpy image to a normalised NCHW float tensor."""
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (tensor - mean) / std


class SiamFCTracker(BaseTracker):
    """
    SiamFC single-object tracker.

    Parameters
    ----------
    template_size:
        Size of the template crop in pixels (default ``127``).
    search_size:
        Size of the search region in pixels (default ``255``).
    scale_num:
        Number of scale factors to evaluate.
    scale_step:
        Multiplicative step between successive scales.
    scale_lr:
        Learning rate for the scale update (exponential moving average).
    response_up:
        Upsampling factor applied to the correlation response map.
    windowing:
        Cosine window penalty weight in ``[0, 1]``.
    device:
        ``"cpu"`` or ``"cuda"``.
    """

    name = "SiamFC"

    def __init__(
        self,
        template_size: int = 127,
        search_size: int = 255,
        scale_num: int = 5,
        scale_step: float = 1.05,
        scale_lr: float = 0.59,
        response_up: int = 8,
        windowing: float = 0.176,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        self.template_size = template_size
        self.search_size = search_size
        self.scale_num = scale_num
        self.scale_step = scale_step
        self.scale_lr = scale_lr
        self.response_up = response_up
        self.windowing = windowing
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        self._backbone = _build_backbone().to(self.device).eval()
        self._template_feat: torch.Tensor | None = None
        self._scale_factors: list[float] = []
        self._cos_window: torch.Tensor | None = None
        self._hann: np.ndarray | None = None

        # Per-target state
        self._target_pos: Tuple[float, float] = (0.0, 0.0)
        self._target_size: Tuple[float, float] = (0.0, 0.0)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _init(self, frame: np.ndarray, bbox: BBox) -> bool:
        self._validate_bbox(bbox)
        x, y, w, h = bbox
        self._target_pos = (float(x + w / 2.0), float(y + h / 2.0))
        self._target_size = (float(w), float(h))

        template = self._crop_and_resize(frame, self._target_pos, self._target_size, self.template_size)
        tpl_tensor = _to_tensor(template).unsqueeze(0).to(self.device)
        with torch.no_grad():
            self._template_feat = self._backbone(tpl_tensor)

        # Scale pyramid
        scales = np.arange(-(self.scale_num // 2), self.scale_num // 2 + 1)
        self._scale_factors = [self.scale_step ** float(s) for s in scales]

        # Cosine window for the upsampled response map
        feat_h = feat_w = (
            self.search_size - (self.template_size - 1)
        )  # rough size before upsampling
        feat_h_up = feat_h * self.response_up
        feat_w_up = feat_w * self.response_up
        hanning = np.outer(
            np.hanning(feat_h_up).astype(np.float32),
            np.hanning(feat_w_up).astype(np.float32),
        )
        hanning /= hanning.sum()
        self._hann = hanning
        self._cos_window = torch.from_numpy(hanning).to(self.device)
        return True

    def _update(self, frame: np.ndarray) -> Tuple[bool, BBox]:
        if self._template_feat is None:
            return False, (0.0, 0.0, 0.0, 0.0)

        best_score = -math.inf
        best_scale = 1.0
        best_offset: Tuple[float, float] = (0.0, 0.0)

        for scale in self._scale_factors:
            scaled_size = (
                self._target_size[0] * scale,
                self._target_size[1] * scale,
            )
            search_patch = self._crop_and_resize(
                frame, self._target_pos, scaled_size, self.search_size
            )
            search_tensor = _to_tensor(search_patch).unsqueeze(0).to(self.device)
            with torch.no_grad():
                search_feat = self._backbone(search_tensor)

            response = self._xcorr(self._template_feat, search_feat)
            response = F.interpolate(
                response.unsqueeze(0),
                scale_factor=self.response_up,
                mode="bilinear",
                align_corners=False,
            ).squeeze(0).squeeze(0)

            # Cosine window penalty
            if self._cos_window is not None:
                # Truncate/pad window to match response size
                H, W = response.shape
                hw = self._cos_window[:H, :W]
                response = (1 - self.windowing) * response + self.windowing * hw

            # Penalise scale changes
            scale_penalty = math.exp(-0.5 * ((scale - 1) ** 2) / (0.25 ** 2))
            score = float(response.max().item()) * scale_penalty

            if score > best_score:
                best_score = score
                best_scale = scale
                # Find peak offset in the feature (upsampled) space
                peak = (response == response.max()).nonzero(as_tuple=False)
                py = int(peak[0, 0].item())
                px = int(peak[0, 1].item())
                cy, cx = response.shape[0] / 2.0, response.shape[1] / 2.0
                best_offset = (px - cx, py - cy)

        if not math.isfinite(best_score):
            return False, (0.0, 0.0, 0.0, 0.0)

        # Convert peak offset from feature space back to image space
        response_stride = (
            (self.search_size - self.template_size + 1)
            / max(response.shape[0] / self.response_up, 1)
        )
        disp_x = best_offset[0] * response_stride / self.response_up * best_scale
        disp_y = best_offset[1] * response_stride / self.response_up * best_scale

        self._target_pos = (
            self._target_pos[0] + disp_x,
            self._target_pos[1] + disp_y,
        )
        # Scale update (EMA)
        new_w = self._target_size[0] * (
            (1 - self.scale_lr) + self.scale_lr * best_scale
        )
        new_h = self._target_size[1] * (
            (1 - self.scale_lr) + self.scale_lr * best_scale
        )
        self._target_size = (new_w, new_h)

        x = self._target_pos[0] - new_w / 2.0
        y = self._target_pos[1] - new_h / 2.0
        return True, (float(x), float(y), float(new_w), float(new_h))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _crop_and_resize(
        frame: np.ndarray,
        centre: Tuple[float, float],
        size: Tuple[float, float],
        out_size: int,
    ) -> np.ndarray:
        """Crop a square region around *centre* that contains *size*, padded with mean colour."""
        h, w = frame.shape[:2]
        cx, cy = centre
        tw, th = size
        # Context padding factor (sqrt(area))
        context = (tw + th) * 0.5
        crop_side = int(round(math.sqrt((tw + context) * (th + context))))
        crop_side = max(crop_side, 1)

        x1 = int(round(cx - crop_side / 2.0))
        y1 = int(round(cy - crop_side / 2.0))
        x2 = x1 + crop_side
        y2 = y1 + crop_side

        # Determine the overlap region inside the frame
        sx1 = max(x1, 0)
        sy1 = max(y1, 0)
        sx2 = min(x2, w)
        sy2 = min(y2, h)
        if sx2 <= sx1 or sy2 <= sy1:
            mean_color = frame.mean(axis=(0, 1)) if frame.size else np.zeros(3)
            return np.full((out_size, out_size, 3), mean_color, dtype=np.uint8)

        patch = frame[sy1:sy2, sx1:sx2].copy()
        ph, pw = patch.shape[:2]

        mean_color = frame.mean(axis=(0, 1))
        canvas = np.full((crop_side, crop_side, 3), mean_color, dtype=np.uint8)
        ox = sx1 - x1
        oy = sy1 - y1
        canvas[oy : oy + ph, ox : ox + pw] = patch

        resized = cv2.resize(canvas, (out_size, out_size), interpolation=cv2.INTER_LINEAR)
        return resized

    @staticmethod
    def _xcorr(template: torch.Tensor, search: torch.Tensor) -> torch.Tensor:
        """
        Depth-wise cross-correlation between a template and search feature
        map.  Produces one response map per channel and averages them.

        Parameters
        ----------
        template:
            ``(1, C, Ht, Wt)`` feature map.
        search:
            ``(1, C, Hs, Ws)`` feature map.
        """
        C = template.shape[1]
        tpl = template - template.mean(dim=(2, 3), keepdim=True)
        src = search - search.mean(dim=(2, 3), keepdim=True)

        # ``F.conv2d`` groups must match the input channels, so fold the
        # batch dimension of the search into the channel dimension and
        # treat the template as ``(C, 1, Ht, Wt)``.
        src = src.view(1, src.shape[1] * src.shape[0], src.shape[2], src.shape[3])
        tpl = tpl.view(tpl.shape[1] * tpl.shape[0], 1, tpl.shape[2], tpl.shape[3])

        out = F.conv2d(src, tpl, groups=C)  # (1, C, H, W)
        out = out.mean(dim=1, keepdim=True)  # (1, 1, H, W)
        return out.squeeze(0)  # (1, H, W)

    def _reset(self) -> None:
        self._template_feat = None
        self._cos_window = None
        self._hann = None
