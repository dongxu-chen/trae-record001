import numpy as np
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from typing import Dict, Tuple, List, Optional


def create_custom_colormap(name: str, colors: List[Tuple[float, float, float]]) -> ListedColormap:
    """创建自定义颜色映射"""
    return ListedColormap(colors, name=name)


def create_gradient_colormap(name: str, color_points: List[Tuple[float, Tuple[float, float, float]]]) -> LinearSegmentedColormap:
    """创建渐变颜色映射"""
    cdict = {'red': [], 'green': [], 'blue': []}
    for position, color in color_points:
        r, g, b = color
        cdict['red'].append((position, r, r))
        cdict['green'].append((position, g, g))
        cdict['blue'].append((position, b, b))
    return LinearSegmentedColormap(name, cdict)


def create_multistop_gradient(name: str, 
                              stops: List[Tuple[float, Tuple[float, float, float]]],
                              N: int = 256) -> LinearSegmentedColormap:
    """
    创建多段渐变颜色映射
    
    Args:
        name: 颜色映射名称
        stops: 颜色停驻点列表 [(position, (r, g, b)), ...]
               position: 0.0 - 1.0
               color: (r, g, b) 范围 0.0 - 1.0
        N: 颜色映射的颜色数量
    
    Returns:
        LinearSegmentedColormap对象
    """
    stops = sorted(stops, key=lambda x: x[0])
    
    if stops[0][0] > 0.0:
        stops.insert(0, (0.0, stops[0][1]))
    if stops[-1][0] < 1.0:
        stops.append((1.0, stops[-1][1]))
    
    cdict = {'red': [], 'green': [], 'blue': []}
    
    for i in range(len(stops) - 1):
        pos1, color1 = stops[i]
        pos2, color2 = stops[i + 1]
        
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        
        cdict['red'].append((pos1, r1, r1))
        cdict['green'].append((pos1, g1, g1))
        cdict['blue'].append((pos1, b1, b1))
        
        cdict['red'].append((pos2, r1, r2))
        cdict['green'].append((pos2, g1, g2))
        cdict['blue'].append((pos2, b1, b2))
    
    return LinearSegmentedColormap(name, cdict, N=N)


def create_cyclic_gradient(name: str, 
                           cycle_colors: List[Tuple[float, float, float]],
                           num_cycles: int = 3,
                           N: int = 256) -> LinearSegmentedColormap:
    """
    创建循环渐变颜色映射
    
    Args:
        name: 颜色映射名称
        cycle_colors: 循环的颜色列表 [(r, g, b), ...]
        num_cycles: 循环次数
        N: 颜色映射的颜色数量
    
    Returns:
        LinearSegmentedColormap对象
    """
    stops = []
    num_colors = len(cycle_colors)
    total_segments = num_colors * num_cycles
    
    for i in range(total_segments + 1):
        pos = i / total_segments
        color_idx = i % num_colors
        color = cycle_colors[color_idx]
        stops.append((pos, color))
    
    return create_multistop_gradient(name, stops, N=N)


def create_piecewise_gradient(name: str,
                              segments: List[Tuple[Tuple[float, float, float], 
                                                Tuple[float, float, float], 
                                                float, float]],
                              N: int = 256) -> LinearSegmentedColormap:
    """
    创建分段渐变颜色映射
    
    Args:
        name: 颜色映射名称
        segments: 分段列表 [(start_color, end_color, start_pos, end_pos), ...]
                  每个分段定义了从start_pos到end_pos之间从start_color渐变到end_color
        N: 颜色映射的颜色数量
    
    Returns:
        LinearSegmentedColormap对象
    """
    stops = []
    
    for start_color, end_color, start_pos, end_pos in segments:
        stops.append((start_pos, start_color))
        stops.append((end_pos, end_color))
    
    return create_multistop_gradient(name, stops, N=N)


def create_rainbow_gradient(name: str = 'custom_rainbow', N: int = 256) -> LinearSegmentedColormap:
    """创建彩虹渐变"""
    rainbow_stops = [
        (0.0, (1.0, 0.0, 0.0)),
        (0.17, (1.0, 0.5, 0.0)),
        (0.33, (1.0, 1.0, 0.0)),
        (0.5, (0.0, 1.0, 0.0)),
        (0.67, (0.0, 1.0, 1.0)),
        (0.83, (0.0, 0.0, 1.0)),
        (1.0, (1.0, 0.0, 1.0)),
    ]
    return create_multistop_gradient(name, rainbow_stops, N=N)


