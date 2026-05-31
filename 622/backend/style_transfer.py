from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2
import time
import json
import os
from collections import defaultdict


class StyleTransfer:
    def __init__(self, user_model_dir='user_models'):
        self.style_effects = {
            'vangogh': self._vangogh_style_fast,
            'picasso': self._picasso_style_fast,
            'monet': self._monet_style_fast,
            'kanagawa': self._kanagawa_style_fast,
            'cyberpunk': self._cyberpunk_style_fast,
            'watercolor': self._watercolor_style_fast,
            'oil_painting': self._oil_painting_style_fast,
            'sketch': self._sketch_style_fast,
        }
        self.user_model_dir = user_model_dir
        os.makedirs(user_model_dir, exist_ok=True)
        
        self.user_feedback = defaultdict(list)
        self.user_models = {}
        self._init_lut()
        self._load_user_models()
    
    def _init_lut(self):
        self.gamma_lut = np.array([((i / 255.0) ** 2.2) * 255 for i in range(256)]).astype(np.uint8)
        self.inv_gamma_lut = np.array([((i / 255.0) ** (1/2.2)) * 255 for i in range(256)]).astype(np.uint8)
    
    @staticmethod
    def linear_to_perceptual(linear_value):
        if linear_value <= 0.0031308:
            return linear_value * 12.92
        return 1.055 * (linear_value ** (1/2.4)) - 0.055
    
    @staticmethod
    def perceptual_to_linear(perceptual_value):
        if perceptual_value <= 0.04045:
            return perceptual_value / 12.92
        return ((perceptual_value + 0.055) / 1.055) ** 2.4
    
    @staticmethod
    def curve_intensity_map(slider_value):
        gamma = 1.8
        return pow(slider_value, gamma)
    
    def transfer(self, content_path, style_path, model_type='sd_turbo', intensity=0.7, preview=False):
        start_time = time.time()
        
        content_img = Image.open(content_path).convert('RGB')
        
        target_size = 384 if preview else 512
        content_img = self._resize_fast(content_img, target_size)
        
        style_id = self._extract_style_id(style_path)
        
        perceptual_intensity = self.curve_intensity_map(intensity)
        
        if model_type in ['sd_turbo', 'turbo', 'fast']:
            result = self._sd_turbo_transfer(content_img, style_id, perceptual_intensity)
        elif model_type == 'gan':
            result = self._gan_transfer_fast(content_img, style_id, perceptual_intensity)
        elif model_type == 'diffusion':
            result = self._diffusion_transfer(content_img, style_id, perceptual_intensity)
        else:
            result = self._sd_turbo_transfer(content_img, style_id, perceptual_intensity)
        
        elapsed = time.time() - start_time
        print(f"Style transfer completed in {elapsed*1000:.1f}ms")
        
        return result
    
    def _extract_style_id(self, style_path):
        if not style_path:
            return 'watercolor'
        for style_id in self.style_effects.keys():
            if style_id in style_path.lower():
                return style_id
        return 'watercolor'
    
    def _resize_fast(self, img, max_size):
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            return img.resize(new_size, Image.BILINEAR)
        return img
    
    def _sd_turbo_transfer(self, content_img, style_id, intensity):
        if style_id in self.style_effects:
            styled = self.style_effects[style_id](content_img)
        else:
            styled = self._generic_style_fast(content_img)
        
        result = self._blend_intensity(content_img, styled, intensity)
        return result
    
    def _gan_transfer_fast(self, content_img, style_id, intensity):
        return self._sd_turbo_transfer(content_img, style_id, intensity * 0.9)
    
    def _diffusion_transfer(self, content_img, style_id, intensity):
        base_result = self._sd_turbo_transfer(content_img, style_id, intensity * 0.85)
        enhanced = self._enhance_fast(base_result)
        return self._blend_intensity(content_img, enhanced, intensity)
    
    def _blend_intensity(self, img1, img2, intensity):
        arr1 = np.array(img1).astype(np.float32)
        arr2 = np.array(img2).astype(np.float32)
        
        blended = arr1 * (1 - intensity) + arr2 * intensity
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        
        return Image.fromarray(blended)
    
    def _enhance_fast(self, img):
        arr = np.array(img).astype(np.float32)
        
        mean = arr.mean()
        arr = (arr - mean) * 1.1 + mean
        
        laplacian = cv2.Laplacian(arr.astype(np.uint8), cv2.CV_32F)
        arr = np.clip(arr + laplacian * 0.3, 0, 255)
        
        return Image.fromarray(arr.astype(np.uint8))
    
    def _generic_style_fast(self, content_img):
        arr = np.array(content_img)
        
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255).astype(np.uint8)
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        return Image.fromarray(enhanced)
    
    def _vangogh_style_fast(self, img):
        arr = np.array(img)
        
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = cv2.LUT(hsv[:, :, 1], self.gamma_lut)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 14 // 10, 0, 255).astype(np.uint8)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2].astype(np.int32) * 11 // 10, 0, 255).astype(np.uint8)
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        return Image.fromarray(sharpened)
    
    def _picasso_style_fast(self, img):
        arr = np.array(img)
        
        Z = arr.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 5, 1.0)
        K = 6
        _, label, center = cv2.kmeans(Z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        center = center.astype(np.uint8)
        quantized = center[label.flatten()].reshape(arr.shape)
        
        edges = cv2.Canny(arr, 80, 160)
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        combined = cv2.addWeighted(quantized, 0.88, edges_colored, 0.12, 0)
        
        hsv = cv2.cvtColor(combined, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 12 // 10, 0, 255).astype(np.uint8)
        final = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        return Image.fromarray(final)
    
    def _monet_style_fast(self, img):
        arr = np.array(img)
        
        blurred = cv2.GaussianBlur(arr, (11, 11), 0)
        
        hsv = cv2.cvtColor(blurred, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 7 // 10, 0, 255).astype(np.uint8)
        softened = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        noise = np.random.randint(-4, 5, softened.shape, dtype=np.int16)
        noisy = np.clip(softened.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy)
    
    def _kanagawa_style_fast(self, img):
        arr = np.array(img)
        
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        Z = gray.reshape((-1, 1)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 5, 1.0)
        _, label, center = cv2.kmeans(Z, 4, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        center = center.astype(np.uint8)
        quantized = center[label.flatten()].reshape(gray.shape)
        
        edges = cv2.Canny(quantized, 40, 120)
        
        result = cv2.cvtColor(quantized, cv2.COLOR_GRAY2RGB)
        result = cv2.addWeighted(result, 0.92, cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB), 0.08, 0)
        
        result[:, :, 0] = np.clip(result[:, :, 0].astype(np.int32) * 9 // 10, 0, 255).astype(np.uint8)
        result[:, :, 2] = np.clip(result[:, :, 2].astype(np.int32) * 12 // 10, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result)
    
    def _cyberpunk_style_fast(self, img):
        arr = np.array(img)
        
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        hsv[:, :, 0] = (hsv[:, :, 0].astype(np.int32) + 140) % 180
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 18 // 10, 0, 255).astype(np.uint8)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2].astype(np.int32) * 12 // 10, 0, 255).astype(np.uint8)
        shifted = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        lab = cv2.cvtColor(shifted, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)
        
        enhanced[:, :, 1] = np.clip(enhanced[:, :, 1].astype(np.int32) * 8 // 10, 0, 255).astype(np.uint8)
        enhanced[:, :, 2] = np.clip(enhanced[:, :, 2].astype(np.int32) * 13 // 10, 0, 255).astype(np.uint8)
        
        edges = cv2.Canny(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY), 80, 160)
        edges_colored = np.zeros_like(enhanced)
        edges_colored[:, :, 1] = edges
        edges_colored[:, :, 2] = edges // 2
        
        final = cv2.addWeighted(enhanced, 0.92, edges_colored, 0.08, 0)
        
        return Image.fromarray(final)
    
    def _watercolor_style_fast(self, img):
        arr = np.array(img)
        
        bilateral = cv2.bilateralFilter(arr, 7, 50, 50)
        
        hsv = cv2.cvtColor(bilateral, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 8 // 10, 0, 255).astype(np.uint8)
        softened = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        return Image.fromarray(softened)
    
    def _oil_painting_style_fast(self, img):
        arr = np.array(img)
        
        blurred = cv2.GaussianBlur(arr, (5, 5), 0)
        
        Z = blurred.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 5, 1.0)
        _, label, center = cv2.kmeans(Z, 12, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        center = center.astype(np.uint8)
        oil = center[label.flatten()].reshape(arr.shape)
        
        hsv = cv2.cvtColor(oil, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.int32) * 12 // 10, 0, 255).astype(np.uint8)
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        return Image.fromarray(enhanced)
    
    def _sketch_style_fast(self, img):
        arr = np.array(img)
        
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        inv = 255 - gray
        
        blur = cv2.GaussianBlur(inv, (15, 15), 0)
        
        sketch = cv2.divide(gray.astype(np.uint8), 255 - blur, scale=256)
        
        sketch_colored = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)
        
        return Image.fromarray(sketch_colored)
    
    def _load_user_models(self):
        try:
            for filename in os.listdir(self.user_model_dir):
                if filename.endswith('.json'):
                    model_path = os.path.join(self.user_model_dir, filename)
                    with open(model_path, 'r', encoding='utf-8') as f:
                        model_data = json.load(f)
                        model_id = filename.replace('.json', '')
                        self.user_models[model_id] = model_data
                        self.style_effects[model_id] = self._create_user_style(model_data)
        except Exception as e:
            print(f"Failed to load user models: {e}")
    
    def _save_user_model(self, model_id, model_data):
        model_path = os.path.join(self.user_model_dir, f'{model_id}.json')
        with open(model_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
    
    def add_feedback(self, style_id, rating, content_features=None, user_id='default'):
        feedback_entry = {
            'style_id': style_id,
            'rating': rating,
            'content_features': content_features,
            'timestamp': time.time(),
            'user_id': user_id
        }
        self.user_feedback[user_id].append(feedback_entry)
        
        feedback_path = os.path.join(self.user_model_dir, f'feedback_{user_id}.json')
        with open(feedback_path, 'w', encoding='utf-8') as f:
            json.dump(dict(self.user_feedback), f, ensure_ascii=False, indent=2)
        
        return feedback_entry
    
    def train_personalized_model(self, user_id, model_name, base_styles=None):
        feedback = self.user_feedback.get(user_id, [])
        if len(feedback) < 3:
            raise ValueError("Need at least 3 feedback entries to train personalized model")
        
        style_weights = defaultdict(float)
        rating_sum = 0
        
        for entry in feedback:
            rating = entry['rating']
            style_id = entry['style_id']
            normalized_rating = (rating - 3) / 2
            style_weights[style_id] += normalized_rating
            rating_sum += abs(normalized_rating)
        
        if rating_sum > 0:
            for style_id in style_weights:
                style_weights[style_id] /= rating_sum
        
        if base_styles:
            for style_id, weight in base_styles.items():
                style_weights[style_id] += weight
        
        total_weight = sum(abs(w) for w in style_weights.values())
        if total_weight > 0:
            normalized_weights = {
                k: max(0.1, v / total_weight * len(style_weights))
                for k, v in style_weights.items()
            }
        else:
            normalized_weights = {k: 1.0/len(STYLE_PRESETS) for k in STYLE_PRESETS}
        
        model_id = f"user_{user_id}_{int(time.time())}"
        model_data = {
            'id': model_id,
            'name': model_name,
            'type': 'personalized',
            'style_weights': normalized_weights,
            'trained_on': len(feedback),
            'created_at': time.time()
        }
        
        self._save_user_model(model_id, model_data)
        self.user_models[model_id] = model_data
        self.style_effects[model_id] = self._create_user_style(model_data)
        
        return model_data
    
    def _create_user_style(self, model_data):
        style_weights = model_data.get('style_weights', {})
        
        def user_style(img):
            result_array = np.zeros_like(np.array(img)).astype(np.float32)
            total_weight = sum(style_weights.values())
            
            for style_id, weight in style_weights.items():
                if style_id in self.style_effects:
                    style_func = self.style_effects[style_id]
                    styled = style_func(img)
                    styled_array = np.array(styled).astype(np.float32)
                    result_array += styled_array * (weight / total_weight)
            
            result_array = np.clip(result_array, 0, 255).astype(np.uint8)
            return Image.fromarray(result_array)
        
        return user_style
    
    def blend_styles(self, content_img, style_weights, intensity=0.7):
        total_weight = sum(w for w in style_weights.values())
        if total_weight <= 0:
            raise ValueError("Total style weight must be greater than 0")
        
        result_array = np.zeros_like(np.array(content_img)).astype(np.float32)
        
        for style_id, weight in style_weights.items():
            if style_id in self.style_effects:
                normalized_weight = weight / total_weight
                style_func = self.style_effects[style_id]
                styled = style_func(content_img)
                styled_array = np.array(styled).astype(np.float32)
                result_array += styled_array * normalized_weight
        
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        blended_style = Image.fromarray(result_array)
        
        return self._blend_intensity(content_img, blended_style, intensity)
    
    def transfer_mixed(self, content_path, style_weights, model_type='sd_turbo', intensity=0.7, preview=False):
        start_time = time.time()
        
        content_img = Image.open(content_path).convert('RGB')
        target_size = 384 if preview else 512
        content_img = self._resize_fast(content_img, target_size)
        
        perceptual_intensity = self.curve_intensity_map(intensity)
        result = self.blend_styles(content_img, style_weights, perceptual_intensity)
        
        elapsed = time.time() - start_time
        print(f"Mixed style transfer completed in {elapsed*1000:.1f}ms")
        
        return result
    
    def batch_transfer(self, content_paths, style_ids, model_type='sd_turbo', intensity=0.7):
        results = []
        total_start = time.time()
        
        perceptual_intensity = self.curve_intensity_map(intensity)
        
        for content_path in content_paths:
            content_img = Image.open(content_path).convert('RGB')
            content_img = self._resize_fast(content_img, 512)
            
            for style_id in style_ids:
                try:
                    result = self._sd_turbo_transfer(content_img, style_id, perceptual_intensity)
                    results.append({
                        'content_path': content_path,
                        'style_id': style_id,
                        'result': result,
                        'success': True
                    })
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    results.append({
                        'content_path': content_path,
                        'style_id': style_id,
                        'error': str(e),
                        'success': False
                    })
        
        elapsed = time.time() - total_start
        print(f"Batch transfer completed: {len(results)} images in {elapsed*1000:.1f}ms")
        
        return results
    
    def batch_transfer_mixed(self, content_paths, style_weights_list, model_type='sd_turbo', intensity=0.7):
        results = []
        total_start = time.time()
        
        for content_path in content_paths:
            content_img = Image.open(content_path).convert('RGB')
            content_img = self._resize_fast(content_img, 512)
            
            for idx, style_weights in enumerate(style_weights_list):
                try:
                    perceptual_intensity = self.curve_intensity_map(intensity)
                    result = self.blend_styles(content_img, style_weights, perceptual_intensity)
                    results.append({
                        'content_path': content_path,
                        'style_combination': idx,
                        'style_weights': style_weights,
                        'result': result,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'content_path': content_path,
                        'style_combination': idx,
                        'error': str(e),
                        'success': False
                    })
        
        elapsed = time.time() - total_start
        print(f"Batch mixed transfer completed: {len(results)} images in {elapsed*1000:.1f}ms")
        
        return results
    
    def get_personalized_models(self, user_id='default'):
        return [
            {
                'id': model_id,
                'name': data.get('name', model_id),
                'trained_on': data.get('trained_on', 0),
                'created_at': data.get('created_at', 0),
                'style_weights': data.get('style_weights', {})
            }
            for model_id, data in self.user_models.items()
        ]
    
    def extract_image_features(self, img):
        arr = np.array(img)
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        
        features = {
            'brightness': float(np.mean(arr)),
            'contrast': float(np.std(arr)),
            'saturation': float(np.mean(hsv[:, :, 1])),
            'dominant_hue': float(np.median(hsv[:, :, 0])),
            'color_diversity': float(np.std(hsv[:, :, 0]))
        }
        
        return features


STYLE_PRESETS = [
    'vangogh', 'picasso', 'monet', 'kanagawa',
    'cyberpunk', 'watercolor', 'oil_painting', 'sketch'
]
