import json
import asyncio
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect

from schemas import WsClientMessage, SAMRequest, SAMResponse, WsServerMessage
from sam_model import sam_service
from image_service import image_service


class WebSocketHandler:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_message(self, websocket: WebSocket, message: WsServerMessage):
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
    
    async def broadcast(self, message: WsServerMessage):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message.model_dump_json())
            except Exception as e:
                print(f"Error broadcasting message: {e}")
                self.disconnect(connection)
    
    async def handle_message(self, websocket: WebSocket, raw_message: str):
        try:
            message = WsClientMessage(**json.loads(raw_message))
        except Exception as e:
            print(f"Error parsing WebSocket message: {e}")
            return
        
        if message.type == 'ping':
            await self.send_message(websocket, WsServerMessage(type='pong', payload=None))
        
        elif message.type == 'sam_predict':
            await self.handle_sam_predict(websocket, message.payload)
        
        elif message.type == 'sam_reset':
            await self.handle_sam_reset(websocket, message.payload)
    
    async def handle_sam_predict(self, websocket: WebSocket, payload):
        try:
            request = SAMRequest(**payload)
        except Exception as e:
            await self.send_message(
                websocket,
                WsServerMessage(
                    type='sam_error',
                    payload={'error': f'Invalid request: {str(e)}'}
                )
            )
            return
        
        if not sam_service.model_loaded:
            await self.send_message(
                websocket,
                WsServerMessage(
                    type='sam_error',
                    payload={'error': 'SAM model not loaded'}
                )
            )
            return
        
        try:
            await self.send_message(
                websocket,
                WsServerMessage(type='sam_progress', payload={'progress': 20})
            )
            
            image = image_service.get_image_array(request.imageId)
            if image is None:
                await self.send_message(
                    websocket,
                    WsServerMessage(
                        type='sam_error',
                        payload={'error': 'Image not found'}
                    )
                )
                return
            
            await self.send_message(
                websocket,
                WsServerMessage(type='sam_progress', payload={'progress': 50})
            )
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: sam_service.predict(
                    image_id=request.imageId,
                    point=request.point,
                    image=image
                )
            )
            
            if result is None:
                await self.send_message(
                    websocket,
                    WsServerMessage(
                        type='sam_error',
                        payload={'error': 'SAM prediction failed'}
                    )
                )
                return
            
            await self.send_message(
                websocket,
                WsServerMessage(type='sam_progress', payload={'progress': 90})
            )
            
            await self.send_message(
                websocket,
                WsServerMessage(type='sam_result', payload=result)
            )
            
            await self.send_message(
                websocket,
                WsServerMessage(type='sam_progress', payload={'progress': 100})
            )
            
        except Exception as e:
            print(f"SAM prediction error: {e}")
            await self.send_message(
                websocket,
                WsServerMessage(
                    type='sam_error',
                    payload={'error': str(e)}
                )
            )
    
    async def handle_sam_reset(self, websocket: WebSocket, payload):
        try:
            image_id = payload.get('imageId') if payload else None
            if image_id:
                sam_service.reset_image(image_id)
        except Exception as e:
            print(f"Error resetting SAM: {e}")
    
    async def handle_connection(self, websocket: WebSocket):
        await self.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await self.handle_message(websocket, data)
        except WebSocketDisconnect:
            print("WebSocket client disconnected")
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.disconnect(websocket)


ws_handler = WebSocketHandler()
