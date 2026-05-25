import numpy as np
import time
from typing import List, Tuple, Dict, Optional
from map import GridMap
from map3d import Map3D


class VelocityCommand:
    def __init__(self, vx: float = 0.0, vy: float = 0.0, vtheta: float = 0.0):
        self.vx = vx
        self.vy = vy
        self.vtheta = vtheta


class RobotState:
    def __init__(self, robot_id: int, x: float = 0.0, y: float = 0.0,
                 theta: float = 0.0, floor: int = 0):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        self.theta = theta
        self.floor = floor
        self.vx = 0.0
        self.vy = 0.0
        self.vtheta = 0.0
        self.radius = 15.0
        self.max_speed = 100.0
        self.max_accel = 200.0

        self.path: List[Tuple[float, float, int]] = []
        self.path_index = 0
        self.goal_reached = False

        self.color = (
            np.random.randint(100, 255),
            np.random.randint(100, 255),
            np.random.randint(100, 255)
        )


class VelocityObstacle:
    def __init__(self):
        self.safety_margin = 5.0
        self.time_horizon = 2.0

    def compute_velocity_obstacle(self, robot: RobotState,
                                   other_robot: RobotState) -> np.ndarray:
        rx = robot.x - other_robot.x
        ry = robot.y - other_robot.y
        r = robot.radius + other_robot.radius + self.safety_margin

        center = np.array([other_robot.vx, other_robot.vy])

        if r * r > rx * rx + ry * ry:
            return center, 1e9

        dist = np.sqrt(rx * rx + ry * ry)
        rx_norm = rx / dist
        ry_norm = ry / dist

        sin_theta = r / dist
        sin_theta = min(max(sin_theta, -1.0), 1.0)
        cos_theta = np.sqrt(1.0 - sin_theta * sin_theta)

        left_ray = np.array([
            rx_norm * cos_theta - ry_norm * sin_theta,
            rx_norm * sin_theta + ry_norm * cos_theta
        ])
        right_ray = np.array([
            rx_norm * cos_theta + ry_norm * sin_theta,
            -rx_norm * sin_theta + ry_norm * cos_theta
        ])

        return center, left_ray, right_ray

    def is_velocity_safe(self, robot: RobotState, vx: float, vy: float,
                         other_robots: List[RobotState]) -> bool:
        for other in other_robots:
            if other.robot_id == robot.robot_id:
                continue
            if other.floor != robot.floor:
                continue

            rx = robot.x - other.x
            ry = robot.y - other.y
            r = robot.radius + other.radius + self.safety_margin

            if np.sqrt(rx * rx + ry * ry) < r:
                return False

            rel_vx = vx - other.vx
            rel_vy = vy - other.vy

            if abs(rel_vx) < 1e-6 and abs(rel_vy) < 1e-6:
                continue

            t = -(rx * rel_vx + ry * rel_vy) / (rel_vx * rel_vx + rel_vy * rel_vy)

            if 0 < t < self.time_horizon:
                closest_x = rx + rel_vx * t
                closest_y = ry + rel_vy * t
                if np.sqrt(closest_x * closest_x + closest_y * closest_y) < r:
                    return False

        return True

    def select_safe_velocity(self, robot: RobotState, desired_vx: float,
                              desired_vy: float,
                              other_robots: List[RobotState]) -> Tuple[float, float]:
        if self.is_velocity_safe(robot, desired_vx, desired_vy, other_robots):
            return desired_vx, desired_vy

        best_vx, best_vy = 0.0, 0.0
        min_cost = float('inf')

        for angle in np.linspace(0, 2 * np.pi, 36):
            for speed in np.linspace(0, robot.max_speed, 8):
                vx = speed * np.cos(angle)
                vy = speed * np.sin(angle)

                if self.is_velocity_safe(robot, vx, vy, other_robots):
                    dx = vx - desired_vx
                    dy = vy - desired_vy
                    cost = dx * dx + dy * dy

                    if cost < min_cost:
                        min_cost = cost
                        best_vx, best_vy = vx, vy

        return best_vx, best_vy


