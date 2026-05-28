import os
import numpy as np
from typing import List, Tuple, Optional, Dict
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

from models.data_models import (
    FollowerRiskLevel,
    DetectionResult,
    FeatureVector,
    AnalysisSummary,
)
from utils.helpers import parse_utc_datetime, get_utc_now
from engine.features import (
    extract_features,
    feature_vector_to_array,
    identify_risk_factors,
    FEATURE_NAMES,
)
from engine.advanced_analysis import BoughtFollowerDetector, InteractionQualityAnalyzer
from engine.network import NetworkAnalyzer

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models")


class FakeFollowerDetector:
    def __init__(self):
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            contamination=0.3,
            random_state=42,
            n_estimators=200,
            max_features=0.8,
        )
        self.random_forest: Optional[RandomForestClassifier] = None
        self._is_trained = False
        self._use_supervised = False
        self.bought_detector = BoughtFollowerDetector()
        self.interaction_analyzer = InteractionQualityAnalyzer()
        self._cached_bought_analysis: Optional[dict] = None
        self._cached_interaction_analysis: Optional[dict] = None
        os.makedirs(MODEL_DIR, exist_ok=True)

    def train_unsupervised(self, feature_arrays: np.ndarray):
        X_scaled = self.scaler.fit_transform(feature_arrays)
        self.isolation_forest.fit(X_scaled)
        self._is_trained = True
        self._use_supervised = False

    def train_supervised(self, feature_arrays: np.ndarray, labels: np.ndarray):
        X_scaled = self.scaler.fit_transform(feature_arrays)
        self.random_forest = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            random_state=42,
            class_weight="balanced",
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, labels, test_size=0.2, random_state=42, stratify=labels
        )
        self.random_forest.fit(X_train, y_train)
        self._is_trained = True
        self._use_supervised = True

    def predict_single(self, follower: dict) -> DetectionResult:
        fv = extract_features(follower)
        feature_array = feature_vector_to_array(fv).reshape(1, -1)

        if not self._is_trained:
            fake_prob = self._heuristic_score(follower)
        elif self._use_supervised and self.random_forest is not None:
            X_scaled = self.scaler.transform(feature_array)
            prob = self.random_forest.predict_proba(X_scaled)[0]
            fake_prob = prob[1] if len(prob) > 1 else prob[0]
        else:
            X_scaled = self.scaler.transform(feature_array)
            prediction = self.isolation_forest.predict(X_scaled)[0]
            score = self.isolation_forest.score_samples(X_scaled)[0]
            fake_prob = 1.0 - (score + 0.5)
            fake_prob = np.clip(fake_prob, 0, 1)
            if prediction == 1:
                fake_prob = min(fake_prob, 0.4)

        risk_factors = identify_risk_factors(follower)
        fake_prob = float(np.clip(fake_prob, 0, 1))
        risk_level = self._probability_to_risk_level(fake_prob)
        recommendation = self._generate_recommendation(risk_level, risk_factors)

        return DetectionResult(
            user_id=follower.get("user_id", ""),
            username=follower.get("username", ""),
            risk_level=risk_level,
            fake_probability=fake_prob,
            feature_vector=fv,
            risk_factors=risk_factors,
            recommendation=recommendation,
        )

    def predict_batch(self, followers: List[dict]) -> List[DetectionResult]:
        return [self.predict_single(f) for f in followers]

    def analyze(self, followers: List[dict]) -> Tuple[List[DetectionResult], AnalysisSummary]:
        results = self.predict_batch(followers)

        genuine = sum(1 for r in results if r.risk_level == FollowerRiskLevel.GENUINE)
        suspicious = sum(1 for r in results if r.risk_level == FollowerRiskLevel.SUSPICIOUS)
        likely_fake = sum(1 for r in results if r.risk_level == FollowerRiskLevel.LIKELY_FAKE)
        fake = sum(1 for r in results if r.risk_level == FollowerRiskLevel.FAKE)

        total = len(results)
        fake_ratio = (likely_fake + fake) / max(total, 1)
        avg_fake_prob = np.mean([r.fake_probability for r in results])

        risk_factor_counts = {}
        for r in results:
            for rf in r.risk_factors:
                risk_factor_counts[rf] = risk_factor_counts.get(rf, 0) + 1

        summary = AnalysisSummary(
            total_followers=total,
            genuine_count=genuine,
            suspicious_count=suspicious,
            likely_fake_count=likely_fake,
            fake_count=fake,
            fake_ratio=fake_ratio,
            avg_fake_probability=float(avg_fake_prob),
            risk_distribution={
                "genuine": genuine,
                "suspicious": suspicious,
                "likely_fake": likely_fake,
                "fake": fake,
            },
            top_risk_factors=dict(
                sorted(risk_factor_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        )

        return results, summary

    def _heuristic_score(self, follower: dict) -> float:
        score = 0.0

        now = get_utc_now()
        reg_date_str = follower.get("registration_date")
        reg_date = parse_utc_datetime(reg_date_str)
        if reg_date:
            age_days = (now - reg_date).days
            if age_days < 7:
                score += 0.25
            elif age_days < 30:
                score += 0.15
            elif age_days < 90:
                score += 0.08

        followers_count = follower.get("followers_count", 0)
        following_count = follower.get("following_count", 0)
        if following_count > 0:
            ratio = followers_count / following_count
            if ratio < 0.05:
                score += 0.2
            elif ratio < 0.1:
                score += 0.12

        engagement_rate = follower.get("engagement_rate", 0.0)
        if engagement_rate < 0.005:
            score += 0.2
        elif engagement_rate < 0.01:
            score += 0.12

        if not follower.get("has_profile_image", True):
            score += 0.1

        bio_length = follower.get("bio_length", len(follower.get("bio", "")))
        if bio_length < 3:
            score += 0.08

        repost_ratio = follower.get("repost_ratio", 0.0)
        if repost_ratio > 0.8:
            score += 0.1

        duplicate_content_ratio = follower.get("duplicate_content_ratio", 0.0)
        if duplicate_content_ratio > 0.5:
            score += 0.1

        content_diversity = follower.get("content_diversity", 0.0)
        if content_diversity < 0.2:
            score += 0.08

        if follower.get("posts_count", 0) < 5 and followers_count < 10 and following_count > 100:
            score += 0.15

        return min(score, 1.0)

    @staticmethod
    def _probability_to_risk_level(prob: float) -> FollowerRiskLevel:
        if prob < 0.25:
            return FollowerRiskLevel.GENUINE
        elif prob < 0.5:
            return FollowerRiskLevel.SUSPICIOUS
        elif prob < 0.75:
            return FollowerRiskLevel.LIKELY_FAKE
        else:
            return FollowerRiskLevel.FAKE

    @staticmethod
    def _generate_recommendation(risk_level: FollowerRiskLevel, risk_factors: list) -> str:
        if risk_level == FollowerRiskLevel.GENUINE:
            return "该账号标注为「真实用户」，无需人工审核。"
        elif risk_level == FollowerRiskLevel.SUSPICIOUS:
            return f"该账号标注为「可疑」（{', '.join(risk_factors[:2])}），建议人工观察后再决定。"
        elif risk_level == FollowerRiskLevel.LIKELY_FAKE:
            return f"该账号标注为「疑似虚假」（{', '.join(risk_factors[:2])}），建议人工审核后处理。"
        else:
            return f"该账号标注为「高风险」（{', '.join(risk_factors[:2])}），强烈建议人工审核后处理。"

    def save_model(self, prefix: str = "fake_detector"):
        if not self._is_trained:
            return
        joblib.dump(self.scaler, os.path.join(MODEL_DIR, f"{prefix}_scaler.pkl"))
        if self._use_supervised and self.random_forest is not None:
            joblib.dump(self.random_forest, os.path.join(MODEL_DIR, f"{prefix}_rf.pkl"))
        else:
            joblib.dump(self.isolation_forest, os.path.join(MODEL_DIR, f"{prefix}_if.pkl"))

    def load_model(self, prefix: str = "fake_detector", supervised: bool = False):
        scaler_path = os.path.join(MODEL_DIR, f"{prefix}_scaler.pkl")
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
        if supervised:
            model_path = os.path.join(MODEL_DIR, f"{prefix}_rf.pkl")
            if os.path.exists(model_path):
                self.random_forest = joblib.load(model_path)
                self._is_trained = True
                self._use_supervised = True
        else:
            model_path = os.path.join(MODEL_DIR, f"{prefix}_if.pkl")
            if os.path.exists(model_path):
                self.isolation_forest = joblib.load(model_path)
                self._is_trained = True
                self._use_supervised = False

    def analyze_bought_followers(self, followers: List[dict]) -> dict:
        analysis = self.bought_detector.analyze_registration_pattern(followers)
        score = self.bought_detector.get_bought_follower_score(followers)
        analysis["bought_score"] = score
        self._cached_bought_analysis = analysis
        return analysis

    def analyze_interaction_quality(self, followers: List[dict]) -> dict:
        analysis = self.interaction_analyzer.analyze_interaction_patterns(followers)
        self._cached_interaction_analysis = analysis
        return analysis

    def get_follower_quality_score(self, user_id: str) -> Optional[dict]:
        if self._cached_interaction_analysis:
            return self._cached_interaction_analysis["follower_scores"].get(user_id)
        return None

    def enhance_risk_with_advanced_analysis(
        self,
        results: List[DetectionResult],
        followers: List[dict],
        bought_analysis: Optional[dict] = None,
        interaction_analysis: Optional[dict] = None,
    ) -> List[DetectionResult]:
        if bought_analysis is None:
            bought_analysis = self._cached_bought_analysis
        if interaction_analysis is None:
            interaction_analysis = self._cached_interaction_analysis

        burst_user_ids = set()
        if bought_analysis and bought_analysis.get("bursts"):
            for burst in bought_analysis["bursts"]:
                burst_user_ids.update(burst.get("user_ids", []))

        enhanced_results = []
        for result, follower in zip(results, followers):
            user_id = result.user_id
            additional_factors = []
            score_adjustment = 0.0

            if user_id in burst_user_ids:
                additional_factors.append("burst_registration")
                score_adjustment += 0.15

            if interaction_analysis:
                quality = interaction_analysis["follower_scores"].get(user_id, {})
                q_score = quality.get("quality_score", 0.5)
                if q_score < 0.3:
                    additional_factors.append("low_interaction_quality")
                    score_adjustment += 0.10
                    for flag in quality.get("flags", []):
                        if flag not in result.risk_factors:
                            additional_factors.append(f"quality_{flag}")
                elif q_score > 0.7:
                    score_adjustment -= 0.10

            new_prob = float(np.clip(result.fake_probability + score_adjustment, 0, 1))
            new_risk_level = self._probability_to_risk_level(new_prob)
            all_risk_factors = result.risk_factors + additional_factors

            enhanced_results.append(DetectionResult(
                user_id=result.user_id,
                username=result.username,
                risk_level=new_risk_level,
                fake_probability=new_prob,
                feature_vector=result.feature_vector,
                risk_factors=list(set(all_risk_factors)),
                recommendation=self._generate_recommendation(new_risk_level, all_risk_factors),
            ))

        return enhanced_results