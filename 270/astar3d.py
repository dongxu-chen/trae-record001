import heapq
import numpy as np
import time
from typing import List, Tuple, Dict, Optional
from map3d import Map3D


class Node3D:
    def __init__(self, x: float, y: float, floor: int):
        self.x = x
        self.y = y
        self.floor = floor
        self.parent = None
        self.g = 0.0
        self.h = 0.0
        self.f = 0.0

    def get_key(self) -> Tuple[int, int, int]:
        return (int(self.x), int(self.y), self.floor)

    def __lt__(self, other):
        return self.f < other.f


class AStar3D:
    def __init__(self, map3d: Map3D):
        self.map3d = map3d
        self.robot_radius = 8.0
        self.step_size = 10.0
        self.planning_time = 0.0
        self.path_length = 0.0
        self.nodes_expanded = 0

    def heuristic(self, node1: Node3D, node2: Node3D) -> float:
        dx = node1.x - node2.x
        dy = node1.y - node2.y
        dfloor = abs(node1.floor - node2.floor) * 50.0
        return np.sqrt(dx * dx + dy * dy) + dfloor

    def get_neighbors(self, node: Node3D) -> List[Node3D]:
        neighbors = []

        directions = [
            (self.step_size, 0), (-self.step_size, 0),
            (0, self.step_size), (0, -self.step_size),
            (self.step_size, self.step_size), (-self.step_size, self.step_size),
            (self.step_size, -self.step_size), (-self.step_size, -self.step_size)
        ]

        for dx, dy in directions:
            new_x = node.x + dx
            new_y = node.y + dy

            if (0 <= new_x < self.map3d.floor_width and
                0 <= new_y < self.map3d.floor_height):
                if self.map3d.is_valid_3d(new_x, new_y, node.floor, self.robot_radius):
                    if self.map3d.is_line_valid_3d(node.x, node.y, new_x, new_y,
                                                   node.floor, self.robot_radius):
                        neighbor = Node3D(new_x, new_y, node.floor)
                        neighbors.append(neighbor)

        connections = self.map3d.get_connections_from_floor(node.floor)
        for conn in connections:
            if conn.floor1 == node.floor:
                target_floor = conn.floor2
                target_pos = conn.pos2
                start_pos = conn.pos1
            else:
                target_floor = conn.floor1
                target_pos = conn.pos1
                start_pos = conn.pos2

            dist_to_conn = np.sqrt((node.x - start_pos[0]) ** 2 +
                                    (node.y - start_pos[1]) ** 2)
            if dist_to_conn < self.step_size * 2:
                if self.map3d.is_valid_3d(target_pos[0], target_pos[1],
                                          target_floor, self.robot_radius):
                    floor_node = Node3D(target_pos[0], target_pos[1], target_floor)
                    neighbors.append(floor_node)

        return neighbors

    def plan(self, start: Tuple[float, float, int],
             goal: Tuple[float, float, int]) -> List[Tuple[float, float, int]]:
        start_time = time.time()
        self.nodes_expanded = 0

        start_node = Node3D(start[0], start[1], start[2])
        goal_node = Node3D(goal[0], goal[1], goal[2])

        if not self.map3d.is_valid_3d(start[0], start[1], start[2], self.robot_radius):
            print("3D A*: Start position is in collision!")
            return []

        if not self.map3d.is_valid_3d(goal[0], goal[1], goal[2], self.robot_radius):
            print("3D A*: Goal position is in collision!")
            return []

        open_set = []
        heapq.heappush(open_set, (start_node.f, start_node))

        open_dict: Dict[Tuple[int, int, int], Node3D] = {}
        open_dict[start_node.get_key()] = start_node

        closed_dict: Dict[Tuple[int, int, int], Node3D] = {}

        start_node.h = self.heuristic(start_node, goal_node)
        start_node.f = start_node.h

        while open_set:
            current_f, current = heapq.heappop(open_set)
            current_key = current.get_key()

            if current_key in closed_dict:
                continue

            if current_key in open_dict and open_dict[current_key].f < current.f:
                continue

            closed_dict[current_key] = current
            self.nodes_expanded += 1

            if (abs(current.x - goal_node.x) < self.step_size and
                abs(current.y - goal_node.y) < self.step_size and
                current.floor == goal_node.floor):
                path = self._reconstruct_path(current)
                path.append((goal[0], goal[1], goal[2]))
                self.planning_time = time.time() - start_time
                self.path_length = self._calculate_path_length(path)
                return path

            for neighbor in self.get_neighbors(current):
                neighbor_key = neighbor.get_key()

                if neighbor_key in closed_dict:
                    continue

                dx = neighbor.x - current.x
                dy = neighbor.y - current.y
                dfloor = abs(neighbor.floor - current.floor) * 50.0
                step_cost = np.sqrt(dx * dx + dy * dy) + dfloor

                tentative_g = current.g + step_cost

                if neighbor_key not in open_dict or tentative_g < open_dict[neighbor_key].g:
                    neighbor.parent = current
                    neighbor.g = tentative_g
                    neighbor.h = self.heuristic(neighbor, goal_node)
                    neighbor.f = neighbor.g + neighbor.h
                    open_dict[neighbor_key] = neighbor
                    heapq.heappush(open_set, (neighbor.f, neighbor))

        self.planning_time = time.time() - start_time
        print("3D A*: No path found!")
        return []

    def _reconstruct_path(self, end_node: Node3D) -> List[Tuple[float, float, int]]:
        path = []
        current = end_node

        while current is not None:
            path.append((current.x, current.y, current.floor))
            current = current.parent

        path.reverse()
        return path

    def _calculate_path_length(self, path: List[Tuple[float, float, int]]) -> float:
        if len(path) < 2:
            return 0.0

        length = 0.0
        for i in range(len(path) - 1):
            x1, y1, f1 = path[i]
            x2, y2, f2 = path[i + 1]
            dx = x2 - x1
            dy = y2 - y1
            dfloor = abs(f2 - f1) * 50.0
            length += np.sqrt(dx * dx + dy * dy) + dfloor

        return length

    def get_statistics(self) -> dict:
        return {
            'planning_time': self.planning_time,
            'path_length': self.path_length,
            'nodes_expanded': self.nodes_expanded
        }
