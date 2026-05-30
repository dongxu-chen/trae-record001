import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from scipy.stats import ks_2samp
from scipy.spatial.distance import jensenshannon
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class DistributionAligner:
    """分布对齐器 - 用于对齐训练集和验证集的分布"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("DistributionAligner", self.config)
        self.feature_weights = {}
        self.reference_distribution = {}

    def calculate_ks_statistic(self, train_data: pd.Series, val_data: pd.Series) -> float:
        """计算KS统计量 - 衡量两个分布的差异"""
        try:
            statistic, p_value = ks_2samp(train_data.dropna(), val_data.dropna())
            return statistic
        except:
            return 1.0

    def calculate_js_divergence(self, train_data: pd.Series, val_data: pd.Series, 
                                 bins: int = 20) -> float:
        """计算JS散度 - 衡量两个分布的差异"""
        try:
            train_hist, bin_edges = np.histogram(train_data.dropna(), bins=bins, density=True)
            val_hist, _ = np.histogram(val_data.dropna(), bins=bin_edges, density=True)
            
            train_hist = train_hist + 1e-10
            val_hist = val_hist + 1e-10
            
            train_prob = train_hist / train_hist.sum()
            val_prob = val_hist / val_hist.sum()
            
            return jensenshannon(train_prob, val_prob)
        except:
            return 1.0

    def calculate_feature_alignment_score(self, train_df: pd.DataFrame, 
                                            val_df: pd.DataFrame,
                                            features: List[str]) -> Dict[str, float]:
        """计算每个特征的分布对齐分数"""
        alignment_scores = {}
        
        for feat in features:
            if feat in train_df.columns and feat in val_df.columns:
                if train_df[feat].dtype in ['int64', 'float64', 'int32', 'float32']:
                    ks_stat = self.calculate_ks_statistic(train_df[feat], val_df[feat])
                    js_div = self.calculate_js_divergence(train_df[feat], val_df[feat])
                    alignment_scores[feat] = {
                        "ks_statistic": ks_stat,
                        "js_divergence": js_div,
                        "aligned": ks_stat < 0.1 and js_div < 0.1
                    }
        
        return alignment_scores

    def get_overall_alignment_score(self, alignment_scores: Dict[str, Dict]) -> float:
        """计算整体分布对齐分数 (0-1, 越高越好)"""
        if not alignment_scores:
            return 0.0
        
        ks_values = [v["ks_statistic"] for v in alignment_scores.values()]
        js_values = [v["js_divergence"] for v in alignment_scores.values()]
        
        avg_ks = np.mean(ks_values)
        avg_js = np.mean(js_values)
        
        combined = 1 - (0.5 * avg_ks + 0.5 * avg_js)
        return max(0, min(1, combined))


class ImportanceSampler:
    """重要性采样器 - 通过加权使样本分布接近目标分布"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("ImportanceSampler", self.config)
        self.target_histograms = {}

    def fit_target_distribution(self, target_data: pd.DataFrame, features: List[str],
                                 bins: int = 20):
        """拟合目标分布"""
        for feat in features:
            if feat in target_data.columns:
                if target_data[feat].dtype in ['int64', 'float64', 'int32', 'float32']:
                    hist, bin_edges = np.histogram(target_data[feat].dropna(), bins=bins)
                    self.target_histograms[feat] = {
                        "hist": hist / hist.sum(),
                        "bin_edges": bin_edges
                    }
                else:
                    counts = target_data[feat].value_counts(normalize=True)
                    self.target_histograms[feat] = counts.to_dict()
        
        self.logger.info(f"Fitted target distribution for {len(self.target_histograms)} features")

    def calculate_sample_weight(self, sample: pd.Series, features: List[str]) -> float:
        """计算单个样本的重要性权重"""
        weights = []
        
        for feat in features:
            if feat not in self.target_histograms:
                continue
            
            if feat in sample.index:
                value = sample[feat]
                target_hist = self.target_histograms[feat]
                
                if isinstance(target_hist, dict) and "hist" not in target_hist:
                    target_prob = target_hist.get(value, 1e-5)
                    weights.append(target_prob)
                else:
                    hist = target_hist["hist"]
                    bin_edges = target_hist["bin_edges"]
                    
                    bin_idx = np.digitize([value], bin_edges)[0] - 1
                    bin_idx = max(0, min(bin_idx, len(hist) - 1))
                    
                    target_prob = hist[bin_idx] + 1e-5
                    weights.append(target_prob)
        
        if weights:
            return np.prod(weights)
        return 1.0

    def calculate_weights(self, data: pd.DataFrame, features: List[str]) -> np.ndarray:
        """计算所有样本的重要性权重"""
        weights = np.ones(len(data))
        
        for i, (idx, row) in enumerate(data.iterrows()):
            weights[i] = self.calculate_sample_weight(row, features)
        
        weights = weights / weights.sum() * len(weights)
        return np.clip(weights, 0.1, 10.0)


