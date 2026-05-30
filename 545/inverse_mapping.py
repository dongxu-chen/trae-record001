import cv2
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class InverseMappingMethod(Enum):
    SIMPLE = "simple"
    DEBEVEC = "debevec"
    GRADIENT = "gradient"
    CHANNEL_RECOVERY = "channel_recovery"


class HDRInverseMapper:
    def __init__(self):
        self.method = InverseMappingMethod.CHANNEL_RECOVERY
        self.gamma = 2.2
        self.max_brightness = 10.0
        self.saturation_threshold = 0.95

    def set_method(self, method: InverseMappingMethod):
        self.method = method

    def set_params(self, gamma: float = 2.2, max_brightness: float = 10.0,
                   saturation_threshold: float = 0.95):
        self.gamma = gamma
        self.max_brightness = max_brightness
        self.saturation_threshold = saturation_threshold

    def map(self, ldr_image: np.ndarray) -> np.ndarray:
        if ldr_image is None:
            raise ValueError("Input image is None")

        if ldr_image.dtype == np.uint8:
            ldr_normalized = ldr_image.astype(np.float32) / 255.0
        elif ldr_image.dtype == np.uint16:
            ldr_normalized = ldr_image.astype(np.float32) / 65535.0
        else:
            ldr_normalized = ldr_image.astype(np.float32)

        ldr_normalized = np.clip(ldr_normalized, 0, 1)

        if self.method == InverseMappingMethod.SIMPLE:
            return self._simple_inverse(ldr_normalized)
        elif self.method == InverseMappingMethod.DEBEVEC:
            return self._debevec_inverse(ldr_normalized)
        elif self.method == InverseMappingMethod.GRADIENT:
            return self._gradient_domain_inverse(ldr_normalized)
        elif self.method == InverseMappingMethod.CHANNEL_RECOVERY:
            return self._channel_recovery_inverse(ldr_normalized)
        else:
            return self._channel_recovery_inverse(ldr_normalized)

    def _simple_inverse(self, ldr: np.ndarray) -> np.ndarray:
        hdr = np.power(ldr, self.gamma) * self.max_brightness
        return hdr.astype(np.float32)

    def _debevec_inverse(self, ldr: np.ndarray) -> np.ndarray:
        exposure_times = np.array([1.0, 2.0, 4.0, 8.0], dtype=np.float32)

        hdr = np.zeros_like(ldr, dtype=np.float32)
        weight_sum = np.zeros_like(ldr, dtype=np.float32)

        for t in exposure_times:
            simulated_ldr = np.clip(ldr * t, 0, 1)
            weight = self._gaussian_weight(simulated_ldr)
            irradiance = np.power(simulated_ldr, self.gamma) / t
            hdr += weight * irradiance
            weight_sum += weight

        weight_sum = np.where(weight_sum == 0, 1e-10, weight_sum)
        hdr = hdr / weight_sum
        hdr = hdr / hdr.max() * self.max_brightness if hdr.max() > 0 else hdr

        return hdr.astype(np.float32)

    def _gaussian_weight(self, x: np.ndarray, sigma: float = 0.2) -> np.ndarray:
        mean = 0.5
        w = np.exp(-((x - mean) ** 2) / (2 * sigma ** 2))
        return w

    def _gradient_domain_inverse(self, ldr: np.ndarray) -> np.ndarray:
        hdr = np.power(ldr, self.gamma)

        for channel in range(3):
            channel_data = hdr[:, :, channel]

            grad_x = np.gradient(channel_data, axis=1)
            grad_y = np.gradient(channel_data, axis=0)

            overexposed = ldr[:, :, channel] > self.saturation_threshold

            grad_x[overexposed] *= 2.0
            grad_y[overexposed] *= 2.0

            recovered = self._poisson_reconstruction(grad_x, grad_y, channel_data)
            hdr[:, :, channel] = recovered

        hdr = np.clip(hdr, 0, self.max_brightness)
        return hdr.astype(np.float32)

    def _poisson_reconstruction(self, grad_x: np.ndarray, grad_y: np.ndarray,
                                 boundary: np.ndarray) -> np.ndarray:
        h, w = grad_x.shape
        div = np.zeros_like(grad_x)
        div[:, 1:-1] += grad_x[:, 1:-1] - grad_x[:, :-2]
        div[1:-1, :] += grad_y[1:-1, :] - grad_y[:-2, :]

        result = cv2.GaussianBlur(boundary, (5, 5), 0)
        for _ in range(50):
            result_new = result.copy()
            result_new[1:-1, 1:-1] = 0.25 * (
                result[:-2, 1:-1] + result[2:, 1:-1] +
                result[1:-1, :-2] + result[1:-1, 2:] -
                div[1:-1, 1:-1]
            )
            result = result_new

        result = np.clip(result, 0, self.max_brightness)
        return result

    def _channel_recovery_inverse(self, ldr: np.ndarray) -> np.ndarray:
        hdr = np.zeros_like(ldr, dtype=np.float32)

        max_channel = np.max(ldr, axis=2)
        min_channel = np.min(ldr, axis=2)
        saturation_mask = max_channel > self.saturation_threshold

        luminance = 0.299 * ldr[:, :, 2] + 0.587 * ldr[:, :, 1] + 0.114 * ldr[:, :, 0]

        base_hdr = np.power(ldr, self.gamma)

        for c in range(3):
            channel = ldr[:, :, c]
            hdr_channel = base_hdr[:, :, c].copy()

            overexposed = channel > self.saturation_threshold
            if np.any(overexposed):
                non_sat_mask = ~overexposed

                if np.sum(non_sat_mask) > 100:
                    ratios = np.ones_like(channel)
                    valid_mask = ldr[:, :, c] > 0.01
                    if np.any(valid_mask & non_sat_mask):
                        avg_ratio = np.mean(
                            luminance[valid_mask & non_sat_mask] /
                            (ldr[valid_mask & non_sat_mask, c] + 1e-6)
                        )
                        ratios[overexposed] = avg_ratio * 1.5

                    hdr_channel[overexposed] = np.power(
                        luminance[overexposed] * ratios[overexposed],
                        self.gamma * 0.8
                    )

                    chroma_recovery = self._recover_chroma(ldr, overexposed, c)
                    hdr_channel[overexposed] *= (1 + chroma_recovery[overexposed])

                hdr_channel[overexposed] = np.clip(
                    hdr_channel[overexposed],
                    np.power(self.saturation_threshold, self.gamma),
                    self.max_brightness
                )

            hdr[:, :, c] = hdr_channel

        hdr = self._local_tone_adjustment(hdr, ldr, saturation_mask)
        hdr = np.clip(hdr, 0, self.max_brightness)

        return hdr.astype(np.float32)

    def _recover_chroma(self, ldr: np.ndarray, overexposed: np.ndarray,
                        target_channel: int) -> np.ndarray:
        chroma = np.zeros(ldr.shape[:2], dtype=np.float32)

        other_channels = [c for c in range(3) if c != target_channel]
        for c in other_channels:
            chroma += ldr[:, :, c]
        chroma /= 2.0

        chroma_strength = np.where(
            chroma > 0.5,
            0.3 * (chroma - 0.5) * 2,
            0.0
        )

        return chroma_strength

    def _local_tone_adjustment(self, hdr: np.ndarray, ldr: np.ndarray,
                               saturation_mask: np.ndarray) -> np.ndarray:
        if not np.any(saturation_mask):
            return hdr

        kernel_size = 15
        luminance_hdr = 0.299 * hdr[:, :, 2] + 0.587 * hdr[:, :, 1] + 0.114 * hdr[:, :, 0]
        luminance_ldr = 0.299 * ldr[:, :, 2] + 0.587 * ldr[:, :, 1] + 0.114 * ldr[:, :, 0]

        local_avg = cv2.GaussianBlur(luminance_ldr, (kernel_size, kernel_size), 0)
        detail = luminance_ldr - local_avg

        adjustment = np.ones_like(luminance_hdr)
        mask_3d = np.stack([saturation_mask] * 3, axis=-1)

        detail_boost = 1.0 + 0.5 * np.abs(detail)
        detail_boost = np.expand_dims(detail_boost, axis=-1)

        hdr = np.where(
            mask_3d,
            hdr * detail_boost,
            hdr
        )

        return hdr

    def recover_overexposed_details(self, ldr_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        hdr = self.map(ldr_image)
        ldr_normalized = ldr_image.astype(np.float32) / 255.0 if ldr_image.dtype == np.uint8 else ldr_image

        overexposed_mask = np.max(ldr_normalized, axis=2) > self.saturation_threshold
        detail_mask = np.stack([overexposed_mask] * 3, axis=-1)

        recovered = np.zeros_like(ldr_normalized, dtype=np.float32)
        if np.any(overexposed_mask):
            hdr_clipped = np.clip(hdr / self.max_brightness, 0, 1)
            recovered = np.where(detail_mask, hdr_clipped, ldr_normalized)
            recovered = np.clip(recovered * 255, 0, 255).astype(np.uint8)

        return hdr, recovered

    @staticmethod
    def load_ldr(filepath: str) -> np.ndarray:
        img = cv2.imread(filepath, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not load LDR image: {filepath}")
        return img

    @staticmethod
    def save_hdr(filepath: str, hdr_image: np.ndarray):
        cv2.imwrite(filepath, hdr_image)
