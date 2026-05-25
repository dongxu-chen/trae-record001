import time
import threading
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime
from collections import deque
import json
import os
import uuid

from config import config
from ..face_recognition import FaceRecognition, SingleFaceLock
from ..screen_recorder import ScreenRecorder
from ..tab_detection import TabSwitchDetector, BrowserTabDetector, FullscreenDetector, MultiMonitorDetector
from ..similarity import SimilarityAnalyzer


class AlertLevel:
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class AlertType:
    FACE_NOT_DETECTED = "face_not_detected"
    FACE_MISMATCH = "face_mismatch"
    MULTIPLE_FACES = "multiple_faces"
    LIVENESS_FAILED = "liveness_failed"
    EXAM_PAUSED = "exam_paused"
    EXAM_RESUMED = "exam_resumed"
    FULLSCREEN_DETECTED = "fullscreen_detected"
    MONITOR_CHANGE = "monitor_change"
    SECONDARY_MONITOR = "secondary_monitor"
    TAB_SWITCH = "tab_switch"
    SUSPICIOUS_WINDOW = "suspicious_window"
    EXCESSIVE_SWITCHING = "excessive_switching"
    TAB_HIDDEN = "tab_hidden"
    ANSWER_SIMILARITY = "answer_similarity"
    RECORDING_STOPPED = "recording_stopped"
    CUSTOM = "custom"


class Alert:
    def __init__(self, alert_type: str, level: str, message: str, 
                 student_id: str = "", exam_id: str = "", 
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.type = alert_type
        self.level = level
        self.message = message
        self.student_id = student_id
        self.exam_id = exam_id
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.acknowledged = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'level': self.level,
            'message': self.message,
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'metadata': self.metadata,
            'timestamp': self.timestamp,
            'acknowledged': self.acknowledged
        }


