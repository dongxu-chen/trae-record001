import numpy as np
from numba import jit, prange
import math
from typing import Tuple, Optional
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


@jit(nopython=True, fastmath=True)
def mandelbulb_distance(x: float, y: float, z: float, power: int = 8,
                        max_iter: int = 20, bailout: float = 2.0) -> float:
    """
    计算Mandelbulb距离估计（距离估计法）
    
    Args:
        x, y, z: 3D空间坐标
        power: Mandelbulb幂次
        max_iter: 最大迭代次数
        bailout: 逃逸半径
        
    Returns:
        距离估计值
    """
    zx, zy, zz = x, y, z
    dr = 1.0
    r = 0.0
    
    for i in range(max_iter):
        r = math.sqrt(zx * zx + zy * zy + zz * zz)
        if r > bailout:
            break
        
        if r > 1e-12:
            theta = math.acos(max(-1.0, min(1.0, zz / r)))
        else:
            theta = 0.0
        phi = math.atan2(zy, zx)
        
        dr = (r ** (power - 1)) * power * dr + 1.0
        
        zr = r ** power
        theta *= power
        phi *= power
        
        sin_theta = math.sin(theta)
        zx = zr * sin_theta * math.cos(phi) + x
        zy = zr * sin_theta * math.sin(phi) + y
        zz = zr * math.cos(theta) + z
    
    if r > bailout and dr > 1e-12:
        return 0.5 * math.log(r) * r / dr
    return 0.0


@jit(nopython=True, fastmath=True, parallel=True)
def mandelbulb_slice(z_plane: float, xmin: float, xmax: float,
                     ymin: float, ymax: float, resolution: int,
                     power: int = 8, max_iter: int = 20) -> np.ndarray:
    """
    生成Mandelbulb的2D切片
    
    Args:
        z_plane: Z轴切片位置
        xmin, xmax: X轴范围
        ymin, ymax: Y轴范围
        resolution: 分辨率
        power: Mandelbulb幂次
        max_iter: 最大迭代次数
        
    Returns:
        2D距离数组
    """
    result = np.zeros((resolution, resolution), dtype=np.float64)
    dx = (xmax - xmin) / resolution
    dy = (ymax - ymin) / resolution
    
    for j in prange(resolution):
        y = ymin + j * dy
        for i in range(resolution):
            x = xmin + i * dx
            result[j, i] = mandelbulb_distance(x, y, z_plane, power, max_iter)
    
    return result


@jit(nopython=True, fastmath=True)
def ray_march(origin: np.ndarray, direction: np.ndarray,
              power: int = 8, max_iter: int = 20,
              max_steps: int = 200, max_dist: float = 10.0,
              epsilon: float = 1e-3) -> Tuple[float, int, np.ndarray]:
    """
    光线步进渲染Mandelbulb
    
    Args:
        origin: 光线起点
        direction: 光线方向（已归一化）
        power: Mandelbulb幂次
        max_iter: 分形迭代次数
        max_steps: 光线步进最大步数
        max_dist: 最大跟踪距离
        epsilon: 距离阈值
        
    Returns:
        (距离, 步数, 击中位置)
    """
    t = 0.0
    pos = origin.copy()
    
    for step in range(max_steps):
        dist = mandelbulb_distance(pos[0], pos[1], pos[2], power, max_iter)
        
        if dist < epsilon:
            return t, step, pos
        
        t += dist
        pos = origin + direction * t
        
        if t > max_dist:
            break
    
    return max_dist, max_steps, pos


