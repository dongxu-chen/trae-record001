import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy.stats import ks_2samp, chi2_contingency, wasserstein_distance
from scipy.spatial.distance import jensenshannon
import json
import threading
import time
import queue

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class FeatureDriftDetector:
    """特征漂移检测器 - 多维度监控特征分布变化"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("FeatureDriftDetector", self.config)

        self.drift_config = self.config.get("drift_detection", {
            "ks_threshold": 0.05,
            "js_threshold": 0.1,
            "psi_threshold": 0.2,
            "wasserstein_threshold": 0.5,
            "window_size": 10000,
            "check_interval_seconds": 300,
            "auto_retrain": True
        })

        self.reference_distributions = {}
        self.drift_history = []
        self.drift_callbacks = []
        self.alert_count = 0

    def set_reference_distribution(self, reference_data: pd.DataFrame, 
                                     features: List[str]):
        """
        设置参考分布（训练集分布）
        
        Args:
            reference_data: 参考数据集（通常是训练集）
            features: 需要监控的特征列表
        """
        self.reference_features = features
        self.reference_distributions = {}

        for feat in features:
            if feat not in reference_data.columns:
                continue

            col = reference_data[feat]
            if col.dtype in ['int64', 'float64', 'int32', 'float32']:
                hist, bin_edges = np.histogram(col.dropna(), bins=50)
                self.reference_distributions[feat] = {
                    "type": "numerical",
                    "values": col.dropna().values,
                    "mean": float(col.mean()),
                    "std": float(col.std()),
                    "hist": hist,
                    "bin_edges": bin_edges,
                    "percentiles": {
                        "p1": float(col.quantile(0.01)),
                        "p5": float(col.quantile(0.05)),
                        "p25": float(col.quantile(0.25)),
                        "p50": float(col.quantile(0.50)),
                        "p75": float(col.quantile(0.75)),
                        "p95": float(col.quantile(0.95)),
                        "p99": float(col.quantile(0.99))
                    }
                }
            else:
                value_counts = col.value_counts(normalize=True)
                self.reference_distributions[feat] = {
                    "type": "categorical",
                    "values": col.values,
                    "distribution": value_counts.to_dict(),
                    "unique_count": col.nunique()
                }

        self.logger.info(f"Reference distribution set for {len(self.reference_distributions)} features")

    def detect_numerical_drift(self, feat_name: str, current_data: np.ndarray) -> Dict:
        """
        检测数值特征的漂移
        
        使用多种统计检验:
        - KS检验 (Kolmogorov-Smirnov)
        - JS散度 (Jensen-Shannon)
        - PSI (Population Stability Index)
        - Wasserstein距离
        """
        ref = self.reference_distributions.get(feat_name)
        if ref is None or ref["type"] != "numerical":
            return {"feature": feat_name, "error": "Feature not in reference or not numerical"}

        ref_values = ref["values"]
        current_clean = np.array(current_data).flatten()
        current_clean = current_clean[~np.isnan(current_clean)]

        if len(current_clean) < 10:
            return {"feature": feat_name, "error": "Insufficient data"}

        try:
            ks_stat, ks_pvalue = ks_2samp(ref_values, current_clean)
        except:
            ks_stat, ks_pvalue = 1.0, 0.0

        try:
            ref_hist, bin_edges = np.histogram(ref_values, bins=50, density=True)
            cur_hist, _ = np.histogram(current_clean, bins=bin_edges, density=True)
            ref_prob = ref_hist / (ref_hist.sum() + 1e-10)
            cur_prob = cur_hist / (cur_hist.sum() + 1e-10)
            js_div = float(jensenshannon(ref_prob, cur_prob))
        except:
            js_div = 1.0

        psi = self._calculate_psi(ref_values, current_clean)

        try:
            wd = float(wasserstein_distance(ref_values, current_clean))
        except:
            wd = float('inf')

        ks_threshold = self.drift_config.get("ks_threshold", 0.05)
        js_threshold = self.drift_config.get("js_threshold", 0.1)
        psi_threshold = self.drift_config.get("psi_threshold", 0.2)
        wd_threshold = self.drift_config.get("wasserstein_threshold", 0.5)

        ks_drift = ks_stat > ks_threshold or ks_pvalue < 0.01
        js_drift = js_div > js_threshold
        psi_drift = psi > psi_threshold
        wd_drift = wd > wd_threshold

        drift_score = (int(ks_drift) + int(js_drift) + int(psi_drift) + int(wd_drift)) / 4.0

        severity = "none"
        if drift_score >= 0.75:
            severity = "critical"
        elif drift_score >= 0.5:
            severity = "high"
        elif drift_score >= 0.25:
            severity = "medium"
        elif drift_score > 0:
            severity = "low"

        current_mean = float(np.mean(current_clean))
        current_std = float(np.std(current_clean))

        return {
            "feature": feat_name,
            "type": "numerical",
            "drift_detected": drift_score > 0.25,
            "severity": severity,
            "drift_score": drift_score,
            "metrics": {
                "ks_statistic": ks_stat,
                "ks_pvalue": ks_pvalue,
                "js_divergence": js_div,
                "psi": psi,
                "wasserstein_distance": wd
            },
            "thresholds": {
                "ks_threshold": ks_threshold,
                "js_threshold": js_threshold,
                "psi_threshold": psi_threshold,
                "wd_threshold": wd_threshold
            },
            "reference_stats": {
                "mean": ref["mean"],
                "std": ref["std"]
            },
            "current_stats": {
                "mean": current_mean,
                "std": current_std,
                "mean_shift_pct": (current_mean - ref["mean"]) / max(abs(ref["mean"]), 1e-10) * 100,
                "std_shift_pct": (current_std - ref["std"]) / max(abs(ref["std"]), 1e-10) * 100
            },
            "checks": {
                "ks_drift": ks_drift,
                "js_drift": js_drift,
                "psi_drift": psi_drift,
                "wd_drift": wd_drift
            }
        }

    def _calculate_psi(self, reference: np.ndarray, current: np.ndarray, 
                        bins: int = 10) -> float:
        """计算PSI (Population Stability Index)"""
        try:
            _, bin_edges = np.histogram(reference, bins=bins)
            bin_edges[0] = -float('inf')
            bin_edges[-1] = float('inf')

            ref_counts = np.histogram(reference, bins=bin_edges)[0]
            cur_counts = np.histogram(current, bins=bin_edges)[0]

            ref_pct = ref_counts / ref_counts.sum()
            cur_pct = cur_counts / cur_counts.sum()

            ref_pct = np.clip(ref_pct, 1e-6, None)
            cur_pct = np.clip(cur_pct, 1e-6, None)

            psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
            return float(psi)
        except:
            return float('inf')

    def detect_categorical_drift(self, feat_name: str, current_data: np.ndarray) -> Dict:
        """检测类别特征的漂移"""
        ref = self.reference_distributions.get(feat_name)
        if ref is None or ref["type"] != "categorical":
            return {"feature": feat_name, "error": "Feature not in reference or not categorical"}

        ref_dist = ref["distribution"]
        current_series = pd.Series(current_data)
        current_dist = current_series.value_counts(normalize=True).to_dict()

        all_categories = set(list(ref_dist.keys()) + list(current_dist.keys()))

        ref_probs = np.array([ref_dist.get(cat, 1e-6) for cat in all_categories])
        cur_probs = np.array([current_dist.get(cat, 1e-6) for cat in all_categories])

        js_div = float(jensenshannon(ref_probs, cur_probs))

        try:
            ref_counts = np.array([int(ref_dist.get(cat, 0) * len(ref["values"])) for cat in all_categories])
            cur_counts = np.array([int(current_dist.get(cat, 0) * len(current_data)) for cat in all_categories])
            if ref_counts.sum() > 0 and cur_counts.sum() > 0:
                contingency = np.array([ref_counts, cur_counts])
                chi2_stat, chi2_pvalue, _, _ = chi2_contingency(contingency + 1)
            else:
                chi2_stat, chi2_pvalue = 0.0, 1.0
        except:
            chi2_stat, chi2_pvalue = 0.0, 1.0

        psi = 0.0
        for cat in all_categories:
            ref_p = ref_dist.get(cat, 1e-6)
            cur_p = current_dist.get(cat, 1e-6)
            if ref_p > 0 and cur_p > 0:
                psi += (cur_p - ref_p) * np.log(cur_p / ref_p)

        js_threshold = self.drift_config.get("js_threshold", 0.1)
        js_drift = js_div > js_threshold
        chi2_drift = chi2_pvalue < 0.01

        drift_score = (int(js_drift) + int(chi2_drift)) / 2.0

        severity = "none"
        if drift_score >= 0.75:
            severity = "critical"
        elif drift_score >= 0.5:
            severity = "high"
        elif drift_score >= 0.25:
            severity = "medium"
        elif drift_score > 0:
            severity = "low"

        return {
            "feature": feat_name,
            "type": "categorical",
            "drift_detected": drift_score > 0.25,
            "severity": severity,
            "drift_score": drift_score,
            "metrics": {
                "js_divergence": js_div,
                "chi2_statistic": chi2_stat,
                "chi2_pvalue": chi2_pvalue,
                "psi": psi
            },
            "checks": {
                "js_drift": js_drift,
                "chi2_drift": chi2_drift
            },
            "new_categories": list(set(current_dist.keys()) - set(ref_dist.keys())),
            "missing_categories": list(set(ref_dist.keys()) - set(current_dist.keys()))
        }

    def detect_all_features(self, current_data: pd.DataFrame) -> Dict:
        """
        检测所有特征的漂移
        
        Args:
            current_data: 当前线上数据
        
        Returns:
            漂移检测报告
        """
        drift_report = {
            "timestamp": datetime.now().isoformat(),
            "total_features_checked": 0,
            "drifted_features": [],
            "drift_details": {},
            "overall_drift_score": 0.0,
            "recommendation": "no_action"
        }

        drift_scores = []

        for feat_name, ref_info in self.reference_distributions.items():
            if feat_name not in current_data.columns:
                continue

            drift_report["total_features_checked"] += 1
            current_values = current_data[feat_name].dropna().values

            if ref_info["type"] == "numerical":
                result = self.detect_numerical_drift(feat_name, current_values)
            else:
                result = self.detect_categorical_drift(feat_name, current_values)

            drift_report["drift_details"][feat_name] = result

            if result.get("drift_detected", False):
                drift_report["drifted_features"].append(feat_name)

            if "drift_score" in result:
                drift_scores.append(result["drift_score"])

            self.drift_history.append({
                "timestamp": datetime.now().isoformat(),
                "feature": feat_name,
                "result": result
            })

        if drift_scores:
            drift_report["overall_drift_score"] = float(np.mean(drift_scores))

        if drift_report["overall_drift_score"] >= 0.5:
            drift_report["recommendation"] = "retrain_immediately"
        elif drift_report["overall_drift_score"] >= 0.25:
            drift_report["recommendation"] = "schedule_retrain"
        elif len(drift_report["drifted_features"]) > 0:
            drift_report["recommendation"] = "monitor_closely"
        else:
            drift_report["recommendation"] = "no_action"

        self.alert_count = len(drift_report["drifted_features"])

        for callback in self.drift_callbacks:
            try:
                callback(drift_report)
            except Exception as e:
                self.logger.error(f"Drift callback error: {e}")

        self.logger.info(
            f"Drift check: {drift_report['total_features_checked']} features, "
            f"{len(drift_report['drifted_features'])} drifted, "
            f"score={drift_report['overall_drift_score']:.4f}, "
            f"recommendation={drift_report['recommendation']}"
        )

        return drift_report

    def register_drift_callback(self, callback):
        """注册漂移回调函数"""
        self.drift_callbacks.append(callback)

    def get_drift_history(self, feature_name: str = None, 
                           last_n: int = 100) -> List[Dict]:
        """获取漂移检测历史"""
        history = self.drift_history
        if feature_name:
            history = [h for h in history if h["feature"] == feature_name]
        return history[-last_n:]


class StreamingDriftMonitor:
    """流式漂移监控 - 持续监控线上特征分布"""

    def __init__(self, config_path: str = "configs/config.yaml",
                 window_size: int = 10000,
                 check_interval: int = 300):
        self.config = load_config(config_path)
        self.logger = setup_logger("StreamingDriftMonitor", self.config)

        self.detector = FeatureDriftDetector(config_path)
        self.window_size = window_size
        self.check_interval = check_interval

        self.data_buffer = []
        self.running = False
        self.monitor_thread = None

        self.last_check_time = None
        self.last_drift_report = None
        self.retrain_triggered = False

    def set_reference(self, reference_data: pd.DataFrame, features: List[str]):
        """设置参考分布"""
        self.detector.set_reference_distribution(reference_data, features)
        self.monitored_features = features

    def add_data_point(self, data: Dict):
        """添加线上数据点到缓冲区"""
        self.data_buffer.append(data)
        if len(self.data_buffer) > self.window_size * 2:
            self.data_buffer = self.data_buffer[-self.window_size:]

    def add_data_batch(self, data_batch: List[Dict]):
        """批量添加数据"""
        self.data_buffer.extend(data_batch)
        if len(self.data_buffer) > self.window_size * 2:
            self.data_buffer = self.data_buffer[-self.window_size:]

    def check_drift(self) -> Dict:
        """执行一次漂移检测"""
        if len(self.data_buffer) < 100:
            return {"error": "Insufficient data in buffer", "buffer_size": len(self.data_buffer)}

        current_df = pd.DataFrame(self.data_buffer[-self.window_size:])
        report = self.detector.detect_all_features(current_df)

        self.last_check_time = datetime.now()
        self.last_drift_report = report

        if report["recommendation"] in ["retrain_immediately", "schedule_retrain"]:
            self.retrain_triggered = True
            self.logger.warning(f"Drift detected! Recommendation: {report['recommendation']}")
            self.logger.warning(f"Drifted features: {report['drifted_features']}")

        return report

    def start_monitoring(self):
        """启动后台监控"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Drift monitoring started")

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("Drift monitoring stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                if len(self.data_buffer) >= self.window_size:
                    self.check_drift()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(60)

    def get_status(self) -> Dict:
        """获取监控状态"""
        return {
            "running": self.running,
            "buffer_size": len(self.data_buffer),
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "retrain_triggered": self.retrain_triggered,
            "monitored_features": list(self.detector.reference_distributions.keys()),
            "overall_drift_score": self.last_drift_report.get("overall_drift_score", 0) if self.last_drift_report else 0
        }


class DriftTriggeredRetrainer:
    """漂移触发重训练器"""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("DriftTriggeredRetrainer", self.config)

        self.monitor = StreamingDriftMonitor(config_path)
        self.retrain_callbacks = []
        self.retrain_history = []

    def setup_monitoring(self, reference_data: pd.DataFrame, features: List[str],
                          window_size: int = 10000, check_interval: int = 300):
        """设置漂移监控"""
        self.monitor.set_reference(reference_data, features)
        self.monitor.window_size = window_size
        self.monitor.check_interval = check_interval

        self.monitor.detector.register_drift_callback(self._on_drift_detected)

    def _on_drift_detected(self, drift_report: Dict):
        """漂移检测回调"""
        self.logger.warning(f"Drift detected: {drift_report['recommendation']}")

        if drift_report["recommendation"] == "retrain_immediately":
            self._trigger_retrain(drift_report, urgent=True)
        elif drift_report["recommendation"] == "schedule_retrain":
            self._trigger_retrain(drift_report, urgent=False)

    def _trigger_retrain(self, drift_report: Dict, urgent: bool = False):
        """触发重训练"""
        retrain_event = {
            "timestamp": datetime.now().isoformat(),
            "trigger": "drift_detection",
            "urgent": urgent,
            "drift_score": drift_report["overall_drift_score"],
            "drifted_features": drift_report["drifted_features"],
            "recommendation": drift_report["recommendation"],
            "status": "triggered"
        }

        self.retrain_history.append(retrain_event)

        for callback in self.retrain_callbacks:
            try:
                callback(retrain_event)
            except Exception as e:
                self.logger.error(f"Retrain callback error: {e}")

    def register_retrain_callback(self, callback):
        """注册重训练回调"""
        self.retrain_callbacks.append(callback)

    def start(self):
        """启动监控"""
        self.monitor.start_monitoring()

    def stop(self):
        """停止监控"""
        self.monitor.stop_monitoring()

    def get_retrain_history(self) -> List[Dict]:
        """获取重训练历史"""
        return self.retrain_history


def main():
    print("Feature Drift Detection Module")
    print("Monitors feature distribution changes and triggers retraining")


if __name__ == "__main__":
    main()
