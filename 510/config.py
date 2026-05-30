import torch
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_WEIGHTS_DIR = BASE_DIR / "weights"
MODEL_WEIGHTS_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

VESPCN_CONFIG = {
    "scale_factor": 2,
    "num_channels": 3,
    "num_frames": 3,
    "base_channels": 64,
    "num_residual_blocks": 6,
    "quality_weight": 0.5,
}

TRAINING_CONFIG = {
    "lr": 1e-4,
    "epochs": 100,
    "batch_size": 4,
    "interp_weight": 0.5,
    "sr_weight": 0.5,
    "temporal_weight": 0.1,
    "flow_weight": 0.05,
    "patch_size": 64,
    "lr_scheduler": "cosine",
    "gradient_clip": 0.5,
}

MOBILE_CONFIG = {
    "target_device": "android",
    "model_format": "onnx",
    "input_resolution": (480, 640),
    "max_model_size_mb": 10.0,
    "target_fps": 30.0,
    "use_half": True,
    "num_threads": 4,
    "lightweight_channels": 32,
    "lightweight_res_blocks": 2,
}

PROCESSING_CONFIG = {
    "batch_size": 1,
    "num_workers": 4,
    "temp_format": "frames_%06d.png",
    "output_format": "mp4",
    "codec": "libx264",
    "crf": 20,
}

QUALITY_METRICS = {
    "metrics": ["psnr", "ssim", "lpips"],
    "lpips_net": "alex",
}

STREAMLIT_CONFIG = {
    "page_title": "视频插帧超分联合处理",
    "page_icon": "🎬",
    "layout": "wide",
    "max_file_size": 2048,
}
