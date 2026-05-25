import numpy as np
from numba import jit, prange
import math
from decimal import Decimal, getcontext, ROUND_HALF_UP
from typing import Tuple, Optional, List


PRECISION_THRESHOLD = 1e-12


def decimal_log(x: Decimal, base: Decimal = None) -> Decimal:
    """使用Newton-Raphson方法计算Decimal的自然对数"""
    if x <= 0:
        raise ValueError("x must be positive")
    
    if base is not None:
        return decimal_log(x) / decimal_log(base)
    
    if x == 1:
        return Decimal('0')
    
    getcontext().prec += 2
    
    result = Decimal('0')
    term = (x - 1) / (x + 1)
    term_sq = term * term
    
    n = Decimal('1')
    current_term = term
    two = Decimal('2')
    
    for _ in range(getcontext().prec * 2):
        result += current_term / n
        current_term *= term_sq
        n += two
        if abs(current_term) < Decimal('1e-' + str(getcontext().prec)):
            break
    
    result *= two
    getcontext().prec -= 2
    
    return result


def decimal_ln(x: Decimal) -> Decimal:
    """计算Decimal的自然对数（AGM算法）"""
    if x <= 0:
        raise ValueError("x must be positive")
    
    if x == 1:
        return Decimal('0')
    
    extra_prec = 10
    orig_prec = getcontext().prec
    getcontext().prec = orig_prec + extra_prec
    
    ln_10 = Decimal('2.302585092994045684017991454684364207601101488628772976033327900967572609677352480235997205089598298341967784350659338')
    ln2 = Decimal('0.693147180559945309417232121458176568075500134360255254120680009493393621969694715605863326996418687542001481020570685')
    
    if x < Decimal('0.5'):
        getcontext().prec = orig_prec
        return -decimal_ln(1 / x)
    
    exp = 0
    while x >= Decimal('2'):
        x *= Decimal('0.5')
        exp += 1
    while x < Decimal('1'):
        x *= Decimal('2')
        exp -= 1
    
    y = (x - 1) / (x + 1)
    y_sq = y * y
    
    result = Decimal('0')
    term = y
    n = 1
    two = Decimal('2')
    
    for _ in range(orig_prec * 2):
        result += term / Decimal(n)
        term *= y_sq
        n += 2
        if abs(term) < Decimal('1e-' + str(orig_prec + 5)):
            break
    
    result *= two
    result += Decimal(exp) * ln2
    
    getcontext().prec = orig_prec
    
    return result


