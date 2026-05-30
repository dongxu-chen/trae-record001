import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import create_app
from config import Config

Config.ensure_dirs()

if __name__ == '__main__':
    app = create_app()
    print("=" * 60)
    print("显著性目标检测 API 服务")
    print("=" * 60)
    print(f"服务地址: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print(f"API文档: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}/")
    print(f"设备: {Config.get_device()}")
    print("=" * 60)
    print()
    
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.DEBUG,
        threaded=True
    )
