import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import RectangleSelector
import matplotlib.pyplot as plt
from typing import Callable, Optional, Tuple, List
import math

from fractal_core import mandelbrot_set, julia_set, burning_ship_set
from geometric_fractals import (
    koch_snowflake, koch_curve, sierpinski_carpet,
    sierpinski_triangle, sierpinski_triangle_recursive,
    dragon_curve, hilbert_curve
)
from high_precision import (
    HighPrecisionCalculator, compute_view_range,
    adaptive_max_iter, mandelbrot_set_optimized,
    JuliaGridCache, julia_set_from_grid, julia_set_optimized
)
from color_maps import (
    apply_fractal_colors, create_hsv_colormap,
    create_psychedelic_colormap, create_hue_cycling_colormap
)
from fractal_3d import MandelbulbRenderer, MandelboxRenderer
from formula_editor import CustomFractalGenerator


class FractalPlotter:
    """分形绘图器，封装Matplotlib绘图和交互功能"""
    
    def __init__(self, parent=None, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.parent = parent
        
        self.fractal_type = 'mandelbrot'
        self.max_iter = 100
        self.zoom = 1.0
        self.center_x = -0.5
        self.center_y = 0.0
        
        self.julia_cx = -0.7
        self.julia_cy = 0.27015
        
        self.cmap_name = 'inferno'
        self.gamma = 1.0
        self.invert_colors = False
        self.log_scale = False
        self.color_mode = 'colormap'
        
        self.geometric_order = 5
        self.sierpinski_size = 729
        
        self.use_high_precision = False
        self.adaptive_iter = True
        
        self.hp_calculator = HighPrecisionCalculator()
        self.julia_grid_cache = JuliaGridCache(width, height)
        
        self.current_data = None
        self.current_image = None
        
        self._last_julia_params = None
        self._last_view_params = None
        
        self.zoom_callback: Optional[Callable] = None
        self.pan_callback: Optional[Callable] = None
        self.update_callback: Optional[Callable] = None
        
        self.custom_formula = 'z*z + c'
        self.custom_generator = CustomFractalGenerator(self.custom_formula)
        
        self.mandelbulb_renderer = MandelbulbRenderer(width, height)
        self.mandelbox_renderer = MandelboxRenderer(width, height)
        self.use_ray_march = False
        
        self.color_offset = 0.0
        
        self._setup_figure()
        self._setup_interaction()
    
    def _setup_figure(self):
        """设置Matplotlib图表"""
        self.fig = Figure(figsize=(self.width / 100, self.height / 100), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_aspect('equal')
        self.fig.patch.set_facecolor('#222222')
        self.ax.set_facecolor('#111111')
        self.ax.tick_params(colors='white')
        for spine in self.ax.spines.values():
            spine.set_color('#444444')
        
        if self.parent is not None:
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.parent)
            self.canvas.draw()
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.parent)
            self.toolbar.update()
            self.toolbar.config(bg='#333333')
        else:
            self.canvas = None
            self.toolbar = None
    
    def _setup_interaction(self):
        """设置交互事件"""
        self.rect_selector = RectangleSelector(
            self.ax, self._on_select,
            useblit=True,
            button=[1],
            minspanx=5, minspany=5,
            spancoords='pixels',
            interactive=True,
            props=dict(edgecolor='white', facecolor='none', linewidth=2, alpha=0.8)
        )
        
        if self.canvas is not None:
            self.canvas.mpl_connect('scroll_event', self._on_scroll)
            self.canvas.mpl_connect('button_press_event', self._on_button_press)
            self.canvas.mpl_connect('button_release_event', self._on_button_release)
            self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        
        self._pan_start = None
        self._pan_center = None
    
    def _on_select(self, eclick, erelease):
        """处理矩形选择缩放"""
        if eclick.button != 1:
            return
        
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        
        if x1 is None or y1 is None or x2 is None or y2 is None:
            return
        
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        range_x = abs(x2 - x1)
        base_range = 3.0
        new_zoom = self.zoom * (base_range / range_x)
        
        self.center_x = center_x
        self.center_y = center_y
        self.zoom = min(max(new_zoom, 0.1), 1e15)
        
        if self.zoom_callback:
            self.zoom_callback(self.zoom, self.center_x, self.center_y)
        
        self.render()
    
    def _on_scroll(self, event):
        """处理滚轮缩放"""
        if event.inaxes != self.ax:
            return
        
        zoom_factor = 1.5 if event.button == 'up' else 1 / 1.5
        new_zoom = self.zoom * zoom_factor
        
        if event.xdata is not None and event.ydata is not None:
            mouse_x = event.xdata
            mouse_y = event.ydata
            xmin, xmax, ymin, ymax = compute_view_range(
                self.center_x, self.center_y, self.zoom,
                self.width, self.height
            )
            rel_x = (mouse_x - xmin) / (xmax - xmin)
            rel_y = (mouse_y - ymin) / (ymax - ymin)
            
            new_xmin, new_xmax, new_ymin, new_ymax = compute_view_range(
                self.center_x, self.center_y, new_zoom,
                self.width, self.height
            )
            new_mouse_x = new_xmin + rel_x * (new_xmax - new_xmin)
            new_mouse_y = new_ymin + rel_y * (new_ymax - new_ymin)
            
            self.center_x += (mouse_x - new_mouse_x)
            self.center_y += (mouse_y - new_mouse_y)
        
        self.zoom = min(max(new_zoom, 0.1), 1e15)
        
        if self.zoom_callback:
            self.zoom_callback(self.zoom, self.center_x, self.center_y)
        
        self.render()
    
    def _on_button_press(self, event):
        """处理鼠标按下（开始平移）"""
        if event.button == 3 and event.inaxes == self.ax:
            self._pan_start = (event.x, event.y)
            self._pan_center = (self.center_x, self.center_y)
    
    def _on_button_release(self, event):
        """处理鼠标释放（结束平移）"""
        if event.button == 3:
            self._pan_start = None
            self._pan_center = None
    
    def _on_motion(self, event):
        """处理鼠标移动（平移）"""
        if self._pan_start is None or event.inaxes != self.ax:
            return
        
        dx_pixels = event.x - self._pan_start[0]
        dy_pixels = event.y - self._pan_start[1]
        
        xmin, xmax, ymin, ymax = compute_view_range(
            self.center_x, self.center_y, self.zoom,
            self.width, self.height
        )
        
        dx_world = dx_pixels * (xmax - xmin) / self.width
        dy_world = dy_pixels * (ymax - ymin) / self.height
        
        self.center_x = self._pan_center[0] - dx_world
        self.center_y = self._pan_center[1] + dy_world
        
        if self.pan_callback:
            self.pan_callback(self.center_x, self.center_y)
        
        self.render()
    
    def get_current_iter(self) -> int:
        """获取当前迭代次数（考虑自适应）"""
        if self.adaptive_iter:
            return adaptive_max_iter(self.zoom, self.max_iter)
        return self.max_iter
    
    def render(self):
        """渲染分形图像"""
        if self.fractal_type in ['mandelbrot', 'julia', 'burning_ship', 'custom']:
            self._render_complex_fractal()
        elif self.fractal_type in ['mandelbulb', 'mandelbox']:
            self._render_3d_fractal()
        else:
            self._render_geometric_fractal()
        
        if self.canvas is not None:
            self.canvas.draw_idle()
        
        if self.update_callback:
            self.update_callback()
    
    def _render_complex_fractal(self):
        """渲染复数分形（Mandelbrot、Julia、Burning Ship）"""
        xmin, xmax, ymin, ymax = compute_view_range(
            self.center_x, self.center_y, self.zoom,
            self.width, self.height
        )
        
        max_iter = self.get_current_iter()
        
        need_hp = self.hp_calculator.should_use_high_precision(xmin, xmax)
        
        data = None
        
        if self.use_high_precision and need_hp:
            if self.fractal_type == 'mandelbrot':
                data = self.hp_calculator.mandelbrot_high_precision(
                    xmin, xmax, ymin, ymax, self.width, self.height, max_iter
                )
            elif self.fractal_type == 'julia':
                data = self.hp_calculator.julia_high_precision(
                    xmin, xmax, ymin, ymax, self.width, self.height,
                    self.julia_cx, self.julia_cy, max_iter
                )
        
        if data is None:
            if self.fractal_type == 'mandelbrot':
                data = mandelbrot_set_optimized(
                    xmin, xmax, ymin, ymax, self.width, self.height, max_iter
                )
            elif self.fractal_type == 'julia':
                current_view = (xmin, xmax, ymin, ymax)
                current_params = (self.julia_cx, self.julia_cy, max_iter)
                
                if self.julia_grid_cache.width != self.width or self.julia_grid_cache.height != self.height:
                    self.julia_grid_cache = JuliaGridCache(self.width, self.height)
                
                use_cache = self.julia_grid_cache.is_cached(xmin, xmax, ymin, ymax)
                
                if not use_cache:
                    self.julia_grid_cache.precompute_grid(xmin, xmax, ymin, ymax)
                
                zx_grid, zy_grid = self.julia_grid_cache.get_grids()
                data = julia_set_from_grid(
                    zx_grid, zy_grid,
                    self.julia_cx, self.julia_cy,
                    max_iter
                )
                
                self._last_julia_params = current_params
                self._last_view_params = current_view
            elif self.fractal_type == 'burning_ship':
                data = burning_ship_set(
                    xmin, xmax, ymin, ymax, self.width, self.height, max_iter
                )
            elif self.fractal_type == 'custom':
                data = self.custom_generator.generate_set(
                    xmin, xmax, ymin, ymax,
                    self.width, self.height,
                    self.julia_cx, self.julia_cy,
                    max_iter,
                    is_mandelbrot=True
                )
        
        self.current_data = data
        
        if self.color_mode == 'hsv':
            colored = create_hsv_colormap(data, max_iter)
        elif self.color_mode == 'psychedelic':
            colored = create_psychedelic_colormap(data, max_iter)
        elif self.color_mode == 'hue_cycle':
            colored = create_hue_cycling_colormap(data, max_iter, num_cycles=5)
        else:
            colored = apply_fractal_colors(
                data, self.cmap_name, self.gamma,
                self.invert_colors, self.log_scale,
                color_mode='colormap', max_iter=max_iter
            )
        
        self.ax.clear()
        self.current_image = self.ax.imshow(
            colored,
            extent=[xmin, xmax, ymin, ymax],
            origin='lower',
            aspect='equal'
        )
        
        self._update_axes_labels()
    
    def _render_geometric_fractal(self):
        """渲染几何分形"""
        self.ax.clear()
        
        if self.fractal_type == 'koch_snowflake':
            x, y = koch_snowflake(self.geometric_order, scale=10.0)
            self.ax.fill(x, y, c='#4488ff', alpha=0.8)
            self.ax.plot(x, y, c='#ffffff', linewidth=0.5)
            
        elif self.fractal_type == 'koch_curve':
            x, y = koch_curve(self.geometric_order, scale=10.0)
            self.ax.plot(x, y, c='#44ff88', linewidth=1.0)
            
        elif self.fractal_type == 'sierpinski_carpet':
            carpet = sierpinski_carpet(self.geometric_order, self.sierpinski_size)
            colored = np.zeros((*carpet.shape, 3))
            colored[carpet == 1] = [0.3, 0.6, 1.0]
            colored[carpet == 0] = [0.1, 0.1, 0.1]
            self.current_image = self.ax.imshow(colored, origin='upper', cmap='Blues')
            
        elif self.fractal_type == 'sierpinski_triangle':
            x, y = sierpinski_triangle(self.geometric_order + 10, scale=10.0)
            self.ax.scatter(x, y, s=0.1, c='#ff6644', alpha=0.6)
            
        elif self.fractal_type == 'sierpinski_triangle_poly':
            triangles = sierpinski_triangle_recursive(self.geometric_order, scale=10.0)
            for x, y in triangles:
                self.ax.fill(x, y, c='#44ffaa', alpha=0.7)
                self.ax.plot(x, y, c='#ffffff', linewidth=0.3)
                
        elif self.fractal_type == 'dragon_curve':
            x, y = dragon_curve(self.geometric_order + 5, scale=10.0)
            colors = plt.cm.rainbow(np.linspace(0, 1, len(x)))
            for i in range(len(x) - 1):
                self.ax.plot(x[i:i+2], y[i:i+2], c=colors[i], linewidth=0.8)
                
        elif self.fractal_type == 'hilbert_curve':
            x, y = hilbert_curve(self.geometric_order, scale=10.0)
            colors = plt.cm.hsv(np.linspace(0, 1, len(x)))
            for i in range(len(x) - 1):
                self.ax.plot(x[i:i+2], y[i:i+2], c=colors[i], linewidth=1.0)
        
        self.ax.set_aspect('equal')
        self.ax.set_facecolor('#111111')
        self._update_axes_labels()
    
    def _update_axes_labels(self):
        """更新坐标轴标签"""
        if self.fractal_type in ['mandelbrot', 'julia', 'burning_ship']:
            xmin, xmax, ymin, ymax = compute_view_range(
                self.center_x, self.center_y, self.zoom,
                self.width, self.height
            )
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)
            self.ax.set_xlabel('Real (Re)', color='white', fontsize=10)
            self.ax.set_ylabel('Imaginary (Im)', color='white', fontsize=10)
        else:
            self.ax.set_xlabel('X', color='white', fontsize=10)
            self.ax.set_ylabel('Y', color='white', fontsize=10)
        
        self.ax.tick_params(axis='both', colors='white', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color('#444444')
    
    def reset_view(self):
        """重置视图到初始状态"""
        if self.fractal_type == 'mandelbrot':
            self.center_x = -0.5
            self.center_y = 0.0
        elif self.fractal_type == 'julia':
            self.center_x = 0.0
            self.center_y = 0.0
        elif self.fractal_type == 'burning_ship':
            self.center_x = -0.5
            self.center_y = -0.5
        else:
            self.center_x = 0.0
            self.center_y = 0.0
        
        self.zoom = 1.0
        self.render()
    
    def set_fractal_type(self, fractal_type: str):
        """设置分形类型"""
        self.fractal_type = fractal_type
        self.reset_view()
    
    def set_parameters(self, **kwargs):
        """设置分形参数"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def update_julia_params(self, cx: float, cy: float, max_iter: int = None):
        """
        快速更新Julia集参数（只更新迭代，不重新计算网格）
        
        Args:
            cx: Julia集常数实部
            cy: Julia集常数虚部
            max_iter: 可选的迭代次数，不指定则使用当前值
        """
        if self.fractal_type != 'julia':
            return
        
        if max_iter is None:
            max_iter = self.get_current_iter()
        
        self.julia_cx = cx
        self.julia_cy = cy
        
        xmin, xmax, ymin, ymax = compute_view_range(
            self.center_x, self.center_y, self.zoom,
            self.width, self.height
        )
        
        if self.julia_grid_cache.width != self.width or self.julia_grid_cache.height != self.height:
            self.julia_grid_cache = JuliaGridCache(self.width, self.height)
        
        if not self.julia_grid_cache.is_cached(xmin, xmax, ymin, ymax):
            self.julia_grid_cache.precompute_grid(xmin, xmax, ymin, ymax)
        
        zx_grid, zy_grid = self.julia_grid_cache.get_grids()
        data = julia_set_from_grid(
            zx_grid, zy_grid,
            cx, cy, max_iter
        )
        
        self.current_data = data
        
        if self.color_mode == 'hsv':
            colored = create_hsv_colormap(data, max_iter)
        elif self.color_mode == 'psychedelic':
            colored = create_psychedelic_colormap(data, max_iter)
        elif self.color_mode == 'hue_cycle':
            colored = create_hue_cycling_colormap(data, max_iter, num_cycles=5)
        else:
            colored = apply_fractal_colors(
                data, self.cmap_name, self.gamma,
                self.invert_colors, self.log_scale,
                color_mode='colormap', max_iter=max_iter
            )
        
        self.ax.clear()
        self.current_image = self.ax.imshow(
            colored,
            extent=[xmin, xmax, ymin, ymax],
            origin='lower',
            aspect='equal'
        )
        
        self._update_axes_labels()
        
        if self.canvas is not None:
            self.canvas.draw_idle()
        
        if self.update_callback:
            self.update_callback()
    
    def get_canvas(self):
        """获取Matplotlib画布"""
        return self.canvas
    
    def get_figure(self):
        """获取Matplotlib图表"""
        return self.fig
    
    def save_image(self, filename: str, dpi: int = 300):
        """保存当前图像"""
        self.fig.savefig(filename, dpi=dpi, facecolor='#222222',
                        bbox_inches='tight', pad_inches=0.1)
    
    def _render_3d_fractal(self):
        """渲染3D分形（Mandelbulb、Mandelbox）"""
        if self.fractal_type == 'mandelbulb':
            renderer = self.mandelbulb_renderer
            renderer.set_parameters(
                power=8,
                max_iter=self.get_current_iter() // 10 + 5
            )
            image = renderer.render(use_ray_march=self.use_ray_march)
        elif self.fractal_type == 'mandelbox':
            renderer = self.mandelbox_renderer
            image = renderer.render()
        else:
            return
        
        self.current_image = image
        
        self.ax.clear()
        self.ax.imshow(image, origin='upper')
        self.ax.set_aspect('equal')
        self.ax.set_facecolor('#111111')
        
        if self.fractal_type == 'mandelbulb':
            self.ax.set_title(
                f"Mandelbulb (power={self.mandelbulb_renderer.power}, "
                f"rot=({math.degrees(self.mandelbulb_renderer.rotation_x):.0f}°, "
                f"{math.degrees(self.mandelbulb_renderer.rotation_y):.0f}°))",
                color='white', fontsize=10
            )
        elif self.fractal_type == 'mandelbox':
            self.ax.set_title(
                f"Mandelbox (scale={self.mandelbox_renderer.scale:.1f})",
                color='white', fontsize=10
            )
        
        self.ax.set_xticks([])
        self.ax.set_yticks([])
    
    def rotate_3d(self, dx: int, dy: int):
        """旋转3D分形视角"""
        if self.fractal_type == 'mandelbulb':
            self.mandelbulb_renderer.rotate(dx, dy)
        elif self.fractal_type == 'mandelbox':
            self.mandelbox_renderer.rotate(dx, dy)
        self.render()
    
    def zoom_3d(self, factor: float):
        """3D缩放"""
        if self.fractal_type == 'mandelbulb':
            self.mandelbulb_renderer.zoom(factor)
        elif self.fractal_type == 'mandelbox':
            self.mandelbox_renderer.zoom(factor)
        self.render()
    
    def set_custom_formula(self, formula: str) -> Tuple[bool, str]:
        """设置自定义公式"""
        valid, error = self.custom_generator.validate_formula(formula)
        if valid:
            self.custom_formula = formula
            self.custom_generator.set_formula(formula)
            return True, ''
        return False, error
    
    def update_parameters(self, params: dict):
        """批量更新参数（用于动画）"""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        if 'power' in params and self.fractal_type == 'mandelbulb':
            self.mandelbulb_renderer.set_parameters(power=params['power'])
        if 'rotation_x' in params and self.fractal_type in ['mandelbulb', 'mandelbox']:
            if self.fractal_type == 'mandelbulb':
                self.mandelbulb_renderer.rotation_x = params['rotation_x']
            else:
                self.mandelbox_renderer.rotation_x = params['rotation_x']
        if 'rotation_y' in params and self.fractal_type in ['mandelbulb', 'mandelbox']:
            if self.fractal_type == 'mandelbulb':
                self.mandelbulb_renderer.rotation_y = params['rotation_y']
            else:
                self.mandelbox_renderer.rotation_y = params['rotation_y']
    
    def _on_button_press(self, event):
        """处理鼠标按下（开始平移/旋转）"""
        if event.button == 3 and event.inaxes == self.ax:
            self._pan_start = (event.x, event.y)
            self._pan_center = (self.center_x, self.center_y)
        
        if event.button == 1 and self.fractal_type in ['mandelbulb', 'mandelbox']:
            self._pan_start = (event.x, event.y)
    
    def _on_motion(self, event):
        """处理鼠标移动（平移/旋转）"""
        if self._pan_start is None or event.inaxes != self.ax:
            return
        
        if self.fractal_type in ['mandelbulb', 'mandelbox']:
            dx_pixels = event.x - self._pan_start[0]
            dy_pixels = event.y - self._pan_start[1]
            
            if abs(dx_pixels) > 1 or abs(dy_pixels) > 1:
                self.rotate_3d(dx_pixels, dy_pixels)
                self._pan_start = (event.x, event.y)
            return
        
        dx_pixels = event.x - self._pan_start[0]
        dy_pixels = event.y - self._pan_start[1]
        
        xmin, xmax, ymin, ymax = compute_view_range(
            self.center_x, self.center_y, self.zoom,
            self.width, self.height
        )
        
        dx_world = dx_pixels * (xmax - xmin) / self.width
        dy_world = dy_pixels * (ymax - ymin) / self.height
        
        self.center_x = self._pan_center[0] - dx_world
        self.center_y = self._pan_center[1] + dy_world
        
        if self.pan_callback:
            self.pan_callback(self.center_x, self.center_y)
        
        self.render()
    
    def _on_scroll(self, event):
        """处理滚轮缩放"""
        if event.inaxes != self.ax:
            return
        
        if self.fractal_type in ['mandelbulb', 'mandelbox']:
            zoom_factor = 1.1 if event.button == 'up' else 1 / 1.1
            self.zoom_3d(zoom_factor)
            return
        
        zoom_factor = 1.5 if event.button == 'up' else 1 / 1.5
        new_zoom = self.zoom * zoom_factor
        
        if event.xdata is not None and event.ydata is not None:
            mouse_x = event.xdata
            mouse_y = event.ydata
            xmin, xmax, ymin, ymax = compute_view_range(
                self.center_x, self.center_y, self.zoom,
                self.width, self.height
            )
            rel_x = (mouse_x - xmin) / (xmax - xmin)
            rel_y = (mouse_y - ymin) / (ymax - ymin)
            
            new_xmin, new_xmax, new_ymin, new_ymax = compute_view_range(
                self.center_x, self.center_y, new_zoom,
                self.width, self.height
            )
            new_mouse_x = new_xmin + rel_x * (new_xmax - new_xmin)
            new_mouse_y = new_ymin + rel_y * (new_ymax - new_ymin)
            
            self.center_x += (mouse_x - new_mouse_x)
            self.center_y += (mouse_y - new_mouse_y)
        
        self.zoom = min(max(new_zoom, 0.1), 1e15)
        
        if self.zoom_callback:
            self.zoom_callback(self.zoom, self.center_x, self.center_y)
        
        self.render()
    
    def get_status_info(self) -> dict:
        """获取当前状态信息"""
        if self.fractal_type in ['mandelbulb', 'mandelbox']:
            if self.fractal_type == 'mandelbulb':
                renderer = self.mandelbulb_renderer
            else:
                renderer = self.mandelbox_renderer
            
            return {
                'fractal_type': self.fractal_type,
                'rotation_x': renderer.rotation_x,
                'rotation_y': renderer.rotation_y,
                'camera_distance': renderer.camera_distance,
                'max_iter': self.get_current_iter(),
                'resolution': (self.width, self.height),
                'is_3d': True
            }
        
        xmin, xmax, ymin, ymax = compute_view_range(
            self.center_x, self.center_y, self.zoom,
            self.width, self.height
        )
        
        return {
            'fractal_type': self.fractal_type,
            'center_x': self.center_x,
            'center_y': self.center_y,
            'zoom': self.zoom,
            'max_iter': self.get_current_iter(),
            'x_range': (xmin, xmax),
            'y_range': (ymin, ymax),
            'resolution': (self.width, self.height),
            'using_high_precision': self.use_high_precision and 
                                   self.hp_calculator.should_use_high_precision(xmin, xmax),
            'is_3d': False
        }
