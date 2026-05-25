import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction.hybrid_predictor import HybridPredictor
from cache.redis_cache import RedisCache
from server.websocket_server import WebSocketServer
from server.http_server import HTTPServer
from config import Config


async def main():
    print("=" * 60)
    print("城市公交车到站时间预测系统")
    print("=" * 60)
    print()
    
    print("正在初始化预测模型...")
    predictor = HybridPredictor()
    print("预测模型初始化完成")
    print()
    
    print("正在连接Redis...")
    cache = RedisCache()
    print("Redis连接完成")
    print()
    
    print("正在启动服务器...")
    ws_server = WebSocketServer(predictor, cache)
    http_server = HTTPServer()
    
    print(f"HTTP服务器: http://{Config.HTTP_HOST}:{Config.HTTP_PORT}")
    print(f"WebSocket服务器: ws://{Config.WEBSOCKET_HOST}:{Config.WEBSOCKET_PORT}")
    print()
    
    await asyncio.gather(
        ws_server.start(),
        http_server.start()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n系统已停止")
    except Exception as e:
        print(f"\n系统错误: {e}")
        import traceback
        traceback.print_exc()
