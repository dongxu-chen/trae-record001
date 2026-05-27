import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ISRHistoryMonitor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        history_config = config.get('isr_history', {})
        self.enabled = history_config.get('enabled', True)
        self.history_file = history_config.get(
            'history_file', './data/isr_history.json'
        )
        self.retention_days = history_config.get('retention_days', 30)
        self.min_recovery_threshold = history_config.get('min_recovery_seconds', 5)

        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

    def _load_history(self) -> Dict[str, Any]:
        if not os.path.exists(self.history_file):
            return {'shrink_events': [], 'partitions': {}}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'shrink_events' not in data:
                data['shrink_events'] = []
            if 'partitions' not in data:
                data['partitions'] = {}
            return data
        except Exception as e:
            logger.warning(f"Failed to load ISR history file: {e}")
            return {'shrink_events': [], 'partitions': {}}

    def _save_history(self, history: Dict[str, Any]) -> None:
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save ISR history file: {e}")

    def _cleanup_old_events(self, history: Dict[str, Any]) -> None:
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cutoff_ts = cutoff.isoformat()

        original_count = len(history.get('shrink_events', []))
        history['shrink_events'] = [
            e for e in history.get('shrink_events', [])
            if e.get('shrink_time', '') >= cutoff_ts
        ]
        cleaned = original_count - len(history['shrink_events'])
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old ISR history events")

        partitions = history.get('partitions', {})
        to_remove = []
        for key, p_data in partitions.items():
            shrink_time = p_data.get('shrink_time')
            if shrink_time and shrink_time < cutoff_ts:
                to_remove.append(key)
        for key in to_remove:
            del partitions[key]

    def _make_partition_key(self, topic: str, partition: int) -> str:
        return f"{topic}-{partition}"

    def record_isr_status(
        self,
        isr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {'status': 'DISABLED', 'history': {}}

        logger.info("Recording ISR history...")

        history = self._load_history()
        self._cleanup_old_events(history)

        partitions_tracking = history.get('partitions', {})
        shrink_events = history.get('shrink_events', [])

        current_under_replicated = set()
        for topic_issue in isr_result.get('topics_with_issues', []):
            topic = topic_issue.get('topic')
            for partition_info in topic_issue.get('partitions', []):
                p_id = partition_info.get('partition')
                key = self._make_partition_key(topic, p_id)
                current_under_replicated.add(key)

                if key not in partitions_tracking:
                    partitions_tracking[key] = {
                        'topic': topic,
                        'partition': p_id,
                        'shrink_time': datetime.now().isoformat(),
                        'isr_count': partition_info.get('isr_count'),
                        'replica_count': partition_info.get('replica_count'),
                        'replicas': partition_info.get('replicas'),
                        'isr': partition_info.get('isr')
                    }
                    logger.debug(
                        f"Recorded ISR shrink: {topic}-{p_id} "
                        f"(ISR: {partition_info.get('isr_count')}/"
                        f"{partition_info.get('replica_count')})"
                    )

        recovered = []
        for key in list(partitions_tracking.keys()):
            if key not in current_under_replicated:
                p_data = partitions_tracking[key]
                shrink_time_str = p_data.get('shrink_time')
                if shrink_time_str:
                    shrink_time = datetime.fromisoformat(shrink_time_str)
                    recovery_time = datetime.now()
                    duration_seconds = (recovery_time - shrink_time).total_seconds()

                    if duration_seconds >= self.min_recovery_threshold:
                        event = {
                            'topic': p_data.get('topic'),
                            'partition': p_data.get('partition'),
                            'shrink_time': shrink_time_str,
                            'recovery_time': recovery_time.isoformat(),
                            'duration_seconds': round(duration_seconds, 2),
                            'isr_count': p_data.get('isr_count'),
                            'replica_count': p_data.get('replica_count'),
                            'isr': p_data.get('isr'),
                            'replicas': p_data.get('replicas')
                        }
                        shrink_events.append(event)
                        recovered.append(event)

                del partitions_tracking[key]

        history['shrink_events'] = shrink_events
        history['partitions'] = partitions_tracking

        self._save_history(history)

        result = self._build_history_result(
            shrink_events, partitions_tracking, isr_result
        )

        return result

    def _build_history_result(
        self,
        shrink_events: List[Dict[str, Any]],
        active_shrinks: Dict[str, Any],
        isr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = {
            'status': 'HEALTHY',
            'total_shrink_events': len(shrink_events),
            'active_shrinks_count': len(active_shrinks),
            'recent_shrinks': [],
            'longest_recovery': None,
            'average_recovery_seconds': 0,
            'recovery_statistics': {},
            'currently_under_replicated_topics': isr_result.get(
                'topics_with_issues', []
            )
        }

        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)

        recent_events = []
        recovery_durations = []

        for event in shrink_events:
            duration = event.get('duration_seconds', 0)
            recovery_durations.append(duration)

            recovery_time = event.get('recovery_time')
            if recovery_time:
                try:
                    rt = datetime.fromisoformat(recovery_time)
                    if rt >= recent_cutoff:
                        recent_events.append(event)
                except (ValueError, TypeError):
                    pass

        recent_events.sort(
            key=lambda x: x.get('recovery_time', ''),
            reverse=True
        )
        result['recent_shrinks'] = recent_events[:20]

        if recovery_durations:
            result['average_recovery_seconds'] = round(
                sum(recovery_durations) / len(recovery_durations), 2
            )
            result['longest_recovery'] = max(
                shrink_events,
                key=lambda x: x.get('duration_seconds', 0)
            )
            result['recovery_statistics'] = {
                'min_seconds': round(min(recovery_durations), 2),
                'max_seconds': round(max(recovery_durations), 2),
                'avg_seconds': round(
                    sum(recovery_durations) / len(recovery_durations), 2
                ),
                'p50_seconds': self._percentile(recovery_durations, 50),
                'p95_seconds': self._percentile(recovery_durations, 95),
                'p99_seconds': self._percentile(recovery_durations, 99),
                'total_recovery_events': len(recovery_durations)
            }

        if active_shrinks:
            result['status'] = 'WARNING' if len(active_shrinks) < 10 else 'CRITICAL'

        return result

    def _percentile(self, data: List[float], percentile: int) -> float:
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        if f == c:
            return round(sorted_data[f], 2)
        d0 = sorted_data[f] * (c - k)
        d1 = sorted_data[c] * (k - f)
        return round(d0 + d1, 2)

    def get_full_history(self) -> Dict[str, Any]:
        history = self._load_history()
        return history