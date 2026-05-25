import heapq
import numpy as np
import time
from typing import List, Tuple, Dict, Optional, Callable
from map import GridMap
from obstacles import ObstacleManager


class HeuristicType:
    MANHATTAN = 'manhattan'
    EUCLIDEAN = 'euclidean'
    CHEBYSHEV = 'chebyshev'
    OCTILE = 'octile'


class AStar:
    def __init__(self, grid_map: GridMap, obstacle_manager: Optional[ObstacleManager] = None,
                 heuristic_type: str = HeuristicType.OCTILE):
        self.grid_map = grid_map
        self.obstacle_manager = obstacle_manager
        self.robot_radius = 5.0
        self.planning_time = 0.0
        self.path_length = 0.0
        self.nodes_expanded = 0
        self.heuristic_type = heuristic_type
        self._heuristic_func = self._get_heuristic_func(heuristic_type)

    def _get_heuristic_func(self, heuristic_type: str) -> Callable:
        if heuristic_type == HeuristicType.MANHATTAN:
            return self._manhattan_heuristic
        elif heuristic_type == HeuristicType.EUCLIDEAN:
            return self._euclidean_heuristic
        elif heuristic_type == HeuristicType.CHEBYSHEV:
            return self._chebyshev_heuristic
        elif heuristic_type == HeuristicType.OCTILE:
            return self._octile_heuristic
        else:
            return self._octile_heuristic

    def set_heuristic(self, heuristic_type: str) -> None:
        self.heuristic_type = heuristic_type
        self._heuristic_func = self._get_heuristic_func(heuristic_type)

    def _manhattan_heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return dx + dy

    def _euclidean_heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return np.sqrt(dx * dx + dy * dy)

    def _chebyshev_heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy)

    def _octile_heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (np.sqrt(2) - 2) * min(dx, dy)

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return self._heuristic_func(a, b)

    def get_neighbors(self, node: Tuple[int, int]) -> List[Tuple[int, int]]:
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]
        neighbors = []
        for dx, dy in directions:
            nx = node[0] + dx
            ny = node[1] + dy
            if 0 <= nx < self.grid_map.grid_width and 0 <= ny < self.grid_map.grid_height:
                neighbors.append((nx, ny))
        return neighbors

    def is_valid(self, node: Tuple[int, int]) -> bool:
        x = node[0] * self.grid_map.resolution
        y = node[1] * self.grid_map.resolution

        if self.grid_map.is_collision(x, y, self.robot_radius):
            return False

        if self.obstacle_manager and self.obstacle_manager.check_collision(x, y, self.robot_radius):
            return False

        return True

    def plan(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        start_time = time.time()
        self.nodes_expanded = 0

        start_grid = (int(start[0] / self.grid_map.resolution),
                       int(start[1] / self.grid_map.resolution))
        goal_grid = (int(goal[0] / self.grid_map.resolution),
                     int(goal[1] / self.grid_map.resolution))

        if not self.is_valid(start_grid):
            print("Start position is in collision!")
            return []

        if not self.is_valid(goal_grid):
            print("Goal position is in collision!")
            return []

        open_set = []
        heapq.heappush(open_set, (0, start_grid))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

        g_score = {start_grid: 0.0}
        f_score = {start_grid: self.heuristic(start_grid, goal_grid)}

        closed_set = set()

        while open_set:
            current_f, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            closed_set.add(current)
            self.nodes_expanded += 1

            if current == goal_grid:
                path = self._reconstruct_path(came_from, current)
                self.planning_time = time.time() - start_time
                self.path_length = self._calculate_path_length(path)
                return path

            for neighbor in self.get_neighbors(current):
                if neighbor in closed_set:
                    continue

                if not self.is_valid(neighbor):
                    continue

                dx = neighbor[0] - current[0]
                dy = neighbor[1] - current[1]
                step_cost = np.sqrt(dx * dx + dy * dy)

                tentative_g = g_score[current] + step_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        self.planning_time = time.time() - start_time
        print("A*: No path found!")
        return []

    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]],
                          current: Tuple[int, int]) -> List[Tuple[float, float]]:
        path_grid = [current]
        while current in came_from:
            current = came_from[current]
            path_grid.append(current)

        path_grid.reverse()

        path = []
        for gx, gy in path_grid:
            x = gx * self.grid_map.resolution + self.grid_map.resolution / 2
            y = gy * self.grid_map.resolution + self.grid_map.resolution / 2
            path.append((x, y))

        return path

    def _calculate_path_length(self, path: List[Tuple[float, float]]) -> float:
        if len(path) < 2:
            return 0.0

        length = 0.0
        for i in range(len(path) - 1):
            dx = path[i + 1][0] - path[i][0]
            dy = path[i + 1][1] - path[i][1]
            length += np.sqrt(dx * dx + dy * dy)

        return length

    def smooth_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(path) < 3:
            return path

        smoothed = [path[0]]
        i = 0

        while i < len(path) - 1:
            for j in range(len(path) - 1, i, -1):
                if not self.grid_map.is_line_collision(
                        path[i][0], path[i][1], path[j][0], path[j][1], self.robot_radius
                ):
                    if not self.obstacle_manager or not self.obstacle_manager.check_line_collision(
                            path[i][0], path[i][1], path[j][0], path[j][1], self.robot_radius
                    ):
                        smoothed.append(path[j])
                        i = j
                        break

        return smoothed

    def get_statistics(self) -> dict:
        return {
            'planning_time': self.planning_time,
            'path_length': self.path_length,
            'nodes_expanded': self.nodes_expanded,
            'heuristic_type': self.heuristic_type
        }
