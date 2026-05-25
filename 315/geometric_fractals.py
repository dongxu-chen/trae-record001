import numpy as np
from numba import jit, prange
from typing import Tuple, List


def koch_snowflake(order: int, scale: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成科赫雪花曲线
    
    Args:
        order: 递归阶数
        scale: 缩放大小
        
    Returns:
        (x坐标数组, y坐标数组)
    """
    def _koch_curve(order: int):
        if order == 0:
            angles = np.array([0, 120, 240]) + 90
            return scale * np.exp(np.deg2rad(angles) * 1j)
        else:
            ZR = 0.5 - 0.5j * np.sqrt(3) / 3
            p1 = _koch_curve(order - 1)
            p2 = np.empty_like(p1)
            p2[:-1] = p1[1:]
            p2[-1] = p1[0]
            dp = p2 - p1
            new_points = np.empty(len(p1) * 4, dtype=np.complex128)
            new_points[::4] = p1
            new_points[1::4] = p1 + dp / 3
            new_points[2::4] = p1 + dp * ZR
            new_points[3::4] = p1 + dp / 3 * 2
            return new_points
    
    points = _koch_curve(order)
    x, y = points.real, points.imag
    return x, y


def koch_curve(order: int, scale: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成科赫曲线（单条）
    
    Args:
        order: 递归阶数
        scale: 缩放大小
        
    Returns:
        (x坐标数组, y坐标数组)
    """
    def _koch_segment(order: int, start: complex, end: complex):
        if order == 0:
            return np.array([start, end])
        else:
            ZR = 0.5 - 0.5j * np.sqrt(3) / 3
            dp = end - start
            p1 = start
            p2 = start + dp / 3
            p3 = start + dp * ZR
            p4 = start + dp / 3 * 2
            p5 = end
            return np.concatenate([
                _koch_segment(order - 1, p1, p2),
                _koch_segment(order - 1, p2, p3)[1:],
                _koch_segment(order - 1, p3, p4)[1:],
                _koch_segment(order - 1, p4, p5)[1:]
            ])
    
    start = complex(-scale / 2, 0)
    end = complex(scale / 2, 0)
    points = _koch_segment(order, start, end)
    return points.real, points.imag


@jit(nopython=True, parallel=True)
def sierpinski_carpet(order: int, size: int = 729) -> np.ndarray:
    """
    生成谢尔宾斯基地毯
    
    Args:
        order: 递归阶数
        size: 图像尺寸（必须是3的幂）
        
    Returns:
        二维数组，1表示填充，0表示空洞
    """
    carpet = np.ones((size, size), dtype=np.uint8)
    current_size = size
    for _ in range(order):
        current_size = current_size // 3
        for j in prange(size):
            for i in range(size):
                if (i // current_size) % 3 == 1 and (j // current_size) % 3 == 1:
                    carpet[j, i] = 0
    return carpet


def sierpinski_triangle(order: int, scale: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成谢尔宾斯基三角形（使用混沌游戏方法）
    
    Args:
        order: 迭代次数（点数为2^order）
        scale: 缩放大小
        
    Returns:
        (x坐标数组, y坐标数组)
    """
    n_points = 2 ** order
    
    vertices = np.array([
        [0, scale * np.sqrt(3) / 2],
        [-scale / 2, 0],
        [scale / 2, 0]
    ])
    
    points = np.zeros((n_points, 2))
    current_point = np.array([0, 0])
    
    for i in range(n_points):
        vertex_idx = np.random.randint(0, 3)
        current_point = (current_point + vertices[vertex_idx]) / 2
        points[i] = current_point
    
    return points[:, 0], points[:, 1]


def sierpinski_triangle_recursive(order: int, scale: float = 10.0) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    递归生成谢尔宾斯基三角形（返回多个三角形多边形）
    
    Args:
        order: 递归阶数
        scale: 缩放大小
        
    Returns:
        三角形列表，每个三角形是(x坐标数组, y坐标数组)
    """
    triangles = []
    
    height = scale * np.sqrt(3) / 2
    
    def _recurse(depth: int, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float):
        if depth == 0:
            x = np.array([x1, x2, x3, x1])
            y = np.array([y1, y2, y3, y1])
            triangles.append((x, y))
        else:
            mx1, my1 = (x1 + x2) / 2, (y1 + y2) / 2
            mx2, my2 = (x2 + x3) / 2, (y2 + y3) / 2
            mx3, my3 = (x3 + x1) / 2, (y3 + y1) / 2
            
            _recurse(depth - 1, x1, y1, mx1, my1, mx3, my3)
            _recurse(depth - 1, mx1, my1, x2, y2, mx2, my2)
            _recurse(depth - 1, mx3, my3, mx2, my2, x3, y3)
    
    _recurse(order, 0, height, -scale / 2, 0, scale / 2, 0)
    return triangles


def dragon_curve(order: int, scale: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成龙形曲线（Heighway dragon）
    
    Args:
        order: 递归阶数（点数为2^order + 1）
        scale: 缩放大小
        
    Returns:
        (x坐标数组, y坐标数组)
    """
    def _dragon(order: int, direction: int = 1):
        if order == 0:
            return np.array([0, 1], dtype=np.complex128)
        else:
            prev = _dragon(order - 1, 1)
            rotated = (prev[-1] - (prev - prev[-1]) * 1j * direction)[::-1]
            return np.concatenate([prev[:-1], rotated])
    
    points = _dragon(order)
    seg_len = scale / (2 ** (order / 2))
    points = points * seg_len
    
    center = (points.real.min() + points.real.max()) / 2 + 1j * (points.imag.min() + points.imag.max()) / 2
    points = points - center
    
    return points.real, points.imag


def hilbert_curve(order: int, scale: float = 10.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成希尔伯特曲线
    
    Args:
        order: 曲线阶数（点数为4^order）
        scale: 缩放大小
        
    Returns:
        (x坐标数组, y坐标数组)
    """
    def _hilbert(order: int):
        if order == 0:
            return np.array([0.5 + 0.5j])
        
        prev = _hilbert(order - 1) / 2
        
        q1 = prev * 1j + 0.5
        q2 = prev + 0.5
        q3 = prev + 0.5 + 0.5j
        q4 = prev * (-1j) + 1 + 0.5j
        
        return np.concatenate([q1, q2, q3, q4])
    
    points = _hilbert(order)
    points = points * scale - scale / 2
    
    return points.real, points.imag
