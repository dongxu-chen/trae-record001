import cv2
import numpy as np


class DynamicAligner:
    def __init__(self, method="farneback", warp_mode="euclidean"):
        self.method = method
        self.warp_mode = warp_mode

    def _compute_optical_flow_farneback(self, img1, img2):
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
        )
        return flow

    def _compute_optical_flow_lk(self, img1, img2):
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        feature_params = dict(maxCorners=2000, qualityLevel=0.01, minDistance=7, blockSize=7)
        lk_params = dict(winSize=(21, 21), maxLevel=3,
                         criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        p0 = cv2.goodFeaturesToTrack(gray1, **feature_params)
        if p0 is None:
            h, w = gray1.shape
            return np.zeros((h, w, 2), dtype=np.float32)
        p1, st, err = cv2.calcOpticalFlowPyrLK(gray1, gray2, p0, None, **lk_params)
        if p1 is None or st is None:
            h, w = gray1.shape
            return np.zeros((h, w, 2), dtype=np.float32)
        good_new = p1[st.flatten() == 1]
        good_old = p0[st.flatten() == 1]
        if len(good_new) < 4:
            h, w = gray1.shape
            return np.zeros((h, w, 2), dtype=np.float32)
        motion_vectors = good_new - good_old
        h, w = gray1.shape
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        flow = np.zeros((h, w, 2), dtype=np.float32)
        distances = np.sqrt(motion_vectors[:, 0] ** 2 + motion_vectors[:, 1] ** 2)
        threshold = np.median(distances) + 2 * np.std(distances)
        valid = distances < threshold
        if np.sum(valid) < 3:
            return flow
        for pt_old, mv in zip(good_old[valid], motion_vectors[valid]):
            x0, y0 = int(pt_old[0]), int(pt_old[1])
            if 0 <= x0 < w and 0 <= y0 < h:
                flow[y0, x0] = mv
        flow = cv2.GaussianBlur(flow, (31, 31), 0)
        return flow

    def _compute_optical_flow(self, img1, img2):
        if self.method == "farneback":
            return self._compute_optical_flow_farneback(img1, img2)
        elif self.method == "lucas_kanade":
            return self._compute_optical_flow_lk(img1, img2)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _warp_by_flow(self, image, flow):
        h, w = image.shape[:2]
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        map_x = (grid_x + flow[:, :, 0]).astype(np.float32)
        map_y = (grid_y + flow[:, :, 1]).astype(np.float32)
        return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def _warp_ecc(self, img1, img2):
        warp_modes = {
            "translation": cv2.MOTION_TRANSLATION,
            "euclidean": cv2.MOTION_EUCLIDEAN,
            "affine": cv2.MOTION_AFFINE,
            "homography": cv2.MOTION_HOMOGRAPHY,
        }
        mode = warp_modes.get(self.warp_mode, cv2.MOTION_EUCLIDEAN)
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        if mode == cv2.MOTION_HOMOGRAPHY:
            warp_matrix = np.eye(3, 3, dtype=np.float32)
        else:
            warp_matrix = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 5000, 1e-6)
        try:
            _, warp_matrix = cv2.findTransformECC(gray1, gray2, warp_matrix, mode, criteria, None, 5)
        except cv2.error:
            if mode == cv2.MOTION_HOMOGRAPHY:
                warp_matrix = np.eye(3, 3, dtype=np.float32)
            else:
                warp_matrix = np.eye(2, 3, dtype=np.float32)
        h, w = img2.shape[:2]
        if mode == cv2.MOTION_HOMOGRAPHY:
            aligned = cv2.warpPerspective(img2, warp_matrix, (w, h), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        else:
            aligned = cv2.warpAffine(img2, warp_matrix, (w, h), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        return aligned

    def align(self, images, ref_idx=0):
        if len(images) <= 1:
            return images
        reference = images[ref_idx]
        aligned = [None] * len(images)
        aligned[ref_idx] = reference.copy()
        for i in range(len(images)):
            if i == ref_idx:
                continue
            flow = self._compute_optical_flow(reference, images[i])
            aligned[i] = self._warp_by_flow(images[i], flow)
        return aligned

    def align_ecc(self, images, ref_idx=0):
        if len(images) <= 1:
            return images
        reference = images[ref_idx]
        aligned = [None] * len(images)
        aligned[ref_idx] = reference.copy()
        for i in range(len(images)):
            if i == ref_idx:
                continue
            aligned[i] = self._warp_ecc(reference, images[i])
        return aligned

    def detect_motion_mask(self, img1, img2, threshold=30):
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        diff = cv2.absdiff(gray1, gray2)
        _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        return mask

    def detect_motion_region_from_flow(self, flow, motion_threshold=1.5, min_area=100):
        h, w = flow.shape[:2]
        mag = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
        motion_mask = np.zeros((h, w), dtype=np.uint8)
        motion_mask[mag > motion_threshold] = 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        refined_mask = np.zeros_like(motion_mask)
        for cnt in contours:
            if cv2.contourArea(cnt) > min_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                pad = 15
                x1, y1 = max(0, x - pad), max(0, y - pad)
                x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)
                refined_mask[y1:y2, x1:x2] = 255
        return refined_mask

    def compute_reliable_fusion_mask(self, img_ref, img_aligned, flow, motion_mask=None):
        h, w = img_ref.shape[:2]
        if motion_mask is None:
            motion_mask = self.detect_motion_region_from_flow(flow)
        gray_ref = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY) if len(img_ref.shape) == 3 else img_ref
        gray_aligned = cv2.cvtColor(img_aligned, cv2.COLOR_BGR2GRAY) if len(img_aligned.shape) == 3 else img_aligned
        diff = cv2.absdiff(gray_ref, gray_aligned).astype(np.float32)
        diff = cv2.GaussianBlur(diff, (5, 5), 0)
        consistency_mask = np.ones((h, w), dtype=np.float32)
        consistency_mask[diff > 40] = np.linspace(1.0, 0.2, 100)[np.clip((diff[diff > 40] - 40).astype(int), 0, 99)]
        mag = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
        motion_confidence = 1.0 - np.clip(mag / 10.0, 0, 1)
        reliable_mask = consistency_mask * motion_confidence
        reliable_mask[motion_mask > 0] = np.minimum(reliable_mask[motion_mask > 0], 0.3)
        reliable_mask = cv2.GaussianBlur(reliable_mask, (11, 11), 0)
        return reliable_mask

    def align_with_motion_aware(self, images, ref_idx=0):
        if len(images) <= 1:
            return images, [None] * len(images), [None] * len(images), [None] * len(images)
        reference = images[ref_idx]
        aligned = [None] * len(images)
        motion_masks = [None] * len(images)
        reliable_masks = [None] * len(images)
        flows = [None] * len(images)
        aligned[ref_idx] = reference.copy()
        for i in range(len(images)):
            if i == ref_idx:
                motion_masks[i] = np.zeros(reference.shape[:2], dtype=np.uint8)
                reliable_masks[i] = np.ones(reference.shape[:2], dtype=np.float32)
                continue
            flow = self._compute_optical_flow(reference, images[i])
            flows[i] = flow
            aligned[i] = self._warp_by_flow(images[i], flow)
            motion_masks[i] = self.detect_motion_region_from_flow(flow)
            reliable_masks[i] = self.compute_reliable_fusion_mask(reference, aligned[i], flow, motion_masks[i])
        return aligned, motion_masks, reliable_masks, flows

    def blend_motion_region(self, img_aligned, img_ref, motion_mask, blend_alpha=0.5):
        mask_float = motion_mask.astype(np.float32) / 255.0
        if len(img_aligned.shape) == 3:
            mask_float = np.stack([mask_float] * img_aligned.shape[2], axis=-1)
        blended = img_ref * (1 - mask_float * blend_alpha) + img_aligned * (mask_float * blend_alpha)
        blended = img_ref * (1 - mask_float) + blended * mask_float
        return np.clip(blended, 0, 255).astype(np.uint8)

    def visualize_flow(self, flow):
        h, w = flow.shape[:2]
        fx, fy = flow[:, :, 0], flow[:, :, 1]
        mag, ang = cv2.cartToPolar(fx, fy)
        hsv = np.zeros((h, w, 3), dtype=np.uint8)
        hsv[..., 0] = ang * 180 / np.pi / 2
        hsv[..., 1] = 255
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return bgr

    def get_available_methods(self):
        return ["farneback", "lucas_kanade"]

    def get_available_warp_modes(self):
        return ["translation", "euclidean", "affine", "homography"]
