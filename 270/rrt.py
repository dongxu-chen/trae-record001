import numpy as np
import time
from typing import List, Tuple, Optional
from map import GridMap
from obstacles import ObstacleManager


class RRTNode:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.parent = None
        self.cost = 0.0


class RRT:
    def __init__(self, grid_map: GridMap, obstacle_manager: Optional[ObstacleManager] = None):
        self.grid_map = grid_map
        self.obstacle_manager = obstacle_manager
        self.robot_radius = 5.0
        self.step_size = 10.0
        self.max_iterations = 5000
        self.goal_sample_rate = 0.1
        self.goal_threshold = 15.0

        self.planning_time = 0.0
        self.path_length = 0.0
        self.nodes_expanded = 0
        self.nodes = []

    def is_valid(self, x: float, y: float) -> bool:
        if self.grid_map.is_collision(x, y, self.robot_radius):
            return False

        if self.obstacle_manager and self.obstacle_manager.check_collision(x, y, self.robot_radius):
            return False

        return True

    def is_line_valid(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        if self.grid_map.is_line_collision(x1, y1, x2, y2, self.robot_radius):
            return False

        if self.obstacle_manager and self.obstacle_manager.check_line_collision(
                x1, y1, x2, y2, self.robot_radius
        ):
            return False

        return True

    def sample_random(self, goal: Tuple[float, float]) -> Tuple[float, float]:
        if np.random.random() < self.goal_sample_rate:
            return goal

        x = np.random.uniform(0, self.grid_map.width)
        y = np.random.uniform(0, self.grid_map.height)
        return (x, y)

    def get_nearest_node(self, x: float, y: float) -> RRTNode:
        distances = []
        for node in self.nodes:
            dx = x - node.x
            dy = y - node.y
            distances.append(dx * dx + dy * dy)

        nearest_idx = np.argmin(distances)
        return self.nodes[nearest_idx]

    def steer(self, from_node: RRTNode, to_x: float, to_y: float) -> RRTNode:
        dx = to_x - from_node.x
        dy = to_y - from_node.y
        dist = np.sqrt(dx * dx + dy * dy)

        if dist <= self.step_size:
            new_node = RRTNode(to_x, to_y)
        else:
            ratio = self.step_size / dist
            new_x = from_node.x + dx * ratio
            new_y = from_node.y + dy * ratio
            new_node = RRTNode(new_x, new_y)

        return new_node

    def is_goal_reached(self, node: RRTNode, goal: Tuple[float, float]) -> bool:
        dx = node.x - goal[0]
        dy = node.y - goal[1]
        dist = np.sqrt(dx * dx + dy * dy)
        return dist < self.goal_threshold

    def plan(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        start_time = time.time()
        self.nodes = []
        self.nodes_expanded = 0

        if not self.is_valid(start[0], start[1]):
            print("RRT: Start position is in collision!")
            return []

        if not self.is_valid(goal[0], goal[1]):
            print("RRT: Goal position is in collision!")
            return []

        start_node = RRTNode(start[0], start[1])
        self.nodes.append(start_node)

        for i in range(self.max_iterations):
            self.nodes_expanded += 1

            sample_x, sample_y = self.sample_random(goal)

            nearest_node = self.get_nearest_node(sample_x, sample_y)

            new_node = self.steer(nearest_node, sample_x, sample_y)

            if self.is_line_valid(nearest_node.x, nearest_node.y, new_node.x, new_node.y):
                new_node.parent = nearest_node
                new_node.cost = nearest_node.cost + self.step_size
                self.nodes.append(new_node)

                if self.is_goal_reached(new_node, goal):
                    if self.is_line_valid(new_node.x, new_node.y, goal[0], goal[1]):
                        goal_node = RRTNode(goal[0], goal[1])
                        goal_node.parent = new_node
                        dx = goal[0] - new_node.x
                        dy = goal[1] - new_node.y
                        goal_node.cost = new_node.cost + np.sqrt(dx * dx + dy * dy)
                        self.nodes.append(goal_node)

                        path = self._reconstruct_path(goal_node)
                        self.planning_time = time.time() - start_time
                        self.path_length = self._calculate_path_length(path)
                        return path

        self.planning_time = time.time() - start_time
        print("RRT: No path found!")
        return []

    def _reconstruct_path(self, end_node: RRTNode) -> List[Tuple[float, float]]:
        path = []
        current = end_node

        while current is not None:
            path.append((current.x, current.y))
            current = current.parent

        path.reverse()
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
                if self.is_line_valid(path[i][0], path[i][1], path[j][0], path[j][1]):
                    smoothed.append(path[j])
                    i = j
                    break

        return smoothed

    def get_tree_edges(self) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        edges = []
        for node in self.nodes:
            if node.parent is not None:
                edges.append(((node.parent.x, node.parent.y), (node.x, node.y)))
        return edges

    def get_statistics(self) -> dict:
        return {
            'planning_time': self.planning_time,
            'path_length': self.path_length,
            'nodes_expanded': self.nodes_expanded,
            'total_nodes': len(self.nodes)
        }
