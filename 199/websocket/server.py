import asyncio
import json
import websockets
from typing import Set, Dict, Any
import threading
import time

from config import WEBSOCKET_CONFIG
from flink import StreamProcessingJob
from suggestion import LiveAdvisor


class WebSocketServer:
    def __init__(self, stream_job: StreamProcessingJob, advisor: LiveAdvisor = None):
        self.host = WEBSOCKET_CONFIG['host']
        self.port = WEBSOCKET_CONFIG['port']
        self.stream_job = stream_job
        self.advisor = advisor
        self._clients: Set[websockets.WebSocketServerProtocol] = set()
        self._latest_data: Dict[str, Any] = {}
        self._running = False

    async def _register(self, websocket: websockets.WebSocketServerProtocol):
        self._clients.add(websocket)
        print(f"新客户端连接，当前连接数: {len(self._clients)}")
        if self._latest_data:
            try:
                await websocket.send(json.dumps(self._latest_data, ensure_ascii=False))
            except:
                pass

    async def _unregister(self, websocket: websockets.WebSocketServerProtocol):
        self._clients.discard(websocket)
        print(f"客户端断开连接，当前连接数: {len(self._clients)}")

    async def _broadcast(self, data: Dict[str, Any]):
        if not self._clients:
            return
        message = json.dumps(data, ensure_ascii=False)
        disconnected = set()
        for client in self._clients:
            try:
                await client.send(message)
            except Exception as e:
                disconnected.add(client)
        for client in disconnected:
            self._clients.discard(client)

    def _on_stream_data(self, data: Dict[str, Any]):
        self._latest_data = data
        if self.advisor:
            suggestion = self.advisor.analyze(data)
            if suggestion:
                data['suggestion'] = suggestion
        asyncio.run_coroutine_threadsafe(
            self._broadcast(data),
            self._loop
        )

    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol):
        await self._register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        await websocket.send(json.dumps({'type': 'pong', 'timestamp': time.time()}))
                except:
                    pass
        finally:
            await self._unregister(websocket)

    async def _start_server(self):
        self._loop = asyncio.get_running_loop()
        self.stream_job.register_callback(self._on_stream_data)
        self.stream_job.start()

        if self.advisor:
            self.advisor.start()

        async with websockets.serve(self._handle_client, self.host, self.port):
            print(f"WebSocket服务器已启动: ws://{self.host}:{self.port}")
            print(f"当前连接数: {len(self._clients)}")
            await asyncio.Future()

    def start(self):
        self._running = True
        asyncio.run(self._start_server())

    def stop(self):
        self._running = False
        self.stream_job.stop()
        if self.advisor:
            self.advisor.stop()
        for client in list(self._clients):
            asyncio.run_coroutine_threadsafe(client.close(), self._loop)


def main():
    from flink import StreamProcessingJob
    from suggestion import LiveAdvisor

    stream_job = StreamProcessingJob(use_pyflink=False)
    advisor = LiveAdvisor()

    server = WebSocketServer(stream_job, advisor)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == '__main__':
    main()
