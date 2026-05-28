import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import json
import os

class IncidentStatus(Enum):
    OPEN = 'open'
    ACKNOWLEDGED = 'acknowledged'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class IncidentPriority(Enum):
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

@dataclass
class ActionLog:
    timestamp: datetime
    action_type: str
    description: str
    user: str
    details: Dict[str, Any] = None

@dataclass
class EffectFeedback:
    timestamp: datetime
    metric: str
    before_value: float
    after_value: float
    improvement_pct: float
    is_effective: bool

@dataclass
class Incident:
    incident_id: str
    start_time: datetime
    status: IncidentStatus
    priority: IncidentPriority
    title: str
    description: str
    affected_metrics: List[str]
    root_cause: str = None
    end_time: datetime = None
    assignee: str = None
    action_logs: List[ActionLog] = None
    effect_feedbacks: List[EffectFeedback] = None
    resolution_notes: str = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        self.created_at = self.created_at or datetime.now()
        self.updated_at = self.updated_at or datetime.now()
        self.action_logs = self.action_logs or []
        self.effect_feedbacks = self.effect_feedbacks or []

class IncidentManager:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.incidents = {}
        self._load_from_storage()
        
    def _load_from_storage(self):
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for incident_data in data:
                    incident = self._dict_to_incident(incident_data)
                    self.incidents[incident.incident_id] = incident
        except Exception as e:
            print(f"Error loading incidents: {e}")
    
    def _save_to_storage(self):
        if not self.storage_path:
            return
        
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = [self._incident_to_dict(i) for i in self.incidents.values()]
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving incidents: {e}")
    
    def _incident_to_dict(self, incident: Incident) -> Dict:
        return {
            'incident_id': incident.incident_id,
            'start_time': incident.start_time.isoformat(),
            'status': incident.status.value,
            'priority': incident.priority.value,
            'title': incident.title,
            'description': incident.description,
            'affected_metrics': incident.affected_metrics,
            'root_cause': incident.root_cause,
            'end_time': incident.end_time.isoformat() if incident.end_time else None,
            'assignee': incident.assignee,
            'action_logs': [
                {
                    'timestamp': log.timestamp.isoformat(),
                    'action_type': log.action_type,
                    'description': log.description,
                    'user': log.user,
                    'details': log.details
                } for log in incident.action_logs
            ],
            'effect_feedbacks': [
                {
                    'timestamp': fb.timestamp.isoformat(),
                    'metric': fb.metric,
                    'before_value': fb.before_value,
                    'after_value': fb.after_value,
                    'improvement_pct': fb.improvement_pct,
                    'is_effective': fb.is_effective
                } for fb in incident.effect_feedbacks
            ],
            'resolution_notes': incident.resolution_notes,
            'created_at': incident.created_at.isoformat(),
            'updated_at': incident.updated_at.isoformat()
        }
    
    def _dict_to_incident(self, data: Dict) -> Incident:
        return Incident(
            incident_id=data['incident_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            status=IncidentStatus(data['status']),
            priority=IncidentPriority(data['priority']),
            title=data['title'],
            description=data['description'],
            affected_metrics=data['affected_metrics'],
            root_cause=data.get('root_cause'),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            assignee=data.get('assignee'),
            action_logs=[
                ActionLog(
                    timestamp=datetime.fromisoformat(log['timestamp']),
                    action_type=log['action_type'],
                    description=log['description'],
                    user=log['user'],
                    details=log.get('details')
                ) for log in data.get('action_logs', [])
            ],
            effect_feedbacks=[
                EffectFeedback(
                    timestamp=datetime.fromisoformat(fb['timestamp']),
                    metric=fb['metric'],
                    before_value=fb['before_value'],
                    after_value=fb['after_value'],
                    improvement_pct=fb['improvement_pct'],
                    is_effective=fb['is_effective']
                ) for fb in data.get('effect_feedbacks', [])
            ],
            resolution_notes=data.get('resolution_notes'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )
    
    def create_incident_from_anomaly(self, anomaly: Dict, 
                                   title: str = None,
                                   description: str = None) -> Incident:
        incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"
        
        metrics = list(anomaly.get('metrics', {}).keys())
        score = anomaly.get('total_score', 0)
        
        if score >= 0.7:
            priority = IncidentPriority.CRITICAL
        elif score >= 0.4:
            priority = IncidentPriority.HIGH
        elif score >= 0.2:
            priority = IncidentPriority.MEDIUM
        else:
            priority = IncidentPriority.LOW
        
        root_cause = None
        if 'most_probable_root_cause' in anomaly:
            cause = anomaly['most_probable_root_cause']
            root_cause = cause.get('cause', cause.get('cause_type', ''))
        
        if not title:
            title = f"异常事件 - {', '.join(metrics)} - {anomaly['timestamp'].strftime('%m-%d %H:%M')}"
        
        if not description:
            description = f"检测到异常: 分数={score:.2%}, 指标={', '.join(metrics)}"
        
        incident = Incident(
            incident_id=incident_id,
            start_time=anomaly['timestamp'],
            status=IncidentStatus.OPEN,
            priority=priority,
            title=title,
            description=description,
            affected_metrics=metrics,
            root_cause=root_cause
        )
        
        self.incidents[incident_id] = incident
        self._save_to_storage()
        
        return incident
    
    def acknowledge_incident(self, incident_id: str, user: str) -> Optional[Incident]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.assignee = user
        incident.updated_at = datetime.now()
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type='acknowledge',
            description='事件已确认',
            user=user
        ))
        
        self._save_to_storage()
        return incident
    
    def start_treatment(self, incident_id: str, user: str, 
                      action_description: str) -> Optional[Incident]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.IN_PROGRESS
        incident.updated_at = datetime.now()
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type='treatment_start',
            description=action_description,
            user=user
        ))
        
        self._save_to_storage()
        return incident
    
    def add_action_log(self, incident_id: str, action_type: str,
                      description: str, user: str, 
                      details: Dict = None) -> Optional[Incident]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type=action_type,
            description=description,
            user=user,
            details=details
        ))
        
        incident.updated_at = datetime.now()
        self._save_to_storage()
        return incident
    
    def add_effect_feedback(self, incident_id: str, metric: str,
                          before_value: float, after_value: float,
                          user: str) -> Optional[EffectFeedback]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        improvement_pct = ((before_value - after_value) / before_value * 100) if before_value != 0 else 0
        is_effective = improvement_pct > 20
        
        feedback = EffectFeedback(
            timestamp=datetime.now(),
            metric=metric,
            before_value=before_value,
            after_value=after_value,
            improvement_pct=improvement_pct,
            is_effective=is_effective
        )
        
        incident.effect_feedbacks.append(feedback)
        incident.updated_at = datetime.now()
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type='effect_feedback',
            description=f"{metric}效果反馈: 改善{improvement_pct:.1f}%",
            user=user
        ))
        
        self._save_to_storage()
        return feedback
    
    def resolve_incident(self, incident_id: str, resolution_notes: str,
                       user: str) -> Optional[Incident]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.RESOLVED
        incident.end_time = datetime.now()
        incident.resolution_notes = resolution_notes
        incident.updated_at = datetime.now()
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type='resolve',
            description=f'事件已解决: {resolution_notes}',
            user=user
        ))
        
        self._save_to_storage()
        return incident
    
    def close_incident(self, incident_id: str, user: str) -> Optional[Incident]:
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.CLOSED
        incident.updated_at = datetime.now()
        
        incident.action_logs.append(ActionLog(
            timestamp=datetime.now(),
            action_type='close',
            description='事件已关闭',
            user=user
        ))
        
        self._save_to_storage()
        return incident
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self.incidents.get(incident_id)
    
    def get_all_incidents(self, status: str = None, 
                         priority: str = None) -> List[Incident]:
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status.value == status]
        
        if priority:
            incidents = [i for i in incidents if i.priority.value == priority]
        
        return sorted(incidents, key=lambda x: x.created_at, reverse=True)
    
    def get_incident_summary(self) -> Dict:
        status_counts = {}
        priority_counts = {}
        
        for incident in self.incidents.values():
            status = incident.status.value
            priority = incident.priority.value
            status_counts[status] = status_counts.get(status, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        avg_resolution_time = None
        resolved_incidents = [i for i in self.incidents.values() 
                             if i.end_time]
        if resolved_incidents:
            durations = [(i.end_time - i.start_time).total_seconds() / 3600 
                        for i in resolved_incidents]
            avg_resolution_time = np.mean(durations)
        
        return {
            'total_incidents': len(self.incidents),
            'by_status': status_counts,
            'by_priority': priority_counts,
            'avg_resolution_hours': avg_resolution_time,
            'open_incidents': status_counts.get('open', 0) + 
                             status_counts.get('acknowledged', 0) +
                             status_counts.get('in_progress', 0)
        }
    
    def get_effectiveness_stats(self, incident_id: str = None) -> Dict:
        if incident_id:
            incidents = [self.incidents.get(incident_id)]
            if not incidents[0]:
                return {}
        else:
            incidents = list(self.incidents.values())
        
        all_feedbacks = []
        for incident in incidents:
            all_feedbacks.extend(incident.effect_feedbacks)
        
        if not all_feedbacks:
            return {}
        
        effective_count = sum(1 for fb in all_feedbacks if fb.is_effective)
        avg_improvement = np.mean([fb.improvement_pct for fb in all_feedbacks])
        
        return {
            'total_feedback_count': len(all_feedbacks),
            'effective_count': effective_count,
            'effectiveness_rate': effective_count / len(all_feedbacks),
            'avg_improvement_pct': avg_improvement
        }
    
    def delete_incident(self, incident_id: str) -> bool:
        if incident_id in self.incidents:
            del self.incidents[incident_id]
            self._save_to_storage()
            return True
        return False