@jit(nopython=True, fastmath=True, parallel=True)
def render_mandelbulb(width: int, height: int,
                      camera_pos: np.ndarray, camera_target: np.ndarray,
                      power: int = 8, max_iter: int = 20,
                      fov: float = 60.0) -> np.ndarray:
    """
    渲染Mandelbulb 3D图像（光线步进）
    
    Args:
        width, height: 图像分辨率
        camera_pos: 相机位置
        camera_target: 相机目标点
        power: Mandelbulb幂次
        max_iter: 分形迭代次数
        fov: 视场角（度）
        
    Returns:
        RGBA图像数组
    """
    aspect = width / height
    fov_rad = math.radians(fov)
    tan_fov = math.tan(fov_rad / 2.0)
    
    forward = camera_target - camera_pos
    forward = forward / np.linalg.norm(forward)
    
    right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
    right = right / np.linalg.norm(right)
    
    up = np.cross(right, forward)
    
    result = np.zeros((height, width, 4), dtype=np.float64)
    
    for j in prange(height):
        for i in range(width):
            px = (2.0 * (i + 0.5) / width - 1.0) * tan_fov * aspect
            py = (1.0 - 2.0 * (j + 0.5) / height) * tan_fov
            
            direction = forward + right * px + up * py
            direction = direction / np.linalg.norm(direction)
            
            dist, steps, hit_pos = ray_march(
                camera_pos, direction, power, max_iter
            )
            
            if dist < 10.0:
                normal = estimate_normal(hit_pos, power, max_iter)
                light_dir = np.array([0.5, 0.8, 0.3])
                light_dir = light_dir / np.linalg.norm(light_dir)
                
                diffuse = max(0.0, np.dot(normal, light_dir))
                ambient = 0.15
                
                intensity = ambient + diffuse * 0.85
                intensity = min(1.0, intensity)
                
                base_color = np.array([0.2, 0.5, 1.0])
                color = base_color * intensity
                
                fog = max(0.0, 1.0 - dist / 8.0)
                color = color * fog + np.array([0.1, 0.1, 0.15]) * (1 - fog)
                
                result[j, i, 0] = min(1.0, color[0])
                result[j, i, 1] = min(1.0, color[1])
                result[j, i, 2] = min(1.0, color[2])
                result[j, i, 3] = 1.0
            else:
                result[j, i, 0] = 0.05
                result[j, i, 1] = 0.05
                result[j, i, 2] = 0.1
                result[j, i, 3] = 1.0
    
    return result


@jit(nopython=True, fastmath=True)
def estimate_normal(pos: np.ndarray, power: int = 8,
                    max_iter: int = 20, epsilon: float = 1e-4) -> np.ndarray:
    """
    估计Mandelbulb表面法向量
    
    Args:
        pos: 表面点位置
        power: Mandelbulb幂次
        max_iter: 迭代次数
        epsilon: 微扰值
        
    Returns:
        法向量（已归一化）
    """
    dx = mandelbulb_distance(pos[0] + epsilon, pos[1], pos[2], power, max_iter) - \
         mandelbulb_distance(pos[0] - epsilon, pos[1], pos[2], power, max_iter)
    dy = mandelbulb_distance(pos[0], pos[1] + epsilon, pos[2], power, max_iter) - \
         mandelbulb_distance(pos[0], pos[1] - epsilon, pos[2], power, max_iter)
    dz = mandelbulb_distance(pos[0], pos[1], pos[2] + epsilon, power, max_iter) - \
         mandelbulb_distance(pos[0], pos[1], pos[2] - epsilon, power, max_iter)
    
    normal = np.array([dx, dy, dz])
    norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    if norm > 0:
        normal = normal / norm
    return normal


