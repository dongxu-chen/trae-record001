import numpy as np
from shapely.geometry import Point, Polygon
from typing import List, Tuple


class DynamicObstacle:
    def __init__(self, obstacle_id: int, shape: str, **kwargs):
        self.id = obstacle_id
        self.shape = shape
        self.velocity = np.array([0.0, 0.0])
        self.position = np.array([0.0, 0.0])

        if shape == 'circle':
            self.radius = kwargs.get('radius', 10.0)
            self.position = np.array([kwargs.get('x', 0.0), kwargs.get('y', 0.0)])
        elif shape == 'rectangle':
            self.width = kwargs.get('width', 20.0)
            self.height = kwargs.get('height', 20.0)
            self.position = np.array([kwargs.get('x', 0.0), kwargs.get('y', 0.0)])
        elif shape == 'polygon':
            self.vertices = np.array(kwargs.get('vertices', []), dtype=np.float64)
            if len(self.vertices) > 0:
                self.position = np.mean(self.vertices, axis=0)

        self.waypoints = []
        self.current_waypoint_idx = 0
        self.speed = 0.0

    def set_linear_velocity(self, vx: float, vy: float) -> None:
        self.velocity = np.array([vx, vy])

    def set_waypoints(self, waypoints: List[Tuple[float, float]], speed: float = 50.0) -> None:
        self.waypoints = [np.array(wp) for wp in waypoints]
        self.speed = speed
        self.current_waypoint_idx = 0
        if len(self.waypoints) > 0:
            self._update_velocity_to_waypoint()

    def _update_velocity_to_waypoint(self) -> None:
        if self.current_waypoint_idx < len(self.waypoints):
            target = self.waypoints[self.current_waypoint_idx]
            direction = target - self.position
            dist = np.linalg.norm(direction)
            if dist > 1e-6:
                self.velocity = direction / dist * self.speed
            else:
                self.velocity = np.array([0.0, 0.0])

    def update(self, dt: float) -> None:
        if len(self.waypoints) > 0:
            target = self.waypoints[self.current_waypoint_idx]
            direction = target - self.position
            dist = np.linalg.norm(direction)

            if dist < self.speed * dt:
                self.position = target.copy()
                self.current_waypoint_idx = (self.current_waypoint_idx + 1) % len(self.waypoints)
                self._update_velocity_to_waypoint()
            else:
                self.position += self.velocity * dt
        else:
            self.position += self.velocity * dt

    def get_shapely_geometry(self) -> Polygon:
        if self.shape == 'circle':
            return Point(self.position[0], self.position[1]).buffer(self.radius)
        elif self.shape == 'rectangle':
            x, y = self.position
            w, h = self.width, self.height
            return Polygon([
                (x - w / 2, y - h / 2),
                (x + w / 2, y - h / 2),
                (x + w / 2, y + h / 2),
                (x - w / 2, y + h / 2)
            ])
        elif self.shape == 'polygon':
            centered_vertices = self.vertices - np.mean(self.vertices, axis=0) + self.position
            return Polygon(centered_vertices)
        return None

    def check_collision(self, x: float, y: float, robot_radius: float = 0.0) -> bool:
        if self.shape == 'circle':
            dx = x - self.position[0]
            dy = y - self.position[1]
            dist = np.sqrt(dx * dx + dy * dy)
            return dist < (self.radius + robot_radius)
        elif self.shape == 'rectangle':
            half_w = self.width / 2 + robot_radius
            half_h = self.height / 2 + robot_radius
            return (self.position[0] - half_w < x < self.position[0] + half_w and
                    self.position[1] - half_h < y < self.position[1] + half_h)
        elif self.shape == 'polygon':
            point = Point(x, y).buffer(robot_radius)
            polygon = self.get_shapely_geometry()
            return point.intersects(polygon)
        return False

    def check_line_collision(self, x1: float, y1: float, x2: float, y2: float,
                             robot_radius: float = 0.0, step_size: float = 1.0) -> bool:
        dx = x2 - x1
        dy = y2 - y1
        dist = np.sqrt(dx * dx + dy * dy)

        if dist < 1e-6:
            return self.check_collision(x1, y1, robot_radius)

        steps = int(dist / step_size) + 1
        for i in range(steps + 1):
            t = i / steps
            x = x1 + dx * t
            y = y1 + dy * t
            if self.check_collision(x, y, robot_radius):
                return True

        return False


class ObstacleManager:
    def __init__(self):
        self.static_obstacles = []
        self.dynamic_obstacles: List[DynamicObstacle] = []
        self._next_id = 0

    def add_dynamic_obstacle(self, shape: str, **kwargs) -> DynamicObstacle:
        obstacle = DynamicObstacle(self._next_id, shape, **kwargs)
        self.dynamic_obstacles.append(obstacle)
        self._next_id += 1
        return obstacle

    def remove_dynamic_obstacle(self, obstacle_id: int) -> bool:
        for i, obs in enumerate(self.dynamic_obstacles):
            if obs.id == obstacle_id:
                del self.dynamic_obstacles[i]
                return True
        return False

    def update_all(self, dt: float) -> None:
        for obstacle in self.dynamic_obstacles:
            obstacle.update(dt)

    def check_collision(self, x: float, y: float, robot_radius: float = 0.0) -> bool:
        for obstacle in self.dynamic_obstacles:
            if obstacle.check_collision(x, y, robot_radius):
                return True
        return False

    def check_line_collision(self, x1: float, y1: float, x2: float, y2: float,
                             robot_radius: float = 0.0, step_size: float = 1.0) -> bool:
        for obstacle in self.dynamic_obstacles:
            if obstacle.check_line_collision(x1, y1, x2, y2, robot_radius, step_size):
                return True
        return False

    def get_all_obstacle_geometries(self) -> list:
        geometries = []
        for obstacle in self.dynamic_obstacles:
            geo = obstacle.get_shapely_geometry()
            if geo is not None:
                geometries.append(geo)
        return geometries
