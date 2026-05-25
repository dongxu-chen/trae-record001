import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from typing import Optional, Callable
import time
import math
import threading

from fractal_plotter import FractalPlotter
from color_maps import get_available_colormaps
from high_precision import get_mandelbrot_interesting_points, get_julia_classic_sets
from formula_editor import FormulaEditor, FormulaPresetLibrary
from fractal_animation import FractalAnimation, PresetAnimations, Keyframe


class ControlPanel(ttk.Frame):
    """控制面板，包含所有参数调节控件"""
    
    def __init__(self, parent, plotter: FractalPlotter, **kwargs):
        super().__init__(parent, **kwargs)
        self.plotter = plotter
        
        self._setup_style()
        self._build_ui()
        
        self._updating = False
    
    def _setup_style(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='white', font=('Arial', 9))
        style.configure('TButton', background='#4a4a4a', foreground='white', font=('Arial', 9))
        style.map('TButton', background=[('active', '#5a5a5a')])
        style.configure('TScale', background='#2b2b2b', troughcolor='#3a3a3a')
        style.configure('TCombobox', fieldbackground='#3a3a3a', background='#4a4a4a', foreground='white')
        style.configure('TCheckbutton', background='#2b2b2b', foreground='white')
        style.configure('TNotebook', background='#2b2b2b', borderwidth=0)
        style.configure('TNotebook.Tab', background='#3a3a3a', foreground='white', padding=[10, 5])
        style.map('TNotebook.Tab', background=[('selected', '#4a4a4a')])
        style.configure('TLabelframe', background='#2b2b2b', foreground='white', bordercolor='#4a4a4a')
        style.configure('TLabelframe.Label', background='#2b2b2b', foreground='white', font=('Arial', 10, 'bold'))
        style.configure('TEntry', fieldbackground='#3a3a3a', foreground='white', insertcolor='white')
        style.configure('Horizontal.TProgressbar', background='#4a90e2', troughcolor='#3a3a3a')
    
    def _build_ui(self):
        """构建用户界面"""
        self.configure(style='TFrame')
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        self._build_main_tab(notebook)
        self._build_color_tab(notebook)
        self._build_3d_tab(notebook)
        self._build_formula_tab(notebook)
        self._build_animation_tab(notebook)
        self._build_presets_tab(notebook)
        self._build_advanced_tab(notebook)
        
        self.formula_editor = FormulaEditor()
        self.current_animation = None
        self.animation_thread = None
    
    def _build_main_tab(self, notebook):
        """构建主参数选项卡"""
        main_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(main_tab, text='主参数')
        
        fractal_frame = ttk.LabelFrame(main_tab, text='分形类型', style='TLabelframe')
        fractal_frame.pack(fill='x', padx=5, pady=5)
        
        fractal_types = [
            ('Mandelbrot集', 'mandelbrot'),
            ('Julia集', 'julia'),
            ('Burning Ship', 'burning_ship'),
            ('自定义公式', 'custom'),
            ('Mandelbulb (3D)', 'mandelbulb'),
            ('Mandelbox (3D)', 'mandelbox'),
            ('科赫雪花', 'koch_snowflake'),
            ('科赫曲线', 'koch_curve'),
            ('谢尔宾斯基地毯', 'sierpinski_carpet'),
            ('谢尔宾斯基三角', 'sierpinski_triangle'),
            ('谢尔宾斯基三角(多边形)', 'sierpinski_triangle_poly'),
            ('龙形曲线', 'dragon_curve'),
            ('希尔伯特曲线', 'hilbert_curve'),
        ]
        
        self.fractal_var = tk.StringVar(value='mandelbrot')
        for i, (name, value) in enumerate(fractal_types):
            rb = ttk.Radiobutton(
                fractal_frame, text=name, value=value,
                variable=self.fractal_var, command=self._on_fractal_change
            )
            rb.grid(row=i // 2, column=i % 2, sticky='w', padx=5, pady=2)
        
        iter_frame = ttk.LabelFrame(main_tab, text='迭代参数', style='TLabelframe')
        iter_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(iter_frame, text='基础迭代次数:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.iter_var = tk.IntVar(value=100)
        self.iter_scale = ttk.Scale(
            iter_frame, from_=10, to=2000, orient='horizontal',
            variable=self.iter_var, command=self._on_iter_change
        )
        self.iter_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.iter_label = ttk.Label(iter_frame, text='100')
        self.iter_label.grid(row=0, column=2, padx=5)
        
        self.adaptive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            iter_frame, text='自适应迭代次数', variable=self.adaptive_var,
            command=self._on_adaptive_change
        ).grid(row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        view_frame = ttk.LabelFrame(main_tab, text='视图控制', style='TLabelframe')
        view_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(view_frame, text='缩放:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.zoom_entry = ttk.Entry(view_frame, textvariable=self.zoom_var, width=15)
        self.zoom_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.zoom_entry.bind('<Return>', self._on_zoom_entry)
        
        ttk.Label(view_frame, text='中心点 X:').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.center_x_var = tk.DoubleVar(value=-0.5)
        self.center_x_entry = ttk.Entry(view_frame, textvariable=self.center_x_var, width=25)
        self.center_x_entry.grid(row=1, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.center_x_entry.bind('<Return>', self._on_center_entry)
        
        ttk.Label(view_frame, text='中心点 Y:').grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.center_y_var = tk.DoubleVar(value=0.0)
        self.center_y_entry = ttk.Entry(view_frame, textvariable=self.center_y_var, width=25)
        self.center_y_entry.grid(row=2, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        self.center_y_entry.bind('<Return>', self._on_center_entry)
        
        btn_frame = ttk.Frame(view_frame, style='TFrame')
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5)
        ttk.Button(btn_frame, text='重置视图', command=self._on_reset_view).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='重新渲染', command=self._on_render).pack(side='left', padx=5)
        
        julia_frame = ttk.LabelFrame(main_tab, text='Julia集参数', style='TLabelframe')
        julia_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(julia_frame, text='常数 Cx:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.julia_cx_var = tk.DoubleVar(value=-0.7)
        self.julia_cx_scale = ttk.Scale(
            julia_frame, from_=-2.0, to=2.0, orient='horizontal',
            variable=self.julia_cx_var, command=self._on_julia_param_change
        )
        self.julia_cx_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.julia_cx_label = ttk.Label(julia_frame, text='-0.7000')
        self.julia_cx_label.grid(row=0, column=2, padx=5)
        
        ttk.Label(julia_frame, text='常数 Cy:').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.julia_cy_var = tk.DoubleVar(value=0.27015)
        self.julia_cy_scale = ttk.Scale(
            julia_frame, from_=-2.0, to=2.0, orient='horizontal',
            variable=self.julia_cy_var, command=self._on_julia_param_change
        )
        self.julia_cy_scale.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.julia_cy_label = ttk.Label(julia_frame, text='0.2702')
        self.julia_cy_label.grid(row=1, column=2, padx=5)
        
        geo_frame = ttk.LabelFrame(main_tab, text='几何分形参数', style='TLabelframe')
        geo_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(geo_frame, text='递归阶数:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.geo_order_var = tk.IntVar(value=5)
        self.geo_order_scale = ttk.Scale(
            geo_frame, from_=1, to=10, orient='horizontal',
            variable=self.geo_order_var, command=self._on_geo_order_change
        )
        self.geo_order_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.geo_order_label = ttk.Label(geo_frame, text='5')
        self.geo_order_label.grid(row=0, column=2, padx=5)
        
        main_tab.columnconfigure(1, weight=1)
        iter_frame.columnconfigure(1, weight=1)
        view_frame.columnconfigure(1, weight=1)
        julia_frame.columnconfigure(1, weight=1)
        geo_frame.columnconfigure(1, weight=1)
    
    def _build_color_tab(self, notebook):
        """构建颜色设置选项卡"""
        color_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(color_tab, text='颜色设置')
        
        color_mode_frame = ttk.LabelFrame(color_tab, text='颜色模式', style='TLabelframe')
        color_mode_frame.pack(fill='x', padx=5, pady=5)
        
        color_modes = [
            ('颜色映射', 'colormap'),
            ('HSV着色', 'hsv'),
            ('迷幻风格', 'psychedelic'),
            ('色相循环', 'hue_cycle'),
        ]
        
        self.color_mode_var = tk.StringVar(value='colormap')
        for i, (name, value) in enumerate(color_modes):
            ttk.Radiobutton(
                color_mode_frame, text=name, value=value,
                variable=self.color_mode_var, command=self._on_color_mode_change
            ).grid(row=0, column=i, sticky='w', padx=10, pady=5)
        
        cmap_frame = ttk.LabelFrame(color_tab, text='颜色映射', style='TLabelframe')
        cmap_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(cmap_frame, text='选择颜色映射:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        self.cmap_var = tk.StringVar(value='inferno')
        cmap_list = sorted(get_available_colormaps().keys())
        self.cmap_combo = ttk.Combobox(
            cmap_frame, textvariable=self.cmap_var, values=cmap_list,
            state='readonly', width=25
        )
        self.cmap_combo.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.cmap_combo.bind('<<ComboboxSelected>>', self._on_cmap_change)
        
        cmap_frame.columnconfigure(1, weight=1)
        
        color_adjust_frame = ttk.LabelFrame(color_tab, text='颜色调整', style='TLabelframe')
        color_adjust_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(color_adjust_frame, text='Gamma校正:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.gamma_var = tk.DoubleVar(value=1.0)
        self.gamma_scale = ttk.Scale(
            color_adjust_frame, from_=0.1, to=3.0, orient='horizontal',
            variable=self.gamma_var, command=self._on_gamma_change
        )
        self.gamma_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.gamma_label = ttk.Label(color_adjust_frame, text='1.00')
        self.gamma_label.grid(row=0, column=2, padx=5)
        
        self.invert_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            color_adjust_frame, text='反转颜色', variable=self.invert_var,
            command=self._on_invert_change
        ).grid(row=1, column=0, sticky='w', padx=5, pady=5)
        
        self.log_scale_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            color_adjust_frame, text='对数缩放', variable=self.log_scale_var,
            command=self._on_log_scale_change
        ).grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        color_adjust_frame.columnconfigure(1, weight=1)
        
        preview_frame = ttk.LabelFrame(color_tab, text='颜色预览', style='TLabelframe')
        preview_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, height=40, bg='#111111', highlightthickness=0)
        self.preview_canvas.pack(fill='x', padx=5, pady=5)
        self._update_color_preview()
    
    def _build_3d_tab(self, notebook):
        """构建3D分形设置选项卡"""
        d3_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(d3_tab, text='3D分形')
        
        d3_params_frame = ttk.LabelFrame(d3_tab, text='3D渲染参数', style='TLabelframe')
        d3_params_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(d3_params_frame, text='Mandelbulb幂次:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.mandelbulb_power_var = tk.IntVar(value=8)
        self.mandelbulb_power_scale = ttk.Scale(
            d3_params_frame, from_=2, to=16, orient='horizontal',
            variable=self.mandelbulb_power_var, command=self._on_mandelbulb_power_change
        )
        self.mandelbulb_power_scale.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.mandelbulb_power_label = ttk.Label(d3_params_frame, text='8')
        self.mandelbulb_power_label.grid(row=0, column=2, padx=5)
        
        self.ray_march_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            d3_params_frame, text='启用光线步进(高质量，慢)',
            variable=self.ray_march_var, command=self._on_ray_march_change
        ).grid(row=1, column=0, columnspan=3, sticky='w', padx=5, pady=5)
        
        d3_controls_frame = ttk.LabelFrame(d3_tab, text='3D视角控制', style='TLabelframe')
        d3_controls_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(d3_controls_frame, text='旋转控制: 左键拖拽').grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Label(d3_controls_frame, text='缩放控制: 滚轮').grid(row=1, column=0, sticky='w', padx=5, pady=2)
        
        btn_frame = ttk.Frame(d3_controls_frame, style='TFrame')
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text='重置视角', command=self._on_reset_3d_view).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='自动旋转', command=self._on_auto_rotate).pack(side='left', padx=5)
        
        d3_params_frame.columnconfigure(1, weight=1)
        
        info_frame = ttk.LabelFrame(d3_tab, text='3D分形说明', style='TLabelframe')
        info_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        d3_help_text = [
            'Mandelbulb:',
            '  经典的3D分形，由Mandelbrot集推广而来',
            '  通过调整幂次可以获得不同的形态',
            '',
            'Mandelbox:',
            '  基于空间折叠的3D分形',
            '  具有独特的立方体结构',
            '',
            '操作提示:',
            '  • 左键拖拽: 旋转3D视角',
            '  • 滚轮: 缩放3D视图',
            '  • 光线步进: 高质量但渲染较慢',
        ]
        
        d3_help_widget = tk.Text(info_frame, bg='#1a1a1a', fg='#cccccc',
                                  font=('Consolas', 9), height=12, wrap='word')
        d3_help_widget.pack(fill='both', expand=True, padx=5, pady=5)
        d3_help_widget.insert('1.0', '\n'.join(d3_help_text))
        d3_help_widget.config(state='disabled')
    
    def _build_formula_tab(self, notebook):
        """构建公式编辑器选项卡"""
        formula_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(formula_tab, text='公式编辑器')
        
        formula_input_frame = ttk.LabelFrame(formula_tab, text='迭代公式', style='TLabelframe')
        formula_input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(formula_input_frame, text='f(z, c) =').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.formula_var = tk.StringVar(value='z*z + c')
        self.formula_entry = ttk.Entry(formula_input_frame, textvariable=self.formula_var, font=('Consolas', 11))
        self.formula_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        self.formula_entry.bind('<Return>', self._on_formula_apply)
        
        btn_frame = ttk.Frame(formula_input_frame, style='TFrame')
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text='验证公式', command=self._on_formula_validate).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='应用公式', command=self._on_formula_apply).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='语法帮助', command=self._on_formula_help).pack(side='left', padx=5)
        
        self.formula_status_var = tk.StringVar(value='')
        self.formula_status_label = ttk.Label(formula_input_frame, textvariable=self.formula_status_var)
        self.formula_status_label.grid(row=2, column=0, columnspan=2, sticky='w', padx=5, pady=2)
        
        presets_frame = ttk.LabelFrame(formula_tab, text='预设公式库', style='TLabelframe')
        presets_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        categories = FormulaPresetLibrary.get_categories()
        self.preset_category_var = tk.StringVar(value=list(categories.keys())[0])
        self.preset_category_combo = ttk.Combobox(
            presets_frame, textvariable=self.preset_category_var,
            values=list(categories.keys()), state='readonly'
        )
        self.preset_category_combo.pack(fill='x', padx=5, pady=5)
        self.preset_category_combo.bind('<<ComboboxSelected>>', self._on_formula_category_change)
        
        self.preset_listbox = tk.Listbox(presets_frame, bg='#3a3a3a', fg='white',
                                         selectbackground='#4a90e2', height=8)
        self.preset_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.preset_listbox.bind('<Double-1>', self._on_formula_preset_select)
        
        ttk.Button(presets_frame, text='应用选中预设',
                  command=self._on_formula_preset_select).pack(fill='x', padx=5, pady=5)
        
        history_frame = ttk.LabelFrame(formula_tab, text='历史公式', style='TLabelframe')
        history_frame.pack(fill='x', padx=5, pady=5)
        
        self.history_listbox = tk.Listbox(history_frame, bg='#3a3a3a', fg='white',
                                          selectbackground='#4a90e2', height=4)
        self.history_listbox.pack(fill='x', padx=5, pady=5)
        self.history_listbox.bind('<Double-1>', self._on_history_select)
        
        formula_input_frame.columnconfigure(1, weight=1)
    
    def _build_animation_tab(self, notebook):
        """构建动画控制选项卡"""
        anim_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(anim_tab, text='动画')
        
        preset_anim_frame = ttk.LabelFrame(anim_tab, text='预设动画', style='TLabelframe')
        preset_anim_frame.pack(fill='x', padx=5, pady=5)
        
        animation_presets = [
            ('Julia参数变化', 'julia_params'),
            ('Mandelbulb旋转', 'mandelbulb_spin'),
            ('迭代次数脉冲', 'iteration_pulse'),
        ]
        
        self.anim_preset_var = tk.StringVar(value='julia_params')
        for i, (name, value) in enumerate(animation_presets):
            ttk.Radiobutton(
                preset_anim_frame, text=name, value=value,
                variable=self.anim_preset_var
            ).grid(row=i // 2, column=i % 2, sticky='w', padx=5, pady=2)
        
        ttk.Label(preset_anim_frame, text='时长(秒):').grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.anim_duration_var = tk.DoubleVar(value=5.0)
        self.anim_duration_entry = ttk.Entry(preset_anim_frame, textvariable=self.anim_duration_var, width=10)
        self.anim_duration_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(preset_anim_frame, text='FPS:').grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.anim_fps_var = tk.IntVar(value=20)
        self.anim_fps_entry = ttk.Entry(preset_anim_frame, textvariable=self.anim_fps_var, width=10)
        self.anim_fps_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        control_frame = ttk.LabelFrame(anim_tab, text='播放控制', style='TLabelframe')
        control_frame.pack(fill='x', padx=5, pady=5)
        
        btn_frame = ttk.Frame(control_frame, style='TFrame')
        btn_frame.pack(fill='x', padx=5, pady=5)
        self.anim_play_btn = ttk.Button(btn_frame, text='▶ 播放', command=self._on_animation_play)
        self.anim_play_btn.pack(side='left', padx=5)
        self.anim_stop_btn = ttk.Button(btn_frame, text='■ 停止', command=self._on_animation_stop, state='disabled')
        self.anim_stop_btn.pack(side='left', padx=5)
        
        self.anim_progress_var = tk.DoubleVar(value=0.0)
        self.anim_progress = ttk.Progressbar(control_frame, variable=self.anim_progress_var, maximum=100)
        self.anim_progress.pack(fill='x', padx=5, pady=5)
        
        self.anim_frame_var = tk.StringVar(value='帧: 0 / 0')
        self.anim_frame_label = ttk.Label(control_frame, textvariable=self.anim_frame_var)
        self.anim_frame_label.pack(padx=5, pady=2)
        
        export_frame = ttk.LabelFrame(anim_tab, text='导出动画', style='TLabelframe')
        export_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(export_frame, text='导出为GIF', command=self._on_export_gif).pack(fill='x', padx=5, pady=5)
        ttk.Button(export_frame, text='导出为视频(需imageio)', command=self._on_export_video).pack(fill='x', padx=5, pady=5)
        
        preset_anim_frame.columnconfigure(1, weight=1)
    
    def _build_presets_tab(self, notebook):
        """构建预设位置选项卡"""
        presets_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(presets_tab, text='预设位置')
        
        mandel_frame = ttk.LabelFrame(presets_tab, text='Mandelbrot 有趣位置', style='TLabelframe')
        mandel_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        mandel_points = get_mandelbrot_interesting_points()
        self.mandel_listbox = tk.Listbox(mandel_frame, bg='#3a3a3a', fg='white',
                                        selectbackground='#4a90e2', height=6)
        for point in mandel_points:
            self.mandel_listbox.insert('end', f"{point['name']} (×{point['zoom']:.0f})")
        self.mandel_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.mandel_listbox.bind('<Double-1>', lambda e: self._on_mandel_preset(mandel_points))
        
        ttk.Button(mandel_frame, text='跳转到选中位置',
                  command=lambda: self._on_mandel_preset(mandel_points)).pack(fill='x', padx=5, pady=5)
        
        julia_frame = ttk.LabelFrame(presets_tab, text='经典 Julia 集', style='TLabelframe')
        julia_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        julia_sets = get_julia_classic_sets()
        self.julia_listbox = tk.Listbox(julia_frame, bg='#3a3a3a', fg='white',
                                       selectbackground='#4a90e2', height=6)
        for js in julia_sets:
            self.julia_listbox.insert('end', f"{js['name']} (C={js['cx']:.4f}+{js['cy']:.4f}i)")
        self.julia_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.julia_listbox.bind('<Double-1>', lambda e: self._on_julia_preset(julia_sets))
        
        ttk.Button(julia_frame, text='应用选中的Julia集',
                  command=lambda: self._on_julia_preset(julia_sets)).pack(fill='x', padx=5, pady=5)
    
    def _build_advanced_tab(self, notebook):
        """构建高级设置选项卡"""
        advanced_tab = ttk.Frame(notebook, style='TFrame')
        notebook.add(advanced_tab, text='高级设置')
        
        precision_frame = ttk.LabelFrame(advanced_tab, text='精度设置', style='TLabelframe')
        precision_frame.pack(fill='x', padx=5, pady=5)
        
        self.high_precision_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            precision_frame, text='启用高精度计算 (decimal)',
            variable=self.high_precision_var, command=self._on_high_precision_change
        ).grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        
        ttk.Label(precision_frame, text='(当缩放超过1e12倍时自动启用高精度)').grid(
            row=1, column=0, columnspan=2, sticky='w', padx=15, pady=2
        )
        
        render_frame = ttk.LabelFrame(advanced_tab, text='渲染设置', style='TLabelframe')
        render_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(render_frame, text='渲染宽度:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.width_var = tk.IntVar(value=800)
        self.width_entry = ttk.Entry(render_frame, textvariable=self.width_var, width=10)
        self.width_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(render_frame, text='渲染高度:').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.height_var = tk.IntVar(value=600)
        self.height_entry = ttk.Entry(render_frame, textvariable=self.height_var, width=10)
        self.height_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Button(render_frame, text='应用分辨率', command=self._on_resolution_change).grid(
            row=2, column=0, columnspan=2, pady=5
        )
        
        save_frame = ttk.LabelFrame(advanced_tab, text='保存图像', style='TLabelframe')
        save_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(save_frame, text='DPI:').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.dpi_var = tk.IntVar(value=300)
        self.dpi_combo = ttk.Combobox(
            save_frame, textvariable=self.dpi_var,
            values=[72, 96, 150, 300, 600], state='readonly', width=10
        )
        self.dpi_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Button(save_frame, text='保存为PNG', command=self._on_save_image).grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5
        )
        
        info_frame = ttk.LabelFrame(advanced_tab, text='使用说明', style='TLabelframe')
        info_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        help_text = [
            '鼠标操作:',
            '  • 左键拖拽: 框选区域缩放',
            '  • 滚轮: 以鼠标位置为中心缩放',
            '  • 右键拖拽: 平移视图',
            '',
            '快捷键:',
            '  • R: 重置视图',
            '  • 空格: 重新渲染',
            '  • S: 保存图像',
            '',
            '分形类型:',
            '  • Mandelbrot/Julia: 复数分形，可无限缩放',
            '  • Burning Ship: 变体分形',
            '  • 科赫雪花/曲线: 几何分形',
            '  • 谢尔宾斯基: 自相似分形',
            '  • 龙形/希尔伯特: 空间填充曲线',
        ]
        
        help_text_widget = tk.Text(info_frame, bg='#1a1a1a', fg='#cccccc',
                                   font=('Consolas', 9), height=15, wrap='word')
        help_text_widget.pack(fill='both', expand=True, padx=5, pady=5)
        help_text_widget.insert('1.0', '\n'.join(help_text))
        help_text_widget.config(state='disabled')
    
    def _update_color_preview(self):
        """更新颜色预览条"""
        try:
            from color_maps import get_colormap
            cmap = get_colormap(self.cmap_var.get())
            
            self.preview_canvas.delete('all')
            width = self.preview_canvas.winfo_width()
            if width < 10:
                width = 400
            height = 40
            
            for i in range(width):
                t = i / (width - 1)
                if self.invert_var.get():
                    t = 1 - t
                if self.gamma_var.get() != 1.0:
                    t = t ** self.gamma_var.get()
                color = cmap(t)
                hex_color = f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'
                self.preview_canvas.create_line(i, 0, i, height, fill=hex_color)
        except:
            pass
    
    def _on_fractal_change(self):
        """分形类型改变"""
        if not self._updating:
            self._updating = True
            fractal_type = self.fractal_var.get()
            self.plotter.set_fractal_type(fractal_type)
            self._update_view_fields()
            self._updating = False
    
    def _on_iter_change(self, value):
        """迭代次数改变"""
        if not self._updating:
            self._updating = True
            self.iter_label.config(text=str(int(float(value))))
            self.plotter.max_iter = int(float(value))
            if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
                self.plotter.render()
            self._updating = False
    
    def _on_adaptive_change(self):
        """自适应迭代改变"""
        self.plotter.adaptive_iter = self.adaptive_var.get()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_zoom_entry(self, event):
        """缩放输入框"""
        try:
            zoom = float(self.zoom_var.get())
            self.plotter.zoom = max(0.1, min(zoom, 1e15))
            self.plotter.render()
        except:
            self.zoom_var.set(self.plotter.zoom)
    
    def _on_center_entry(self, event):
        """中心点输入框"""
        try:
            cx = float(self.center_x_var.get())
            cy = float(self.center_y_var.get())
            self.plotter.center_x = cx
            self.plotter.center_y = cy
            self.plotter.render()
        except:
            self.center_x_var.set(self.plotter.center_x)
            self.center_y_var.set(self.plotter.center_y)
    
    def _on_reset_view(self):
        """重置视图"""
        self.plotter.reset_view()
        self._update_view_fields()
    
    def _on_render(self):
        """重新渲染"""
        self.plotter.render()
    
    def _on_julia_param_change(self, value=None):
        """Julia参数改变（使用快速更新，只更新迭代公式）"""
        if not self._updating:
            self._updating = True
            cx = self.julia_cx_var.get()
            cy = self.julia_cy_var.get()
            self.julia_cx_label.config(text=f'{cx:.4f}')
            self.julia_cy_label.config(text=f'{cy:.4f}')
            if self.fractal_var.get() == 'julia':
                max_iter = self.plotter.get_current_iter()
                self.plotter.update_julia_params(cx, cy, max_iter)
            else:
                self.plotter.julia_cx = cx
                self.plotter.julia_cy = cy
            self._updating = False
    
    def _on_geo_order_change(self, value):
        """几何分形阶数改变"""
        if not self._updating:
            self._updating = True
            order = int(float(value))
            self.geo_order_label.config(text=str(order))
            self.plotter.geometric_order = order
            if self.fractal_var.get() not in ['mandelbrot', 'julia', 'burning_ship']:
                self.plotter.render()
            self._updating = False
    
    def _on_color_mode_change(self):
        """颜色模式改变"""
        self.plotter.color_mode = self.color_mode_var.get()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_cmap_change(self, event=None):
        """颜色映射改变"""
        self.plotter.cmap_name = self.cmap_var.get()
        self._update_color_preview()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_gamma_change(self, value):
        """Gamma改变"""
        gamma = float(value)
        self.gamma_label.config(text=f'{gamma:.2f}')
        self.plotter.gamma = gamma
        self._update_color_preview()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_invert_change(self):
        """反转颜色改变"""
        self.plotter.invert_colors = self.invert_var.get()
        self._update_color_preview()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_log_scale_change(self):
        """对数缩放改变"""
        self.plotter.log_scale = self.log_scale_var.get()
        if self.fractal_var.get() in ['mandelbrot', 'julia', 'burning_ship']:
            self.plotter.render()
    
    def _on_mandel_preset(self, points):
        """Mandelbrot预设位置"""
        selection = self.mandel_listbox.curselection()
        if selection:
            point = points[selection[0]]
            self.fractal_var.set('mandelbrot')
            self.plotter.set_fractal_type('mandelbrot')
            self.plotter.center_x = point['center_x']
            self.plotter.center_y = point['center_y']
            self.plotter.zoom = point['zoom']
            self.plotter.render()
            self._update_view_fields()
    
    def _on_julia_preset(self, julia_sets):
        """Julia预设"""
        selection = self.julia_listbox.curselection()
        if selection:
            js = julia_sets[selection[0]]
            self.fractal_var.set('julia')
            self.plotter.set_fractal_type('julia')
            self.julia_cx_var.set(js['cx'])
            self.julia_cy_var.set(js['cy'])
            self.julia_cx_label.config(text=f'{js["cx"]:.4f}')
            self.julia_cy_label.config(text=f'{js["cy"]:.4f}')
            self.plotter.julia_cx = js['cx']
            self.plotter.julia_cy = js['cy']
            self.plotter.center_x = js['center_x']
            self.plotter.center_y = js['center_y']
            self.plotter.zoom = js['zoom']
            self.plotter.render()
            self._update_view_fields()
    
    def _on_high_precision_change(self):
        """高精度设置改变"""
        self.plotter.use_high_precision = self.high_precision_var.get()
    
    def _on_resolution_change(self):
        """分辨率改变"""
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            width = max(200, min(width, 4096))
            height = max(200, min(height, 4096))
            self.plotter.width = width
            self.plotter.height = height
            self.plotter.render()
        except:
            messagebox.showerror('错误', '请输入有效的分辨率值')
    
    def _on_save_image(self):
        """保存图像"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG图像', '*.png'), ('JPEG图像', '*.jpg'), ('所有文件', '*.*')]
        )
        if filename:
            try:
                self.plotter.save_image(filename, dpi=self.dpi_var.get())
                messagebox.showinfo('成功', f'图像已保存到:\n{filename}')
            except Exception as e:
                messagebox.showerror('错误', f'保存失败: {str(e)}')
    
    def _update_view_fields(self):
        """更新视图字段显示"""
        self._updating = True
        self.zoom_var.set(self.plotter.zoom)
        self.center_x_var.set(self.plotter.center_x)
        self.center_y_var.set(self.plotter.center_y)
        self._updating = False
    
    def update_from_plotter(self):
        """从plotter更新控件值"""
        if not self._updating:
            self._updating = True
            self.zoom_var.set(round(self.plotter.zoom, 6))
            self.center_x_var.set(round(self.plotter.center_x, 15))
            self.center_y_var.set(round(self.plotter.center_y, 15))
            self.iter_label.config(text=str(self.plotter.get_current_iter()))
            self._updating = False
    
    def _on_mandelbulb_power_change(self, value):
        """Mandelbulb幂次改变"""
        if not self._updating:
            self._updating = True
            power = int(float(value))
            self.mandelbulb_power_label.config(text=str(power))
            self.plotter.mandelbulb_renderer.set_parameters(power=power)
            if self.fractal_var.get() == 'mandelbulb':
                self.plotter.render()
            self._updating = False
    
    def _on_ray_march_change(self):
        """光线步进设置改变"""
        self.plotter.use_ray_march = self.ray_march_var.get()
        if self.fractal_var.get() in ['mandelbulb', 'mandelbox']:
            self.plotter.render()
    
    def _on_reset_3d_view(self):
        """重置3D视角"""
        if self.fractal_var.get() == 'mandelbulb':
            self.plotter.mandelbulb_renderer.rotation_x = 0.3
            self.plotter.mandelbulb_renderer.rotation_y = 0.5
            self.plotter.mandelbulb_renderer.camera_distance = 3.0
        elif self.fractal_var.get() == 'mandelbox':
            self.plotter.mandelbox_renderer.rotation_x = 0.3
            self.plotter.mandelbox_renderer.rotation_y = 0.5
            self.plotter.mandelbox_renderer.camera_distance = 4.0
        self.plotter.render()
    
    def _on_auto_rotate(self):
        """自动旋转3D视图"""
        if not hasattr(self, '_auto_rotating') or not self._auto_rotating:
            self._auto_rotating = True
            self._auto_rotate_step()
        else:
            self._auto_rotating = False
    
    def _auto_rotate_step(self):
        """自动旋转步进"""
        if hasattr(self, '_auto_rotating') and self._auto_rotating:
            if self.fractal_var.get() == 'mandelbulb':
                self.plotter.mandelbulb_renderer.rotation_y += 0.02
                self.plotter.render()
            elif self.fractal_var.get() == 'mandelbox':
                self.plotter.mandelbox_renderer.rotation_y += 0.02
                self.plotter.render()
            self.after(50, self._auto_rotate_step)
    
    def _on_formula_validate(self, event=None):
        """验证公式"""
        formula = self.formula_var.get().strip()
        if not formula:
            self.formula_status_var.set('请输入公式')
            self.formula_status_label.config(foreground='orange')
            return
        
        valid, error = self.formula_editor.test_formula(formula)
        if valid:
            self.formula_status_var.set('✓ 公式有效')
            self.formula_status_label.config(foreground='lightgreen')
        else:
            self.formula_status_var.set(f'✗ {error}')
            self.formula_status_label.config(foreground='red')
    
    def _on_formula_apply(self, event=None):
        """应用公式"""
        formula = self.formula_var.get().strip()
        if not formula:
            self.formula_status_var.set('请输入公式')
            self.formula_status_label.config(foreground='orange')
            return
        
        valid, error = self.plotter.set_custom_formula(formula)
        if valid:
            self.formula_status_var.set('✓ 公式已应用')
            self.formula_status_label.config(foreground='lightgreen')
            self.formula_editor.apply_formula(formula)
            self._update_history_list()
            
            self.fractal_var.set('custom')
            self.plotter.set_fractal_type('custom')
        else:
            self.formula_status_var.set(f'✗ {error}')
            self.formula_status_label.config(foreground='red')
    
    def _on_formula_help(self):
        """显示公式语法帮助"""
        help_text = self.formula_editor.get_syntax_help()
        messagebox.showinfo('公式语法帮助', help_text)
    
    def _on_formula_category_change(self, event=None):
        """公式分类改变"""
        category = self.preset_category_var.get()
        categories = FormulaPresetLibrary.get_categories()
        if category in categories:
            self.preset_listbox.delete(0, 'end')
            for name, formula in categories[category]:
                self.preset_listbox.insert('end', f'{name}: {formula}')
    
    def _on_formula_preset_select(self, event=None):
        """选择公式预设"""
        selection = self.preset_listbox.curselection()
        if selection:
            category = self.preset_category_var.get()
            categories = FormulaPresetLibrary.get_categories()
            if category in categories:
                name, formula = categories[category][selection[0]]
                self.formula_var.set(formula)
                self._on_formula_apply()
    
    def _on_history_select(self, event=None):
        """选择历史公式"""
        selection = self.history_listbox.curselection()
        if selection:
            history = self.formula_editor.get_history()
            formula = history[selection[0]]
            self.formula_var.set(formula)
    
    def _update_history_list(self):
        """更新历史公式列表"""
        self.history_listbox.delete(0, 'end')
        for formula in reversed(self.formula_editor.get_history()):
            self.history_listbox.insert('end', formula)
    
    def _on_animation_play(self):
        """播放动画"""
        if self.current_animation is not None and self.current_animation.is_playing:
            return
        
        preset = self.anim_preset_var.get()
        duration = self.anim_duration_var.get()
        fps = self.anim_fps_var.get()
        
        if preset == 'julia_params':
            self.fractal_var.set('julia')
            self.plotter.set_fractal_type('julia')
            self.current_animation = PresetAnimations.create_julia_rotation(
                self.plotter,
                cx_start=-0.7, cx_end=-0.7,
                cy_start=-0.3, cy_end=0.3,
                duration=duration, fps=fps
            )
        elif preset == 'mandelbulb_spin':
            self.fractal_var.set('mandelbulb')
            self.plotter.set_fractal_type('mandelbulb')
            self.current_animation = PresetAnimations.create_mandelbulb_spin(
                self.plotter, duration=duration, fps=fps
            )
        elif preset == 'iteration_pulse':
            self.current_animation = PresetAnimations.create_iteration_pulse(
                self.plotter, min_iter=50, max_iter=500,
                duration=duration, fps=fps
            )
        
        if self.current_animation:
            self.anim_play_btn.config(state='disabled')
            self.anim_stop_btn.config(state='normal')
            
            def on_frame(frame, image):
                total = self.current_animation.total_frames
                progress = (frame / total) * 100 if total > 0 else 0
                self.anim_progress_var.set(progress)
                self.anim_frame_var.set(f'帧: {frame} / {total}')
                
                if hasattr(self.plotter, 'canvas') and self.plotter.canvas is not None:
                    self.plotter.canvas.draw_idle()
            
            def play_animation():
                self.current_animation.play(callback=on_frame, loop=True)
                
                if self.animation_thread and self.animation_thread.is_alive():
                    self.anim_play_btn.config(state='normal')
                    self.anim_stop_btn.config(state='disabled')
                    self.anim_progress_var.set(0)
                    self.anim_frame_var.set('帧: 0 / 0')
            
            self.animation_thread = threading.Thread(target=play_animation, daemon=True)
            self.animation_thread.start()
    
    def _on_animation_stop(self):
        """停止动画"""
        if self.current_animation:
            self.current_animation.stop()
        
        self.anim_play_btn.config(state='normal')
        self.anim_stop_btn.config(state='disabled')
        self.anim_progress_var.set(0)
        self.anim_frame_var.set('帧: 0 / 0')
    
    def _on_export_gif(self):
        """导出为GIF"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.gif',
            filetypes=[('GIF动画', '*.gif'), ('所有文件', '*.*')]
        )
        if filename and self.current_animation:
            try:
                def progress(current, total):
                    self.anim_progress_var.set((current / total) * 100)
                    self.anim_frame_var.set(f'导出: {current} / {total}')
                    self.root.update_idletasks()
                
                self.current_animation.export_gif(filename, progress_callback=progress)
                messagebox.showinfo('成功', f'动画已导出到:\n{filename}')
            except Exception as e:
                messagebox.showerror('错误', f'导出失败: {str(e)}')
    
    def _on_export_video(self):
        """导出为视频"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.mp4',
            filetypes=[('MP4视频', '*.mp4'), ('AVI视频', '*.avi'), ('所有文件', '*.*')]
        )
        if filename and self.current_animation:
            try:
                def progress(current, total):
                    self.anim_progress_var.set((current / total) * 100)
                    self.anim_frame_var.set(f'导出: {current} / {total}')
                    self.root.update_idletasks()
                
                self.current_animation.export_video(filename, progress_callback=progress)
                messagebox.showinfo('成功', f'视频已导出到:\n{filename}')
            except ImportError as e:
                messagebox.showerror('错误', '需要安装imageio库:\npip install imageio[ffmpeg]')
            except Exception as e:
                messagebox.showerror('错误', f'导出失败: {str(e)}')


class StatusBar(ttk.Frame):
    """状态栏"""
    
    def __init__(self, parent, plotter: FractalPlotter, **kwargs):
        super().__init__(parent, **kwargs)
        self.plotter = plotter
        self.configure(style='TFrame', height=25)
        
        self.status_var = tk.StringVar(value='就绪')
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor='w')
        self.status_label.pack(side='left', padx=10)
        
        self.info_var = tk.StringVar(value='')
        self.info_label = ttk.Label(self, textvariable=self.info_var, anchor='e')
        self.info_label.pack(side='right', padx=10)
        
        self.render_time_var = tk.StringVar(value='')
        self.render_time_label = ttk.Label(self, textvariable=self.render_time_var, anchor='e')
        self.render_time_label.pack(side='right', padx=20)
    
    def set_status(self, text: str):
        """设置状态文本"""
        self.status_var.set(text)
    
    def update_info(self):
        """更新状态信息"""
        info = self.plotter.get_status_info()
        
        if info.get('is_3d', False):
            rot_x = math.degrees(info['rotation_x'])
            rot_y = math.degrees(info['rotation_y'])
            info_text = (
                f"3D分形 | "
                f"旋转: ({rot_x:.0f}°, {rot_y:.0f}°) | "
                f"距离: {info['camera_distance']:.2f} | "
                f"迭代: {info['max_iter']}"
            )
        else:
            info_text = (
                f"缩放: {info['zoom']:.2e}× | "
                f"迭代: {info['max_iter']} | "
                f"中心: ({info['center_x']:.6e}, {info['center_y']:.6e})"
            )
            if info.get('using_high_precision', False):
                info_text += ' | 高精度: 开启'
        
        self.info_var.set(info_text)
    
    def set_render_time(self, time_ms: float):
        """设置渲染时间"""
        self.render_time_var.set(f'渲染: {time_ms:.1f}ms')


class FractalGeneratorApp:
    """分形生成器主应用"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('分形生成器 - Fractal Generator')
        self.root.geometry('1280x800')
        self.root.configure(bg='#1a1a1a')
        
        self._setup_keyboard_shortcuts()
        
        self.plotter = FractalPlotter(width=800, height=600)
        
        self._build_layout()
        
        self.plotter.zoom_callback = self._on_plotter_zoom
        self.plotter.pan_callback = self._on_plotter_pan
        self.plotter.update_callback = self._on_plotter_update
        
        self.root.after(100, self._initial_render)
        self.root.after(200, self._init_formula_categories)
    
    def _setup_keyboard_shortcuts(self):
        """设置键盘快捷键"""
        self.root.bind('<KeyPress-r>', lambda e: self.control_panel._on_reset_view())
        self.root.bind('<KeyPress-R>', lambda e: self.control_panel._on_reset_view())
        self.root.bind('<space>', lambda e: self.control_panel._on_render())
        self.root.bind('<KeyPress-s>', lambda e: self.control_panel._on_save_image())
        self.root.bind('<KeyPress-S>', lambda e: self.control_panel._on_save_image())
    
    def _build_layout(self):
        """构建主布局"""
        main_paned = tk.PanedWindow(self.root, orient='horizontal',
                                   bg='#1a1a1a', sashwidth=4, sashrelief='flat')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        left_frame = ttk.Frame(main_paned, style='TFrame', width=380)
        main_paned.add(left_frame, minsize=300)
        
        self.control_panel = ControlPanel(left_frame, self.plotter)
        self.control_panel.pack(fill='both', expand=True)
        
        right_frame = ttk.Frame(main_paned, style='TFrame')
        main_paned.add(right_frame, minsize=500)
        
        plot_container = ttk.Frame(right_frame, style='TFrame')
        plot_container.pack(fill='both', expand=True)
        
        self.plotter.parent = plot_container
        self.plotter._setup_figure()
        self.plotter.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.plotter.toolbar.pack(fill='x')
        
        self.status_bar = StatusBar(right_frame, self.plotter)
        self.status_bar.pack(fill='x', side='bottom')
        
        main_paned.sash_place(0, 380, 0)
    
    def _initial_render(self):
        """初始渲染"""
        self.status_bar.set_status('正在渲染...')
        self.root.update()
        
        start_time = time.perf_counter()
        self.plotter.render()
        render_time = (time.perf_counter() - start_time) * 1000
        
        self.status_bar.set_render_time(render_time)
        self.status_bar.update_info()
        self.status_bar.set_status('就绪')
    
    def _init_formula_categories(self):
        """初始化公式分类列表"""
        self.control_panel._on_formula_category_change()
    
    def _on_plotter_zoom(self, zoom: float, cx: float, cy: float):
        """缩放回调"""
        self.control_panel.update_from_plotter()
        self.status_bar.set_status(f'缩放中... ({zoom:.2e}×)')
        self.root.update_idletasks()
    
    def _on_plotter_pan(self, cx: float, cy: float):
        """平移回调"""
        self.control_panel.update_from_plotter()
    
    def _on_plotter_update(self):
        """更新回调"""
        self.status_bar.update_info()
        
        if hasattr(self, '_last_render_start'):
            render_time = (time.perf_counter() - self._last_render_start) * 1000
            self.status_bar.set_render_time(render_time)
            self.status_bar.set_status('就绪')
    
    def run(self):
        """运行应用"""
        self.root.mainloop()
