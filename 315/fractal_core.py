import numpy as np
from numba import jit, prange
import math


@jit(nopython=True, fastmath=True)
def mandelbrot_pixel(cx: float, cy: float, max_iter: int, escape_radius: float = 2.0) -> float:
    """计算单个Mandelbrot像素的迭代次数"""
    x, y = 0.0, 0.0
    x2, y2 = 0.0, 0.0
    iteration = 0
    
    while x2 + y2 <= escape_radius * escape_radius and iteration < max_iter:
        y = 2 * x * y + cy
        x = x2 - y2 + cx
        x2 = x * x
        y2 = y * y
        iteration += 1
    
    if iteration < max_iter:
        log_zn = math.log(x2 + y2) / 2.0
        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        iteration = iteration + 1 - nu
    
    return iteration


@jit(nopython=True, fastmath=True, parallel=True)
def mandelbrot_set(xmin: float, xmax: float, ymin: float, ymax: float,
                   width: int, height: int, max_iter: int) -> np.ndarray:
    """生成Mandelbrot集（并行加速）"""
    result = np.zeros((height, width), dtype=np.float64)
    dx = (xmax - xmin) / width
    dy = (ymax - ymin) / height
    
    for j in prange(height):
        cy = ymin + j * dy
        for i in range(width):
            cx = xmin + i * dx
            result[j, i] = mandelbrot_pixel(cx, cy, max_iter)
    
    return result


@jit(nopython=True, fastmath=True)
def julia_pixel(zx: float, zy: float, cx: float, cy: float,
                max_iter: int, escape_radius: float = 2.0) -> float:
    """计算单个Julia像素的迭代次数"""
    x2 = zx * zx
    y2 = zy * zy
    iteration = 0
    
    while x2 + y2 <= escape_radius * escape_radius and iteration < max_iter:
        zy = 2 * zx * zy + cy
        zx = x2 - y2 + cx
        x2 = zx * zx
        y2 = zy * zy
        iteration += 1
    
    if iteration < max_iter:
        log_zn = math.log(x2 + y2) / 2.0
        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        iteration = iteration + 1 - nu
    
    return iteration


@jit(nopython=True, fastmath=True, parallel=True)
def julia_set(xmin: float, xmax: float, ymin: float, ymax: float,
              width: int, height: int, cx: float, cy: float,
              max_iter: int) -> np.ndarray:
    """生成Julia集（并行加速）"""
    result = np.zeros((height, width), dtype=np.float64)
    dx = (xmax - xmin) / width
    dy = (ymax - ymin) / height
    
    for j in prange(height):
        zy = ymin + j * dy
        for i in range(width):
            zx = xmin + i * dx
            result[j, i] = julia_pixel(zx, zy, cx, cy, max_iter)
    
    return result


@jit(nopython=True, fastmath=True)
def burning_ship_pixel(cx: float, cy: float, max_iter: int, escape_radius: float = 2.0) -> float:
    """计算Burning Ship分形的单个像素"""
    x, y = 0.0, 0.0
    x2, y2 = 0.0, 0.0
    iteration = 0
    
    while x2 + y2 <= escape_radius * escape_radius and iteration < max_iter:
        y = abs(2 * x * y) + cy
        x = x2 - y2 + cx
        x2 = x * x
        y2 = y * y
        iteration += 1
    
    if iteration < max_iter:
        log_zn = math.log(x2 + y2) / 2.0
        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        iteration = iteration + 1 - nu
    
    return iteration


@jit(nopython=True, fastmath=True, parallel=True)
def burning_ship_set(xmin: float, xmax: float, ymin: float, ymax: float,
                     width: int, height: int, max_iter: int) -> np.ndarray:
    """生成Burning Ship分形"""
    result = np.zeros((height, width), dtype=np.float64)
    dx = (xmax - xmin) / width
    dy = (ymax - ymin) / height
    
    for j in prange(height):
        cy = ymin + j * dy
        for i in range(width):
            cx = xmin + i * dx
            result[j, i] = burning_ship_pixel(cx, cy, max_iter)
    
    return result