class HighPrecisionCalculator:
    """高精度分形计算器，支持无限缩放（使用decimal模块）"""
    
    def __init__(self):
        self._use_high_precision = False
        self._current_precision = 53
    
    def _determine_precision(self, xmin: float, xmax: float) -> int:
        """根据缩放级别确定所需精度（十进制位数）"""
        range_size = abs(xmax - xmin)
        if range_size > PRECISION_THRESHOLD:
            return 28
        
        digits_needed = int(math.ceil(-math.log10(range_size / 1e-15)))
        return max(28, digits_needed + 5)
    
    def should_use_high_precision(self, xmin: float, xmax: float) -> bool:
        """判断是否需要使用高精度计算"""
        range_size = abs(xmax - xmin)
        return range_size <= PRECISION_THRESHOLD
    
    def _to_decimal(self, value: float, precision: int) -> Decimal:
        """将float转换为Decimal，设置精度"""
        return Decimal(str(value))
    
    def mandelbrot_high_precision(self, xmin: float, xmax: float, ymin: float,
                                   ymax: float, width: int, height: int,
                                   max_iter: int) -> Optional[np.ndarray]:
        """使用高精度计算Mandelbrot集（decimal模块）"""
        precision = self._determine_precision(xmin, xmax)
        getcontext().prec = precision
        getcontext().rounding = ROUND_HALF_UP
        
        result = np.zeros((height, width), dtype=np.float64)
        
        xmin_d = self._to_decimal(xmin, precision)
        xmax_d = self._to_decimal(xmax, precision)
        ymin_d = self._to_decimal(ymin, precision)
        ymax_d = self._to_decimal(ymax, precision)
        width_d = Decimal(width)
        height_d = Decimal(height)
        
        dx = (xmax_d - xmin_d) / width_d
        dy = (ymax_d - ymin_d) / height_d
        
        escape_radius_sq = Decimal('4.0')
        two = Decimal('2')
        one = Decimal('1')
        
        ln2 = decimal_ln(two)
        
        for j in range(height):
            cy = ymin_d + Decimal(j) * dy
            for i in range(width):
                cx = xmin_d + Decimal(i) * dx
                x = Decimal('0')
                y = Decimal('0')
                x2 = Decimal('0')
                y2 = Decimal('0')
                iteration = 0
                
                while x2 + y2 <= escape_radius_sq and iteration < max_iter:
                    y = two * x * y + cy
                    x = x2 - y2 + cx
                    x2 = x * x
                    y2 = y * y
                    iteration += 1
                
                if iteration < max_iter:
                    try:
                        log_zn = decimal_ln(x2 + y2) / two
                        nu = decimal_ln(log_zn / ln2) / ln2
                        iteration = float(Decimal(iteration) + one - nu)
                    except:
                        pass
                
                result[j, i] = iteration
        
        return result
    
    def julia_high_precision(self, xmin: float, xmax: float, ymin: float,
                              ymax: float, width: int, height: int,
                              cx: float, cy: float, max_iter: int) -> Optional[np.ndarray]:
        """使用高精度计算Julia集（decimal模块）"""
        precision = self._determine_precision(xmin, xmax)
        getcontext().prec = precision
        getcontext().rounding = ROUND_HALF_UP
        
        result = np.zeros((height, width), dtype=np.float64)
        
        xmin_d = self._to_decimal(xmin, precision)
        xmax_d = self._to_decimal(xmax, precision)
        ymin_d = self._to_decimal(ymin, precision)
        ymax_d = self._to_decimal(ymax, precision)
        width_d = Decimal(width)
        height_d = Decimal(height)
        
        cx_d = self._to_decimal(cx, precision)
        cy_d = self._to_decimal(cy, precision)
        
        dx = (xmax_d - xmin_d) / width_d
        dy = (ymax_d - ymin_d) / height_d
        
        escape_radius_sq = Decimal('4.0')
        two = Decimal('2')
        one = Decimal('1')
        
        ln2 = decimal_ln(two)
        
        for j in range(height):
            zy = ymin_d + Decimal(j) * dy
            for i in range(width):
                zx = xmin_d + Decimal(i) * dx
                x2 = zx * zx
                y2 = zy * zy
                iteration = 0
                
                while x2 + y2 <= escape_radius_sq and iteration < max_iter:
                    zy = two * zx * zy + cy_d
                    zx = x2 - y2 + cx_d
                    x2 = zx * zx
                    y2 = zy * zy
                    iteration += 1
                
                if iteration < max_iter:
                    try:
                        log_zn = decimal_ln(x2 + y2) / two
                        nu = decimal_ln(log_zn / ln2) / ln2
                        iteration = float(Decimal(iteration) + one - nu)
                    except:
                        pass
                
                result[j, i] = iteration
        
        return result


@jit(nopython=True, fastmath=True)
def _mandelbrot_pixel_quad(cx: float, cy: float, max_iter: int) -> float:
    """使用周期检测优化的Mandelbrot像素计算"""
    x, y = 0.0, 0.0
    x2, y2 = 0.0, 0.0
    iteration = 0
    
    x_old, y_old = 0.0, 0.0
    period = 0
    period_check = 20
    
    while x2 + y2 <= 4.0 and iteration < max_iter:
        y = 2 * x * y + cy
        x = x2 - y2 + cx
        x2 = x * x
        y2 = y * y
        iteration += 1
        
        if x == x_old and y == y_old:
            return float(max_iter)
        
        period += 1
        if period >= period_check:
            period = 0
            x_old, y_old = x, y
            period_check *= 2
    
    if iteration < max_iter:
        log_zn = math.log(x2 + y2) / 2.0
        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        iteration = iteration + 1 - nu
    
    return iteration


