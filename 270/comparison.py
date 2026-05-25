import time
import numpy as np
from typing import List, Tuple, Dict
from map import GridMap
from obstacles import ObstacleManager
from astar import AStar
from rrt import RRT
from rrt_star import RRTStar


class PathPlannerComparison:
    def __init__(self, grid_map: GridMap, obstacle_manager: ObstacleManager = None):
        self.grid_map = grid_map
        self.obstacle_manager = obstacle_manager
        self.robot_radius = 5.0

        self.astar = AStar(grid_map, obstacle_manager)
        self.rrt = RRT(grid_map, obstacle_manager)
        self.rrt_star = RRTStar(grid_map, obstacle_manager)

        self.astar.robot_radius = self.robot_radius
        self.rrt.robot_radius = self.robot_radius
        self.rrt_star.robot_radius = self.robot_radius

    def compare_all(self, start: Tuple[float, float], goal: Tuple[float, float],
                    num_runs: int = 1) -> Dict[str, dict]:
        results = {}

        print("\n" + "=" * 50)
        print("算法对比测试")
        print("=" * 50)

        print("\n[1/3] 运行 A* 算法...")
        astar_times = []
        astar_lengths = []
        astar_success = 0

        for i in range(num_runs):
            path = self.astar.plan(start, goal)
            if len(path) > 0:
                path = self.astar.smooth_path(path)
                astar_times.append(self.astar.planning_time)
                astar_lengths.append(self.astar.path_length)
                astar_success += 1

        if astar_success > 0:
            results['astar'] = {
                'success_rate': astar_success / num_runs,
                'avg_time': np.mean(astar_times),
                'std_time': np.std(astar_times),
                'avg_length': np.mean(astar_lengths),
                'std_length': np.std(astar_lengths),
                'nodes_expanded': self.astar.nodes_expanded
            }
        else:
            results['astar'] = {'success_rate': 0.0}

        print(f"  成功率: {results['astar']['success_rate']*100:.1f}%")
        if astar_success > 0:
            print(f"  平均时间: {results['astar']['avg_time']*1000:.2f}ms")
            print(f"  平均长度: {results['astar']['avg_length']:.2f}")

        print("\n[2/3] 运行 RRT 算法...")
        rrt_times = []
        rrt_lengths = []
        rrt_success = 0

        for i in range(num_runs):
            path = self.rrt.plan(start, goal)
            if len(path) > 0:
                path = self.rrt.smooth_path(path)
                rrt_times.append(self.rrt.planning_time)
                rrt_lengths.append(self.rrt.path_length)
                rrt_success += 1

        if rrt_success > 0:
            results['rrt'] = {
                'success_rate': rrt_success / num_runs,
                'avg_time': np.mean(rrt_times),
                'std_time': np.std(rrt_times),
                'avg_length': np.mean(rrt_lengths),
                'std_length': np.std(rrt_lengths),
                'nodes_expanded': self.rrt.nodes_expanded,
                'total_nodes': len(self.rrt.nodes)
            }
        else:
            results['rrt'] = {'success_rate': 0.0}

        print(f"  成功率: {results['rrt']['success_rate']*100:.1f}%")
        if rrt_success > 0:
            print(f"  平均时间: {results['rrt']['avg_time']*1000:.2f}ms")
            print(f"  平均长度: {results['rrt']['avg_length']:.2f}")

        print("\n[3/3] 运行 RRT* 算法...")
        rrt_star_times = []
        rrt_star_lengths = []
        rrt_star_success = 0

        for i in range(num_runs):
            path = self.rrt_star.plan(start, goal)
            if len(path) > 0:
                path = self.rrt_star.smooth_path(path)
                rrt_star_times.append(self.rrt_star.planning_time)
                rrt_star_lengths.append(self.rrt_star.path_length)
                rrt_star_success += 1

        if rrt_star_success > 0:
            results['rrt_star'] = {
                'success_rate': rrt_star_success / num_runs,
                'avg_time': np.mean(rrt_star_times),
                'std_time': np.std(rrt_star_times),
                'avg_length': np.mean(rrt_star_lengths),
                'std_length': np.std(rrt_star_lengths),
                'nodes_expanded': self.rrt_star.nodes_expanded,
                'total_nodes': len(self.rrt_star.nodes)
            }
        else:
            results['rrt_star'] = {'success_rate': 0.0}

        print(f"  成功率: {results['rrt_star']['success_rate']*100:.1f}%")
        if rrt_star_success > 0:
            print(f"  平均时间: {results['rrt_star']['avg_time']*1000:.2f}ms")
            print(f"  平均长度: {results['rrt_star']['avg_length']:.2f}")

        print("\n" + "=" * 50)
        print("总结报告")
        print("=" * 50)
        self.print_comparison_table(results)

        return results

    def print_comparison_table(self, results: Dict[str, dict]) -> None:
        print(f"\n{'算法':<10} {'成功率':<10} {'平均时间(ms)':<15} {'平均长度':<12} {'节点数':<10}")
        print("-" * 60)

        algo_names = {'astar': 'A*', 'rrt': 'RRT', 'rrt_star': 'RRT*'}

        for algo, stats in results.items():
            name = algo_names.get(algo, algo)
            success = f"{stats['success_rate']*100:.1f}%"
            time_str = f"{stats.get('avg_time', 0)*1000:.2f}" if stats['success_rate'] > 0 else "-"
            length_str = f"{stats.get('avg_length', 0):.2f}" if stats['success_rate'] > 0 else "-"
            nodes = stats.get('nodes_expanded', '-')

            print(f"{name:<10} {success:<10} {time_str:<15} {length_str:<12} {str(nodes):<10}")

    def get_paths(self) -> Dict[str, List[Tuple[float, float]]]:
        paths = {}

        path_astar = self.astar.plan(
            (self.astar.start_pos[0], self.astar.start_pos[1]),
            (self.astar.goal_pos[0], self.astar.goal_pos[1])
        )
        if path_astar:
            paths['astar'] = self.astar.smooth_path(path_astar)

        path_rrt = self.rrt.plan(
            (self.rrt.start_pos[0], self.rrt.start_pos[1]),
            (self.rrt.goal_pos[0], self.rrt.goal_pos[1])
        )
        if path_rrt:
            paths['rrt'] = self.rrt.smooth_path(path_rrt)

        path_rrt_star = self.rrt_star.plan(
            (self.rrt_star.start_pos[0], self.rrt_star.start_pos[1]),
            (self.rrt_star.goal_pos[0], self.rrt_star.goal_pos[1])
        )
        if path_rrt_star:
            paths['rrt_star'] = self.rrt_star.smooth_path(path_rrt_star)

        return paths
