import numpy as np
import cv2
import pydensecrf.densecrf as dcrf
from pydensecrf.utils import unary_from_softmax, create_pairwise_bilateral, create_pairwise_gaussian


class FastCRFDepthOptimizer:
    def __init__(
        self,
        num_iterations=3,
        bilateral_sxy=60,
        bilateral_srgb=10,
        bilateral_compat=8,
        gaussian_sxy=3,
        gaussian_compat=3,
        num_depth_bins=24,
        downscale=2,
        use_approx=True,
        texture_skip_threshold=0.01,
    ):
        self.num_iterations = num_iterations
        self.bilateral_sxy = bilateral_sxy
        self.bilateral_srgb = bilateral_srgb
        self.bilateral_compat = bilateral_compat
        self.gaussian_sxy = gaussian_sxy
        self.gaussian_compat = gaussian_compat
        self.num_depth_bins = num_depth_bins
        self.downscale = max(1, int(downscale))
        self.use_approx = use_approx
        self.texture_skip_threshold = texture_skip_threshold

    def _detect_texture(self, gray):
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var < self.texture_skip_threshold, laplacian_var

    def _detect_texture_regions(self, gray, grid_size=32):
        h, w = gray.shape[:2]
        gh = h // grid_size
        gw = w // grid_size
        texture_map = np.zeros((gh, gw), dtype=np.float32)

        for i in range(gh):
            for j in range(gw):
                y0, y1 = i * grid_size, min((i + 1) * grid_size, h)
                x0, x1 = j * grid_size, min((j + 1) * grid_size, w)
                patch = gray[y0:y1, x0:x1]
                if patch.size > 0:
                    laplacian_var = cv2.Laplacian(patch, cv2.CV_64F).var()
                    texture_map[i, j] = laplacian_var

        return texture_map

    def _depth_to_probability_fast(self, depth_map):
        h, w = depth_map.shape[:2]
        depth_flat = depth_map.ravel()
        indices = np.clip(depth_flat * (self.num_depth_bins - 1), 0, self.num_depth_bins - 1).astype(np.int32)

        prob = np.zeros((self.num_depth_bins, h * w), dtype=np.float32)
        bin_centers = (np.arange(self.num_depth_bins, dtype=np.float32) + 0.5) / self.num_depth_bins
        depth_vals = depth_flat[np.newaxis, :]
        diff = np.abs(bin_centers[:, np.newaxis] - depth_vals)
        prob = np.exp(-2.0 * (diff ** 2))

        prob_sum = prob.sum(axis=0, keepdims=True)
        prob_sum[prob_sum < 1e-10] = 1e-10
        prob /= prob_sum
        return prob

    def _guided_filter_fast(self, guidance, target, r=4, eps=0.05):
        if guidance.ndim == 3:
            guidance_gray = cv2.cvtColor(guidance, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        else:
            guidance_gray = guidance.astype(np.float32) / 255.0 if guidance.max() > 1 else guidance

        target = target.astype(np.float32)

        mean_I = cv2.boxFilter(guidance_gray, cv2.CV_32F, (r, r))
        mean_p = cv2.boxFilter(target, cv2.CV_32F, (r, r))
        mean_Ip = cv2.boxFilter(guidance_gray * target, cv2.CV_32F, (r, r))
        cov_Ip = mean_Ip - mean_I * mean_p

        mean_II = cv2.boxFilter(guidance_gray * guidance_gray, cv2.CV_32F, (r, r))
        var_I = mean_II - mean_I * mean_I

        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I

        mean_a = cv2.boxFilter(a, cv2.CV_32F, (r, r))
        mean_b = cv2.boxFilter(b, cv2.CV_32F, (r, r))

        q = mean_a * guidance_gray + mean_b
        return q.astype(np.float32)

    def _approx_crf_inference(self, image_rgb, prob, h, w):
        depth_bins = np.arange(self.num_depth_bins, dtype=np.float32) / (self.num_depth_bins - 1)
        initial_depth = np.sum(prob.reshape(self.num_depth_bins, h, w) * depth_bins[:, None, None], axis=0)

        filtered = self._guided_filter_fast(image_rgb, initial_depth, r=8, eps=0.1)
        edges = cv2.Canny(image_rgb, 30, 90)
        edge_mask = edges.astype(np.float32) / 255.0

        detail_map = cv2.Laplacian(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
        detail_map = np.abs(detail_map)
        detail_map = (detail_map - detail_map.min()) / (detail_map.max() - detail_map.min() + 1e-10)

        alpha = 0.4 + 0.5 * (1.0 - detail_map)
        blended = alpha * filtered + (1.0 - alpha) * initial_depth

        depth_edges = cv2.Sobel(initial_depth, cv2.CV_64F, 1, 1, ksize=3)
        depth_edges = np.abs(depth_edges)
        depth_edges = (depth_edges - depth_edges.min()) / (depth_edges.max() - depth_edges.min() + 1e-10)

        edge_confidence = edge_mask * (1.0 - depth_edges)
        local_mean = cv2.blur(blended, (5, 5))
        diff = blended - local_mean
        sharpened = local_mean + diff * (1.0 + 0.3 * edge_confidence)
        sharpened = np.clip(sharpened, 0, 1)

        return sharpened.astype(np.float32)

    def optimize(self, image_bgr, depth_map):
        if image_bgr is None or depth_map is None:
            return depth_map

        h_full, w_full = depth_map.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        is_low_texture, texture_var = self._detect_texture(gray)

        if is_low_texture and self.use_approx:
            return depth_map.astype(np.float32)

        if self.downscale > 1:
            h_small = h_full // self.downscale
            w_small = w_full // self.downscale
            image_small = cv2.resize(image_bgr, (w_small, h_small), interpolation=cv2.INTER_AREA)
            depth_small = cv2.resize(depth_map, (w_small, h_small), interpolation=cv2.INTER_AREA)
        else:
            image_small = image_bgr
            depth_small = depth_map
            h_small, w_small = h_full, w_full

        h, w = depth_small.shape[:2]

        prob = self._depth_to_probability_fast(depth_small)
        U = unary_from_softmax(prob)
        U = np.ascontiguousarray(U)

        if self.use_approx:
            image_rgb = cv2.cvtColor(image_small, cv2.COLOR_BGR2RGB).astype(np.uint8)
            optimized_small = self._approx_crf_inference(image_rgb, prob, h, w)
        else:
            d = dcrf.DenseCRF2D(w, h, self.num_depth_bins)
            d.setUnaryEnergy(U)

            pairwise_gaussian = create_pairwise_gaussian(
                sdims=(self.gaussian_sxy, self.gaussian_sxy), shape=(h, w)
            )
            d.addPairwiseEnergy(pairwise_gaussian, compat=self.gaussian_compat)

            image_rgb = cv2.cvtColor(image_small, cv2.COLOR_BGR2RGB).astype(np.uint8)
            pairwise_bilateral = create_pairwise_bilateral(
                sdims=(self.bilateral_sxy, self.bilateral_sxy),
                schan=(self.bilateral_srgb, self.bilateral_srgb, self.bilateral_srgb),
                img=image_rgb,
                chdim=2,
            )
            d.addPairwiseEnergy(pairwise_bilateral, compat=self.bilateral_compat)

            Q = d.inference(self.num_iterations)
            Q = np.array(Q).reshape((self.num_depth_bins, h, w))
            depth_bins = np.arange(self.num_depth_bins, dtype=np.float32) / (self.num_depth_bins - 1)
            optimized_small = np.sum(Q * depth_bins[:, None, None], axis=0)

        if self.downscale > 1:
            optimized = cv2.resize(optimized_small, (w_full, h_full), interpolation=cv2.INTER_LINEAR)
        else:
            optimized = optimized_small

        image_full_resized = cv2.resize(image_bgr, (w_full, h_full))
        optimized = self._guided_filter_fast(image_full_resized, optimized, r=3, eps=0.01)

        optimized = (optimized - optimized.min()) / (optimized.max() - optimized.min() + 1e-10)
        return optimized.astype(np.float32)

    def optimize_with_edge_guidance(self, image_bgr, depth_map, edge_map=None):
        if image_bgr is None or depth_map is None:
            return depth_map

        h_full, w_full = depth_map.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        is_low_texture, texture_var = self._detect_texture(gray)

        if edge_map is None:
            edge_map = cv2.Canny(gray, 50, 150)
            edge_map = edge_map.astype(np.float32) / 255.0

        if is_low_texture and self.use_approx:
            optimized = depth_map.astype(np.float32)
        else:
            optimized = self.optimize(image_bgr, depth_map)

        edge_mask = edge_map > 0.1
        if np.any(edge_mask):
            detail_map = cv2.Laplacian(gray, cv2.CV_64F)
            detail_map = np.abs(detail_map)
            detail_map = (detail_map - detail_map.min()) / (detail_map.max() - detail_map.min() + 1e-10)

            texture_mask = detail_map > 0.3
            if self.downscale > 1:
                edge_map_full = cv2.resize(edge_map, (w_full, h_full))
                texture_mask_full = cv2.resize(texture_mask.astype(np.uint8), (w_full, h_full)).astype(bool)
            else:
                edge_map_full = edge_map
                texture_mask_full = texture_mask

            edge_mask_full = edge_map_full > 0.1

            if np.any(edge_mask_full):
                depth_edges = cv2.Sobel(depth_map, cv2.CV_64F, 1, 1, ksize=3)
                depth_edges = np.abs(depth_edges)
                depth_edges = (depth_edges - depth_edges.min()) / (depth_edges.max() - depth_edges.min() + 1e-10)

                sharpened = optimized.copy()
                base_boost = 0.3
                texture_penalty = 0.8
                edge_boost = 1.0 + base_boost * edge_map_full * (1.0 - depth_edges) * (1.0 - texture_penalty * texture_mask_full.astype(np.float32))

                local_mean = cv2.blur(optimized, (5, 5))
                diff = optimized - local_mean
                sharpened = local_mean + diff * edge_boost
                sharpened = np.clip(sharpened, 0, 1)
                optimized = sharpened

        return optimized.astype(np.float32)