@jit(nopython=True, fastmath=True, parallel=True)
def mandelbrot_set_optimized(xmin: float, xmax: float, ymin: float,
                              ymax: float, width: int, height: int,
                              max_iter: int) -> np.ndarray:
    """优化的Mandelbrot集生成（带周期检测）"""
    result = np.zeros((height, width), dtype=np.float64)
    dx = (xmax - xmin) / width
    dy = (ymax - ymin) / height
    
    for j in prange(height):
        cy = ymin + j * dy
        for i in range(width):
            cx = xmin + i * dx
            result[j, i] = _mandelbrot_pixel_quad(cx, cy, max_iter)
    
    return result


class JuliaGridCache:
    """Julia集网格缓存，预计算网格点实现参数变化快速更新"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self._zx_grid = None
        self._zy_grid = None
        self._xmin = None
        self._xmax = None
        self._ymin = None
        self._ymax = None
        self._cached = False
    
    def precompute_grid(self, xmin: float, xmax: float, ymin: float, ymax: float):
        """预计算网格点坐标"""
        if (self._cached and 
            self._xmin == xmin and self._xmax == xmax and
            self._ymin == ymin and self._ymax == ymax):
            return
        
        dx = (xmax - xmin) / self.width
        dy = (ymax - ymin) / self.height
        
        x_coords = np.linspace(xmin, xmax - dx, self.width, dtype=np.float64)
        y_coords = np.linspace(ymin, ymax - dy, self.height, dtype=np.float64)
        
        self._zx_grid, self._zy_grid = np.meshgrid(x_coords, y_coords)
        
        self._xmin = xmin
        self._xmax = xmax
        self._ymin = ymin
        self._ymax = ymax
        self._cached = True
    
    def invalidate(self):
        """使缓存失效"""
        self._cached = False
        self._zx_grid = None
        self._zy_grid = None
    
    def is_cached(self, xmin: float, xmax: float, ymin: float, ymax: float) -> bool:
        """检查是否已有缓存"""
        return (self._cached and 
                self._xmin == xmin and self._xmax == xmax and
                self._ymin == ymin and self._ymax == ymax)
    
    def get_grids(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取预计算的网格"""
        return self._zx_grid, self._zy_grid


@jit(nopython=True, fastmath=True, parallel=True)
def julia_set_from_grid(zx: np.ndarray, zy: np.ndarray,
                        cx: float, cy: float, max_iter: int) -> np.ndarray:
    """使用预计算网格快速计算Julia集（只更新迭代公式）"""
    height, width = zx.shape
    result = np.zeros((height, width), dtype=np.float64)
    escape_radius_sq = 4.0
    log2 = math.log(2.0)
    
    for j in prange(height):
        for i in range(width):
            zx_val = zx[j, i]
            zy_val = zy[j, i]
            x2 = zx_val * zx_val
            y2 = zy_val * zy_val
            iteration = 0
            
            while x2 + y2 <= escape_radius_sq and iteration < max_iter:
                zy_val = 2 * zx_val * zy_val + cy
                zx_val = x2 - y2 + cx
                x2 = zx_val * zx_val
                y2 = zy_val * zy_val
                iteration += 1
            
            if iteration < max_iter:
                log_zn = math.log(x2 + y2) / 2.0
                nu = math.log(log_zn / log2) / log2
                iteration = iteration + 1 - nu
            
            result[j, i] = iteration
    
    return result


