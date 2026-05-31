import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        async with self._lock:
            await websocket.accept()
            self._active_connections[client_id] = websocket

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            if client_id in self._active_connections:
                del self._active_connections[client_id]

    async def send_to_client(self, client_id: str, message: dict) -> None:
        try:
            async with self._lock:
                websocket = self._active_connections.get(client_id)
                if websocket:
                    await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message to client {client_id}: {e}")

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            for client_id, websocket in list(self._active_connections.items()):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to client {client_id}: {e}")
                    del self._active_connections[client_id]

    async def get_client_count(self) -> int:
        async with self._lock:
            return len(self._active_connections)

    async def get_active_clients(self) -> List[str]:
        async with self._lock:
            return list(self._active_connections.keys())
