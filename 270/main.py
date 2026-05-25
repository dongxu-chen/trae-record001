import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from visualizer import PathPlannerVisualizer


def main():
    print("=" * 50)
    print("机器人路径规划可视化系统")
    print("=" * 50)
    print("\n快捷键说明:")
    print("  S - 设置起点")
    print("  G - 设置终点")
    print("  D - 绘制障碍物模式")
    print("  C - 清除所有障碍物")
    print("  P - 开始路径规划")
    print("  A - 开始/停止动态障碍动画")
    print("  T - 显示/隐藏RRT树")
    print("  X - 清除所有路径")
    print("=" * 50)
    print("\n启动可视化界面...")

    visualizer = PathPlannerVisualizer(width=1000, height=700)
    visualizer.run()


if __name__ == "__main__":
    main()
