import uuid
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum


class EventType(Enum):
    COMMENT_POSTED = 'comment_posted'
    COMMENT_LIKED = 'comment_liked'
    COMMENT_REPORTED = 'comment_reported'
    REPORT_VERIFIED = 'report_verified'
    REPORT_REJECTED = 'report_rejected'
    COMMENT_DELETED = 'comment_deleted'
    USER_VERIFIED = 'user_verified'
    LEVEL_UPGRADED = 'level_upgraded'
    INFRACTION_ISSUED = 'infraction_issued'
    APPEAL_GRANTED = 'appeal_granted'


class EventSeverity(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class ReputationEvent:
    event_id: str
    event_type: EventType
    user_id: str
    timestamp: datetime
    severity: EventSeverity
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    reputation_impact: float = 0.0
    event_source: str = 'system'


@dataclass
class EventProcessingResult:
    success: bool
    old_reputation: float
    new_reputation: float
    change_amount: float
    reason: str
    event: ReputationEvent


@dataclass
class EventLogEntry:
    event_id: str
    event_type: str
    user_id: str
    timestamp: str
    severity: str
    reputation_impact: float
    metadata: Dict
    processed: bool


class EventDrivenReputationSystem:
    def __init__(self):
        self.event_handlers: Dict[EventType, Callable] = {}
        self.event_queue: deque = deque()
        self.event_history: List[ReputationEvent] = []
        self.user_event_counts: Dict[str, Dict[EventType, int]] = defaultdict(lambda: defaultdict(int))
        self.user_reputation_cache: Dict[str, float] = {}
        self.cooldown_periods: Dict[str, Dict[EventType, float]] = defaultdict(dict)
        self._init_event_handlers()
        self._init_severity_weights()
        self._init_cooldown_config()
    
    def _init_event_handlers(self):
        self.event_handlers = {
            EventType.COMMENT_POSTED: self._handle_comment_posted,
            EventType.COMMENT_LIKED: self._handle_comment_liked,
            EventType.COMMENT_REPORTED: self._handle_comment_reported,
            EventType.REPORT_VERIFIED: self._handle_report_verified,
            EventType.REPORT_REJECTED: self._handle_report_rejected,
            EventType.COMMENT_DELETED: self._handle_comment_deleted,
            EventType.USER_VERIFIED: self._handle_user_verified,
            EventType.LEVEL_UPGRADED: self._handle_level_upgraded,
            EventType.INFRACTION_ISSUED: self._handle_infraction_issued,
            EventType.APPEAL_GRANTED: self._handle_appeal_granted,
        }
    
    def _init_severity_weights(self):
        self.severity_impact = {
            EventSeverity.LOW: 0.01,
            EventSeverity.MEDIUM: 0.05,
            EventSeverity.HIGH: 0.10,
            EventSeverity.CRITICAL: 0.20
        }
        
        self.event_base_impact = {
            EventType.COMMENT_POSTED: 0.005,
            EventType.COMMENT_LIKED: 0.002,
            EventType.COMMENT_REPORTED: -0.02,
            EventType.REPORT_VERIFIED: -0.10,
            EventType.REPORT_REJECTED: 0.02,
            EventType.COMMENT_DELETED: -0.03,
            EventType.USER_VERIFIED: 0.10,
            EventType.LEVEL_UPGRADED: 0.05,
            EventType.INFRACTION_ISSUED: -0.15,
            EventType.APPEAL_GRANTED: 0.05,
        }
    
    def _init_cooldown_config(self):
        self.cooldown_config = {
            EventType.COMMENT_LIKED: {'max_per_hour': 50, 'decay_time': 3600},
            EventType.COMMENT_POSTED: {'max_per_hour': 10, 'decay_time': 3600},
            EventType.COMMENT_REPORTED: {'max_per_hour': 5, 'decay_time': 7200},
        }
    
    def create_event(
        self,
        event_type: EventType,
        user_id: str,
        severity: EventSeverity = EventSeverity.MEDIUM,
        metadata: Optional[Dict] = None,
        event_source: str = 'system'
    ) -> ReputationEvent:
        event = ReputationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.now(),
            severity=severity,
            metadata=metadata or {},
            event_source=event_source
        )
        return event
    
    def queue_event(self, event: ReputationEvent) -> str:
        self.event_queue.append(event)
        return event.event_id
    
    def process_event(self, event: ReputationEvent, current_reputation: float) -> EventProcessingResult:
        if event.processed:
            return EventProcessingResult(
                success=False,
                old_reputation=current_reputation,
                new_reputation=current_reputation,
                change_amount=0,
                reason='事件已处理',
                event=event
            )
        
        if self._is_in_cooldown(event):
            return EventProcessingResult(
                success=False,
                old_reputation=current_reputation,
                new_reputation=current_reputation,
                change_amount=0,
                reason='事件处于冷却期，暂不处理',
                event=event
            )
        
        handler = self.event_handlers.get(event.event_type)
        if not handler:
            return EventProcessingResult(
                success=False,
                old_reputation=current_reputation,
                new_reputation=current_reputation,
                change_amount=0,
                reason=f'未找到事件类型 {event.event_type} 的处理器',
                event=event
            )
        
        old_reputation = current_reputation
        impact, reason = handler(event)
        
        history_events = self._get_user_events(event.user_id, event.event_type, limit=10)
        impact = self._apply_diminishing_returns(impact, len(history_events))
        impact = self._apply_severity_modifier(impact, event.severity)
        
        new_reputation = max(0.0, min(1.0, old_reputation + impact))
        actual_change = new_reputation - old_reputation
        
        event.processed = True
        event.reputation_impact = actual_change
        
        self.event_history.append(event)
        self.user_event_counts[event.user_id][event.event_type] += 1
        self.user_reputation_cache[event.user_id] = new_reputation
        self._update_cooldown(event)
        
        return EventProcessingResult(
            success=True,
            old_reputation=round(old_reputation, 4),
            new_reputation=round(new_reputation, 4),
            change_amount=round(actual_change, 4),
            reason=reason,
            event=event
        )
    
    def process_queue(self, user_reputation_getter: Callable[[str], float]) -> List[EventProcessingResult]:
        results = []
        while self.event_queue:
            event = self.event_queue.popleft()
            current_rep = user_reputation_getter(event.user_id)
            result = self.process_event(event, current_rep)
            results.append(result)
        return results
    
    def _handle_comment_posted(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.COMMENT_POSTED]
        metadata = event.metadata
        
        text_quality = metadata.get('text_quality', 0.5)
        quality_multiplier = 0.5 + text_quality
        
        impact = base_impact * quality_multiplier
        
        if metadata.get('is_quality_review', False):
            impact *= 1.5
            reason = f'发布高质量评论，信誉 +{impact:.4f}'
        else:
            reason = f'发布评论，信誉 +{impact:.4f}'
        
        return impact, reason
    
    def _handle_comment_liked(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.COMMENT_LIKED]
        metadata = event.metadata
        
        like_count = metadata.get('like_count', 1)
        is_high_quality = metadata.get('is_high_quality_content', False)
        
        multiplier = 1.0
        if like_count >= 100:
            multiplier = 3.0
        elif like_count >= 50:
            multiplier = 2.0
        elif like_count >= 10:
            multiplier = 1.5
        
        if is_high_quality:
            multiplier *= 1.5
        
        impact = base_impact * multiplier * min(like_count, 10) / 10.0
        
        reason = f'评论获得{like_count}个点赞，信誉 +{impact:.4f}'
        return impact, reason
    
    def _handle_comment_reported(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.COMMENT_REPORTED]
        metadata = event.metadata
        
        report_count = metadata.get('report_count', 1)
        report_reason = metadata.get('report_reason', 'unknown')
        
        reason_multipliers = {
            'spam': 1.5,
            'abuse': 2.0,
            'fake': 2.5,
            'copyright': 1.8,
            'other': 1.0
        }
        
        multiplier = reason_multipliers.get(report_reason, 1.0)
        impact = base_impact * multiplier * min(report_count, 5) / 5.0
        
        reason = f'评论被举报（原因：{report_reason}），信誉 {impact:.4f}'
        return impact, reason
    
    def _handle_report_verified(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.REPORT_VERIFIED]
        metadata = event.metadata
        
        violation_type = metadata.get('violation_type', 'unknown')
        is_first_offense = metadata.get('is_first_offense', True)
        has_prior_records = metadata.get('has_prior_records', False)
        
        multiplier = 1.0
        if violation_type == 'fake_review':
            multiplier = 2.0
        elif violation_type == 'harassment':
            multiplier = 1.8
        elif violation_type == 'spam':
            multiplier = 1.5
        
        if not is_first_offense or has_prior_records:
            multiplier *= 1.5
        
        impact = base_impact * multiplier
        
        reason = f'举报核实，违规类型：{violation_type}，信誉 {impact:.4f}'
        return impact, reason
    
    def _handle_report_rejected(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.REPORT_REJECTED]
        metadata = event.metadata
        
        is_false_report = metadata.get('is_false_report', False)
        
        impact = base_impact
        if is_false_report:
            impact *= 0.5
        
        reason = f'举报被驳回，信誉恢复 +{impact:.4f}'
        return impact, reason
    
    def _handle_comment_deleted(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.COMMENT_DELETED]
        metadata = event.metadata
        
        delete_reason = metadata.get('delete_reason', 'user_deleted')
        
        if delete_reason == 'violation':
            impact = base_impact * 2.0
        elif delete_reason == 'user_deleted':
            impact = base_impact * 0.5
        else:
            impact = base_impact
        
        reason = f'评论被删除（原因：{delete_reason}），信誉 {impact:.4f}'
        return impact, reason
    
    def _handle_user_verified(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.USER_VERIFIED]
        metadata = event.metadata
        
        verification_type = metadata.get('verification_type', 'identity')
        
        type_multipliers = {
            'identity': 1.0,
            'enterprise': 1.5,
            'expert': 2.0
        }
        
        multiplier = type_multipliers.get(verification_type, 1.0)
        impact = base_impact * multiplier
        
        reason = f'用户完成{verification_type}认证，信誉 +{impact:.4f}'
        return impact, reason
    
    def _handle_level_upgraded(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.LEVEL_UPGRADED]
        metadata = event.metadata
        
        old_level = metadata.get('old_level', 1)
        new_level = metadata.get('new_level', 2)
        level_diff = max(1, new_level - old_level)
        
        impact = base_impact * level_diff
        
        reason = f'用户等级从 Lv.{old_level} 升级到 Lv.{new_level}，信誉 +{impact:.4f}'
        return impact, reason
    
    def _handle_infraction_issued(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.INFRACTION_ISSUED]
        metadata = event.metadata
        
        infraction_type = metadata.get('infraction_type', 'warning')
        infraction_level = metadata.get('infraction_level', 1)
        
        type_multipliers = {
            'warning': 0.5,
            'temporary_ban': 1.0,
            'permanent_ban': 3.0
        }
        
        multiplier = type_multipliers.get(infraction_type, 1.0) * infraction_level
        impact = base_impact * multiplier
        
        reason = f'收到违规处罚（{infraction_type}，等级{infraction_level}），信誉 {impact:.4f}'
        return impact, reason
    
    def _handle_appeal_granted(self, event: ReputationEvent) -> Tuple[float, str]:
        base_impact = self.event_base_impact[EventType.APPEAL_GRANTED]
        metadata = event.metadata
        
        original_impact = abs(metadata.get('original_impact', 0.0))
        restore_percentage = metadata.get('restore_percentage', 0.5)
        
        impact = max(base_impact, original_impact * restore_percentage)
        
        reason = f'申诉成功，恢复信誉 +{impact:.4f}'
        return impact, reason
    
    def _apply_diminishing_returns(self, impact: float, event_count: int) -> float:
        if event_count == 0:
            return impact
        
        decay_factor = 1.0 / (1.0 + 0.1 * event_count)
        return impact * decay_factor
    
    def _apply_severity_modifier(self, impact: float, severity: EventSeverity) -> float:
        severity_modifier = self.severity_impact.get(severity, 1.0)
        
        if impact >= 0:
            return impact * (1 + severity_modifier)
        else:
            return impact * (1 + severity_modifier)
    
    def _is_in_cooldown(self, event: ReputationEvent) -> bool:
        config = self.cooldown_config.get(event.event_type)
        if not config:
            return False
        
        now = time.time()
        last_event_time = self.cooldown_periods.get(event.user_id, {}).get(event.event_type, 0)
        time_since_last = now - last_event_time
        
        if time_since_last < 60:
            recent_events = [
                e for e in self.event_history
                if e.user_id == event.user_id 
                and e.event_type == event.event_type
                and (now - e.timestamp.timestamp()) < config['decay_time']
            ]
            
            if len(recent_events) >= config['max_per_hour']:
                return True
        
        return False
    
    def _update_cooldown(self, event: ReputationEvent):
        if event.event_type in self.cooldown_config:
            self.cooldown_periods[event.user_id][event.event_type] = time.time()
    
    def _get_user_events(self, user_id: str, event_type: Optional[EventType] = None, limit: int = 10) -> List[ReputationEvent]:
        events = [e for e in reversed(self.event_history) if e.user_id == user_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[:limit]
    
    def get_user_event_summary(self, user_id: str) -> Dict:
        event_counts = self.user_event_counts.get(user_id, {})
        recent_events = self._get_user_events(user_id, limit=20)
        
        return {
            'total_events': sum(event_counts.values()),
            'event_type_counts': {k.value: v for k, v in event_counts.items()},
            'recent_events': [
                {
                    'event_id': e.event_id,
                    'event_type': e.event_type.value,
                    'timestamp': e.timestamp.isoformat(),
                    'severity': e.severity.value,
                    'impact': e.reputation_impact
                }
                for e in recent_events
            ],
            'current_reputation': self.user_reputation_cache.get(user_id, 0.5)
        }
    
    def export_event_log(self, file_path: str, user_id: Optional[str] = None):
        events_to_export = self.event_history
        if user_id:
            events_to_export = [e for e in events_to_export if e.user_id == user_id]
        
        log_entries = []
        for event in events_to_export:
            log_entries.append({
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'user_id': event.user_id,
                'timestamp': event.timestamp.isoformat(),
                'severity': event.severity.value,
                'metadata': event.metadata,
                'processed': event.processed,
                'reputation_impact': event.reputation_impact,
                'event_source': event.event_source
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(log_entries, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def get_audit_trail(self, user_id: str, start_time: Optional[datetime] = None, 
                       end_time: Optional[datetime] = None) -> List[Dict]:
        events = self._get_user_events(user_id, limit=100)
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        audit_trail = []
        running_rep = self.user_reputation_cache.get(user_id, 0.5)
        
        for event in reversed(events):
            prev_rep = running_rep - event.reputation_impact
            audit_trail.append({
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type.value,
                'severity': event.severity.value,
                'old_reputation': round(prev_rep, 4),
                'change': round(event.reputation_impact, 4),
                'new_reputation': round(running_rep, 4),
                'metadata': event.metadata,
                'event_id': event.event_id
            })
            running_rep = prev_rep
        
        return audit_trail
    
    def simulate_event_impact(self, event: ReputationEvent, current_reputation: float) -> EventProcessingResult:
        original_processed = event.processed
        event.processed = False
        
        result = self.process_event(event, current_reputation)
        
        self.event_history.remove(event)
        self.user_event_counts[event.user_id][event.event_type] -= 1
        self.user_reputation_cache[event.user_id] = current_reputation
        event.processed = original_processed
        
        return result