@jit(nopython=True, fastmath=True, parallel=True)
def julia_set_optimized(xmin: float, xmax: float, ymin: float, ymax: float,
                        width: int, height: int, cx: float, cy: float,
                        max_iter: int) -> np.ndarray:
    """优化的Julia集生成（Numba加速）"""
    result = np.zeros((height, width), dtype=np.float64)
    dx = (xmax - xmin) / width
    dy = (ymax - ymin) / height
    escape_radius_sq = 4.0
    log2 = math.log(2.0)
    y_base = ymin
    
    for j in prange(height):
        zy0 = y_base + j * dy
        for i in range(width):
            zx = xmin + i * dx
            zy = zy0
            x2 = zx * zx
            y2 = zy * zy
            iteration = 0
            
            while x2 + y2 <= escape_radius_sq and iteration < max_iter:
                zy = 2 * zx * zy + cy
                zx = x2 - y2 + cx
                x2 = zx * zx
                y2 = zy * zy
                iteration += 1
            
            if iteration < max_iter:
                log_zn = math.log(x2 + y2) / 2.0
                nu = math.log(log_zn / log2) / log2
                iteration = iteration + 1 - nu
            
            result[j, i] = iteration
    
    return result


def compute_view_range(center_x: float, center_y: float, zoom: float,
                       width: int, height: int) -> Tuple[float, float, float, float]:
    """
    根据中心点和缩放级别计算视图范围
    
    Args:
        center_x: 中心点x坐标
        center_y: 中心点y坐标
        zoom: 缩放级别（1.0为默认视图）
        width: 图像宽度（像素）
        height: 图像高度（像素）
        
    Returns:
        (xmin, xmax, ymin, ymax)
    """
    aspect_ratio = width / height
    base_width = 3.0
    base_height = base_width / aspect_ratio
    
    view_width = base_width / zoom
    view_height = base_height / zoom
    
    xmin = center_x - view_width / 2
    xmax = center_x + view_width / 2
    ymin = center_y - view_height / 2
    ymax = center_y + view_height / 2
    
    return xmin, xmax, ymin, ymax


def adaptive_max_iter(zoom: float, base_iter: int = 100) -> int:
    """
    根据缩放级别自适应调整迭代次数
    
    Args:
        zoom: 缩放级别
        base_iter: 基础迭代次数
        
    Returns:
        自适应的迭代次数
    """
    if zoom <= 1:
        return base_iter
    
    iter_increase = int(math.log2(zoom) * 30)
    return min(base_iter + iter_increase, 5000)


def get_mandelbrot_interesting_points() -> list:
    """获取Mandelbrot集中有趣的观察点"""
    return [
        {
            "name": "整体视图",
            "center_x": -0.5,
            "center_y": 0.0,
            "zoom": 1.0
        },
        {
            "name": "海马谷",
            "center_x": -0.743643887037158,
            "center_y": 0.131825904205330,
            "zoom": 1000000.0
        },
        {
            "name": "西瓦螺旋",
            "center_x": -0.748,
            "center_y": 0.1,
            "zoom": 100.0
        },
        {
            "name": "闪电区域",
            "center_x": -0.7453,
            "center_y": 0.1127,
            "zoom": 300.0
        },
        {
            "name": "小Mandelbrot",
            "center_x": -1.748,
            "center_y": 0.0,
            "zoom": 200.0
        },
        {
            "name": "大象谷",
            "center_x": 0.275,
            "center_y": 0.0,
            "zoom": 100.0
        }
    ]


def get_julia_classic_sets() -> list:
    """获取经典的Julia集参数"""
    return [
        {
            "name": "Douady兔子",
            "cx": -0.123,
            "cy": 0.745,
            "center_x": 0.0,
            "center_y": 0.0,
            "zoom": 1.0
        },
        {
            "name": "Siegel圆盘",
            "cx": -0.391,
            "cy": -0.587,
            "center_x": 0.0,
            "center_y": 0.0,
            "zoom": 1.0
        },
        {
            "name": "龙形",
            "cx": -0.70176,
            "cy": -0.3842,
            "center_x": 0.0,
            "center_y": 0.0,
            "zoom": 1.0
        },
        {
            "name": "螺旋",
            "cx": -0.745,
            "cy": 0.113,
            "center_x": 0.0,
            "center_y": 0.0,
            "zoom": 1.0
        },
        {
            "name": "雪花",
            "cx": -0.7,
            "cy": 0.3555,
            "center_x": 0.0,
            "center_y": 0.0,
            "zoom": 1.0
        }
    ]
