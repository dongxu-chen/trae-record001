"""
Siamese Region Proposal Network (SiamRPN) tracker with optional TensorRT
acceleration.

Implements the tracker from *High Performance Visual Tracking with
Siamese Region Proposal Network* (Li et al., 2018).

**TensorRT acceleration**: if ``tensorrt`` is installed and the tracker is
running on CUDA, the backbone + RPN heads are traced and converted to a
TensorRT engine, which typically yields a ~3x speedup over raw PyTorch.
"""

from __future__ import annotations

import os
import math
from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from ..tracker_base import BBox, BaseTracker


# ---------------------------------------------------------------------------
# Network architecture
# ---------------------------------------------------------------------------
class _RPN(nn.Module):
    """
    Region proposal network with classification and regression heads.

    Produces ``2 * anchors`` classification scores and ``4 * anchors``
    regression deltas per spatial position.
    """

    def __init__(self, in_channels: int = 128, anchors: int = 5) -> None:
        super().__init__()
        self.cls = nn.Conv2d(in_channels, 2 * anchors, 1)
        self.reg = nn.Conv2d(in_channels, 4 * anchors, 1)

    def forward(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:  # pragma: no cover
        return self.cls(x), self.reg(x)


class SiamRPNBackbone(nn.Module):
    """
    Shared Siamese backbone — 8-layer convnet compatible with SiamRPN.
    """

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 24, 3, stride=2, padding=0, bias=False),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.Conv2d(24, 48, 3, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.Conv2d(48, 96, 3, stride=2, padding=0, bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.Conv2d(96, 96, 3, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.Conv2d(96, 128, 3, stride=2, padding=0, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # pragma: no cover
        return self.features(x)


class SiamRPN(nn.Module):
    """
    End-to-end SiamRPN network: backbone + RPN + cross-correlation.

    For deployment, the template and search branches are fused into a
    single forward pass when tracing for TensorRT.
    """

    def __init__(self, anchors: int = 5) -> None:
        super().__init__()
        self.backbone = SiamRPNBackbone()
        self.rpn_template = _RPN(in_channels=128, anchors=anchors)
        self.rpn_search = _RPN(in_channels=128, anchors=anchors)

    def template(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        zf = self.backbone(z)
        return self.rpn_template(zf)

    def search(
        self, z_cls: torch.Tensor, z_reg: torch.Tensor, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        xf = self.backbone(x)
        x_cls, x_reg = self.rpn_search(xf)
        return self._xcorr(z_cls, x_cls), self._xcorr(z_reg, x_reg)

    @staticmethod
    def _xcorr(kernel: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
        batch = kernel.shape[0]
        out_ch = kernel.shape[1]
        kernel = kernel.view(-1, 1, kernel.shape[2], kernel.shape[3])
        x = x.view(1, -1, x.shape[2], x.shape[3])
        out = F.conv2d(x, kernel, groups=batch * out_ch)
        return out.view(batch, out_ch, out.shape[2], out.shape[3])


# ---------------------------------------------------------------------------
# TensorRT wrapper
# ---------------------------------------------------------------------------
class _TensorRTEngine:
    """
    Wraps a TensorRT engine for the SiamRPN search path.

    The engine is built from a traced PyTorch module the first time
    :meth:`build` is called, then cached to disk for subsequent runs.
    """

    def __init__(self, cache_path: str = "siamrpn_trt.engine") -> None:
        self.cache_path = cache_path
        self.engine = None
        self.context = None
        self.input_binding = None
        self.output_binding_cls = None
        self.output_binding_reg = None
        self.stream = None

    def is_available(self) -> bool:
        try:
            import tensorrt  # type: ignore  # noqa: F401
            return torch.cuda.is_available()
        except Exception:
            return False

    def build(
        self,
        model: SiamRPN,
        z_cls: torch.Tensor,
        z_reg: torch.Tensor,
        x: torch.Tensor,
    ) -> bool:
        if not self.is_available():
            return False
        try:
            import tensorrt as trt  # type: ignore
        except Exception:
            return False

        # Build a wrapper module that takes a single search input and
        # returns both classification and regression outputs.
        class _DeployWrapper(nn.Module):
            def __init__(self, model: SiamRPN, z_cls: torch.Tensor, z_reg: torch.Tensor) -> None:
                super().__init__()
                self.z_cls = z_cls
                self.z_reg = z_reg
                self.backbone = model.backbone
                self.rpn_search = model.rpn_search

            def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
                xf = self.backbone(x)
                x_cls, x_reg = self.rpn_search(xf)
                return SiamRPN._xcorr(self.z_cls, x_cls), SiamRPN._xcorr(self.z_reg, x_reg)

        wrapper = _DeployWrapper(model, z_cls, z_reg).eval().cuda()

        # Trace with TorchScript
        with torch.no_grad():
            traced = torch.jit.trace(wrapper, [x.cuda()])

        # Convert to ONNX
        onnx_path = self.cache_path + ".onnx"
        torch.onnx.export(
            traced,
            x.cuda(),
            onnx_path,
            input_names=["search"],
            output_names=["cls", "reg"],
            opset_version=16,
            dynamic_axes=None,
        )

        # Build TensorRT engine
        logger = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(logger)
        config = builder.create_builder_config()
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
        config.set_flag(trt.BuilderFlag.FP16)

        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = builder.create_network(network_flags)
        parser = trt.OnnxParser(network, logger)
        with open(onnx_path, "rb") as f:
            if not parser.parse(f.read()):
                return False

        serialized = builder.build_serialized_network(network, config)
        if serialized is None:
            return False

        with open(self.cache_path, "wb") as f:
            f.write(serialized)

        # Load engine
        runtime = trt.Runtime(logger)
        self.engine = runtime.deserialize_cuda_engine(serialized)
        self.context = self.engine.create_execution_context()
        self.stream = torch.cuda.current_stream().cuda_stream

        for i in range(self.engine.num_bindings):
            name = self.engine.get_binding_name(i)
            if name == "search":
                self.input_binding = i
            elif name == "cls":
                self.output_binding_cls = i
            elif name == "reg":
                self.output_binding_reg = i

        # Clean up
        try:
            os.remove(onnx_path)
        except Exception:  # pragma: no cover
            pass

        return True

    def infer(
        self, x: torch.Tensor
    ) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
        if self.context is None:
            return None

        batch_size = x.shape[0]
        cls_out = torch.empty(
            (batch_size, 10, 17, 17), dtype=torch.float32, device="cuda"
        )
        reg_out = torch.empty(
            (batch_size, 20, 17, 17), dtype=torch.float32, device="cuda"
        )

        bindings = [0] * 3
        bindings[self.input_binding] = x.data_ptr()
        bindings[self.output_binding_cls] = cls_out.data_ptr()
        bindings[self.output_binding_reg] = reg_out.data_ptr()

        if not self.context.execute_v2(bindings):
            return None
        return cls_out, reg_out


# ---------------------------------------------------------------------------
# Anchor generation
# ---------------------------------------------------------------------------
def _generate_anchors(
    stride: int = 8,
    base_size: int = 8,
    ratios: Tuple[float, ...] = (0.33, 0.5, 1.0, 2.0, 3.0),
    scales: Tuple[float, ...] = (8,),
) -> np.ndarray:
    """Generate anchor boxes centred at (0, 0)."""
    anchors = []
    for r in ratios:
        for s in scales:
            w = base_size * s * math.sqrt(r)
            h = base_size * s / math.sqrt(r)
            anchors.append([-w / 2.0, -h / 2.0, w / 2.0, h / 2.0])
    return np.array(anchors, dtype=np.float32)


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------
class SiamRPNTracker(BaseTracker):
    """
    SiamRPN single-object tracker with optional TensorRT acceleration.

    Parameters
    ----------
    template_size:
        Size of the template crop in pixels.
    search_size:
        Size of the search region in pixels.
    scale_step:
        Multiplicative scale step for the multi-scale search pyramid.
    scale_num:
        Number of scales in the pyramid.
    response_up:
        Response map upsampling factor.
    windowing:
        Cosine window penalty weight in ``[0, 1]``.
    penalty_k:
        Shape-change penalty coefficient.
    lr:
        Template update learning rate.
    use_trt:
        Whether to try to use TensorRT acceleration (when available).
    device:
        ``"cpu"`` or ``"cuda"``.
    """

    name = "SiamRPN"

    def __init__(
        self,
        template_size: int = 127,
        search_size: int = 271,
        scale_step: float = 1.0375,
        scale_num: int = 3,
        response_up: int = 16,
        windowing: float = 0.3,
        penalty_k: float = 0.055,
        lr: float = 0.3,
        use_trt: bool = True,
        device: str = "cpu",
    ) -> None:
        super().__init__()
        self.template_size = template_size
        self.search_size = search_size
        self.scale_step = scale_step
        self.scale_num = scale_num
        self.response_up = response_up
        self.windowing = windowing
        self.penalty_k = penalty_k
        self.lr = lr
        self.use_trt = use_trt

        self.device = torch.device(
            device if torch.cuda.is_available() or device == "cpu" else "cpu"
        )

        self._model = SiamRPN(anchors=5).to(self.device).eval()
        self._trt = _TensorRTEngine()

        # Per-target state
        self._z_cls: Optional[torch.Tensor] = None
        self._z_reg: Optional[torch.Tensor] = None
        self._target_pos: Tuple[float, float] = (0.0, 0.0)
        self._target_size: Tuple[float, float] = (0.0, 0.0)
        self._anchors: Optional[np.ndarray] = None
        self._window: Optional[np.ndarray] = None
        self._trt_active = False

        # Benchmarking
        self._pytorch_time = 0.0
        self._trt_time = 0.0
        self._inference_count = 0

    @property
    def trt_active(self) -> bool:
        """Whether TensorRT is currently being used for inference."""
        return self._trt_active

    @property
    def speedup_ratio(self) -> Optional[float]:
        """Measured speedup ratio (PyTorch time / TensorRT time) if available."""
        if self._trt_time > 0 and self._pytorch_time > 0:
            return self._pytorch_time / self._trt_time
        return None

    # ------------------------------------------------------------------
    # Init / update
    # ------------------------------------------------------------------
    def _init(self, frame: np.ndarray, bbox: BBox) -> bool:
        self._validate_bbox(bbox)
        x, y, w, h = bbox
        self._target_pos = (float(x + w / 2.0), float(y + h / 2.0))
        self._target_size = (float(w), float(h))

        template = self._crop_and_resize(
            frame, self._target_pos, self._target_size, self.template_size
        )
        tpl_tensor = self._to_tensor(template).unsqueeze(0).to(self.device)

        with torch.no_grad():
            self._z_cls, self._z_reg = self._model.template(tpl_tensor)

        self._init_anchors_and_window()

        # Build TensorRT engine if requested and available
        if self.use_trt and self._trt.is_available():
            dummy = self._to_tensor(np.zeros((self.search_size, self.search_size, 3), dtype=np.uint8))
            dummy = dummy.unsqueeze(0).to(self.device)
            if self._trt.build(self._model, self._z_cls, self._z_reg, dummy):
                self._trt_active = True

        # Run a few warm-up iterations and measure baseline speed
        if self._trt_active:
            self._benchmark_speed(dummy)

        return True

    def _update(self, frame: np.ndarray) -> Tuple[bool, BBox]:
        if self._z_cls is None:
            return False, (0.0, 0.0, 0.0, 0.0)

        best_score = -math.inf
        best_scale = 1.0
        best_anchor_idx = 0
        best_pos_idx: Tuple[int, int] = (0, 0)
        best_reg: Optional[np.ndarray] = None

        scales = [
            self.scale_step ** float(i - self.scale_num // 2)
            for i in range(self.scale_num)
        ]

        import time

        for scale in scales:
            scaled_size = (
                self._target_size[0] * scale,
                self._target_size[1] * scale,
            )
            search = self._crop_and_resize(
                frame, self._target_pos, scaled_size, self.search_size
            )
            search_tensor = self._to_tensor(search).unsqueeze(0).to(self.device)

            t0 = time.perf_counter()
            with torch.no_grad():
                if self._trt_active:
                    out = self._trt.infer(search_tensor)
                    if out is not None:
                        cls_out, reg_out = out
                    else:
                        cls_out, reg_out = self._model.search(
                            self._z_cls, self._z_reg, search_tensor
                        )
                else:
                    cls_out, reg_out = self._model.search(
                        self._z_cls, self._z_reg, search_tensor
                    )
            elapsed = time.perf_counter() - t0

            if self._trt_active:
                self._trt_time += elapsed
            else:
                self._pytorch_time += elapsed
            self._inference_count += 1

            # Process outputs
            cls_prob = F.softmax(cls_out.view(2, 5, *cls_out.shape[-2:]), dim=0)[1]
            cls_prob = F.interpolate(
                cls_prob.unsqueeze(0),
                scale_factor=self.response_up,
                mode="bilinear",
                align_corners=False,
            ).squeeze(0)

            reg_delta = reg_out.view(4, 5, *reg_out.shape[-2:])
            reg_delta = F.interpolate(
                reg_delta,
                scale_factor=self.response_up,
                mode="bilinear",
                align_corners=False,
            ).cpu().numpy()

            # Apply cosine window penalty
            if self._window is not None:
                A, H, W = cls_prob.shape
                window = torch.from_numpy(self._window[:, :H, :W]).to(cls_prob.device)
                cls_prob = (1 - self.windowing) * cls_prob + self.windowing * window

            cls_np = cls_prob.cpu().numpy()

            # Penalty for scale/ratio change
            for a in range(5):
                score_map = cls_np[a]
                score = score_map.max()
                if score > best_score:
                    best_score = float(score)
                    best_scale = scale
                    best_anchor_idx = a
                    peak = np.unravel_index(np.argmax(score_map), score_map.shape)
                    best_pos_idx = (int(peak[0]), int(peak[1]))
                    best_reg = reg_delta[:, a, :, :]

        if not math.isfinite(best_score) or best_reg is None:
            return False, (0.0, 0.0, 0.0, 0.0)

        # Get anchor and regression delta
        stride = self.search_size / max(cls_prob.shape[-2] / self.response_up, 1) / 8 * self.response_up
        py, px = best_pos_idx
        cy, cx = best_reg.shape[1] // 2, best_reg.shape[2] // 2
        disp_y = (py - cy) * stride / self.response_up
        disp_x = (px - cx) * stride / self.response_up

        dx = disp_x * best_scale
        dy = disp_y * best_scale

        # Apply regression delta
        anchor = self._anchors[best_anchor_idx]
        reg = best_reg[:, py, px]
        pred_w = math.exp(reg[2]) * (anchor[2] - anchor[0])
        pred_h = math.exp(reg[3]) * (anchor[3] - anchor[1])

        # Smooth target update
        new_w = self._target_size[0] * (1 - self.lr) + pred_w * best_scale * self.lr
        new_h = self._target_size[1] * (1 - self.lr) + pred_h * best_scale * self.lr

        self._target_pos = (
            self._target_pos[0] + dx,
            self._target_pos[1] + dy,
        )
        self._target_size = (new_w, new_h)

        x = self._target_pos[0] - new_w / 2.0
        y = self._target_pos[1] - new_h / 2.0
        return True, (float(x), float(y), float(new_w), float(new_h))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _init_anchors_and_window(self) -> None:
        self._anchors = _generate_anchors()
        feat_size = (self.search_size - self.template_size) // 8 + 1
        feat_size_up = feat_size * self.response_up
        hanning = np.outer(
            np.hanning(feat_size_up).astype(np.float32),
            np.hanning(feat_size_up).astype(np.float32),
        )
        hanning = np.stack([hanning] * 5, axis=0)
        hanning /= hanning.sum()
        self._window = hanning

    @staticmethod
    def _to_tensor(image: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        return (tensor - mean) / std

    @staticmethod
    def _crop_and_resize(
        frame: np.ndarray,
        centre: Tuple[float, float],
        size: Tuple[float, float],
        out_size: int,
    ) -> np.ndarray:
        h, w = frame.shape[:2]
        cx, cy = centre
        tw, th = size
        context = (tw + th) * 0.5
        crop_side = int(round(math.sqrt((tw + context) * (th + context))))
        crop_side = max(crop_side, 1)

        x1 = int(round(cx - crop_side / 2.0))
        y1 = int(round(cy - crop_side / 2.0))
        x2 = x1 + crop_side
        y2 = y1 + crop_side

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

        return cv2.resize(canvas, (out_size, out_size), interpolation=cv2.INTER_LINEAR)

    def _benchmark_speed(self, dummy: torch.Tensor, num_iters: int = 20) -> None:
        """Run a quick benchmark to measure baseline PyTorch speed."""
        import time

        # Warmup
        for _ in range(5):
            with torch.no_grad():
                self._model.search(self._z_cls, self._z_reg, dummy)

        # Measure PyTorch
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(num_iters):
            with torch.no_grad():
                self._model.search(self._z_cls, self._z_reg, dummy)
        torch.cuda.synchronize()
        self._pytorch_time = (time.perf_counter() - t0) / num_iters

        # Measure TRT
        if self._trt_active:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(num_iters):
                with torch.no_grad():
                    self._trt.infer(dummy)
            torch.cuda.synchronize()
            self._trt_time = (time.perf_counter() - t0) / num_iters

    def _reset(self) -> None:
        self._z_cls = None
        self._z_reg = None
        self._anchors = None
        self._window = None
        self._trt_active = False
