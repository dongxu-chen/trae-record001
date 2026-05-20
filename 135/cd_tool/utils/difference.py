import cv2
import numpy as np
import torch


class DifferenceCalculator:
    def __init__(self, method='cva'):
        self.method = method
        self.methods = {
            'cva': self._cva,
            'diff': self._diff,
            'ratio': self._ratio,
            'ndvi': self._ndvi_diff
        }

    def compute(self, img1, img2):
        if isinstance(img1, torch.Tensor):
            img1 = img1.cpu().numpy()
            img2 = img2.cpu().numpy()
        if len(img1.shape) == 4:
            img1 = img1.transpose(0, 2, 3, 1)
            img2 = img2.transpose(0, 2, 3, 1)
            diffs = []
            for i in range(img1.shape[0]):
                diff = self.methods[self.method](img1[i], img2[i])
                diffs.append(diff)
            return np.array(diffs)
        else:
            return self.methods[self.method](img1, img2)

    def _cva(self, img1, img2):
        diff = img1.astype(np.float32) - img2.astype(np.float32)
        cva = np.sqrt(np.sum(diff ** 2, axis=-1))
        return (cva - cva.min()) / (cva.max() - cva.min() + 1e-8)

    def _diff(self, img1, img2):
        if len(img1.shape) == 3:
            img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if img1.shape[-1] == 3 else img1[..., 0]
            img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if img2.shape[-1] == 3 else img2[..., 0]
        else:
            img1_gray = img1
            img2_gray = img2
        diff = np.abs(img1_gray.astype(np.float32) - img2_gray.astype(np.float32))
        return (diff - diff.min()) / (diff.max() - diff.min() + 1e-8)

    def _ratio(self, img1, img2):
        if len(img1.shape) == 3:
            img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if img1.shape[-1] == 3 else img1[..., 0]
            img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if img2.shape[-1] == 3 else img2[..., 0]
        else:
            img1_gray = img1
            img2_gray = img2
        ratio = np.log((img1_gray.astype(np.float32) + 1) / (img2_gray.astype(np.float32) + 1))
        ratio = np.abs(ratio)
        return (ratio - ratio.min()) / (ratio.max() - ratio.min() + 1e-8)

    def _ndvi_diff(self, img1, img2):
        def calc_ndvi(img):
            if img.shape[-1] >= 4:
                nir = img[..., 3].astype(np.float32)
                red = img[..., 2].astype(np.float32)
            else:
                nir = img[..., 0].astype(np.float32)
                red = img[..., 1].astype(np.float32) if img.shape[-1] > 1 else nir
            ndvi = (nir - red) / (nir + red + 1e-8)
            return ndvi
        ndvi1 = calc_ndvi(img1)
        ndvi2 = calc_ndvi(img2)
        diff = np.abs(ndvi1 - ndvi2)
        return (diff - diff.min()) / (diff.max() - diff.min() + 1e-8)

    def visualize(self, diff, colormap=cv2.COLORMAP_JET):
        diff_norm = (diff * 255).astype(np.uint8)
        return cv2.applyColorMap(diff_norm, colormap)