def create_ocean_gradient(name: str = 'custom_ocean', N: int = 256) -> LinearSegmentedColormap:
    """创建海洋渐变"""
    ocean_stops = [
        (0.0, (0.0, 0.0, 0.1)),
        (0.25, (0.0, 0.2, 0.4)),
        (0.5, (0.0, 0.4, 0.6)),
        (0.75, (0.0, 0.6, 0.8)),
        (1.0, (0.5, 0.9, 1.0)),
    ]
    return create_multistop_gradient(name, ocean_stops, N=N)


def create_fire_gradient(name: str = 'custom_fire', N: int = 256) -> LinearSegmentedColormap:
    """创建火焰渐变"""
    fire_stops = [
        (0.0, (0.0, 0.0, 0.0)),
        (0.3, (0.3, 0.0, 0.0)),
        (0.5, (0.6, 0.2, 0.0)),
        (0.7, (1.0, 0.5, 0.0)),
        (0.85, (1.0, 0.8, 0.0)),
        (1.0, (1.0, 1.0, 0.5)),
    ]
    return create_multistop_gradient(name, fire_stops, N=N)


def create_cyclic_rainbow(name: str = 'cyclic_rainbow', num_cycles: int = 5, N: int = 256) -> LinearSegmentedColormap:
    """创建循环彩虹渐变"""
    colors = [
        (1.0, 0.0, 0.0),
        (1.0, 0.5, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 1.0, 1.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
    ]
    return create_cyclic_gradient(name, colors, num_cycles=num_cycles, N=N)


def create_cyclic_neon(name: str = 'cyclic_neon', num_cycles: int = 4, N: int = 256) -> LinearSegmentedColormap:
    """创建循环霓虹渐变"""
    colors = [
        (0.0, 1.0, 1.0),
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
    ]
    return create_cyclic_gradient(name, colors, num_cycles=num_cycles, N=N)


def create_cyclic_pastel(name: str = 'cyclic_pastel', num_cycles: int = 3, N: int = 256) -> LinearSegmentedColormap:
    """创建循环粉彩渐变"""
    colors = [
        (1.0, 0.7, 0.7),
        (0.7, 1.0, 0.7),
        (0.7, 0.7, 1.0),
        (1.0, 1.0, 0.7),
        (0.7, 1.0, 1.0),
        (1.0, 0.7, 1.0),
    ]
    return create_cyclic_gradient(name, colors, num_cycles=num_cycles, N=N)


def create_cyclic_earth(name: str = 'cyclic_earth', num_cycles: int = 2, N: int = 256) -> LinearSegmentedColormap:
    """创建循环大地色调渐变"""
    colors = [
        (0.2, 0.4, 0.2),
        (0.6, 0.4, 0.2),
        (0.8, 0.6, 0.4),
        (0.4, 0.3, 0.2),
    ]
    return create_cyclic_gradient(name, colors, num_cycles=num_cycles, N=N)


def get_available_colormaps() -> Dict[str, str]:
    """获取所有可用的颜色映射"""
    builtin_cmaps = [
        'viridis', 'plasma', 'inferno', 'magma', 'cividis',
        'hot', 'cool', 'spring', 'summer', 'autumn', 'winter',
        'jet', 'rainbow', 'hsv', 'twilight', 'twilight_shifted',
        'bone', 'copper', 'gist_earth', 'terrain', 'ocean',
        'gist_stern', 'brg', 'CMRmap', 'cubehelix', 'gnuplot',
        'gnuplot2', 'gist_ncar', 'nipy_spectral', 'jet_r',
        'Spectral', 'coolwarm', 'RdYlBu', 'RdBu', 'PiYG',
        'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdYlGn',
        'flag', 'prism', 'Dark2', 'Paired', 'Pastel1',
        'Pastel2', 'Set1', 'Set2', 'Set3', 'Accent'
    ]
    
    custom_cmaps = create_custom_colormaps()
    gradient_cmaps = create_gradient_colormaps()
    cyclic_cmaps = create_cyclic_colormaps()
    
    all_cmaps = {}
    for cmap in builtin_cmaps:
        all_cmaps[cmap] = cmap
    
    for name in custom_cmaps:
        all_cmaps[name] = name
    
    for name in gradient_cmaps:
        all_cmaps[name] = name
    
    for name in cyclic_cmaps:
        all_cmaps[name] = name
    
    return all_cmaps


def create_custom_colormaps() -> Dict[str, ListedColormap]:
    """创建自定义分形专用颜色映射"""
    custom_cmaps = {}
    
    fractal_colors = [
        (0.0, 0.0, 0.0),
        (0.1, 0.1, 0.3),
        (0.2, 0.1, 0.5),
        (0.4, 0.2, 0.6),
        (0.6, 0.3, 0.5),
        (0.8, 0.5, 0.3),
        (1.0, 0.7, 0.1),
        (1.0, 1.0, 0.0),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['fractal_flame'] = create_custom_colormap('fractal_flame', fractal_colors)
    
    ocean_depth = [
        (0.0, 0.0, 0.1),
        (0.0, 0.1, 0.3),
        (0.0, 0.2, 0.5),
        (0.0, 0.4, 0.6),
        (0.0, 0.6, 0.7),
        (0.0, 0.8, 0.8),
        (0.2, 0.9, 0.9),
        (0.5, 1.0, 1.0),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['ocean_depth'] = create_custom_colormap('ocean_depth', ocean_depth)
    
    cosmic = [
        (0.0, 0.0, 0.0),
        (0.1, 0.0, 0.2),
        (0.3, 0.0, 0.4),
        (0.5, 0.1, 0.3),
        (0.7, 0.2, 0.1),
        (0.9, 0.5, 0.0),
        (1.0, 0.8, 0.2),
        (1.0, 1.0, 0.5),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['cosmic'] = create_custom_colormap('cosmic', cosmic)
    
    rainbow_soft = [
        (0.0, 0.0, 0.0),
        (0.2, 0.0, 0.4),
        (0.0, 0.4, 0.6),
        (0.0, 0.6, 0.4),
        (0.4, 0.6, 0.0),
        (0.8, 0.4, 0.0),
        (0.8, 0.0, 0.4),
        (0.4, 0.0, 0.6),
    ]
    custom_cmaps['rainbow_soft'] = create_custom_colormap('rainbow_soft', rainbow_soft)
    
    neon = [
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 1.0),
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['neon'] = create_custom_colormap('neon', neon)
    
    fire = [
        (0.0, 0.0, 0.0),
        (0.1, 0.0, 0.0),
        (0.3, 0.1, 0.0),
        (0.5, 0.2, 0.0),
        (0.7, 0.4, 0.0),
        (0.9, 0.6, 0.0),
        (1.0, 0.8, 0.0),
        (1.0, 1.0, 0.5),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['fire'] = create_custom_colormap('fire', fire)
    
    ice = [
        (0.0, 0.0, 0.1),
        (0.0, 0.1, 0.3),
        (0.0, 0.3, 0.5),
        (0.0, 0.5, 0.7),
        (0.2, 0.7, 0.9),
        (0.5, 0.8, 1.0),
        (0.8, 0.9, 1.0),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['ice'] = create_custom_colormap('ice', ice)
    
    forest = [
        (0.0, 0.0, 0.0),
        (0.0, 0.2, 0.1),
        (0.0, 0.4, 0.2),
        (0.0, 0.6, 0.3),
        (0.2, 0.7, 0.3),
        (0.4, 0.8, 0.4),
        (0.6, 0.9, 0.5),
        (0.8, 1.0, 0.6),
        (1.0, 1.0, 1.0),
    ]
    custom_cmaps['forest'] = create_custom_colormap('forest', forest)
    
    sunset = [
        (0.0, 0.0, 0.2),
        (0.2, 0.1, 0.4),
        (0.4, 0.2, 0.5),
        (0.6, 0.3, 0.4),
        (0.8, 0.5, 0.3),
        (0.9, 0.7, 0.2),
        (1.0, 0.9, 0.3),
        (1.0, 1.0, 0.5),
    ]
    custom_cmaps['sunset'] = create_custom_colormap('sunset', sunset)
    
    grayscale_reverse = [
        (1.0, 1.0, 1.0),
        (0.8, 0.8, 0.8),
        (0.6, 0.6, 0.6),
        (0.4, 0.4, 0.4),
        (0.2, 0.2, 0.2),
        (0.0, 0.0, 0.0),
    ]
    custom_cmaps['grayscale_rev'] = create_custom_colormap('grayscale_rev', grayscale_reverse)
    
    return custom_cmaps


def create_gradient_colormaps() -> Dict[str, LinearSegmentedColormap]:
    """创建多段渐变颜色映射"""
    gradient_cmaps = {}
    
    gradient_cmaps['gradient_rainbow'] = create_rainbow_gradient('gradient_rainbow')
    gradient_cmaps['gradient_ocean'] = create_ocean_gradient('gradient_ocean')
    gradient_cmaps['gradient_fire'] = create_fire_gradient('gradient_fire')
    
    aurora_stops = [
        (0.0, (0.0, 0.0, 0.1)),
        (0.2, (0.0, 0.2, 0.3)),
        (0.4, (0.0, 0.5, 0.4)),
        (0.6, (0.2, 0.7, 0.3)),
        (0.8, (0.5, 0.8, 0.2)),
        (1.0, (0.8, 0.9, 0.4)),
    ]
    gradient_cmaps['gradient_aurora'] = create_multistop_gradient('gradient_aurora', aurora_stops)
    
    galaxy_stops = [
        (0.0, (0.0, 0.0, 0.0)),
        (0.15, (0.1, 0.0, 0.2)),
        (0.3, (0.3, 0.0, 0.4)),
        (0.5, (0.5, 0.1, 0.3)),
        (0.7, (0.6, 0.3, 0.1)),
        (0.85, (0.8, 0.5, 0.0)),
        (1.0, (1.0, 0.8, 0.3)),
    ]
    gradient_cmaps['gradient_galaxy'] = create_multistop_gradient('gradient_galaxy', galaxy_stops)
    
    poison_stops = [
        (0.0, (0.0, 0.1, 0.0)),
        (0.25, (0.2, 0.4, 0.0)),
        (0.5, (0.5, 0.7, 0.0)),
        (0.75, (0.8, 0.9, 0.2)),
        (1.0, (1.0, 1.0, 0.5)),
    ]
    gradient_cmaps['gradient_poison'] = create_multistop_gradient('gradient_poison', poison_stops)
    
    candy_stops = [
        (0.0, (1.0, 0.4, 0.6)),
        (0.25, (1.0, 0.6, 0.8)),
        (0.5, (0.8, 0.8, 1.0)),
        (0.75, (0.6, 0.8, 1.0)),
        (1.0, (0.4, 0.6, 1.0)),
    ]
    gradient_cmaps['gradient_candy'] = create_multistop_gradient('gradient_candy', candy_stops)
    
    metal_stops = [
        (0.0, (0.1, 0.1, 0.1)),
        (0.2, (0.3, 0.3, 0.35)),
        (0.4, (0.5, 0.5, 0.55)),
        (0.5, (0.8, 0.8, 0.9)),
        (0.6, (0.5, 0.5, 0.55)),
        (0.8, (0.3, 0.3, 0.35)),
        (1.0, (0.1, 0.1, 0.1)),
    ]
    gradient_cmaps['gradient_metal'] = create_multistop_gradient('gradient_metal', metal_stops)
    
    return gradient_cmaps


def create_cyclic_colormaps() -> Dict[str, LinearSegmentedColormap]:
    """创建循环渐变颜色映射"""
    cyclic_cmaps = {}
    
    cyclic_cmaps['cyclic_rainbow_3'] = create_cyclic_rainbow('cyclic_rainbow_3', num_cycles=3)
    cyclic_cmaps['cyclic_rainbow_5'] = create_cyclic_rainbow('cyclic_rainbow_5', num_cycles=5)
    cyclic_cmaps['cyclic_rainbow_10'] = create_cyclic_rainbow('cyclic_rainbow_10', num_cycles=10)
    
    cyclic_cmaps['cyclic_neon_3'] = create_cyclic_neon('cyclic_neon_3', num_cycles=3)
    cyclic_cmaps['cyclic_neon_5'] = create_cyclic_neon('cyclic_neon_5', num_cycles=5)
    cyclic_cmaps['cyclic_neon_8'] = create_cyclic_neon('cyclic_neon_8', num_cycles=8)
    
    cyclic_cmaps['cyclic_pastel_2'] = create_cyclic_pastel('cyclic_pastel_2', num_cycles=2)
    cyclic_cmaps['cyclic_pastel_4'] = create_cyclic_pastel('cyclic_pastel_4', num_cycles=4)
    
    cyclic_cmaps['cyclic_earth_2'] = create_cyclic_earth('cyclic_earth_2', num_cycles=2)
    cyclic_cmaps['cyclic_earth_4'] = create_cyclic_earth('cyclic_earth_4', num_cycles=4)
    
    warm_colors = [
        (1.0, 0.2, 0.0),
        (1.0, 0.5, 0.0),
        (1.0, 0.8, 0.0),
        (1.0, 0.5, 0.0),
    ]
    cyclic_cmaps['cyclic_warm_5'] = create_cyclic_gradient('cyclic_warm_5', warm_colors, num_cycles=5)
    
    cool_colors = [
        (0.0, 0.5, 1.0),
        (0.0, 0.8, 1.0),
        (0.5, 0.8, 1.0),
        (0.0, 0.8, 1.0),
    ]
    cyclic_cmaps['cyclic_cool_5'] = create_cyclic_gradient('cyclic_cool_5', cool_colors, num_cycles=5)
    
    rgb_colors = [
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    ]
    cyclic_cmaps['cyclic_rgb_10'] = create_cyclic_gradient('cyclic_rgb_10', rgb_colors, num_cycles=10)
    
    return cyclic_cmaps


_gradient_cache = None
_cyclic_cache = None


def get_colormap(name: str) -> object:
    """获取颜色映射"""
    global _gradient_cache, _cyclic_cache
    
    custom_cmaps = create_custom_colormaps()
    
    if _gradient_cache is None:
        _gradient_cache = create_gradient_colormaps()
    
    if _cyclic_cache is None:
        _cyclic_cache = create_cyclic_colormaps()
    
    if name in custom_cmaps:
        return custom_cmaps[name]
    
    if name in _gradient_cache:
        return _gradient_cache[name]
    
    if name in _cyclic_cache:
        return _cyclic_cache[name]
    
    try:
        return cm.get_cmap(name)
    except:
        return cm.get_cmap('viridis')


def apply_fractal_colors(data: np.ndarray, cmap_name: str = 'inferno',
                         gamma: float = 1.0, invert: bool = False,
                         log_scale: bool = False,
                         color_mode: str = 'colormap',
                         max_iter: Optional[int] = None) -> np.ndarray:
    """
    将分形数据应用颜色映射
    
    Args:
        data: 分形迭代数据
        cmap_name: 颜色映射名称
        gamma: Gamma校正值
        invert: 是否反转颜色
        log_scale: 是否使用对数缩放
        color_mode: 颜色模式 ('colormap', 'hsv', 'psychedelic')
        max_iter: 最大迭代次数（用于HSV模式）
        
    Returns:
        RGBA颜色数组
    """
    if color_mode == 'hsv':
        if max_iter is None:
            max_iter = int(data.max())
        rgb = create_hsv_colormap(data, max_iter)
        alpha = np.ones((*data.shape, 1))
        return np.concatenate([rgb, alpha], axis=-1)
    
    elif color_mode == 'psychedelic':
        if max_iter is None:
            max_iter = int(data.max())
        rgb = create_psychedelic_colormap(data, max_iter)
        alpha = np.ones((*data.shape, 1))
        return np.concatenate([rgb, alpha], axis=-1)
    
    cmap = get_colormap(cmap_name)
    
    normalized = data.astype(np.float64)
    
    if log_scale:
        normalized = np.log1p(normalized)
    
    max_val = normalized.max()
    min_val = normalized.min()
    
    if max_val > min_val:
        normalized = (normalized - min_val) / (max_val - min_val)
    else:
        normalized = np.zeros_like(normalized)
    
    if gamma != 1.0:
        normalized = np.power(normalized, gamma)
    
    if invert:
        normalized = 1.0 - normalized
    
    rgba = cmap(normalized)
    
    return rgba


def create_hsv_colormap(iterations: np.ndarray, max_iter: int,
                        saturation: float = 0.8, value: float = 1.0,
                        hue_offset: float = 0.0, hue_cycles: float = 1.0) -> np.ndarray:
    """
    创建HSV颜色映射（经典分形着色）
    
    Args:
        iterations: 迭代次数数组
        max_iter: 最大迭代次数
        saturation: 饱和度
        value: 明度
        hue_offset: 色相偏移 (0.0 - 1.0)
        hue_cycles: 色相循环次数
        
    Returns:
        RGB颜色数组
    """
    normalized = iterations / max_iter
    
    h = (normalized * hue_cycles + hue_offset) % 1.0
    s = np.full_like(normalized, saturation)
    v = np.where(iterations < max_iter, value, 0.0)
    
    rgb = hsv_to_rgb(h, s, v)
    return rgb


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """将HSV转换为RGB"""
    shape = h.shape
    h = h.ravel()
    s = s.ravel()
    v = v.ravel()
    
    i = (h * 6).astype(int)
    f = (h * 6) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    
    i = i % 6
    
    rgb = np.zeros((len(h), 3))
    
    mask = i == 0
    rgb[mask] = np.column_stack([v[mask], t[mask], p[mask]])
    
    mask = i == 1
    rgb[mask] = np.column_stack([q[mask], v[mask], p[mask]])
    
    mask = i == 2
    rgb[mask] = np.column_stack([p[mask], v[mask], t[mask]])
    
    mask = i == 3
    rgb[mask] = np.column_stack([p[mask], q[mask], v[mask]])
    
    mask = i == 4
    rgb[mask] = np.column_stack([t[mask], p[mask], v[mask]])
    
    mask = i == 5
    rgb[mask] = np.column_stack([v[mask], p[mask], q[mask]])
    
    return rgb.reshape((*shape, 3))


def create_psychedelic_colormap(iterations: np.ndarray, max_iter: int,
                                freq_r: float = 3.0, freq_g: float = 5.0, freq_b: float = 7.0,
                                phase_r: float = 0.0, phase_g: float = 2.0, phase_b: float = 4.0) -> np.ndarray:
    """
    创建迷幻风格的颜色映射
    
    Args:
        iterations: 迭代次数数组
        max_iter: 最大迭代次数
        freq_r/g/b: RGB通道的频率
        phase_r/g/b: RGB通道的相位偏移
        
    Returns:
        RGB颜色数组
    """
    normalized = iterations / max_iter
    two_pi = 2 * np.pi
    
    r = np.sin(normalized * two_pi * freq_r + phase_r) * 0.5 + 0.5
    g = np.sin(normalized * two_pi * freq_g + phase_g) * 0.5 + 0.5
    b = np.sin(normalized * two_pi * freq_b + phase_b) * 0.5 + 0.5
    
    rgb = np.stack([r, g, b], axis=-1)
    
    rgb[iterations >= max_iter] = 0
    
    return rgb


def create_hue_cycling_colormap(iterations: np.ndarray, max_iter: int,
                                num_cycles: int = 5, saturation: float = 0.9,
                                value: float = 1.0) -> np.ndarray:
    """
    创建色相循环着色（专门为分形边界设计的循环渐变）
    
    Args:
        iterations: 迭代次数数组
        max_iter: 最大迭代次数
        num_cycles: 循环次数
        saturation: 饱和度
        value: 明度
        
    Returns:
        RGB颜色数组
    """
    normalized = iterations / max_iter
    
    h = (normalized * num_cycles) % 1.0
    s = np.full_like(normalized, saturation)
    v = np.where(iterations < max_iter, value, 0.0)
    
    v = v * (1 - np.exp(-normalized * 3))
    
    rgb = hsv_to_rgb(h, s, v)
    return rgb