class OnlineValidationSampler:
    """线上验证集采样器 - 从线上流量中采样保持分布一致"""
    
    def __init__(self, config_path: str = "configs/config.yaml", 
                 sampling_rate: float = 0.1,
                 time_window_hours: int = 24):
        self.config = load_config(config_path)
        self.logger = setup_logger("OnlineValidationSampler", self.config)
        
        self.sampling_rate = sampling_rate
        self.time_window_hours = time_window_hours
        
        self.sampler_config = self.config.get("validation_sampling", {})
        
        self.online_buffer = []
        self.buffer_max_size = self.sampler_config.get("buffer_size", 100000)
        
        self.distribution_aligner = DistributionAligner(config_path)
        self.importance_sampler = ImportanceSampler(config_path)
        
        self.training_distribution_features = None
        self.last_sampling_time = datetime.now()

    def set_training_distribution(self, train_df: pd.DataFrame, features: List[str]):
        """设置训练集分布作为参考"""
        self.training_distribution_features = features
        self.importance_sampler.fit_target_distribution(train_df, features)
        self.logger.info(f"Set training distribution reference with {len(features)} features")

    def deterministic_hash(self, value: str) -> float:
        """确定性哈希 - 用于稳定采样"""
        hash_val = int(hashlib.md5(str(value).encode()).hexdigest()[:8], 16)
        return hash_val / (2**32)

    def should_sample(self, user_id: str = None, request_id: str = None) -> bool:
        """
        判断是否应该采样
        使用确定性哈希保证同一用户/请求的一致性
        """
        if user_id:
            hash_val = self.deterministic_hash(user_id)
        elif request_id:
            hash_val = self.deterministic_hash(request_id)
        else:
            hash_val = np.random.random()
        
        return hash_val < self.sampling_rate

    def add_online_sample(self, sample: Dict):
        """添加线上样本到缓冲区"""
        if len(self.online_buffer) >= self.buffer_max_size:
            self.online_buffer.pop(0)
        
        sample["_sampled_at"] = datetime.now().isoformat()
        self.online_buffer.append(sample)

    def build_validation_set(self, target_size: int = 10000,
                              use_importance_weighting: bool = True,
                              align_features: List[str] = None) -> pd.DataFrame:
        """
        构建验证集
        
        Args:
            target_size: 目标验证集大小
            use_importance_weighting: 是否使用重要性加权
            align_features: 用于分布对齐的特征列表
        
        Returns:
            DataFrame: 验证集
        """
        if not self.online_buffer:
            self.logger.warning("No online samples in buffer")
            return pd.DataFrame()
        
        df = pd.DataFrame(self.online_buffer)
        
        if align_features and self.training_distribution_features:
            features_to_use = align_features or self.training_distribution_features
            
            if use_importance_weighting:
                weights = self.importance_sampler.calculate_weights(df, features_to_use)
                df["_sample_weight"] = weights
                
                if len(df) > target_size:
                    probs = weights / weights.sum()
                    selected_indices = np.random.choice(
                        len(df), 
                        size=min(target_size, len(df)),
                        p=probs,
                        replace=False
                    )
                    df = df.iloc[selected_indices].reset_index(drop=True)
            else:
                if len(df) > target_size:
                    df = df.sample(n=target_size, random_state=42).reset_index(drop=True)
            
            alignment_scores = self.distribution_aligner.calculate_feature_alignment_score(
                pd.DataFrame(self.online_buffer[:1000]),
                df,
                features_to_use
            )
            overall_score = self.distribution_aligner.get_overall_alignment_score(alignment_scores)
            
            self.logger.info(f"Built validation set of size {len(df)}")
            self.logger.info(f"Overall distribution alignment score: {overall_score:.4f}")
            
            df.attrs["alignment_scores"] = alignment_scores
            df.attrs["overall_alignment_score"] = overall_score
        else:
            if len(df) > target_size:
                df = df.sample(n=target_size, random_state=42).reset_index(drop=True)
        
        return df

    def get_buffer_stats(self) -> Dict:
        """获取缓冲区统计信息"""
        return {
            "buffer_size": len(self.online_buffer),
            "max_buffer_size": self.buffer_max_size,
            "sampling_rate": self.sampling_rate,
            "time_window_hours": self.time_window_hours
        }

    def cleanup_old_samples(self, hours: int = None):
        """清理过期样本"""
        if hours is None:
            hours = self.time_window_hours
        
        cutoff_time = datetime.now() - pd.Timedelta(hours=hours)
        
        self.online_buffer = [
            s for s in self.online_buffer
            if datetime.fromisoformat(s["_sampled_at"]) > cutoff_time
        ]
        
        self.logger.info(f"Cleaned up old samples, remaining: {len(self.online_buffer)}")


