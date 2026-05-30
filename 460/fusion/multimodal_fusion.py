import numpy as np
import cv2
import pywt


class MultimodalFusion:
    def __init__(self, method="intensity_weighted"):
        self.method = method

    @staticmethod
    def _ensure_3channel(image):
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image

    @staticmethod
    def _to_gray(image):
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
        return image.astype(np.float64)

    @staticmethod
    def _align_channels(img_ir, img_vis):
        if len(img_ir.shape) == 2:
            img_ir_3ch = cv2.cvtColor(img_ir, cv2.COLOR_GRAY2BGR)
        else:
            if img_ir.shape[2] == 1:
                img_ir_3ch = cv2.cvtColor(img_ir, cv2.COLOR_GRAY2BGR)
            elif img_ir.shape[2] == 4:
                img_ir_3ch = img_ir[:, :, :3]
            else:
                img_ir_3ch = img_ir.copy()
        if len(img_vis.shape) == 2:
            img_vis_3ch = cv2.cvtColor(img_vis, cv2.COLOR_GRAY2BGR)
        else:
            if img_vis.shape[2] == 1:
                img_vis_3ch = cv2.cvtColor(img_vis, cv2.COLOR_GRAY2BGR)
            elif img_vis.shape[2] == 4:
                img_vis_3ch = img_vis[:, :, :3]
            else:
                img_vis_3ch = img_vis.copy()
        return img_ir_3ch, img_vis_3ch

    def fuse_intensity_weighted(self, img_ir, img_vis, ir_weight=0.5, vis_weight=0.5):
        img_ir_3, img_vis_3 = self._align_channels(img_ir, img_vis)
        total = ir_weight + vis_weight
        if total == 0:
            total = 1
        w_ir = ir_weight / total
        w_vis = vis_weight / total
        result = (img_ir_3.astype(np.float64) * w_ir + img_vis_3.astype(np.float64) * w_vis)
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_gradient_guided(self, img_ir, img_vis):
        img_ir_3, img_vis_3 = self._align_channels(img_ir, img_vis)
        gray_ir = self._to_gray(img_ir_3)
        gray_vis = self._to_gray(img_vis_3)
        grad_ir_x = cv2.Sobel(gray_ir, cv2.CV_64F, 1, 0, ksize=3)
        grad_ir_y = cv2.Sobel(gray_ir, cv2.CV_64F, 0, 1, ksize=3)
        grad_vis_x = cv2.Sobel(gray_vis, cv2.CV_64F, 1, 0, ksize=3)
        grad_vis_y = cv2.Sobel(gray_vis, cv2.CV_64F, 0, 1, ksize=3)
        grad_ir_mag = np.sqrt(grad_ir_x ** 2 + grad_ir_y ** 2)
        grad_vis_mag = np.sqrt(grad_vis_x ** 2 + grad_vis_y ** 2)
        weight_ir = grad_ir_mag / (grad_ir_mag + grad_vis_mag + 1e-10)
        weight_vis = 1.0 - weight_ir
        result = np.zeros_like(img_ir_3, dtype=np.float64)
        for c in range(3):
            result[:, :, c] = (img_ir_3[:, :, c].astype(np.float64) * weight_ir +
                               img_vis_3[:, :, c].astype(np.float64) * weight_vis)
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_wavelet_cross_modal(self, img_ir, img_vis, wavelet="db2", level=3):
        img_ir_3, img_vis_3 = self._align_channels(img_ir, img_vis)
        result = np.zeros_like(img_ir_3, dtype=np.float64)
        for c in range(3):
            ir_ch = img_ir_3[:, :, c].astype(np.float64)
            vis_ch = img_vis_3[:, :, c].astype(np.float64)
            coeffs_ir = pywt.wavedec2(ir_ch, wavelet, level=level)
            coeffs_vis = pywt.wavedec2(vis_ch, wavelet, level=level)
            fused_approx = (coeffs_ir[0] + coeffs_vis[0]) / 2.0
            fused_coeffs = [fused_approx]
            for l_idx in range(1, len(coeffs_ir)):
                ir_lh, ir_hl, ir_hh = coeffs_ir[l_idx]
                vis_lh, vis_hl, vis_hh = coeffs_vis[l_idx]
                fused_lh = np.where(np.abs(ir_lh) > np.abs(vis_lh), ir_lh, vis_lh)
                fused_hl = np.where(np.abs(ir_hl) > np.abs(vis_hl), ir_hl, vis_hl)
                fused_hh = np.where(np.abs(ir_hh) > np.abs(vis_hh), ir_hh, vis_hh)
                fused_coeffs.append((fused_lh, fused_hl, fused_hh))
            result[:, :, c] = pywt.waverec2(fused_coeffs, wavelet)
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_laplacian_pyramid(self, img_ir, img_vis, levels=4):
        img_ir_3, img_vis_3 = self._align_channels(img_ir, img_vis)
        img_ir_f = img_ir_3.astype(np.float64)
        img_vis_f = img_vis_3.astype(np.float64)
        gp_ir = [img_ir_f.copy()]
        gp_vis = [img_vis_f.copy()]
        for _ in range(levels):
            img_ir_f = cv2.pyrDown(img_ir_f)
            img_vis_f = cv2.pyrDown(img_vis_f)
            gp_ir.append(img_ir_f.copy())
            gp_vis.append(img_vis_f.copy())
        lp_ir = [gp_ir[-1]]
        lp_vis = [gp_vis[-1]]
        for i in range(levels, 0, -1):
            up_ir = cv2.pyrUp(gp_ir[i], dstsize=(gp_ir[i - 1].shape[1], gp_ir[i - 1].shape[0]))
            up_vis = cv2.pyrUp(gp_vis[i], dstsize=(gp_vis[i - 1].shape[1], gp_vis[i - 1].shape[0]))
            lp_ir.append(gp_ir[i - 1] - up_ir)
            lp_vis.append(gp_vis[i - 1] - up_vis)
        fused_lp = []
        for i in range(len(lp_ir)):
            if i == len(lp_ir) - 1:
                fused = (lp_ir[i] + lp_vis[i]) / 2.0
            else:
                fused = np.where(np.abs(lp_ir[i]) > np.abs(lp_vis[i]), lp_ir[i], lp_vis[i])
            fused_lp.append(fused)
        result = fused_lp[0]
        for i in range(1, len(fused_lp)):
            result = cv2.pyrUp(result, dstsize=(fused_lp[i].shape[1], fused_lp[i].shape[0]))
            result = result + fused_lp[i]
        return np.clip(result, 0, 255).astype(np.uint8)

    def fuse_salience_weighted(self, img_ir, img_vis):
        img_ir_3, img_vis_3 = self._align_channels(img_ir, img_vis)
        gray_ir = self._to_gray(img_ir_3)
        gray_vis = self._to_gray(img_vis_3)
        sal_ir = self._compute_saliency(gray_ir)
        sal_vis = self._compute_saliency(gray_vis)
        total_sal = sal_ir + sal_vis + 1e-10
        w_ir = sal_ir / total_sal
        w_vis = sal_vis / total_sal
        result = np.zeros_like(img_ir_3, dtype=np.float64)
        for c in range(3):
            result[:, :, c] = (img_ir_3[:, :, c].astype(np.float64) * w_ir +
                               img_vis_3[:, :, c].astype(np.float64) * w_vis)
        return np.clip(result, 0, 255).astype(np.uint8)

    @staticmethod
    def _compute_saliency(gray):
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        mean_val = blurred.mean()
        saliency = np.abs(gray - mean_val)
        saliency = cv2.GaussianBlur(saliency, (11, 11), 2.0)
        saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-10)
        return saliency

    def fuse(self, img_ir, img_vis, **kwargs):
        if self.method == "intensity_weighted":
            return self.fuse_intensity_weighted(img_ir, img_vis, **kwargs)
        elif self.method == "gradient_guided":
            return self.fuse_gradient_guided(img_ir, img_vis)
        elif self.method == "wavelet":
            return self.fuse_wavelet_cross_modal(img_ir, img_vis, **kwargs)
        elif self.method == "laplacian_pyramid":
            return self.fuse_laplacian_pyramid(img_ir, img_vis, **kwargs)
        elif self.method == "salience_weighted":
            return self.fuse_salience_weighted(img_ir, img_vis)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    @staticmethod
    def get_available_methods():
        return ["intensity_weighted", "gradient_guided", "wavelet", "laplacian_pyramid", "salience_weighted"]

    @staticmethod
    def generate_pseudo_color(gray_ir):
        if len(gray_ir.shape) == 3:
            gray_ir = cv2.cvtColor(gray_ir, cv2.COLOR_BGR2GRAY)
        norm = cv2.normalize(gray_ir, None, 0, 255, cv2.NORM_MINMAX)
        return cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_JET)
