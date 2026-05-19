import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import init_database

if __name__ == '__main__':
    print("正在初始化数据库...")
    try:
        init_database()
        print("数据库初始化成功！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        sys.exit(1)
