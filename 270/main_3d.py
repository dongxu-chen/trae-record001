import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from visualizer3d import PathPlanner3DVisualizer


def main():
    print("=" * 60)
    print("3D 多机器人路径规划可视化系统")
    print("=" * 60)
    print("\n功能特性:")
    print("  ✓ 3楼层地图 - 大厅/办公区/会议室")
    print("  ✓ 电梯/楼梯连接点 - 跨楼层路径规划")
    print("  ✓ 3D A*算法 - 支持跨楼层路径搜索")
    print("  ✓ 多机器人协同 - 速度障碍法避障")
    print("  ✓ 机器人仿真 - 差分/全向驱动模型")
    print("  ✓ 速度指令输出 - 实时vx, vy, vtheta")
    print("\n操作说明:")
    print("  1F/2F/3F 按钮 - 切换楼层")
    print("  3D路径规划模式 - 单机器人跨楼层规划")
    print("  多机器人协同模式 - 多机协同避障")
    print("  鼠标点击 - 设置起终点/添加机器人")
    print("  S/G/P/A - 快捷键操作")
    print("=" * 60)
    print("\n启动可视化界面...\n")

    visualizer = PathPlanner3DVisualizer(width=1200, height=750)
    visualizer.run()


if __name__ == "__main__":
    main()
