import asyncio
import json
import websockets
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from realtime_processor import RealTimeDataProcessor
import config


class WebSocketServer:
    def __init__(self):
        self.processor = RealTimeDataProcessor()
        self.connected_clients = set()
        self.push_interval = 1.0

    async def register_client(self, websocket):
        self.connected_clients.add(websocket)
        print(f"新客户端连接，当前连接数: {len(self.connected_clients)}")

    async def unregister_client(self, websocket):
        self.connected_clients.remove(websocket)
        print(f"客户端断开连接，当前连接数: {len(self.connected_clients)}")

    async def push_data_to_clients(self):
        while True:
            if self.connected_clients:
                try:
                    data = self.processor.get_summary_data()
                    message = json.dumps(data, ensure_ascii=False)
                    
                    disconnected = set()
                    for websocket in self.connected_clients:
                        try:
                            await websocket.send(message)
                        except Exception as e:
                            print(f"推送数据失败: {e}")
                            disconnected.add(websocket)
                    
                    for websocket in disconnected:
                        await self.unregister_client(websocket)
                        
                except Exception as e:
                    print(f"获取数据失败: {e}")
            
            await asyncio.sleep(self.push_interval)

    async def handle_client(self, websocket, path):
        await self.register_client(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('action') == 'ping':
                        await websocket.send(json.dumps({'action': 'pong', 'timestamp': datetime.now().isoformat()}))
                except Exception as e:
                    print(f"处理客户端消息失败: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start(self):
        print("启动实时数据处理器...")
        self.processor.start()
        
        print(f"启动WebSocket服务器: {config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
        
        push_task = asyncio.create_task(self.push_data_to_clients())
        
        async with websockets.serve(
            self.handle_client,
            config.WEBSOCKET_HOST,
            config.WEBSOCKET_PORT
        ):
            print("WebSocket服务器已启动，等待客户端连接...")
            await push_task


if __name__ == '__main__':
    server = WebSocketServer()
    asyncio.run(server.start())
