import os
import sys
import pickle
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from lifelines import CoxPHFitter
    from lifelines.utils import concordance_index, k_fold_cross_validation
    from lifelines.statistics import multivariate_logrank_test
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False

import pandas as pd
import numpy as np

from common.logger import get_logger
from common.utils import load_config, get_risk_level

logger = get_logger("StratifiedCoxModel")


USER_LEVELS = ["new", "bronze", "silver", "gold", "platinum"]

USER_LEVEL_TO_SEGMENT = {
    "new": "new_users",
    "bronze": "low_value",
    "silver": "mid_value",
    "gold": "high_value",
    "platinum": "premium"
}

MIN_SAMPLES_PER_STRATUM = 10
MIN_EVENTS_PER_STRATUM = 3


class StratumModel:
    def __init__(self, stratum_name: str, model_config: Dict):
        self.stratum_name = stratum_name
        self.model: Optional[CoxPHFitter] = None
        self.feature_columns: List[str] = []
        self.is_trained = False
        self.train_samples: int = 0
        self.test_samples: int = 0
        self.event_count: int = 0
        self.c_index: float = 0.0
        self.c_index_train: float = 0.0
        self.prediction_window: int = model_config.get("prediction_window_days", 30)
        self.high_threshold: float = model_config.get("high_risk_threshold", 0.7)
        self.medium_threshold: float = model_config.get("medium_risk_threshold", 0.4)
        self.quantiles: List[float] = model_config.get("survival_time_quantiles", [0.25, 0.5, 0.75])
        self.config = model_config
        self.trained_at: Optional[str] = None

    def fit(self, train_df: pd.DataFrame, feature_cols: List[str]) -> bool:
        if len(train_df) < MIN_SAMPLES_PER_STRATUM:
            logger.warning(f"Stratum {self.stratum_name}: insufficient samples ({len(train_df)}), need {MIN_SAMPLES_PER_STRATUM}")
            return False

        event_count = train_df["event"].sum()
        if event_count < MIN_EVENTS_PER_STRATUM:
            logger.warning(f"Stratum {self.stratum_name}: insufficient events ({event_count}), need {MIN_EVENTS_PER_STRATUM}")
            return False

        train_cols = ["duration", "event"] + feature_cols
        self.feature_columns = feature_cols

        try:
            cph = CoxPHFitter(penalizer=0.1, l1_ratio=0.1, alpha=0.05)
            cph.fit(
                train_df[train_cols],
                duration_col="duration",
                event_col="event",
                show_progress=False
            )
        except Exception as e:
            logger.warning(f"Stratum {self.stratum_name} first fit failed: {e}. Trying reduced features.")
            reduced_cols = [c for c in feature_cols if train_df[c].std() > 1e-6]
            reduced_cols = [c for c in reduced_cols if not c.startswith("window_1d_")]
            if len(reduced_cols) < 2:
                reduced_cols = feature_cols[:3]
            train_cols = ["duration", "event"] + reduced_cols
            self.feature_columns = reduced_cols
            try:
                cph = CoxPHFitter(penalizer=1.0, l1_ratio=0.0, alpha=0.05)
                cph.fit(
                    train_df[train_cols],
                    duration_col="duration",
                    event_col="event",
                    show_progress=False
                )
            except Exception as e2:
                logger.error(f"Stratum {self.stratum_name} fit failed: {e2}")
                return False

        self.model = cph
        self.is_trained = True
        self.train_samples = len(train_df)
        self.event_count = int(event_count)
        self.trained_at = datetime.now().isoformat()

        try:
            pred = cph.predict_partial_hazard(train_df[self.feature_columns])
            self.c_index_train = concordance_index(
                train_df["duration"], pred, train_df["event"]
            )
        except Exception:
            self.c_index_train = 0.5

        self.c_index = self.c_index_train
        return True

    def evaluate(self, test_df: pd.DataFrame) -> float:
        if not self.is_trained or len(test_df) == 0:
            return 0.0
        try:
            pred = self.model.predict_partial_hazard(test_df[self.feature_columns])
            c_idx = concordance_index(
                test_df["duration"], pred, test_df["event"]
            )
            self.c_index = float(c_idx)
            self.test_samples = len(test_df)
            return self.c_index
        except Exception:
            return self.c_index

    def predict(self, features: Dict) -> Dict:
        if not self.is_trained:
            return self._predict_heuristic(features)

        try:
            feature_dict = {k: v for k, v in features.items() if k in self.feature_columns}
            for col in self.feature_columns:
                if col not in feature_dict:
                    feature_dict[col] = 0

            df = pd.DataFrame([feature_dict])[self.feature_columns]
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(0)

            hazard_ratio = float(self.model.predict_partial_hazard(df).iloc[0])
            survival_function = self.model.predict_survival_function(df)

            time_index = survival_function.index.values
            surv_probs = survival_function.values.flatten()

            prediction_window = min(self.prediction_window, max(time_index))
            idx = np.searchsorted(time_index, prediction_window)
            if idx >= len(surv_probs):
                idx = len(surv_probs) - 1
            churn_probability = 1 - float(surv_probs[idx])

            expected_days = self._calc_expected_survival(time_index, surv_probs)

            quantile_days = {}
            for q in self.quantiles:
                quantile_days[f"quantile_{int(q*100)}"] = self._find_quantile_time(time_index, surv_probs, q)

            risk_level = get_risk_level(churn_probability)

            return {
                "churn_probability": float(churn_probability),
                "hazard_ratio": float(hazard_ratio),
                "expected_days_to_churn": float(expected_days),
                "risk_level": risk_level,
                "risk_score": float(churn_probability * 1000),
                "survival_quantiles": quantile_days,
                "prediction_timestamp": datetime.now().isoformat(),
                "model_version": f"stratified_{self.stratum_name}_1.0.0",
                "stratum": self.stratum_name
            }
        except Exception as e:
            logger.warning(f"Stratum {self.stratum_name} predict error: {e}, using heuristic")
            return self._predict_heuristic(features)

    def _predict_heuristic(self, features: Dict) -> Dict:
        days_since_last = features.get("days_since_last_event", 
                                      features.get("window_30d_total_events", 0) / 30)
        event_frequency = features.get("event_frequency", 0)
        total_events = features.get("window_30d_total_events", 0)
        error_rate = features.get("window_30d_error_rate", 0)

        churn_score = 0.0
        if days_since_last > 14:
            churn_score += 0.35
        elif days_since_last > 7:
            churn_score += 0.2

        if event_frequency < 0.1:
            churn_score += 0.2
        if total_events < 5:
            churn_score += 0.15
        if error_rate > 0.1:
            churn_score += 0.1

        churn_probability = min(max(churn_score, 0.01), 0.99)
        expected_days = 7 if churn_probability >= 0.7 else (14 if churn_probability >= 0.4 else 30)

        return {
            "churn_probability": float(churn_probability),
            "hazard_ratio": float(churn_probability / 0.5),
            "expected_days_to_churn": float(expected_days),
            "risk_level": get_risk_level(churn_probability),
            "risk_score": float(churn_probability * 1000),
            "survival_quantiles": {
                "quantile_25": float(expected_days * 0.5),
                "quantile_50": float(expected_days),
                "quantile_75": float(expected_days * 1.5)
            },
            "prediction_timestamp": datetime.now().isoformat(),
            "model_version": f"heuristic_{self.stratum_name}_1.0.0",
            "stratum": self.stratum_name
        }

    def _calc_expected_survival(self, times: np.ndarray, surv_probs: np.ndarray) -> float:
        if len(times) < 2:
            return float(times[-1]) if len(times) > 0 else 30.0
        area = 0
        for i in range(1, len(times)):
            dt = times[i] - times[i-1]
            avg_surv = (surv_probs[i] + surv_probs[i-1]) / 2
            area += dt * avg_surv
        return float(area)

    def _find_quantile_time(self, times: np.ndarray, surv_probs: np.ndarray, quantile: float) -> float:
        target = 1 - quantile
        for i, prob in enumerate(surv_probs):
            if prob <= target:
                if i == 0:
                    return float(times[0])
                t0, t1 = times[i-1], times[i]
                p0, p1 = surv_probs[i-1], surv_probs[i]
                if p1 == p0:
                    return float(t1)
                fraction = (target - p0) / (p1 - p0)
                return float(t0 + fraction * (t1 - t0))
        return float(times[-1])

    def to_dict(self) -> Dict:
        return {
            "stratum_name": self.stratum_name,
            "is_trained": self.is_trained,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
            "event_count": self.event_count,
            "c_index": self.c_index,
            "c_index_train": self.c_index_train,
            "num_features": len(self.feature_columns),
            "trained_at": self.trained_at
        }


