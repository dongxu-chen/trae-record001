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


def demo_multi_guess_ik(robot):
    print("\n" + "=" * 60)
    print("1. 多初值逆运动学演示")
    print("=" * 60)

    target_position = np.array([0.45, 0.15, 0.35])
    print(f"\n目标位置: {target_position}")

    q_single, success_single, error_single = robot.inverse_kinematics_position(
        target_position,
        initial_guess=np.zeros(6),
        max_iter=500,
        tolerance=1e-4
    )
    print(f"\n  单初值求解:")
    print(f"    成功: {success_single}, 误差: {error_single:.6f}")
    if success_single:
        print(f"    关节角: {np.round(q_single, 4)}")
        print(f"    可操作性: {robot.manipulability(q_single):.6f}")
        print(f"    条件数: {robot.condition_number(q_single):.2f}")

    print(f"\n  多初值求解 (20个随机初值):")
    q_multi, success_multi, error_multi, info = robot.inverse_kinematics_position_multi_guess(
        target_position,
        num_guesses=20,
        max_iter=500,
        tolerance=1e-4
    )

    print(f"    找到有效解数量: {info['num_solutions']}")
    if success_multi:
        print(f"    最优解误差: {error_multi:.6f}")
        print(f"    最优解关节角: {np.round(q_multi, 4)}")
        print(f"    可操作性: {info['manipulability']:.6f}")
        print(f"    条件数: {info['condition_number']:.2f}")
        print(f"    综合评分: {info['score']:.6f}")

    return q_multi if success_multi else q_single


def demo_mesh_collision(collision_checker, robot):
    print("\n" + "=" * 60)
    print("2. 精确网格碰撞检测演示")
    print("=" * 60)

    q_safe = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, 0.0, 0.0])
    q_risky = np.array([0.0, -np.pi / 2, np.pi / 2, 0.0, 0.0, 0.0])

    print(f"\n  安全姿态检测:")
    collision_quick = collision_checker.check_collision(q_safe)
    collision_mesh = collision_checker.check_mesh_collision(q_safe)
    dist_mesh, obj1, obj2 = collision_checker.compute_minimum_mesh_distance(q_safe)

    print(f"    快速碰撞检测: {collision_quick}")
    print(f"    精确网格碰撞: {collision_mesh}")
    print(f"    最小网格距离: {dist_mesh:.6f} m")
    if obj1 and obj2:
        print(f"    最近物体对: {obj1} <-> {obj2}")

    print(f"\n  风险姿态检测:")
    collision_quick = collision_checker.check_collision(q_risky)
    collision_mesh = collision_checker.check_mesh_collision(q_risky)
    dist_mesh, obj1, obj2 = collision_checker.compute_minimum_mesh_distance(q_risky)

    print(f"    快速碰撞检测: {collision_quick}")
    print(f"    精确网格碰撞: {collision_mesh}")
    print(f"    最小网格距离: {dist_mesh:.6f} m")

    colliding_pairs = collision_checker.get_colliding_pairs(q_risky, use_mesh=True)
    if colliding_pairs:
        print(f"    碰撞对: {colliding_pairs}")

    print(f"\n  添加环境障碍物 (盒子):")
    collision_checker.add_environment_box(
        "obstacle1",
        position=np.array([0.3, 0.0, 0.2]),
        size=np.array([0.15, 0.15, 0.15])
    )

    collision_env = collision_checker.check_collision_with_env(q_safe, use_mesh=True)
    print(f"    环境碰撞检测: {collision_env}")

    collision_checker.add_environment_sphere(
        "obstacle2",
        position=np.array([0.5, 0.2, 0.4]),
        radius=0.08
    )

    collision_env2 = collision_checker.check_collision_with_env(q_safe, use_mesh=True)
    print(f"    加入球体后的环境碰撞: {collision_env2}")

    collision_checker.clear_environment()


