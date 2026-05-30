import cv2
import numpy as np
from enum import Enum
from typing import Dict, Any, Optional


class ToneMappingOperator(Enum):
    REINHARD = "reinhard"
    FILMIC = "filmic"
    ACES = "aces"


class ToneMapper:
    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self._gpu_available = self._check_gpu_available()
        if use_gpu and not self._gpu_available:
            print("Warning: GPU not available, falling back to CPU")
            self.use_gpu = False

        self._init_default_params()

    def _check_gpu_available(self) -> bool:
        if not hasattr(cv2, 'cuda'):
            return False
        try:
            return cv2.cuda.getCudaEnabledDeviceCount() > 0
        except Exception:
            return False

    def _init_default_params(self):
        self.params = {
            ToneMappingOperator.REINHARD: {
                'intensity': 0.0,
                'light_adapt': 1.0,
                'color_adapt': 0.0,
                'gamma': 2.2
            },
            ToneMappingOperator.FILMIC: {
                'contrast': 1.0,
                'shoulder': 0.5,
                'linear': 0.1,
                'linear_angle': 0.1,
                'toe': 0.01,
                'toe_num_a': 0.55,
                'toe_num_b': 0.01,
                'toe_den_a': 0.4,
                'toe_den_b': 0.02,
                'gamma': 2.2
            },
            ToneMappingOperator.ACES: {
                'exposure': 1.0,
                'saturation': 1.0,
                'gamma': 2.2
            }
        }

    def set_param(self, op: ToneMappingOperator, param_name: str, value: float):
        if op in self.params and param_name in self.params[op]:
            self.params[op][param_name] = value

    def get_params(self, op: ToneMappingOperator) -> Dict[str, float]:
        return self.params.get(op, {}).copy()

    def process(self, hdr_image: np.ndarray, op: ToneMappingOperator) -> np.ndarray:
        if hdr_image is None:
            raise ValueError("Input image is None")

        if hdr_image.dtype != np.float32 and hdr_image.dtype != np.float64:
            hdr_image = hdr_image.astype(np.float32)

        if self.use_gpu and self._gpu_available:
            return self._process_gpu(hdr_image, op)
        else:
            return self._process_cpu(hdr_image, op)

    def _process_cpu(self, hdr_image: np.ndarray, op: ToneMappingOperator) -> np.ndarray:
        params = self.params[op]

        if op == ToneMappingOperator.REINHARD:
            return self._reinhard_cpu(hdr_image, params)
        elif op == ToneMappingOperator.FILMIC:
            return self._filmic_cpu(hdr_image, params)
        elif op == ToneMappingOperator.ACES:
            return self._aces_cpu(hdr_image, params)
        else:
            raise ValueError(f"Unknown operator: {op}")

    def _process_gpu(self, hdr_image: np.ndarray, op: ToneMappingOperator) -> np.ndarray:
        params = self.params[op]
        gpu_img = cv2.cuda_GpuMat()
        gpu_img.upload(hdr_image)

        try:
            if op == ToneMappingOperator.REINHARD:
                result = self._reinhard_gpu(gpu_img, params)
            elif op == ToneMappingOperator.FILMIC:
                result = self._filmic_gpu(gpu_img, params)
            elif op == ToneMappingOperator.ACES:
                result = self._aces_gpu(gpu_img, params)
            else:
                raise ValueError(f"Unknown operator: {op}")
            return result
        except Exception as e:
            print(f"GPU processing failed, falling back to CPU: {e}")
            return self._process_cpu(hdr_image, op)

    def _reinhard_cpu(self, img: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        intensity = params['intensity']
        light_adapt = params['light_adapt']
        color_adapt = params['color_adapt']
        gamma = params['gamma']

        tonemap = cv2.createTonemapReinhard(
            gamma=gamma,
            intensity=intensity,
            light_adapt=light_adapt,
            color_adapt=color_adapt
        )
        result = tonemap.process(img)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _reinhard_gpu(self, gpu_img: cv2.cuda_GpuMat, params: Dict[str, float]) -> np.ndarray:
        intensity = params['intensity']
        light_adapt = params['light_adapt']
        color_adapt = params['color_adapt']
        gamma = params['gamma']

        tonemap = cv2.cuda.createTonemapReinhard(
            gamma=gamma,
            intensity=intensity,
            light_adapt=light_adapt,
            color_adapt=color_adapt
        )
        gpu_result = tonemap.process(gpu_img)
        result = gpu_result.download()
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _filmic_cpu(self, img: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        gamma = params['gamma']

        tonemap = cv2.createTonemapDrago(
            gamma=gamma,
            saturation=1.0,
            bias=0.85
        )
        result = tonemap.process(img)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        result = self._apply_filmic_curve(result, params)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _filmic_gpu(self, gpu_img: cv2.cuda_GpuMat, params: Dict[str, float]) -> np.ndarray:
        gamma = params['gamma']

        tonemap = cv2.cuda.createTonemapDrago(
            gamma=gamma,
            saturation=1.0,
            bias=0.85
        )
        gpu_result = tonemap.process(gpu_img)
        result = gpu_result.download()
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        result = self._apply_filmic_curve(result, params)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _apply_filmic_curve(self, x: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        contrast = params['contrast']
        shoulder = params['shoulder']
        linear = params['linear']
        linear_angle = params['linear_angle']
        toe_num_a = params['toe_num_a']
        toe_num_b = params['toe_num_b']
        toe_den_a = params['toe_den_a']
        toe_den_b = params['toe_den_b']

        x = x * contrast

        result = np.zeros_like(x)

        toe_mask = x < linear
        shoulder_mask = (x >= linear) & (x < linear + shoulder)
        highlight_mask = x >= linear + shoulder

        if np.any(toe_mask):
            x_toe = x[toe_mask]
            num = toe_num_a * x_toe + toe_num_b
            den = toe_den_a * x_toe + toe_den_b
            den_safe = np.where(den == 0, 1e-10, den)
            result[toe_mask] = num / den_safe

        if np.any(shoulder_mask):
            x_shoulder = x[shoulder_mask]
            if shoulder > 0:
                t = (x_shoulder - linear) / shoulder
            else:
                t = np.zeros_like(x_shoulder)
            t = np.clip(t, 0, 1)
            base = linear * linear_angle
            result[shoulder_mask] = base + t * (1.0 - base)

        if np.any(highlight_mask):
            result[highlight_mask] = 1.0

        return result

    def _aces_cpu(self, img: np.ndarray, params: Dict[str, float]) -> np.ndarray:
        exposure = params['exposure']
        saturation = params['saturation']
        gamma = params['gamma']

        img = img * exposure
        result = self._aces_fit(img)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)

        if saturation != 1.0:
            result = self._adjust_saturation(result, saturation)

        result = np.power(np.clip(result, 0, 1), 1.0 / gamma)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _aces_gpu(self, gpu_img: cv2.cuda_GpuMat, params: Dict[str, float]) -> np.ndarray:
        exposure = params['exposure']
        saturation = params['saturation']
        gamma = params['gamma']

        img = gpu_img.download()
        img = img * exposure
        result = self._aces_fit(img)
        result = np.nan_to_num(result, nan=0.0, posinf=1.0, neginf=0.0)

        if saturation != 1.0:
            result = self._adjust_saturation(result, saturation)

        result = np.power(np.clip(result, 0, 1), 1.0 / gamma)
        return np.clip(result * 255.0, 0, 255).astype(np.uint8)

    def _adjust_saturation(self, img: np.ndarray, saturation: float) -> np.ndarray:
        gray = 0.299 * img[:, :, 2] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 0]
        gray = np.expand_dims(gray, axis=-1)
        result = gray + saturation * (img - gray)
        return np.clip(result, 0, 1)

    def _aces_fit(self, x: np.ndarray) -> np.ndarray:
        a = 2.51
        b = 0.03
        c = 2.43
        d = 0.59
        e = 0.14

        x_safe = np.clip(x, 0, None)
        numerator = x_safe * (a * x_safe + b)
        denominator = x_safe * (c * x_safe + d) + e
        denominator_safe = np.where(denominator == 0, 1e-10, denominator)
        return np.clip(numerator / denominator_safe, 0, 1)

    @staticmethod
    def load_hdr(filepath: str) -> np.ndarray:
        img = cv2.imread(filepath, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not load HDR image: {filepath}")
        if img.dtype != np.float32:
            img = img.astype(np.float32)
        return img

    @staticmethod
    def save_ldr(filepath: str, img: np.ndarray):
        cv2.imwrite(filepath, img)
