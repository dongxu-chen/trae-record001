import time
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime, timedelta
import yaml
import numpy as np


@dataclass
class ReviewSample:
    sample_id: str
    click_id: str
    ip: str
    device_id: str
    publisher_id: str
    timestamp: float
    fraud_score: float
    predicted_action: str
    rule_hits: List[str]
    model_features: Dict[str, float]
    review_status: str = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[float] = None
    actual_label: Optional[str] = None
    review_notes: Optional[str] = None
    feedback_used: bool = False


@dataclass
class ReviewStats:
    total_samples: int = 0
    pending_samples: int = 0
    reviewed_samples: int = 0
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0


class HumanReviewSystem:
    def __init__(self, config_path: str = 'config/config.yaml', 
                 redis_client=None):
        self.config = self._load_config(config_path)
        self.samples: Dict[str, ReviewSample] = {}
        self.ip_to_samples: Dict[str, List[str]] = defaultdict(list)
        self.publisher_to_samples: Dict[str, List[str]] = defaultdict(list)
        self.stats = ReviewStats()
        
        self.redis_client = redis_client
        self.use_redis = redis_client is not None
        
        self.auto_sample_threshold = self.config.get('review_system', {}).get(
            'auto_sample_threshold', 0.6
        )
        self.sample_high_risk_ratio = self.config.get('review_system', {}).get(
            'sample_high_risk_ratio', 0.7
        )
        self.feedback_update_interval = self.config.get('review_system', {}).get(
            'feedback_update_interval', 3600
        )
        
        self.last_feedback_update = time.time()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if 'review_system' not in config:
                config['review_system'] = {
                    'auto_sample_threshold': 0.6,
                    'sample_high_risk_ratio': 0.7,
                    'feedback_update_interval': 3600
                }
            return config

    def _generate_sample_id(self) -> str:
        return f"sample_{uuid.uuid4().hex[:12]}"

    def should_sample(self, fraud_score: float) -> bool:
        if fraud_score >= self.auto_sample_threshold:
            return True
        
        random_threshold = (1 - self.sample_high_risk_ratio) * 0.1
        return np.random.random() < random_threshold

    def add_sample(self, click_id: str, ip: str, device_id: str, 
                   publisher_id: str, fraud_score: float, 
                   predicted_action: str, rule_hits: List[str] = None,
                   model_features: Dict[str, float] = None) -> Optional[str]:
        if not self.should_sample(fraud_score):
            return None
        
        sample_id = self._generate_sample_id()
        sample = ReviewSample(
            sample_id=sample_id,
            click_id=click_id,
            ip=ip,
            device_id=device_id,
            publisher_id=publisher_id,
            timestamp=time.time(),
            fraud_score=fraud_score,
            predicted_action=predicted_action,
            rule_hits=rule_hits or [],
            model_features=model_features or {}
        )
        
        self.samples[sample_id] = sample
        self.ip_to_samples[ip].append(sample_id)
        self.publisher_to_samples[publisher_id].append(sample_id)
        
        if self.use_redis:
            self._save_to_redis(sample)
        
        return sample_id

    def _save_to_redis(self, sample: ReviewSample):
        try:
            key = f"review:samples:{sample.sample_id}"
            self.redis_client.setex(key, 86400 * 7, json.dumps(asdict(sample), ensure_ascii=False))
            self.redis_client.sadd("review:pending", sample.sample_id)
        except Exception as e:
            print(f"Redis save error: {e}")

    def get_pending_samples(self, limit: int = 100, 
                           publisher_id: str = None,
                           min_score: float = None) -> List[ReviewSample]:
        pending = [s for s in self.samples.values() if s.review_status == "pending"]
        
        if publisher_id:
            pending = [s for s in pending if s.publisher_id == publisher_id]
        if min_score is not None:
            pending = [s for s in pending if s.fraud_score >= min_score]
        
        pending.sort(key=lambda x: -x.fraud_score)
        return pending[:limit]

    def get_sample(self, sample_id: str) -> Optional[ReviewSample]:
        return self.samples.get(sample_id)

    def review_sample(self, sample_id: str, actual_label: str, 
                      reviewer: str = "admin", notes: str = None) -> bool:
        if sample_id not in self.samples:
            return False
        
        sample = self.samples[sample_id]
        sample.review_status = "reviewed"
        sample.reviewed_by = reviewer
        sample.reviewed_at = time.time()
        sample.actual_label = actual_label
        sample.review_notes = notes
        
        if self.use_redis:
            self._update_redis_review(sample)
        
        return True

    def _update_redis_review(self, sample: ReviewSample):
        try:
            key = f"review:samples:{sample.sample_id}"
            self.redis_client.setex(key, 86400 * 7, json.dumps(asdict(sample), ensure_ascii=False))
            self.redis_client.srem("review:pending", sample.sample_id)
            self.redis_client.sadd("review:reviewed", sample.sample_id)
        except Exception as e:
            print(f"Redis update error: {e}")

    def batch_review(self, sample_ids: List[str], actual_label: str,
                     reviewer: str = "admin") -> int:
        success_count = 0
        for sample_id in sample_ids:
            if self.review_sample(sample_id, actual_label, reviewer):
                success_count += 1
        return success_count

    def calculate_statistics(self) -> ReviewStats:
        reviewed = [s for s in self.samples.values() if s.review_status == "reviewed"]
        
        tp = tn = fp = fn = 0
        
        for sample in reviewed:
            predicted_fraud = sample.fraud_score >= 0.5
            actual_fraud = sample.actual_label == "fraud"
            
            if predicted_fraud and actual_fraud:
                tp += 1
            elif not predicted_fraud and not actual_fraud:
                tn += 1
            elif predicted_fraud and not actual_fraud:
                fp += 1
            else:
                fn += 1
        
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(0.001, precision + recall)
        
        self.stats = ReviewStats(
            total_samples=len(self.samples),
            pending_samples=len([s for s in self.samples.values() if s.review_status == "pending"]),
            reviewed_samples=len(reviewed),
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1
        )
        
        return self.stats

    def get_feedback_data(self) -> List[Dict]:
        reviewed = [s for s in self.samples.values() 
                   if s.review_status == "reviewed" and not s.feedback_used]
        
        feedback = []
        for sample in reviewed:
            feedback.append({
                'features': sample.model_features,
                'label': 1 if sample.actual_label == "fraud" else 0,
                'sample_id': sample.sample_id,
                'fraud_score': sample.fraud_score
            })
        
        return feedback

    def mark_feedback_used(self, sample_ids: List[str]):
        for sample_id in sample_ids:
            if sample_id in self.samples:
                self.samples[sample_id].feedback_used = True

    def get_suspicious_ips(self, min_samples: int = 3) -> List[Dict]:
        suspicious = []
        for ip, sample_ids in self.ip_to_samples.items():
            if len(sample_ids) >= min_samples:
                samples = [self.samples[sid] for sid in sample_ids if sid in self.samples]
                avg_score = np.mean([s.fraud_score for s in samples])
                fraud_count = sum(1 for s in samples if s.actual_label == "fraud")
                
                suspicious.append({
                    'ip': ip,
                    'sample_count': len(samples),
                    'avg_fraud_score': float(avg_score),
                    'confirmed_fraud': fraud_count
                })
        
        suspicious.sort(key=lambda x: -x['avg_fraud_score'])
        return suspicious

    def get_publisher_performance(self) -> List[Dict]:
        performance = []
        for publisher_id, sample_ids in self.publisher_to_samples.items():
            samples = [self.samples[sid] for sid in sample_ids if sid in self.samples]
            reviewed = [s for s in samples if s.review_status == "reviewed"]
            
            if reviewed:
                avg_score = np.mean([s.fraud_score for s in samples])
                fraud_rate = sum(1 for s in reviewed if s.actual_label == "fraud") / len(reviewed)
                
                performance.append({
                    'publisher_id': publisher_id,
                    'total_samples': len(samples),
                    'reviewed_samples': len(reviewed),
                    'avg_fraud_score': float(avg_score),
                    'confirmed_fraud_rate': float(fraud_rate)
                })
        
        performance.sort(key=lambda x: -x['confirmed_fraud_rate'])
        return performance

    def export_samples_json(self, status: str = None) -> str:
        if status:
            samples = [s for s in self.samples.values() if s.review_status == status]
        else:
            samples = list(self.samples.values())
        
        return json.dumps(
            [asdict(s) for s in samples], 
            ensure_ascii=False, 
            indent=2,
            default=str
        )

    def import_samples_json(self, json_str: str) -> int:
        data = json.loads(json_str)
        count = 0
        
        for item in data:
            sample = ReviewSample(**item)
            self.samples[sample.sample_id] = sample
            self.ip_to_samples[sample.ip].append(sample.sample_id)
            self.publisher_to_samples[sample.publisher_id].append(sample.sample_id)
            count += 1
        
        return count

    def cleanup_old_samples(self, days: int = 7):
        cutoff = time.time() - days * 86400
        old_ids = [sid for sid, s in self.samples.items() if s.timestamp < cutoff]
        
        for sid in old_ids:
            sample = self.samples[sid]
            del self.samples[sid]
            
            if sample.ip in self.ip_to_samples:
                if sid in self.ip_to_samples[sample.ip]:
                    self.ip_to_samples[sample.ip].remove(sid)
            
            if sample.publisher_id in self.publisher_to_samples:
                if sid in self.publisher_to_samples[sample.publisher_id]:
                    self.publisher_to_samples[sample.publisher_id].remove(sid)
        
        return len(old_ids)

    def get_dashboard_data(self) -> Dict[str, Any]:
        stats = self.calculate_statistics()
        
        last_24h = time.time() - 86400
        recent_samples = [s for s in self.samples.values() if s.timestamp >= last_24h]
        
        score_distribution = {
            '0-0.2': sum(1 for s in self.samples.values() if 0 <= s.fraud_score < 0.2),
            '0.2-0.4': sum(1 for s in self.samples.values() if 0.2 <= s.fraud_score < 0.4),
            '0.4-0.6': sum(1 for s in self.samples.values() if 0.4 <= s.fraud_score < 0.6),
            '0.6-0.8': sum(1 for s in self.samples.values() if 0.6 <= s.fraud_score < 0.8),
            '0.8-1.0': sum(1 for s in self.samples.values() if 0.8 <= s.fraud_score <= 1.0)
        }
        
        return {
            'statistics': asdict(stats),
            'recent_samples': len(recent_samples),
            'pending_count': stats.pending_samples,
            'score_distribution': score_distribution,
            'top_suspicious_ips': self.get_suspicious_ips(2)[:10],
            'top_publishers': self.get_publisher_performance()[:10]
        }
