from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
from pathlib import Path


def process_image(input_path, output_path, max_size=1024):
    img = Image.open(input_path)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    
    img.save(output_path, 'JPEG', quality=95)
    return output_path


def adjust_intensity(content_img, style_img, intensity):
    content_array = np.array(content_img).astype(np.float32)
    style_array = np.array(style_img).astype(np.float32)
    
    blended = content_array * (1 - intensity) + style_array * intensity
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    
    return Image.fromarray(blended)


def apply_color_transfer(content_img, style_img):
    content_lab = cv2.cvtColor(np.array(content_img), cv2.COLOR_RGB2LAB)
    style_lab = cv2.cvtColor(np.array(style_img), cv2.COLOR_RGB2LAB)
    
    content_mean, content_std = cv2.meanStdDev(content_lab)
    style_mean, style_std = cv2.meanStdDev(style_lab)
    
    content_lab = ((content_lab - content_mean.reshape(1, 1, 3)) * 
                   (style_std.reshape(1, 1, 3) / (content_std.reshape(1, 1, 3) + 1e-6)) + 
                   style_mean.reshape(1, 1, 3))
    
    content_lab = np.clip(content_lab, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(content_lab, cv2.COLOR_LAB2RGB)
    
    return Image.fromarray(result)


def enhance_image(img, brightness=1.0, contrast=1.0, saturation=1.0):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(saturation)
    
    return img


def resize_for_preview(img, max_size=512):
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    return img
