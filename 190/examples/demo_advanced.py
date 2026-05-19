import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robot_kinematics import (
    RobotKinematics,
    MeshCatVisualizer,
    TrajectoryPlanner,
    DynamicsSimulator,
    DragTeach,
)


def demo_trajectory_planning(robot, viz=None):
    print("\n" + "=" * 60)
    print("1. 笛卡尔空间轨迹规划")
    print("=" * 60)

    planner = TrajectoryPlanner(robot)

    q_start = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, 0.0, 0.0])
    q_end = np.array([np.pi / 4, -np.pi / 3, np.pi / 3, 0.0, np.pi / 6, 0.0])

    pose_start = robot.forward_kinematics(q_start)
    pose_end = robot.forward_kinematics(q_end)

    print(f"\n  起点位置: {np.round(pose_start[:3, 3], 4)}")
    print(f"  终点位置: {np.round(pose_end[:3, 3], 4)}")

    print("\n  [1.1] 直线插补轨迹...")
    linear_poses = planner.linear_interpolation(
        pose_start, pose_end, num_waypoints=50
    )
    print(f"    生成 {len(linear_poses)} 个直线插补位姿")
    print(f"    起点: {np.round(linear_poses[0][:3, 3], 4)}")
    print(f"    终点: {np.round(linear_poses[-1][:3, 3], 4)}")

    print("\n  [1.2] 圆弧插补轨迹...")
    point1 = pose_start[:3, 3]
    point2 = np.array([0.4, 0.3, 0.3])
    point3 = pose_end[:3, 3]
    arc_poses = planner.three_point_arc(
        point1, point2, point3, num_waypoints=50
    )
    print(f"    三点: {np.round(point1, 3)} -> {np.round(point2, 3)} -> {np.round(point3, 3)}")
    print(f"    生成 {len(arc_poses)} 个圆弧插补位姿")

    print("\n  [1.3] 关节空间五次多项式轨迹...")
    time_steps, q_traj, dq_traj, ddq_traj = planner.quintic_trajectory(
        q_start, q_end, duration=3.0, num_waypoints=100
    )
    print(f"    时长: {time_steps[-1]:.1f}s, 步数: {len(time_steps)}")
    print(f"    最大关节速度: {np.max(np.abs(dq_traj)):.3f} rad/s")
    print(f"    最大关节加速度: {np.max(np.abs(ddq_traj)):.3f} rad/s²")

    print("\n  [1.4] 最小Jerk轨迹...")
    time_steps_mj, q_traj_mj, dq_traj_mj, ddq_traj_mj = planner.minimum_jerk_trajectory(
        q_start, q_end, duration=3.0, num_waypoints=100
    )
    print(f"    最小Jerk轨迹生成完成")
    print(f"    最大关节速度: {np.max(np.abs(dq_traj_mj)):.3f} rad/s")

    print("\n  [1.5] 轨迹光滑性检查...")
    is_smooth, smooth_info = planner.check_trajectory_smoothness(
        q_traj, max_joint_velocity=np.pi, max_joint_acceleration=4 * np.pi
    )
    print(f"    光滑性: {'通过' if is_smooth else '不通过'}")
    print(f"    最大速度: {smooth_info['max_velocity']:.3f} / {smooth_info['velocity_limit']:.3f}")
    print(f"    最大加速度: {smooth_info['max_acceleration']:.3f} / {smooth_info['acceleration_limit']:.3f}")

    if viz is not None:
        print("\n  在可视化器中绘制轨迹...")
        viz.display(q_start)

        positions = np.array([pose[:3, 3] for pose in linear_poses])
        viz.draw_trajectory("linear_traj", positions, color=0x0000ff, point_size=0.005)

        arc_positions = np.array([pose[:3, 3] for pose in arc_poses])
        viz.draw_trajectory("arc_traj", arc_positions, color=0xff0000, point_size=0.005)

        print("  蓝色: 直线轨迹, 红色: 圆弧轨迹")

    return q_traj, time_steps


def demo_dynamics_simulation(robot, viz=None):
    print("\n" + "=" * 60)
    print("2. 动力学仿真")
    print("=" * 60)

    dynamics = DynamicsSimulator(robot)

    q0 = np.array([0.0, -np.pi / 6, np.pi / 6, 0.0, 0.0, 0.0])
    dq0 = np.zeros(6)

    print("\n  [2.1] 机器人质量矩阵 (M)...")
    M = dynamics.compute_mass_matrix(q0)
    print(f"    质量矩阵形状: {M.shape}")
    print(f"    条件数: {np.linalg.cond(M):.2f}")
    print(f"    行列式: {np.linalg.det(M):.6f}")

    print("\n  [2.2] 重力补偿力矩...")
    g = dynamics.compute_gravity_vector(q0)
    print(f"    重力补偿: {np.round(g, 4)} N·m")

    print("\n  [2.3] 恒力响应仿真 (给关节2施加5 N·m力矩)...")
    tau_constant = np.zeros(6)
    tau_constant[1] = 5.0

    sim_result = dynamics.simulate_constant_torque(
        q0, dq0, tau_constant, duration=2.0, dt=0.01
    )
    print(f"    仿真时长: {sim_result['time'][-1]:.2f}s")
    print(f"    最终关节角: {np.round(sim_result['q'][-1], 4)}")
    print(f"    最终关节速度: {np.round(sim_result['dq'][-1], 4)}")

    print("\n  [2.4] PD控制位置跟踪...")
    q_target = np.array([0.0, -np.pi / 3, np.pi / 3, 0.0, 0.0, 0.0])
    kp = np.ones(6) * 50.0
    kd = np.ones(6) * 5.0

    pd_result = dynamics.simulate_pd_control(
        q0, dq0, q_target, kp, kd, duration=3.0, dt=0.01
    )
    final_error = np.linalg.norm(pd_result['q'][-1] - q_target)
    print(f"    目标关节角: {np.round(q_target, 4)}")
    print(f"    最终关节角: {np.round(pd_result['q'][-1], 4)}")
    print(f"    最终误差: {final_error:.6f} rad")

    print("\n  [2.5] 能量分析...")
    ke = dynamics.compute_kinetic_energy(q0, dq0)
    pe = dynamics.compute_potential_energy(q0)
    total = dynamics.compute_total_energy(q0, dq0)
    print(f"    初始动能: {ke:.4f} J")
    print(f"    初始势能: {pe:.4f} J")
    print(f"    总能量: {total:.4f} J")

    print("\n  [2.6] 逆动力学 (RNEA)...")
    ddq_test = np.zeros(6)
    tau_id = dynamics.compute_inverse_dynamics(q0, dq0, ddq_test)
    print(f"    保持当前位姿所需力矩: {np.round(tau_id, 4)} N·m")

    if viz is not None:
        print("\n  在可视化器中播放PD控制仿真...")
        try:
            for i in range(0, len(pd_result['q']), 5):
                viz.display(pd_result['q'][i])
                import time
                time.sleep(0.02)
        except Exception:
            pass

    return sim_result, pd_result


