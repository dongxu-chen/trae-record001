import cv2
import numpy as np
from config import ENHANCE_CONFIG


class ImageEnhancer:
    def __init__(self, config=None):
        self.config = config or ENHANCE_CONFIG
        self.sigma_list = [15, 80, 250]
        self.alpha = 125.0
        self.beta = 46.0
        self.G = 192.0
        self.b = -30.0

    def enhance(self, image):
        if image is None:
            return None
        
        brightness = self._estimate_brightness(image)
        
        if brightness < 80:
            enhanced = self._msrcr_enhance(image)
        elif brightness < 120:
            enhanced = self._moderate_enhance(image)
        else:
            enhanced = image.copy()
        
        enhanced = self._post_process(enhanced)
        return enhanced

    def _estimate_brightness(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.mean(gray)

    def _msrcr_enhance(self, image):
        image_float = image.astype(np.float32) + 1.0
        
        msrcr_result = self._msrcr(image_float)
        
        msrcr_result = self._color_restoration(msrcr_result, image_float)
        
        msrcr_result = self._gamma_correction(msrcr_result)
        
        enhanced = self._normalize_image(msrcr_result)
        
        enhanced = self._color_correction(enhanced, image)
        
        return enhanced

    def _msrcr(self, image):
        channels = cv2.split(image)
        result_channels = []
        
        for channel in channels:
            channel_log = np.log(channel)
            
            msrcr = np.zeros_like(channel_log)
            weight_sum = 0.0
            
            for sigma in self.sigma_list:
                weight = 1.0 / (sigma ** 2)
                weight_sum += weight
                
                gaussian = cv2.GaussianBlur(
                    channel,
                    (0, 0),
                    sigmaX=sigma,
                    sigmaY=sigma,
                    borderType=cv2.BORDER_REPLICATE
                )
                gaussian_log = np.log(gaussian + 1.0)
                
                retinex = channel_log - gaussian_log
                msrcr += weight * retinex
            
            msrcr /= weight_sum
            result_channels.append(msrcr)
        
        msrcr_result = cv2.merge(result_channels)
        return msrcr_result

    def _color_restoration(self, msrcr_result, original_image):
        image_sum = np.sum(original_image, axis=2, keepdims=True)
        image_sum = np.maximum(image_sum, 1e-6)
        
        log_image_sum = np.log(image_sum)
        
        log_channels = np.log(original_image)
        
        color_restoration = self.beta * (
            log_channels - log_image_sum / 3.0
        )
        
        result = self.alpha * (msrcr_result + color_restoration)
        
        return result

    def _gamma_correction(self, image):
        mean_val = np.mean(image)
        std_val = np.std(image)
        
        gamma = 1.0
        if mean_val < 50:
            gamma = 0.7
        elif mean_val < 80:
            gamma = 0.85
        elif mean_val > 150:
            gamma = 1.1
        
        image_normalized = (image - np.min(image)) / (np.max(image) - np.min(image) + 1e-6)
        image_gamma = np.power(image_normalized, gamma)
        image_gamma = image_gamma * (np.max(image) - np.min(image)) + np.min(image)
        
        return image_gamma

    def _normalize_image(self, image):
        result = self.G * image + self.b
        
        result = np.clip(result, 0, 255)
        result = result.astype(np.uint8)
        
        return result

    def _moderate_enhance(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced

    def _color_correction(self, enhanced, original):
        enhanced_float = enhanced.astype(np.float32)
        original_float = original.astype(np.float32)
        
        for c in range(3):
            orig_mean = np.mean(original_float[:, :, c])
            enh_mean = np.mean(enhanced_float[:, :, c])
            
            if enh_mean > 0:
                ratio = orig_mean / enh_mean
                enhanced_float[:, :, c] *= ratio
        
        hsv_orig = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
        hsv_enh = cv2.cvtColor(enhanced_float.astype(np.uint8), cv2.COLOR_BGR2HSV)
        
        hsv_enh[:, :, 0] = hsv_orig[:, :, 0]
        hsv_enh[:, :, 1] = np.clip(hsv_enh[:, :, 1] * 0.95, 0, 255).astype(np.uint8)
        
        corrected = cv2.cvtColor(hsv_enh, cv2.COLOR_HSV2BGR)
        
        return corrected

    def _post_process(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        l = cv2.bilateralFilter(l, d=5, sigmaColor=50, sigmaSpace=50)
        
        kernel = np.array([[0, -0.25, 0],
                           [-0.25, 2, -0.25],
                           [0, -0.25, 0]], dtype=np.float32)
        
        l_sharp = cv2.filter2D(l, -1, kernel)
        l_sharp = np.clip(l_sharp, 0, 255).astype(np.uint8)
        
        lab_enhanced = cv2.merge([l_sharp, a, b])
        sharpened = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        return sharpened

    def auto_white_balance(self, image):
        result = cv2.xphoto.createSimpleWB().balanceWhite(image)
        return result

    def denoise(self, image):
        return cv2.fastNlMeansDenoisingColored(image, None, 5, 5, 7, 21)

    def _ssr(self, image, sigma=80):
        image_float = image.astype(np.float32) + 1.0
        
        channels = cv2.split(image_float)
        result_channels = []
        
        for channel in channels:
            gaussian = cv2.GaussianBlur(
                channel,
                (0, 0),
                sigmaX=sigma,
                sigmaY=sigma,
                borderType=cv2.BORDER_REPLICATE
            )
            
            retinex = np.log(channel) - np.log(gaussian + 1.0)
            result_channels.append(retinex)
        
        result = cv2.merge(result_channels)
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        
        return result

    def _msr(self, image):
        image_float = image.astype(np.float32) + 1.0
        
        channels = cv2.split(image_float)
        result_channels = []
        
        for channel in channels:
            channel_log = np.log(channel)
            
            msr = np.zeros_like(channel_log)
            weight_sum = 0.0
            
            for sigma in self.sigma_list:
                weight = 1.0 / (sigma ** 2)
                weight_sum += weight
                
                gaussian = cv2.GaussianBlur(
                    channel,
                    (0, 0),
                    sigmaX=sigma,
                    sigmaY=sigma,
                    borderType=cv2.BORDER_REPLICATE
                )
                gaussian_log = np.log(gaussian + 1.0)
                
                retinex = channel_log - gaussian_log
                msr += weight * retinex
            
            msr /= weight_sum
            result_channels.append(msr)
        
        result = cv2.merge(result_channels)
        result = self._normalize_image(result)
        
        return result
