"""
图像风格迁移库
使用PyTorch + VGG19 + Perceptual Loss实现快速风格迁移

特性:
- 大图分块处理，重叠拼贴减少接缝
- 自适应强度调度，低强度保留更多纹理
- 批量处理保持原始宽高比，黑边填充对齐
- 视频风格迁移，帧间稳定避免闪烁
- 任意风格即时迁移，无需重新训练
- 风格插值，双风格平滑过渡
"""

from .stylizer import Stylizer
from .vgg import VGG19Extractor
from .losses import (
    PerceptualLoss, AdaptiveScheduler,
    ContentLoss, StyleLoss, TotalVariationLoss,
    MultiStyleLoss, TemporalLoss,
)
from .utils import (
    load_image, save_image, show_images, prepare_transform,
    extract_patches, merge_patches, create_blend_mask,
)
from .styles import list_available_styles, get_style_config, PRETRAINED_STYLES
from .video import (
    extract_frames, frames_to_video,
    TemporalLoss as VideoTemporalLoss,
    OpticalFlowTemporalLoss,
)

__version__ = "3.0.0"
__all__ = [
    "Stylizer",
    "VGG19Extractor",
    "PerceptualLoss",
    "AdaptiveScheduler",
    "ContentLoss",
    "StyleLoss",
    "TotalVariationLoss",
    "MultiStyleLoss",
    "TemporalLoss",
    "load_image",
    "save_image",
    "show_images",
    "prepare_transform",
    "extract_patches",
    "merge_patches",
    "create_blend_mask",
    "list_available_styles",
    "get_style_config",
    "PRETRAINED_STYLES",
    "extract_frames",
    "frames_to_video",
    "VideoTemporalLoss",
    "OpticalFlowTemporalLoss",
]