def demo_drag_teach(robot, viz=None):
    print("\n" + "=" * 60)
    print("3. 拖拽示教功能")
    print("=" * 60)

    drag_teach = DragTeach(robot, viz)

    q_initial = np.array([0.0, -np.pi / 4, np.pi / 4, 0.0, 0.0, 0.0])

    print("\n  [3.1] 启动拖拽示教模式...")
    drag_teach.start_drag(q_initial)
    print(f"    初始末端位置: {np.round(drag_teach.drag_start_pose[:3, 3], 4)}")

    print("\n  [3.2] 生成示例拖拽路径 (8字形)...")
    num_points = 100
    waypoints = np.zeros((num_points, 3))
    start_pos = drag_teach.drag_start_pose[:3, 3].copy()

    for i in range(num_points):
        t = i / (num_points - 1) * 2 * np.pi
        waypoints[i] = start_pos + np.array([
            0.15 * np.sin(t),
            0.15 * np.sin(t) * np.cos(t),
            0.05 * np.sin(2 * t)
        ])

    print(f"    生成 {num_points} 个路径点")
    print(f"    路径范围: X [{np.min(waypoints[:, 0]):.3f}, {np.max(waypoints[:, 0]):.3f}]")
    print(f"            Y [{np.min(waypoints[:, 1]):.3f}, {np.max(waypoints[:, 1]):.3f}]")
    print(f"            Z [{np.min(waypoints[:, 2]):.3f}, {np.max(waypoints[:, 2]):.3f}]")

    print("\n  [3.3] 执行拖拽轨迹跟踪...")
    q_traj, _ = drag_teach.simulate_drag_along_path(
        waypoints, q_initial, num_steps_per_segment=5
    )
    print(f"    生成 {len(q_traj)} 个关节角轨迹点")

    print("\n  [3.4] 停止拖拽并生成轨迹...")
    recorded = drag_teach.stop_drag()
    print(f"    记录点位: {len(recorded['positions'])}")

    print("\n  [3.5] 轨迹后处理 (平滑+速度/加速度计算)...")
    processed = drag_teach.generate_trajectory_from_demonstration(
        recorded, smoothing=True, smooth_sigma=2.0
    )
    print(f"    平滑后轨迹长度: {len(processed['positions'])}")
    print(f"    最大速度: {np.max(np.linalg.norm(processed['velocities'], axis=1)):.4f} m/s")
    print(f"    最大加速度: {np.max(np.linalg.norm(processed['accelerations'], axis=1)):.4f} m/s²")

    print("\n  [3.6] 检查轨迹奇异性...")
    singular_count = 0
    for q in processed['joint_angles'][::10]:
        if robot.is_singular(q, threshold=1e-2):
            singular_count += 1
    singular_ratio = singular_count / (len(processed['joint_angles']) / 10) * 100
    print(f"    奇异位形比例: {singular_ratio:.1f}%")

    if viz is not None:
        print("\n  在可视化器中绘制拖拽轨迹...")
        viz.draw_trajectory(
            "drag_original", recorded['positions'], color=0xff8800, point_size=0.006
        )
        viz.draw_trajectory(
            "drag_smoothed", processed['positions'], color=0x00ff00, point_size=0.004
        )
        print("  橙色: 原始拖拽, 绿色: 平滑后")

    return processed


def main():
    urdf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "urdf",
        "simple_arm.urdf"
    )

    print("=" * 60)
    print("高级功能演示: 轨迹规划 + 动力学 + 拖拽示教")
    print("=" * 60)

    robot = RobotKinematics(urdf_path, end_effector_name="tool0")
    print(f"\n机器人加载完成: {robot.model.name}, 自由度: {robot.model.nq}")

    viz = None
    try:
        viz = MeshCatVisualizer(robot)
        print("\n可视化器已启动，请在浏览器中打开 MeshCat URL")
    except Exception as e:
        print(f"\n可视化器跳过: {e}")

    q_traj, time_steps = demo_trajectory_planning(robot, viz)
    sim_result, pd_result = demo_dynamics_simulation(robot, viz)
    drag_traj = demo_drag_teach(robot, viz)

    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)

    if viz is not None:
        try:
            input("\n按Enter键关闭可视化器...")
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            viz.clear()


if __name__ == "__main__":
    main()
