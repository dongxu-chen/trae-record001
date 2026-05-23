import json
import redis
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from models.content_detector import ContentType, RiskLevel

class ReportPeriod:
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class AuditReportManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True
        )
        self._prefix = "audit:report:"
        self._log_prefix = "audit:log:"
    
    def _get_date_key(self, period: str, dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.now()
        
        if period == ReportPeriod.HOURLY:
            return dt.strftime("%Y-%m-%d-%H")
        elif period == ReportPeriod.DAILY:
            return dt.strftime("%Y-%m-%d")
        elif period == ReportPeriod.WEEKLY:
            return dt.strftime("%Y-%W")
        elif period == ReportPeriod.MONTHLY:
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y-%m-%d")
    
    def record_audit(self, image_id: str, result: Dict, process_time: float) -> None:
        timestamp = datetime.now()
        date_key = self._get_date_key(ReportPeriod.DAILY, timestamp)
        hour_key = self._get_date_key(ReportPeriod.HOURLY, timestamp)
        
        log_entry = {
            "image_id": image_id,
            "timestamp": timestamp.isoformat(),
            "risk_level": result.get("risk_level", "unknown"),
            "main_content": result.get("main_content", "unknown"),
            "confidence": result.get("confidence", 0),
            "process_time": process_time,
            "cached": result.get("cached", False),
            "from_similar": result.get("from_similar", False)
        }
        
        self.redis_client.rpush(
            f"{self._log_prefix}{date_key}",
            json.dumps(log_entry)
        )
        
        self._update_stats(date_key, log_entry)
        self._update_stats(hour_key, log_entry)
    
    def _update_stats(self, key_suffix: str, log_entry: Dict) -> None:
        stats_key = f"{self._prefix}stats:{key_suffix}"
        
        pipe = self.redis_client.pipeline()
        
        pipe.hincrby(stats_key, "total_count", 1)
        
        risk_level = log_entry["risk_level"]
        pipe.hincrby(stats_key, f"risk_{risk_level}", 1)
        
        main_content = log_entry["main_content"]
        pipe.hincrby(stats_key, f"content_{main_content}", 1)
        
        if log_entry["cached"]:
            pipe.hincrby(stats_key, "cached_count", 1)
        if log_entry["from_similar"]:
            pipe.hincrby(stats_key, "similar_count", 1)
        
        pipe.hincrbyfloat(stats_key, "total_process_time", log_entry["process_time"])
        
        pipe.execute()
    
    def record_video_audit(self, video_id: str, result: Dict, process_time: float) -> None:
        timestamp = datetime.now()
        date_key = self._get_date_key(ReportPeriod.DAILY, timestamp)
        
        log_entry = {
            "video_id": video_id,
            "timestamp": timestamp.isoformat(),
            "overall_risk": result.get("overall_risk", "unknown"),
            "violation_count": result.get("violation_count", 0),
            "sampled_frames": result.get("sampled_frames", 0),
            "duration": result.get("duration", 0),
            "process_time": process_time
        }
        
        self.redis_client.rpush(
            f"{self._log_prefix}video:{date_key}",
            json.dumps(log_entry)
        )
        
        stats_key = f"{self._prefix}video_stats:{date_key}"
        pipe = self.redis_client.pipeline()
        pipe.hincrby(stats_key, "total_count", 1)
        pipe.hincrby(stats_key, f"risk_{log_entry['overall_risk']}", 1)
        pipe.hincrbyfloat(stats_key, "total_violations", log_entry["violation_count"])
        pipe.hincrbyfloat(stats_key, "total_duration", log_entry["duration"])
        pipe.execute()
    
    def record_review(self, review_id: str, image_id: str, 
                       original_result: Dict, final_result: Dict,
                       reviewer: str) -> None:
        timestamp = datetime.now()
        date_key = self._get_date_key(ReportPeriod.DAILY, timestamp)
        
        original_risk = original_result.get("risk_level", "unknown")
        final_risk = final_result.get("risk_level", "unknown")
        is_consistent = original_risk == final_risk
        
        log_entry = {
            "review_id": review_id,
            "image_id": image_id,
            "timestamp": timestamp.isoformat(),
            "reviewer": reviewer,
            "original_risk": original_risk,
            "final_risk": final_risk,
            "is_consistent": is_consistent
        }
        
        self.redis_client.rpush(
            f"{self._log_prefix}review:{date_key}",
            json.dumps(log_entry)
        )
        
        stats_key = f"{self._prefix}review_stats:{date_key}"
        pipe = self.redis_client.pipeline()
        pipe.hincrby(stats_key, "total_count", 1)
        if is_consistent:
            pipe.hincrby(stats_key, "consistent_count", 1)
        else:
            pipe.hincrby(stats_key, "inconsistent_count", 1)
        pipe.execute()
    
    def get_content_distribution(self, period: str = ReportPeriod.DAILY, 
                                  date: datetime = None) -> Dict:
        key_suffix = self._get_date_key(period, date)
        stats_key = f"{self._prefix}stats:{key_suffix}"
        
        stats = self.redis_client.hgetall(stats_key)
        
        distribution = {}
        for key, value in stats.items():
            if key.startswith("content_"):
                content_type = key.replace("content_", "")
                distribution[content_type] = int(value)
        
        total = sum(distribution.values())
        percentages = {}
        for content_type, count in distribution.items():
            percentages[content_type] = {
                "count": count,
                "percentage": round(count / max(total, 1) * 100, 2)
            }
        
        return {
            "period": period,
            "date": key_suffix,
            "total": total,
            "distribution": percentages
        }
    
    def get_risk_distribution(self, period: str = ReportPeriod.DAILY,
                               date: datetime = None) -> Dict:
        key_suffix = self._get_date_key(period, date)
        stats_key = f"{self._prefix}stats:{key_suffix}"
        
        stats = self.redis_client.hgetall(stats_key)
        
        distribution = {}
        for key, value in stats.items():
            if key.startswith("risk_"):
                risk_level = key.replace("risk_", "")
                distribution[risk_level] = int(value)
        
        total = sum(distribution.values())
        percentages = {}
        for risk_level, count in distribution.items():
            percentages[risk_level] = {
                "count": count,
                "percentage": round(count / max(total, 1) * 100, 2)
            }
        
        return {
            "period": period,
            "date": key_suffix,
            "total": total,
            "distribution": percentages
        }
    
    def get_audit_performance(self, period: str = ReportPeriod.DAILY,
                               date: datetime = None) -> Dict:
        key_suffix = self._get_date_key(period, date)
        stats_key = f"{self._prefix}stats:{key_suffix}"
        
        stats = self.redis_client.hgetall(stats_key)
        
        total_count = int(stats.get("total_count", 0))
        total_time = float(stats.get("total_process_time", 0))
        cached_count = int(stats.get("cached_count", 0))
        similar_count = int(stats.get("similar_count", 0))
        
        avg_time = total_time / max(total_count, 1)
        cache_hit_rate = cached_count / max(total_count, 1) * 100
        similar_rate = similar_count / max(total_count, 1) * 100
        
        return {
            "period": period,
            "date": key_suffix,
            "total_count": total_count,
            "total_process_time": round(total_time, 3),
            "avg_process_time": round(avg_time, 4),
            "cached_count": cached_count,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "similar_count": similar_count,
            "similar_hit_rate": round(similar_rate, 2)
        }
    
    def get_review_consistency(self, period: str = ReportPeriod.DAILY,
                                date: datetime = None) -> Dict:
        key_suffix = self._get_date_key(period, date)
        stats_key = f"{self._prefix}review_stats:{key_suffix}"
        
        stats = self.redis_client.hgetall(stats_key)
        
        total_count = int(stats.get("total_count", 0))
        consistent_count = int(stats.get("consistent_count", 0))
        inconsistent_count = int(stats.get("inconsistent_count", 0))
        
        consistency_rate = consistent_count / max(total_count, 1) * 100
        
        return {
            "period": period,
            "date": key_suffix,
            "total_reviews": total_count,
            "consistent_count": consistent_count,
            "inconsistent_count": inconsistent_count,
            "consistency_rate": round(consistency_rate, 2)
        }
    
    def get_comprehensive_report(self, period: str = ReportPeriod.DAILY,
                                  date: datetime = None) -> Dict:
        return {
            "content_distribution": self.get_content_distribution(period, date),
            "risk_distribution": self.get_risk_distribution(period, date),
            "performance": self.get_audit_performance(period, date),
            "review_consistency": self.get_review_consistency(period, date)
        }
    
    def get_trend_data(self, days: int = 7) -> Dict:
        trend_data = []
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            key_suffix = self._get_date_key(ReportPeriod.DAILY, date)
            stats_key = f"{self._prefix}stats:{key_suffix}"
            stats = self.redis_client.hgetall(stats_key)
            
            trend_data.append({
                "date": key_suffix,
                "total_count": int(stats.get("total_count", 0)),
                "high_risk_count": int(stats.get("risk_high_risk", 0)),
                "low_risk_count": int(stats.get("risk_low_risk", 0)),
                "avg_process_time": round(
                    float(stats.get("total_process_time", 0)) / 
                    max(int(stats.get("total_count", 0)), 1), 4
                )
            })
        
        return {
            "days": days,
            "trend": list(reversed(trend_data))
        }
    
    def get_top_violations(self, limit: int = 10, 
                            period: str = ReportPeriod.DAILY,
                            date: datetime = None) -> List[Dict]:
        key_suffix = self._get_date_key(period, date)
        log_key = f"{self._log_prefix}{key_suffix}"
        
        logs = self.redis_client.lrange(log_key, 0, -1)
        violation_logs = []
        
        for log_str in logs:
            try:
                log = json.loads(log_str)
                if log.get("risk_level") in [RiskLevel.HIGH_RISK, RiskLevel.LOW_RISK]:
                    violation_logs.append(log)
            except:
                continue
        
        violation_logs.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return violation_logs[:limit]
    
    def export_report(self, period: str = ReportPeriod.DAILY,
                       date: datetime = None, format: str = "json") -> str:
        report = self.get_comprehensive_report(period, date)
        
        if format == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        
        return str(report)

report_manager = AuditReportManager()
