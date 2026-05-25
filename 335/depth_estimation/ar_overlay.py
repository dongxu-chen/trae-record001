import numpy as np
import cv2
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field

from .camera_calibration import CameraCalibrator


@dataclass
class ARConfig:
    enabled: bool = True
    object_scale: float = 1.0
    object_color: Tuple[int, int, int] = (0, 255, 0)
    object_alpha: float = 0.7
    occlusion_threshold: float = 0.05
    shadow_enabled: bool = True
    shadow_alpha: float = 0.3
    wireframe: bool = False
    place_on_surface: bool = True
    surface_offset: float = 0.0
    min_depth_for_placement: float = 0.1
    max_depth_for_placement: float = 10.0
    object_type: str = 'cube'


@dataclass
class ARObject:
    position_3d: np.ndarray
    rotation: np.ndarray = field(default_factory=lambda: np.eye(3))
    scale: float = 1.0
    color: Tuple[int, int, int] = (0, 255, 0)
    alpha: float = 0.7
    object_type: str = 'cube'
    visible: bool = True


class AROverlay:
    def __init__(self, 
                 calibrator: CameraCalibrator,
                 config: ARConfig = ARConfig()):
        self.calibrator = calibrator
        self.config = config
        self.objects: List[ARObject] = []
        self._current_depth = None
    
    def add_object(self, 
                   position_3d: np.ndarray,
                   object_type: str = 'cube',
                   scale: Optional[float] = None,
                   color: Optional[Tuple[int, int, int]] = None,
                   alpha: Optional[float] = None) -> int:
        obj = ARObject(
            position_3d=position_3d.copy(),
            scale=scale if scale is not None else self.config.object_scale,
            color=color if color is not None else self.config.object_color,
            alpha=alpha if alpha is not None else self.config.object_alpha,
            object_type=object_type
        )
        self.objects.append(obj)
        return len(self.objects) - 1
    
    def remove_object(self, index: int):
        if 0 <= index < len(self.objects):
            self.objects.pop(index)
    
    def clear_objects(self):
        self.objects.clear()
    
    def update_object_position(self, index: int, position_3d: np.ndarray):
        if 0 <= index < len(self.objects):
            self.objects[index].position_3d = position_3d.copy()
    
    def place_object_at_pixel(self, 
                              depth_map: np.ndarray,
                              pixel_x: int, 
                              pixel_y: int,
                              object_type: str = 'cube',
                              scale: Optional[float] = None,
                              color: Optional[Tuple[int, int, int]] = None) -> Optional[int]:
        if pixel_y < 0 or pixel_y >= depth_map.shape[0] or \
           pixel_x < 0 or pixel_x >= depth_map.shape[1]:
            return None
        
        depth = depth_map[pixel_y, pixel_x]
        
        if depth <= 0 or not np.isfinite(depth):
            return None
        
        if depth < self.config.min_depth_for_placement or \
           depth > self.config.max_depth_for_placement:
            return None
        
        point_3d = self.calibrator.backproject_to_3d(pixel_x, pixel_y, depth)
        
        if self.config.place_on_surface:
            point_3d[2] += self.config.surface_offset
        
        return self.add_object(point_3d, object_type, scale, color)
    
    def place_object_on_surface(self,
                                 depth_map: np.ndarray,
                                 pixel_x: int,
                                 pixel_y: int,
                                 surface_normal: Optional[np.ndarray] = None,
                                 object_type: str = 'cube',
                                 scale: Optional[float] = None) -> Optional[int]:
        search_radius = 5
        h, w = depth_map.shape
        
        for r in range(search_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    px = pixel_x + dx
                    py = pixel_y + dy
                    
                    if 0 <= px < w and 0 <= py < h:
                        depth = depth_map[py, px]
                        if depth > 0 and np.isfinite(depth):
                            point_3d = self.calibrator.backproject_to_3d(px, py, depth)
                            
                            if surface_normal is not None:
                                point_3d += surface_normal * self.config.surface_offset
                            
                            return self.add_object(point_3d, object_type, scale)
        
        return None
    
    def render(self, 
               rgb_image: np.ndarray,
               depth_map: np.ndarray) -> np.ndarray:
        if not self.objects:
            return rgb_image.copy()
        
        output = rgb_image.copy()
        
        for obj in self.objects:
            if not obj.visible:
                continue
            
            if obj.object_type == 'cube':
                output = self._render_cube(output, depth_map, obj)
            elif obj.object_type == 'sphere':
                output = self._render_sphere(output, depth_map, obj)
            elif obj.object_type == 'pyramid':
                output = self._render_pyramid(output, depth_map, obj)
            elif obj.object_type == 'cylinder':
                output = self._render_cylinder(output, depth_map, obj)
        
        return output
    
    def _render_cube(self, 
                     image: np.ndarray,
                     depth_map: np.ndarray,
                     obj: ARObject) -> np.ndarray:
        half_size = obj.scale / 2.0
        
        corners_3d = [
            np.array([-half_size, -half_size, -half_size]),
            np.array([half_size, -half_size, -half_size]),
            np.array([half_size, half_size, -half_size]),
            np.array([-half_size, half_size, -half_size]),
            np.array([-half_size, -half_size, half_size]),
            np.array([half_size, -half_size, half_size]),
            np.array([half_size, half_size, half_size]),
            np.array([-half_size, half_size, half_size]),
        ]
        
        corners_3d_rotated = [
            obj.rotation @ corner + obj.position_3d
            for corner in corners_3d
        ]
        
        corners_2d = []
        for corner in corners_3d_rotated:
            u, v = self.calibrator.project_to_pixel(corner)
            corners_2d.append((u, v))
        
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]
        
        output = image.copy()
        
        if not self.config.wireframe:
            faces = [
                [0, 1, 2, 3],
                [4, 5, 6, 7],
                [0, 1, 5, 4],
                [2, 3, 7, 6],
                [1, 2, 6, 5],
                [0, 3, 7, 4]
            ]
            
            for face in faces:
                pts = np.array([corners_2d[i] for i in face], dtype=np.int32)
                
                face_center_3d = np.mean([corners_3d_rotated[i] for i in face], axis=0)
                
                if self._check_occlusion(face_center_3d, depth_map):
                    continue
                
                overlay = output.copy()
                cv2.fillPoly(overlay, [pts], obj.color[::-1])
                
                output = cv2.addWeighted(
                    output, 1 - obj.alpha,
                    overlay, obj.alpha, 0
                )
        
        for edge in edges:
            pt1 = corners_2d[edge[0]]
            pt2 = corners_2d[edge[1]]
            
            mid_3d = (corners_3d_rotated[edge[0]] + corners_3d_rotated[edge[1]]) / 2
            
            if self._check_occlusion(mid_3d, depth_map):
                continue
            
            cv2.line(output, pt1, pt2, obj.color[::-1], 2, cv2.LINE_AA)
        
        return output
    
    def _render_sphere(self,
                       image: np.ndarray,
                       depth_map: np.ndarray,
                       obj: ARObject) -> np.ndarray:
        u, v = self.calibrator.project_to_pixel(obj.position_3d)
        
        if u < 0 or u >= image.shape[1] or v < 0 or v >= image.shape[0]:
            return image
        
        radius_3d = obj.scale / 2.0
        
        top_point = obj.position_3d + np.array([0, -radius_3d, 0])
        bottom_point = obj.position_3d + np.array([0, radius_3d, 0])
        
        u_top, v_top = self.calibrator.project_to_pixel(top_point)
        u_bot, v_bot = self.calibrator.project_to_pixel(bottom_point)
        
        radius_2d = max(abs(v_top - v_bot) // 2, 1)
        
        if self._check_occlusion(obj.position_3d, depth_map):
            return image
        
        output = image.copy()
        
        if not self.config.wireframe:
            overlay = output.copy()
            cv2.circle(overlay, (u, v), radius_2d, obj.color[::-1], -1)
            output = cv2.addWeighted(
                output, 1 - obj.alpha,
                overlay, obj.alpha, 0
            )
        
        cv2.circle(output, (u, v), radius_2d, obj.color[::-1], 2, cv2.LINE_AA)
        
        return output
    
    def _render_pyramid(self,
                        image: np.ndarray,
                        depth_map: np.ndarray,
                        obj: ARObject) -> np.ndarray:
        half_base = obj.scale / 2.0
        height = obj.scale
        
        base_corners = [
            np.array([-half_base, half_base, -half_base]),
            np.array([half_base, half_base, -half_base]),
            np.array([half_base, half_base, half_base]),
            np.array([-half_base, half_base, half_base]),
        ]
        apex = np.array([0, -half_base, 0])
        
        corners_3d = [
            obj.rotation @ corner + obj.position_3d
            for corner in base_corners + [apex]
        ]
        
        corners_2d = []
        for corner in corners_3d:
            u, v = self.calibrator.project_to_pixel(corner)
            corners_2d.append((u, v))
        
        output = image.copy()
        
        faces = [
            [0, 1, 2, 3],
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4]
        ]
        
        for face in faces:
            pts = np.array([corners_2d[i] for i in face], dtype=np.int32)
            
            face_center_3d = np.mean([corners_3d[i] for i in face], axis=0)
            
            if self._check_occlusion(face_center_3d, depth_map):
                continue
            
            if not self.config.wireframe:
                overlay = output.copy()
                cv2.fillPoly(overlay, [pts], obj.color[::-1])
                output = cv2.addWeighted(
                    output, 1 - obj.alpha,
                    overlay, obj.alpha, 0
                )
            else:
                cv2.polylines(output, [pts], True, obj.color[::-1], 2, cv2.LINE_AA)
        
        return output
    
    def _render_cylinder(self,
                         image: np.ndarray,
                         depth_map: np.ndarray,
                         obj: ARObject) -> np.ndarray:
        radius = obj.scale / 2.0
        height = obj.scale
        
        num_segments = 32
        angles = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
        
        top_points = []
        bottom_points = []
        
        for angle in angles:
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            
            top_3d = np.array([x, -height/2, z])
            bottom_3d = np.array([x, height/2, z])
            
            top_3d_rotated = obj.rotation @ top_3d + obj.position_3d
            bottom_3d_rotated = obj.rotation @ bottom_3d + obj.position_3d
            
            u_top, v_top = self.calibrator.project_to_pixel(top_3d_rotated)
            u_bot, v_bot = self.calibrator.project_to_pixel(bottom_3d_rotated)
            
            top_points.append((u_top, v_top))
            bottom_points.append((u_bot, v_bot))
        
        output = image.copy()
        
        center_depth = self._get_depth_at_3d_point(obj.position_3d, depth_map)
        
        if center_depth > 0 and not self._check_occlusion(obj.position_3d, depth_map):
            if not self.config.wireframe:
                top_pts = np.array(top_points, dtype=np.int32)
                bot_pts = np.array(bottom_points, dtype=np.int32)
                
                side_pts = np.vstack([top_pts, bot_pts[::-1]])
                
                overlay = output.copy()
                cv2.fillPoly(overlay, [side_pts], obj.color[::-1])
                cv2.fillPoly(overlay, [top_pts], obj.color[::-1])
                cv2.fillPoly(overlay, [bot_pts], obj.color[::-1])
                
                output = cv2.addWeighted(
                    output, 1 - obj.alpha,
                    overlay, obj.alpha, 0
                )
            
            for i in range(num_segments):
                next_i = (i + 1) % num_segments
                
                mid_top = (np.array([top_points[i][0], top_points[i][1]]) + 
                          np.array([top_points[next_i][0], top_points[next_i][1]])) / 2
                mid_bot = (np.array([bottom_points[i][0], bottom_points[i][1]]) + 
                          np.array([bottom_points[next_i][0], bottom_points[next_i][1]])) / 2
                
                cv2.line(output, top_points[i], top_points[next_i], obj.color[::-1], 2, cv2.LINE_AA)
                cv2.line(output, bottom_points[i], bottom_points[next_i], obj.color[::-1], 2, cv2.LINE_AA)
                cv2.line(output, top_points[i], bottom_points[i], obj.color[::-1], 2, cv2.LINE_AA)
        
        return output
    
    def _check_occlusion(self, 
                         point_3d: np.ndarray,
                         depth_map: np.ndarray) -> bool:
        u, v = self.calibrator.project_to_pixel(point_3d)
        
        h, w = depth_map.shape
        if u < 0 or u >= w or v < 0 or v >= h:
            return True
        
        scene_depth = depth_map[v, u]
        
        if scene_depth <= 0 or not np.isfinite(scene_depth):
            return False
        
        object_depth = point_3d[2]
        
        return object_depth > scene_depth + self.config.occlusion_threshold
    
    def _get_depth_at_3d_point(self,
                                point_3d: np.ndarray,
                                depth_map: np.ndarray) -> float:
        u, v = self.calibrator.project_to_pixel(point_3d)
        
        h, w = depth_map.shape
        if u < 0 or u >= w or v < 0 or v >= h:
            return 0.0
        
        return float(depth_map[v, u])
    
    def get_object_position_3d(self, index: int) -> Optional[np.ndarray]:
        if 0 <= index < len(self.objects):
            return self.objects[index].position_3d.copy()
        return None
    
    def get_object_screen_position(self, index: int) -> Optional[Tuple[int, int]]:
        if 0 <= index < len(self.objects):
            return self.calibrator.project_to_pixel(
                self.objects[index].position_3d
            )
        return None
    
    def get_objects_stats(self) -> Dict:
        return {
            'num_objects': len(self.objects),
            'objects': [
                {
                    'position_3d': obj.position_3d.tolist(),
                    'type': obj.object_type,
                    'scale': obj.scale,
                    'visible': obj.visible
                }
                for obj in self.objects
            ]
        }
    
    def render_shadow(self,
                      image: np.ndarray,
                      depth_map: np.ndarray,
                      ground_y: float = 0.0) -> np.ndarray:
        if not self.config.shadow_enabled or not self.objects:
            return image
        
        output = image.copy()
        
        for obj in self.objects:
            if not obj.visible:
                continue
            
            shadow_position = obj.position_3d.copy()
            shadow_position[1] = ground_y
            
            u, v = self.calibrator.project_to_pixel(shadow_position)
            
            h, w = image.shape[:2]
            if u < 0 or u >= w or v < 0 or v >= h:
                continue
            
            scene_depth = self._get_depth_at_3d_point(shadow_position, depth_map)
            
            if scene_depth <= 0:
                continue
            
            if abs(shadow_position[2] - scene_depth) > self.config.occlusion_threshold:
                continue
            
            radius = int(obj.scale * 50)
            radius = max(1, min(radius, 100))
            
            shadow_mask = np.zeros(image.shape[:2], dtype=np.float32)
            cv2.circle(shadow_mask, (u, v), radius, 1.0, -1)
            shadow_mask = cv2.GaussianBlur(shadow_mask, (21, 21), 0)
            
            alpha = self.config.shadow_alpha
            shadow_factor = 1.0 - alpha * shadow_mask[..., np.newaxis]
            output = (output.astype(np.float32) * shadow_factor).astype(np.uint8)
            output = np.clip(output, 0, 255).astype(np.uint8)
        
        return output
    
    def get_placement_depth_at_pixel(self,
                                      depth_map: np.ndarray,
                                      pixel_x: int,
                                      pixel_y: int) -> Optional[float]:
        search_radius = 10
        h, w = depth_map.shape
        
        depths = []
        
        for r in range(search_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    px = pixel_x + dx
                    py = pixel_y + dy
                    
                    if 0 <= px < w and 0 <= py < h:
                        depth = depth_map[py, px]
                        if depth > 0 and np.isfinite(depth):
                            depths.append(depth)
            
            if depths:
                return float(np.median(depths))
        
        return None
