import os
import sys
import pickle
from typing import Dict, List, Optional, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from lifelines import CoxPHFitter
    from lifelines.utils import concordance_index, k_fold_cross_validation
    from lifelines.statistics import logrank_test
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    print("Warning: Lifelines not available. Install with: pip install lifelines")

import pandas as pd
import numpy as np

from common.logger import get_logger
from common.utils import (
    load_config,
    get_risk_level,
    quantile,
    safe_divide,
    to_json_safe
)

logger = get_logger("CoxModel")


class CoxSurvivalModel:
    def __init__(self):
        self.config = load_config()
        self.model_config = self.config["model"]
        
        self.model_path = self.model_config["model_path"]
        self.scaler_path = self.model_config["scaler_path"]
        self.prediction_window = self.model_config["prediction_window_days"]
        self.high_threshold = self.model_config["high_risk_threshold"]
        self.medium_threshold = self.model_config["medium_risk_threshold"]
        self.quantiles = self.model_config["survival_time_quantiles"]
        
        self.model: Optional[CoxPHFitter] = None
        self.feature_columns: List[str] = []
        self.scaler = None
        self.is_trained = False
        
        if not LIFELINES_AVAILABLE:
            logger.warning("Lifelines not installed. Model functionality will be limited.")
    
    def _prepare_dataframe(self, features: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(features)
        
        required_cols = ["user_id", "duration", "event"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        self.feature_columns = [
            col for col in df.columns 
            if col not in ["user_id", "duration", "event"]
        ]
        
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
        
        df["duration"] = df["duration"].clip(lower=1)
        df["event"] = df["event"].astype(int)
        
        logger.info(f"Prepared dataframe: {len(df)} samples, {len(self.feature_columns)} features")
        return df
    
    def train(self, features: List[Dict], test_size: float = 0.2) -> Dict:
        if not LIFELINES_AVAILABLE:
            raise RuntimeError("Lifelines library is required for training")
        
        logger.info("Starting Cox PH model training...")
        
        df = self._prepare_dataframe(features)
        
        if test_size > 0:
            msk = np.random.rand(len(df)) < (1 - test_size)
            train_df = df[msk].copy()
            test_df = df[~msk].copy()
            logger.info(f"Train: {len(train_df)}, Test: {len(test_df)}")
        else:
            train_df = df.copy()
            test_df = None
        
        train_cols = ["duration", "event"] + self.feature_columns
        cph = CoxPHFitter(
            penalizer=0.1,
            l1_ratio=0.1,
            alpha=0.05
        )
        
        try:
            cph.fit(
                train_df[train_cols],
                duration_col="duration",
                event_col="event",
                show_progress=False
            )
        except Exception as e:
            logger.warning(f"First fit attempt failed: {e}. Trying with reduced features.")
            feature_cols = [c for c in self.feature_columns if train_df[c].std() > 1e-6]
            feature_cols = [c for c in feature_cols if not c.startswith("window_1d_") 
                           and not c.startswith("window_7d_")]
            if len(feature_cols) < 2:
                feature_cols = [c for c in self.feature_columns if train_df[c].std() > 1e-6][:5]
            if len(feature_cols) < 1:
                feature_cols = self.feature_columns[:5]
            train_cols = ["duration", "event"] + feature_cols
            self.feature_columns = feature_cols
            cph2 = CoxPHFitter(
                penalizer=1.0,
                l1_ratio=0.0,
                alpha=0.05
            )
            cph2.fit(
                train_df[train_cols],
                duration_col="duration",
                event_col="event",
                show_progress=False
            )
            cph = cph2
        
        self.model = cph
        self.is_trained = True
        
        metrics = self._calculate_metrics(train_df, test_df)
        
        logger.info(f"Model training complete. C-index: {metrics['c_index']:.4f}")
        
        return metrics
    
    def _calculate_metrics(self, train_df: pd.DataFrame, 
                          test_df: Optional[pd.DataFrame]) -> Dict:
        metrics = {}
        
        train_cols = ["duration", "event"] + self.feature_columns
        
        train_pred = self.model.predict_partial_hazard(train_df[self.feature_columns])
        metrics["c_index_train"] = concordance_index(
            train_df["duration"],
            train_pred,
            train_df["event"]
        )
        
        if test_df is not None and len(test_df) > 0:
            test_pred = self.model.predict_partial_hazard(test_df[self.feature_columns])
            metrics["c_index_test"] = concordance_index(
                test_df["duration"],
                test_pred,
                test_df["event"]
            )
            
            churned_train = train_df[train_df["event"] == 1]["duration"]
            not_churned_train = train_df[train_df["event"] == 0]["duration"]
            if len(churned_train) > 0 and len(not_churned_train) > 0:
                lr_result = logrank_test(churned_train, not_churned_train)
                metrics["logrank_p_value"] = lr_result.p_value
        
        metrics["c_index"] = metrics.get("c_index_test", metrics["c_index_train"])
        
        metrics["feature_importance"] = self.get_feature_importance(top_n=20)
        metrics["num_features"] = len(self.feature_columns)
        metrics["num_samples_train"] = len(train_df)
        metrics["num_samples_test"] = len(test_df) if test_df is not None else 0
        metrics["num_events"] = int(train_df["event"].sum())
        
        return metrics
    
    def get_feature_importance(self, top_n: Optional[int] = None) -> Dict[str, float]:
        if not self.is_trained:
            return {}
        
        summary = self.model.summary
        importance = {}
        
        for feature in self.feature_columns:
            if feature in summary.index:
                coef = summary.loc[feature, "coef"]
                hr = summary.loc[feature, "exp(coef)"]
                importance[feature] = {
                    "coefficient": float(coef),
                    "hazard_ratio": float(hr),
                    "p_value": float(summary.loc[feature, "p"]),
                    "importance": float(abs(coef))
                }
        
        sorted_features = sorted(
            importance.items(), 
            key=lambda x: x[1]["importance"], 
            reverse=True
        )
        
        if top_n:
            sorted_features = sorted_features[:top_n]
        
        return {k: v for k, v in sorted_features}
    
    def predict(self, features: Dict) -> Dict:
        if not self.is_trained:
            logger.warning("Model not trained. Using heuristic predictions.")
            return self._predict_heuristic(features)
        
        try:
            feature_dict = {k: v for k, v in features.items() 
                          if k in self.feature_columns}
            
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
            idx_30d = np.searchsorted(time_index, prediction_window)
            if idx_30d >= len(surv_probs):
                idx_30d = len(surv_probs) - 1
            churn_probability = 1 - float(surv_probs[idx_30d])
            
            expected_days = self._calculate_expected_survival_time(
                time_index, surv_probs
            )
            
            quantile_days = {}
            for q in self.quantiles:
                q_days = self._find_quantile_time(time_index, surv_probs, q)
                quantile_days[f"quantile_{int(q*100)}"] = float(q_days)
            
            risk_level = get_risk_level(churn_probability, self.config)
            
            result = {
                "churn_probability": float(churn_probability),
                "hazard_ratio": float(hazard_ratio),
                "expected_days_to_churn": float(expected_days),
                "risk_level": risk_level,
                "risk_score": float(churn_probability * 1000),
                "survival_quantiles": quantile_days,
                "prediction_timestamp": datetime.now().isoformat(),
                "model_version": "1.0.0"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return self._predict_heuristic(features)
    
    def _predict_heuristic(self, features: Dict) -> Dict:
        days_since_last = features.get("days_since_last_event", 
                                      features.get("window_30d_total_events", 0) / 30)
        
        event_frequency = features.get("event_frequency", 0)
        
        total_events = features.get("window_30d_total_events", 0)
        error_rate = features.get("window_30d_error_rate", 0)
        login_count = features.get("window_30d_login_count", 0)
        purchase_count = features.get("window_30d_purchase_count", 0)
        
        churn_score = 0
        
        if days_since_last > 14:
            churn_score += 0.4
        elif days_since_last > 7:
            churn_score += 0.2
        
        if event_frequency < 0.1:
            churn_score += 0.2
        elif event_frequency < 0.5:
            churn_score += 0.1
        
        if total_events < 5:
            churn_score += 0.15
        
        if error_rate > 0.1:
            churn_score += 0.1
        
        if login_count < 2:
            churn_score += 0.1
        
        if purchase_count == 0 and features.get("total_spend", 0) > 0:
            churn_score += 0.05
        
        churn_probability = min(max(churn_score, 0.01), 0.99)
        
        if churn_probability >= 0.7:
            expected_days = 7
        elif churn_probability >= 0.4:
            expected_days = 14
        else:
            expected_days = 30
        
        risk_level = get_risk_level(churn_probability, self.config)
        
        return {
            "churn_probability": float(churn_probability),
            "hazard_ratio": float(churn_probability / 0.5),
            "expected_days_to_churn": float(expected_days),
            "risk_level": risk_level,
            "risk_score": float(churn_probability * 1000),
            "survival_quantiles": {
                "quantile_25": float(expected_days * 0.5),
                "quantile_50": float(expected_days),
                "quantile_75": float(expected_days * 1.5)
            },
            "prediction_timestamp": datetime.now().isoformat(),
            "model_version": "heuristic_1.0.0"
        }
    
    def _calculate_expected_survival_time(self, times: np.ndarray, 
                                         surv_probs: np.ndarray) -> float:
        if len(times) < 2:
            return float(times[-1]) if len(times) > 0 else 30.0
        
        area = 0
        for i in range(1, len(times)):
            dt = times[i] - times[i-1]
            avg_surv = (surv_probs[i] + surv_probs[i-1]) / 2
            area += dt * avg_surv
        
        return float(area)
    
    def _find_quantile_time(self, times: np.ndarray, surv_probs: np.ndarray, 
                           quantile: float) -> float:
        target_prob = 1 - quantile
        
        for i, prob in enumerate(surv_probs):
            if prob <= target_prob:
                if i == 0:
                    return float(times[0])
                
                t0, t1 = times[i-1], times[i]
                p0, p1 = surv_probs[i-1], surv_probs[i]
                
                if p1 == p0:
                    return float(t1)
                
                fraction = (target_prob - p0) / (p1 - p0)
                return float(t0 + fraction * (t1 - t0))
        
        return float(times[-1])
    
    def predict_batch(self, features_list: List[Dict]) -> List[Dict]:
        predictions = []
        for features in features_list:
            pred = self.predict(features)
            pred["user_id"] = features.get("user_id", "unknown")
            predictions.append(pred)
        return predictions
    
    def get_survival_curve(self, features: Dict) -> Dict:
        if not self.is_trained:
            return {
                "times": [7, 14, 30, 60, 90],
                "survival_probabilities": [0.9, 0.8, 0.6, 0.4, 0.2]
            }
        
        feature_dict = {k: v for k, v in features.items() 
                      if k in self.feature_columns}
        
        for col in self.feature_columns:
            if col not in feature_dict:
                feature_dict[col] = 0
        
        df = pd.DataFrame([feature_dict])[self.feature_columns]
        
        surv_func = self.model.predict_survival_function(df)
        
        return {
            "times": surv_func.index.tolist(),
            "survival_probabilities": surv_func.values.flatten().tolist()
        }
    
    def save_model(self, model_path: Optional[str] = None, 
                   scaler_path: Optional[str] = None):
        model_path = model_path or self.model_path
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        model_data = {
            "model": self.model,
            "feature_columns": self.feature_columns,
            "is_trained": self.is_trained,
            "config": self.model_config,
            "trained_at": datetime.now().isoformat()
        }
        
        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, model_path: Optional[str] = None, 
                   scaler_path: Optional[str] = None) -> bool:
        model_path = model_path or self.model_path
        
        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}")
            return False
        
        try:
            with open(model_path, "rb") as f:
                model_data = pickle.load(f)
            
            self.model = model_data["model"]
            self.feature_columns = model_data["feature_columns"]
            self.is_trained = model_data.get("is_trained", False)
            
            logger.info(f"Model loaded from {model_path}. "
                       f"Trained: {self.is_trained}, "
                       f"Features: {len(self.feature_columns)}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def print_summary(self):
        if not self.is_trained:
            logger.info("Model not trained yet.")
            return
        
        print("\n" + "="*80)
        print("COX PROPORTIONAL HAZARDS MODEL SUMMARY")
        print("="*80)
        print(f"\nNumber of features: {len(self.feature_columns)}")
        print(f"Model trained: {self.is_trained}")
        
        print("\nTop 10 Feature Importance:")
        print("-" * 80)
        importance = self.get_feature_importance(top_n=10)
        for feat, data in importance.items():
            print(f"  {feat:40s} HR={data['hazard_ratio']:.4f}  "
                  f"p={data['p_value']:.4f}  coef={data['coefficient']:.4f}")
        
        print("\n" + "="*80 + "\n")
    
    def cross_validate(self, features: List[Dict], k: int = 5) -> Dict:
        if not LIFELINES_AVAILABLE:
            raise RuntimeError("Lifelines library is required for cross-validation")
        
        df = self._prepare_dataframe(features)
        train_cols = ["duration", "event"] + self.feature_columns
        
        cph = CoxPHFitter(penalizer=0.01)
        
        try:
            cv_results = k_fold_cross_validation(
                cph,
                df[train_cols],
                duration_col="duration",
                event_col="event",
                k=k,
                scoring_method="concordance_index"
            )
            
            return {
                "cv_scores": cv_results,
                "mean_c_index": float(np.mean(cv_results)),
                "std_c_index": float(np.std(cv_results)),
                "min_c_index": float(np.min(cv_results)),
                "max_c_index": float(np.max(cv_results)),
                "folds": k
            }
        except Exception as e:
            logger.error(f"Cross-validation error: {e}")
            return {
                "cv_scores": [],
                "mean_c_index": 0.0,
                "std_c_index": 0.0,
                "min_c_index": 0.0,
                "max_c_index": 0.0,
                "folds": k,
                "error": str(e)
            }


class ModelTrainer:
    def __init__(self):
        self.config = load_config()
        self.model = CoxSurvivalModel()
        self.training_history: List[Dict] = []
        
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
    
    def train_and_save(self, features: List[Dict], 
                       model_path: Optional[str] = None) -> Dict:
        logger.info("Starting model training pipeline...")
        
        metrics = self.model.train(features, test_size=0.2)
        
        cv_results = self.model.cross_validate(features, k=5)
        metrics["cross_validation"] = cv_results
        
        self.model.save_model(model_path)
        
        training_record = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "num_samples": len(features),
            "model_path": model_path or self.model.model_path
        }
        self.training_history.append(training_record)
        
        logger.info(f"Training complete. C-index: {metrics['c_index']:.4f}")
        
        return metrics
    
    def retrain_if_needed(self, features: List[Dict]) -> bool:
        retrain_interval = self.config["model"]["retrain_interval_days"]
        
        if not self.training_history:
            return True
        
        last_training = self.training_history[-1]
        last_train_time = datetime.fromisoformat(last_training["timestamp"])
        days_since = (datetime.now() - last_train_time).days
        
        if days_since >= retrain_interval:
            logger.info(f"Retraining model (last trained {days_since} days ago)")
            self.train_and_save(features)
            return True
        
        return False


def main():
    trainer = ModelTrainer()
    
    print("=" * 60)
    print("Cox Survival Model - Training and Prediction")
    print("=" * 60)
    
    print("\n1. Train new model")
    print("2. Load and evaluate existing model")
    print("3. Make prediction with sample data")
    print("4. Show model summary")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        features_path = input("Enter features CSV path (default: ./data/features_latest.csv): ").strip()
        if not features_path:
            features_path = "./data/features_latest.csv"
        
        if not os.path.exists(features_path):
            print(f"Features file not found: {features_path}")
            print("Generating synthetic data and features...")
            
            from spark.feature_engineering import FeatureEngineering
            fe = FeatureEngineering(use_spark=False)
            fe.run_batch()
            features_path = "./data/features_latest.csv"
        
        features = trainer.load_features(features_path)
        
        model_path = input("Enter model save path (default: ./models/cox_model.pkl): ").strip()
        if not model_path:
            model_path = "./models/cox_model.pkl"
        
        metrics = trainer.train_and_save(features, model_path)
        
        print("\n" + "=" * 60)
        print("Training Results:")
        print(f"  C-index (Train): {metrics['c_index_train']:.4f}")
        print(f"  C-index (Test): {metrics.get('c_index_test', 'N/A')}")
        print(f"  Samples: {metrics['num_samples_train']} train, {metrics['num_samples_test']} test")
        print(f"  Events (churned): {metrics['num_events']}")
        print(f"  CV Mean C-index: {metrics['cross_validation']['mean_c_index']:.4f}")
        print("=" * 60)
    
    elif choice == "2":
        model_path = input("Enter model path (default: ./models/cox_model.pkl): ").strip()
        if not model_path:
            model_path = "./models/cox_model.pkl"
        
        if trainer.model.load_model(model_path):
            trainer.model.print_summary()
        else:
            print("Failed to load model")
    
    elif choice == "3":
        model_path = input("Enter model path (default: ./models/cox_model.pkl): ").strip()
        if not model_path:
            model_path = "./models/cox_model.pkl"
        
        trainer.model.load_model(model_path)
        
        sample_features = {
            "user_id": "test_user_001",
            "total_spend": 5000,
            "days_since_signup": 180,
            "days_since_last_event": 3,
            "event_frequency": 0.5,
            "window_7d_total_events": 15,
            "window_7d_login_count": 5,
            "window_7d_purchase_count": 2,
            "window_7d_error_count": 0,
            "window_7d_total_purchase": 250,
            "window_30d_total_events": 50,
            "window_30d_login_count": 15,
            "window_30d_purchase_count": 8,
            "window_30d_error_count": 1,
            "window_30d_total_purchase": 800,
            "avg_days_between_events": 2.5,
            "user_level": 2,
            "region": 1,
            "channel": 0
        }
        
        prediction = trainer.model.predict(sample_features)
        
        print("\n" + "=" * 60)
        print("Prediction Results:")
        print(f"  User ID: {sample_features['user_id']}")
        print(f"  Churn Probability: {prediction['churn_probability']:.4f} ({prediction['churn_probability']*100:.2f}%)")
        print(f"  Risk Level: {prediction['risk_level'].upper()}")
        print(f"  Hazard Ratio: {prediction['hazard_ratio']:.4f}")
        print(f"  Expected Days to Churn: {prediction['expected_days_to_churn']:.1f}")
        print(f"  Risk Score: {prediction['risk_score']:.0f}")
        print(f"\n  Survival Quantiles:")
        for k, v in prediction['survival_quantiles'].items():
            print(f"    {k}: {v:.1f} days")
        print(f"\n  Model: {prediction['model_version']}")
        print(f"  Timestamp: {prediction['prediction_timestamp']}")
        print("=" * 60)
        
        curve = trainer.model.get_survival_curve(sample_features)
        print(f"\nSurvival Curve Data Points (first 10):")
        for t, p in list(zip(curve["times"], curve["survival_probabilities"]))[:10]:
            print(f"  Day {t:6.1f}: {p:.4f} survival probability")
    
    elif choice == "4":
        model_path = input("Enter model path (default: ./models/cox_model.pkl): ").strip()
        if not model_path:
            model_path = "./models/cox_model.pkl"
        
        if trainer.model.load_model(model_path):
            trainer.model.print_summary()


if __name__ == "__main__":
    main()
