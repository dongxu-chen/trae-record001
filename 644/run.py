#!/usr/bin/env python
import os
import sys

def check_dependencies():
    required = ['flask', 'jieba', 'pypinyin', 'numpy']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print("缺少依赖包，正在安装...")
        os.system(f"{sys.executable} -m pip install {' '.join(missing)}")
        print("依赖安装完成！")

def main():
    check_dependencies()
    
    from app import app
    
    print("=" * 50)
    print("电商搜索纠错系统启动中...")
    print("=" * 50)
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
