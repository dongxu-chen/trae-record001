import os
import sys
import uvicorn
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import create_app


def main():
    print("="*70)
    print("电影票房预测平台")
    print("="*70)
    print("\n启动 FastAPI 服务...")
    print("API文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/health")
    print("="*70 + "\n")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == '__main__':
    main()
