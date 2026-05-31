import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json
import os
from datetime import datetime


@dataclass
class CTRFeature:
    color_vibrancy: float = 0.0
    color_harmony: float = 0.0
    contrast_score: float = 0.0
    composition_score: float = 0.0
    face_presence: float = 0.0
    face_expression: float = 0.0
    text_area_ratio: float = 0.0
    brightness: float = 0.0
    saturation: float = 0.0
    sharpness: float = 0.0
    symmetry: float = 0.0
    visual_balance: float = 0.0
    dominant_hue: float = 0.0
    edge_density: float = 0.0
    skin_ratio: float = 0.0


class CTRPredictor:
    def __init__(self):
        self.feature_weights = {
            "color_vibrancy": 0.12,
            "color_harmony": 0.08,
            "contrast_score": 0.10,
            "composition_score": 0.10,
            "face_presence": 0.15,
            "face_expression": 0.08,
            "text_area_ratio": 0.07,
            "brightness": 0.05,
            "saturation": 0.06,
            "sharpness": 0.05,
            "symmetry": 0.04,
            "visual_balance": 0.04,
            "dominant_hue": 0.02,
            "edge_density": 0.02,
            "skin_ratio": 0.02,
        }

        self.optimal_ranges = {
            "color_vibrancy": (0.5, 0.8),
            "color_harmony": (0.4, 0.7),
            "contrast_score": (0.5, 0.8),
            "composition_score": (0.6, 0.9),
            "face_presence": (0.3, 1.0),
            "face_expression": (0.4, 0.9),
            "text_area_ratio": (0.05, 0.25),
            "brightness": (0.4, 0.7),
            "saturation": (0.4, 0.8),
            "sharpness": (0.5, 1.0),
            "symmetry": (0.3, 0.7),
            "visual_balance": (0.5, 0.9),
            "dominant_hue": (0.0, 1.0),
            "edge_density": (0.1, 0.5),
            "skin_ratio": (0.05, 0.4),
        }

        self.hue_ctr_map = {
            "warm": 0.065,
            "cool": 0.055,
            "neutral": 0.058,
            "vibrant": 0.070,
            "muted": 0.050,
        }

        self.style_ctr_boost = {
            "tech": 1.15,
            "cute": 1.20,
            "warm": 1.10,
            "calm": 0.95,
            "professional": 1.05,
            "artistic": 1.08,
        }

        self.historical_data = []
        self.model_fitted = False
        self.baseline_ctr = 0.05

    def extract_features(self, frame: np.ndarray,
                         face_analysis: Optional[Dict] = None,
                         quality_analysis: Optional[Dict] = None,
                         composition_analysis: Optional[Dict] = None,
                         has_text_overlay: bool = False,
                         text_area_ratio: float = 0.0) -> CTRFeature:
        h, w = frame.shape[:2]
        feature = CTRFeature()

        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        feature.saturation = float(np.mean(hsv[:, :, 1]) / 255.0)
        feature.brightness = float(np.mean(hsv[:, :, 2]) / 255.0)

        hist_h = np.histogram(hsv[:, :, 0].flatten(), bins=12, range=(0, 180))[0]
        hist_h = hist_h / hist_h.sum() if hist_h.sum() > 0 else hist_h
        feature.dominant_hue = float(np.argmax(hist_h) / 12.0)

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        feature.sharpness = float(min(1.0, cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0))

        edges = cv2.Canny(gray, 50, 150)
        feature.edge_density = float(np.count_nonzero(edges) / edges.size)

        lower_skin = np.array([0, 48, 80], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        feature.skin_ratio = float(np.count_nonzero(skin_mask) / skin_mask.size)

        if face_analysis:
            feature.face_presence = min(1.0, face_analysis.get("num_faces", 0) / 2.0)
            expr_scores = face_analysis.get("expression_scores", {})
            if expr_scores:
                positive = expr_scores.get("happy", 0) + expr_scores.get("surprised", 0)
                feature.face_expression = min(1.0, positive / 2.0)
            else:
                main_expr = face_analysis.get("main_expression", "neutral")
                feature.face_expression = 0.6 if main_expr in ("happy", "surprised") else 0.3

        if quality_analysis:
            color_info = quality_analysis.get("color_analysis", {})
            feature.color_vibrancy = color_info.get("vibrancy_score", 0.5)
            feature.color_harmony = color_info.get("harmony_score", 0.5)
            feature.contrast_score = color_info.get("contrast_score", 0.5)

        if composition_analysis:
            feature.composition_score = composition_analysis.get("composition_score", 0.5)
            feature.symmetry = composition_analysis.get("symmetry_score", 0.5)
            feature.visual_balance = composition_analysis.get("visual_balance_score", 0.5)

        if has_text_overlay:
            feature.text_area_ratio = text_area_ratio
        else:
            feature.text_area_ratio = 0.0

        return feature

    def _calculate_feature_score(self, feature_name: str, value: float) -> float:
        low, high = self.optimal_ranges.get(feature_name, (0.0, 1.0))
        mid = (low + high) / 2.0
        half_range = (high - low) / 2.0

        if half_range == 0:
            return 0.5

        distance = abs(value - mid) / half_range
        score = max(0.0, 1.0 - distance * 0.5)
        return score

    def predict_ctr(self, feature: CTRFeature,
                    video_style: Optional[str] = None,
                    category: Optional[str] = None) -> Dict:
        feature_scores = {}
        for fname, weight in self.feature_weights.items():
            fval = getattr(feature, fname, 0.0)
            fscore = self._calculate_feature_score(fname, fval)
            feature_scores[fname] = {
                "value": fval,
                "score": fscore,
                "weight": weight,
                "contribution": weight * fscore,
            }

        weighted_score = sum(v["contribution"] for v in feature_scores.values())

        base_ctr = self.baseline_ctr
        ctr_multiplier = 0.5 + weighted_score * 1.5
        predicted_ctr = base_ctr * ctr_multiplier

        if video_style and video_style in self.style_ctr_boost:
            predicted_ctr *= self.style_ctr_boost[video_style]

        if category:
            category_multipliers = {
                "entertainment": 1.15,
                "education": 0.95,
                "gaming": 1.10,
                "music": 1.05,
                "tech": 1.00,
                "lifestyle": 1.08,
                "food": 1.12,
                "travel": 1.05,
            }
            predicted_ctr *= category_multipliers.get(category, 1.0)

        predicted_ctr = max(0.01, min(0.20, predicted_ctr))

        confidence = self._calculate_confidence(feature)

        top_factors = sorted(
            feature_scores.items(),
            key=lambda x: x[1]["contribution"],
            reverse=True,
        )[:5]

        weak_factors = sorted(
            feature_scores.items(),
            key=lambda x: x[1]["contribution"],
        )[:3]

        return {
            "predicted_ctr": predicted_ctr,
            "ctr_percentage": f"{predicted_ctr * 100:.2f}%",
            "confidence": confidence,
            "weighted_score": weighted_score,
            "feature_scores": feature_scores,
            "top_factors": [(k, v) for k, v in top_factors],
            "weak_factors": [(k, v) for k, v in weak_factors],
            "video_style": video_style,
            "category": category,
        }

    def _calculate_confidence(self, feature: CTRFeature) -> float:
        non_zero = sum(1 for fname in self.feature_weights if getattr(feature, fname, 0.0) > 0)
        coverage = non_zero / len(self.feature_weights)
        feature_values = [getattr(feature, fname) for fname in self.feature_weights]
        variance = float(np.var(feature_values)) if feature_values else 0.0
        confidence = coverage * 0.6 + min(1.0, variance * 4) * 0.4
        return min(1.0, confidence)

    def predict_ctr_for_frame(self, frame: np.ndarray,
                              face_analysis: Optional[Dict] = None,
                              quality_analysis: Optional[Dict] = None,
                              composition_analysis: Optional[Dict] = None,
                              video_style: Optional[str] = None,
                              category: Optional[str] = None,
                              has_text_overlay: bool = False,
                              text_area_ratio: float = 0.0) -> Dict:
        feature = self.extract_features(
            frame, face_analysis, quality_analysis, composition_analysis,
            has_text_overlay, text_area_ratio
        )
        return self.predict_ctr(feature, video_style, category)

    def rank_frames_by_ctr(self, frames_with_analysis: List[Tuple],
                           video_style: Optional[str] = None,
                           category: Optional[str] = None) -> List[Dict]:
        results = []
        for item in frames_with_analysis:
            if len(item) >= 5:
                frame_idx, frame, face_analysis, quality_analysis, comp_analysis = item[:5]
            else:
                frame_idx, frame = item[0], item[1]
                face_analysis = item[2] if len(item) > 2 else None
                quality_analysis = item[3] if len(item) > 3 else None
                comp_analysis = item[4] if len(item) > 4 else None

            prediction = self.predict_ctr_for_frame(
                frame, face_analysis, quality_analysis, comp_analysis,
                video_style, category
            )
            results.append({
                "frame_index": frame_idx,
                "predicted_ctr": prediction["predicted_ctr"],
                "ctr_percentage": prediction["ctr_percentage"],
                "confidence": prediction["confidence"],
                "top_factors": prediction["top_factors"],
                "weak_factors": prediction["weak_factors"],
            })

        results.sort(key=lambda x: x["predicted_ctr"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1

        return results

    def generate_improvement_suggestions(self, prediction: Dict) -> List[str]:
        suggestions = []
        weak = prediction.get("weak_factors", [])

        factor_descriptions = {
            "color_vibrancy": "增加画面色彩鲜艳度，使用更饱和的颜色",
            "color_harmony": "优化颜色搭配，使用互补色或邻近色方案",
            "contrast_score": "增强明暗对比，突出主体内容",
            "composition_score": "改进构图，遵循三分法则，突出视觉焦点",
            "face_presence": "添加人脸元素，人脸能显著提升点击率",
            "face_expression": "使用积极表情（开心、惊讶），更容易吸引点击",
            "text_area_ratio": "添加标题文字，但不要超过画面25%",
            "brightness": "调整画面亮度至适中水平",
            "saturation": "适当提高色彩饱和度",
            "sharpness": "确保画面清晰，避免模糊",
            "symmetry": "适当利用对称构图增加视觉舒适度",
            "visual_balance": "保持画面左右视觉平衡",
            "dominant_hue": "考虑使用暖色调，暖色调通常有更高点击率",
            "edge_density": "画面内容不宜过于复杂，保持重点突出",
            "skin_ratio": "适当增加人物肤色的画面占比",
        }

        for fname, finfo in weak:
            desc = factor_descriptions.get(fname, f"优化{fname}")
            suggestions.append(f"• {desc}（当前值: {finfo['value']:.2f}）")

        return suggestions

    def add_historical_data(self, frame: np.ndarray, actual_ctr: float,
                            face_analysis: Optional[Dict] = None,
                            quality_analysis: Optional[Dict] = None,
                            composition_analysis: Optional[Dict] = None,
                            video_style: Optional[str] = None,
                            category: Optional[str] = None):
        feature = self.extract_features(frame, face_analysis, quality_analysis, composition_analysis)
        self.historical_data.append({
            "feature": feature,
            "actual_ctr": actual_ctr,
            "video_style": video_style,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        })

        if len(self.historical_data) >= 10:
            self._recalibrate()

    def _recalibrate(self):
        if len(self.historical_data) < 10:
            return

        actual_ctrs = [d["actual_ctr"] for d in self.historical_data]
        self.baseline_ctr = float(np.mean(actual_ctrs))

        feature_contributions = {}
        for fname in self.feature_weights:
            values = []
            ctrs = []
            for d in self.historical_data:
                fval = getattr(d["feature"], fname, 0.0)
                values.append(fval)
                ctrs.append(d["actual_ctr"])

            if len(values) >= 5:
                correlation = abs(float(np.corrcoef(values, ctrs)[0, 1]))
                if not np.isnan(correlation):
                    feature_contributions[fname] = correlation

        if feature_contributions:
            total = sum(feature_contributions.values())
            if total > 0:
                for fname, contrib in feature_contributions.items():
                    new_weight = contrib / total
                    self.feature_weights[fname] = (
                        self.feature_weights[fname] * 0.7 + new_weight * 0.3
                    )

        total_w = sum(self.feature_weights.values())
        if total_w > 0:
            for fname in self.feature_weights:
                self.feature_weights[fname] /= total_w

        self.model_fitted = True

    def save_model(self, filepath: str):
        data = {
            "feature_weights": self.feature_weights,
            "baseline_ctr": self.baseline_ctr,
            "model_fitted": self.model_fitted,
            "num_historical": len(self.historical_data),
            "saved_at": datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_model(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.feature_weights = data.get("feature_weights", self.feature_weights)
        self.baseline_ctr = data.get("baseline_ctr", self.baseline_ctr)
        self.model_fitted = data.get("model_fitted", False)
