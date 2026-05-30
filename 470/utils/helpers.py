import os
import cv2
import numpy as np
from datetime import datetime
from config import Config


def load_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def save_image(image, save_path, convert_bgr=True):
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif convert_bgr and image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    cv2.imwrite(save_path, image)
    return save_path


def normalize_image(image):
    if image.max() > 1.0:
        image = image.astype(np.float32) / 255.0
    return image


def tensor_to_numpy(tensor):
    try:
        import torch
        if isinstance(tensor, torch.Tensor):
            tensor = tensor.detach().cpu().numpy()
    except ImportError:
        pass
    if tensor.ndim == 4:
        tensor = tensor.squeeze(0)
    if tensor.ndim == 3 and tensor.shape[0] in [1, 3]:
        tensor = tensor.transpose(1, 2, 0)
    if tensor.shape[-1] == 1:
        tensor = tensor.squeeze(-1)
    return tensor


def get_file_list(directory, extensions=None):
    if extensions is None:
        extensions = Config.ALLOWED_EXTENSIONS
    
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().split('.')[-1] in extensions:
                file_list.append(os.path.join(root, file))
    return sorted(file_list)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def generate_output_filename(prefix='saliency', ext='.png'):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"{prefix}_{timestamp}{ext}"


def min_max_normalize(saliency_map):
    min_val = saliency_map.min()
    max_val = saliency_map.max()
    if max_val - min_val < 1e-8:
        return np.zeros_like(saliency_map)
    return (saliency_map - min_val) / (max_val - min_val)
