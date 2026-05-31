from typing import Dict, Optional, Tuple

import torch

from .base import BaseActionRecognizer
from .timesformer import TimeSformerRecognizer
from .videomae import VideoMAERecognizer
from .lightweight import LightweightRecognizer


_MODEL_CACHE: Dict[str, BaseActionRecognizer] = {}


def _get_cache_key(
    model_type: str,
    device: str,
    fp16: bool,
    multi_label: bool,
) -> str:
    return f"{model_type}_{device}_{fp16}_{multi_label}"


def get_model(
    model_type: str,
    device: str = "cpu",
    class_names: Optional[Dict[int, str]] = None,
    confidence_threshold: float = 0.5,
    fp16: bool = False,
    multi_label: bool = True,
    num_frames: int = 16,
    frame_size: int = 224,
    mean: Tuple[float, float, float] = (0.45, 0.45, 0.45),
    std: Tuple[float, float, float] = (0.225, 0.225, 0.225),
    use_cache: bool = True,
) -> BaseActionRecognizer:
    model_type = model_type.lower().strip()

    cache_key = _get_cache_key(model_type, device, fp16, multi_label)

    if use_cache and cache_key in _MODEL_CACHE:
        cached_model = _MODEL_CACHE[cache_key]
        cached_model.class_names = class_names or cached_model.class_names
        cached_model.confidence_threshold = confidence_threshold
        return cached_model

    try:
        if model_type == "timesformer":
            model = TimeSformerRecognizer(
                device=device,
                class_names=class_names,
                confidence_threshold=confidence_threshold,
                fp16=fp16,
                multi_label=multi_label,
                num_frames=num_frames,
                frame_size=frame_size,
                mean=mean,
                std=std,
            )
        elif model_type == "videomae":
            model = VideoMAERecognizer(
                device=device,
                class_names=class_names,
                confidence_threshold=confidence_threshold,
                fp16=fp16,
                multi_label=multi_label,
                num_frames=num_frames,
                frame_size=frame_size,
                mean=mean,
                std=std,
            )
        elif model_type in ["mobilenetv2", "shufflenetv2", "lightweight"]:
            model_arch = model_type if model_type != "lightweight" else "mobilenetv2"
            model = LightweightRecognizer(
                device=device,
                class_names=class_names,
                confidence_threshold=confidence_threshold,
                fp16=fp16,
                multi_label=multi_label,
                num_frames=8,
                frame_size=224,
                model_arch=model_arch,
                width_mult=1.0,
                mean=mean,
                std=std,
            )
        else:
            raise ValueError(
                f"Unsupported model type: '{model_type}'. "
                f"Supported types are: 'timesformer', 'videomae', 'mobilenetv2', 'shufflenetv2', 'lightweight'"
            )

        model.load_model()

        if use_cache:
            _MODEL_CACHE[cache_key] = model

        return model

    except ImportError as e:
        raise RuntimeError(
            f"Failed to load dependencies for model '{model_type}': {e}"
        )
    except torch.cuda.OutOfMemoryError as e:
        raise RuntimeError(
            f"CUDA out of memory when loading model '{model_type}'. "
            f"Consider using CPU or reducing model size: {e}"
        )
    except RuntimeError as e:
        raise RuntimeError(
            f"Failed to load model '{model_type}': {e}"
        )
    except Exception as e:
        raise RuntimeError(
            f"Unexpected error loading model '{model_type}': {e}"
        )


def clear_model_cache() -> None:
    _MODEL_CACHE.clear()


def get_cached_model_keys() -> list:
    return list(_MODEL_CACHE.keys())


def remove_from_cache(model_type: str, device: str, fp16: bool = False) -> bool:
    cache_key = _get_cache_key(model_type, device, fp16)
    if cache_key in _MODEL_CACHE:
        del _MODEL_CACHE[cache_key]
        return True
    return False
