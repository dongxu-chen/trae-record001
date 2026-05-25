import numpy as np
import json
from PIL import Image
from shapely.geometry import Point, Polygon


class GridMap:
    def __init__(self, width: int = 800, height: int = 600, resolution: float = 1.0):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)
        self.obstacle_polygons = []

    def load_from_image(self, image_path: str, threshold: int = 128) -> None:
        img = Image.open(image_path).convert('L')
        img = img.resize((self.grid_width, self.grid_height))
        img_array = np.array(img)
        self.grid = (img_array < threshold).astype(np.uint8)

    def load_from_json(self, json_path: str) -> None:
        with open(json_path, 'r') as f:
            data = json.load(f)

        self.width = data.get('width', self.width)
        self.height = data.get('height', self.height)
        self.resolution = data.get('resolution', self.resolution)
        self.grid_width = int(self.width / self.resolution)
        self.grid_height = int(self.height / self.resolution)
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=np.uint8)

        obstacles = data.get('obstacles', [])
        for obstacle in obstacles:
            obstacle_type = obstacle.get('type', 'rectangle')
            if obstacle_type == 'rectangle':
                self._add_rectangle_obstacle(obstacle)
            elif obstacle_type == 'circle':
                self._add_circle_obstacle(obstacle)
            elif obstacle_type == 'polygon':
                self._add_polygon_obstacle(obstacle)

    def _add_rectangle_obstacle(self, obstacle: dict) -> None:
        x = int(obstacle.get('x', 0) / self.resolution)
        y = int(obstacle.get('y', 0) / self.resolution)
        w = int(obstacle.get('width', 0) / self.resolution)
        h = int(obstacle.get('height', 0) / self.resolution)

        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self.grid_width, x + w)
        y2 = min(self.grid_height, y + h)

        self.grid[y1:y2, x1:x2] = 1

        polygon = Polygon([
            (x * self.resolution, y * self.resolution),
            ((x + w) * self.resolution, y * self.resolution),
            ((x + w) * self.resolution, (y + h) * self.resolution),
            (x * self.resolution, (y + h) * self.resolution)
        ])
        self.obstacle_polygons.append(polygon)

    def _add_circle_obstacle(self, obstacle: dict) -> None:
        cx = obstacle.get('x', 0)
        cy = obstacle.get('y', 0)
        radius = obstacle.get('radius', 0)

        cx_grid = int(cx / self.resolution)
        cy_grid = int(cy / self.resolution)
        r_grid = int(radius / self.resolution)

        y, x = np.ogrid[-cy_grid:self.grid_height - cy_grid, -cx_grid:self.grid_width - cx_grid]
        mask = x * x + y * y <= r_grid * r_grid
        self.grid[mask] = 1

        circle = Point(cx, cy).buffer(radius)
        self.obstacle_polygons.append(circle)

    def _add_polygon_obstacle(self, obstacle: dict) -> None:
        vertices = obstacle.get('vertices', [])
        if len(vertices) < 3:
            return

        vertices_array = np.array(vertices, dtype=np.float32)
        min_x = int(np.min(vertices_array[:, 0]) / self.resolution)
        max_x = int(np.max(vertices_array[:, 0]) / self.resolution)
        min_y = int(np.min(vertices_array[:, 1]) / self.resolution)
        max_y = int(np.max(vertices_array[:, 1]) / self.resolution)

        for y in range(max(0, min_y), min(self.grid_height, max_y + 1)):
            for x in range(max(0, min_x), min(self.grid_width, max_x + 1)):
                if self._point_in_polygon(x * self.resolution, y * self.resolution, vertices):
                    self.grid[y, x] = 1

        polygon = Polygon(vertices)
        self.obstacle_polygons.append(polygon)

    def _point_in_polygon(self, px: float, py: float, vertices: list) -> bool:
        n = len(vertices)
        inside = False
        x_ints = 0.0
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside
            j = i
        return inside

    def is_collision(self, x: float, y: float, robot_radius: float = 0.0) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True

        if robot_radius > 0:
            grid_r = int(robot_radius / self.resolution)
            gx = int(x / self.resolution)
            gy = int(y / self.resolution)

            x1 = max(0, gx - grid_r)
            y1 = max(0, gy - grid_r)
            x2 = min(self.grid_width, gx + grid_r + 1)
            y2 = min(self.grid_height, gy + grid_r + 1)

            if np.any(self.grid[y1:y2, x1:x2] == 1):
                return True
        else:
            gx = int(x / self.resolution)
            gy = int(y / self.resolution)
            if self.grid[gy, gx] == 1:
                return True

        return False

    def is_line_collision(self, x1: float, y1: float, x2: float, y2: float,
                          robot_radius: float = 0.0, step_size: float = 1.0) -> bool:
        dx = x2 - x1
        dy = y2 - y1
        dist = np.sqrt(dx * dx + dy * dy)

        if dist < 1e-6:
            return self.is_collision(x1, y1, robot_radius)

        steps = int(dist / step_size) + 1
        for i in range(steps + 1):
            t = i / steps
            x = x1 + dx * t
            y = y1 + dy * t
            if self.is_collision(x, y, robot_radius):
                return True

        return False

    def get_free_space(self) -> list:
        free_cells = np.argwhere(self.grid == 0)
        return [(float(y) * self.resolution, float(x) * self.resolution) for y, x in free_cells]

    def save_to_json(self, json_path: str) -> None:
        data = {
            'width': self.width,
            'height': self.height,
            'resolution': self.resolution,
            'obstacles': []
        }

        for polygon in self.obstacle_polygons:
            if polygon.geom_type == 'Polygon':
                coords = list(polygon.exterior.coords)[:-1]
                data['obstacles'].append({
                    'type': 'polygon',
                    'vertices': [[float(c[0]), float(c[1])] for c in coords]
                })

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
