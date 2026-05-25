import asyncio
import json
import cv2
import numpy as np
from typing import Dict, Optional, Any, Callable
from datetime import datetime
import uuid

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRelay
    import av
    HAS_AIORTC = True
except ImportError:
    HAS_AIORTC = False
    print("Warning: aiortc not installed. WebRTC features will be limited.")

from config import config
from core.face_recognition import FaceRecognition


class VideoTransformTrack(MediaStreamTrack if HAS_AIORTC else object):
    kind = "video"
    
    def __init__(self, track, face_recognition: FaceRecognition, 
                 on_frame_callback: Optional[Callable[[np.ndarray], None]] = None):
        if HAS_AIORTC:
            super().__init__()
        self.track = track
        self.face_recognition = face_recognition
        self.on_frame_callback = on_frame_callback
        self._frame_count = 0
    
    async def recv(self):
        if not HAS_AIORTC:
            return None
        
        frame = await self.track.recv()
        
        if isinstance(frame, av.VideoFrame):
            img = frame.to_ndarray(format="bgr24")
            
            faces = self.face_recognition.detect_face(img)
            img = self.face_recognition.draw_faces(img, faces)
            
            self._frame_count += 1
            if self._frame_count % 5 == 0 and self.on_frame_callback:
                try:
                    self.on_frame_callback(img)
                except Exception as e:
                    print(f"Error in frame callback: {e}")
            
            new_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        
        return frame


class WebRTCPeer:
    def __init__(self, student_id: str, peer_connection, 
                 face_recognition: FaceRecognition):
        self.student_id = student_id
        self.peer_connection = peer_connection
        self.face_recognition = face_recognition
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now().isoformat()
        self.video_track = None
        self.audio_track = None
        self.relay = MediaRelay() if HAS_AIORTC else None
        self._frame_buffer = []
        self._latest_frame = None
        
        self.on_frame_callback: Optional[Callable[[str, np.ndarray], None]] = None
        self.on_disconnect_callback: Optional[Callable[[str], None]] = None
    
    def _handle_frame(self, frame: np.ndarray) -> None:
        self._latest_frame = frame
        if self.on_frame_callback:
            try:
                self.on_frame_callback(self.student_id, frame)
            except Exception as e:
                print(f"Error in frame callback: {e}")
    
    def add_track(self, track) -> None:
        if not HAS_AIORTC:
            return
        
        if track.kind == "video":
            self.video_track = VideoTransformTrack(
                self.relay.subscribe(track),
                self.face_recognition,
                self._handle_frame
            )
            self.peer_connection.addTrack(self.video_track)
        
        elif track.kind == "audio":
            self.audio_track = self.relay.subscribe(track)
            self.peer_connection.addTrack(self.audio_track)
    
    async def close(self) -> None:
        if self.peer_connection:
            await self.peer_connection.close()
        
        if self.on_disconnect_callback:
            try:
                self.on_disconnect_callback(self.student_id)
            except Exception as e:
                print(f"Error in disconnect callback: {e}")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        return self._latest_frame
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'has_video': self.video_track is not None,
            'has_audio': self.audio_track is not None,
            'created_at': self.created_at,
            'frame_count': self.video_track._frame_count if self.video_track else 0
        }


