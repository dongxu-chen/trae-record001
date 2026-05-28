import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import uuid

class AnomalyEvent:
    def __init__(self, event_id: str, start_time: datetime):
        self.event_id = event_id
        self.start_time = start_time
        self.end_time = None
        self.anomalies = []
        self.root_cause_hypothesis = None
        self.correlation_score = 0.0
        self.severity = 'LOW'
        self.affected_metrics = set()
        self.detection_methods = set()
        
    def add_anomaly(self, anomaly: Dict):
        self.anomalies.append(anomaly)
        
        if 'metrics' in anomaly:
            self.affected_metrics.update(anomaly['metrics'].keys())
        elif 'metric' in anomaly:
            self.affected_metrics.add(anomaly['metric'])
        
        if 'detected_by' in anomaly:
            self.detection_methods.update(anomaly['detected_by'])
        
        self._update_severity()
        
    def _update_severity(self):
        if not self.anomalies:
            self.severity = 'LOW'
            return
        
        max_score = max(a.get('total_score', 0) for a in self.anomalies)
        
        if max_score >= 0.7:
            self.severity = 'CRITICAL'
        elif max_score >= 0.4:
            self.severity = 'HIGH'
        elif max_score >= 0.2:
            self.severity = 'MEDIUM'
        else:
            self.severity = 'LOW'
    
    def get_duration_minutes(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0
    
    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_minutes': self.get_duration_minutes(),
            'anomaly_count': len(self.anomalies),
            'severity': self.severity,
            'affected_metrics': list(self.affected_metrics),
            'detection_methods': list(self.detection_methods),
            'root_cause_hypothesis': self.root_cause_hypothesis,
            'correlation_score': self.correlation_score
        }

