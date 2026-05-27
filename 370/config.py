"""
遥感图像变化检测 - 配置文件
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
CHECKPOINT_DIR = os.path.join(BASE_DIR, 'checkpoints')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

INPUT_IMAGE_1 = os.path.join(DATA_DIR, 'time1.tif')
INPUT_IMAGE_2 = os.path.join(DATA_DIR, 'time2.tif')
LABEL_IMAGE = os.path.join(DATA_DIR, 'label.tif')

MODEL_CONFIG = {
    'in_channels': 4,
    'out_channels': 2,
    'base_channels': 64,
    'num_blocks': 4,
    'bilinear': True,
}

TRAIN_CONFIG = {
    'batch_size': 4,
    'num_epochs': 100,
    'learning_rate': 1e-4,
    'weight_decay': 1e-5,
    'train_ratio': 0.8,
    'num_workers': 0,
    'patch_size': 256,
    'stride': 128,
}

CLASS_NAMES = ['未变化', '建筑物变化', '植被变化', '水体变化', '其他变化']
CLASS_COLORS = [
    [0, 0, 0],
    [255, 0, 0],
    [0, 255, 0],
    [0, 0, 255],
    [255, 255, 0],
]

PIXEL_SIZE = 1.0
