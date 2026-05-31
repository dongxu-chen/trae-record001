import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ctr_predictor import CTRPredictor, CTRFeature
import json
import os
from datetime import datetime


@dataclass
class CompetitorCover:
    name: str
    image: Optional[np.ndarray] = None
    source: str = ""
    category: str = ""
    video_style: str = ""
    features: Optional[CTRFeature] = None
    ctr_prediction: Optional[Dict] = None


class CompetitorAnalyzer:
    def __init__(self, ctr_predictor: Optional[CTRPredictor] = None):
        self.ctr_predictor = ctr_predictor or CTRPredictor()
        self.competitors: List[CompetitorCover] = []
        self.our_cover: Optional[CompetitorCover] = None
        self.comparison_results: Optional[Dict] = None

        self.industry_benchmarks = {
            "entertainment": {
                "avg_ctr": 0.065,
                "top_ctr": 0.12,
                "avg_face_presence": 0.7,
                "avg_saturation": 0.55,
                "avg_brightness": 0.50,
            },
            "gaming": {
                "avg_ctr": 0.058,
                "top_ctr": 0.10,
                "avg_face_presence": 0.5,
                "avg_saturation": 0.65,
                "avg_brightness": 0.45,
            },
            "education": {
                "avg_ctr": 0.045,
                "top_ctr": 0.08,
                "avg_face_presence": 0.6,
                "avg_saturation": 0.40,
                "avg_brightness": 0.55,
            },
            "tech": {
                "avg_ctr": 0.050,
                "top_ctr": 0.09,
                "avg_face_presence": 0.4,
                "avg_saturation": 0.45,
                "avg_brightness": 0.50,
            },
            "lifestyle": {
                "avg_ctr": 0.060,
                "top_ctr": 0.11,
                "avg_face_presence": 0.8,
                "avg_saturation": 0.55,
                "avg_brightness": 0.55,
            },
            "food": {
                "avg_ctr": 0.070,
                "top_ctr": 0.13,
                "avg_face_presence": 0.5,
                "avg_saturation": 0.70,
                "avg_brightness": 0.55,
            },
            "music": {
                "avg_ctr": 0.055,
                "top_ctr": 0.10,
                "avg_face_presence": 0.7,
                "avg_saturation": 0.60,
                "avg_brightness": 0.45,
            },
            "default": {
                "avg_ctr": 0.050,
                "top_ctr": 0.09,
                "avg_face_presence": 0.5,
                "avg_saturation": 0.50,
                "avg_brightness": 0.50,
            },
        }

    def add_our_cover(self, image: np.ndarray, name: str = "我方封面",
                      category: str = "", video_style: str = "",
                      face_analysis: Optional[Dict] = None,
                      quality_analysis: Optional[Dict] = None,
                      composition_analysis: Optional[Dict] = None) -> Dict:
        feature = self.ctr_predictor.extract_features(
            image, face_analysis, quality_analysis, composition_analysis
        )
        prediction = self.ctr_predictor.predict_ctr(feature, video_style, category)

        self.our_cover = CompetitorCover(
            name=name,
            image=image,
            category=category,
            video_style=video_style,
            features=feature,
            ctr_prediction=prediction,
        )

        return prediction

    def add_competitor(self, image: np.ndarray, name: str,
                       source: str = "", category: str = "",
                       video_style: str = "",
                       face_analysis: Optional[Dict] = None,
                       quality_analysis: Optional[Dict] = None,
                       composition_analysis: Optional[Dict] = None) -> Dict:
        feature = self.ctr_predictor.extract_features(
            image, face_analysis, quality_analysis, composition_analysis
        )
        prediction = self.ctr_predictor.predict_ctr(feature, video_style, category)

        competitor = CompetitorCover(
            name=name,
            image=image,
            source=source,
            category=category,
            video_style=video_style,
            features=feature,
            ctr_prediction=prediction,
        )
        self.competitors.append(competitor)

        return prediction

    def clear_competitors(self):
        self.competitors = []

    def compare_all(self, category: Optional[str] = None) -> Dict:
        if not self.our_cover:
            return {"error": "请先添加我方封面"}

        if not self.competitors:
            return {"error": "请至少添加一个竞品封面"}

        all_covers = [self.our_cover] + self.competitors
        all_predictions = [c.ctr_prediction for c in all_covers]

        our_ctr = self.our_cover.ctr_prediction["predicted_ctr"]
        competitor_ctrs = [c.ctr_prediction["predicted_ctr"] for c in self.competitors]
        avg_comp_ctr = float(np.mean(competitor_ctrs))
        max_comp_ctr = float(np.max(competitor_ctrs))

        ctr_rank = 1
        for cctr in competitor_ctrs:
            if cctr > our_ctr:
                ctr_rank += 1

        feature_comparison = self._compare_features(all_covers)

        radar_data = self._generate_radar_data(all_covers)

        strengths, weaknesses = self._identify_strengths_weaknesses()

        benchmark_comparison = self._compare_to_benchmarks(category)

        suggestions = self._generate_competitive_suggestions(
            strengths, weaknesses, benchmark_comparison
        )

        self.comparison_results = {
            "our_cover": {
                "name": self.our_cover.name,
                "predicted_ctr": our_ctr,
                "ctr_percentage": f"{our_ctr * 100:.2f}%",
                "confidence": self.our_cover.ctr_prediction["confidence"],
            },
            "competitors": [
                {
                    "name": c.name,
                    "predicted_ctr": c.ctr_prediction["predicted_ctr"],
                    "ctr_percentage": f"{c.ctr_prediction['predicted_ctr'] * 100:.2f}%",
                    "confidence": c.ctr_prediction["confidence"],
                }
                for c in self.competitors
            ],
            "ctr_rank": ctr_rank,
            "total_compared": len(all_covers),
            "our_vs_avg": our_ctr - avg_comp_ctr,
            "our_vs_avg_percent": (
                (our_ctr / avg_comp_ctr - 1) * 100 if avg_comp_ctr > 0 else 0
            ),
            "our_vs_best": our_ctr - max_comp_ctr,
            "avg_competitor_ctr": avg_comp_ctr,
            "best_competitor_ctr": max_comp_ctr,
            "feature_comparison": feature_comparison,
            "radar_data": radar_data,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "benchmark_comparison": benchmark_comparison,
            "suggestions": suggestions,
            "category": category,
        }

        return self.comparison_results

    def _compare_features(self, covers: List[CompetitorCover]) -> Dict:
        feature_names = [
            "color_vibrancy", "color_harmony", "contrast_score",
            "composition_score", "face_presence", "face_expression",
            "brightness", "saturation", "sharpness", "symmetry",
            "visual_balance", "edge_density",
        ]

        comparison = {}
        for fname in feature_names:
            values = []
            for c in covers:
                val = getattr(c.features, fname, 0.0)
                values.append({"name": c.name, "value": val})

            our_val = values[0]["value"]
            others = [v["value"] for v in values[1:]]
            avg_others = float(np.mean(others)) if others else 0

            if avg_others > 0:
                diff_pct = (our_val - avg_others) / avg_others * 100
            else:
                diff_pct = 0

            comparison[fname] = {
                "values": values,
                "our_value": our_val,
                "avg_competitor": avg_others,
                "diff_percent": diff_pct,
                "advantage": diff_pct > 0,
            }

        return comparison

    def _generate_radar_data(self, covers: List[CompetitorCover]) -> Dict:
        key_features = [
            "color_vibrancy", "contrast_score", "composition_score",
            "face_presence", "sharpness", "visual_balance",
        ]

        labels = [
            "色彩鲜艳度", "对比度", "构图", "人脸元素", "清晰度", "视觉平衡",
        ]

        datasets = []
        for c in covers:
            data = [getattr(c.features, f, 0.0) for f in key_features]
            datasets.append({"name": c.name, "data": data})

        return {"labels": labels, "datasets": datasets}

    def _identify_strengths_weaknesses(self) -> Tuple[List[str], List[str]]:
        if not self.our_cover or not self.competitors:
            return [], []

        feature_names = [
            "color_vibrancy", "color_harmony", "contrast_score",
            "composition_score", "face_presence", "face_expression",
            "brightness", "saturation", "sharpness",
        ]

        feature_labels = {
            "color_vibrancy": "色彩鲜艳度",
            "color_harmony": "颜色和谐度",
            "contrast_score": "对比度",
            "composition_score": "构图质量",
            "face_presence": "人脸元素",
            "face_expression": "表情吸引力",
            "brightness": "亮度",
            "saturation": "饱和度",
            "sharpness": "清晰度",
        }

        strengths = []
        weaknesses = []

        our_features = self.our_cover.features
        for fname in feature_names:
            our_val = getattr(our_features, fname, 0.0)
            comp_vals = [getattr(c.features, fname, 0.0) for c in self.competitors]
            avg_comp = float(np.mean(comp_vals)) if comp_vals else 0

            label = feature_labels.get(fname, fname)

            if our_val > avg_comp * 1.15:
                strengths.append(f"{label}（高于竞品平均 {(our_val/avg_comp-1)*100:.0f}%）")
            elif our_val < avg_comp * 0.85:
                weaknesses.append(f"{label}（低于竞品平均 {(1-our_val/avg_comp)*100:.0f}%）")

        return strengths, weaknesses

    def _compare_to_benchmarks(self, category: Optional[str] = None) -> Dict:
        cat = category or "default"
        benchmark = self.industry_benchmarks.get(cat, self.industry_benchmarks["default"])

        if not self.our_cover:
            return {}

        our = self.our_cover.features
        our_ctr = self.our_cover.ctr_prediction["predicted_ctr"]

        comparisons = {
            "ctr_vs_avg": {
                "our": our_ctr,
                "benchmark": benchmark["avg_ctr"],
                "diff_pct": (our_ctr / benchmark["avg_ctr"] - 1) * 100,
                "status": "above" if our_ctr > benchmark["avg_ctr"] else "below",
            },
            "ctr_vs_top": {
                "our": our_ctr,
                "benchmark": benchmark["top_ctr"],
                "diff_pct": (our_ctr / benchmark["top_ctr"] - 1) * 100,
                "status": "above" if our_ctr > benchmark["top_ctr"] else "below",
            },
            "saturation_vs_avg": {
                "our": our.saturation,
                "benchmark": benchmark["avg_saturation"],
                "diff_pct": (our.saturation / benchmark["avg_saturation"] - 1) * 100
                if benchmark["avg_saturation"] > 0 else 0,
                "status": "above" if our.saturation > benchmark["avg_saturation"] else "below",
            },
            "face_vs_avg": {
                "our": our.face_presence,
                "benchmark": benchmark["avg_face_presence"],
                "diff_pct": (our.face_presence / benchmark["avg_face_presence"] - 1) * 100
                if benchmark["avg_face_presence"] > 0 else 0,
                "status": "above" if our.face_presence > benchmark["avg_face_presence"] else "below",
            },
        }

        return comparisons

    def _generate_competitive_suggestions(self,
                                          strengths: List[str],
                                          weaknesses: List[str],
                                          benchmark: Dict) -> List[str]:
        suggestions = []

        if weaknesses:
            suggestions.append("🔧 需要改进的方面:")
            for w in weaknesses:
                suggestions.append(f"  • {w}")

        if strengths:
            suggestions.append("✅ 相对优势:")
            for s in strengths:
                suggestions.append(f"  • {s}")

        ctr_vs_avg = benchmark.get("ctr_vs_avg", {})
        if ctr_vs_avg.get("status") == "below":
            suggestions.append(
                f"⚠️ 预测CTR低于行业均值 {abs(ctr_vs_avg.get('diff_pct', 0)):.1f}%，"
                "建议重点关注颜色和人脸元素优化"
            )

        ctr_vs_top = benchmark.get("ctr_vs_top", {})
        if ctr_vs_top.get("status") == "above":
            suggestions.append(
                f"🌟 预测CTR已超过行业TOP水平 {ctr_vs_top.get('diff_pct', 0):.1f}%，封面设计处于领先位置"
            )
        else:
            gap = abs(ctr_vs_top.get("diff_pct", 0))
            suggestions.append(
                f"📈 距行业TOP水平还差 {gap:.1f}%，"
                "可通过A/B测试持续优化"
            )

        if self.our_cover and self.our_cover.features.face_presence < 0.3:
            suggestions.append("👤 建议添加人脸元素，行业数据显示含人脸的封面CTR平均提升20-30%")

        if self.our_cover and self.our_cover.features.saturation < 0.4:
            suggestions.append("🎨 建议提高色彩饱和度，鲜艳的颜色更容易吸引点击")

        return suggestions

    def generate_heatmap_comparison(self, image1: np.ndarray,
                                    image2: np.ndarray,
                                    name1: str = "Cover 1",
                                    name2: str = "Cover 2") -> np.ndarray:
        h, w = min(image1.shape[0], image2.shape[0]), min(image1.shape[1], image2.shape[1])

        img1_resized = cv2.resize(image1, (w, h))
        img2_resized = cv2.resize(image2, (w, h))

        gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_RGB2GRAY).astype(np.float32)
        gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_RGB2GRAY).astype(np.float32)

        gray1_norm = gray1 / 255.0
        gray2_norm = gray2 / 255.0

        attention1 = self._compute_attention_map(gray1_norm)
        attention2 = self._compute_attention_map(gray2_norm)

        diff_map = np.abs(attention1 - attention2)

        diff_colored = cv2.applyColorMap(
            (diff_map * 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        diff_colored = cv2.cvtColor(diff_colored, cv2.COLOR_BGR2RGB)

        border = np.ones((h, 3, 3), dtype=np.uint8) * 128
        combined = np.hstack([img1_resized, border, img2_resized, border, diff_colored])

        return combined

    def _compute_attention_map(self, gray_norm: np.ndarray) -> np.ndarray:
        saliency = np.zeros_like(gray_norm)

        laplacian = np.abs(cv2.Laplacian(
            (gray_norm * 255).astype(np.uint8), cv2.CV_64F
        ))
        laplacian_norm = laplacian / (laplacian.max() + 1e-10)

        h, w = gray_norm.shape
        center_x, center_y = w / 2, h / 2
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        center_bias = 1.0 - np.sqrt(
            ((x_coords - center_x) / w) ** 2 + ((y_coords - center_y) / h) ** 2
        ) / np.sqrt(0.5)

        saliency = laplacian_norm * 0.6 + center_bias * 0.4

        saliency = cv2.GaussianBlur(saliency, (21, 21), 0)
        if saliency.max() > 0:
            saliency = saliency / saliency.max()

        return saliency

    def get_feature_comparison_table(self) -> Dict:
        if not self.comparison_results:
            return {}

        return self.comparison_results.get("feature_comparison", {})

    def save_comparison(self, filepath: str):
        if not self.comparison_results:
            return

        data = {k: v for k, v in self.comparison_results.items()
                if k not in ("radar_data",)}

        radar = self.comparison_results.get("radar_data", {})
        data["radar_data"] = {
            "labels": radar.get("labels", []),
            "datasets": radar.get("datasets", []),
        }

        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
