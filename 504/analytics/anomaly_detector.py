import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from enum import Enum


class AnomalyType(Enum):
    SKIP_STEP = "跳步"
    STEP_BACK = "回退"
    LOOP = "循环"
    RARE_TRANSITION = "罕见转移"
    DEAD_END = "死胡同"
    UNUSUAL_START = "异常起点"
    RAPID_EXIT = "快速退出"
    STUCK = "停滞"


ANOMALY_SEVERITY = {
    AnomalyType.SKIP_STEP: "medium",
    AnomalyType.STEP_BACK: "low",
    AnomalyType.LOOP: "high",
    AnomalyType.RARE_TRANSITION: "medium",
    AnomalyType.DEAD_END: "high",
    AnomalyType.UNUSUAL_START: "low",
    AnomalyType.RAPID_EXIT: "high",
    AnomalyType.STUCK: "high"
}

ANOMALY_DESCRIPTION = {
    AnomalyType.SKIP_STEP: "用户跳过了预期的中间步骤，直接到达后续页面",
    AnomalyType.STEP_BACK: "用户回退到之前的步骤，可能表示流程不顺畅",
    AnomalyType.LOOP: "用户在相同步骤间反复循环，表示流程卡住",
    AnomalyType.RARE_TRANSITION: "发生了极低概率的转移，可能是误操作",
    AnomalyType.DEAD_END: "用户到达某个节点后没有后续行为，表示流失",
    AnomalyType.UNUSUAL_START: "用户从非典型入口开始，可能是外部链接引入",
    AnomalyType.RAPID_EXIT: "用户在极短时间内离开，可能是页面加载问题",
    AnomalyType.STUCK: "用户在某个页面停留时间异常长，可能遇到困难"
}


