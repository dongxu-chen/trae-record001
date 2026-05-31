import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from skimage.metrics import structural_similarity as ssim


class MotionAnalyzer:
    def __init__(self):
        self.prev_frame = None
        self.prev_gray = None

    def calculate_optical_flow(self, frame_gray: np.ndarray, prev_gray: np.ndarray) -> Dict:
        if prev_gray is None:
            return {
                "flow_magnitude": 0,
                "flow_mean": 0,
                "flow_max": 0,
                "motion_score": 0.5
            }
        
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, frame_gray,
            None,
            0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        return {
            "flow_magnitude": np.mean(magnitude),
            "flow_mean": np.mean(magnitude),
            "flow_max": np.max(magnitude),
            "motion_score": min(1.0, np.mean(magnitude) / 10.0)
        }

    def calculate_frame_difference(self, frame_gray: np.ndarray, prev_gray: np.ndarray) -> Dict:
        if prev_gray is None:
            return {
                "diff_mean": 0,
                "diff_std": 0,
                "motion_ratio": 0,
                "motion_score": 0.5
            }
        
        frame_diff = cv2.absdiff(frame_gray, prev_gray)
        
        _, motion_mask = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        motion_ratio = np.count_nonzero(motion_mask) / motion_mask.size
        
        return {
            "diff_mean": np.mean(frame_diff),
            "diff_std": np.std(frame_diff),
            "motion_ratio": motion_ratio,
            "motion_score": min(1.0, motion_ratio * 3)
        }

    def calculate_ssim(self, frame_gray: np.ndarray, prev_gray: np.ndarray) -> Dict:
        if prev_gray is None or frame_gray.shape != prev_gray.shape:
            return {
                "ssim_score": 1.0,
                "change_score": 0
            }
        
        ssim_value = ssim(frame_gray, prev_gray)
        
        return {
            "ssim_score": ssim_value,
            "change_score": 1.0 - ssim_value
        }

    def analyze_color_vibrancy(self, frame: np.ndarray) -> Dict:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        
        saturation = hsv[:, :, 1]
        brightness = hsv[:, :, 2]
        
        avg_saturation = np.mean(saturation) / 255.0
        avg_brightness = np.mean(brightness) / 255.0
        std_brightness = np.std(brightness) / 255.0
        
        vibrancy_score = avg_saturation * 0.5 + std_brightness * 0.3 + avg_brightness * 0.2
        
        return {
            "avg_saturation": avg_saturation,
            "avg_brightness": avg_brightness,
            "std_brightness": std_brightness,
            "vibrancy_score": min(1.0, vibrancy_score)
        }

    def analyze_color_harmony(self, frame: np.ndarray) -> Dict:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        h_channel = hsv[:, :, 0].flatten()
        
        hist, _ = np.histogram(h_channel, bins=12, range=(0, 180))
        hist = hist / hist.sum() if hist.sum() > 0 else hist
        
        dominant_hue_idx = np.argmax(hist)
        dominant_ratio = hist[dominant_hue_idx]
        
        complementary_idx = (dominant_hue_idx + 6) % 12
        complementary_ratio = hist[complementary_idx]
        
        analogous_ratio = (
            hist[(dominant_hue_idx - 1) % 12] +
            hist[dominant_hue_idx] +
            hist[(dominant_hue_idx + 1) % 12]
        )
        
        hue_entropy = -np.sum(hist * np.log2(hist + 1e-10))
        normalized_entropy = hue_entropy / np.log2(12)
        
        harmony_score = (
            analogous_ratio * 0.4 +
            complementary_ratio * 0.3 +
            (1 - abs(dominant_ratio - 0.3)) * 0.3
        )
        
        return {
            "dominant_hue": dominant_hue_idx * 15,
            "dominant_ratio": dominant_ratio,
            "analogous_ratio": analogous_ratio,
            "complementary_ratio": complementary_ratio,
            "hue_entropy": normalized_entropy,
            "harmony_score": min(1.0, harmony_score)
        }

    def extract_color_palette(self, frame: np.ndarray, num_colors: int = 5) -> Dict:
        pixels = frame.reshape(-1, 3).astype(np.float32)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )
        
        centers = centers.astype(np.uint8)
        
        unique_labels, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(counts)[::-1]
        
        palette = []
        for idx in sorted_indices:
            color = centers[idx].tolist()
            ratio = counts[idx] / len(labels)
            palette.append({
                "color": color,
                "ratio": ratio,
                "hex": "#{:02x}{:02x}{:02x}".format(*color)
            })
        
        return {
            "palette": palette,
            "dominant_color": palette[0]["color"] if palette else [0, 0, 0]
        }

    def analyze_contrast(self, frame: np.ndarray) -> Dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 256))
        hist = hist / hist.sum()
        
        cdf = np.cumsum(hist)
        low_threshold = np.argmax(cdf > 0.01)
        high_threshold = np.argmax(cdf > 0.99)
        
        contrast_ratio = (high_threshold - low_threshold) / 255.0
        
        std = np.std(gray)
        std_score = min(1.0, std / 64.0)
        
        michelson_contrast = (gray.max() - gray.min()) / (gray.max() + gray.min() + 1e-6)
        
        contrast_score = contrast_ratio * 0.5 + std_score * 0.3 + michelson_contrast * 0.2
        
        return {
            "contrast_ratio": contrast_ratio,
            "std_score": std_score,
            "michelson_contrast": michelson_contrast,
            "contrast_score": min(1.0, contrast_score)
        }

    def detect_video_style(self, frame: np.ndarray, color_analysis: Dict, composition_analysis: Dict) -> Dict:
        palette_info = self.extract_color_palette(frame)
        harmony_info = self.analyze_color_harmony(frame)
        contrast_info = self.analyze_contrast(frame)
        
        dominant_color = palette_info["dominant_color"]
        r, g, b = dominant_color
        
        coldness = ((b - (r + g) / 2) + 128) / 256
        coldness = max(0, min(1, coldness))
        
        saturation = color_analysis.get("avg_saturation", 0.5)
        brightness = color_analysis.get("avg_brightness", 0.5)
        contrast = contrast_info["contrast_score"]
        harmony = harmony_info["harmony_score"]
        
        tech_score = (
            coldness * 0.35 +
            contrast * 0.25 +
            (1 - saturation) * 0.2 +
            harmony * 0.2
        )
        
        cute_score = (
            (1 - coldness) * 0.25 +
            saturation * 0.25 +
            brightness * 0.25 +
            harmony * 0.25
        )
        
        warm_score = (1 - coldness)
        cool_score = coldness
        
        styles = {
            "technology": min(1.0, tech_score),
            "cute": min(1.0, cute_score),
            "warm": warm_score,
            "cool": cool_score,
            "professional": contrast * 0.6 + harmony * 0.4,
            "artistic": harmony * 0.5 + saturation * 0.5
        }
        
        main_style = max(styles.keys(), key=lambda k: styles[k])
        
        return {
            "styles": styles,
            "main_style": main_style,
            "dominant_color": dominant_color,
            "coldness": coldness,
            "palette": palette_info["palette"]
        }

    def analyze_composition(self, frame: np.ndarray) -> Dict:
        h, w = frame.shape[:2]
        
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        center_x, center_y = w // 2, h // 2
        center_region = gray[center_y - h//4:center_y + h//4, center_x - w//4:center_x + w//4]
        center_brightness = np.mean(center_region) / 255.0
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        
        thirds_x = [w // 3, 2 * w // 3]
        thirds_y = [h // 3, 2 * h // 3]
        
        rule_of_thirds_score = 0
        for tx in thirds_x:
            for ty in thirds_y:
                region = gray[ty - 20:ty + 20, tx - 20:tx + 20]
                if region.size > 0:
                    rule_of_thirds_score += np.std(region) / 255.0
        rule_of_thirds_score /= 4
        
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, 
                                minLineLength=min(w, h) // 10, maxLineGap=20)
        line_symmetry_score = self._calculate_line_symmetry(lines, w, h) if lines is not None else 0.3
        
        balance_score = self._calculate_visual_balance(gray)
        
        golden_ratio_score = self._calculate_golden_ratio_composition(gray, w, h)
        
        depth_score = self._calculate_depth_perception(frame)
        
        symmetry_score = self._calculate_symmetry(gray)
        
        composition_score = (
            edge_density * 0.15 +
            center_brightness * 0.1 +
            rule_of_thirds_score * 0.2 +
            line_symmetry_score * 0.15 +
            balance_score * 0.15 +
            golden_ratio_score * 0.15 +
            symmetry_score * 0.1
        )
        
        return {
            "center_brightness": center_brightness,
            "edge_density": edge_density,
            "rule_of_thirds_score": rule_of_thirds_score,
            "line_symmetry_score": line_symmetry_score,
            "balance_score": balance_score,
            "golden_ratio_score": golden_ratio_score,
            "depth_score": depth_score,
            "symmetry_score": symmetry_score,
            "composition_score": min(1.0, composition_score)
        }

    def _calculate_line_symmetry(self, lines, w: int, h: int) -> float:
        if lines is None or len(lines) == 0:
            return 0.3
        
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            if abs(angle) < 15 or abs(angle) > 165:
                horizontal_lines.append(((x1 + x2) / 2, (y1 + y2) / 2))
            elif abs(angle - 90) < 15 or abs(angle + 90) < 15:
                vertical_lines.append(((x1 + x2) / 2, (y1 + y2) / 2))
        
        h_symmetry = 0.5
        if horizontal_lines:
            h_centers = [y for _, y in horizontal_lines]
            h_centers = sorted(h_centers)
            if len(h_centers) >= 2:
                third_h = h / 3
                near_thirds = sum(1 for y in h_centers 
                                  if abs(y - third_h) < h * 0.1 or abs(y - 2 * third_h) < h * 0.1)
                h_symmetry = min(1.0, near_thirds / 2 + 0.3)
        
        v_symmetry = 0.5
        if vertical_lines:
            v_centers = [x for x, _ in vertical_lines]
            v_centers = sorted(v_centers)
            if len(v_centers) >= 2:
                third_w = w / 3
                near_thirds = sum(1 for x in v_centers 
                                  if abs(x - third_w) < w * 0.1 or abs(x - 2 * third_w) < w * 0.1)
                v_symmetry = min(1.0, near_thirds / 2 + 0.3)
        
        return (h_symmetry + v_symmetry) / 2

    def _calculate_visual_balance(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        
        left_half = gray[:, :w//2]
        right_half = gray[:, w//2:]
        top_half = gray[:h//2, :]
        bottom_half = gray[h//2:, :]
        
        left_brightness = np.mean(left_half)
        right_brightness = np.mean(right_half)
        top_brightness = np.mean(top_half)
        bottom_brightness = np.mean(bottom_half)
        
        h_balance = 1 - abs(left_brightness - right_brightness) / 255
        v_balance = 1 - abs(top_brightness - bottom_brightness) / 255
        
        left_contrast = np.std(left_half)
        right_contrast = np.std(right_half)
        contrast_balance = 1 - abs(left_contrast - right_contrast) / 128
        
        return (h_balance * 0.4 + v_balance * 0.4 + contrast_balance * 0.2)

    def _calculate_golden_ratio_composition(self, gray: np.ndarray, w: int, h: int) -> float:
        golden_ratio = 1.618
        
        gr_w = w / golden_ratio
        gr_h = h / golden_ratio
        
        interest_points = [
            (w // 2 - int(gr_w / 2), h // 2 - int(gr_h / 2)),
            (w // 2 + int(gr_w / 2), h // 2 - int(gr_h / 2)),
            (w // 2 - int(gr_w / 2), h // 2 + int(gr_h / 2)),
            (w // 2 + int(gr_w / 2), h // 2 + int(gr_h / 2)),
        ]
        
        point_scores = []
        for (px, py) in interest_points:
            px = max(10, min(w - 10, px))
            py = max(10, min(h - 10, py))
            
            region = gray[py-10:py+10, px-10:px+10]
            if region.size > 0:
                std = np.std(region)
                point_scores.append(std / 128)
        
        return np.mean(point_scores) if point_scores else 0.5

    def _calculate_depth_perception(self, frame: np.ndarray) -> float:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = np.var(laplacian)
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.count_nonzero(edges) / edges.size
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        gradient_mean = np.mean(gradient_magnitude)
        
        depth_score = (
            min(1.0, laplacian_var / 1000) * 0.4 +
            edge_density * 0.3 +
            min(1.0, gradient_mean / 50) * 0.3
        )
        
        return depth_score

    def _calculate_symmetry(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        
        left = gray[:, :w//2]
        right_flipped = cv2.flip(gray[:, w//2:], 1)
        
        min_width = min(left.shape[1], right_flipped.shape[1])
        left = left[:, :min_width]
        right_flipped = right_flipped[:, :min_width]
        
        diff = cv2.absdiff(left, right_flipped)
        h_symmetry = 1 - np.mean(diff) / 255
        
        top = gray[:h//2, :]
        bottom_flipped = cv2.flip(gray[h//2:, :], 0)
        
        min_height = min(top.shape[0], bottom_flipped.shape[0])
        top = top[:min_height, :]
        bottom_flipped = bottom_flipped[:min_height, :]
        
        diff = cv2.absdiff(top, bottom_flipped)
        v_symmetry = 1 - np.mean(diff) / 255
        
        return max(h_symmetry, v_symmetry)

    def analyze_frame_motion(self, frame: np.ndarray, prev_frame: Optional[np.ndarray] = None) -> Dict:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        if prev_frame is not None:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY)
        else:
            prev_gray = self.prev_gray
        
        flow_result = self.calculate_optical_flow(frame_gray, prev_gray)
        diff_result = self.calculate_frame_difference(frame_gray, prev_gray)
        ssim_result = self.calculate_ssim(frame_gray, prev_gray)
        
        self.prev_gray = frame_gray.copy()
        
        motion_score = (
            flow_result["motion_score"] * 0.4 +
            diff_result["motion_score"] * 0.3 +
            ssim_result["change_score"] * 0.3
        )
        
        return {
            "optical_flow": flow_result,
            "frame_difference": diff_result,
            "ssim": ssim_result,
            "motion_score": motion_score,
            "is_high_motion": motion_score > 0.5
        }

    def analyze_frame_quality(self, frame: np.ndarray) -> Dict:
        color_result = self.analyze_color_vibrancy(frame)
        composition_result = self.analyze_composition(frame)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, laplacian_var / 500.0)
        
        quality_score = (
            color_result["vibrancy_score"] * 0.35 +
            composition_result["composition_score"] * 0.35 +
            sharpness_score * 0.3
        )
        
        return {
            "color_analysis": color_result,
            "composition_analysis": composition_result,
            "sharpness_score": sharpness_score,
            "quality_score": quality_score
        }

    def get_action_score(self, motion_result: Dict) -> float:
        motion_score = motion_result.get("motion_score", 0.5)
        
        preferred_motion = max(0, 1.0 - abs(motion_score - 0.4) * 2)
        
        return preferred_motion


class FrameScorer:
    def __init__(self, 
                 face_weight: float = 0.25,
                 motion_weight: float = 0.15,
                 quality_weight: float = 0.15,
                 expression_weight: float = 0.15,
                 color_weight: float = 0.15,
                 composition_weight: float = 0.15):
        self.face_weight = face_weight
        self.motion_weight = motion_weight
        self.quality_weight = quality_weight
        self.expression_weight = expression_weight
        self.color_weight = color_weight
        self.composition_weight = composition_weight

    def calculate_aesthetics_score(self, frame: np.ndarray, quality_analysis: Dict) -> Dict:
        color_analysis = quality_analysis.get("color_analysis", {})
        composition_analysis = quality_analysis.get("composition_analysis", {})
        
        vibrancy_score = color_analysis.get("vibrancy_score", 0.5)
        harmony_score = color_analysis.get("harmony_score", 0.5)
        contrast_score = color_analysis.get("contrast_score", 0.5)
        composition_score = composition_analysis.get("composition_score", 0.5)
        
        color_aesthetics_score = (
            vibrancy_score * 0.4 +
            harmony_score * 0.35 +
            contrast_score * 0.25
        )
        
        aesthetics_score = (
            color_aesthetics_score * 0.55 +
            composition_score * 0.45
        )
        
        return {
            "color_aesthetics_score": color_aesthetics_score,
            "composition_score": composition_score,
            "vibrancy_score": vibrancy_score,
            "harmony_score": harmony_score,
            "contrast_score": contrast_score,
            "aesthetics_score": aesthetics_score
        }

    def score_frame(self, 
                    frame: np.ndarray,
                    face_analysis: Dict,
                    motion_analysis: Dict,
                    quality_analysis: Dict,
                    aesthetics_analysis: Optional[Dict] = None) -> Dict:
        face_score = face_analysis.get("face_score", 0)
        expression_score = face_analysis.get("expression_score", 0)
        motion_score = motion_analysis.get("motion_score", 0.5)
        quality_score = quality_analysis.get("quality_score", 0)
        
        if aesthetics_analysis is None:
            aesthetics_analysis = self.calculate_aesthetics_score(frame, quality_analysis)
        
        aesthetics_score = aesthetics_analysis.get("aesthetics_score", 0.5)
        color_score = aesthetics_analysis.get("color_aesthetics_score", 0.5)
        composition_score = aesthetics_analysis.get("composition_score", 0.5)
        
        motion_score = max(0, 1.0 - abs(motion_score - 0.3) * 2)
        
        total_score = (
            face_score * self.face_weight +
            motion_score * self.motion_weight +
            quality_score * self.quality_weight +
            expression_score * self.expression_weight +
            color_score * self.color_weight +
            composition_score * self.composition_weight
        )
        
        return {
            "total_score": total_score,
            "face_score": face_score,
            "expression_score": expression_score,
            "motion_score": motion_score,
            "quality_score": quality_score,
            "aesthetics_score": aesthetics_score,
            "color_score": color_score,
            "composition_score": composition_score,
            "score_breakdown": {
                "face": face_score * self.face_weight,
                "motion": motion_score * self.motion_weight,
                "quality": quality_score * self.quality_weight,
                "expression": expression_score * self.expression_weight,
                "color": color_score * self.color_weight,
                "composition": composition_score * self.composition_weight
            }
        }

    def rank_frames(self, frame_scores: List[Tuple[int, Dict]], top_k: int = 5) -> List[Tuple[int, Dict]]:
        sorted_frames = sorted(
            frame_scores,
            key=lambda x: x[1]["total_score"],
            reverse=True
        )
        return sorted_frames[:top_k]
