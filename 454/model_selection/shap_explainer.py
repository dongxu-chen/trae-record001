import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import deque
import json
import threading
import queue

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class SHAPExplainer:
    """SHAP值解释器 - 支持KernelSHAP和DeepSHAP"""

    def __init__(self, model, feature_names: List[str], config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("SHAPExplainer", self.config)
        self.model = model
        self.feature_names = feature_names
        self.background_data = None
        self.explainer = None
        self.shap_values_cache = {}

    def set_background_data(self, background_data: pd.DataFrame, sample_size: int = 100):
        """设置背景数据（参考分布）"""
        if len(background_data) > sample_size:
            self.background_data = background_data.sample(n=sample_size, random_state=42)
        else:
            self.background_data = background_data.copy()
        self.logger.info(f"Background data set with {len(self.background_data)} samples")

    def _predict_wrapper(self, X: np.ndarray) -> np.ndarray:
        """模型预测包装器，兼容SHAP接口"""
        if isinstance(X, pd.DataFrame):
            feature_dict = {col: X[col].values.astype(np.float32) for col in X.columns}
        else:
            feature_dict = {}
            for i, feat in enumerate(self.feature_names):
                if i < X.shape[1]:
                    feature_dict[feat] = X[:, i].astype(np.float32)

        try:
            import tensorflow as tf
            predictions = self.model(feature_dict, training=False)
            if isinstance(predictions, dict):
                predictions = predictions.get("click", predictions.get("output", list(predictions.values())[0]))
            return predictions.numpy().flatten()
        except Exception as e:
            self.logger.warning(f"Prediction wrapper error: {e}")
            return np.full(X.shape[0], 0.5)

    def explain_instance(self, instance: Dict, nsamples: int = 100) -> Dict[str, float]:
        """
        解释单个实例的SHAP值
        
        Args:
            instance: 特征字典
            nsamples: KernelSHAP采样次数
        
        Returns:
            各特征的SHAP值字典
        """
        instance_df = pd.DataFrame([instance])

        try:
            import shap
            if self.explainer is None:
                if self.background_data is not None:
                    self.explainer = shap.KernelExplainer(
                        self._predict_wrapper,
                        self.background_data[self.feature_names].values
                    )
                else:
                    self.explainer = shap.KernelExplainer(
                        self._predict_wrapper,
                        np.zeros((1, len(self.feature_names)))
                    )

            shap_values = self.explainer.shap_values(
                instance_df[self.feature_names].values,
                nsamples=nsamples
            )

            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            if shap_values.ndim > 1:
                shap_values = shap_values[0]

            result = {}
            for i, feat in enumerate(self.feature_names):
                if i < len(shap_values):
                    result[feat] = float(shap_values[i])

            return result

        except ImportError:
            self.logger.warning("shap not installed, using gradient-based approximation")
            return self._gradient_shap_approx(instance)
        except Exception as e:
            self.logger.error(f"SHAP computation error: {e}")
            return {feat: 0.0 for feat in self.feature_names}

    def _gradient_shap_approx(self, instance: Dict) -> Dict[str, float]:
        """梯度近似SHAP值（当SHAP库不可用时的降级方案）"""
        try:
            import tensorflow as tf

            instance_tensor = {}
            for feat in self.feature_names:
                val = instance.get(feat, 0.0)
                instance_tensor[feat] = tf.convert_to_tensor([float(val)], dtype=tf.float32)

            baseline_tensor = {}
            for feat in self.feature_names:
                baseline_tensor[feat] = tf.convert_to_tensor([0.0], dtype=tf.float32)

            with tf.GradientTape() as tape:
                for key in instance_tensor:
                    tape.watch(instance_tensor[key])
                pred = self.model(instance_tensor, training=False)
                if isinstance(pred, dict):
                    pred = pred.get("click", list(pred.values())[0])

            gradients = tape.gradient(pred, list(instance_tensor.values()))

            with tf.GradientTape() as tape:
                for key in baseline_tensor:
                    tape.watch(baseline_tensor[key])
                baseline_pred = self.model(baseline_tensor, training=False)
                if isinstance(baseline_pred, dict):
                    baseline_pred = baseline_pred.get("click", list(baseline_pred.values())[0])

            baseline_gradients = tape.gradient(baseline_pred, list(baseline_tensor.values()))

            shap_approx = {}
            for i, feat in enumerate(self.feature_names):
                if gradients[i] is not None and baseline_gradients[i] is not None:
                    avg_grad = (gradients[i] + baseline_gradients[i]) / 2.0
                    diff = instance_tensor[feat] - baseline_tensor[feat]
                    shap_approx[feat] = float((avg_grad * diff).numpy()[0])
                else:
                    shap_approx[feat] = 0.0

            return shap_approx

        except Exception as e:
            self.logger.error(f"Gradient SHAP approximation error: {e}")
            return {feat: 0.0 for feat in self.feature_names}

    def explain_batch(self, instances: List[Dict], nsamples: int = 50) -> List[Dict[str, float]]:
        """批量解释"""
        results = []
        for instance in instances:
            shap_vals = self.explain_instance(instance, nsamples=nsamples)
            results.append(shap_vals)
        return results


class RealtimeSHAPServer:
    """实时SHAP值输出服务 - 异步计算，不阻塞预测"""

    def __init__(self, model, feature_names: List[str], 
                 config_path: str = "configs/config.yaml",
                 max_cache_size: int = 10000):
        self.config = load_config(config_path)
        self.logger = setup_logger("RealtimeSHAPServer", self.config)

        self.explainer = SHAPExplainer(model, feature_names, config_path)
        self.feature_names = feature_names

        self.shap_cache = {}
        self.max_cache_size = max_cache_size
        self.recent_shap_values = deque(maxlen=10000)

        self.async_queue = queue.Queue(maxsize=50000)
        self.workers = []
        self.running = False
        self.num_workers = 2

        self.stats = {
            "total_computed": 0,
            "cache_hits": 0,
            "avg_compute_time_ms": 0
        }
        self._lock = threading.Lock()

    def set_background_data(self, background_data: pd.DataFrame, sample_size: int = 100):
        """设置背景数据"""
        self.explainer.set_background_data(background_data, sample_size)

    def get_shap_values_sync(self, instance: Dict, use_cache: bool = True) -> Dict[str, float]:
        """
        同步获取SHAP值
        
        Args:
            instance: 特征字典
            use_cache: 是否使用缓存
        
        Returns:
            SHAP值字典
        """
        if use_cache:
            cache_key = self._compute_cache_key(instance)
            if cache_key in self.shap_cache:
                with self._lock:
                    self.stats["cache_hits"] += 1
                return self.shap_cache[cache_key]

        import time
        start = time.time()

        shap_values = self.explainer.explain_instance(instance, nsamples=50)

        compute_time = (time.time() - start) * 1000
        with self._lock:
            self.stats["total_computed"] += 1
            self.stats["avg_compute_time_ms"] = (
                0.9 * self.stats["avg_compute_time_ms"] + 0.1 * compute_time
            )

        if use_cache:
            self._add_to_cache(cache_key, shap_values)

        self.recent_shap_values.append({
            "shap_values": shap_values,
            "timestamp": datetime.now().isoformat()
        })

        return shap_values

    def get_shap_values_async(self, prediction_id: str, instance: Dict, 
                               callback: Optional[callable] = None):
        """
        异步获取SHAP值 - 不阻塞主预测链路
        
        Args:
            prediction_id: 预测ID
            instance: 特征字典
            callback: 计算完成后的回调函数
        """
        try:
            self.async_queue.put_nowait({
                "prediction_id": prediction_id,
                "instance": instance,
                "callback": callback,
                "enqueue_time": datetime.now().isoformat()
            })
        except queue.Full:
            self.logger.warning("SHAP async queue full, dropping request")

    def _worker_loop(self):
        """工作线程主循环"""
        while self.running:
            try:
                item = self.async_queue.get(timeout=1.0)
                shap_values = self.explainer.explain_instance(item["instance"], nsamples=50)

                self.recent_shap_values.append({
                    "prediction_id": item["prediction_id"],
                    "shap_values": shap_values,
                    "timestamp": datetime.now().isoformat()
                })

                with self._lock:
                    self.stats["total_computed"] += 1

                if item.get("callback"):
                    try:
                        item["callback"](item["prediction_id"], shap_values)
                    except Exception as e:
                        self.logger.error(f"SHAP callback error: {e}")

                self.async_queue.task_done()
            except queue.Empty:
                continue

    def start(self):
        """启动异步工作线程"""
        if self.running:
            return
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
        self.logger.info(f"Started {self.num_workers} SHAP workers")

    def stop(self):
        """停止工作线程"""
        self.running = False
        for w in self.workers:
            w.join(timeout=5.0)
        self.workers = []

    def _compute_cache_key(self, instance: Dict) -> str:
        """计算缓存键"""
        import hashlib
        key_parts = []
        for feat in sorted(self.feature_names):
            if feat in instance:
                key_parts.append(f"{feat}:{instance[feat]}")
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _add_to_cache(self, cache_key: str, shap_values: Dict):
        """添加到缓存"""
        if len(self.shap_cache) >= self.max_cache_size:
            oldest_key = next(iter(self.shap_cache))
            del self.shap_cache[oldest_key]
        self.shap_cache[cache_key] = shap_values

    def get_aggregated_shap(self, top_k: int = 20) -> Dict[str, Dict[str, float]]:
        """
        获取聚合SHAP值 - 近期所有预测的平均贡献
        
        Returns:
            各特征的平均绝对SHAP值和方向
        """
        if not self.recent_shap_values:
            return {}

        all_shaps = {}
        for item in self.recent_shap_values:
            for feat, val in item["shap_values"].items():
                if feat not in all_shaps:
                    all_shaps[feat] = []
                all_shaps[feat].append(val)

        aggregated = {}
        for feat, values in all_shaps.items():
            abs_values = [abs(v) for v in values]
            aggregated[feat] = {
                "mean_abs_shap": float(np.mean(abs_values)),
                "mean_shap": float(np.mean(values)),
                "std_shap": float(np.std(values)),
                "direction": "positive" if np.mean(values) > 0 else "negative"
            }

        sorted_feats = sorted(aggregated.items(), key=lambda x: x[1]["mean_abs_shap"], reverse=True)
        return dict(sorted_feats[:top_k])

    def get_explanation_summary(self, instance: Dict, top_k: int = 10) -> Dict:
        """
        获取单个实例的解释摘要
        
        Returns:
            包含SHAP值和解释的字典
        """
        shap_values = self.get_shap_values_sync(instance)

        sorted_shap = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)

        base_value = 0.0
        try:
            if self.explainer.explainer is not None:
                base_value = float(self.explainer.explainer.expected_value)
                if isinstance(base_value, np.ndarray):
                    base_value = float(base_value[0])
        except:
            pass

        prediction = base_value + sum(shap_values.values())

        top_positive = [f for f, v in sorted_shap if v > 0][:top_k]
        top_negative = [f for f, v in sorted_shap if v < 0][:top_k]

        return {
            "base_value": base_value,
            "prediction": prediction,
            "shap_values": shap_values,
            "top_positive_features": top_positive,
            "top_negative_features": top_negative,
            "explanation": self._generate_explanation(shap_values, top_k),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_explanation(self, shap_values: Dict, top_k: int) -> str:
        """生成自然语言解释"""
        sorted_shap = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
        top_features = sorted_shap[:top_k]

        positive = [f"{feat}(+{val:.4f})" for feat, val in top_features if val > 0]
        negative = [f"{feat}({val:.4f})" for feat, val in top_features if val < 0]

        explanation_parts = []
        if positive:
            explanation_parts.append(f"正向驱动: {', '.join(positive[:5])}")
        if negative:
            explanation_parts.append(f"负向驱动: {', '.join(negative[:5])}")

        return "; ".join(explanation_parts)

    def plot_shap_summary(self, output_path: str = "reports/shap_summary.png"):
        """绘制SHAP汇总图"""
        ensure_dir(os.path.dirname(output_path))
        aggregated = self.get_aggregated_shap()

        if not aggregated:
            self.logger.warning("No SHAP values to plot")
            return

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        features = list(aggregated.keys())
        mean_abs_shap = [aggregated[f]["mean_abs_shap"] for f in features]
        directions = [aggregated[f]["mean_shap"] for f in features]

        sorted_idx = np.argsort(mean_abs_shap)[::-1]
        features = [features[i] for i in sorted_idx]
        mean_abs_shap = [mean_abs_shap[i] for i in sorted_idx]
        directions = [directions[i] for i in sorted_idx]

        colors = ["#ff6b6b" if d < 0 else "#4ecdc4" for d in directions]

        fig, ax = plt.subplots(figsize=(10, max(6, len(features) * 0.4)))
        y_pos = np.arange(len(features))
        ax.barh(y_pos, mean_abs_shap, color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.set_xlabel("Mean |SHAP value|")
        ax.set_title("SHAP Feature Importance (Real-time Aggregated)")
        ax.invert_yaxis()
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"SHAP summary plot saved to {output_path}")

    def plot_waterfall(self, instance: Dict, output_path: str = "reports/shap_waterfall.png"):
        """绘制单个实例的SHAP瀑布图"""
        ensure_dir(os.path.dirname(output_path))

        summary = self.get_explanation_summary(instance)
        shap_values = summary["shap_values"]

        sorted_shap = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        features = [f[0] for f in sorted_shap[:15]]
        values = [f[1] for f in sorted_shap[:15]]

        fig, ax = plt.subplots(figsize=(10, max(6, len(features) * 0.4)))
        colors = ["#ff6b6b" if v < 0 else "#4ecdc4" for v in values]
        y_pos = np.arange(len(features))

        cumulative = [summary["base_value"]]
        for v in values:
            cumulative.append(cumulative[-1] + v)

        ax.barh(y_pos, values, left=cumulative[:-1], color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.set_xlabel("SHAP value (impact on prediction)")
        ax.set_title(f"SHAP Waterfall - Prediction: {summary['prediction']:.4f}")
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)
        ax.invert_yaxis()
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"SHAP waterfall plot saved to {output_path}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
        stats["cache_size"] = len(self.shap_cache)
        stats["queue_size"] = self.async_queue.qsize()
        stats["recent_count"] = len(self.recent_shap_values)
        return stats


def main():
    print("SHAP Explainer Module")
    print("Provides real-time SHAP value computation for model interpretability")


if __name__ == "__main__":
    main()