class AnomalyDetector:
    def __init__(self):
        self.normal_transitions = {}
        self.transition_probs = {}
        self.expected_flow = []
        self.event_positions = {}
        self._is_fitted = False

    def fit(self, paths_df: pd.DataFrame, 
            expected_flow: Optional[List[str]] = None) -> 'AnomalyDetector':
        self.transition_counts = defaultdict(Counter)
        self.event_counts = Counter()
        self.start_events = Counter()
        self.end_events = Counter()
        self.path_lengths = []

        for _, row in paths_df.iterrows():
            path = row['path']
            weight = row.get('count', 1)
            events = path.split(' -> ')

            self.start_events[events[0]] += weight
            self.end_events[events[-1]] += weight
            self.path_lengths.append(len(events))

            for event in events:
                self.event_counts[event] += weight

            for i in range(len(events) - 1):
                self.transition_counts[events[i]][events[i + 1]] += weight

        total_transitions = sum(
            sum(targets.values()) for targets in self.transition_counts.values()
        )
        for source, targets in self.transition_counts.items():
            source_total = sum(targets.values())
            self.transition_probs[source] = {
                target: count / source_total 
                for target, count in targets.items()
            }
            for target, count in targets.items():
                self.normal_transitions[(source, target)] = count / total_transitions

        if expected_flow:
            self.expected_flow = expected_flow
            self.event_positions = {
                event: idx for idx, event in enumerate(expected_flow)
            }
        else:
            self._infer_expected_flow()

        self._is_fitted = True
        return self

    def _infer_expected_flow(self):
        sorted_events = sorted(
            self.event_counts.items(), key=lambda x: x[1], reverse=True
        )
        self.expected_flow = [event for event, _ in sorted_events]
        self.event_positions = {
            event: idx for idx, event in enumerate(self.expected_flow)
        }

    def detect_anomalies(self, path: str, path_count: int = 1) -> List[Dict]:
        if not self._is_fitted:
            raise ValueError("模型未训练，请先调用 fit()")

        events = path.split(' -> ')
        anomalies = []

        anomalies.extend(self._detect_skip_steps(events, path_count))
        anomalies.extend(self._detect_step_back(events, path_count))
        anomalies.extend(self._detect_loops(events, path_count))
        anomalies.extend(self._detect_rare_transitions(events, path_count))
        anomalies.extend(self._detect_dead_ends(events, path_count))
        anomalies.extend(self._detect_unusual_start(events, path_count))
        anomalies.extend(self._detect_rapid_exit(events, path_count))

        return anomalies

    def _detect_skip_steps(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []
        if not self.expected_flow or len(self.expected_flow) < 3:
            return anomalies

        for i in range(len(events) - 1):
            source = events[i]
            target = events[i + 1]

            source_pos = self.event_positions.get(source)
            target_pos = self.event_positions.get(target)

            if source_pos is not None and target_pos is not None:
                gap = target_pos - source_pos
                if gap > 1:
                    skipped = self.expected_flow[source_pos + 1:target_pos]
                    anomalies.append({
                        'type': AnomalyType.SKIP_STEP.value,
                        'severity': ANOMALY_SEVERITY[AnomalyType.SKIP_STEP],
                        'description': ANOMALY_DESCRIPTION[AnomalyType.SKIP_STEP],
                        'location': f"{source} -> {target}",
                        'detail': f"跳过了 {gap - 1} 个步骤: {', '.join(skipped)}",
                        'skipped_events': skipped,
                        'gap_size': gap - 1,
                        'occurrence_count': count
                    })

        return anomalies

    def _detect_step_back(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []

        for i in range(len(events) - 1):
            source = events[i]
            target = events[i + 1]

            source_pos = self.event_positions.get(source)
            target_pos = self.event_positions.get(target)

            if source_pos is not None and target_pos is not None:
                if target_pos < source_pos:
                    back_steps = source_pos - target_pos
                    anomalies.append({
                        'type': AnomalyType.STEP_BACK.value,
                        'severity': ANOMALY_SEVERITY[AnomalyType.STEP_BACK],
                        'description': ANOMALY_DESCRIPTION[AnomalyType.STEP_BACK],
                        'location': f"{source} -> {target}",
                        'detail': f"从位置{source_pos}回退到位置{target_pos}，回退了{back_steps}步",
                        'back_steps': back_steps,
                        'occurrence_count': count
                    })

        return anomalies

    def _detect_loops(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []
        seen_sequences = {}

        for window_size in [2, 3]:
            for i in range(len(events) - window_size * 2 + 1):
                seq = tuple(events[i:i + window_size])
                if seq in seen_sequences:
                    continue

                for j in range(i + window_size, len(events) - window_size + 1):
                    later_seq = tuple(events[j:j + window_size])
                    if seq == later_seq:
                        loop_events = events[i:j + window_size]
                        anomalies.append({
                            'type': AnomalyType.LOOP.value,
                            'severity': ANOMALY_SEVERITY[AnomalyType.LOOP],
                            'description': ANOMALY_DESCRIPTION[AnomalyType.LOOP],
                            'location': ' -> '.join(loop_events),
                            'detail': f"检测到循环: {' -> '.join(seq)} 重复出现",
                            'loop_sequence': list(seq),
                            'loop_count': 2,
                            'occurrence_count': count
                        })
                        seen_sequences[seq] = True
                        break

        return anomalies

    def _detect_rare_transitions(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []
        rare_threshold = 0.01

        for i in range(len(events) - 1):
            source = events[i]
            target = events[i + 1]
            key = (source, target)
            prob = self.normal_transitions.get(key, 0)

            if prob < rare_threshold and prob > 0:
                anomalies.append({
                    'type': AnomalyType.RARE_TRANSITION.value,
                    'severity': ANOMALY_SEVERITY[AnomalyType.RARE_TRANSITION],
                    'description': ANOMALY_DESCRIPTION[AnomalyType.RARE_TRANSITION],
                    'location': f"{source} -> {target}",
                    'detail': f"转移概率仅 {prob * 100:.2f}%, 远低于正常水平",
                    'transition_prob': round(prob * 100, 4),
                    'occurrence_count': count
                })

        return anomalies

    def _detect_dead_ends(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []
        last_event = events[-1]

        if last_event not in self.transition_probs or len(self.transition_probs[last_event]) == 0:
            total_starts = sum(self.start_events.values())
            start_rate = self.start_events.get(events[0], 0) / total_starts if total_starts > 0 else 0

            if start_rate > 0.1:
                anomalies.append({
                    'type': AnomalyType.DEAD_END.value,
                    'severity': ANOMALY_SEVERITY[AnomalyType.DEAD_END],
                    'description': ANOMALY_DESCRIPTION[AnomalyType.DEAD_END],
                    'location': last_event,
                    'detail': f"用户在 {last_event} 后无后续行为",
                    'dead_end_event': last_event,
                    'path_length': len(events),
                    'occurrence_count': count
                })

        return anomalies

    def _detect_unusual_start(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []
        if not events:
            return anomalies

        first_event = events[0]
        total_starts = sum(self.start_events.values())
        start_rate = self.start_events.get(first_event, 0) / total_starts if total_starts > 0 else 0

        if start_rate < 0.05 and first_event not in self.expected_flow[:3]:
            anomalies.append({
                'type': AnomalyType.UNUSUAL_START.value,
                'severity': ANOMALY_SEVERITY[AnomalyType.UNUSUAL_START],
                'description': ANOMALY_DESCRIPTION[AnomalyType.UNUSUAL_START],
                'location': first_event,
                'detail': f"起始事件 {first_event} 仅占 {start_rate * 100:.2f}% 的会话",
                'start_rate': round(start_rate * 100, 2),
                'occurrence_count': count
            })

        return anomalies

    def _detect_rapid_exit(self, events: List[str], count: int) -> List[Dict]:
        anomalies = []

        if len(events) <= 2:
            conversion_events = {'purchase', 'checkout_complete', 'order_confirmation'}
            if not any(e in conversion_events for e in events):
                anomalies.append({
                    'type': AnomalyType.RAPID_EXIT.value,
                    'severity': ANOMALY_SEVERITY[AnomalyType.RAPID_EXIT],
                    'description': ANOMALY_DESCRIPTION[AnomalyType.RAPID_EXIT],
                    'location': ' -> '.join(events),
                    'detail': f"用户仅在 {len(events)} 步后即退出，无转化行为",
                    'path_length': len(events),
                    'occurrence_count': count
                })

        return anomalies

    def batch_detect(self, paths_df: pd.DataFrame, 
                      top_n: int = 50) -> pd.DataFrame:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        all_anomalies = []

        for _, row in paths_df.iterrows():
            path = row['path']
            count = row.get('count', 1)
            anomalies = self.detect_anomalies(path, count)
            for anomaly in anomalies:
                anomaly['path'] = path
                all_anomalies.append(anomaly)

        if not all_anomalies:
            return pd.DataFrame()

        df = pd.DataFrame(all_anomalies)

        anomaly_summary = df.groupby(['type', 'severity', 'location', 'detail']).agg({
            'occurrence_count': 'sum',
            'path': 'count'
        }).reset_index()
        anomaly_summary.columns = [
            'anomaly_type', 'severity', 'location', 'detail',
            'total_occurrences', 'affected_paths'
        ]
        anomaly_summary = anomaly_summary.sort_values(
            'total_occurrences', ascending=False
        )

        return anomaly_summary.head(top_n)

    def get_anomaly_heatmap_data(self, paths_df: pd.DataFrame) -> Dict:
        if not self._is_fitted:
            raise ValueError("模型未训练")

        transition_anomaly_scores = {}

        for _, row in paths_df.iterrows():
            path = row['path']
            count = row.get('count', 1)
            events = path.split(' -> ')

            for i in range(len(events) - 1):
                source = events[i]
                target = events[i + 1]
                key = (source, target)

                prob = self.transition_probs.get(source, {}).get(target, 0)
                if prob < 0.05:
                    anomaly_score = 1.0 - prob
                    if key in transition_anomaly_scores:
                        transition_anomaly_scores[key]['score'] = max(
                            transition_anomaly_scores[key]['score'], anomaly_score
                        )
                        transition_anomaly_scores[key]['count'] += count
                    else:
                        transition_anomaly_scores[key] = {
                            'source': source,
                            'target': target,
                            'score': round(anomaly_score, 4),
                            'probability': round(prob * 100, 2),
                            'count': count
                        }

        return transition_anomaly_scores

    def get_anomaly_summary_stats(self, paths_df: pd.DataFrame) -> Dict:
        anomaly_df = self.batch_detect(paths_df, top_n=1000)
        if anomaly_df.empty:
            return {
                'total_anomalies': 0,
                'by_type': {},
                'by_severity': {},
                'top_anomaly': None
            }

        by_type = anomaly_df.groupby('anomaly_type')['total_occurrences'].sum().to_dict()
        by_severity = anomaly_df.groupby('severity')['total_occurrences'].sum().to_dict()
        top_anomaly = anomaly_df.iloc[0].to_dict() if not anomaly_df.empty else None

        return {
            'total_anomalies': int(anomaly_df['total_occurrences'].sum()),
            'unique_anomaly_types': anomaly_df['anomaly_type'].nunique(),
            'by_type': by_type,
            'by_severity': by_severity,
            'top_anomaly': top_anomaly
        }