def generate_3d_points(power: int = 8, max_iter: int = 15,
                       num_points: int = 50000,
                       bounds: Tuple[float, float] = (-1.5, 1.5)) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成Mandelbulb点云（用于快速可视化）
    
    Args:
        power: Mandelbulb幂次
        max_iter: 迭代次数
        num_points: 点数量
        bounds: 坐标范围
        
    Returns:
        (点坐标数组, 迭代次数数组)
    """
    points = []
    iterations = []
    
    while len(points) < num_points:
        x = np.random.uniform(bounds[0], bounds[1])
        y = np.random.uniform(bounds[0], bounds[1])
        z = np.random.uniform(bounds[0], bounds[1])
        
        dist = mandelbulb_distance(x, y, z, power, max_iter)
        
        if dist < 0.01:
            points.append([x, y, z])
            iterations.append(max_iter)
    
    return np.array(points), np.array(iterations)


def create_rotation_matrix(angle_x: float, angle_y: float, angle_z: float = 0.0) -> np.ndarray:
    """
    创建3D旋转矩阵
    
    Args:
        angle_x: X轴旋转角（弧度）
        angle_y: Y轴旋转角（弧度）
        angle_z: Z轴旋转角（弧度）
        
    Returns:
        3x3旋转矩阵
    """
    cx, sx = math.cos(angle_x), math.sin(angle_x)
    cy, sy = math.cos(angle_y), math.sin(angle_y)
    cz, sz = math.cos(angle_z), math.sin(angle_z)
    
    Rx = np.array([[1, 0, 0],
                    [0, cx, -sx],
                    [0, sx, cx]])
    
    Ry = np.array([[cy, 0, sy],
                    [0, 1, 0],
                    [-sy, 0, cy]])
    
    Rz = np.array([[cz, -sz, 0],
                    [sz, cz, 0],
                    [0, 0, 1]])
    
    return Rz @ Ry @ Rx


class MandelbulbRenderer:
    """Mandelbulb 3D渲染器"""
    
    def __init__(self, width: int = 400, height: int = 300):
        self.width = width
        self.height = height
        self.power = 8
        self.max_iter = 15
        self.fov = 60.0
        
        self.camera_distance = 3.0
        self.rotation_x = 0.3
        self.rotation_y = 0.5
        
        self._current_image = None
        self._points_cache = None
    
    def get_camera_position(self) -> np.ndarray:
        """根据旋转角度计算相机位置"""
        R = create_rotation_matrix(self.rotation_x, self.rotation_y)
        base_pos = np.array([0, 0, self.camera_distance])
        return R @ base_pos
    
    def get_camera_target(self) -> np.ndarray:
        """获取相机目标点"""
        return np.array([0.0, 0.0, 0.0])
    
    def render(self, use_ray_march: bool = False) -> np.ndarray:
        """
        渲染Mandelbulb
        
        Args:
            use_ray_march: 是否使用光线步进（质量高但慢）
            
        Returns:
            RGBA图像数组
        """
        camera_pos = self.get_camera_position()
        camera_target = self.get_camera_target()
        
        if use_ray_march:
            self._current_image = render_mandelbulb(
                self.width, self.height,
                camera_pos, camera_target,
                self.power, self.max_iter, self.fov
            )
        else:
            self._current_image = self._render_fast()
        
        return self._current_image
    
    def _render_fast(self) -> np.ndarray:
        """快速渲染（使用点云投影）"""
        if self._points_cache is None or self._points_cache[1] != self.power:
            points, _ = generate_3d_points(
                self.power, self.max_iter, num_points=20000
            )
            self._points_cache = (points, self.power)
        else:
            points = self._points_cache[0]
        
        R = create_rotation_matrix(self.rotation_x, self.rotation_y)
        rotated = points @ R.T
        
        x = rotated[:, 0]
        y = rotated[:, 1]
        z = rotated[:, 2]
        
        depth = z + self.camera_distance
        
        img = np.zeros((self.height, self.width, 4))
        img[:, :, 0:3] = 0.05
        img[:, :, 3] = 1.0
        
        fov_rad = math.radians(self.fov)
        scale = self.width / (2 * math.tan(fov_rad / 2.0))
        
        for i in range(len(x)):
            if depth[i] > 0:
                px = int(self.width / 2 + x[i] / depth[i] * scale)
                py = int(self.height / 2 - y[i] / depth[i] * scale)
                
                if 0 <= px < self.width and 0 <= py < self.height:
                    brightness = 1.0 - min(1.0, depth[i] / 4.0)
                    color = np.array([0.2, 0.5, 1.0]) * brightness
                    img[py, px, 0:3] = np.maximum(img[py, px, 0:3], color)
                    img[py, px, 3] = 1.0
        
        return img
    
    def rotate(self, dx: float, dy: float):
        """旋转视角"""
        self.rotation_y += dx * 0.01
        self.rotation_x += dy * 0.01
        self.rotation_x = max(-1.5, min(1.5, self.rotation_x))
    
    def zoom(self, factor: float):
        """缩放"""
        self.camera_distance *= factor
        self.camera_distance = max(1.5, min(8.0, self.camera_distance))
    
    def set_parameters(self, power: int = None, max_iter: int = None,
                       fov: float = None):
        """设置渲染参数"""
        if power is not None:
            self.power = max(2, min(16, power))
            self._points_cache = None
        if max_iter is not None:
            self.max_iter = max(5, min(50, max_iter))
            self._points_cache = None
        if fov is not None:
            self.fov = max(30, min(120, fov))


class MandelboxRenderer:
    """Mandelbox 3D分形渲染器"""
    
    def __init__(self, width: int = 400, height: int = 300):
        self.width = width
        self.height = height
        self.scale = 2.0
        self.min_radius = 0.5
        self.fixed_radius = 1.0
        self.max_iter = 10
        
        self.camera_distance = 4.0
        self.rotation_x = 0.3
        self.rotation_y = 0.5
        self.fov = 60.0
        
        self._current_image = None
    
    @staticmethod
    @jit(nopython=True, fastmath=True)
    def _distance(x: float, y: float, z: float, scale: float,
                  min_r: float, fixed_r: float, max_iter: int) -> float:
        """Mandelbox距离估计"""
        zx, zy, zz = x, y, z
        dr = 1.0
        
        for i in range(max_iter):
            if zx > 1.0: zx = 2.0 - zx
            elif zx < -1.0: zx = -2.0 - zx
            
            if zy > 1.0: zy = 2.0 - zy
            elif zy < -1.0: zy = -2.0 - zy
            
            if zz > 1.0: zz = 2.0 - zz
            elif zz < -1.0: zz = -2.0 - zz
            
            r2 = zx * zx + zy * zy + zz * zz
            if r2 < min_r * min_r:
                factor = fixed_r * fixed_r / (min_r * min_r)
                dr *= factor
                zx *= factor
                zy *= factor
                zz *= factor
            elif r2 < fixed_r * fixed_r:
                factor = fixed_r * fixed_r / r2
                dr *= factor
                zx *= factor
                zy *= factor
                zz *= factor
            
            zx = zx * scale + x
            zy = zy * scale + y
            zz = zz * scale + z
            dr = dr * abs(scale) + 1.0
        
        r = math.sqrt(zx * zx + zy * zy + zz * zz)
        return r / abs(dr)
    
    def get_camera_position(self) -> np.ndarray:
        R = create_rotation_matrix(self.rotation_x, self.rotation_y)
        base_pos = np.array([0, 0, self.camera_distance])
        return R @ base_pos
    
    def render(self) -> np.ndarray:
        """渲染Mandelbox"""
        camera_pos = self.get_camera_position()
        camera_target = np.array([0.0, 0.0, 0.0])
        
        aspect = self.width / self.height
        fov_rad = math.radians(self.fov)
        tan_fov = math.tan(fov_rad / 2.0)
        
        forward = camera_target - camera_pos
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        
        result = np.zeros((self.height, self.width, 4))
        
        for j in range(self.height):
            for i in range(self.width):
                px = (2.0 * (i + 0.5) / self.width - 1.0) * tan_fov * aspect
                py = (1.0 - 2.0 * (j + 0.5) / self.height) * tan_fov
                
                direction = forward + right * px + up * py
                direction = direction / np.linalg.norm(direction)
                
                t = 0.0
                pos = camera_pos.copy()
                hit = False
                
                for step in range(100):
                    dist = self._distance(
                        pos[0], pos[1], pos[2],
                        self.scale, self.min_radius, self.fixed_radius,
                        self.max_iter
                    )
                    
                    if dist < 1e-3:
                        hit = True
                        break
                    
                    t += dist
                    pos = camera_pos + direction * t
                    
                    if t > 10.0:
                        break
                
                if hit:
                    result[j, i] = [0.8, 0.6, 0.2, 1.0]
                else:
                    result[j, i] = [0.05, 0.05, 0.1, 1.0]
        
        self._current_image = result
        return result
    
    def rotate(self, dx: float, dy: float):
        self.rotation_y += dx * 0.01
        self.rotation_x += dy * 0.01
        self.rotation_x = max(-1.5, min(1.5, self.rotation_x))
    
    def zoom(self, factor: float):
        self.camera_distance *= factor
        self.camera_distance = max(2.0, min(15.0, self.camera_distance))
