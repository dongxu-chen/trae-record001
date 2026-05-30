import copy
import numpy as np
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple


class VectorEditor:
    def __init__(self, svg_path: str = None):
        self.paths: List[Dict] = []
        self.width = 0
        self.height = 0
        self.bg_color = (255, 255, 255)
        self.svg_path = svg_path
        self._history: List[List[Dict]] = []
        self._redo_stack: List[List[Dict]] = []

        if svg_path:
            self.load_svg(svg_path)

    def load_svg(self, svg_path: str):
        self.svg_path = svg_path
        tree = ET.parse(svg_path)
        root = tree.getroot()

        ns = {'svg': 'http://www.w3.org/2000/svg'}

        vb = root.get('viewBox')
        if vb:
            parts = vb.split()
            self.width = float(parts[2])
            self.height = float(parts[3])
        else:
            try:
                self.width = float(root.get('width', 0))
                self.height = float(root.get('height', 0))
            except ValueError:
                self.width = 800
                self.height = 600

        rect_elements = root.findall('.//svg:rect', ns)
        if not rect_elements:
            rect_elements = root.findall('.//{http://www.w3.org/2000/svg}rect')
        if not rect_elements:
            rect_elements = root.iter('rect')
        for rect in rect_elements:
            fill = rect.get('fill', 'rgb(255,255,255)')
            self.bg_color = self._parse_rgb(fill)

        path_elements = root.findall('.//svg:path', ns)
        if not path_elements:
            path_elements = root.findall('.//{http://www.w3.org/2000/svg}path')
        if not path_elements:
            path_elements = root.iter('path')

        for path_elem in path_elements:
            d = path_elem.get('d', '')
            fill = path_elem.get('fill', 'rgb(128,128,128)')
            stroke = path_elem.get('stroke', 'rgb(128,128,128)')
            stroke_width = float(path_elem.get('stroke-width', '1'))

            points = self._parse_path_data(d)
            if len(points) >= 3:
                self.paths.append({
                    'points': points,
                    'fill': self._parse_rgb(fill),
                    'stroke': self._parse_rgb(stroke),
                    'stroke_width': stroke_width,
                    'closed': d.strip().endswith('Z'),
                    'visible': True
                })

    @staticmethod
    def _parse_rgb(color_str: str) -> Tuple[int, int, int]:
        color_str = color_str.strip()
        if color_str.startswith('rgb('):
            inner = color_str[4:-1]
            parts = inner.split(',')
            return (int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip()))
        elif color_str.startswith('#') and len(color_str) == 7:
            r = int(color_str[1:3], 16)
            g = int(color_str[3:5], 16)
            b = int(color_str[5:7], 16)
            return (r, g, b)
        return (128, 128, 128)

    @staticmethod
    def _parse_path_data(d: str) -> List[np.ndarray]:
        points = []
        d = d.replace(',', ' ')
        tokens = d.strip().split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in ('M', 'L', 'm', 'l'):
                i += 1
                if i + 1 < len(tokens):
                    try:
                        x = float(tokens[i])
                        y = float(tokens[i + 1])
                        points.append(np.array([x, y], dtype=np.float64))
                        i += 2
                    except ValueError:
                        i += 1
                else:
                    i += 1
            elif token.upper() == 'Z':
                i += 1
            else:
                try:
                    x = float(token)
                    if i + 1 < len(tokens):
                        y = float(tokens[i + 1])
                        points.append(np.array([x, y], dtype=np.float64))
                        i += 2
                    else:
                        i += 1
                except ValueError:
                    i += 1
        return points

    def _save_state(self):
        self._history.append(copy.deepcopy(self.paths))
        self._redo_stack.clear()
        if len(self._history) > 50:
            self._history.pop(0)

    def undo(self):
        if self._history:
            self._redo_stack.append(copy.deepcopy(self.paths))
            self.paths = self._history.pop()

    def redo(self):
        if self._redo_stack:
            self._history.append(copy.deepcopy(self.paths))
            self.paths = self._redo_stack.pop()

    def get_path_count(self) -> int:
        return len(self.paths)

    def get_path_points(self, path_index: int) -> List[np.ndarray]:
        if 0 <= path_index < len(self.paths):
            return self.paths[path_index]['points']
        return []

    def move_anchor(self, path_index: int, point_index: int, new_x: float, new_y: float):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            if 0 <= point_index < len(points):
                points[point_index] = np.array([new_x, new_y], dtype=np.float64)

    def move_anchor_delta(self, path_index: int, point_index: int, dx: float, dy: float):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            if 0 <= point_index < len(points):
                points[point_index] += np.array([dx, dy], dtype=np.float64)

    def add_anchor(self, path_index: int, after_index: int, x: float, y: float):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            insert_pos = after_index + 1
            if 0 <= after_index < len(points):
                points.insert(insert_pos, np.array([x, y], dtype=np.float64))

    def remove_anchor(self, path_index: int, point_index: int):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            if 0 <= point_index < len(points) and len(points) > 3:
                points.pop(point_index)

    def smooth_path(self, path_index: int, iterations: int = 3, factor: float = 0.5):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            n = len(points)
            if n < 3:
                return

            for _ in range(iterations):
                new_points = []
                for i in range(n):
                    prev_i = (i - 1) % n
                    next_i = (i + 1) % n
                    neighbor_avg = (points[prev_i] + points[next_i]) / 2.0
                    smoothed = points[i] * (1 - factor) + neighbor_avg * factor
                    new_points.append(smoothed)
                points = new_points

            self.paths[path_index]['points'] = points

    def simplify_path(self, path_index: int, tolerance: float = 2.0):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            if len(points) < 3:
                return

            simplified = [points[0]]
            for point in points[1:]:
                dist = np.linalg.norm(point - simplified[-1])
                if dist > tolerance:
                    simplified.append(point)

            if len(simplified) >= 3:
                self.paths[path_index]['points'] = simplified

    def set_path_color(self, path_index: int, fill: Tuple[int, int, int] = None,
                       stroke: Tuple[int, int, int] = None):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            if fill is not None:
                self.paths[path_index]['fill'] = fill
            if stroke is not None:
                self.paths[path_index]['stroke'] = stroke

    def set_path_stroke_width(self, path_index: int, width: float):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            self.paths[path_index]['stroke_width'] = width

    def toggle_path_visibility(self, path_index: int):
        if 0 <= path_index < len(self.paths):
            self.paths[path_index]['visible'] = not self.paths[path_index]['visible']

    def delete_path(self, path_index: int):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            self.paths.pop(path_index)

    def merge_paths(self, index_a: int, index_b: int):
        self._save_state()
        if (0 <= index_a < len(self.paths) and 0 <= index_b < len(self.paths)
                and index_a != index_b):
            points_a = self.paths[index_a]['points']
            points_b = self.paths[index_b]['points']
            merged = points_a + points_b
            self.paths[index_a]['points'] = merged
            self.paths.pop(index_b)

    def split_path(self, path_index: int, split_point_index: int):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            if 3 <= split_point_index < len(points) - 3:
                part_a = points[:split_point_index]
                part_b = points[split_point_index:]

                if len(part_a) >= 3 and len(part_b) >= 3:
                    self.paths[path_index]['points'] = part_a
                    new_path = copy.deepcopy(self.paths[path_index])
                    new_path['points'] = part_b
                    self.paths.insert(path_index + 1, new_path)

    def transform_path(self, path_index: int, translate: Tuple[float, float] = (0, 0),
                       scale: Tuple[float, float] = (1, 1), rotate: float = 0):
        self._save_state()
        if 0 <= path_index < len(self.paths):
            points = self.paths[path_index]['points']
            centroid = np.mean(points, axis=0)

            new_points = []
            for pt in points:
                p = pt - centroid
                p[0] *= scale[0]
                p[1] *= scale[1]

                if rotate != 0:
                    rad = np.radians(rotate)
                    cos_r, sin_r = np.cos(rad), np.sin(rad)
                    x_new = p[0] * cos_r - p[1] * sin_r
                    y_new = p[0] * sin_r + p[1] * cos_r
                    p = np.array([x_new, y_new])

                p += centroid + np.array(translate)
                new_points.append(p)

            self.paths[path_index]['points'] = new_points

    def find_nearest_anchor(self, x: float, y: float, max_distance: float = 10.0) -> Optional[Tuple[int, int]]:
        query = np.array([x, y], dtype=np.float64)
        best_dist = max_distance
        best_result = None

        for pi, path in enumerate(self.paths):
            if not path['visible']:
                continue
            for ai, point in enumerate(path['points']):
                dist = np.linalg.norm(point - query)
                if dist < best_dist:
                    best_dist = dist
                    best_result = (pi, ai)

        return best_result

    def save_svg(self, output_path: str = None):
        output_path = output_path or self.svg_path
        if not output_path:
            raise ValueError("未指定输出路径")

        import svgwrite
        dwg = svgwrite.Drawing(output_path, size=(self.width, self.height), profile='tiny')

        dwg.add(dwg.rect(insert=(0, 0), size=(self.width, self.height),
                          fill=f'rgb({self.bg_color[0]},{self.bg_color[1]},{self.bg_color[2]})'))

        for path in self.paths:
            if not path['visible']:
                continue

            points = path['points']
            if len(points) < 3:
                continue

            d = f"M {points[0][0]:.2f},{points[0][1]:.2f} "
            for pt in points[1:]:
                d += f"L {pt[0]:.2f},{pt[1]:.2f} "
            if path['closed']:
                d += "Z"

            dwg.add(dwg.path(
                d=d,
                fill=f'rgb({path["fill"][0]},{path["fill"][1]},{path["fill"][2]})',
                stroke=f'rgb({path["stroke"][0]},{path["stroke"][1]},{path["stroke"][2]})',
                stroke_width=path['stroke_width']
            ))

        dwg.save()
        return output_path

    def get_edit_info(self) -> Dict:
        total_points = sum(len(p['points']) for p in self.paths)
        visible = sum(1 for p in self.paths if p['visible'])
        return {
            'total_paths': len(self.paths),
            'visible_paths': visible,
            'total_anchors': total_points,
            'canvas_size': (self.width, self.height),
            'undo_available': len(self._history) > 0,
            'redo_available': len(self._redo_stack) > 0
        }
