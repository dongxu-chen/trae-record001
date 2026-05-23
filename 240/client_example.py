import asyncio
import websockets
import json
import pyaudio
import argparse
from typing import Optional


class ASRWebSocketClient:
    def __init__(self, server_uri: str, hotwords: Optional[list] = None):
        self.server_uri = server_uri
        self.hotwords = hotwords or []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        self.websocket = None
        
    async def connect(self):
        print(f"连接到服务器: {self.server_uri}")
        self.websocket = await websockets.connect(self.server_uri)
        print("连接成功!")
        
        if self.hotwords:
            await self.send_hotwords(self.hotwords)
        
        await self.request_info()
    
    async def send_hotwords(self, hotwords: list):
        message = {
            'type': 'hotwords',
            'hotwords': hotwords
        }
        await self.websocket.send(json.dumps(message, ensure_ascii=False))
        print(f"已发送热词: {hotwords}")
    
    async def request_info(self):
        message = {'type': 'info'}
        await self.websocket.send(json.dumps(message))
    
    async def receive_results(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'partial':
                    print(f"\r[部分] {data.get('text', '')} "
                          f"(置信度: {data.get('confidence', 0):.1%})", end='', flush=True)
                elif msg_type == 'final':
                    print(f"\n[最终] {data.get('text', '')} "
                          f"(置信度: {data.get('confidence', 0):.1%})")
                elif msg_type == 'info':
                    print(f"[信息] 模型: {data.get('model', 'N/A')}, "
                          f"热词: {data.get('hotwords', [])}")
                elif msg_type == 'error':
                    print(f"[错误] {data.get('message', 'Unknown error')}")
                elif msg_type in ['config_ack', 'hotwords_ack']:
                    print(f"[确认] {msg_type}: {data.get('status', 'success')}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("\n服务器连接已关闭")
        except Exception as e:
            print(f"\n接收错误: {e}")
    
    async def send_audio_from_mic(self):
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        print("开始录音，请说话... (按 Ctrl+C 停止)")
        self.is_running = True
        
        try:
            while self.is_running:
                data = self.stream.read(1024, exception_on_overflow=False)
                await self.websocket.send(data)
                await asyncio.sleep(0.001)
                
        except Exception as e:
            print(f"录音错误: {e}")
        finally:
            self.stream.stop_stream()
            self.stream.close()
    
    async def run(self):
        await self.connect()
        
        receive_task = asyncio.create_task(self.receive_results())
        send_task = asyncio.create_task(self.send_audio_from_mic())
        
        try:
            await asyncio.gather(receive_task, send_task)
        except KeyboardInterrupt:
            print("\n正在停止...")
        finally:
            self.is_running = False
            if self.websocket:
                await self.websocket.close()
            self.audio.terminate()


def main():
    parser = argparse.ArgumentParser(description='ASR WebSocket 客户端')
    parser.add_argument('--server', type=str, default='ws://localhost:8765',
                       help='WebSocket服务器地址')
    parser.add_argument('--hotwords', type=str, default='',
                       help='自定义热词，用逗号分隔')
    args = parser.parse_args()
    
    hotwords = [w.strip() for w in args.hotwords.split(',') if w.strip()] if args.hotwords else []
    
    client = ASRWebSocketClient(args.server, hotwords)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n客户端已停止")


if __name__ == '__main__':
    main()
