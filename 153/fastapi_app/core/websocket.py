from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RoomState:
    users: Dict[str, WebSocket] = field(default_factory=dict)
    user_count: int = 0
    started: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, RoomState] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
    
    async def disconnect(self, client_id: str):
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            
            for room_id, room in self.rooms.items():
                if client_id in room.users:
                    del room.users[client_id]
                    room.user_count -= 1
                    await self._broadcast_to_room(
                        room_id,
                        {
                            "type": "user_left",
                            "client_id": client_id,
                            "user_count": room.user_count
                        }
                    )
    
    async def join_room(self, room_id: str, client_id: str, user_type: str = "user"):
        async with self._lock:
            if room_id not in self.rooms:
                self.rooms[room_id] = RoomState()
            
            room = self.rooms[room_id]
            if client_id in self.active_connections:
                room.users[client_id] = self.active_connections[client_id]
                room.user_count += 1
                
                await self._broadcast_to_room(
                    room_id,
                    {
                        "type": "user_joined",
                        "client_id": client_id,
                        "user_type": user_type,
                        "user_count": room.user_count
                    }
                )
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def send_room_message(self, room_id: str, message: dict):
        async with self._lock:
            await self._broadcast_to_room(room_id, message)
    
    async def _broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.rooms:
            for ws in self.rooms[room_id].users.values():
                try:
                    await ws.send_json(message)
                except Exception:
                    pass
    
    async def broadcast(self, message: dict):
        async with self._lock:
            for connection in self.active_connections.values():
                try:
                    await connection.send_json(message)
                except Exception:
                    pass
    
    async def handle_webrtc_signal(self, room_id: str, from_client: str, signal_data: dict):
        async with self._lock:
            if room_id in self.rooms:
                message = {
                    "type": "webrtc_signal",
                    "from": from_client,
                    "data": signal_data
                }
                for client_id, ws in self.rooms[room_id].users.items():
                    if client_id != from_client:
                        try:
                            await ws.send_json(message)
                        except Exception:
                            pass
    
    async def handle_chat_message(self, room_id: str, from_client: str, content: str):
        message = {
            "type": "chat_message",
            "from": from_client,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_room_message(room_id, message)
    
    def get_room_users(self, room_id: str) -> int:
        if room_id in self.rooms:
            return self.rooms[room_id].user_count
        return 0


manager = ConnectionManager()