def demo_workspace_enhanced(workspace, robot):
    print("\n" + "=" * 60)
    print("3. 工作空间分析 (含奇异位形检测)")
    print("=" * 60)

    print("\n  采样工作空间点 (含信息)...")
    info = workspace.sample_workspace_with_info(num_samples=2000)

    num_singular = np.sum(info['is_singular'])
    singular_ratio = num_singular / len(info['is_singular']) * 100

    print(f"  采样总数: {len(info['positions'])}")
    print(f"  奇异位形数量: {num_singular} ({singular_ratio:.1f}%)")

    if num_singular > 0:
        singular_positions = info['positions'][info['is_singular']]
        print(f"  奇异位形位置范围:")
        print(f"    X: [{np.min(singular_positions[:, 0]):.3f}, {np.max(singular_positions[:, 0]):.3f}]")
        print(f"    Y: [{np.min(singular_positions[:, 1]):.3f}, {np.max(singular_positions[:, 1]):.3f}]")
        print(f"    Z: [{np.min(singular_positions[:, 2]):.3f}, {np.max(singular_positions[:, 2]):.3f}]")

    print(f"\n  可操作性统计:")
    print(f"    平均值: {np.mean(info['manipulability']):.6f}")
    print(f"    最大值: {np.max(info['manipulability']):.6f}")
    print(f"    最小值: {np.min(info['manipulability']):.6f}")
    print(f"    中位数: {np.median(info['manipulability']):.6f}")

    print(f"\n  条件数统计:")
    cond = np.minimum(info['condition_numbers'], 1000)
    print(f"    平均值: {np.mean(cond):.2f}")
    print(f"    中位数: {np.median(cond):.2f}")

    print("\n  过滤奇异位形的工作空间采样...")
    positions_filtered = workspace.sample_workspace(
        num_samples=1000,
        filter_singular=True,
        remove_outliers=True
    )
    print(f"  过滤后样本数: {len(positions_filtered)}")

    print("\n  查找奇异区域...")
    singular_info = workspace.find_singular_regions(
        num_samples=5000,
        singular_threshold=1e-3
    )
    print(f"  奇异位形比例: {singular_info['singular_ratio'] * 100:.2f}%")

    return info


def demo_singularity_detection(robot):
    print("\n" + "=" * 60)
    print("4. 奇异性检测演示")
    print("=" * 60)

    q_normal = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, 0.0, 0.0])
    q_singular = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    print(f"\n  正常姿态:")
    print(f"    关节角: {np.round(q_normal, 3)}")
    print(f"    是否奇异: {robot.is_singular(q_normal)}")
    print(f"    最小奇异值: {np.min(np.linalg.svd(robot.jacobian(q_normal), compute_uv=False)):.6f}")
    print(f"    条件数: {robot.condition_number(q_normal):.2f}")

    print(f"\n  奇异姿态 (全零位形):")
    print(f"    关节角: {np.round(q_singular, 3)}")
    print(f"    是否奇异: {robot.is_singular(q_singular, threshold=1e-2)}")
    print(f"    最小奇异值: {np.min(np.linalg.svd(robot.jacobian(q_singular), compute_uv=False)):.6f}")
    print(f"    条件数: {robot.condition_number(q_singular):.2f}")


def main():
    urdf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "urdf",
        "simple_arm.urdf"
    )

    print("=" * 60)
    print("增强版机器人运动学库演示")
    print("=" * 60)

    robot = RobotKinematics(urdf_path, end_effector_name="tool0")
    print(f"\n机器人加载完成: {robot.model.name}")
    print(f"自由度: {robot.model.nq}")

    workspace = WorkspaceAnalyzer(robot)
    collision_checker = CollisionChecker(robot)

    q_best = demo_multi_guess_ik(robot)
    demo_mesh_collision(collision_checker, robot)
    demo_workspace_enhanced(workspace, robot)
    demo_singularity_detection(robot)

    print("\n" + "=" * 60)
    print("启动可视化演示...")
    print("=" * 60)

    try:
        viz = MeshCatVisualizer(robot)
        print("\n请在浏览器中打开 MeshCat URL 查看可视化")

        viz.display(q_best)

        print("\n按 Enter 键绘制工作空间点云...")
        input()

        viz.draw_sphere("target", np.array([0.45, 0.15, 0.35]),
                        radius=0.05, color=0xff0000)

        workspace.visualize_workspace(
            viz,
            num_samples=2000,
            filter_singular=True,
            color_by_manipulability=True
        )

        print("\n工作空间已绘制 (红色=高可操作性, 蓝色=低可操作性)")
        print("按 Ctrl+C 或关闭浏览器窗口退出")

        while True:
            try:
                input()
                break
            except KeyboardInterrupt:
                break

    except Exception as e:
        print(f"\n可视化跳过: {e}")

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
