import cv2
import numpy as np


class DarkChannelDehazer:
    def __init__(self, patch_size=15, omega=None, t_min=None, atmospheric_light=240,
                 sky_detection=True, sky_threshold=0.7, dehaze_strength=None,
                 adaptive_params=True, auto_brightness=True,
                 enhance_enabled=False, enhance_strength=0.5):
        self.patch_size = patch_size
        self._default_omega = 0.95
        self._default_t_min = 0.1
        self._default_strength = 1.0
        self.omega = omega if omega is not None else self._default_omega
        self.t_min = t_min if t_min is not None else self._default_t_min
        self.atmospheric_light = atmospheric_light
        self.sky_detection = sky_detection
        self.sky_threshold = sky_threshold
        self.dehaze_strength = dehaze_strength if dehaze_strength is not None else self._default_strength
        self.adaptive_params = adaptive_params
        self.auto_brightness = auto_brightness
        self.enhance_enabled = enhance_enabled
        self.enhance_strength = enhance_strength
        self.last_haze_density = None
        self.last_sky_mask = None
        self.last_atmospheric_light = None

    def _dark_channel(self, img):
        min_channel = np.min(img, axis=2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.patch_size, self.patch_size))
        dark = cv2.erode(min_channel, kernel)
        return dark

    def _estimate_atmospheric_light(self, img, dark, sky_mask=None):
        m, n = dark.shape
        flat_dark = dark.reshape(-1)
        flat_img = img.reshape(-1, 3)
        num_pixels = m * n
        if sky_mask is not None and self.sky_detection:
            non_sky_mask = (1 - sky_mask).reshape(-1)
            valid_indices = np.where(non_sky_mask > 0.5)[0]
            if len(valid_indices) > num_pixels * 0.1:
                flat_dark = flat_dark[valid_indices]
                flat_img = flat_img[valid_indices]
                num_pixels = len(valid_indices)
        top_pixels = max(int(num_pixels * 0.001), 10)
        indices = np.argsort(flat_dark)[-top_pixels:]
        atmospheric_light = np.max(flat_img[indices], axis=0)
        return atmospheric_light

    def estimate_haze_density(self, img):
        img_float = img.astype(np.float32) / 255.0
        dark = self._dark_channel(img_float)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        brightness = np.mean(gray)
        dark_mean = np.mean(dark)
        saturation = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32) / 255.0
        sat_mean = np.mean(saturation)
        haze_indicator = 1.0 - dark_mean
        haze_score = (haze_indicator * 0.5 +
                      brightness * 0.3 +
                      (1.0 - sat_mean) * 0.2)
        haze_score = np.clip(haze_score, 0.0, 1.0)
        self.last_haze_density = haze_score
        return haze_score

    def _detect_sky_region(self, img):
        h, w = img.shape[:2]
        img_float = img.astype(np.float32) / 255.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        edge_magnitude = cv2.normalize(edge_magnitude, None, 0, 1, cv2.NORM_MINMAX)
        brightness = gray.astype(np.float32) / 255.0
        blue_channel = img_float[:, :, 0]
        green_channel = img_float[:, :, 1]
        red_channel = img_float[:, :, 2]
        blue_reduce = np.clip(blue_channel - red_channel, 0, 1)
        green_reduce = np.clip(green_channel - red_channel, 0, 1)
        color_likelihood = blue_reduce * 0.6 + green_reduce * 0.4
        position_penalty = np.linspace(1.0, 0.3, h).reshape(-1, 1)
        sky_likelihood = (brightness * 0.35 +
                          (1 - edge_magnitude) * 0.25 +
                          color_likelihood * 0.25 +
                          position_penalty * 0.15)
        sky_likelihood = cv2.normalize(sky_likelihood, None, 0, 1, cv2.NORM_MINMAX)
        adaptive_threshold = self.sky_threshold
        if self.adaptive_params and self.last_haze_density is not None:
            adaptive_threshold = 0.6 + 0.15 * self.last_haze_density
        sky_mask = (sky_likelihood > adaptive_threshold).astype(np.float32)
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_OPEN, kernel_small)
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        sky_mask = cv2.morphologyEx(sky_mask, cv2.MORPH_CLOSE, kernel_large)
        sky_mask = cv2.GaussianBlur(sky_mask, (31, 31), 0)
        self.last_sky_mask = sky_mask
        return sky_mask

    def _soft_matting(self, img, t):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        t = t.astype(np.float32)
        try:
            guided = cv2.ximgproc.guidedFilter(gray, t, radius=60, eps=1e-4)
        except AttributeError:
            guided = cv2.bilateralFilter(t, 15, 75, 75)
        return guided

    def _adaptive_parameters(self, haze_density):
        if not self.adaptive_params:
            return self.omega, self.t_min, self.dehaze_strength
        omega = 0.85 + 0.2 * haze_density
        t_min = 0.15 - 0.1 * haze_density
        t_min = max(t_min, 0.05)
        if haze_density < 0.3:
            strength = 0.7 + haze_density
        elif haze_density < 0.6:
            strength = 1.0 + (haze_density - 0.3) * 0.5
        else:
            strength = 1.15 + (haze_density - 0.6) * 0.7
        strength = min(strength, 1.8)
        return omega, t_min, strength

    def _process_sky_region(self, img_float, dehazed, sky_mask, atmospheric_light):
        if not self.sky_detection or sky_mask is None:
            return dehazed
        if np.sum(sky_mask > 0.5) < 10:
            return dehazed
        sky_mask_3ch = np.repeat(sky_mask[:, :, np.newaxis], 3, axis=2)
        non_sky_mask_3ch = 1.0 - sky_mask_3ch
        original_sky = img_float * sky_mask_3ch
        brightness_factor = 1.0
        if self.auto_brightness:
            sky_pixels = original_sky[sky_mask > 0.5]
            if len(sky_pixels) > 0:
                sky_mean = np.mean(sky_pixels)
                if not np.isnan(sky_mean) and sky_mean > 0:
                    target_brightness = min(sky_mean * 1.15, 0.95)
                    brightness_factor = target_brightness / (sky_mean + 1e-6)
                    brightness_factor = np.clip(brightness_factor, 0.9, 1.25)
        processed_sky = original_sky * brightness_factor
        if self.last_haze_density is not None:
            sky_saturation_factor = 0.85 + 0.15 * (1.0 - self.last_haze_density)
        else:
            sky_saturation_factor = 1.0
        processed_sky = self._adjust_saturation(processed_sky, sky_saturation_factor, sky_mask)
        atmospheric_3ch = np.ones_like(img_float) * atmospheric_light
        if self.last_haze_density is not None:
            haze_compensation = min(0.2 * self.last_haze_density, 0.3)
        else:
            haze_compensation = 0.0
        processed_sky = processed_sky * (1 - haze_compensation) + atmospheric_3ch * haze_compensation * sky_mask_3ch
        processed_sky = np.clip(processed_sky, 0, 1)
        final = dehazed * non_sky_mask_3ch + processed_sky * sky_mask_3ch
        return final

    def _adjust_saturation(self, img, factor, mask=None):
        img_clipped = np.clip(img, 0, 1)
        img_uint8 = (img_clipped * 255).astype(np.uint8)
        hsv = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = hsv[:, :, 1] * factor
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        hsv_uint8 = hsv.astype(np.uint8)
        adjusted = cv2.cvtColor(hsv_uint8, cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0
        if mask is not None:
            mask_3ch = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
            adjusted = img * (1 - mask_3ch) + adjusted * mask_3ch
        return adjusted

    def _global_color_correction(self, img_float, dehazed, haze_density):
        if not self.auto_brightness or haze_density < 0.2:
            return dehazed
        original_mean = np.mean(img_float, axis=(0, 1))
        dehazed_mean = np.mean(dehazed, axis=(0, 1))
        correction_strength = min(haze_density * 0.5, 0.3)
        for c in range(3):
            if dehazed_mean[c] < 0.35:
                adjustment = (0.35 - dehazed_mean[c]) * correction_strength
                dehazed[:, :, c] = dehazed[:, :, c] + adjustment
            elif dehazed_mean[c] > 0.8:
                adjustment = (dehazed_mean[c] - 0.8) * correction_strength * 0.5
                dehazed[:, :, c] = dehazed[:, :, c] - adjustment
        dehazed = np.clip(dehazed, 0, 1)
        return dehazed

    def dehaze(self, img, haze_density=None):
        img_float = img.astype(np.float32) / 255.0
        if haze_density is None:
            haze_density = self.estimate_haze_density(img)
        self.last_haze_density = haze_density
        if self.adaptive_params:
            omega, t_min, strength = self._adaptive_parameters(haze_density)
        else:
            omega, t_min, strength = self.omega, self.t_min, self.dehaze_strength
        dark = self._dark_channel(img_float)
        if self.sky_detection:
            sky_mask = self._detect_sky_region(img)
        else:
            sky_mask = None
        atmospheric_light = self._estimate_atmospheric_light(img_float, dark, sky_mask)
        self.last_atmospheric_light = atmospheric_light
        transmission = 1.0 - omega * self._dark_channel(img_float / atmospheric_light)
        transmission = self._soft_matting(img, transmission)
        transmission = np.clip(transmission * strength, t_min, 1.0)
        transmission_3ch = np.repeat(transmission[:, :, np.newaxis], 3, axis=2)
        dehazed = np.zeros_like(img_float)
        for c in range(3):
            dehazed[:, :, c] = (img_float[:, :, c] - atmospheric_light[c]) / \
                               transmission_3ch[:, :, c] + atmospheric_light[c]
        dehazed = np.clip(dehazed, 0, 1)
        dehazed = self._global_color_correction(img_float, dehazed, haze_density)
        if self.sky_detection and sky_mask is not None:
            dehazed = self._process_sky_region(img_float, dehazed, sky_mask, atmospheric_light)
        dehazed = (dehazed * 255).astype(np.uint8)
        return dehazed

    def dehaze_with_info(self, img):
        haze_density = self.estimate_haze_density(img)
        dehazed = self.dehaze(img, haze_density=haze_density)
        omega, t_min, strength = self._adaptive_parameters(haze_density) if self.adaptive_params \
            else (self.omega, self.t_min, self.dehaze_strength)
        info = {
            'haze_density': haze_density,
            'omega': omega,
            't_min': t_min,
            'strength': strength,
            'sky_ratio': np.mean(self.last_sky_mask) if self.last_sky_mask is not None else 0.0,
            'atmospheric_light': self.last_atmospheric_light
        }
        return dehazed, info

    def set_dehaze_strength(self, strength):
        self.dehaze_strength = np.clip(strength, 0.0, 2.0)

    def get_transmission_map(self, img):
        img_float = img.astype(np.float32) / 255.0
        dark = self._dark_channel(img_float)
        atmospheric_light = self._estimate_atmospheric_light(img_float, dark)
        transmission = 1.0 - self.omega * self._dark_channel(img_float / atmospheric_light)
        transmission = np.clip(transmission * self.dehaze_strength, self.t_min, 1.0)
        return (transmission * 255).astype(np.uint8)

    def get_sky_mask(self, img):
        if not self.sky_detection:
            return None
        sky_mask = self._detect_sky_region(img)
        return (sky_mask * 255).astype(np.uint8)

    def _adaptive_enhance(self, img, haze_density=None):
        if haze_density is None:
            haze_density = self.last_haze_density if self.last_haze_density is not None else 0.5
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clip_limit = 1.0 + haze_density * 2.0
        tile_grid_size = max(4, int(8 - haze_density * 4))
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
        l_enhanced = clahe.apply(l)
        gain = 1.0 + self.enhance_strength * 0.2
        l_enhanced = np.clip(l_enhanced * gain, 0, 255).astype(np.uint8)
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        return enhanced

    def dehaze_and_enhance(self, img, enhance_strength=None, haze_density=None):
        if enhance_strength is not None:
            self.enhance_strength = enhance_strength
        dehazed = self.dehaze(img, haze_density=haze_density)
        if self.enhance_strength > 0:
            enhanced = self._adaptive_enhance(dehazed, self.last_haze_density)
        else:
            enhanced = dehazed
        return enhanced, dehazed

    def dehaze_with_info_and_enhance(self, img, enhance_strength=None):
        if enhance_strength is not None:
            self.enhance_strength = enhance_strength
        dehazed, info = self.dehaze_with_info(img)
        if self.enhance_strength > 0:
            enhanced = self._adaptive_enhance(dehazed, info['haze_density'])
        else:
            enhanced = dehazed
        info['enhanced'] = self.enhance_strength > 0
        return enhanced, dehazed, info

    def set_enhance_strength(self, strength):
        self.enhance_strength = np.clip(strength, 0.0, 2.0)
