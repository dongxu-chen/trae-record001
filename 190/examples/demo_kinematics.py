import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robot_kinematics import (
    RobotKinematics,
    MeshCatVisualizer,
    WorkspaceAnalyzer,
    CollisionChecker
)


def main():
    urdf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "urdf",
        "simple_arm.urdf"
    )

    print("=" * 60)
    print("机器人运动学库演示")
    print("=" * 60)

    print("\n1. 加载机器人模型...")
    robot = RobotKinematics(urdf_path, end_effector_name="tool0")
    print(f"   机器人名称: {robot.model.name}")
    print(f"   关节数量: {robot.model.nq}")
    print(f"   关节名称: {robot.get_joint_names()}")
    print(f"   末端执行器: {robot.end_effector_name}")

    lower, upper = robot.get_joint_limits()
    print(f"   关节下限: {lower}")
    print(f"   关节上限: {upper}")

    print("\n2. 正运动学测试...")
    q_test = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, np.pi / 6, 0.0])
    pose = robot.forward_kinematics(q_test)
    print(f"   测试关节角度: {np.round(q_test, 3)}")
    print(f"   末端位姿矩阵:")
    print(np.round(pose, 4))
    print(f"   末端位置: {np.round(pose[:3, 3], 4)}")

    print("\n3. 雅可比矩阵计算...")
    J = robot.jacobian(q_test)
    print(f"   雅可比矩阵形状: {J.shape}")
    print(f"   雅可比矩阵:")
    print(np.round(J, 4))

    manipulability = robot.manipulability(q_test)
    print(f"   可操作性: {manipulability:.6f}")

    print("\n4. 逆运动学测试...")
    target_position = np.array([0.4, 0.2, 0.3])
    q_guess = np.zeros(6)
    q_ik, success, error = robot.inverse_kinematics_position(
        target_position,
        initial_guess=q_guess,
        max_iter=500,
        tolerance=1e-4
    )
    print(f"   目标位置: {target_position}")
    print(f"   求解成功: {success}")
    print(f"   最终误差: {error:.6f}")
    print(f"   求解关节角: {np.round(q_ik, 4)}")
    
    if success:
        actual_pos = robot.get_frame_position(q_ik, robot.end_effector_name)
        print(f"   实际位置: {np.round(actual_pos, 4)}")
        print(f"   位置误差: {np.linalg.norm(target_position - actual_pos):.6f}")

    print("\n5. 碰撞检测测试...")
    collision_checker = CollisionChecker(robot)
    q_safe = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, 0.0, 0.0])
    q_collision = np.array([0.0, -np.pi / 2, np.pi / 2, 0.0, 0.0, 0.0])
    
    is_collision_safe = collision_checker.check_collision(q_safe)
    is_collision_bad = collision_checker.check_collision(q_collision)
    print(f"   安全姿态碰撞: {is_collision_safe}")
    print(f"   风险姿态碰撞: {is_collision_bad}")
    
    min_dist = collision_checker.compute_minimum_distance(q_safe)
    print(f"   安全姿态最小距离: {min_dist:.4f} m")

    print("\n6. 工作空间分析...")
    workspace = WorkspaceAnalyzer(robot)
    print("   采样工作空间点 (5000个样本)...")
    points = workspace.sample_workspace(num_samples=5000)
    min_bound, max_bound = workspace.compute_workspace_bounds(num_samples=5000)
    print(f"   工作空间范围:")
    print(f"     X: [{min_bound[0]:.3f}, {max_bound[0]:.3f}] m")
    print(f"     Y: [{min_bound[1]:.3f}, {max_bound[1]:.3f}] m")
    print(f"     Z: [{min_bound[2]:.3f}, {max_bound[2]:.3f}] m")

    print("\n7. 可视化演示...")
    print("   启动MeshCat可视化器...")
    viz = MeshCatVisualizer(robot)
    print("   请在浏览器中打开显示的URL查看可视化")
    
    viz.display(q_test)
    viz.draw_frame("ee_frame", pose, size=0.1)
    viz.draw_sphere("target", target_position, radius=0.05, color=0xff0000)

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    try:
        input("\n按Enter键关闭可视化器...")
    except KeyboardInterrupt:
        pass
    finally:
        viz.clear()


if __name__ == "__main__":
    main()
