import numpy as np
import time
from typing import List, Tuple, Optional, Dict
from map import GridMap
from obstacles import ObstacleManager
from astar import AStar
from rrt import RRT
from rrt_star import RRTStar


class PathReplanner:
    def __init__(self, grid_map: GridMap, obstacle_manager: ObstacleManager,
                 algorithm: str = 'astar'):
        self.grid_map = grid_map
        self.obstacle_manager = obstacle_manager
        self.algorithm = algorithm
        self.robot_radius = 8.0

        self.current_path: List[Tuple[float, float]] = []
        self.current_waypoint_index = 0

        self.collision_check_radius = 50.0
        self.local_replan_radius = 100.0
        self.replan_cooldown = 0.5
        self.last_replan_time = 0.0

        self._init_planner()

    def _init_planner(self) -> None:
        if self.algorithm == 'astar':
            self.planner = AStar(self.grid_map, self.obstacle_manager)
        elif self.algorithm == 'rrt':
            self.planner = RRT(self.grid_map, self.obstacle_manager)
        elif self.algorithm == 'rrt_star':
            self.planner = RRTStar(self.grid_map, self.obstacle_manager)
        else:
            self.planner = AStar(self.grid_map, self.obstacle_manager)

        self.planner.robot_radius = self.robot_radius

    def set_algorithm(self, algorithm: str) -> None:
        self.algorithm = algorithm
        self._init_planner()

    def plan_initial_path(self, start: Tuple[float, float],
                          goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        self.current_path = self.planner.plan(start, goal)
        if self.current_path:
            self.current_path = self.planner.smooth_path(self.current_path)
        self.current_waypoint_index = 0
        return self.current_path

    def check_path_collision(self, look_ahead: int = 10) -> List[int]:
        if not self.current_path:
            return []

        collision_indices = []
        start_idx = self.current_waypoint_index
        end_idx = min(start_idx + look_ahead, len(self.current_path))

        for i in range(start_idx, end_idx):
            x, y = self.current_path[i]
            if self.obstacle_manager.check_collision(x, y, self.robot_radius):
                collision_indices.append(i)
            elif i < end_idx - 1:
                x2, y2 = self.current_path[i + 1]
                if self.obstacle_manager.check_line_collision(
                        x, y, x2, y2, self.robot_radius
                ):
                    collision_indices.append(i)

        return collision_indices

    def find_replan_region(self, collision_indices: List[int]) -> Tuple[int, int, Tuple[float, float]]:
        if not collision_indices:
            return -1, -1, (0.0, 0.0)

        first_collision = min(collision_indices)
        safe_start_idx = max(0, first_collision - 1)

        for i in range(first_collision - 1, -1, -1):
            x, y = self.current_path[i]
            if not self.obstacle_manager.check_collision(x, y, self.robot_radius):
                safe_start_idx = i
                break

        replan_end_idx = min(len(self.current_path) - 1, first_collision + 20)

        for i in range(first_collision + 1, len(self.current_path)):
            x, y = self.current_path[i]
            if not self.obstacle_manager.check_collision(x, y, self.robot_radius):
                collision_free = True
                for j in range(safe_start_idx, i):
                    x1, y1 = self.current_path[j]
                    x2, y2 = self.current_path[j + 1]
                    if self.obstacle_manager.check_line_collision(
                            x1, y1, x2, y2, self.robot_radius
                    ):
                        collision_free = False
                        break
                if collision_free:
                    replan_end_idx = i
                    break

        safe_start = self.current_path[safe_start_idx]
        return safe_start_idx, replan_end_idx, safe_start

    def replan_local(self, start_idx: int, end_idx: int,
                     local_start: Tuple[float, float]) -> bool:
        if end_idx >= len(self.current_path):
            return False

        local_goal = self.current_path[end_idx]

        local_path = self.planner.plan(local_start, local_goal)
        if not local_path:
            return False

        local_path = self.planner.smooth_path(local_path)

        if len(local_path) < 2:
            return False

        new_path = (
            self.current_path[:start_idx + 1] +
            local_path[1:-1] +
            self.current_path[end_idx:]
        )

        self.current_path = new_path
        return True

    def update_and_replan(self, robot_position: Tuple[float, float],
                          dt: float) -> Tuple[List[Tuple[float, float]], bool]:
        if not self.current_path:
            return [], False

        self._update_waypoint_index(robot_position)

        current_time = time.time()
        if current_time - self.last_replan_time < self.replan_cooldown:
            return self.current_path, False

        collision_indices = self.check_path_collision()

        if collision_indices:
            start_idx, end_idx, local_start = self.find_replan_region(collision_indices)

            if start_idx >= 0 and end_idx < len(self.current_path):
                success = self.replan_local(start_idx, end_idx, local_start)
                self.last_replan_time = current_time
                return self.current_path, success

        return self.current_path, False

    def _update_waypoint_index(self, robot_position: Tuple[float, float]) -> None:
        if not self.current_path:
            return

        min_dist = float('inf')
        closest_idx = self.current_waypoint_index

        search_range = 10
        start_idx = max(0, self.current_waypoint_index - search_range)
        end_idx = min(len(self.current_path), self.current_waypoint_index + search_range + 1)

        for i in range(start_idx, end_idx):
            x, y = self.current_path[i]
            dx = x - robot_position[0]
            dy = y - robot_position[1]
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        self.current_waypoint_index = closest_idx

    def get_current_waypoint(self) -> Optional[Tuple[float, float]]:
        if self.current_waypoint_index < len(self.current_path):
            return self.current_path[self.current_waypoint_index]
        return None

    def replan_from_scratch(self, start: Tuple[float, float],
                            goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        self.current_path = self.planner.plan(start, goal)
        if self.current_path:
            self.current_path = self.planner.smooth_path(self.current_path)
        self.current_waypoint_index = 0
        self.last_replan_time = time.time()
        return self.current_path

    def get_statistics(self) -> Dict:
        return {
            'algorithm': self.algorithm,
            'path_length': len(self.current_path),
            'current_waypoint': self.current_waypoint_index,
            'last_replan': self.last_replan_time
        }


class IncrementalReplanner:
    def __init__(self, grid_map: GridMap, obstacle_manager: ObstacleManager):
        self.grid_map = grid_map
        self.obstacle_manager = obstacle_manager
        self.replanners = {
            'astar': PathReplanner(grid_map, obstacle_manager, 'astar'),
            'rrt': PathReplanner(grid_map, obstacle_manager, 'rrt'),
            'rrt_star': PathReplanner(grid_map, obstacle_manager, 'rrt_star')
        }
        self.active_replanner = 'astar'

    def set_active_algorithm(self, algorithm: str) -> None:
        if algorithm in self.replanners:
            self.active_replanner = algorithm

    def plan_path(self, start: Tuple[float, float],
                  goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        return self.replanners[self.active_replanner].plan_initial_path(start, goal)

    def update(self, robot_position: Tuple[float, float],
               dt: float) -> Tuple[List[Tuple[float, float]], bool]:
        return self.replanners[self.active_replanner].update_and_replan(robot_position, dt)

    def get_path(self) -> List[Tuple[float, float]]:
        return self.replanners[self.active_replanner].current_path

    def force_replan(self, start: Tuple[float, float],
                     goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        return self.replanners[self.active_replanner].replan_from_scratch(start, goal)
