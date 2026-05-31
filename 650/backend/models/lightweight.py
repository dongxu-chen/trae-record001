from typing import Dict, List, Tuple, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torchvision import transforms

from .base import BaseActionRecognizer


class TemporalShiftModule(nn.Module):
    def __init__(self, n_segment: int = 8, n_div: int = 8, inplace: bool = False):
        super().__init__()
        self.n_segment = n_segment
        self.fold_div = n_div
        self.inplace = inplace

    def forward(self, x):
        nt, c, h, w = x.size()
        n_batch = nt // self.n_segment
        x = x.view(n_batch, self.n_segment, c, h, w)

        fold = c // self.fold_div
        out = torch.zeros_like(x)
        out[:, :-1, :fold] = x[:, 1:, :fold]
        out[:, 1:, fold: 2 * fold] = x[:, :-1, fold: 2 * fold]
        out[:, :, 2 * fold:] = x[:, :, 2 * fold:]

        return out.view(nt, c, h, w)


class ConvBNReLU(nn.Sequential):
    def __init__(self, in_planes: int, out_planes: int, kernel_size: int = 3, 
                 stride: int = 1, groups: int = 1):
        padding = (kernel_size - 1) // 2
        super().__init__(
            nn.Conv2d(in_planes, out_planes, kernel_size, stride, padding, groups=groups, bias=False),
            nn.BatchNorm2d(out_planes),
            nn.ReLU6(inplace=True)
        )


class InvertedResidual(nn.Module):
    def __init__(self, inp: int, oup: int, stride: int, expand_ratio: int):
        super().__init__()
        self.stride = stride
        assert stride in [1, 2]

        hidden_dim = int(round(inp * expand_ratio))
        self.use_res_connect = self.stride == 1 and inp == oup

        layers = []
        if expand_ratio != 1:
            layers.append(ConvBNReLU(inp, hidden_dim, kernel_size=1))

        layers.extend([
            ConvBNReLU(hidden_dim, hidden_dim, stride=stride, groups=hidden_dim),
            nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
            nn.BatchNorm2d(oup),
        ])

        self.conv = nn.Sequential(*layers)
        self.tsm = TemporalShiftModule(n_segment=8, n_div=8)

    def forward(self, x):
        if self.use_res_connect:
            return x + self.tsm(self.conv(x))
        else:
            return self.tsm(self.conv(x))


class MobileNetV2TSM(nn.Module):
    def __init__(self, num_classes: int = 400, width_mult: float = 1.0, 
                 n_segment: int = 8, dropout: float = 0.5):
        super().__init__()
        self.n_segment = n_segment
        self.num_classes = num_classes

        input_channel = 32
        last_channel = 1280

        inverted_residual_setting = [
            [1, 16, 1, 1],
            [6, 24, 2, 2],
            [6, 32, 3, 2],
            [6, 64, 4, 2],
            [6, 96, 3, 1],
            [6, 160, 3, 2],
            [6, 320, 1, 1],
        ]

        input_channel = int(input_channel * width_mult)
        self.last_channel = int(last_channel * max(1.0, width_mult))

        features = [ConvBNReLU(3, input_channel, stride=2)]

        for t, c, n, s in inverted_residual_setting:
            output_channel = int(c * width_mult)
            for i in range(n):
                stride = s if i == 0 else 1
                features.append(InvertedResidual(input_channel, output_channel, stride, expand_ratio=t))
                input_channel = output_channel

        features.append(ConvBNReLU(input_channel, self.last_channel, kernel_size=1))
        self.features = nn.Sequential(*features)

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(self.last_channel, num_classes)

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        B = x.shape[0]
        if x.dim() == 5:
            x = x.permute(0, 2, 1, 3, 4).contiguous()
            x = x.view(B * self.n_segment, 3, x.shape[3], x.shape[4])

        x = self.features(x)
        x = self.avgpool(x)
        x = x.view(B, self.n_segment, -1)
        x = x.mean(dim=1)
        x = self.dropout(x)
        x = self.fc(x)

        return x

    def get_features(self, x):
        B = x.shape[0]
        if x.dim() == 5:
            x = x.permute(0, 2, 1, 3, 4).contiguous()
            x = x.view(B * self.n_segment, 3, x.shape[3], x.shape[4])

        x = self.features(x)
        x = self.avgpool(x)
        x = x.view(B, self.n_segment, -1)

        return x


