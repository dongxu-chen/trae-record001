#!/usr/bin/env python3
import subprocess
import sys


def build():
    try:
        result = subprocess.run(
            ["hugo", "--minify", "--gc", "--cleanDestinationDir"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Hugo 构建失败: {result.stderr}")
            sys.exit(1)
        print("Hugo 构建成功")
        print(result.stdout)
    except FileNotFoundError:
        print("错误: 未找到 hugo 命令，请确保已安装 Hugo")
        sys.exit(1)


if __name__ == "__main__":
    build()