class StratifiedCoxModel:
    def __init__(self):
        self.config = load_config()
        self.model_config = self.config["model"]
        self.strata_models: Dict[str, StratumModel] = {}
        self.fallback_model: Optional[StratumModel] = None
        self.is_trained = False
        self.global_feature_columns: List[str] = []
        self.stratification_features: List[str] = [
            "user_level", "region", "channel"
        ]
        self.min_stratum_size: int = self.model_config.get("min_stratum_size", 10)

        if not LIFELINES_AVAILABLE:
            logger.warning("Lifelines not available. Stratified model will use heuristic predictions.")

    def _get_stratum_for_user(self, features: Dict) -> str:
        user_level = features.get("user_level", "new")
        if isinstance(user_level, str):
            segment = USER_LEVEL_TO_SEGMENT.get(user_level, "new_users")
        else:
            level_map = {0: "new", 1: "bronze", 2: "silver", 3: "gold", 4: "platinum"}
            level_str = level_map.get(int(user_level) if user_level is not None else 0, "new")
            segment = USER_LEVEL_TO_SEGMENT.get(level_str, "new_users")
        return segment

    def train(self, features: List[Dict], test_size: float = 0.2) -> Dict:
        if not LIFELINES_AVAILABLE:
            raise RuntimeError("Lifelines library is required for training")

        logger.info("Starting stratified Cox PH model training...")

        df = self._prepare_dataframe(features)

        strata_groups: Dict[str, List[int]] = defaultdict(list)
        for idx, row in df.iterrows():
            user_features = {col: row[col] for col in df.columns}
            stratum = self._get_stratum_for_user(user_features)
            strata_groups[stratum].append(idx)

        logger.info(f"Strata distribution: { {k: len(v) for k, v in strata_groups.items()} }")

        self.global_feature_columns = [
            col for col in df.columns
            if col not in ["user_id", "duration", "event"]
        ]

        self.strata_models = {}
        metrics = {
            "strata": {},
            "total_train": 0,
            "total_test": 0,
            "weighted_c_index": 0.0
        }

        all_test_results = []

        for stratum_name, indices in strata_groups.items():
            stratum_df = df.iloc[indices].copy()
            n = len(stratum_df)

            if n < self.min_stratum_size:
                logger.info(f"Stratum {stratum_name}: {n} samples < {self.min_stratum_size}, merging to fallback model")
                continue

            logger.info(f"Training stratum: {stratum_name} ({n} samples, {int(stratum_df['event'].sum())} events)")

            msk = np.random.rand(n) < (1 - test_size)
            train_df = stratum_df[msk].copy()
            test_df = stratum_df[~msk].copy()

            stratum_model = StratumModel(stratum_name, self.model_config)
            success = stratum_model.fit(train_df, self.global_feature_columns)

            if success:
                stratum_model.evaluate(test_df)
                self.strata_models[stratum_name] = stratum_model
                all_test_results.append((len(test_df), stratum_model.c_index))
                metrics["strata"][stratum_name] = stratum_model.to_dict()
                metrics["total_train"] += len(train_df)
                metrics["total_test"] += len(test_df)
            else:
                logger.warning(f"Stratum {stratum_name} training failed, will use fallback")

        pooled_indices = []
        for stratum_name, indices in strata_groups.items():
            if stratum_name not in self.strata_models:
                pooled_indices.extend(indices)

        if len(pooled_indices) >= self.min_stratum_size:
            pooled_df = df.iloc[pooled_indices].copy()
            logger.info(f"Training fallback pooled model: {len(pooled_df)} samples")

            msk = np.random.rand(len(pooled_df)) < (1 - test_size)
            train_df = pooled_df[msk].copy()
            test_df = pooled_df[~msk].copy()

            self.fallback_model = StratumModel("pooled", self.model_config)
            if self.fallback_model.fit(train_df, self.global_feature_columns):
                self.fallback_model.evaluate(test_df)
                all_test_results.append((len(test_df), self.fallback_model.c_index))
                metrics["fallback"] = self.fallback_model.to_dict()
                metrics["total_train"] += len(train_df)
                metrics["total_test"] += len(test_df)

        if all_test_results:
            total_weight = sum(w for w, _ in all_test_results)
            weighted_c_index = sum(w * c for w, c in all_test_results) / max(total_weight, 1)
            metrics["weighted_c_index"] = float(weighted_c_index)
            metrics["c_index"] = float(weighted_c_index)
        else:
            metrics["weighted_c_index"] = 0.0
            metrics["c_index"] = 0.0

        metrics["num_strata"] = len(self.strata_models)
        metrics["has_fallback"] = self.fallback_model is not None and self.fallback_model.is_trained
        metrics["total_samples"] = len(df)
        self.is_trained = len(self.strata_models) > 0 or (self.fallback_model is not None and self.fallback_model.is_trained)

        logger.info(f"Stratified training complete. {len(self.strata_models)} strata, "
                    f"weighted C-index: {metrics.get('c_index', 0):.4f}")
        return metrics

    def predict(self, features: Dict) -> Dict:
        if not self.is_trained:
            model = StratumModel("untrained", self.model_config)
            return model._predict_heuristic(features)

        stratum = self._get_stratum_for_user(features)

        if stratum in self.strata_models and self.strata_models[stratum].is_trained:
            return self.strata_models[stratum].predict(features)
        elif self.fallback_model and self.fallback_model.is_trained:
            result = self.fallback_model.predict(features)
            result["stratum"] = f"fallback_{stratum}"
            return result
        else:
            model = StratumModel("no_model", self.model_config)
            return model._predict_heuristic(features)

    def predict_batch(self, features_list: List[Dict]) -> List[Dict]:
        predictions = []
        for features in features_list:
            pred = self.predict(features)
            pred["user_id"] = features.get("user_id", "unknown")
            predictions.append(pred)
        return predictions

    def _prepare_dataframe(self, features: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(features)

        required_cols = ["user_id", "duration", "event"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
        df["duration"] = df["duration"].clip(lower=1)
        df["event"] = df["event"].astype(int)

        logger.info(f"Prepared dataframe: {len(df)} samples")
        return df

    def cross_validate(self, features: List[Dict], k: int = 5) -> Dict:
        if not LIFELINES_AVAILABLE:
            raise RuntimeError("Lifelines library is required for cross-validation")

        logger.info(f"Running {k}-fold cross-validation for stratified model...")
        df = self._prepare_dataframe(features)

        results = {"strata": {}, "mean_c_index": 0.0, "folds": k}

        for stratum_name, stratum_model in self.strata_models.items():
            stratum_indices = []
            for idx, row in df.iterrows():
                if self._get_stratum_for_user({c: row[c] for c in df.columns}) == stratum_name:
                    stratum_indices.append(idx)

            if len(stratum_indices) < k * MIN_SAMPLES_PER_STRATUM:
                results["strata"][stratum_name] = {"skipped": True, "reason": "insufficient_samples"}
                continue

            stratum_df = df.iloc[stratum_indices].copy()
            train_cols = ["duration", "event"] + stratum_model.feature_columns

            try:
                cv_results = k_fold_cross_validation(
                    CoxPHFitter(penalizer=0.1),
                    stratum_df[train_cols],
                    duration_col="duration",
                    event_col="event",
                    k=k,
                    scoring_method="concordance_index"
                )
                results["strata"][stratum_name] = {
                    "cv_scores": list(cv_results),
                    "mean_c_index": float(np.mean(cv_results)),
                    "std_c_index": float(np.std(cv_results))
                }
            except Exception as e:
                results["strata"][stratum_name] = {"error": str(e)}

        cv_values = []
        for s_data in results["strata"].values():
            if "mean_c_index" in s_data:
                cv_values.append(s_data["mean_c_index"])

        if cv_values:
            results["mean_c_index"] = float(np.mean(cv_values))

        return results

    def get_strata_summary(self) -> Dict:
        summary = {
            "total_strata": len(self.strata_models),
            "has_fallback": self.fallback_model is not None and self.fallback_model.is_trained,
            "strata": {}
        }

        for name, model in self.strata_models.items():
            summary["strata"][name] = {
                "is_trained": model.is_trained,
                "train_samples": model.train_samples,
                "event_count": model.event_count,
                "c_index": model.c_index,
                "num_features": len(model.feature_columns)
            }

        if self.fallback_model:
            summary["fallback"] = {
                "is_trained": self.fallback_model.is_trained,
                "train_samples": self.fallback_model.train_samples,
                "event_count": self.fallback_model.event_count,
                "c_index": self.fallback_model.c_index
            }

        return summary

    def save_model(self, model_path: Optional[str] = None):
        model_path = model_path or self.model_config.get("model_path", "./models/cox_model.pkl")
        base, ext = os.path.splitext(model_path)
        stratified_path = f"{base}_stratified{ext}"

        os.makedirs(os.path.dirname(stratified_path), exist_ok=True)

        model_data = {
            "strata_models": self.strata_models,
            "fallback_model": self.fallback_model,
            "global_feature_columns": self.global_feature_columns,
            "is_trained": self.is_trained,
            "config": self.model_config,
            "trained_at": datetime.now().isoformat()
        }

        with open(stratified_path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"Stratified model saved to {stratified_path}")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        model_path = model_path or self.model_config.get("model_path", "./models/cox_model.pkl")
        base, ext = os.path.splitext(model_path)
        stratified_path = f"{base}_stratified{ext}"

        if not os.path.exists(stratified_path):
            logger.warning(f"Stratified model file not found: {stratified_path}")
            return False

        try:
            with open(stratified_path, "rb") as f:
                model_data = pickle.load(f)

            self.strata_models = model_data.get("strata_models", {})
            self.fallback_model = model_data.get("fallback_model")
            self.global_feature_columns = model_data.get("global_feature_columns", [])
            self.is_trained = model_data.get("is_trained", False)

            logger.info(f"Stratified model loaded: {len(self.strata_models)} strata, "
                        f"trained: {self.is_trained}")
            return True
        except Exception as e:
            logger.error(f"Error loading stratified model: {e}")
            return False


class StratifiedModelTrainer:
    def __init__(self):
        self.config = load_config()
        self.model = StratifiedCoxModel()
        self.training_history: List[Dict] = []

    def train_and_save(self, features: List[Dict],
                       model_path: Optional[str] = None) -> Dict:
        logger.info("Starting stratified model training pipeline...")

        metrics = self.model.train(features, test_size=0.2)

        cv_results = self.model.cross_validate(features, k=5)
        metrics["cross_validation"] = cv_results

        self.model.save_model(model_path)

        self.training_history.append({
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "num_samples": len(features)
        })

        logger.info(f"Stratified training complete. Weighted C-index: {metrics.get('c_index', 0):.4f}")
        return metrics

    def load_features(self, features_path: str) -> List[Dict]:
        import csv
        features = []
        with open(features_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_row = {}
                for k, v in row.items():
                    try:
                        if "." in v:
                            processed_row[k] = float(v)
                        else:
                            processed_row[k] = int(v)
                    except (ValueError, TypeError):
                        processed_row[k] = v
                features.append(processed_row)
        logger.info(f"Loaded {len(features)} feature rows from {features_path}")
        return features


def main():
    trainer = StratifiedModelTrainer()

    print("=" * 60)
    print("STRATIFIED COX SURVIVAL MODEL - Training and Prediction")
    print("=" * 60)

    from spark.feature_engineering import FeatureEngineering
    fe = FeatureEngineering(use_spark=False)

    print("\nGenerating synthetic training data...")
    users, events = fe.generate_synthetic_data(num_users=200, avg_events_per_user=20, churn_ratio=0.3)

    features = fe.extract_features_pandas(users, events)
    processed_features, metadata = fe.preprocess_features_pandas(features)

    print(f"\nTraining stratified model on {len(processed_features)} samples...")
    metrics = trainer.train_and_save(processed_features)

    print("\n" + "=" * 60)
    print("Training Results:")
    print(f"  Total Strata: {metrics.get('num_strata', 0)}")
    print(f"  Weighted C-index: {metrics.get('c_index', 0):.4f}")
    print(f"  Total Train: {metrics.get('total_train', 0)}")
    print(f"  Total Test: {metrics.get('total_test', 0)}")
    print(f"  Has Fallback: {metrics.get('has_fallback', False)}")

    print("\nPer-Stratum Details:")
    for name, data in metrics.get("strata", {}).items():
        print(f"  {name:20s}: samples={data.get('train_samples', 0):4d}, "
              f"events={data.get('event_count', 0):3d}, "
              f"C-index={data.get('c_index', 0):.4f}, "
              f"trained={data.get('is_trained', False)}")

    if "cross_validation" in metrics:
        cv = metrics["cross_validation"]
        print(f"\nCross-validation (k={cv.get('folds', 5)}):")
        print(f"  Mean C-index: {cv.get('mean_c_index', 0):.4f}")
        for name, cv_data in cv.get("strata", {}).items():
            if "mean_c_index" in cv_data:
                print(f"    {name:20s}: CV mean={cv_data['mean_c_index']:.4f} ± {cv_data.get('std_c_index', 0):.4f}")

    print("\n" + "=" * 60)
    print("Making predictions for sample users...")
    sample_users = [u for u in users if u.get("churned", False)][:5]
    for user in sample_users:
        user_features = {}
        for f in processed_features:
            if f["user_id"] == user["user_id"]:
                user_features = f
                break

        if user_features:
            pred = trainer.model.predict(user_features)
            print(f"\n  User: {user['user_id']} (level={user['user_level']}, churned={user['churned']})")
            print(f"    Stratum: {pred.get('stratum', 'unknown')}")
            print(f"    Churn Probability: {pred['churn_probability']:.2%}")
            print(f"    Expected Days to Churn: {pred['expected_days_to_churn']:.1f}")
            print(f"    Risk Level: {pred['risk_level'].upper()}")
            print(f"    Model: {pred.get('model_version', 'unknown')}")

    fe.close()


if __name__ == "__main__":
    main()