class ShuffleNetV2TSM(nn.Module):
    def __init__(self, num_classes: int = 400, model_size: str = '1.0x', 
                 n_segment: int = 8, dropout: float = 0.5):
        super().__init__()
        self.n_segment = n_segment
        self.num_classes = num_classes

        if model_size == '0.5x':
            stages_out_channels = [24, 48, 96, 192, 1024]
        elif model_size == '1.0x':
            stages_out_channels = [24, 116, 232, 464, 1024]
        elif model_size == '1.5x':
            stages_out_channels = [24, 176, 352, 704, 1024]
        elif model_size == '2.0x':
            stages_out_channels = [24, 244, 488, 976, 2048]
        else:
            raise ValueError(f"Unsupported model size: {model_size}")

        self.stem = nn.Sequential(
            nn.Conv2d(3, stages_out_channels[0], 3, 2, 1, bias=False),
            nn.BatchNorm2d(stages_out_channels[0]),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, 2, 1)
        )

        self.stage2 = self._make_stage(stages_out_channels[0], stages_out_channels[1], 4)
        self.stage3 = self._make_stage(stages_out_channels[1], stages_out_channels[2], 8)
        self.stage4 = self._make_stage(stages_out_channels[2], stages_out_channels[3], 4)

        self.conv5 = nn.Sequential(
            nn.Conv2d(stages_out_channels[3], stages_out_channels[4], 1, 1, 0, bias=False),
            nn.BatchNorm2d(stages_out_channels[4]),
            nn.ReLU(inplace=True)
        )

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(stages_out_channels[4], num_classes)

        self.tsm = TemporalShiftModule(n_segment=n_segment, n_div=8)
        self._initialize_weights()

    def _make_stage(self, in_channels: int, out_channels: int, num_blocks: int):
        blocks = []
        for i in range(num_blocks):
            if i == 0:
                blocks.append(self._downsample_block(in_channels, out_channels))
            else:
                blocks.append(self._basic_block(out_channels))
        return nn.Sequential(*blocks)

    def _downsample_block(self, in_channels: int, out_channels: int):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels // 2, 3, 2, 1, groups=in_channels, bias=False),
            nn.BatchNorm2d(out_channels // 2),
            nn.Conv2d(out_channels // 2, out_channels // 2, 1, 1, 0, bias=False),
            nn.BatchNorm2d(out_channels // 2),
            nn.ReLU(inplace=True)
        )

    def _basic_block(self, channels: int):
        return nn.Sequential(
            nn.Conv2d(channels, channels, 3, 1, 1, groups=channels, bias=False),
            nn.BatchNorm2d(channels),
            nn.Conv2d(channels, channels, 1, 1, 0, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True)
        )

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        B = x.shape[0]
        if x.dim() == 5:
            x = x.permute(0, 2, 1, 3, 4).contiguous()
            x = x.view(B * self.n_segment, 3, x.shape[3], x.shape[4])

        x = self.stem(x)
        x = self.tsm(x)
        x = self.stage2(x)
        x = self.tsm(x)
        x = self.stage3(x)
        x = self.tsm(x)
        x = self.stage4(x)
        x = self.conv5(x)
        x = self.avgpool(x)
        x = x.view(B, self.n_segment, -1)
        x = x.mean(dim=1)
        x = self.dropout(x)
        x = self.fc(x)

        return x


class LightweightRecognizer(BaseActionRecognizer):
    def __init__(
        self,
        device: str = "cpu",
        class_names: Optional[Dict[int, str]] = None,
        confidence_threshold: float = 0.5,
        fp16: bool = False,
        multi_label: bool = True,
        num_frames: int = 8,
        frame_size: int = 224,
        model_arch: str = "mobilenetv2",
        width_mult: float = 1.0,
        dropout: float = 0.5,
        mean: Tuple[float, float, float] = (0.45, 0.45, 0.45),
        std: Tuple[float, float, float] = (0.225, 0.225, 0.225),
    ) -> None:
        super().__init__(device, class_names, confidence_threshold, fp16, multi_label)
        self.num_frames: int = num_frames
        self.frame_size: int = frame_size
        self.model_arch: str = model_arch
        self.width_mult: float = width_mult
        self.dropout: float = dropout
        self.mean: Tuple[float, float, float] = mean
        self.std: Tuple[float, float, float] = std
        self._num_classes: int = len(self.class_names) if self.class_names else 400

    def load_model(self, model_path: Optional[str] = None) -> None:
        try:
            self.model_path = model_path or f"{self.model_arch}_kinetics"

            if self.model_arch == "mobilenetv2":
                self.model = MobileNetV2TSM(
                    num_classes=self._num_classes,
                    width_mult=self.width_mult,
                    n_segment=self.num_frames,
                    dropout=self.dropout
                )
            elif self.model_arch == "shufflenetv2":
                model_size = '1.0x' if self.width_mult >= 1.0 else '0.5x'
                self.model = ShuffleNetV2TSM(
                    num_classes=self._num_classes,
                    model_size=model_size,
                    n_segment=self.num_frames,
                    dropout=self.dropout
                )
            else:
                raise ValueError(f"Unsupported model architecture: {self.model_arch}")

            if model_path and not model_path.endswith("_kinetics"):
                state_dict = torch.load(model_path, map_location=self.device)
                if "state_dict" in state_dict:
                    state_dict = state_dict["state_dict"]
                self.model.load_state_dict(state_dict, strict=False)

            self.model = self.model.to(self.device)
            self.model.eval()

            if self.fp16:
                self.model = self.model.half()

            self._is_loaded = True

        except Exception as e:
            raise RuntimeError(f"Failed to load lightweight model: {e}")

    def preprocess(self, frames: List[np.ndarray]) -> torch.Tensor:
        self._validate_frames(frames, self.num_frames)

        frames = frames[:self.num_frames]
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
        clip_tensor = clip_tensor.permute(1, 0, 2, 3)
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

    def get_flops(self) -> float:
        if self.model_arch == "mobilenetv2":
            base_flops = 0.3
            return base_flops * self.width_mult * self.num_frames
        elif self.model_arch == "shufflenetv2":
            model_flops = {'0.5x': 0.04, '1.0x': 0.15, '1.5x': 0.3, '2.0x': 0.6}
            size_key = '1.0x' if self.width_mult >= 1.0 else '0.5x'
            return model_flops.get(size_key, 0.15) * self.num_frames
        return 0.3

    def get_model_size(self) -> float:
        if self.model_arch == "mobilenetv2":
            base_params = 3.5
            return base_params * self.width_mult
        elif self.model_arch == "shufflenetv2":
            model_params = {'0.5x': 1.4, '1.0x': 2.3, '1.5x': 3.5, '2.0x': 7.4}
            size_key = '1.0x' if self.width_mult >= 1.0 else '0.5x'
            return model_params.get(size_key, 2.3)
        return 3.5
