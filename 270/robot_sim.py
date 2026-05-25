import numpy as np
from typing import Tuple, Dict, List, Optional
from multi_robot import VelocityCommand


class DifferentialDriveSimulator:
    def __init__(self, wheel_base: float = 0.3, wheel_radius: float = 0.05,
                 max_wheel_speed: float = 10.0, noise_level: float = 0.02):
        self.wheel_base = wheel_base
        self.wheel_radius = wheel_radius
        self.max_wheel_speed = max_wheel_speed
        self.noise_level = noise_level

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.v = 0.0
        self.omega = 0.0

    def set_pose(self, x: float, y: float, theta: float) -> None:
        self.x = x
        self.y = y
        self.theta = theta

    def get_pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.theta

    def twist_to_wheel_velocities(self, v: float,
                                   omega: float) -> Tuple[float, float]:
        v_left = v - omega * self.wheel_base / 2.0
        v_right = v + omega * self.wheel_base / 2.0

        v_left = max(-self.max_wheel_speed, min(self.max_wheel_speed, v_left))
        v_right = max(-self.max_wheel_speed, min(self.max_wheel_speed, v_right))

        return v_left, v_right

    def wheel_velocities_to_twist(self, v_left: float,
                                   v_right: float) -> Tuple[float, float]:
        v = (v_left + v_right) / 2.0
        omega = (v_right - v_left) / self.wheel_base
        return v, omega

    def update_with_twist(self, v: float, omega: float, dt: float) -> None:
        v_left, v_right = self.twist_to_wheel_velocities(v, omega)

        v_left += np.random.normal(0, self.noise_level * abs(v_left))
        v_right += np.random.normal(0, self.noise_level * abs(v_right))

        v, omega = self.wheel_velocities_to_twist(v_left, v_right)
        self.v = v
        self.omega = omega

        if abs(omega) > 1e-6:
            self.x += (v / omega) * (np.sin(self.theta + omega * dt) - np.sin(self.theta))
            self.y += (v / omega) * (np.cos(self.theta) - np.cos(self.theta + omega * dt))
            self.theta += omega * dt
        else:
            self.x += v * np.cos(self.theta) * dt
            self.y += v * np.sin(self.theta) * dt

        self.theta = self._wrap_angle(self.theta)

    def _wrap_angle(self, angle: float) -> float:
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle


class OmnidirectionalDriveSimulator:
    def __init__(self, max_speed: float = 1.0, noise_level: float = 0.02):
        self.max_speed = max_speed
        self.noise_level = noise_level

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vtheta = 0.0

    def set_pose(self, x: float, y: float, theta: float) -> None:
        self.x = x
        self.y = y
        self.theta = theta

    def get_pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.theta

    def update_with_velocity(self, vx: float, vy: float, vtheta: float,
                              dt: float) -> None:
        speed = np.sqrt(vx * vx + vy * vy)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            vx *= scale
            vy *= scale

        vx += np.random.normal(0, self.noise_level * abs(vx))
        vy += np.random.normal(0, self.noise_level * abs(vy))
        vtheta += np.random.normal(0, self.noise_level * abs(vtheta))

        self.vx = vx
        self.vy = vy
        self.vtheta = vtheta

        self.x += vx * dt
        self.y += vy * dt
        self.theta += vtheta * dt

        while self.theta > np.pi:
            self.theta -= 2 * np.pi
        while self.theta < -np.pi:
            self.theta += 2 * np.pi


