import numpy as np
import json
from typing import List, Tuple, Dict, Optional
from map import GridMap


class FloorConnection:
    def __init__(self, conn_type: str, floor1: int, floor2: int,
                 pos1: Tuple[float, float], pos2: Tuple[float, float],
                 speed: float = 1.0):
        self.type = conn_type
        self.floor1 = floor1
        self.floor2 = floor2
        self.pos1 = pos1
        self.pos2 = pos2
        self.speed = speed


class Floor3D:
    def __init__(self, floor_id: int, width: int = 800, height: int = 600,
                 resolution: float = 5.0, name: str = None):
        self.floor_id = floor_id
        self.name = name or f"Floor {floor_id}"
        self.grid_map = GridMap(width, height, resolution)
        self.connections: List[FloorConnection] = []

    def load_from_json(self, data: dict) -> None:
        obstacles = data.get('obstacles', [])
        for obs in obstacles:
            obs_type = obs.get('type', 'rectangle')
            if obs_type == 'rectangle':
                self.grid_map._add_rectangle_obstacle(obs)
            elif obs_type == 'circle':
                self.grid_map._add_circle_obstacle(obs)
            elif obs_type == 'polygon':
                self.grid_map._add_polygon_obstacle(obs)

    def add_connection(self, connection: FloorConnection) -> None:
        self.connections.append(connection)


class Map3D:
    def __init__(self, floor_width: int = 800, floor_height: int = 600,
                 resolution: float = 5.0):
        self.floor_width = floor_width
        self.floor_height = floor_height
        self.resolution = resolution
        self.floors: Dict[int, Floor3D] = {}
        self.connections: List[FloorConnection] = []

    def add_floor(self, floor_id: int, name: str = None) -> Floor3D:
        floor = Floor3D(floor_id, self.floor_width, self.floor_height,
                        self.resolution, name)
        self.floors[floor_id] = floor
        return floor

    def get_floor(self, floor_id: int) -> Optional[Floor3D]:
        return self.floors.get(floor_id)

    def add_connection(self, conn_type: str, floor1: int, floor2: int,
                       pos1: Tuple[float, float], pos2: Tuple[float, float],
                       speed: float = 1.0) -> FloorConnection:
        connection = FloorConnection(conn_type, floor1, floor2, pos1, pos2, speed)
        self.connections.append(connection)

        if floor1 in self.floors:
            self.floors[floor1].add_connection(connection)
        if floor2 in self.floors:
            self.floors[floor2].add_connection(connection)

        return connection

    def get_connections_from_floor(self, floor_id: int) -> List[FloorConnection]:
        return [c for c in self.connections
                if c.floor1 == floor_id or c.floor2 == floor_id]

    def is_valid_3d(self, x: float, y: float, floor: int,
                    robot_radius: float = 0.0) -> bool:
        if floor not in self.floors:
            return False
        return not self.floors[floor].grid_map.is_collision(x, y, robot_radius)

    def is_line_valid_3d(self, x1: float, y1: float, x2: float, y2: float,
                         floor: int, robot_radius: float = 0.0) -> bool:
        if floor not in self.floors:
            return False
        return not self.floors[floor].grid_map.is_line_collision(
            x1, y1, x2, y2, robot_radius
        )

    def load_from_json(self, json_path: str) -> None:
        with open(json_path, 'r') as f:
            data = json.load(f)

        floors_data = data.get('floors', [])
        for floor_data in floors_data:
            floor_id = floor_data.get('id', 0)
            floor_name = floor_data.get('name', None)
            floor = self.add_floor(floor_id, floor_name)
            floor.load_from_json(floor_data)

        connections_data = data.get('connections', [])
        for conn_data in connections_data:
            self.add_connection(
                conn_data.get('type', 'stairs'),
                conn_data.get('floor1', 0),
                conn_data.get('floor2', 1),
                tuple(conn_data.get('pos1', [0, 0])),
                tuple(conn_data.get('pos2', [0, 0])),
                conn_data.get('speed', 1.0)
            )

    def save_to_json(self, json_path: str) -> None:
        data = {
            'floor_width': self.floor_width,
            'floor_height': self.floor_height,
            'resolution': self.resolution,
            'floors': [],
            'connections': []
        }

        for floor_id, floor in self.floors.items():
            floor_data = {
                'id': floor_id,
                'name': floor.name,
                'obstacles': []
            }
            data['floors'].append(floor_data)

        for conn in self.connections:
            data['connections'].append({
                'type': conn.type,
                'floor1': conn.floor1,
                'floor2': conn.floor2,
                'pos1': list(conn.pos1),
                'pos2': list(conn.pos2),
                'speed': conn.speed
            })

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_floor_ids(self) -> List[int]:
        return sorted(list(self.floors.keys()))
