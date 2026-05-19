import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

PLATE_TYPE_CONFIG = {
    'blue': {
        'name': '蓝牌',
        'hsv_lower': (100, 100, 60),
        'hsv_upper': (130, 255, 255),
        'char_count': 7
    },
    'green': {
        'name': '绿牌(新能源)',
        'hsv_lower': (35, 43, 46),
        'hsv_upper': (90, 255, 255),
        'char_count': 8
    },
    'yellow': {
        'name': '黄牌',
        'hsv_lower': (15, 60, 60),
        'hsv_upper': (35, 255, 255),
        'char_count': 7
    },
    'new_energy_small': {
        'name': '新能源小车',
        'hsv_lower': (85, 43, 46),
        'hsv_upper': (110, 255, 255),
        'char_count': 8
    },
    'new_energy_large': {
        'name': '新能源大车',
        'hsv_lower': (85, 43, 46),
        'hsv_upper': (110, 255, 255),
        'char_count': 8
    }
}

OCR_CONFIG = {
    'use_angle_cls': True,
    'lang': 'ch',
    'show_log': False,
    'det_model_dir': None,
    'rec_model_dir': None,
    'cls_model_dir': None
}

ENHANCE_CONFIG = {
    'gamma': 1.2,
    'clip_limit': 2.0,
    'tile_grid_size': (8, 8),
    'bilateral_d': 9,
    'bilateral_sigma_color': 75,
    'bilateral_sigma_space': 75
}

DETECTION_CONFIG = {
    'min_area': 500,
    'max_area': 50000,
    'min_aspect_ratio': 1.5,
    'max_aspect_ratio': 5.0,
    'morph_kernel_size': (3, 3),
    'gaussian_kernel_size': (5, 5)
}