class RobotInterface:
    def __init__(self, robot_id: int, drive_type: str = 'omnidirectional'):
        self.robot_id = robot_id
        self.drive_type = drive_type

        if drive_type == 'differential':
            self.drive = DifferentialDriveSimulator()
        else:
            self.drive = OmnidirectionalDriveSimulator()

        self.floor = 0
        self.radius = 15.0
        self.max_speed = 100.0

        self.path: List[Tuple[float, float, int]] = []
        self.path_index = 0
        self.goal_reached = False

        self.color = (
            np.random.randint(100, 255),
            np.random.randint(100, 255),
            np.random.randint(100, 255)
        )

    def set_start_pose(self, x: float, y: float, theta: float = 0.0,
                       floor: int = 0) -> None:
        self.drive.set_pose(x, y, theta)
        self.floor = floor
        self.path_index = 0
        self.goal_reached = False

    def get_pose(self) -> Tuple[float, float, float, int]:
        x, y, theta = self.drive.get_pose()
        return x, y, theta, self.floor

    def get_velocity(self) -> Tuple[float, float, float]:
        if self.drive_type == 'differential':
            return self.drive.v, 0.0, self.drive.omega
        else:
            return self.drive.vx, self.drive.vy, self.drive.vtheta

    def set_path(self, path: List[Tuple[float, float, int]]) -> None:
        self.path = path
        self.path_index = 0
        self.goal_reached = False

    def compute_desired_velocity(self) -> Tuple[float, float, float]:
        if not self.path or self.path_index >= len(self.path):
            self.goal_reached = True
            return 0.0, 0.0, 0.0

        target_x, target_y, target_floor = self.path[self.path_index]
        current_x, current_y, current_theta, current_floor = self.get_pose()

        if target_floor != current_floor:
            return 0.0, 0.0, 0.0

        dx = target_x - current_x
        dy = target_y - current_y
        dist = np.sqrt(dx * dx + dy * dy)

        if dist < 10.0:
            self.path_index += 1
            if self.path_index >= len(self.path):
                self.goal_reached = True
                return 0.0, 0.0, 0.0
            return self.compute_desired_velocity()

        if dist < 1e-6:
            return 0.0, 0.0, 0.0

        speed = min(self.max_speed, dist * 3.0)
        vx = (dx / dist) * speed
        vy = (dy / dist) * speed

        target_theta = np.arctan2(dy, dx)
        dtheta = target_theta - current_theta
        while dtheta > np.pi:
            dtheta -= 2 * np.pi
        while dtheta < -np.pi:
            dtheta += 2 * np.pi
        vtheta = dtheta * 2.0

        return vx, vy, vtheta

    def update(self, dt: float, override_vx: float = None,
               override_vy: float = None,
               override_vtheta: float = None) -> None:
        if override_vx is not None and override_vy is not None:
            vx, vy, vtheta = override_vx, override_vy, override_vtheta or 0.0
        else:
            vx, vy, vtheta = self.compute_desired_velocity()

        if self.drive_type == 'differential':
            v = np.sqrt(vx * vx + vy * vy)
            if vx < 0:
                v = -v
            self.drive.update_with_twist(v, vtheta, dt)
        else:
            self.drive.update_with_velocity(vx, vy, vtheta, dt)


class RobotSimulationManager:
    def __init__(self):
        self.robots: Dict[int, RobotInterface] = {}
        self.next_robot_id = 0

    def add_robot(self, x: float = 0.0, y: float = 0.0,
                  floor: int = 0,
                  drive_type: str = 'omnidirectional') -> RobotInterface:
        robot = RobotInterface(self.next_robot_id, drive_type)
        robot.set_start_pose(x, y, 0.0, floor)
        self.robots[self.next_robot_id] = robot
        self.next_robot_id += 1
        return robot

    def remove_robot(self, robot_id: int) -> bool:
        if robot_id in self.robots:
            del self.robots[robot_id]
            return True
        return False

    def get_robot(self, robot_id: int) -> Optional[RobotInterface]:
        return self.robots.get(robot_id)

    def send_velocity_command(self, robot_id: int, cmd: VelocityCommand) -> None:
        if robot_id in self.robots:
            self.robots[robot_id].update(
                0.01, cmd.vx, cmd.vy, cmd.vtheta
            )

    def update_all(self, dt: float) -> Dict[int, VelocityCommand]:
        commands = {}
        for robot_id, robot in self.robots.items():
            vx, vy, vtheta = robot.compute_desired_velocity()
            robot.update(dt, vx, vy, vtheta)
            commands[robot_id] = VelocityCommand(vx, vy, vtheta)
        return commands

    def get_all_robot_poses(self) -> Dict[int, Tuple[float, float, float, int]]:
        poses = {}
        for robot_id, robot in self.robots.items():
            poses[robot_id] = robot.get_pose()
        return poses

    def get_all_robot_velocities(self) -> Dict[int, Tuple[float, float, float]]:
        vels = {}
        for robot_id, robot in self.robots.items():
            vels[robot_id] = robot.get_velocity()
        return vels
