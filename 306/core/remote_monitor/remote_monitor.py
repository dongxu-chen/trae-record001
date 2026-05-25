import base64
import threading
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import cv2
import numpy as np


@dataclass
class StudentMonitorInfo:
    student_id: str
    exam_id: str
    student_name: str = ""
    status: str = "active"
    risk_level: str = "low"
    last_frame_time: Optional[str] = None
    alert_count: int = 0
    audio_alert: bool = False
    tab_switch_count: int = 0
    face_detected: bool = True
    face_count: int = 1
    is_paused: bool = False
    join_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'student_name': self.student_name,
            'status': self.status,
            'risk_level': self.risk_level,
            'last_frame_time': self.last_frame_time,
            'alert_count': self.alert_count,
            'audio_alert': self.audio_alert,
            'tab_switch_count': self.tab_switch_count,
            'face_detected': self.face_detected,
            'face_count': self.face_count,
            'is_paused': self.is_paused,
            'join_time': self.join_time
        }


@dataclass
class ThumbnailFrame:
    student_id: str
    exam_id: str
    frame_base64: str
    timestamp: str
    student_info: StudentMonitorInfo

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'frame': self.frame_base64,
            'timestamp': self.timestamp,
            'student_info': self.student_info.to_dict()
        }


class RemoteMonitor:
    def __init__(self, thumbnail_size: Tuple[int, int] = (320, 240),
                 max_history: int = 50,
                 quality: int = 85):
        self.thumbnail_size = thumbnail_size
        self.max_history = max_history
        self.quality = quality
        self._lock = threading.Lock()
        self._students: Dict[str, StudentMonitorInfo] = {}
        self._frames: Dict[str, ThumbnailFrame] = {}
        self._frame_history: Dict[str, deque] = {}
        self._exam_rooms: Dict[str, List[str]] = {}
        self._alert_summary: Dict[str, List[Dict[str, Any]]] = {}

    def _encode_frame(self, frame: np.ndarray) -> Optional[str]:
        if frame is None or frame.size == 0:
            return None
        try:
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            resized = cv2.resize(frame, self.thumbnail_size)
            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            if buffer is None:
                return None
            return base64.b64encode(buffer.tobytes()).decode('utf-8')
        except Exception:
            return None

    def _encode_frame_full(self, frame: np.ndarray) -> Optional[str]:
        if frame is None or frame.size == 0:
            return None
        try:
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            if buffer is None:
                return None
            return base64.b64encode(buffer.tobytes()).decode('utf-8')
        except Exception:
            return None

    def register_student(self, student_id: str, exam_id: str,
                       student_name: str = "") -> bool:
        with self._lock:
            if student_id in self._students:
                return False
            self._students[student_id] = StudentMonitorInfo(
                student_id=student_id,
                exam_id=exam_id,
                student_name=student_name
            )
            self._frame_history[student_id] = deque(maxlen=self.max_history)
            self._alert_summary[student_id] = []
            if exam_id not in self._exam_rooms:
                self._exam_rooms[exam_id] = []
            if student_id not in self._exam_rooms[exam_id]:
                self._exam_rooms[exam_id].append(student_id)
            return True

    def unregister_student(self, student_id: str) -> bool:
        with self._lock:
            if student_id in self._students:
                info = self._students[student_id]
                exam_id = info.exam_id
                if exam_id in self._exam_rooms:
                    if student_id in self._exam_rooms[exam_id]:
                        self._exam_rooms[exam_id].remove(student_id)
                del self._students[student_id]
                if student_id in self._frames:
                    del self._frames[student_id]
                if student_id in self._frame_history:
                    del self._frame_history[student_id]
                if student_id in self._alert_summary:
                    del self._alert_summary[student_id]
                return True
            return False

    def update_frame(self, student_id: str, frame: np.ndarray,
                     face_details: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            if student_id not in self._students:
                return False
            frame_base64 = self._encode_frame(frame)
            if frame_base64 is None:
                return False
            info = self._students[student_id]
            info.last_frame_time = datetime.now().isoformat()
            if face_details:
                info.face_count = face_details.get('face_count', info.face_count)
                info.face_detected = face_details.get('face_count', 0) > 0
                info.is_paused = face_details.get('is_paused', info.is_paused)
            thumb_frame = ThumbnailFrame(
                student_id=student_id,
                exam_id=info.exam_id,
                frame_base64=frame_base64,
                timestamp=datetime.now().isoformat(),
                student_info=info
            )
            self._frames[student_id] = thumb_frame
            self._frame_history[student_id].append(thumb_frame)
            return True

    def update_student_status(self, student_id: str,
                              status: Optional[str] = None,
                              risk_level: Optional[str] = None,
                              alert_count: Optional[int] = None,
                              audio_alert: Optional[bool] = None,
                              tab_switch_count: Optional[int] = None) -> bool:
        with self._lock:
            if student_id not in self._students:
                return False
            info = self._students[student_id]
            if status is not None:
                info.status = status
            if risk_level is not None:
                info.risk_level = risk_level
            if alert_count is not None:
                info.alert_count = alert_count
            if audio_alert is not None:
                info.audio_alert = audio_alert
            if tab_switch_count is not None:
                info.tab_switch_count = tab_switch_count
            return True

    def add_alert(self, student_id: str, alert_type: str,
                  level: str, message: str) -> None:
        with self._lock:
            if student_id not in self._alert_summary:
                self._alert_summary[student_id] = []
            self._alert_summary[student_id].append({
                'type': alert_type,
                'level': level,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
            if student_id in self._students:
                self._students[student_id].alert_count += 1
                if level in ['high', 'danger', 'critical']:
                    self._students[student_id].risk_level = level

    def get_thumbnail(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if student_id in self._frames:
                return self._frames[student_id].to_dict()
            return None

    def get_all_thumbnails(self, view_type: str = "grid",
                           max_items: int = 50) -> Dict[str, Any]:
        with self._lock:
            thumbnails = []
            for student_id, frame in list(self._frames.items()):
                if len(thumbnails) >= max_items:
                    break
                thumbnails.append(frame.to_dict())
            return {
                'thumbnails': thumbnails,
                'total_count': len(self._frames),
                'view_type': view_type,
                'students': [
                    info.to_dict() for info in self._students.values()]
            }

    def get_thumbnails_by_exam(self, exam_id: str,
                                max_items: int = 50) -> Dict[str, Any]:
        with self._lock:
            thumbnails = []
            student_ids = self._exam_rooms.get(exam_id, [])
            for student_id in student_ids:
                if len(thumbnails) >= max_items:
                    break
                if student_id in self._frames:
                    thumbnails.append(self._frames[student_id].to_dict())
            return {
                'exam_id': exam_id,
                'thumbnails': thumbnails,
                'total_count': len(thumbnails),
                'students_in_exam': len(student_ids)
            }

    def get_thumbnails_by_risk(self, min_risk_level: str = "medium",
                               max_items: int = 50) -> Dict[str, Any]:
        risk_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3, 'danger': 4}
        min_level = risk_order.get(min_risk_level, 1)
        with self._lock:
            thumbnails = []
            for student_id, frame in self._frames.items():
                info = self._students.get(student_id)
                if info and risk_order.get(info.risk_level, 0) >= min_level:
                    if len(thumbnails) >= max_items:
                        break
                    thumbnails.append(frame.to_dict())
            return {
                'min_risk_level': min_risk_level,
                'thumbnails': thumbnails,
                'total_count': len(thumbnails)
            }

    def get_student_list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [info.to_dict() for info in self._students.values()]

    def get_monitor_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_students = len(self._students)
            active_students = sum(
                1 for info in self._students.values()
                if info.status == 'active'
            )
            paused_students = sum(
                1 for info in self._students.values()
                if info.is_paused
            )
            risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            for info in self._students.values():
                level = info.risk_level if info.risk_level in risk_counts else 'low'
                risk_counts[level] += 1
            total_alerts = sum(
                len(student_id) for student_id in self._alert_summary.values()
            )
            return {
                'total_students': total_students,
                'active_students': active_students,
                'paused_students': paused_students,
                'by_risk': risk_counts,
                'total_alerts': total_alerts,
                'exam_rooms': {
                    exam_id: len(students)
                    for exam_id, students in self._exam_rooms.items()
                },
                'students_with_alerts': [
                    info.to_dict() for info in self._students.values()
                    if info.alert_count > 0
                ]
            }

    def get_alert_summary(self) -> Dict[str, Any]:
        with self._lock:
            all_alerts = []
            for student_id, alerts in self._alert_summary.items():
                for alert in alerts:
                    all_alerts.append({
                    'student_id': student_id,
                    **alert
                })
            all_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            return {
                'total_alerts': len(all_alerts),
                'recent_alerts': all_alerts[:100],
                'by_level': {
                    'low': len([a for a in all_alerts if a['level'] == 'low']),
                    'medium': len([a for a in all_alerts if a['level'] == 'medium']),
                    'high': len([a for a in all_alerts if a['level'] == 'high']),
                    'critical': len([a for a in all_alerts if a['level'] == 'critical']),
                    'danger': len([a for a in all_alerts if a['level'] == 'danger'])
                }
            }

    def get_frame_history(self, student_id: str,
                           limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            if student_id not in self._frame_history:
                return []
            history = list(self._frame_history[student_id])
            return [f.to_dict() for f in history[-limit:]]

    def search_students(self, query: str,
                         status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        with self._lock:
            results = []
            for info in self._students.values():
                if status_filter and info.status != status_filter:
                    continue
                if (query_lower in info.student_id.lower() or
                    query_lower in info.student_name.lower() or
                    query_lower in info.exam_id.lower()):
                    results.append(info.to_dict())
            return results

    def get_exam_rooms(self) -> Dict[str, List[str]]:
        with self._lock:
            return {k: list(v) for k, v in self._exam_rooms.items()}

    def set_thumbnail_size(self, width: int, height: int) -> None:
        self.thumbnail_size = (width, height)
