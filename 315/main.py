import sys
import tkinter as tk

try:
    import numpy
    import numba
    import matplotlib
except ImportError as e:
    print(f"缺少必要的依赖库: {e}")
    print("请先运行: pip install -r requirements.txt")
    sys.exit(1)

from gui import FractalGeneratorApp


def main():
    """程序主入口"""
    root = tk.Tk()
    
    try:
        root.iconbitmap(default='')
    except:
        pass
    
    app = FractalGeneratorApp(root)
    
    print("=" * 60)
    print("分形生成器 - Fractal Generator")
    print("=" * 60)
    print()
    print("支持的分形类型:")
    print("  • Mandelbrot集 - 经典复数分形，可无限缩放")
    print("  • Julia集 - 参数化复数分形")
    print("  • Burning Ship - 变体分形")
    print("  • 科赫雪花/曲线 - 几何分形")
    print("  • 谢尔宾斯基地毯/三角 - 自相似分形")
    print("  • 龙形曲线/希尔伯特曲线 - 空间填充曲线")
    print()
    print("操作说明:")
    print("  • 左键拖拽: 框选区域缩放")
    print("  • 滚轮: 以鼠标位置为中心缩放")
    print("  • 右键拖拽: 平移视图")
    print("  • R键: 重置视图")
    print("  • 空格键: 重新渲染")
    print("  • S键: 保存图像")
    print()
    print("=" * 60)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
