import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== 模块导入测试 ===")

try:
    from map import GridMap
    print("✓ map 模块导入成功")
except Exception as e:
    print(f"✗ map 模块导入失败: {e}")

try:
    from obstacles import ObstacleManager, DynamicObstacle
    print("✓ obstacles 模块导入成功")
except Exception as e:
    print(f"✗ obstacles 模块导入失败: {e}")

try:
    from astar import AStar
    print("✓ astar 模块导入成功")
except Exception as e:
    print(f"✗ astar 模块导入失败: {e}")

try:
    from rrt import RRT
    print("✓ rrt 模块导入成功")
except Exception as e:
    print(f"✗ rrt 模块导入失败: {e}")

try:
    from rrt_star import RRTStar
    print("✓ rrt_star 模块导入成功")
except Exception as e:
    print(f"✗ rrt_star 模块导入失败: {e}")

try:
    from comparison import PathPlannerComparison
    print("✓ comparison 模块导入成功")
except Exception as e:
    print(f"✗ comparison 模块导入失败: {e}")

print("\n=== 功能测试 ===")

try:
    grid_map = GridMap(800, 600, resolution=5.0)
    print("✓ GridMap 初始化成功")
    
    obs = {'type': 'rectangle', 'x': 100, 'y': 100, 'width': 50, 'height': 50}
    grid_map._add_rectangle_obstacle(obs)
    print("✓ 添加矩形障碍物成功")
    
    circle_obs = {'type': 'circle', 'x': 300, 'y': 300, 'radius': 30}
    grid_map._add_circle_obstacle(circle_obs)
    print("✓ 添加圆形障碍物成功")
    
    collision = grid_map.is_collision(125, 125, 0)
    print(f"✓ 碰撞检测: 障碍物中心={collision}")
    
    no_collision = grid_map.is_collision(50, 50, 0)
    print(f"✓ 碰撞检测: 空闲区域={not no_collision}")
    
except Exception as e:
    print(f"✗ GridMap 功能测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    obs_manager = ObstacleManager()
    dyn_obs = obs_manager.add_dynamic_obstacle('circle', x=200, y=200, radius=15)
    print("✓ 动态障碍物创建成功")
    
    dyn_obs.set_waypoints([(200, 200), (300, 300)], speed=50)
    print("✓ 路径点设置成功")
    
    dyn_obs.update(0.1)
    print("✓ 动态障碍物更新成功")
    
except Exception as e:
    print(f"✗ ObstacleManager 功能测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    test_map = GridMap(800, 600, resolution=5.0)
    test_manager = ObstacleManager()
    
    start = (50.0, 50.0)
    goal = (700.0, 500.0)
    
    astar_planner = AStar(test_map, test_manager)
    path = astar_planner.plan(start, goal)
    print(f"✓ A* 路径规划成功，路径点数量: {len(path)}")
    
    if len(path) > 0:
        smoothed = astar_planner.smooth_path(path)
        print(f"✓ A* 路径平滑成功，路径点数量: {len(smoothed)}")
        
except Exception as e:
    print(f"✗ A* 算法测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    test_map = GridMap(800, 600, resolution=5.0)
    test_manager = ObstacleManager()
    
    start = (50.0, 50.0)
    goal = (700.0, 500.0)
    
    rrt_planner = RRT(test_map, test_manager)
    rrt_planner.max_iterations = 1000
    path = rrt_planner.plan(start, goal)
    print(f"✓ RRT 路径规划成功，路径点数量: {len(path)}")
    
except Exception as e:
    print(f"✗ RRT 算法测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    test_map = GridMap(800, 600, resolution=5.0)
    test_manager = ObstacleManager()
    
    start = (50.0, 50.0)
    goal = (700.0, 500.0)
    
    rrt_star_planner = RRTStar(test_map, test_manager)
    rrt_star_planner.max_iterations = 1000
    path = rrt_star_planner.plan(start, goal)
    print(f"✓ RRT* 路径规划成功，路径点数量: {len(path)}")
    
except Exception as e:
    print(f"✗ RRT* 算法测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 所有测试完成 ===")
