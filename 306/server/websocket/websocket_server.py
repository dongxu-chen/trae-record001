import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from core.monitoring import ExamMonitor, Alert


class WebSocketConnection:
    def __init__(self, websocket: WebSocket, student_id: str, role: str = "student"):
        self.websocket = websocket
        self.student_id = student_id
        self.role = role
        self.connected_at = datetime.now().isoformat()
        self.id = str(uuid.uuid4())
    
    async def send(self, message: Dict[str, Any]) -> None:
        await self.websocket.send_json(message)
    
    async def receive(self) -> Dict[str, Any]:
        data = await self.websocket.receive_json()
        return data if isinstance(data, dict) else {}


class ExamWebSocketManager:
    def __init__(self, exam_monitor: ExamMonitor):
        self.exam_monitor = exam_monitor
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self._lock = asyncio.Lock()
        
        self.exam_monitor.add_alert_callback(self._on_alert)
    
    def _on_alert(self, alert: Alert) -> None:
        asyncio.create_task(self._broadcast_alert(alert))
    
    async def connect(self, websocket: WebSocket, student_id: str, role: str = "student") -> WebSocketConnection:
        await websocket.accept()
        connection = WebSocketConnection(websocket, student_id, role)
        
        async with self._lock:
            self.active_connections[student_id] = connection
        
        await self._send_message(connection, {
            'type': 'connected',
            'student_id': student_id,
            'role': role,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"WebSocket connected: {student_id} ({role})")
        return connection
    
    async def disconnect(self, student_id: str) -> None:
        async with self._lock:
            if student_id in self.active_connections:
                del self.active_connections[student_id]
                print(f"WebSocket disconnected: {student_id}")
    
    async def _send_message(self, connection: WebSocketConnection, message: Dict[str, Any]) -> None:
        try:
            await connection.send(message)
        except Exception as e:
            print(f"Error sending message to {connection.student_id}: {e}")
    
    async def send_to_student(self, student_id: str, message: Dict[str, Any]) -> bool:
        connection = self.active_connections.get(student_id)
        if connection:
            await self._send_message(connection, message)
            return True
        return False
    
    async def broadcast(self, message: Dict[str, Any], role: Optional[str] = None) -> int:
        count = 0
        async with self._lock:
            for connection in self.active_connections.values():
                if role is None or connection.role == role:
                    try:
                        await connection.send(message)
                        count += 1
                    except Exception as e:
                        print(f"Error broadcasting: {e}")
        return count
    
    async def _broadcast_alert(self, alert: Alert) -> None:
        message = {
            'type': 'alert',
            'data': alert.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        await self.send_to_student(alert.student_id, message)
        
        teacher_message = message.copy()
        await self.broadcast(teacher_message, role='teacher')
    
    async def handle_message(self, student_id: str, message: Dict[str, Any]) -> None:
        msg_type = message.get('type')
        data = message.get('data', {})
        
        if msg_type == 'ping':
            await self.send_to_student(student_id, {
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            })
        
        elif msg_type == 'visibility_change':
            is_visible = data.get('is_visible', True)
            self.exam_monitor.browser_detector.on_visibility_change(is_visible)
        
        elif msg_type == 'tab_blur':
            self.exam_monitor.browser_detector.on_blur()
        
        elif msg_type == 'tab_focus':
            self.exam_monitor.browser_detector.on_focus()
        
        elif msg_type == 'face_verification':
            face_image = data.get('image')
            if face_image:
                is_match, similarity = self.exam_monitor.verify_student_face(student_id, face_image)
                await self.send_to_student(student_id, {
                    'type': 'face_verification_result',
                    'data': {
                        'is_match': is_match,
                        'similarity': similarity
                    }
                })
        
        elif msg_type == 'request_stats':
            stats = self.exam_monitor.get_student_stats(student_id)
            await self.send_to_student(student_id, {
                'type': 'stats',
                'data': stats,
                'timestamp': datetime.now().isoformat()
            })
        
        elif msg_type == 'request_alerts':
            alerts = self.exam_monitor.get_alerts(student_id=student_id)
            await self.send_to_student(student_id, {
                'type': 'alerts',
                'data': [a.to_dict() for a in alerts],
                'timestamp': datetime.now().isoformat()
            })
        
        elif msg_type == 'acknowledge_alert':
            alert_id = data.get('alert_id')
            if alert_id:
                success = self.exam_monitor.acknowledge_alert(alert_id, student_id)
                await self.send_to_student(student_id, {
                    'type': 'alert_acknowledged',
                    'data': {'success': success, 'alert_id': alert_id}
                })
        
        elif msg_type == 'custom_event':
            event_type = data.get('event_type', 'custom')
            event_data = data.get('event_data', {})
            session = self.exam_monitor.get_session(student_id)
            if session:
                session.add_event(event_type, event_data)
    
    async def send_face_frame(self, student_id: str, frame_data: str, 
                              face_detected: bool, similarity: float = 0.0) -> None:
        await self.send_to_student(student_id, {
            'type': 'face_monitor',
            'data': {
                'frame': frame_data,
                'face_detected': face_detected,
                'similarity': similarity,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    async def send_status_update(self, student_id: str, status: str, details: Dict = None) -> None:
        await self.send_to_student(student_id, {
            'type': 'status_update',
            'data': {
                'status': status,
                'details': details or {},
                'timestamp': datetime.now().isoformat()
            }
        })
    
    async def send_monitor_update(self, update_type: str, data: Dict) -> None:
        message = {
            'type': 'monitor_update',
            'update_type': update_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast(message, role='teacher')
    
    async def get_connected_students(self) -> list:
        return [
            {
                'student_id': conn.student_id,
                'role': conn.role,
                'connected_at': conn.connected_at
            }
            for conn in self.active_connections.values()
        ]
    
    async def disconnect_all(self) -> None:
        async with self._lock:
            for student_id in list(self.active_connections.keys()):
                try:
                    conn = self.active_connections[student_id]
                    await conn.websocket.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")
            self.active_connections.clear()


async def websocket_endpoint(websocket: WebSocket, student_id: str, 
                            manager: ExamWebSocketManager, role: str = "student"):
    connection = await manager.connect(websocket, student_id, role)
    
    try:
        while True:
            try:
                data = await connection.receive()
                await manager.handle_message(student_id, data)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_to_student(student_id, {
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
            except Exception as e:
                print(f"Error handling message: {e}")
                await manager.send_to_student(student_id, {
                    'type': 'error',
                    'message': str(e)
                })
    finally:
        await manager.disconnect(student_id)