class StreamingValidationSampler:
    """流式验证集采样器 - 用于实时数据流的验证集构建"""
    
    def __init__(self, kafka_topic: str = "ctr_impressions",
                 validation_topic: str = "ctr_validation_samples",
                 sampling_rate: float = 0.05):
        self.kafka_topic = kafka_topic
        self.validation_topic = validation_topic
        self.sampling_rate = sampling_rate
        
        self.samples_collected = 0
        self.samples_skipped = 0

    def process_stream(self, message: Dict) -> Optional[Dict]:
        """
        处理流消息，判断是否采样为验证集
        
        Returns:
            如果采样，返回带标签的样本；否则返回None
        """
        user_id = message.get("user_id", "")
        request_id = message.get("request_id", "")
        
        hash_val = int(hashlib.md5(f"{user_id}_{request_id}".encode()).hexdigest()[:8], 16)
        should_keep = hash_val / (2**32) < self.sampling_rate
        
        if should_keep:
            self.samples_collected += 1
            return {
                **message,
                "_is_validation_sample": True,
                "_sampling_rate": self.sampling_rate
            }
        else:
            self.samples_skipped += 1
            return None

    def get_stats(self) -> Dict:
        """获取采样统计"""
        total = self.samples_collected + self.samples_skipped
        return {
            "samples_collected": self.samples_collected,
            "samples_skipped": self.samples_skipped,
            "total_processed": total,
            "actual_sampling_rate": self.samples_collected / max(total, 1)
        }


def main():
    print("Online Validation Sampler Module")
    print("Provides distribution-aligned validation set sampling")
    
    sampler = OnlineValidationSampler()
    
    np.random.seed(42)
    for i in range(10000):
        sample = {
            "user_id": f"user_{i}",
            "ad_id": f"ad_{np.random.randint(0, 100)}",
            "user_age": np.random.randint(18, 65),
            "user_gender": np.random.choice([0, 1, 2]),
            "ad_price": np.random.uniform(0.1, 10.0),
            "click": np.random.binomial(1, 0.05)
        }
        sampler.add_online_sample(sample)
    
    print("Buffer stats:", sampler.get_buffer_stats())
    
    val_df = sampler.build_validation_set(target_size=1000)
    print(f"Validation set shape: {val_df.shape}")


if __name__ == "__main__":
    main()
