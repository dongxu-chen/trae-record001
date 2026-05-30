import pywt
import numpy as np
import cv2


class WaveletFusion:
    def __init__(self, wavelet="db2", level="auto", fusion_rule="max"):
        self.wavelet = wavelet
        self._level = level
        self.fusion_rule = fusion_rule
        self.level = level if isinstance(level, int) else 3

    @staticmethod
    def auto_level(image_shape):
        h, w = image_shape[:2]
        min_dim = min(h, w)
        if min_dim < 128:
            return 2
        elif min_dim < 256:
            return 3
        elif min_dim < 512:
            return 4
        elif min_dim < 1024:
            return 5
        else:
            return 6

    def _fuse_coefficients(self, coeffs_list, rule, reliable_masks=None):
        if reliable_masks is None:
            reliable_masks = [np.ones_like(c) for c in coeffs_list]
        if rule == "max":
            return self._fuse_max(coeffs_list, reliable_masks)
        elif rule == "mean":
            return self._fuse_mean(coeffs_list, reliable_masks)
        elif rule == "energy":
            return self._fuse_energy(coeffs_list, reliable_masks)
        elif rule == "weighted":
            return self._fuse_weighted(coeffs_list, reliable_masks)
        else:
            raise ValueError(f"Unknown fusion rule: {rule}")

    def _fuse_max(self, coeffs_list, reliable_masks):
        h, w = coeffs_list[0].shape
        abs_list = [np.abs(c) * m for c, m in zip(coeffs_list, reliable_masks)]
        stacked = np.stack(abs_list, axis=0)
        best_idx = np.argmax(stacked, axis=0)
        coeffs_stacked = np.stack(coeffs_list, axis=0)
        result = coeffs_stacked[best_idx, np.arange(h)[:, None], np.arange(w)]
        return result

    def _fuse_mean(self, coeffs_list, reliable_masks):
        total_weight = sum(reliable_masks) + 1e-10
        weighted_sum = sum(c * m for c, m in zip(coeffs_list, reliable_masks))
        return weighted_sum / total_weight

    def _fuse_weighted(self, coeffs_list, reliable_masks):
        weights = []
        for coeffs, rm in zip(coeffs_list, reliable_masks):
            energy = np.sum((coeffs * rm) ** 2)
            weights.append(energy + 1e-10)
        total = sum(weights)
        weights = [w / total for w in weights]
        result = np.zeros_like(coeffs_list[0])
        for w, coeffs in zip(weights, coeffs_list):
            result += w * coeffs
        return result

    def _fuse_energy(self, coeffs_list, reliable_masks):
        block_size = 8
        h, w = coeffs_list[0].shape
        result = np.zeros_like(coeffs_list[0])
        for i in range(0, h, block_size):
            for j in range(0, w, block_size):
                bh = min(block_size, h - i)
                bw = min(block_size, w - j)
                max_energy = -1
                best_idx = 0
                for idx, (coeffs, rm) in enumerate(zip(coeffs_list, reliable_masks)):
                    block = coeffs[i:i + bh, j:j + bw]
                    rm_block = rm[i:i + bh, j:j + bw]
                    energy = np.sum((block * rm_block) ** 2)
                    if energy > max_energy:
                        max_energy = energy
                        best_idx = idx
                result[i:i + bh, j:j + bw] = coeffs_list[best_idx][i:i + bh, j:j + bw]
        return result

    def _decompose(self, image):
        if self._level == "auto":
            self.level = self.auto_level(image.shape)
        else:
            self.level = self._level
        if len(image.shape) == 3:
            channels = []
            for c in range(image.shape[2]):
                ch = image[:, :, c].astype(np.float64)
                coeffs = pywt.wavedec2(ch, self.wavelet, level=self.level)
                channels.append(coeffs)
            return channels
        else:
            return [pywt.wavedec2(image.astype(np.float64), self.wavelet, level=self.level)]

    def _reconstruct(self, channels_coeffs):
        results = []
        for coeffs in channels_coeffs:
            results.append(pywt.waverec2(coeffs, self.wavelet))
        if len(results) == 1:
            return results[0]
        return np.stack(results, axis=-1)

    def _downsample_mask(self, mask, target_shape):
        h, w = target_shape
        resized = cv2.resize(mask, (w, h), interpolation=cv2.INTER_AREA)
        return resized.astype(np.float64)

    def fuse(self, images, reliable_masks=None):
        if not images:
            raise ValueError("No images provided")
        ref = images[0]
        h, w = ref.shape[:2]
        resized = []
        for img in images:
            if img.shape[:2] != (h, w):
                img = cv2.resize(img, (w, h))
            resized.append(img)

        if self._level == "auto":
            self.level = self.auto_level(ref.shape)
        else:
            self.level = self._level

        all_channels = [self._decompose(img) for img in resized]
        num_channels = len(all_channels[0])
        fused_channels = []

        masks_processed = None
        if reliable_masks is not None:
            masks_processed = []
            for rm in reliable_masks:
                if rm is None:
                    masks_processed.append(None)
                    continue
                if rm.shape[:2] != (h, w):
                    rm = cv2.resize(rm, (w, h))
                if len(rm.shape) == 3:
                    rm = cv2.cvtColor(rm, cv2.COLOR_BGR2GRAY)
                rm = rm.astype(np.float64) if rm.dtype != np.float64 else rm
                masks_processed.append(rm)

        for ch_idx in range(num_channels):
            channel_coeffs_list = [all_channels[img_idx][ch_idx] for img_idx in range(len(resized))]
            approx_list = [c[0] for c in channel_coeffs_list]
            if masks_processed is not None and masks_processed[0] is not None:
                approx_weights = [self._downsample_mask(m, approx_list[0].shape) for m in masks_processed]
                total_w = sum(approx_weights) + 1e-10
                fused_approx = sum(a * w for a, w in zip(approx_list, approx_weights)) / total_w
            else:
                fused_approx = np.mean(approx_list, axis=0)
            fused_detail_coeffs = [fused_approx]

            for level_idx in range(1, len(channel_coeffs_list[0])):
                detail_coeffs_per_image = [c[level_idx] for c in channel_coeffs_list]
                lh_list = [d[0] for d in detail_coeffs_per_image]
                hl_list = [d[1] for d in detail_coeffs_per_image]
                hh_list = [d[2] for d in detail_coeffs_per_image]

                detail_masks = None
                if masks_processed is not None:
                    detail_masks = [self._downsample_mask(m, lh_list[0].shape) for m in masks_processed]

                fused_lh = self._fuse_coefficients(lh_list, self.fusion_rule, detail_masks)
                fused_hl = self._fuse_coefficients(hl_list, self.fusion_rule, detail_masks)
                fused_hh = self._fuse_coefficients(hh_list, self.fusion_rule, detail_masks)
                fused_detail_coeffs.append((fused_lh, fused_hl, fused_hh))

            fused_channels.append(fused_detail_coeffs)

        result = self._reconstruct(fused_channels)
        result = np.clip(result, 0, 255).astype(np.uint8)
        if result.shape[:2] != (h, w):
            result = cv2.resize(result, (w, h))
        return result

    def get_available_wavelets(self):
        return pywt.wavelist()

    def get_available_rules(self):
        return ["max", "mean", "energy", "weighted"]
