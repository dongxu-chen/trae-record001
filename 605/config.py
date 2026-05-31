import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODEL_DIR = os.path.join(BASE_DIR, "checkpoints")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

MVSNET_CONFIG = {
    "num_depth": 192,
    "interval_scale": 1.06,
    "depth_min": 0.5,
    "depth_max": 10.0,
    "num_groups": 1,
    "feat_channels": 32,
    "cost_volume_channels": 32,
    "refine_channels": 32,
    "img_width": 640,
    "img_height": 512,
}

RECONSTRUCTION_CONFIG = {
    "prob_threshold": 0.8,
    "num_consistent": 3,
    "voxel_size": 0.005,
    "poisson_depth": 9,
    "simplify_factor": 0.5,
    "smooth_iter": 10,
}

FLASK_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": False,
    "max_content_length": 500 * 1024 * 1024,
}

CUDA_CONFIG = {
    "device": "cuda",
    "gpu_id": 0,
}

REALTIME_CONFIG = {
    "frame_skip": 2,
    "voxel_size": 0.01,
    "max_queue_size": 30,
    "keyframe_interval": 5,
    "max_keyframes": 20,
    "min_motion_for_keyframe": 5.0,
}

DYNAMIC_REMOVAL_CONFIG = {
    "num_frames": 5,
    "depth_variance_thresh": 0.05,
    "motion_thresh": 5.0,
    "min_consistent_views": 3,
    "bg_history_length": 30,
    "bg_ratio": 0.3,
    "min_motion_area": 100,
}

TEXTURE_CONFIG = {
    "atlas_resolution": 4096,
    "chart_padding": 4,
    "gaussian_sigma": 1.0,
    "blending_mode": "median",
    "visibility_thresh": 0.0,
}