class EventCorrelator:
    def __init__(self, time_window_minutes: int = 30,
                 similarity_threshold: float = 0.6):
        self.time_window = timedelta(minutes=time_window_minutes)
        self.similarity_threshold = similarity_threshold
        
    def correlate_anomalies(self, anomalies: List[Dict]) -> List[AnomalyEvent]:
        if not anomalies:
            return []
        
        sorted_anomalies = sorted(anomalies, key=lambda x: x['timestamp'])
        
        events = []
        current_event = None
        
        for anomaly in sorted_anomalies:
            anomaly_time = anomaly['timestamp']
            
            if not current_event:
                current_event = self._create_new_event(anomaly)
                current_event.add_anomaly(anomaly)
                continue
            
            time_diff = anomaly_time - current_event.start_time
            
            if time_diff <= self.time_window:
                similarity = self._calculate_correlation_similarity(current_event, anomaly)
                
                if similarity >= self.similarity_threshold:
                    current_event.add_anomaly(anomaly)
                    current_event.end_time = anomaly_time
                    current_event.correlation_score = max(
                        current_event.correlation_score, similarity
                    )
                else:
                    events.append(current_event)
                    current_event = self._create_new_event(anomaly)
                    current_event.add_anomaly(anomaly)
            else:
                events.append(current_event)
                current_event = self._create_new_event(anomaly)
                current_event.add_anomaly(anomaly)
        
        if current_event:
            events.append(current_event)
        
        for event in events:
            event.root_cause_hypothesis = self._infer_root_cause(event)
        
        return sorted(events, key=lambda x: x.correlation_score, reverse=True)
    
    def _create_new_event(self, initial_anomaly: Dict) -> AnomalyEvent:
        event_id = str(uuid.uuid4())[:8]
        event = AnomalyEvent(event_id, initial_anomaly['timestamp'])
        event.end_time = initial_anomaly['timestamp']
        return event
    
    def _calculate_correlation_similarity(self, event: AnomalyEvent, 
                                       new_anomaly: Dict) -> float:
        if not event.anomalies:
            return 1.0
        
        similarity = 0.0
        factors = 0
        
        last_anomaly = event.anomalies[-1]
        
        if 'metrics' in last_anomaly and 'metrics' in new_anomaly:
            common_metrics = set(last_anomaly['metrics'].keys()) & set(new_anomaly['metrics'].keys())
            if common_metrics:
                similarity += 0.4
                factors += 1
        
        if 'best_matched_pattern' in last_anomaly and 'best_matched_pattern' in new_anomaly:
            if last_anomaly['best_matched_pattern']['pattern_id'] == new_anomaly['best_matched_pattern']['pattern_id']:
                similarity += 0.3
                factors += 1
        
        if 'detected_by' in last_anomaly and 'detected_by' in new_anomaly:
            common_methods = set(last_anomaly['detected_by']) & set(new_anomaly['detected_by'])
            if common_methods:
                similarity += 0.2
                factors += 1
        
        if 'most_probable_root_cause' in last_anomaly and 'most_probable_root_cause' in new_anomaly:
            if (last_anomaly['most_probable_root_cause'].get('cause') == 
                new_anomaly['most_probable_root_cause'].get('cause')):
                similarity += 0.4
                factors += 1
        
        return min(1.0, similarity / max(factors, 1))
    
    def _infer_root_cause(self, event: AnomalyEvent) -> Dict:
        if len(event.anomalies) < 2:
            return {}
        
        root_cause_votes = defaultdict(float)
        
        for anomaly in event.anomalies:
            if 'most_probable_root_cause' in anomaly:
                cause = anomaly['most_probable_root_cause']
                cause_type = cause.get('cause', cause.get('cause_type', 'unknown'))
                confidence = cause.get('posterior_probability', cause.get('confidence', 0.5))
                root_cause_votes[cause_type] += confidence
            
            if 'best_matched_pattern' in anomaly:
                pattern = anomaly['best_matched_pattern']
                root_cause_votes[pattern['root_cause_hint']] += pattern.get('match_score', 0.5) * 0.7
        
        if root_cause_votes:
            most_likely = max(root_cause_votes.items(), key=lambda x: x[1])[0]
            total_votes = sum(root_cause_votes.values())
            
            return {
                'most_likely_cause': most_likely,
                'confidence': root_cause_votes[most_likely] / total_votes,
                'all_candidates': [
                    {'cause': cause, 'score': score / total_votes}
                    for cause, score in sorted(root_cause_votes.items(), key=lambda x: x[1], reverse=True)
                ]
            }
        
        return {}
    
    def group_by_root_cause(self, events: List[AnomalyEvent]) -> Dict[str, List[AnomalyEvent]]:
        groups = defaultdict(list)
        
        for event in events:
            cause = event.root_cause_hypothesis.get('most_likely_cause', 'unknown')
            groups[cause].append(event)
        
        return dict(groups)
    
    def get_summary(self, events: List[AnomalyEvent]) -> Dict:
        if not events:
            return {}
        
        by_severity = defaultdict(int)
        total_duration = 0
        
        for event in events:
            by_severity[event.severity] += 1
            total_duration += event.get_duration_minutes()
        
        return {
            'total_events': len(events),
            'by_severity': dict(by_severity),
            'average_duration_minutes': total_duration / len(events),
            'total_affected_metrics': len(set().union(*[e.affected_metrics for e in events]))
        }
    
    def merge_similar_events(self, events: List[AnomalyEvent], 
                            max_time_gap_hours: int = 2) -> List[AnomalyEvent]:
        if len(events) < 2:
            return events
        
        sorted_events = sorted(events, key=lambda x: x.start_time)
        
        merged = []
        current_group = [sorted_events[0]]
        
        for event in sorted_events[1:]:
            last_end = current_group[-1].end_time or current_group[-1].start_time
            time_gap = event.start_time - last_end
            
            if time_gap <= timedelta(hours=max_time_gap_hours):
                cause_similarity = self._cause_similarity(current_group[-1], event)
                
                if cause_similarity >= 0.7:
                    current_group.append(event)
                else:
                    merged.append(self._merge_event_group(current_group))
                    current_group = [event]
            else:
                merged.append(self._merge_event_group(current_group))
                current_group = [event]
        
        if current_group:
            merged.append(self._merge_event_group(current_group))
        
        return merged
    
    def _cause_similarity(self, event1: AnomalyEvent, 
                             event2: AnomalyEvent) -> float:
        cause1 = event1.root_cause_hypothesis.get('most_likely_cause', '')
        cause2 = event2.root_cause_hypothesis.get('most_likely_cause', '')
        
        if cause1 == cause2 and cause1 != '':
            return 1.0
        
        metrics1 = event1.affected_metrics
        metrics2 = event2.affected_metrics
        
        if metrics1 & metrics2:
            return len(metrics1 & metrics2) / len(metrics1 | metrics2)
        
        return 0.0
    
    def _merge_event_group(self, group: List[AnomalyEvent]) -> AnomalyEvent:
        if len(group) == 1:
            return group[0]
        
        merged = AnomalyEvent(group[0].event_id, group[0].start_time)
        merged.end_time = group[-1].end_time
        
        for event in group:
            for anomaly in event.anomalies:
                merged.add_anomaly(anomaly)
        
        merged.root_cause_hypothesis = self._infer_root_cause(merged)
        merged.correlation_score = max(e.correlation_score for e in group)
        
        return merged
    
    def find_recurring_patterns(self, events: List[AnomalyEvent], 
                            min_occurrences: int = 3) -> List[Dict]:
        pattern_counts = defaultdict(list)
        
        for event in events:
            cause = event.root_cause_hypothesis.get('most_likely_cause', 'unknown')
            pattern_counts[cause].append(event)
        
        recurring = []
        for cause, event_list in pattern_counts.items():
            if len(event_list) >= min_occurrences:
                recurring.append({
                    'root_cause': cause,
                    'occurrence_count': len(event_list),
                    'events': [e.to_dict() for e in event_list],
                    'average_severity': max(e.severity for e in event_list)
                })
        
        return sorted(recurring, key=lambda x: x['occurrence_count'], reverse=True)
