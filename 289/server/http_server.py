from aiohttp import web
import os
from config import Config


class HTTPServer:
    def __init__(self):
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_static('/static', 'static', name='static')
    
    async def index(self, request):
        index_path = os.path.join('static', 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return web.Response(text=content, content_type='text/html')
        else:
            return web.Response(text='页面不存在', status=404)
    
    async def start(self):
        print(f"HTTP服务器启动在 http://{Config.HTTP_HOST}:{Config.HTTP_PORT}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, Config.HTTP_HOST, Config.HTTP_PORT)
        await site.start()
