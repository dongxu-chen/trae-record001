import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> 'RiskLevel':
        if score >= 80:
            return cls.CRITICAL
        elif score >= 60:
            return cls.HIGH
        elif score >= 30:
            return cls.MEDIUM
        else:
            return cls.LOW


class RiskDimension(str, Enum):
    FACE_RECOGNITION = "face_recognition"
    LIVENESS = "liveness"
    SINGLE_FACE = "single_face"
    TAB_SWITCH = "tab_switch"
    FULLSCREEN = "fullscreen"
    MULTI_MONITOR = "multi_monitor"
    AUDIO = "audio"
    SIMILARITY = "similarity"
    BEHAVIOR = "behavior"


@dataclass
class DimensionScore:
    dimension: RiskDimension
    score: float = 0.0
    weight: float = 1.0
    event_count: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'dimension': self.dimension.value,
            'score': self.score,
            'weight': self.weight,
            'event_count': self.event_count,
            'events': self.events[-20:],
            'last_updated': self.last_updated
        }


@dataclass
class RiskReport:
    student_id: str
    exam_id: str
    overall_score: float = 0.0
    level: RiskLevel = RiskLevel.LOW
    dimensions: Dict[RiskDimension, DimensionScore] = field(default_factory=dict)
    needs_review: bool = False
    review_reason: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'overall_score': self.overall_score,
            'level': self.level.value,
            'dimensions': {
                d.value: s.to_dict()
                for d, s in self.dimensions.items()
            },
            'needs_review': self.needs_review,
            'review_reason': self.review_reason,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class RiskScorer:
    def __init__(self):
        self._lock = threading.Lock()
        self._reports: Dict[str, RiskReport] = {}
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._auto_review_threshold = 60.0
        self._critical_threshold = 80.0
        self._medium_threshold = 30.0
        
        self._dimension_weights: Dict[RiskDimension, float] = {
            RiskDimension.FACE_RECOGNITION: 1.2,
            RiskDimension.LIVENESS: 1.3,
            RiskDimension.SINGLE_FACE: 1.5,
            RiskDimension.TAB_SWITCH: 1.0,
            RiskDimension.FULLSCREEN: 0.8,
            RiskDimension.MULTI_MONITOR: 1.2,
            RiskDimension.AUDIO: 1.1,
            RiskDimension.SIMILARITY: 1.4,
            RiskDimension.BEHAVIOR: 1.0,
        }
        
        self._event_scores: Dict[str, float] = {
            'face_mismatch': 25.0,
            'face_not_detected': 15.0,
            'liveness_failed': 30.0,
            'multiple_faces': 35.0,
            'tab_switch': 10.0,
            'excessive_tab_switch': 20.0,
            'fullscreen_detected': 15.0,
            'multi_monitor_detected': 20.0,
            'cross_screen_window': 25.0,
            'speech_detected': 20.0,
            'suspicious_sound': 25.0,
            'high_similarity': 30.0,
            'very_high_similarity': 45.0,
            'multiple_matches': 35.0,
        }

    def _get_key(self, student_id: str, exam_id: str) -> str:
        return f"{student_id}_{exam_id}"

    def _get_or_create_dimension(self, report: RiskReport,
                                 dimension: RiskDimension) -> DimensionScore:
        if dimension not in report.dimensions:
            report.dimensions[dimension] = DimensionScore(
                dimension=dimension,
                weight=self._dimension_weights.get(dimension, 1.0)
            )
        return report.dimensions[dimension]

    def _calculate_overall_score(self, report: RiskReport) -> float:
        if not report.dimensions:
            return 0.0
        total_weight = 0.0
        weighted_sum = 0.0
        for dim_score in report.dimensions.values():
            weighted_sum += dim_score.score * dim_score.weight
            total_weight += dim_score.weight
        if total_weight == 0:
            return 0.0
        return min(100.0, weighted_sum / total_weight)

    def _check_needs_review(self, report: RiskReport) -> Tuple[bool, Optional[str]]:
        if report.overall_score >= self._auto_review_threshold:
            return True, f"综合风险分 {report.overall_score:.1f} 超过自动复核阈值"
        critical_dims = [
            dim for dim, score in report.dimensions.items()
            if score.score >= self._critical_threshold
        ]
        if critical_dims:
            return True, f"高风险维度: {', '.join(d.value for d in critical_dims)}"
        if len(report.dimensions) >= 3:
            high_count = sum(
                1 for s in report.dimensions.values()
                if s.score >= self._medium_threshold
            )
            if high_count >= 3:
                return True, f"多个中高风险维度 ({high_count}个)"
        return False, None

    def create_report(self, student_id: str, exam_id: str) -> RiskReport:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key in self._reports:
                return self._reports[key]
            report = RiskReport(
                student_id=student_id,
                exam_id=exam_id
            )
            self._reports[key] = report
            return report

    def add_event(self, student_id: str, exam_id: str,
                  dimension: RiskDimension, event_type: str,
                  message: str, metadata: Optional[Dict[str, Any]] = None) -> RiskReport:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                self.create_report(student_id, exam_id)
            report = self._reports[key]
            dim_score = self._get_or_create_dimension(report, dimension)
            event_score = self._event_scores.get(event_type, 10.0)
            dim_score.score = min(100.0, dim_score.score + event_score)
            dim_score.event_count += 1
            event = {
                'type': event_type,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            if metadata:
                event.update(metadata)
            dim_score.events.append(event)
            dim_score.last_updated = datetime.now().isoformat()
            report.overall_score = self._calculate_overall_score(report)
            report.level = RiskLevel.from_score(report.overall_score)
            report.updated_at = datetime.now().isoformat()
            needs_review, reason = self._check_needs_review(report)
            report.needs_review = needs_review
            report.review_reason = reason
            self._history[key].append({
                'timestamp': datetime.now().isoformat(),
                'score': report.overall_score,
                'level': report.level.value,
                'event': event_type
            })
            return report

    def update_face_score(self, student_id: str, exam_id: str,
                          face_match: bool, face_detected: bool,
                          liveness_passed: bool, face_count: int) -> RiskReport:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                self.create_report(student_id, exam_id)
            report = self._reports[key]
            if not face_detected:
                return self.add_event(
                    student_id, exam_id,
                    RiskDimension.FACE_RECOGNITION,
                    'face_not_detected',
                    '未检测到人脸',
                    {'face_count': face_count}
                )
            if not face_match:
                return self.add_event(
                    student_id, exam_id,
                    RiskDimension.FACE_RECOGNITION,
                    'face_mismatch',
                    '人脸不匹配',
                    {'face_count': face_count}
                )
            if not liveness_passed:
                return self.add_event(
                    student_id, exam_id,
                    RiskDimension.LIVENESS,
                    'liveness_failed',
                    '活体检测未通过',
                    {}
                )
            if face_count > 1:
                return self.add_event(
                    student_id, exam_id,
                    RiskDimension.SINGLE_FACE,
                    'multiple_faces',
                    f'检测到 {face_count} 张人脸',
                    {'face_count': face_count}
                )
            dim = self._get_or_create_dimension(report, RiskDimension.FACE_RECOGNITION)
            dim.score = max(0.0, dim.score - 2.0)
            return report

    def update_tab_switch_score(self, student_id: str, exam_id: str,
                                switch_count: int, excessive: bool = False) -> RiskReport:
        if excessive:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.TAB_SWITCH,
                'excessive_tab_switch',
                f'频繁切屏，累计 {switch_count} 次',
                {'switch_count': switch_count}
            )
        return self.add_event(
            student_id, exam_id,
            RiskDimension.TAB_SWITCH,
            'tab_switch',
            f'检测到切屏，累计 {switch_count} 次',
            {'switch_count': switch_count}
        )

    def update_fullscreen_score(self, student_id: str, exam_id: str,
                                fullscreen_count: int, duration: float = 0) -> RiskReport:
        return self.add_event(
            student_id, exam_id,
            RiskDimension.FULLSCREEN,
            'fullscreen_detected',
            f'检测到全屏模式 {fullscreen_count} 次',
            {'fullscreen_count': fullscreen_count, 'duration': duration}
        )

    def update_multi_monitor_score(self, student_id: str, exam_id: str,
                                   monitor_count: int, cross_screen_events: int = 0) -> RiskReport:
        if monitor_count > 1:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.MULTI_MONITOR,
                'multi_monitor_detected',
                f'检测到 {monitor_count} 个显示器',
                {'monitor_count': monitor_count, 'cross_screen_events': cross_screen_events}
            )
        if cross_screen_events > 0:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.MULTI_MONITOR,
                'cross_screen_window',
                f'窗口跨屏移动 {cross_screen_events} 次',
                {'cross_screen_events': cross_screen_events}
            )
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                self.create_report(student_id, exam_id)
            report = self._reports[key]
            dim = self._get_or_create_dimension(report, RiskDimension.MULTI_MONITOR)
            dim.score = max(0.0, dim.score - 5.0)
            return report

    def update_audio_score(self, student_id: str, exam_id: str,
                           is_speech: bool, suspicious: bool,
                           speech_count: int = 0, suspicious_count: int = 0) -> RiskReport:
        if suspicious:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.AUDIO,
                'suspicious_sound',
                '检测到可疑声音（提示音等）',
                {'suspicious_count': suspicious_count}
            )
        if is_speech:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.AUDIO,
                'speech_detected',
                '检测到说话声',
                {'speech_count': speech_count}
            )
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                self.create_report(student_id, exam_id)
            report = self._reports[key]
            dim = self._get_or_create_dimension(report, RiskDimension.AUDIO)
            dim.score = max(0.0, dim.score - 1.0)
            return report

    def update_similarity_score(self, student_id: str, exam_id: str,
                                similarity_risk: float,
                                matched_students: int = 0) -> RiskReport:
        if similarity_risk >= 0.85:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.SIMILARITY,
                'very_high_similarity',
                f'答案相似度极高 ({similarity_risk:.2f})',
                {'similarity_risk': similarity_risk, 'matched_students': matched_students}
            )
        if similarity_risk >= 0.7:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.SIMILARITY,
                'high_similarity',
                f'答案相似度较高 ({similarity_risk:.2f})',
                {'similarity_risk': similarity_risk, 'matched_students': matched_students}
            )
        if matched_students >= 3:
            return self.add_event(
                student_id, exam_id,
                RiskDimension.SIMILARITY,
                'multiple_matches',
                f'与 {matched_students} 名学生答案相似',
                {'matched_students': matched_students}
            )
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                self.create_report(student_id, exam_id)
            report = self._reports[key]
            dim = self._get_or_create_dimension(report, RiskDimension.SIMILARITY)
            dim.score = max(0.0, dim.score - 5.0)
            return report

    def get_report(self, student_id: str, exam_id: str) -> Optional[RiskReport]:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            return self._reports.get(key)

    def get_all_reports(self, min_level: Optional[RiskLevel] = None) -> List[Dict[str, Any]]:
        with self._lock:
            reports = []
            for report in self._reports.values():
                if min_level:
                    level_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
                    if level_order.index(report.level) < level_order.index(min_level):
                        continue
                reports.append(report.to_dict())
            return reports

    def get_reports_needing_review(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                report.to_dict()
                for report in self._reports.values()
                if report.needs_review
            ]

    def get_risk_summary(self) -> Dict[str, Any]:
        with self._lock:
            total_reports = len(self._reports)
            by_level = {
                'low': 0,
                'medium': 0,
                'high': 0,
                'critical': 0
            }
            needing_review = 0
            for report in self._reports.values():
                level = report.level.value
                if level in by_level:
                    by_level[level] += 1
                if report.needs_review:
                    needing_review += 1
            return {
                'total_reports': total_reports,
                'by_level': by_level,
                'needing_review': needing_review
            }

    def get_history(self, student_id: str, exam_id: str,
                    limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._history:
                return []
            history = list(self._history[key])
            return history[-limit:]

    def mark_reviewed(self, student_id: str, exam_id: str,
                      reviewer: str = "", notes: str = "") -> bool:
        with self._lock:
            key = self._get_key(student_id, exam_id)
            if key not in self._reports:
                return False
            report = self._reports[key]
            report.needs_review = False
            report.review_reason = f"已复核 - 复核人: {reviewer}, 备注: {notes}"
            self._history[key].append({
                'timestamp': datetime.now().isoformat(),
                'action': 'reviewed',
                'reviewer': reviewer,
                'notes': notes
            })
            return True

    def set_thresholds(self, auto_review: Optional[float] = None,
                       critical: Optional[float] = None,
                       medium: Optional[float] = None) -> None:
        if auto_review is not None:
            self._auto_review_threshold = auto_review
        if critical is not None:
            self._critical_threshold = critical
        if medium is not None:
            self._medium_threshold = medium

    def set_dimension_weight(self, dimension: RiskDimension, weight: float) -> None:
        self._dimension_weights[dimension] = weight

    def set_event_score(self, event_type: str, score: float) -> None:
        self._event_scores[event_type] = score