class MultiRobotCoordinator:
    def __init__(self, grid_map: GridMap = None, map3d: Map3D = None):
        self.grid_map = grid_map
        self.map3d = map3d
        self.robots: Dict[int, RobotState] = {}
        self.velocity_obstacle = VelocityObstacle()
        self.robot_radius = 15.0

        self.next_robot_id = 0

    def add_robot(self, x: float, y: float, floor: int = 0) -> RobotState:
        robot = RobotState(self.next_robot_id, x, y, 0.0, floor)
        robot.radius = self.robot_radius
        self.robots[self.next_robot_id] = robot
        self.next_robot_id += 1
        return robot

    def remove_robot(self, robot_id: int) -> bool:
        if robot_id in self.robots:
            del self.robots[robot_id]
            return True
        return False

    def set_robot_path(self, robot_id: int,
                       path: List[Tuple[float, float, int]]) -> None:
        if robot_id in self.robots and len(path) > 0:
            self.robots[robot_id].path = path
            self.robots[robot_id].path_index = 0
            self.robots[robot_id].goal_reached = False

    def compute_desired_velocity(self, robot: RobotState) -> Tuple[float, float]:
        if not robot.path or robot.path_index >= len(robot.path):
            robot.goal_reached = True
            return 0.0, 0.0

        target_x, target_y, target_floor = robot.path[robot.path_index]

        if target_floor != robot.floor:
            return 0.0, 0.0

        dx = target_x - robot.x
        dy = target_y - robot.y
        dist = np.sqrt(dx * dx + dy * dy)

        if dist < 10.0:
            robot.path_index += 1
            if robot.path_index >= len(robot.path):
                robot.goal_reached = True
                return 0.0, 0.0
            target_x, target_y, _ = robot.path[robot.path_index]
            dx = target_x - robot.x
            dy = target_y - robot.y
            dist = np.sqrt(dx * dx + dy * dy)

        if dist < 1e-6:
            return 0.0, 0.0

        speed = min(robot.max_speed, dist * 2.0)
        vx = (dx / dist) * speed
        vy = (dy / dist) * speed

        return vx, vy

    def update(self, dt: float) -> List[VelocityCommand]:
        commands = []
        other_robots_list = list(self.robots.values())

        for robot_id, robot in self.robots.items():
            if robot.goal_reached:
                cmd = VelocityCommand(0.0, 0.0, 0.0)
                commands.append(cmd)
                continue

            desired_vx, desired_vy = self.compute_desired_velocity(robot)

            safe_vx, safe_vy = self.velocity_obstacle.select_safe_velocity(
                robot, desired_vx, desired_vy, other_robots_list
            )

            dvx = safe_vx - robot.vx
            dvy = safe_vy - robot.vy
            dvs = np.sqrt(dvx * dvx + dvy * dvy)

            if dvs > robot.max_accel * dt:
                scale = (robot.max_accel * dt) / dvs
                robot.vx += dvx * scale
                robot.vy += dvy * scale
            else:
                robot.vx = safe_vx
                robot.vy = safe_vy

            robot.x += robot.vx * dt
            robot.y += robot.vy * dt

            current_speed = np.sqrt(robot.vx ** 2 + robot.vy ** 2)
            if current_speed > 0.1:
                robot.theta = np.arctan2(robot.vy, robot.vx)

            cmd = VelocityCommand(robot.vx, robot.vy, 0.0)
            commands.append(cmd)

        return commands

    def get_robot_states(self) -> List[RobotState]:
        return list(self.robots.values())

    def get_velocity_commands(self) -> Dict[int, VelocityCommand]:
        commands = {}
        for robot_id, robot in self.robots.items():
            commands[robot_id] = VelocityCommand(robot.vx, robot.vy, robot.vtheta)
        return commands
