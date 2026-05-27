#!/usr/bin/env python3
from app.routes import create_app
import os

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print("=" * 50)
    print("🛡️  垃圾邮件过滤系统 API")
    print("=" * 50)
    print(f"📊 服务器地址: http://localhost:{port}")
    print(f"📋 健康检查: http://localhost:{port}/api/health")
    print(f"📈 仪表盘: http://localhost:{port}/api/dashboard")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
