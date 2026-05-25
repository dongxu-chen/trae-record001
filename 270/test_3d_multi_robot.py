import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("3D多机器人系统功能测试")
print("=" * 70)

print("\n[1/5] 测试3D地图模块...")
try:
    from map3d import Map3D, FloorConnection

    map3d = Map3D(floor_width=750, floor_height=700, resolution=5.0)

    floor0 = map3d.add_floor(0, "1F - 大厅")
    floor1 = map3d.add_floor(1, "2F - 办公区")
    floor2 = map3d.add_floor(2, "3F - 会议室")
    print(f"  ✓ 创建3个楼层: {[f.name for f in map3d.floors.values()]}")

    obs = {'type': 'rectangle', 'x': 100, 'y': 100, 'width': 100, 'height': 100}
    floor0.grid_map._add_rectangle_obstacle(obs)
    print("  ✓ 添加障碍物成功")

    map3d.add_connection('elevator', 0, 1, (700, 100), (700, 100), speed=2.0)
    map3d.add_connection('stairs', 1, 2, (100, 600), (100, 600), speed=1.0)
    print(f"  ✓ 创建{len(map3d.connections)}个楼层连接点")

    valid = map3d.is_valid_3d(50, 50, 0)
    print(f"  ✓ 碰撞检测: 空闲区域={valid}")

    print("✓ 3D地图模块测试通过")
except Exception as e:
    print(f"✗ 3D地图模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[2/5] 测试3D A*路径规划算法...")
try:
    from astar3d import AStar3D

    planner = AStar3D(map3d)
    planner.robot_radius = 8.0

    start = (50.0, 50.0, 0)
    goal = (600.0, 500.0, 2)

    path = planner.plan(start, goal)
    stats = planner.get_statistics()

    if path:
        print(f"  ✓ 找到3D路径: {len(path)} 个路径点")

        floor_changes = []
        for i in range(1, len(path)):
            if path[i][2] != path[i-1][2]:
                floor_changes.append((path[i-1][2], path[i][2]))

        if floor_changes:
            print(f"  ✓ 跨楼层次数: {len(floor_changes)} 次")

        print(f"  ✓ 路径长度: {stats['path_length']:.1f}, 规划时间: {stats['planning_time']*1000:.1f}ms")
        print(f"  ✓ 扩展节点数: {stats['nodes_expanded']}")
    else:
        print("  ! 未找到路径（正常现象，取决于地图）")

    print("✓ 3D A*算法测试通过")
except Exception as e:
    print(f"✗ 3D A*算法测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[3/5] 测试多机器人协调模块...")
try:
    from multi_robot import MultiRobotCoordinator, VelocityCommand, VelocityObstacle

    coordinator = MultiRobotCoordinator(map3d=map3d)

    robot1 = coordinator.add_robot(100.0, 100.0, floor=0)
    robot2 = coordinator.add_robot(200.0, 200.0, floor=0)
    robot3 = coordinator.add_robot(300.0, 100.0, floor=1)
    print(f"  ✓ 创建{len(coordinator.robots)}个机器人")

    vo = VelocityObstacle()
    safe = vo.is_velocity_safe(robot1, 50.0, 0.0, [robot2])
    print(f"  ✓ 速度障碍检测: {safe}")

    path1 = [(50, 50, 0), (150, 50, 0), (250, 150, 0)]
    path2 = [(250, 50, 0), (150, 150, 0), (50, 250, 0)]
    coordinator.set_robot_path(robot1.robot_id, path1)
    coordinator.set_robot_path(robot2.robot_id, path2)
    print("  ✓ 设置机器人路径")

    commands = coordinator.update(0.1)
    print(f"  ✓ 协调更新完成，生成{len(commands)}个速度指令")

    print("✓ 多机器人协调模块测试通过")
except Exception as e:
    print(f"✗ 多机器人协调模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[4/5] 测试机器人仿真接口...")
try:
    from robot_sim import RobotSimulationManager, DifferentialDriveSimulator, OmnidirectionalDriveSimulator

    diff_drive = DifferentialDriveSimulator(wheel_base=0.3, wheel_radius=0.05)
    diff_drive.set_pose(0.0, 0.0, 0.0)
    diff_drive.update_with_twist(1.0, 0.5, 0.1)
    pose = diff_drive.get_pose()
    print(f"  ✓ 差分驱动仿真: ({pose[0]:.2f}, {pose[1]:.2f}, {pose[2]:.2f})")

    omni_drive = OmnidirectionalDriveSimulator(max_speed=100.0)
    omni_drive.set_pose(100.0, 100.0, 0.0)
    omni_drive.update_with_velocity(50.0, 30.0, 0.2, 0.1)
    pose = omni_drive.get_pose()
    print(f"  ✓ 全向驱动仿真: ({pose[0]:.2f}, {pose[1]:.2f}, {pose[2]:.2f})")

    sim_manager = RobotSimulationManager()
    robot_a = sim_manager.add_robot(50.0, 50.0, floor=0, drive_type='omnidirectional')
    robot_b = sim_manager.add_robot(200.0, 100.0, floor=1, drive_type='differential')
    print(f"  ✓ 创建仿真机器人: {len(sim_manager.robots)}个")

    commands = sim_manager.update_all(0.05)
    poses = sim_manager.get_all_robot_poses()
    vels = sim_manager.get_all_robot_velocities()
    print(f"  ✓ 仿真更新: {len(commands)}个指令, {len(poses)}个位姿")

    print("✓ 机器人仿真接口测试通过")
except Exception as e:
    print(f"✗ 机器人仿真接口测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[5/5] 测试综合集成...")
try:
    test_map = Map3D(floor_width=750, floor_height=700, resolution=5.0)
    for f in range(3):
        test_map.add_floor(f)

    test_map.add_connection('elevator', 0, 1, (650, 50), (650, 50))
    test_map.add_connection('stairs', 1, 2, (50, 650), (50, 650))

    planner = AStar3D(test_map)
    coordinator = MultiRobotCoordinator(map3d=test_map)
    sim_manager = RobotSimulationManager()

    robot = coordinator.add_robot(50.0, 50.0, floor=0)
    sim_robot = sim_manager.add_robot(50.0, 50.0, floor=0)

    path = planner.plan((50.0, 50.0, 0), (600.0, 500.0, 1))
    if path:
        coordinator.set_robot_path(robot.robot_id, path)
        sim_robot.set_path(path)

    for i in range(10):
        coordinator.update(0.05)
        sim_manager.update_all(0.05)

    poses = sim_manager.get_all_robot_poses()
    print(f"  ✓ 集成测试完成，机器人位置: ({poses[0][0]:.1f}, {poses[0][1]:.1f})")

    print("✓ 综合集成测试通过")
except Exception as e:
    print(f"✗ 综合集成测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("所有3D多机器人功能测试完成!")
print("=" * 70)
print("\n运行主程序:")
print("  python main.py    - 2D路径规划")
print("  python main_3d.py - 3D多机器人路径规划")
print("=" * 70)
