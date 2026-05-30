#!/usr/bin/env python
import os
import sys

def check_dependencies():
    package_import_names = {
        'flask': 'flask',
        'flask_socketio': 'flask_socketio',
        'eventlet': 'eventlet',
        'torch': 'torch',
        'transformers': 'transformers'
    }
    
    required_packages = [
        'flask',
        'flask_socketio',
        'eventlet'
    ]
    
    optional_packages = [
        'torch',
        'transformers'
    ]
    
    print("=" * 60)
    print("检查依赖包...")
    print("=" * 60)
    
    missing_required = []
    for pkg in required_packages:
        try:
            __import__(package_import_names[pkg])
            print(f"✓ {pkg}")
        except ImportError:
            print(f"✗ {pkg} (缺失)")
            missing_required.append(pkg)
    
    print("\n可选依赖 (BERT模型):")
    missing_optional = []
    for pkg in optional_packages:
        try:
            __import__(package_import_names[pkg])
            print(f"✓ {pkg}")
        except Exception:
            print(f"✗ {pkg} (将使用规则匹配)")
            missing_optional.append(pkg)
    
    if missing_required:
        print(f"\n缺少必需依赖包: {', '.join(missing_required)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print(f"\n提示: 缺少BERT相关依赖，将使用基于规则的情感分析。")
        print("如需使用BERT模型，请安装: pip install torch transformers")
    
    return True

def main():
    if not check_dependencies():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("启动客户对话情感分析系统...")
    print("=" * 60)
    
    from app import socketio, app
    
    print("\n系统启动成功!")
    print("访问地址: http://localhost:5002")
    print("按 Ctrl+C 停止服务\n")
    
    socketio.run(app, host='0.0.0.0', port=5002, debug=False)

if __name__ == '__main__':
    main()