class ExamSession:
    def __init__(self, exam_id: str, student_id: str):
        self.exam_id = exam_id
        self.student_id = student_id
        self.start_time = datetime.now().isoformat()
        self.end_time: Optional[str] = None
        self.is_active = True
        
        self.is_paused = False
        self.paused_at: Optional[str] = None
        self.paused_reason: Optional[str] = None
        self.pause_count = 0
        self.total_paused_seconds = 0.0
        self._pause_start_time: Optional[float] = None
        
        self.face_verified = False
        self.face_verified_at: Optional[str] = None
        
        self.allowed_fullscreen_apps: List[str] = []
        self.allowed_monitors: List[int] = [0]
        
        self.alerts: List[Alert] = []
        self.events: List[Dict[str, Any]] = []
        
        self.stats = {
            'face_checks': 0,
            'face_matches': 0,
            'face_failures': 0,
            'liveness_failures': 0,
            'tab_switches': 0,
            'background_time': 0,
            'warning_alerts': 0,
            'danger_alerts': 0,
            'pause_count': 0,
            'total_paused_seconds': 0
        }
    
    def add_alert(self, alert: Alert) -> None:
        self.alerts.append(alert)
        self.events.append({
            'type': 'alert',
            'alert': alert.to_dict(),
            'timestamp': datetime.now().isoformat()
        })
        
        if alert.level == AlertLevel.WARNING:
            self.stats['warning_alerts'] += 1
        elif alert.level == AlertLevel.DANGER:
            self.stats['danger_alerts'] += 1
    
    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        self.events.append({
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    def pause(self, reason: str, alert: Optional['Alert'] = None) -> bool:
        if not self.is_active or self.is_paused:
            return False
        
        self.is_paused = True
        self.paused_at = datetime.now().isoformat()
        self.paused_reason = reason
        self._pause_start_time = time.time()
        self.pause_count += 1
        self.stats['pause_count'] = self.pause_count
        
        self.add_event('exam_paused', {
            'reason': reason,
            'alert_id': alert.id if alert else None
        })
        
        return True
    
    def resume(self, reason: str = "管理员恢复") -> bool:
        if not self.is_active or not self.is_paused:
            return False
        
        if self._pause_start_time:
            paused_duration = time.time() - self._pause_start_time
            self.total_paused_seconds += paused_duration
            self.stats['total_paused_seconds'] = int(self.total_paused_seconds)
            self._pause_start_time = None
        
        self.is_paused = False
        self.paused_reason = None
        self.paused_at = None
        
        self.add_event('exam_resumed', {
            'reason': reason,
            'paused_duration': self.total_paused_seconds
        })
        
        return True
    
    def can_continue_exam(self) -> bool:
        return self.is_active and not self.is_paused
    
    def end(self) -> None:
        if self.is_paused and self._pause_start_time:
            paused_duration = time.time() - self._pause_start_time
            self.total_paused_seconds += paused_duration
            self.stats['total_paused_seconds'] = int(self.total_paused_seconds)
        
        self.is_active = False
        self.end_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'exam_id': self.exam_id,
            'student_id': self.student_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'is_active': self.is_active,
            'is_paused': self.is_paused,
            'paused_at': self.paused_at,
            'paused_reason': self.paused_reason,
            'pause_count': self.pause_count,
            'total_paused_seconds': self.total_paused_seconds,
            'face_verified': self.face_verified,
            'face_verified_at': self.face_verified_at,
            'alerts': [a.to_dict() for a in self.alerts],
            'stats': self.stats
        }


class ExamMonitor:
    def __init__(self):
        self.face_recognition = FaceRecognition()
        self.single_face_lock = SingleFaceLock(
            grace_period=config.MULTIPLE_FACE_GRACE_PERIOD,
            auto_pause=config.ENABLE_AUTO_PAUSE_ON_MULTIPLE_FACES
        )
        self.screen_recorder = ScreenRecorder()
        self.tab_detector = TabSwitchDetector()
        self.browser_detector = BrowserTabDetector()
        self.fullscreen_detector = FullscreenDetector()
        self.multi_monitor_detector = MultiMonitorDetector()
        self.similarity_analyzer = SimilarityAnalyzer()
        
        self.sessions: Dict[str, ExamSession] = {}
        self.active_sessions: Dict[str, ExamSession] = {}
        
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_monitoring = False
        
        self._face_check_interval = config.FACE_DETECTION_INTERVAL
        self._monitor_check_interval = config.MONITOR_DETECTION_INTERVAL
        
        self._setup_callbacks()
    
    def _setup_callbacks(self) -> None:
        self.tab_detector.set_on_switch_callback(self._on_tab_switch)
        self.tab_detector.set_on_suspicious_callback(self._on_suspicious_switching)
        self.browser_detector.set_on_visibility_change_callback(self._on_visibility_change)
        self.browser_detector.set_on_suspicious_callback(self._on_browser_suspicious)
        self.fullscreen_detector.set_on_fullscreen_callback(self._on_fullscreen_detected)
        self.multi_monitor_detector.set_on_monitor_change_callback(self._on_monitor_change)
        self.single_face_lock.set_on_multiple_faces_callback(self._on_multiple_faces_detected)
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def _trigger_alert(self, alert: Alert) -> None:
        session = self.active_sessions.get(alert.student_id)
        if session:
            session.add_alert(alert)
        
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Error in alert callback: {e}")
    
    def _on_tab_switch(self, from_window: str, to_window: str, student_id: str = "") -> None:
        session = self.active_sessions.get(student_id)
        if session:
            session.stats['tab_switches'] += 1
        
        alert = Alert(
            alert_type=AlertType.TAB_SWITCH,
            level=AlertLevel.WARNING,
            message=f"窗口切换: 从 '{from_window}' 到 '{to_window}'",
            student_id=student_id,
            metadata={'from': from_window, 'to': to_window}
        )
        self._trigger_alert(alert)
    
    def _on_suspicious_switching(self, count: int, window: float, student_id: str = "") -> None:
        alert = Alert(
            alert_type=AlertType.EXCESSIVE_SWITCHING,
            level=AlertLevel.DANGER,
            message=f"在{window}秒内切换窗口{count}次，行为可疑",
            student_id=student_id,
            metadata={'count': count, 'window_seconds': window}
        )
        self._trigger_alert(alert)
    
    def _on_visibility_change(self, is_visible: bool, student_id: str = "") -> None:
        if not is_visible:
            alert = Alert(
                alert_type=AlertType.TAB_HIDDEN,
                level=AlertLevel.WARNING,
                message="考试页面被隐藏",
                student_id=student_id
            )
            self._trigger_alert(alert)
    
    def _on_browser_suspicious(self, reason: str, student_id: str = "") -> None:
        alert = Alert(
            alert_type=AlertType.CUSTOM,
            level=AlertLevel.WARNING,
            message=reason,
            student_id=student_id,
            metadata={'reason': reason}
        )
        self._trigger_alert(alert)
    
    def _on_fullscreen_detected(self, window_title: str, process_name: str, 
                                is_fullscreen: bool, student_id: str = "") -> None:
        session = self.active_sessions.get(student_id)
        if session and window_title in session.allowed_fullscreen_apps:
            return
        
        if is_fullscreen and config.ENABLE_FULLSCREEN_DETECTION:
            alert = Alert(
                alert_type=AlertType.FULLSCREEN_DETECTED,
                level=AlertLevel.WARNING,
                message=f"检测到全屏窗口: {window_title}",
                student_id=student_id,
                metadata={
                    'window_title': window_title,
                    'process_name': process_name
                }
            )
            self._trigger_alert(alert)
    
    def _on_monitor_change(self, monitor_count: int, monitors: List[Dict[str, Any]], 
                           student_id: str = "") -> None:
        session = self.active_sessions.get(student_id)
        if session and all(m['index'] in session.allowed_monitors for m in monitors):
            return
        
        if monitor_count > 1 and config.ENABLE_MULTI_MONITOR_DETECTION:
            alert = Alert(
                alert_type=AlertType.MONITOR_CHANGE,
                level=AlertLevel.WARNING,
                message=f"检测到{monitor_count}台显示器",
                student_id=student_id,
                metadata={
                    'monitor_count': monitor_count,
                    'monitors': monitors
                }
            )
            self._trigger_alert(alert)
            
            for monitor in monitors[1:]:
                if monitor['index'] not in session.allowed_monitors:
                    alert = Alert(
                        alert_type=AlertType.SECONDARY_MONITOR,
                        level=AlertLevel.DANGER,
                        message=f"使用第二台显示器: {monitor.get('name', '未知')}",
                        student_id=student_id,
                        metadata={'monitor': monitor}
                    )
                    self._trigger_alert(alert)
    
    def _on_multiple_faces_detected(self, face_count: int, faces: List[Any], 
                                    student_id: str = "") -> None:
        session = self.active_sessions.get(student_id)
        
        alert = Alert(
            alert_type=AlertType.MULTIPLE_FACES,
            level=AlertLevel.DANGER,
            message=f"检测到{face_count}张人脸，请确保只有考生本人在场",
            student_id=student_id,
            metadata={'face_count': face_count}
        )
        self._trigger_alert(alert)
        
        if session and config.ENABLE_AUTO_PAUSE_ON_MULTIPLE_FACES:
            pause_alert = Alert(
                alert_type=AlertType.EXAM_PAUSED,
                level=AlertLevel.DANGER,
                message="考试已暂停：检测到多人在场",
                student_id=student_id,
                metadata={'face_count': face_count}
            )
            self._trigger_alert(pause_alert)
            
            session.pause("检测到多人在场", pause_alert)
    
    def register_student_face(self, student_id: str, face_image) -> bool:
        return self.face_recognition.register_face(student_id, face_image)
    
    def verify_student_face(self, student_id: str, face_image, 
                           check_liveness: bool = True,
                           check_single: bool = True) -> Tuple[bool, float, Dict[str, Any]]:
        is_match, similarity, details = self.face_recognition.verify_face(
            student_id, face_image,
            check_liveness=check_liveness and config.ENABLE_LIVENESS_DETECTION,
            check_single=check_single and config.ENABLE_SINGLE_FACE_LOCK
        )
        
        session = self.active_sessions.get(student_id)
        if session:
            session.stats['face_checks'] += 1
            if is_match:
                session.stats['face_matches'] += 1
            else:
                session.stats['face_failures'] += 1
        
        if details.get('face_count', 1) > 1:
            self._on_multiple_faces_detected(
                details['face_count'], 
                details.get('faces', []),
                student_id
            )
        
        if config.ENABLE_LIVENESS_DETECTION and not details.get('liveness_passed', True):
            session.stats['liveness_failures'] += 1
            alert = Alert(
                alert_type=AlertType.LIVENESS_FAILED,
                level=AlertLevel.DANGER,
                message=details.get('liveness_reason', '活体检测失败'),
                student_id=student_id,
                metadata={'liveness_details': details}
            )
            self._trigger_alert(alert)
            return False, similarity, details
        
        if not is_match:
            alert = Alert(
                alert_type=AlertType.FACE_MISMATCH,
                level=AlertLevel.DANGER,
                message=f"人脸验证失败，相似度: {similarity:.2f}",
                student_id=student_id,
                metadata={'similarity': similarity}
            )
            self._trigger_alert(alert)
        
        return is_match, similarity, details
    
    def start_exam_session(self, exam_id: str, student_id: str, 
                          face_image = None) -> ExamSession:
        session = ExamSession(exam_id, student_id)
        self.sessions[f"{exam_id}_{student_id}"] = session
        self.active_sessions[student_id] = session
        
        if config.ENABLE_RECORDING:
            self.screen_recorder.start(exam_id)
        
        if config.ENABLE_TAB_DETECTION:
            self.tab_detector.start()
        
        if config.ENABLE_FULLSCREEN_DETECTION:
            self.fullscreen_detector.start()
        
        if config.ENABLE_MULTI_MONITOR_DETECTION:
            self.multi_monitor_detector.start()
        
        session.add_event('session_started', {'exam_id': exam_id})
        
        if face_image is not None and config.ENABLE_FACE_DETECTION:
            is_match, similarity, details = self.verify_student_face(student_id, face_image)
            if is_match:
                session.face_verified = True
                session.face_verified_at = datetime.now().isoformat()
                session.add_event('face_verified', {
                    'similarity': similarity,
                    'liveness_passed': details.get('liveness_passed', False)
                })
        
        return session
    
    def end_exam_session(self, student_id: str) -> Optional[ExamSession]:
        session = self.active_sessions.pop(student_id, None)
        if not session:
            return None
        
        session.end()
        
        if config.ENABLE_RECORDING:
            self.screen_recorder.stop()
        
        if config.ENABLE_TAB_DETECTION:
            self.tab_detector.stop()
        
        if config.ENABLE_FULLSCREEN_DETECTION:
            self.fullscreen_detector.stop()
        
        if config.ENABLE_MULTI_MONITOR_DETECTION:
            self.multi_monitor_detector.stop()
        
        self.single_face_lock.reset()
        
        session.add_event('session_ended', {})
        return session
    
    def check_face_periodic(self, student_id: str, frame) -> Tuple[bool, float, Dict[str, Any]]:
        if not config.ENABLE_FACE_DETECTION:
            return True, 1.0, {}
        
        session = self.active_sessions.get(student_id)
        if session and not session.can_continue_exam():
            return False, 0.0, {'paused': True, 'reason': session.paused_reason}
        
        is_match, similarity, details = self.verify_student_face(
            student_id, frame,
            check_liveness=config.ENABLE_LIVENESS_DETECTION,
            check_single=config.ENABLE_SINGLE_FACE_LOCK
        )
        
        if details.get('face_count', 1) == 0:
            alert = Alert(
                alert_type=AlertType.FACE_NOT_DETECTED,
                level=AlertLevel.WARNING,
                message="未检测到人脸",
                student_id=student_id
            )
            self._trigger_alert(alert)
            return False, 0.0, details
        
        if config.ENABLE_SINGLE_FACE_LOCK:
            self.single_face_lock.check_faces(details.get('face_count', 1), details.get('faces', []), student_id)
        
        return is_match, similarity, details
    
    def pause_exam(self, student_id: str, reason: str) -> bool:
        session = self.active_sessions.get(student_id)
        if not session:
            return False
        
        result = session.pause(reason)
        if result:
            alert = Alert(
                alert_type=AlertType.EXAM_PAUSED,
                level=AlertLevel.DANGER,
                message=f"考试已暂停: {reason}",
                student_id=student_id,
                metadata={'reason': reason}
            )
            self._trigger_alert(alert)
        
        return result
    
    def resume_exam(self, student_id: str, reason: str = "管理员恢复") -> bool:
        session = self.active_sessions.get(student_id)
        if not session:
            return False
        
        result = session.resume(reason)
        if result:
            self.single_face_lock.reset()
            
            alert = Alert(
                alert_type=AlertType.EXAM_RESUMED,
                level=AlertLevel.INFO,
                message=f"考试已恢复: {reason}",
                student_id=student_id,
                metadata={'reason': reason}
            )
            self._trigger_alert(alert)
        
        return result
    
    def is_exam_paused(self, student_id: str) -> bool:
        session = self.active_sessions.get(student_id)
        return session.is_paused if session else False
    
    def analyze_student_answers(self, exam_id: str, submissions: List[Dict]) -> Dict:
        if not config.ENABLE_SIMILARITY_CHECK:
            return {}
        
        result = self.similarity_analyzer.analyze_exam_answers_structured(submissions)
        
        for student_id, analysis in result.get('student_analysis', {}).items():
            if analysis.get('risk_score', 0) > config.STRUCTURED_SIMILARITY_RISK_THRESHOLD:
                alert = Alert(
                    alert_type=AlertType.ANSWER_SIMILARITY,
                    level=AlertLevel.DANGER,
                    message=f"答案相似度风险评分: {analysis['risk_score']:.2f}",
                    student_id=student_id,
                    exam_id=exam_id,
                    metadata={
                        'risk_score': analysis['risk_score'],
                        'risk_level': analysis['risk_level'],
                        'suspicious_questions': analysis.get('suspicious_questions', []),
                        'matched_students': list(analysis.get('pairwise', {}).keys())
                    }
                )
                self._trigger_alert(alert)
        
        for pair in result.get('suspicious_pairs', []):
            questions = pair.get('question_similarities', [])
            for q in questions:
                if q.get('similarity', 0) > config.STRUCTURED_SIMILARITY_THRESHOLD:
                    alert = Alert(
                        alert_type=AlertType.ANSWER_SIMILARITY,
                        level=AlertLevel.DANGER,
                        message=f"题目{q['question_id']}答案相似度 {q['similarity']:.2f} 超过阈值",
                        student_id=pair['student1_id'],
                        exam_id=exam_id,
                        metadata={
                            'other_student': pair['student2_id'],
                            'question_id': q['question_id'],
                            'question_type': q.get('question_type', 'unknown'),
                            'similarity': q['similarity']
                        }
                    )
                    self._trigger_alert(alert)
                    
                    alert2 = Alert(
                        alert_type=AlertType.ANSWER_SIMILARITY,
                        level=AlertLevel.DANGER,
                        message=f"题目{q['question_id']}答案相似度 {q['similarity']:.2f} 超过阈值",
                        student_id=pair['student2_id'],
                        exam_id=exam_id,
                        metadata={
                            'other_student': pair['student1_id'],
                            'question_id': q['question_id'],
                            'question_type': q.get('question_type', 'unknown'),
                            'similarity': q['similarity']
                        }
                    )
                    self._trigger_alert(alert2)
        
        return result
    
    def start_background_monitoring(self) -> None:
        if self._is_monitoring:
            return
        
        self._stop_event.clear()
        self._is_monitoring = True
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self._monitoring_thread.start()
    
    def stop_background_monitoring(self) -> None:
        if not self._is_monitoring:
            return
        
        self._stop_event.set()
        
        if self._monitoring_thread is not None:
            self._monitoring_thread.join(timeout=5.0)
        
        self._is_monitoring = False
    
    def _monitoring_loop(self) -> None:
        last_monitor_check = 0.0
        
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                if config.ENABLE_TAB_DETECTION:
                    for student_id, session in self.active_sessions.items():
                        if not session.can_continue_exam():
                            continue
                        
                        if not self.tab_detector.is_current_window_allowed():
                            current_window = self.tab_detector.get_current_window()
                            alert = Alert(
                                alert_type=AlertType.SUSPICIOUS_WINDOW,
                                level=AlertLevel.WARNING,
                                message=f"当前窗口不在允许列表: {current_window}",
                                student_id=student_id,
                                metadata={'window': current_window}
                            )
                            self._trigger_alert(alert)
                
                if config.ENABLE_FULLSCREEN_DETECTION:
                    self.fullscreen_detector.check_current_window()
                    fs_info = self.fullscreen_detector.get_fullscreen_info()
                    if fs_info.get('is_fullscreen'):
                        for student_id, session in self.active_sessions.items():
                            if session.can_continue_exam():
                                self._on_fullscreen_detected(
                                    fs_info['window_title'],
                                    fs_info.get('process_name', ''),
                                    True,
                                    student_id
                                )
                
                if config.ENABLE_MULTI_MONITOR_DETECTION and \
                   current_time - last_monitor_check >= self._monitor_check_interval:
                    self.multi_monitor_detector.detect_monitors()
                    monitor_info = self.multi_monitor_detector.get_monitor_info()
                    if monitor_info.get('monitor_count', 0) > 1:
                        active_window = self.multi_monitor_detector.get_active_window_monitor()
                        for student_id, session in self.active_sessions.items():
                            if session.can_continue_exam():
                                self._on_monitor_change(
                                    monitor_info['monitor_count'],
                                    monitor_info.get('monitors', []),
                                    student_id
                                )
                    last_monitor_check = current_time
                
                browser_stats = self.browser_detector.get_stats()
                for student_id, session in self.active_sessions.items():
                    session.stats['background_time'] = browser_stats['total_background_seconds']
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            time.sleep(1.0)
    
    def get_session(self, student_id: str) -> Optional[ExamSession]:
        return self.active_sessions.get(student_id)
    
    def get_session_by_exam(self, exam_id: str, student_id: str) -> Optional[ExamSession]:
        return self.sessions.get(f"{exam_id}_{student_id}")
    
    def get_all_active_sessions(self) -> Dict[str, ExamSession]:
        return self.active_sessions.copy()
    
    def get_alerts(self, student_id: Optional[str] = None, 
                  level: Optional[str] = None) -> List[Alert]:
        alerts = []
        
        if student_id:
            session = self.active_sessions.get(student_id)
            if session:
                alerts = session.alerts
        else:
            for session in self.active_sessions.values():
                alerts.extend(session.alerts)
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, student_id: str) -> bool:
        session = self.active_sessions.get(student_id)
        if not session:
            return False
        
        for alert in session.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        
        return False
    
    def get_student_stats(self, student_id: str) -> Optional[Dict]:
        session = self.active_sessions.get(student_id)
        if not session:
            return None
        
        return {
            'student_id': student_id,
            'exam_id': session.exam_id,
            'face_verified': session.face_verified,
            'stats': session.stats,
            'alert_count': len(session.alerts),
            'active': session.is_active
        }
    
    def get_all_stats(self) -> Dict:
        return {
            'active_sessions': len(self.active_sessions),
            'total_sessions': len(self.sessions),
            'total_alerts': sum(len(s.alerts) for s in self.active_sessions.values()),
            'danger_alerts': sum(1 for s in self.active_sessions.values() 
                                  for a in s.alerts if a.level == AlertLevel.DANGER),
            'warning_alerts': sum(1 for s in self.active_sessions.values()
                                   for a in s.alerts if a.level == AlertLevel.WARNING)
        }
    
    def save_session_report(self, student_id: str, filepath: str) -> bool:
        session = self.active_sessions.get(student_id)
        if not session:
            return False
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        
        return True
    
    def custom_alert(self, student_id: str, message: str, 
                    level: str = AlertLevel.WARNING, 
                    metadata: Optional[Dict] = None) -> Alert:
        alert = Alert(
            alert_type=AlertType.CUSTOM,
            level=level,
            message=message,
            student_id=student_id,
            metadata=metadata or {}
        )
        self._trigger_alert(alert)
        return alert
