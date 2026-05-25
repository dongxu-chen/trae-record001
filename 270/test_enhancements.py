import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("增强功能测试")
print("=" * 60)

print("\n[1/5] 测试 A* 可配置启发函数...")
try:
    from map import GridMap
    from obstacles import ObstacleManager
    from astar import AStar, HeuristicType

    test_map = GridMap(800, 600, resolution=5.0)
    obs_manager = ObstacleManager()

    start = (50.0, 50.0)
    goal = (700.0, 500.0)

    heuristics = [
        (HeuristicType.MANHATTAN, "曼哈顿距离"),
        (HeuristicType.EUCLIDEAN, "欧氏距离"),
        (HeuristicType.CHEBYSHEV, "切比雪夫距离"),
        (HeuristicType.OCTILE, "Octile距离")
    ]

    for heur_type, name in heuristics:
        planner = AStar(test_map, obs_manager, heuristic_type=heur_type)
        planner.robot_radius = 5.0
        path = planner.plan(start, goal)
        stats = planner.get_statistics()
        print(f"  ✓ {name}: 路径长度={stats['path_length']:.1f}, 时间={stats['planning_time']*1000:.2f}ms, 节点={stats['nodes_expanded']}")

    print("  ✓ 启发函数切换测试...")
    planner = AStar(test_map, obs_manager)
    planner.set_heuristic(HeuristicType.EUCLIDEAN)
    assert planner.heuristic_type == HeuristicType.EUCLIDEAN
    planner.set_heuristic(HeuristicType.MANHATTAN)
    assert planner.heuristic_type == HeuristicType.MANHATTAN
    print("  ✓ 启发函数动态切换成功")

    print("✓ A* 可配置启发函数测试通过")
except Exception as e:
    print(f"✗ A* 启发函数测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[2/5] 测试 RRT* 动态连接半径...")
try:
    from rrt_star import RRTStar

    test_map = GridMap(800, 600, resolution=5.0)
    obs_manager = ObstacleManager()

    planner_dynamic = RRTStar(test_map, obs_manager, use_dynamic_radius=True)
    planner_dynamic.robot_radius = 5.0
    planner_dynamic.max_iterations = 500

    radii = []
    for i in range(5):
        planner_dynamic.nodes = []
        planner_dynamic.plan(start, goal)
        final_radius = planner_dynamic.get_dynamic_radius()
        radii.append(final_radius)

    print(f"  ✓ 动态半径最终值: {radii[0]:.2f} (随节点数 {len(planner_dynamic.nodes)} 变化)")

    planner_static = RRTStar(test_map, obs_manager, use_dynamic_radius=False)
    planner_static.robot_radius = 5.0
    planner_static.max_iterations = 500
    planner_static.plan(start, goal)
    stats_static = planner_static.get_statistics()
    print(f"  ✓ 静态半径模式: {stats_static['final_radius']:.2f}")

    print("✓ RRT* 动态连接半径测试通过")
except Exception as e:
    print(f"✗ RRT* 动态半径测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[3/5] 测试增量重规划模块...")
try:
    from replanner import PathReplanner, IncrementalReplanner

    test_map = GridMap(800, 600, resolution=5.0)
    obs_manager = ObstacleManager()

    replanner = PathReplanner(test_map, obs_manager, algorithm='astar')
    path = replanner.plan_initial_path(start, goal)
    print(f"  ✓ 初始规划: 路径点数量={len(path)}")

    fake_robot_pos = (100.0, 100.0)
    updated_path, replanned = replanner.update_and_replan(fake_robot_pos, 0.1)
    print(f"  ✓ 常规更新: 重规划发生={replanned}")

    collision_indices = replanner.check_path_collision()
    print(f"  ✓ 碰撞检测: 冲突点数量={len(collision_indices)}")

    print("✓ 增量重规划模块测试通过")
except Exception as e:
    print(f"✗ 增量重规划测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[4/5] 测试综合重规划器...")
try:
    test_map = GridMap(800, 600, resolution=5.0)
    obs_manager = ObstacleManager()

    inc_replanner = IncrementalReplanner(test_map, obs_manager)

    for algo in ['astar', 'rrt', 'rrt_star']:
        inc_replanner.set_active_algorithm(algo)
        path = inc_replanner.plan_path(start, goal)
        print(f"  ✓ {algo.upper()} 规划: 路径点数量={len(path)}")

    updated_path, replanned = inc_replanner.update(start, 0.1)
    print(f"  ✓ 增量更新正常工作")

    print("✓ 综合重规划器测试通过")
except Exception as e:
    print(f"✗ 综合重规划器测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n[5/5] 测试动态障碍物与重规划交互...")
try:
    test_map = GridMap(800, 600, resolution=5.0)
    obs_manager = ObstacleManager()

    dyn_obs = obs_manager.add_dynamic_obstacle('circle', x=400, y=300, radius=30)
    dyn_obs.set_linear_velocity(50, 0)

    replanner = PathReplanner(test_map, obs_manager, algorithm='astar')
    path = replanner.plan_initial_path(start, goal)

    for i in range(5):
        obs_manager.update_all(0.1)
        updated_path, replanned = replanner.update_and_replan((100, 100), 0.1)

    print(f"  ✓ 动态障碍物交互正常, 最终路径长度={len(updated_path)}")

    print("✓ 动态障碍物与重规划交互测试通过")
except Exception as e:
    print(f"✗ 动态障碍物交互测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("所有增强功能测试完成!")
print("=" * 60)
