import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("测试导入机器人运动学库...")

try:
    import numpy as np
    print("  ✓ numpy 导入成功")
except ImportError as e:
    print(f"  ✗ numpy 导入失败: {e}")

try:
    import pinocchio as pin
    print("  ✓ pinocchio 导入成功")
    print(f"    Pinocchio 版本: {pin.__version__}")
except ImportError as e:
    print(f"  ✗ pinocchio 导入失败: {e}")

try:
    import meshcat
    print("  ✓ meshcat 导入成功")
except ImportError as e:
    print(f"  ✗ meshcat 导入失败: {e}")

try:
    from robot_kinematics import RobotKinematics
    print("  ✓ RobotKinematics 导入成功")
except ImportError as e:
    print(f"  ✗ RobotKinematics 导入失败: {e}")

try:
    from robot_kinematics import MeshCatVisualizer
    print("  ✓ MeshCatVisualizer 导入成功")
except ImportError as e:
    print(f"  ✗ MeshCatVisualizer 导入失败: {e}")

try:
    from robot_kinematics import WorkspaceAnalyzer
    print("  ✓ WorkspaceAnalyzer 导入成功")
except ImportError as e:
    print(f"  ✗ WorkspaceAnalyzer 导入失败: {e}")

try:
    from robot_kinematics import CollisionChecker
    print("  ✓ CollisionChecker 导入成功")
except ImportError as e:
    print(f"  ✗ CollisionChecker 导入失败: {e}")

urdf_path = os.path.join("examples", "urdf", "simple_arm.urdf")
if os.path.exists(urdf_path):
    print(f"\n✓ URDF 文件存在: {urdf_path}")
else:
    print(f"\n✗ URDF 文件不存在: {urdf_path}")

print("\n导入测试完成!")
