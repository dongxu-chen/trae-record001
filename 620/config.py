import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_CONFIG = {
    'edsr': {
        'scale': 4,
        'num_features': 64,
        'num_res_blocks': 16,
        'res_scale': 1.0,
        'rgb_range': 255,
        'n_colors': 3,
    },
    'rcan': {
        'scale': 4,
        'num_features': 64,
        'num_rg': 10,
        'num_rcab': 20,
        'reduction': 16,
        'rgb_range': 255,
        'n_colors': 3,
    }
}

PROCESS_CONFIG = {
    'target_fps': 30,
    'batch_size': 1,
    'temp_dir': os.path.join(BASE_DIR, 'temp'),
    'output_dir': os.path.join(BASE_DIR, 'output'),
    'device': 'auto',
    'half_precision': False,
}

DENOISE_CONFIG = {
    'enable': True,
    'num_frames': 5,
    'fusion_method': 'flow_guided',
    'temporal_weight': 0.15,
    'center_weight': 0.4,
    'enable_flow_alignment': True,
    'flow_method': 'farneback',
}

TEMPORAL_CONFIG = {
    'enable': True,
    'method': 'flow_guided',
    'alpha': 0.8,
    'flow_threshold': 0.5,
    'consistency_weight': 0.3,
    'enable_deflicker': True,
    'deflicker_strength': 0.3,
    'window_size': 5,
}

BITRATE_CONFIG = {
    'enable': True,
    'mode': 'auto',
    'crf_range': (15, 28),
    'target_quality': 'high',
    'preset': 'slow',
    'codec': 'libx264',
    'enable_texture_analysis': True,
    'texture_weight': 0.6,
    'motion_weight': 0.4,
}

QUALITY_PRESETS = {
    'low': {'crf': 28, 'bitrate_factor': 0.5, 'preset': 'fast'},
    'medium': {'crf': 23, 'bitrate_factor': 1.0, 'preset': 'medium'},
    'high': {'crf': 18, 'bitrate_factor': 2.0, 'preset': 'slow'},
    'ultra': {'crf': 15, 'bitrate_factor': 3.0, 'preset': 'veryslow'},
}

FACE_ENHANCE_CONFIG = {
    'enable': False,
    'face_scale': 8,
    'confidence_threshold': 0.7,
    'margin': 0.2,
    'blend_alpha': 0.8,
    'tracking': True,
    'track_window': 5,
}

SUBTITLE_CONFIG = {
    'enable': False,
    'min_area': 100,
    'max_area_ratio': 0.5,
    'aspect_ratio_range': (0.1, 10.0),
    'sharpen_amount': 1.5,
    'edge_enhance': 1.2,
    'contrast_adjust': 1.1,
    'denoise_strength': 5,
    'detection_interval': 10,
}

REALTIME_CONFIG = {
    'enable': False,
    'target_fps': 30,
    'batch_size': 4,
    'prefetch_frames': 10,
    'use_tensorrt': False,
    'use_cuda_graph': False,
    'frame_skip': False,
    'max_resolution': (1920, 1080),
    'async_transfer': True,
    'pipeline_depth': 3,
}