class WebRTCManager:
    def __init__(self, face_recognition: FaceRecognition):
        self.face_recognition = face_recognition
        self.peers: Dict[str, WebRTCPeer] = {}
        self._lock = asyncio.Lock()
        
        self.on_frame_callback: Optional[Callable[[str, np.ndarray], None]] = None
        self.on_new_peer_callback: Optional[Callable[[str], None]] = None
        self.on_peer_disconnect_callback: Optional[Callable[[str], None]] = None
    
    def set_on_frame_callback(self, callback: Callable[[str, np.ndarray], None]) -> None:
        self.on_frame_callback = callback
        for peer in self.peers.values():
            peer.on_frame_callback = callback
    
    def set_on_new_peer_callback(self, callback: Callable[[str], None]) -> None:
        self.on_new_peer_callback = callback
    
    def set_on_peer_disconnect_callback(self, callback: Callable[[str], None]) -> None:
        self.on_peer_disconnect_callback = callback
    
    async def create_peer_connection(self, student_id: str) -> RTCPeerConnection:
        if not HAS_AIORTC:
            raise RuntimeError("aiortc is not installed")
        
        peer_connection = RTCPeerConnection()
        peer = WebRTCPeer(student_id, peer_connection, self.face_recognition)
        peer.on_frame_callback = self.on_frame_callback
        peer.on_disconnect_callback = self._on_peer_disconnect
        
        async with self._lock:
            self.peers[student_id] = peer
        
        @peer_connection.on("track")
        def on_track(track):
            print(f"Track received from {student_id}: {track.kind}")
            peer.add_track(track)
            
            @track.on("ended")
            async def on_ended():
                print(f"Track ended from {student_id}")
        
        @peer_connection.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"ICE connection state for {student_id}: {peer_connection.iceConnectionState}")
            if peer_connection.iceConnectionState == "failed":
                await self.remove_peer(student_id)
        
        if self.on_new_peer_callback:
            try:
                self.on_new_peer_callback(student_id)
            except Exception as e:
                print(f"Error in new peer callback: {e}")
        
        return peer_connection
    
    async def handle_offer(self, student_id: str, offer: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_AIORTC:
            return {'error': 'aiortc not available'}
        
        if student_id not in self.peers:
            await self.create_peer_connection(student_id)
        
        peer = self.peers[student_id]
        
        rtc_offer = RTCSessionDescription(
            sdp=offer['sdp'],
            type=offer['type']
        )
        await peer.peer_connection.setRemoteDescription(rtc_offer)
        
        answer = await peer.peer_connection.createAnswer()
        await peer.peer_connection.setLocalDescription(answer)
        
        return {
            'sdp': peer.peer_connection.localDescription.sdp,
            'type': peer.peer_connection.localDescription.type
        }
    
    async def add_ice_candidate(self, student_id: str, candidate: Dict[str, Any]) -> bool:
        if not HAS_AIORTC:
            return False
        
        peer = self.peers.get(student_id)
        if not peer:
            return False
        
        try:
            from aiortc import RTCIceCandidate
            rtc_candidate = RTCIceCandidate(
                component=candidate.get('component', 1),
                foundation=candidate.get('foundation', ''),
                ip=candidate.get('ip', ''),
                port=candidate.get('port', 0),
                priority=candidate.get('priority', 0),
                protocol=candidate.get('protocol', 'udp'),
                type=candidate.get('type', 'host')
            )
            await peer.peer_connection.addIceCandidate(rtc_candidate)
            return True
        except Exception as e:
            print(f"Error adding ICE candidate: {e}")
            return False
    
    async def remove_peer(self, student_id: str) -> bool:
        peer = self.peers.pop(student_id, None)
        if peer:
            await peer.close()
            return True
        return False
    
    def _on_peer_disconnect(self, student_id: str) -> None:
        if self.on_peer_disconnect_callback:
            try:
                self.on_peer_disconnect_callback(student_id)
            except Exception as e:
                print(f"Error in peer disconnect callback: {e}")
    
    def get_peer(self, student_id: str) -> Optional[WebRTCPeer]:
        return self.peers.get(student_id)
    
    def get_latest_frame(self, student_id: str) -> Optional[np.ndarray]:
        peer = self.peers.get(student_id)
        if peer:
            return peer.get_latest_frame()
        return None
    
    def get_all_peers(self) -> Dict[str, WebRTCPeer]:
        return self.peers.copy()
    
    def get_peer_stats(self, student_id: str) -> Optional[Dict[str, Any]]:
        peer = self.peers.get(student_id)
        if peer:
            return peer.get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, Any]:
        return {
            'peer_count': len(self.peers),
            'peers': {
                sid: peer.get_stats() for sid, peer in self.peers.items()
            }
        }
    
    async def close_all(self) -> None:
        async with self._lock:
            for student_id in list(self.peers.keys()):
                try:
                    await self.remove_peer(student_id)
                except Exception as e:
                    print(f"Error closing peer {student_id}: {e}")
            self.peers.clear()
    
    def frame_to_base64(self, frame: np.ndarray) -> Optional[str]:
        try:
            import base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"Error converting frame to base64: {e}")
            return None
