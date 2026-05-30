import numpy as np
import cv2
from scipy.ndimage import sobel
from scipy.signal import fftconvolve


class FusionQualityAssessor:
    def __init__(self):
        self.results = {}
        self.mos_scores = {}
        self.subjective_weights = {}
        self.mos_history = []

    def collect_mos(self, image_id, score, observer_id=None, comment=""):
        if not (1 <= score <= 5):
            raise ValueError("MOS score must be between 1 and 5")
        if image_id not in self.mos_scores:
            self.mos_scores[image_id] = []
        entry = {"score": float(score), "observer": observer_id, "comment": comment}
        self.mos_scores[image_id].append(entry)
        self.mos_history.append({"image_id": image_id, **entry})

    def get_mos(self, image_id=None):
        if image_id is not None:
            if image_id not in self.mos_scores or len(self.mos_scores[image_id]) == 0:
                return None
            scores = [e["score"] for e in self.mos_scores[image_id]]
            return {
                "mean": np.mean(scores),
                "std": np.std(scores),
                "count": len(scores),
                "95_ci": 1.96 * np.std(scores) / np.sqrt(len(scores)) if len(scores) > 1 else 0,
                "scores": scores,
            }
        else:
            return {iid: self.get_mos(iid) for iid in self.mos_scores.keys()}

    def _normalize_metric(self, value, metric_name):
        ranges = {
            "entropy": (0, 8),
            "spatial_frequency": (0, 50),
            "average_gradient": (0, 20),
            "standard_deviation": (0, 80),
            "MI_avg": (0, 5),
            "NMI_avg": (0, 1),
            "Q_AB_avg": (0, 1),
            "FMI_avg": (0, 5),
            "PSNR": (0, 50),
            "SSIM": (0, 1),
        }
        low, high = ranges.get(metric_name, (0, 1))
        return np.clip((value - low) / (high - low + 1e-10), 0, 1)

    def compute_objective_quality_score(self, results=None):
        if results is None:
            results = self.results
        key_metrics = ["NMI_avg", "Q_AB_avg", "FMI_avg", "entropy", "spatial_frequency", "average_gradient"]
        available = [m for m in key_metrics if m in results]
        if not available:
            return None
        default_weights = {
            "NMI_avg": 0.25,
            "Q_AB_avg": 0.25,
            "FMI_avg": 0.2,
            "entropy": 0.1,
            "spatial_frequency": 0.1,
            "average_gradient": 0.1,
        }
        weights = self.subjective_weights if self.subjective_weights else default_weights
        score = 0
        total_w = 0
        for m in available:
            norm_val = self._normalize_metric(results[m], m)
            w = weights.get(m, 0.1)
            score += norm_val * w
            total_w += w
        if total_w > 0:
            score = score / total_w
        results["Objective_Score"] = score
        return score

    def compute_combined_score(self, image_id, results=None, mos_weight=0.4, obj_weight=0.6):
        mos_data = self.get_mos(image_id)
        mos_score = mos_data["mean"] / 5.0 if mos_data else None
        obj_score = self.compute_objective_quality_score(results)
        combined = None
        if mos_score is not None and obj_score is not None:
            combined = mos_weight * mos_score + obj_weight * obj_score
        elif obj_score is not None:
            combined = obj_score
        if combined is not None and results is not None:
            if mos_score is not None:
                results["MOS"] = mos_data["mean"]
                results["MOS_95CI"] = mos_data["95_ci"]
            results["Objective_Score"] = obj_score
            if mos_score is not None:
                results["Combined_Score"] = combined
        return combined

    def set_subjective_weights(self, weights):
        self.subjective_weights = weights

    def predict_mos_from_objective(self, results=None):
        if results is None:
            results = self.results
        obj_score = self.compute_objective_quality_score(results)
        if obj_score is None:
            return None
        predicted_mos = 1.0 + obj_score * 4.0
        if results is not None:
            results["Predicted_MOS"] = predicted_mos
        return predicted_mos

    @staticmethod
    def _to_gray(image):
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
        return image.astype(np.float64)

    def mutual_information(self, img_fused, img_source):
        fused = self._to_gray(img_fused)
        source = self._to_gray(img_source)
        hist_2d, _, _ = np.histogram2d(fused.ravel(), source.ravel(), bins=256, range=[[0, 255], [0, 255]])
        hist_2d = hist_2d / hist_2d.sum()
        px = hist_2d.sum(axis=1)
        py = hist_2d.sum(axis=0)
        px_py = px[:, None] * py[None, :]
        nz = hist_2d > 0
        mi = np.sum(hist_2d[nz] * np.log2(hist_2d[nz] / px_py[nz]))
        return mi

    def normalized_mutual_information(self, img_fused, img_source):
        mi = self.mutual_information(img_fused, img_source)
        fused = self._to_gray(img_fused)
        source = self._to_gray(img_source)
        h_fused = -np.sum(fused.ravel() * np.log2(fused.ravel() + 1e-10) / fused.size)
        h_source = -np.sum(source.ravel() * np.log2(source.ravel() + 1e-10) / source.size)
        hist_f, _ = np.histogram(fused.ravel(), bins=256, range=[0, 255])
        hist_f = hist_f / hist_f.sum()
        nz_f = hist_f > 0
        h_f = -np.sum(hist_f[nz_f] * np.log2(hist_f[nz_f]))
        hist_s, _ = np.histogram(source.ravel(), bins=256, range=[0, 255])
        hist_s = hist_s / hist_s.sum()
        nz_s = hist_s > 0
        h_s = -np.sum(hist_s[nz_s] * np.log2(hist_s[nz_s]))
        if h_f + h_s == 0:
            return 0
        return 2 * mi / (h_f + h_s)

    def q_ab(self, img_fused, img_source, edge_threshold=1.5):
        fused = self._to_gray(img_fused)
        source = self._to_gray(img_source)

        def _edge_info(img):
            sx = sobel(img, axis=1)
            sy = sobel(img, axis=0)
            strength = np.sqrt(sx ** 2 + sy ** 2)
            orientation = np.arctan2(sy, sx + 1e-10)
            return strength, orientation

        s_src, o_src = _edge_info(source)
        s_fus, o_fus = _edge_info(fused)
        s_ratio = np.where(s_src > edge_threshold, s_fus / (s_src + 1e-10), 0)
        o_diff = np.abs(o_fus - o_src)
        o_diff = np.minimum(o_diff, 2 * np.pi - o_diff)
        q_s = np.where(s_src > edge_threshold, 1 - np.abs(1 - s_ratio), 0)
        q_o = np.where(s_src > edge_threshold, 1 - o_diff / (np.pi / 2), 0)
        q = np.maximum(q_s * q_o, 0)
        mask = s_src > edge_threshold
        if mask.sum() == 0:
            return 0.0
        return np.sum(q) / mask.sum()

    def feature_mutual_information(self, img_fused, img_source):
        fused = self._to_gray(img_fused)
        source = self._to_gray(img_source)

        def _local_features(img, block_size=8):
            h, w = img.shape
            features = []
            for i in range(0, h - block_size + 1, block_size):
                for j in range(0, w - block_size + 1, block_size):
                    block = img[i:i + block_size, j:j + block_size]
                    mean_val = block.mean()
                    std_val = block.std()
                    features.append([mean_val, std_val])
            return np.array(features)

        feat_f = _local_features(fused)
        feat_s = _local_features(source)
        if len(feat_f) == 0:
            return 0.0
        mi_total = 0
        for col in range(feat_f.shape[1]):
            hist_2d, _, _ = np.histogram2d(feat_f[:, col], feat_s[:, col], bins=64)
            hist_2d = hist_2d / hist_2d.sum()
            px = hist_2d.sum(axis=1)
            py = hist_2d.sum(axis=0)
            px_py = px[:, None] * py[None, :]
            nz = hist_2d > 0
            if nz.any():
                mi_total += np.sum(hist_2d[nz] * np.log2(hist_2d[nz] / (px_py[nz] + 1e-10)))
        return mi_total / feat_f.shape[1]

    def psnr(self, img_fused, img_reference):
        fused = self._to_gray(img_fused)
        ref = self._to_gray(img_reference)
        mse = np.mean((fused - ref) ** 2)
        if mse == 0:
            return float("inf")
        return 10 * np.log10(255.0 ** 2 / mse)

    def ssim(self, img1, img2, window_size=11):
        i1 = self._to_gray(img1)
        i2 = self._to_gray(img2)
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        mu1 = cv2.GaussianBlur(i1, (window_size, window_size), 1.5)
        mu2 = cv2.GaussianBlur(i2, (window_size, window_size), 1.5)
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        sigma1_sq = cv2.GaussianBlur(i1 ** 2, (window_size, window_size), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(i2 ** 2, (window_size, window_size), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(i1 * i2, (window_size, window_size), 1.5) - mu1_mu2
        numerator = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
        denominator = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
        ssim_map = numerator / (denominator + 1e-10)
        return ssim_map.mean()

    def spatial_frequency(self, image):
        img = self._to_gray(image)
        h, w = img.shape
        rf = np.sqrt(np.mean(np.diff(img, axis=1) ** 2))
        cf = np.sqrt(np.mean(np.diff(img, axis=0) ** 2))
        return np.sqrt(rf ** 2 + cf ** 2)

    def average_gradient(self, image):
        img = self._to_gray(image)
        gx = np.diff(img, axis=1)
        gy = np.diff(img, axis=0)
        gx = np.pad(gx, ((0, 0), (0, 1)), mode="edge")
        gy = np.pad(gy, ((0, 1), (0, 0)), mode="edge")
        return np.mean(np.sqrt((gx ** 2 + gy ** 2) / 2))

    def entropy(self, image):
        img = self._to_gray(image)
        hist, _ = np.histogram(img.ravel(), bins=256, range=[0, 255])
        hist = hist / hist.sum()
        nz = hist > 0
        return -np.sum(hist[nz] * np.log2(hist[nz]))

    def standard_deviation(self, image):
        img = self._to_gray(image)
        return np.std(img)

    def evaluate(self, img_fused, img_sources, reference=None, image_id=None, mos_weight=0.4, obj_weight=0.6):
        results = {}
        results["entropy"] = self.entropy(img_fused)
        results["spatial_frequency"] = self.spatial_frequency(img_fused)
        results["average_gradient"] = self.average_gradient(img_fused)
        results["standard_deviation"] = self.standard_deviation(img_fused)

        mi_values = []
        nmi_values = []
        qab_values = []
        fmi_values = []
        for i, src in enumerate(img_sources):
            mi = self.mutual_information(img_fused, src)
            nmi = self.normalized_mutual_information(img_fused, src)
            qab = self.q_ab(img_fused, src)
            fmi = self.feature_mutual_information(img_fused, src)
            mi_values.append(mi)
            nmi_values.append(nmi)
            qab_values.append(qab)
            fmi_values.append(fmi)
            results[f"MI_source_{i}"] = mi
            results[f"NMI_source_{i}"] = nmi
            results[f"Q_AB_source_{i}"] = qab
            results[f"FMI_source_{i}"] = fmi

        results["MI_avg"] = np.mean(mi_values)
        results["NMI_avg"] = np.mean(nmi_values)
        results["Q_AB_avg"] = np.mean(qab_values)
        results["FMI_avg"] = np.mean(fmi_values)

        if reference is not None:
            results["PSNR"] = self.psnr(img_fused, reference)
            results["SSIM"] = self.ssim(img_fused, reference)

        self.predict_mos_from_objective(results)

        if image_id is not None:
            self.compute_combined_score(image_id, results, mos_weight, obj_weight)

        self.results = results
        return results

    def format_results(self, results=None):
        if results is None:
            results = self.results
        lines = []
        lines.append("=" * 60)
        lines.append("  Fusion Quality Assessment Report")
        lines.append("=" * 60)
        has_mos = "MOS" in results
        has_combined = "Combined_Score" in results
        obj_score = results.get("Objective_Score", None)
        predicted_mos = results.get("Predicted_MOS", None)

        if has_mos:
            lines.append("--- Subjective Quality ---")
            lines.append(f"  {'MOS':25s}: {results['MOS']:.4f} / 5.0")
            if "MOS_95CI" in results:
                lines.append(f"  {'MOS_95CI':25s}: ±{results['MOS_95CI']:.4f}")
            lines.append("")

        lines.append("--- Objective Quality ---")
        obj_keys = []
        for key, value in sorted(results.items()):
            if key.startswith("MI_") or key.startswith("NMI_") or key.startswith("Q_AB_") or key.startswith("FMI_"):
                if not key.endswith("_avg") and key.startswith(("MI_source_", "NMI_source_", "Q_AB_source_", "FMI_source_")):
                    continue
                obj_keys.append(key)
            elif key in ("entropy", "spatial_frequency", "average_gradient", "standard_deviation", "PSNR", "SSIM"):
                obj_keys.append(key)
        for key in obj_keys:
            lines.append(f"  {key:25s}: {results[key]:.4f}")
        lines.append("")

        lines.append("--- Combined Scores ---")
        if predicted_mos is not None:
            lines.append(f"  {'Predicted_MOS':25s}: {predicted_mos:.4f} / 5.0")
        if obj_score is not None:
            lines.append(f"  {'Objective_Score':25s}: {obj_score:.4f} (0~1)")
        if has_combined:
            lines.append(f"  {'Combined_Score':25s}: {results['Combined_Score']:.4f} (0~1)")
            lines.append(f"  {'  *MOS weight':25s}: 0.4, Objective: 0.6")
        lines.append("=" * 60)
        return "\n".join(lines)
