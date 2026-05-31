import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os
import threading
import time
from enum import Enum


class ScheduleStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class CoverVariant:
    def __init__(self, variant_id: str, frame_index: int,
                 image_data: Optional[np.ndarray] = None,
                 title: str = "", style: str = "modern",
                 predicted_ctr: float = 0.0):
        self.variant_id = variant_id
        self.frame_index = frame_index
        self.image_data = image_data
        self.title = title
        self.style = style
        self.predicted_ctr = predicted_ctr
        self.actual_ctr = 0.0
        self.impressions = 0
        self.clicks = 0
        self.conversions = 0
        self.published_at: Optional[datetime] = None
        self.unpublished_at: Optional[datetime] = None
        self.is_active = False

    def to_dict(self) -> Dict:
        return {
            "variant_id": self.variant_id,
            "frame_index": self.frame_index,
            "title": self.title,
            "style": self.style,
            "predicted_ctr": self.predicted_ctr,
            "actual_ctr": self.actual_ctr,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "is_active": self.is_active,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class ScheduleConfig:
    test_id: str = ""
    interval_hours: float = 24.0
    max_rotations: int = 10
    auto_switch_threshold: float = 0.02
    min_impressions_before_switch: int = 500
    warmup_hours: float = 2.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ScheduleStatus = ScheduleStatus.PENDING


class CoverScheduler:
    def __init__(self):
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.variants: Dict[str, List[CoverVariant]] = {}
        self.performance_log: Dict[str, List[Dict]] = {}
        self.current_variant: Dict[str, Optional[str]] = {}
        self.rotation_count: Dict[str, int] = {}
        self._timer_threads: Dict[str, Optional[threading.Thread]] = {}
        self._stop_events: Dict[str, threading.Event] = {}

    def create_schedule(self, test_id: str,
                        variants: List[CoverVariant],
                        config: Optional[ScheduleConfig] = None) -> Dict:
        if config is None:
            config = ScheduleConfig(test_id=test_id)

        if config.start_time is None:
            config.start_time = datetime.now()

        self.schedules[test_id] = config
        self.variants[test_id] = variants
        self.performance_log[test_id] = []
        self.rotation_count[test_id] = 0
        self.current_variant[test_id] = None

        sorted_variants = sorted(variants, key=lambda v: v.predicted_ctr, reverse=True)
        best = sorted_variants[0]
        best.is_active = True
        best.published_at = datetime.now()
        self.current_variant[test_id] = best.variant_id

        return {
            "test_id": test_id,
            "status": config.status.value,
            "num_variants": len(variants),
            "initial_variant": best.variant_id,
            "initial_predicted_ctr": best.predicted_ctr,
            "interval_hours": config.interval_hours,
            "max_rotations": config.max_rotations,
        }

    def start_schedule(self, test_id: str) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        config = self.schedules[test_id]
        config.status = ScheduleStatus.ACTIVE
        config.start_time = datetime.now()

        self._stop_events[test_id] = threading.Event()
        thread = threading.Thread(
            target=self._schedule_loop,
            args=(test_id,),
            daemon=True,
        )
        thread.start()
        self._timer_threads[test_id] = thread

        return {
            "test_id": test_id,
            "status": "active",
            "started_at": config.start_time.isoformat(),
            "next_rotation": (
                config.start_time + timedelta(hours=config.interval_hours)
            ).isoformat(),
        }

    def pause_schedule(self, test_id: str) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        self.schedules[test_id].status = ScheduleStatus.PAUSED
        if test_id in self._stop_events:
            self._stop_events[test_id].set()

        return {"test_id": test_id, "status": "paused"}

    def resume_schedule(self, test_id: str) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        return self.start_schedule(test_id)

    def stop_schedule(self, test_id: str) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        self.schedules[test_id].status = ScheduleStatus.COMPLETED
        if test_id in self._stop_events:
            self._stop_events[test_id].set()

        if test_id in self.current_variant and self.current_variant[test_id]:
            for v in self.variants[test_id]:
                if v.variant_id == self.current_variant[test_id]:
                    v.is_active = False
                    v.unpublished_at = datetime.now()

        return {"test_id": test_id, "status": "completed"}

    def _schedule_loop(self, test_id: str):
        config = self.schedules.get(test_id)
        if not config:
            return

        stop_event = self._stop_events.get(test_id)
        if not stop_event:
            return

        interval_seconds = config.interval_hours * 3600

        while not stop_event.is_set():
            stop_event.wait(timeout=interval_seconds)

            if stop_event.is_set():
                break

            if config.status != ScheduleStatus.ACTIVE:
                break

            self._perform_rotation(test_id)

    def _perform_rotation(self, test_id: str):
        config = self.schedules.get(test_id)
        variants = self.variants.get(test_id, [])

        if not config or not variants:
            return

        current_vid = self.current_variant.get(test_id)
        current_variant = None
        for v in variants:
            if v.variant_id == current_vid:
                current_variant = v
                break

        if current_variant and current_variant.impressions >= config.min_impressions_before_switch:
            other_variants = [v for v in variants if v.variant_id != current_vid and v.impressions >= config.min_impressions_before_switch]

            if other_variants:
                best_other = max(other_variants, key=lambda v: v.actual_ctr)

                if best_other.actual_ctr > current_variant.actual_ctr + config.auto_switch_threshold:
                    current_variant.is_active = False
                    current_variant.unpublished_at = datetime.now()

                    best_other.is_active = True
                    best_other.published_at = datetime.now()
                    self.current_variant[test_id] = best_other.variant_id

                    self._log_rotation(test_id, current_variant, best_other, "auto_switch")

        self.rotation_count[test_id] = self.rotation_count.get(test_id, 0) + 1

        if self.rotation_count[test_id] >= config.max_rotations:
            config.status = ScheduleStatus.COMPLETED

        self._record_performance(test_id)

    def _log_rotation(self, test_id: str, from_variant: CoverVariant,
                      to_variant: CoverVariant, reason: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "rotation",
            "from_variant": from_variant.variant_id,
            "to_variant": to_variant.variant_id,
            "from_ctr": from_variant.actual_ctr,
            "to_ctr": to_variant.actual_ctr,
            "from_impressions": from_variant.impressions,
            "reason": reason,
        }
        self.performance_log.setdefault(test_id, []).append(entry)

    def _record_performance(self, test_id: str):
        variants = self.variants.get(test_id, [])
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "performance_snapshot",
            "variants": {v.variant_id: v.to_dict() for v in variants},
            "current_variant": self.current_variant.get(test_id),
            "rotation_count": self.rotation_count.get(test_id, 0),
        }
        self.performance_log.setdefault(test_id, []).append(entry)

    def update_metrics(self, test_id: str, variant_id: str,
                       impressions: int = 0, clicks: int = 0,
                       conversions: int = 0):
        variants = self.variants.get(test_id, [])
        for v in variants:
            if v.variant_id == variant_id:
                v.impressions += impressions
                v.clicks += clicks
                v.conversions += conversions
                if v.impressions > 0:
                    v.actual_ctr = v.clicks / v.impressions
                break

    def simulate_performance(self, test_id: str,
                             hours: float = 168.0,
                             base_impressions_per_hour: int = 100) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        config = self.schedules[test_id]
        variants = self.variants[test_id]

        total_hours = int(hours)
        snapshots = []

        for hour in range(total_hours):
            for v in variants:
                imp = np.random.poisson(base_impressions_per_hour / len(variants))
                effective_ctr = v.predicted_ctr * (0.8 + np.random.random() * 0.4)
                clk = np.random.binomial(imp, effective_ctr)
                conv = np.random.binomial(clk, 0.3) if clk > 0 else 0

                v.impressions += imp
                v.clicks += clk
                v.conversions += conv
                v.actual_ctr = v.clicks / v.impressions if v.impressions > 0 else 0

            if hour > 0 and hour % int(config.interval_hours) == 0:
                current_vid = self.current_variant.get(test_id)
                current_v = None
                for v in variants:
                    if v.variant_id == current_vid:
                        current_v = v
                        break

                if current_v and current_v.impressions >= config.min_impressions_before_switch:
                    best = max(variants, key=lambda v: v.actual_ctr)
                    if best.actual_ctr > current_v.actual_ctr + config.auto_switch_threshold:
                        current_v.is_active = False
                        current_v.unpublished_at = datetime.now()
                        best.is_active = True
                        best.published_at = datetime.now()
                        self.current_variant[test_id] = best.variant_id
                        self.rotation_count[test_id] = self.rotation_count.get(test_id, 0) + 1

                        self._log_rotation(test_id, current_v, best, "auto_switch")

            if hour % 12 == 0 or hour == total_hours - 1:
                snapshots.append({
                    "hour": hour,
                    "timestamp": (datetime.now() + timedelta(hours=hour)).isoformat(),
                    "variants": {v.variant_id: v.to_dict() for v in variants},
                    "current_variant": self.current_variant.get(test_id),
                })

        final_ranking = sorted(variants, key=lambda v: v.actual_ctr, reverse=True)
        winner = final_ranking[0]

        return {
            "test_id": test_id,
            "simulated_hours": total_hours,
            "total_snapshots": len(snapshots),
            "snapshots": snapshots,
            "winner": {
                "variant_id": winner.variant_id,
                "predicted_ctr": winner.predicted_ctr,
                "actual_ctr": winner.actual_ctr,
                "total_impressions": winner.impressions,
                "total_clicks": winner.clicks,
            },
            "final_ranking": [
                {
                    "variant_id": v.variant_id,
                    "predicted_ctr": v.predicted_ctr,
                    "actual_ctr": v.actual_ctr,
                    "impressions": v.impressions,
                    "clicks": v.clicks,
                }
                for v in final_ranking
            ],
            "rotation_count": self.rotation_count.get(test_id, 0),
        }

    def get_schedule_status(self, test_id: str) -> Dict:
        if test_id not in self.schedules:
            return {"error": "测试不存在"}

        config = self.schedules[test_id]
        variants = self.variants.get(test_id, [])
        current_vid = self.current_variant.get(test_id)

        current_v = None
        for v in variants:
            if v.variant_id == current_vid:
                current_v = v
                break

        return {
            "test_id": test_id,
            "status": config.status.value,
            "rotation_count": self.rotation_count.get(test_id, 0),
            "max_rotations": config.max_rotations,
            "interval_hours": config.interval_hours,
            "current_variant": current_v.to_dict() if current_v else None,
            "all_variants": [v.to_dict() for v in variants],
            "start_time": config.start_time.isoformat() if config.start_time else None,
        }

    def reset_schedule(self, test_id: str):
        if test_id in self._stop_events:
            self._stop_events[test_id].set()

        if test_id in self.schedules:
            del self.schedules[test_id]
        if test_id in self.variants:
            del self.variants[test_id]
        if test_id in self.performance_log:
            del self.performance_log[test_id]
        if test_id in self.current_variant:
            del self.current_variant[test_id]
        if test_id in self.rotation_count:
            del self.rotation_count[test_id]

    def get_performance_log(self, test_id: str) -> List[Dict]:
        return self.performance_log.get(test_id, [])
