import cv2
import numpy as np
from typing import Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class RainFogResult:
    enhanced_image: np.ndarray
    rain_removed: np.ndarray
    fog_removed: np.ndarray
    rain_intensity: str
    fog_density: float
    enhancement_strength: float


class FogRemover:
    def __init__(self, omega: float = 0.95, t0: float = 0.1, radius: int = 15):
        self.omega = omega
        self.t0 = t0
        self.radius = radius

    def dark_channel(self, image: np.ndarray) -> np.ndarray:
        b, g, r = cv2.split(image)
        min_channel = np.minimum(np.minimum(b, g), r)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.radius, self.radius))
        dark = cv2.erode(min_channel, kernel)
        
        return dark

    def estimate_atmospheric_light(self, image: np.ndarray, dark_channel: np.ndarray) -> np.ndarray:
        h, w = dark_channel.shape
        num_pixels = h * w
        num_brightest = int(max(num_pixels * 0.001, 1))
        
        flat_dark = dark_channel.flatten()
        indices = np.argsort(flat_dark)[-num_brightest:]
        
        atmospheric_light = np.zeros(3, dtype=np.float64)
        for c in range(3):
            channel = image[:, :, c].flatten()
            atmospheric_light[c] = np.mean(channel[indices])
        
        return atmospheric_light

    def estimate_transmission(self, image: np.ndarray, atmospheric_light: np.ndarray) -> np.ndarray:
        epsilon = 1e-6
        atmospheric_light_safe = np.maximum(atmospheric_light, epsilon)
        normalized_image = image.astype(np.float64) / atmospheric_light_safe
        
        dark = self.dark_channel(normalized_image)
        transmission = 1 - self.omega * dark
        
        return transmission

    def refine_transmission(self, image: np.ndarray, transmission: np.ndarray,
                            epsilon: float = 1e-4, r: int = 60) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
        refined = cv2.ximgproc.guidedFilter(gray, transmission, r, epsilon) if hasattr(cv2, 'ximgproc') else transmission
        
        return refined

    def remove_fog(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        if image.dtype == np.uint8:
            image_float = image.astype(np.float64) / 255.0
        else:
            image_float = image.copy()
        
        dark = self.dark_channel(image_float)
        atmospheric_light = self.estimate_atmospheric_light(image_float, dark)
        transmission = self.estimate_transmission(image_float, atmospheric_light)
        
        try:
            transmission = self.refine_transmission(image, transmission)
        except:
            pass
        
        transmission = np.maximum(transmission, self.t0)
        
        fog_density = 1 - np.mean(transmission)
        
        scene_radiance = np.zeros_like(image_float)
        for c in range(3):
            scene_radiance[:, :, c] = (image_float[:, :, c] - atmospheric_light[c]) / transmission + atmospheric_light[c]
        
        scene_radiance = np.clip(scene_radiance, 0, 1)
        
        if image.dtype == np.uint8:
            scene_radiance = (scene_radiance * 255).astype(np.uint8)
        
        return scene_radiance, transmission, fog_density


class ContrastEnhancer:
    def __init__(self, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)):
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

    def enhance(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            l_enhanced = self.clahe.apply(l)
            
            enhanced_lab = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        else:
            enhanced = self.clahe.apply(image)
        
        return enhanced


class GammaCorrector:
    def __init__(self, gamma: float = 1.0):
        self.gamma = gamma

    def correct(self, image: np.ndarray) -> np.ndarray:
        inv_gamma = 1.0 / self.gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
        return cv2.LUT(image, table)


class RainFogEnhancer:
    def __init__(self, model=None, device=None):
        from config import Config
        
        self.device = device or Config.DEVICE
        self.model = model
        
        self.fog_remover = FogRemover(omega=0.95, t0=0.1, radius=15)
        self.contrast_enhancer = ContrastEnhancer(clip_limit=2.0)
        self.gamma_corrector = GammaCorrector(gamma=1.2)
        
        from .rain_estimation import RainEstimator
        self.rain_estimator = RainEstimator()

    def estimate_fog_density(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        std_dev = np.std(gray)
        histogram = cv2.calcHist([gray], [0], None, [256], [0, 256])
        histogram = histogram.flatten() / histogram.sum()
        
        entropy = -np.sum(histogram[histogram > 0] * np.log2(histogram[histogram > 0]))
        
        fog_score = (1 - std_dev / 128) * 0.5 + (1 - entropy / 8) * 0.5
        
        return max(0, min(1, fog_score))

    def process_image(self, image: np.ndarray, 
                     remove_rain: bool = True,
                     remove_fog: bool = True,
                     enhance: bool = True) -> RainFogResult:
        result = image.copy()
        rain_intensity = 'none'
        fog_density = 0.0
        enhancement_strength = 0.0
        
        if remove_rain and self.model is not None:
            rain_result = self.rain_estimator.estimate(image, return_visualization=False)
            rain_intensity = rain_result.intensity.value
            
            result = self._apply_derain(result)
        
        fog_removed = result.copy()
        if remove_fog:
            fog_density = self.estimate_fog_density(image)
            
            if fog_density > 0.2:
                fog_removed, _, _ = self.fog_remover.remove_fog(result)
                result = fog_removed
                enhancement_strength += fog_density
        
        if enhance:
            result = self.contrast_enhancer.enhance(result)
            result = self.gamma_corrector.correct(result)
            enhancement_strength = min(enhancement_strength + 0.3, 1.0)
        
        return RainFogResult(
            enhanced_image=result,
            rain_removed=self._apply_derain(image) if remove_rain and self.model else image,
            fog_removed=fog_removed,
            rain_intensity=rain_intensity,
            fog_density=fog_density,
            enhancement_strength=enhancement_strength
        )

    def _apply_derain(self, image: np.ndarray) -> np.ndarray:
        if self.model is None:
            return image
        
        import torch
        
        if len(image.shape) == 3:
            if image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        
        if image.dtype == np.uint8:
            image_float = image_rgb.astype(np.float32) / 255.0
        else:
            image_float = image_rgb
        
        tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            derained_tensor = self.model(tensor)
        
        derained = derained_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        derained = np.clip(derained, 0, 1)
        derained = (derained * 255).astype(np.uint8)
        derained_bgr = cv2.cvtColor(derained, cv2.COLOR_RGB2BGR)
        
        return derained_bgr

    def process_video(self, input_path: str, output_path: str,
                     remove_rain: bool = True,
                     remove_fog: bool = True,
                     enhance: bool = True,
                     show_progress: bool = True) -> Dict:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        avg_fog_density = 0.0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            result = self.process_image(frame, remove_rain, remove_fog, enhance)
            out.write(result.enhanced_image)
            
            avg_fog_density += result.fog_density
            frame_count += 1
            
            if show_progress and frame_count % 10 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Processing: {frame_count}/{total_frames} frames ({progress:.1f}%)", end='\r')
        
        cap.release()
        out.release()
        
        if show_progress:
            print(f"\nVideo processing completed. {frame_count} frames processed.")
        
        return {
            'input_path': input_path,
            'output_path': output_path,
            'fps': fps,
            'width': width,
            'height': height,
            'total_frames': frame_count,
            'avg_fog_density': avg_fog_density / frame_count if frame_count > 0 else 0
        }


def add_fog(image: np.ndarray, density: float = 0.5) -> np.ndarray:
    if image.dtype == np.uint8:
        image_float = image.astype(np.float32) / 255.0
    else:
        image_float = image.copy()
    
    fog_color = np.array([0.8, 0.85, 0.9])
    
    foggy_image = image_float * (1 - density) + fog_color * density
    foggy_image = np.clip(foggy_image, 0, 1)
    
    if image.dtype == np.uint8:
        foggy_image = (foggy_image * 255).astype(np.uint8)
    
    return foggy_image


def add_rain_fog(image: np.ndarray, rain_intensity: str = 'medium',
                 fog_density: float = 0.3) -> np.ndarray:
    from data import RainSynthesizer
    
    rain_synth = RainSynthesizer(intensity=rain_intensity)
    
    if len(image.shape) == 3:
        if image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    
    rainy = rain_synth(image_rgb)
    rainy_bgr = cv2.cvtColor((rainy * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    
    rainy_foggy = add_fog(rainy_bgr, density=fog_density)
    
    return rainy_foggy
