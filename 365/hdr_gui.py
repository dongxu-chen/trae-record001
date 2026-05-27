import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import cv2
import os
from typing import List, Tuple, Optional
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import cm
import matplotlib.pyplot as plt

from hdr_core import (
    compute_response_curve,
    create_hdr,
    tone_map,
    align_images,
    CameraResponseCalculator,
    HDRComposer,
    ToneMapper,
    ImageAligner,
    GhostRemoval,
    AdaptiveHDRComposer,
    ResponseCurveLibrary,
    get_response_curve_library
)


class ImageListItem:
    def __init__(self, filepath: str, exposure_time: float):
        self.filepath = filepath
        self.exposure_time = exposure_time
        self.image: Optional[np.ndarray] = None
        self.aligned_image: Optional[np.ndarray] = None
    
    def load(self) -> np.ndarray:
        if self.image is None:
            self.image = cv2.imread(self.filepath)
            if self.image is None:
                raise ValueError(f"无法加载图像: {self.filepath}")
        return self.image


class HDRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("HDR 图像合成工具 (高级版)")
        self.root.geometry("1500x950")
        
        self.image_list: List[ImageListItem] = []
        self.response_curves: Optional[List[np.ndarray]] = None
        self.hdr_image: Optional[np.ndarray] = None
        self.tonemapped_image: Optional[np.ndarray] = None
        self.aligned_images: Optional[List[np.ndarray]] = None
        self.ghost_masks: Optional[List[np.ndarray]] = None
        self.cleaned_images: Optional[List[np.ndarray]] = None
        self.weight_maps: Optional[List[np.ndarray]] = None
        
        self.use_alignment = tk.BooleanVar(value=False)
        self.use_ghost_removal = tk.BooleanVar(value=False)
        self.use_adaptive = tk.BooleanVar(value=False)
        self.use_curve_library = tk.BooleanVar(value=False)
        
        self.curve_library = get_response_curve_library()
        
        self._setup_style()
        self._create_widgets()
    
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=6, font=('Arial', 10))
        style.configure('TLabel', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('TNotebook', font=('Arial', 10))
        style.configure('Highlight.Horizontal.TProgressbar', 
                        troughcolor='gray', background='#4CAF50')
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        self._create_control_panel(main_frame)
        self._create_display_panel(main_frame)
    
    def _create_control_panel(self, parent: ttk.Frame):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        control_frame = ttk.Frame(canvas, padding="5")
        
        control_frame.bind('<Configure>', 
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=control_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=0, sticky=(tk.N, tk.E, tk.S))
        
        self._build_image_list_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_exposure_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_alignment_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_ghost_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_curve_library_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_hdr_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_tonemap_section(control_frame)
        ttk.Separator(control_frame).pack(fill=tk.X, pady=8)
        self._build_save_section(control_frame)
    
    def _build_image_list_section(self, parent):
        ttk.Label(parent, text="图像列表", style='Header.TLabel').pack(pady=(0, 5))
        
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.X, pady=5)
        
        self.image_tree = ttk.Treeview(list_frame, columns=('file', 'exposure'), 
                                       show='headings', height=8)
        self.image_tree.heading('file', text='文件')
        self.image_tree.heading('exposure', text='曝光 (s)')
        self.image_tree.column('file', width=140)
        self.image_tree.column('exposure', width=80)
        self.image_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                   command=self.image_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_tree.configure(yscrollcommand=tree_scroll.set)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="添加图像", command=self.add_images).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="移除选中", command=self.remove_selected).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_list).pack(fill=tk.X, pady=2)
    
    def _build_exposure_section(self, parent):
        ttk.Label(parent, text="曝光时间设置", style='Header.TLabel').pack(pady=(0, 5))
        
        exp_frame = ttk.Frame(parent)
        exp_frame.pack(fill=tk.X, pady=5)
        ttk.Label(exp_frame, text="曝光:").pack(side=tk.LEFT)
        self.exp_var = tk.StringVar(value="1/1000")
        ttk.Entry(exp_frame, textvariable=self.exp_var, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(exp_frame, text="应用", command=self.apply_exposure).pack(side=tk.LEFT)
        
        ttk.Label(parent, text="自动递增设置:").pack(pady=(5, 2))
        auto_frame = ttk.Frame(parent)
        auto_frame.pack(fill=tk.X, pady=2)
        ttk.Label(auto_frame, text="起:").pack(side=tk.LEFT)
        self.start_exp_var = tk.StringVar(value="1/1000")
        ttk.Entry(auto_frame, textvariable=self.start_exp_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(auto_frame, text="步:").pack(side=tk.LEFT)
        self.step_var = tk.StringVar(value="2")
        ttk.Entry(auto_frame, textvariable=self.step_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(auto_frame, text="设置", command=self.auto_set_exposures).pack(side=tk.LEFT, padx=5)
    
    def _build_alignment_section(self, parent):
        ttk.Label(parent, text="SIFT 图像配准", style='Header.TLabel').pack(pady=(0, 5))
        
        ttk.Checkbutton(parent, text="启用 SIFT 图像配准 (消除重影)",
                       variable=self.use_alignment).pack(anchor=tk.W, pady=2)
        
        align_frame = ttk.Frame(parent)
        align_frame.pack(fill=tk.X, pady=5)
        ttk.Label(align_frame, text="参考图索引:").pack(side=tk.LEFT)
        self.ref_idx_var = tk.StringVar(value="0")
        ttk.Entry(align_frame, textvariable=self.ref_idx_var, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(align_frame, text="特征点:").pack(side=tk.LEFT)
        self.max_feat_var = tk.StringVar(value="5000")
        ttk.Entry(align_frame, textvariable=self.max_feat_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(parent, text="执行配准", 
                   command=self.run_alignment).pack(fill=tk.X, pady=5)
    
    def _build_ghost_section(self, parent):
        ttk.Label(parent, text="鬼影检测与移除", style='Header.TLabel').pack(pady=(0, 5))
        
        ttk.Checkbutton(parent, text="启用鬼影移除 (运动物体检测)",
                       variable=self.use_ghost_removal).pack(anchor=tk.W, pady=2)
        
        param_grid = ttk.Frame(parent)
        param_grid.pack(fill=tk.X, pady=5)
        
        ttk.Label(param_grid, text="差异阈值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ghost_thresh_var = tk.StringVar(value="30")
        ttk.Entry(param_grid, textvariable=self.ghost_thresh_var, width=8).grid(row=0, column=1, pady=2)
        
        ttk.Label(param_grid, text="最小区域:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.min_ghost_var = tk.StringVar(value="100")
        ttk.Entry(param_grid, textvariable=self.min_ghost_var, width=8).grid(row=0, column=3, pady=2)
        
        ttk.Label(param_grid, text="形态学核:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.morph_ksize_var = tk.StringVar(value="5")
        ttk.Entry(param_grid, textvariable=self.morph_ksize_var, width=8).grid(row=1, column=1, pady=2)
        
        ttk.Label(param_grid, text="膨胀次数:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.dilate_iter_var = tk.StringVar(value="2")
        ttk.Entry(param_grid, textvariable=self.dilate_iter_var, width=8).grid(row=1, column=3, pady=2)
        
        ttk.Button(parent, text="检测鬼影",
                   command=self.detect_ghosts).pack(fill=tk.X, pady=3)
        ttk.Button(parent, text="移除鬼影",
                   command=self.remove_ghosts).pack(fill=tk.X, pady=3)
    
    def _build_curve_library_section(self, parent):
        ttk.Label(parent, text="响应曲线库", style='Header.TLabel').pack(pady=(0, 5))
        
        ttk.Checkbutton(parent, text="使用预设响应曲线",
                       variable=self.use_curve_library).pack(anchor=tk.W, pady=2)
        
        curve_frame = ttk.Frame(parent)
        curve_frame.pack(fill=tk.X, pady=5)
        ttk.Label(curve_frame, text="曲线类型:").pack(side=tk.LEFT)
        self.curve_type_var = tk.StringVar(value="sRGB")
        curve_combo = ttk.Combobox(curve_frame, textvariable=self.curve_type_var,
                                   values=self.curve_library.list_curves(),
                                   state="readonly", width=12)
        curve_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(parent, text="应用曲线",
                   command=self.apply_curve_from_library).pack(fill=tk.X, pady=3)
        ttk.Button(parent, text="匹配最佳曲线",
                   command=self.match_best_curve).pack(fill=tk.X, pady=3)
    
    def _build_hdr_section(self, parent):
        ttk.Label(parent, text="HDR 合成 (加权最小二乘 + 自适应)", style='Header.TLabel').pack(pady=(0, 5))
        
        ttk.Checkbutton(parent, text="启用亮度自适应合成",
                       variable=self.use_adaptive).pack(anchor=tk.W, pady=2)
        
        adaptive_grid = ttk.Frame(parent)
        adaptive_grid.pack(fill=tk.X, pady=5)
        
        ttk.Label(adaptive_grid, text="块大小:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.block_size_var = tk.StringVar(value="32")
        ttk.Entry(adaptive_grid, textvariable=self.block_size_var, width=8).grid(row=0, column=1, pady=2)
        
        ttk.Label(adaptive_grid, text="重叠:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.overlap_var = tk.StringVar(value="16")
        ttk.Entry(adaptive_grid, textvariable=self.overlap_var, width=8).grid(row=0, column=3, pady=2)
        
        ttk.Label(adaptive_grid, text="对比度权:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.contrast_w_var = tk.StringVar(value="1.0")
        ttk.Entry(adaptive_grid, textvariable=self.contrast_w_var, width=8).grid(row=1, column=1, pady=2)
        
        ttk.Label(adaptive_grid, text="饱和度权:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.sat_w_var = tk.StringVar(value="1.0")
        ttk.Entry(adaptive_grid, textvariable=self.sat_w_var, width=8).grid(row=1, column=3, pady=2)
        
        ttk.Label(adaptive_grid, text="曝光质量权:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.well_exp_w_var = tk.StringVar(value="1.0")
        ttk.Entry(adaptive_grid, textvariable=self.well_exp_w_var, width=8).grid(row=2, column=1, pady=2)
        
        param_grid = ttk.Frame(parent)
        param_grid.pack(fill=tk.X, pady=5)
        
        ttk.Label(param_grid, text="采样点:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.samples_var = tk.StringVar(value="100")
        ttk.Entry(param_grid, textvariable=self.samples_var, width=8).grid(row=0, column=1, pady=2)
        
        ttk.Label(param_grid, text="平滑度:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.smooth_var = tk.StringVar(value="100")
        ttk.Entry(param_grid, textvariable=self.smooth_var, width=8).grid(row=0, column=3, pady=2)
        
        ttk.Label(param_grid, text="正则化 λ:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.reg_var = tk.StringVar(value="1.0")
        ttk.Entry(param_grid, textvariable=self.reg_var, width=8).grid(row=1, column=1, pady=2)
        
        ttk.Label(param_grid, text="迭代次数:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.iter_var = tk.StringVar(value="10")
        ttk.Entry(param_grid, textvariable=self.iter_var, width=8).grid(row=1, column=3, pady=2)
        
        ttk.Button(parent, text="计算响应曲线",
                   command=self.calculate_response).pack(fill=tk.X, pady=3)
        ttk.Button(parent, text="合成 HDR 图像",
                   command=self.compose_hdr).pack(fill=tk.X, pady=3)
    
    def _build_tonemap_section(self, parent):
        ttk.Label(parent, text="色调映射 (含高光压缩)", style='Header.TLabel').pack(pady=(0, 5))
        
        method_frame = ttk.Frame(parent)
        method_frame.pack(fill=tk.X, pady=2)
        ttk.Label(method_frame, text="方法:").pack(side=tk.LEFT)
        self.tone_method = tk.StringVar(value="reinhard")
        method_combo = ttk.Combobox(method_frame, textvariable=self.tone_method,
                                    values=["reinhard", "filmic", "gamma"], 
                                    state="readonly", width=12)
        method_combo.pack(side=tk.LEFT, padx=5)
        method_combo.bind('<<ComboboxSelected>>', self._on_method_change)
        
        self.param_frame = ttk.LabelFrame(parent, text="参数")
        self.param_frame.pack(fill=tk.X, pady=5)
        
        self.param_widgets = {}
        self._create_param_widgets(self.param_frame)
        
        ttk.Button(parent, text="应用色调映射",
                   command=self.apply_tonemap).pack(fill=tk.X, pady=5)
    
    def _build_save_section(self, parent):
        ttk.Label(parent, text="保存", style='Header.TLabel').pack(pady=(0, 5))
        ttk.Button(parent, text="保存 HDR (.hdr)",
                   command=self.save_hdr).pack(fill=tk.X, pady=2)
        ttk.Button(parent, text="保存 LDR (.png)",
                   command=self.save_ldr).pack(fill=tk.X, pady=2)
        ttk.Button(parent, text="保存响应曲线图",
                   command=self.save_response_plot).pack(fill=tk.X, pady=2)
    
    def _create_param_widgets(self, parent: ttk.Frame):
        for widget in parent.winfo_children():
            widget.destroy()
        
        method = self.tone_method.get()
        
        row = 0
        
        if method == "reinhard":
            ttk.Label(parent, text="Key:").grid(row=row, column=0, sticky=tk.W, pady=2)
            key_var = tk.StringVar(value="0.18")
            ttk.Entry(parent, textvariable=key_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['key'] = key_var
            row += 1
            
            ttk.Label(parent, text="White:").grid(row=row, column=0, sticky=tk.W, pady=2)
            white_var = tk.StringVar(value="")
            ttk.Entry(parent, textvariable=white_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['white'] = white_var
            row += 1
            
            ttk.Label(parent, text="高光强度:").grid(row=row, column=0, sticky=tk.W, pady=2)
            hc_var = tk.StringVar(value="0.3")
            ttk.Entry(parent, textvariable=hc_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_compression'] = hc_var
            row += 1
            
            ttk.Label(parent, text="高光阈值:").grid(row=row, column=0, sticky=tk.W, pady=2)
            ht_var = tk.StringVar(value="0.8")
            ttk.Entry(parent, textvariable=ht_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_threshold'] = ht_var
        
        elif method == "filmic":
            ttk.Label(parent, text="曝光:").grid(row=row, column=0, sticky=tk.W, pady=2)
            exp_var = tk.StringVar(value="1.0")
            ttk.Entry(parent, textvariable=exp_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['exposure'] = exp_var
            row += 1
            
            ttk.Label(parent, text="对比度:").grid(row=row, column=0, sticky=tk.W, pady=2)
            contrast_var = tk.StringVar(value="1.0")
            ttk.Entry(parent, textvariable=contrast_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['contrast'] = contrast_var
            row += 1
            
            ttk.Label(parent, text="饱和度:").grid(row=row, column=0, sticky=tk.W, pady=2)
            sat_var = tk.StringVar(value="1.0")
            ttk.Entry(parent, textvariable=sat_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['saturation'] = sat_var
            row += 1
            
            ttk.Label(parent, text="高光强度:").grid(row=row, column=0, sticky=tk.W, pady=2)
            hc_var = tk.StringVar(value="0.4")
            ttk.Entry(parent, textvariable=hc_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_compression'] = hc_var
            row += 1
            
            ttk.Label(parent, text="高光阈值:").grid(row=row, column=0, sticky=tk.W, pady=2)
            ht_var = tk.StringVar(value="0.85")
            ttk.Entry(parent, textvariable=ht_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_threshold'] = ht_var
        
        elif method == "gamma":
            ttk.Label(parent, text="Gamma:").grid(row=row, column=0, sticky=tk.W, pady=2)
            gamma_var = tk.StringVar(value="2.2")
            ttk.Entry(parent, textvariable=gamma_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['gamma'] = gamma_var
            row += 1
            
            ttk.Label(parent, text="高光强度:").grid(row=row, column=0, sticky=tk.W, pady=2)
            hc_var = tk.StringVar(value="0.2")
            ttk.Entry(parent, textvariable=hc_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_compression'] = hc_var
            row += 1
            
            ttk.Label(parent, text="高光阈值:").grid(row=row, column=0, sticky=tk.W, pady=2)
            ht_var = tk.StringVar(value="0.8")
            ttk.Entry(parent, textvariable=ht_var, width=10).grid(row=row, column=1, pady=2)
            self.param_widgets['highlight_threshold'] = ht_var
    
    def _on_method_change(self, event):
        self._create_param_widgets(self.param_frame)
    
    def _create_display_panel(self, parent: ttk.Frame):
        display_frame = ttk.Frame(parent, padding="5")
        display_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)
        
        self.notebook = ttk.Notebook(display_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self._create_input_tab()
        self._create_alignment_tab()
        self._create_ghost_tab()
        self._create_response_tab()
        self._create_weight_tab()
        self._create_hdr_tab()
        self._create_result_tab()
    
    def _create_input_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="输入图像")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.input_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.input_canvas.draw()
        self.input_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.input_canvas, tab)
        toolbar.update()
        self.input_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.input_fig = fig
    
    def _create_alignment_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="配准结果")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.align_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.align_canvas.draw()
        self.align_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.align_canvas, tab)
        toolbar.update()
        self.align_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.align_fig = fig
    
    def _create_ghost_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="鬼影检测")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.ghost_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.ghost_canvas.draw()
        self.ghost_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.ghost_canvas, tab)
        toolbar.update()
        self.ghost_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.ghost_fig = fig
    
    def _create_response_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="响应曲线")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.response_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.response_canvas.draw()
        self.response_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.response_canvas, tab)
        toolbar.update()
        self.response_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.response_fig = fig
    
    def _create_weight_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="权重图")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.weight_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.weight_canvas.draw()
        self.weight_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.weight_canvas, tab)
        toolbar.update()
        self.weight_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.weight_fig = fig
    
    def _create_hdr_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HDR 预览")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.hdr_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.hdr_canvas.draw()
        self.hdr_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.hdr_canvas, tab)
        toolbar.update()
        self.hdr_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.hdr_fig = fig
    
    def _create_result_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="色调映射结果")
        
        fig = Figure(figsize=(8, 6), dpi=100)
        self.result_canvas = FigureCanvasTkAgg(fig, master=tab)
        self.result_canvas.draw()
        self.result_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.result_canvas, tab)
        toolbar.update()
        self.result_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.result_fig = fig
    
    def _parse_exposure(self, exp_str: str) -> float:
        exp_str = exp_str.strip()
        if '/' in exp_str:
            parts = exp_str.split('/')
            return float(parts[0]) / float(parts[1])
        return float(exp_str)
    
    def add_images(self):
        files = filedialog.askopenfilenames(
            title="选择图像文件",
            filetypes=[("图像文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"), ("所有文件", "*.*")]
        )
        
        for file in files:
            exp = 1.0 / 1000
            item = ImageListItem(file, exp)
            self.image_list.append(item)
            self.image_tree.insert('', tk.END, values=(os.path.basename(file), f"{exp:.6f}"))
        
        if files:
            self._update_input_display()
    
    def remove_selected(self):
        selection = self.image_tree.selection()
        if not selection:
            return
        
        indices = []
        for sel in selection:
            idx = self.image_tree.index(sel)
            indices.append(idx)
        
        for idx in sorted(indices, reverse=True):
            del self.image_list[idx]
            self.image_tree.delete(selection[indices.index(idx)])
        
        self._update_input_display()
    
    def clear_list(self):
        self.image_list.clear()
        self.image_tree.delete(*self.image_tree.get_children())
        self.hdr_image = None
        self.tonemapped_image = None
        self.response_curves = None
        self.aligned_images = None
        self._update_input_display()
    
    def apply_exposure(self):
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择图像")
            return
        
        try:
            exp = self._parse_exposure(self.exp_var.get())
            for sel in selection:
                idx = self.image_tree.index(sel)
                self.image_list[idx].exposure_time = exp
                self.image_tree.item(sel, values=(self.image_tree.item(sel, 'values')[0], f"{exp:.6f}"))
        except ValueError:
            messagebox.showerror("错误", "无效的曝光时间格式")
    
    def auto_set_exposures(self):
        if not self.image_list:
            messagebox.showwarning("警告", "图像列表为空")
            return
        
        try:
            start = self._parse_exposure(self.start_exp_var.get())
            step = float(self.step_var.get())
            
            for i, item in enumerate(self.image_list):
                exp = start * (step ** i)
                item.exposure_time = exp
            
            self._refresh_tree()
        except ValueError:
            messagebox.showerror("错误", "无效的参数格式")
    
    def _refresh_tree(self):
        self.image_tree.delete(*self.image_tree.get_children())
        for item in self.image_list:
            self.image_tree.insert('', tk.END, values=(
                os.path.basename(item.filepath), 
                f"{item.exposure_time:.6f}"
            ))
    
    def _get_images_and_exposures(self) -> Tuple[List[np.ndarray], np.ndarray]:
        if len(self.image_list) < 2:
            raise ValueError("至少需要2张图像")
        
        images = []
        exposures = []
        
        for item in self.image_list:
            img = item.load()
            if img is None:
                raise ValueError(f"无法加载图像: {item.filepath}")
            images.append(img)
            exposures.append(item.exposure_time)
        
        return images, np.array(exposures, dtype=np.float64)
    
    def run_alignment(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            ref_idx = int(self.ref_idx_var.get())
            ref_idx = max(0, min(ref_idx, len(images) - 1))
            max_features = int(self.max_feat_var.get())
            
            aligner = ImageAligner(max_features=max_features)
            self.aligned_images = aligner.align_images(images, ref_idx)
            
            for i, item in enumerate(self.image_list):
                item.aligned_image = self.aligned_images[i]
            
            self._plot_alignment_results()
            messagebox.showinfo("完成", "SIFT 图像配准完成")
            self.notebook.select(1)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def _plot_alignment_results(self):
        self.align_fig.clear()
        
        if self.aligned_images is None or len(self.aligned_images) == 0:
            return
        
        n = len(self.aligned_images)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        
        for i, (aligned, item) in enumerate(zip(self.aligned_images, self.image_list)):
            ax = self.align_fig.add_subplot(rows, cols, i + 1)
            img_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
            ax.imshow(img_rgb)
            ax.set_title(f"{os.path.basename(item.filepath)}\n已配准")
            ax.axis('off')
        
        self.align_fig.tight_layout()
        self.align_canvas.draw()
    
    def detect_ghosts(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            if self.aligned_images is not None:
                images = self.aligned_images
            
            threshold = float(self.ghost_thresh_var.get())
            min_ghost_size = int(self.min_ghost_var.get())
            morph_ksize = int(self.morph_ksize_var.get())
            dilate_iter = int(self.dilate_iter_var.get())
            
            ghost_remover = GhostRemoval(
                threshold=threshold,
                min_ghost_size=min_ghost_size,
                morph_kernel_size=morph_ksize,
                dilation_iterations=dilate_iter
            )
            
            self.ghost_masks = ghost_remover.detect_ghosts(images, reference_idx=0)
            
            self._plot_ghost_masks()
            messagebox.showinfo("完成", "鬼影检测完成")
            self.notebook.select(2)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def remove_ghosts(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            if self.aligned_images is not None:
                images = self.aligned_images
            
            threshold = float(self.ghost_thresh_var.get())
            min_ghost_size = int(self.min_ghost_var.get())
            morph_ksize = int(self.morph_ksize_var.get())
            dilate_iter = int(self.dilate_iter_var.get())
            
            ghost_remover = GhostRemoval(
                threshold=threshold,
                min_ghost_size=min_ghost_size,
                morph_kernel_size=morph_ksize,
                dilation_iterations=dilate_iter
            )
            
            self.cleaned_images, self.ghost_masks = ghost_remover.detect_and_remove(
                images, exposures, reference_idx=0
            )
            
            self._plot_cleaned_images()
            messagebox.showinfo("完成", "鬼影移除完成")
            self.notebook.select(2)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def _plot_ghost_masks(self):
        self.ghost_fig.clear()
        
        if self.ghost_masks is None:
            return
        
        n = len(self.ghost_masks)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        
        for i, (mask, item) in enumerate(zip(self.ghost_masks, self.image_list)):
            ax = self.ghost_fig.add_subplot(rows, cols, i + 1)
            ax.imshow(mask, cmap='Reds')
            ax.set_title(f"{os.path.basename(item.filepath)}\n鬼影掩码")
            ax.axis('off')
        
        self.ghost_fig.tight_layout()
        self.ghost_canvas.draw()
    
    def _plot_cleaned_images(self):
        self.ghost_fig.clear()
        
        if self.cleaned_images is None:
            return
        
        n = len(self.cleaned_images)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        
        for i, (img, item) in enumerate(zip(self.cleaned_images, self.image_list)):
            ax = self.ghost_fig.add_subplot(rows, cols, i + 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            ax.imshow(img_rgb)
            ax.set_title(f"{os.path.basename(item.filepath)}\n已去鬼影")
            ax.axis('off')
        
        self.ghost_fig.tight_layout()
        self.ghost_canvas.draw()
    
    def apply_curve_from_library(self):
        try:
            curve_name = self.curve_type_var.get()
            num_channels = 3
            
            self.response_curves = self.curve_library.get_curves_for_rgb(curve_name)
            
            self._plot_response_curves()
            messagebox.showinfo("完成", f"已应用响应曲线: {curve_name}")
            self.notebook.select(3)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def match_best_curve(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            temp_curves = compute_response_curve(images, exposures)
            
            best_names = []
            best_dists = []
            
            for c in range(len(temp_curves)):
                name, dist = self.curve_library.match_curve(temp_curves[c])
                best_names.append(name)
                best_dists.append(dist)
            
            message = "最佳匹配曲线:\n"
            channel_names = ['Blue', 'Green', 'Red']
            for i, (name, dist) in enumerate(zip(best_names, best_dists)):
                message += f"  {channel_names[i]}: {name} (距离: {dist:.4f})\n"
            
            from collections import Counter
            name_counts = Counter(best_names)
            most_common = name_counts.most_common(1)[0][0]
            
            messagebox.showinfo("曲线匹配结果", message)
            
            if messagebox.askyesno("应用曲线", f"是否应用最常见的曲线 '{most_common}'?"):
                self.response_curves = self.curve_library.get_curves_for_rgb(most_common)
                self._plot_response_curves()
                self.notebook.select(3)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def calculate_response(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            num_samples = int(self.samples_var.get())
            smoothness = float(self.smooth_var.get())
            regularization = float(self.reg_var.get())
            max_iter = int(self.iter_var.get())
            
            calc = CameraResponseCalculator(
                num_samples=num_samples, smoothness=smoothness,
                regularization=regularization, max_iter=max_iter
            )
            num_channels = images[0].shape[2] if len(images[0].shape) == 3 else 1
            
            self.response_curves = []
            for c in range(num_channels):
                channel_images = [img[:, :, c] for img in images]
                g, _ = calc.solve_response_curve(channel_images, exposures)
                self.response_curves.append(g)
            
            self._plot_response_curves()
            messagebox.showinfo("完成", "响应曲线计算完成 (加权最小二乘)")
            self.notebook.select(2)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def compose_hdr(self):
        try:
            images, exposures = self._get_images_and_exposures()
            
            if self.use_alignment.get() and self.aligned_images is not None:
                images = self.aligned_images
            
            if self.use_ghost_removal.get():
                if self.cleaned_images is not None:
                    images = self.cleaned_images
                else:
                    threshold = float(self.ghost_thresh_var.get())
                    min_ghost_size = int(self.min_ghost_var.get())
                    ghost_remover = GhostRemoval(
                        threshold=threshold, min_ghost_size=min_ghost_size
                    )
                    images, self.ghost_masks = ghost_remover.detect_and_remove(
                        images, exposures, reference_idx=0
                    )
            
            if self.response_curves is None and not self.use_curve_library.get():
                self.calculate_response()
            
            if self.use_curve_library.get() and self.response_curves is None:
                curve_name = self.curve_type_var.get()
                self.response_curves = self.curve_library.get_curves_for_rgb(curve_name)
            
            if self.use_adaptive.get():
                block_size = int(self.block_size_var.get())
                overlap = int(self.overlap_var.get())
                contrast_w = float(self.contrast_w_var.get())
                sat_w = float(self.sat_w_var.get())
                well_exp_w = float(self.well_exp_w_var.get())
                
                composer = AdaptiveHDRComposer(
                    block_size=block_size, overlap=overlap,
                    contrast_weight=contrast_w, saturation_weight=sat_w,
                    well_exposedness_weight=well_exp_w
                )
                
                self.weight_maps = []
                for img in images:
                    self.weight_maps.append(composer.compute_weight_map(img))
                
                self._plot_weight_maps()
            else:
                composer = HDRComposer()
            
            self.hdr_image = composer.compose(images, exposures, self.response_curves)
            
            self._plot_hdr_preview()
            messagebox.showinfo("完成", "HDR 图像合成完成")
            
            if self.use_adaptive.get():
                self.notebook.select(4)
            else:
                self.notebook.select(5)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def _plot_weight_maps(self):
        self.weight_fig.clear()
        
        if self.weight_maps is None:
            return
        
        n = len(self.weight_maps)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        
        for i, (wm, item) in enumerate(zip(self.weight_maps, self.image_list)):
            ax = self.weight_fig.add_subplot(rows, cols, i + 1)
            im = ax.imshow(wm, cmap='hot')
            ax.set_title(f"{os.path.basename(item.filepath)}\n权重图")
            ax.axis('off')
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        self.weight_fig.tight_layout()
        self.weight_canvas.draw()
    
    def apply_tonemap(self):
        if self.hdr_image is None:
            messagebox.showwarning("警告", "请先生成 HDR 图像")
            return
        
        try:
            method = self.tone_method.get()
            kwargs = {}
            
            for key, var in self.param_widgets.items():
                val = var.get()
                if val.strip() == "":
                    continue
                try:
                    kwargs[key] = float(val)
                except ValueError:
                    continue
            
            self.tonemapped_image = tone_map(self.hdr_image, method, **kwargs)
            self._plot_result()
            self.notebook.select(6)
            
        except Exception as e:
            messagebox.showerror("错误", str(e))
    
    def _update_input_display(self):
        self.input_fig.clear()
        
        if not self.image_list:
            ax = self.input_fig.add_subplot(111)
            ax.text(0.5, 0.5, "请添加图像", ha='center', va='center', 
                    transform=ax.transAxes, fontsize=16)
            ax.axis('off')
            self.input_canvas.draw()
            return
        
        n = len(self.image_list)
        cols = min(3, n)
        rows = (n + cols - 1) // cols
        
        for i, item in enumerate(self.image_list):
            ax = self.input_fig.add_subplot(rows, cols, i + 1)
            img = cv2.cvtColor(item.load(), cv2.COLOR_BGR2RGB)
            ax.imshow(img)
            ax.set_title(f"{os.path.basename(item.filepath)}\nExp: {item.exposure_time:.4f}s")
            ax.axis('off')
        
        self.input_fig.tight_layout()
        self.input_canvas.draw()
    
    def _plot_response_curves(self):
        self.response_fig.clear()
        
        if self.response_curves is None:
            return
        
        colors = ['b', 'g', 'r'] if len(self.response_curves) == 3 else ['k']
        labels = ['Blue', 'Green', 'Red'] if len(self.response_curves) == 3 else ['Luminance']
        
        ax = self.response_fig.add_subplot(111)
        
        for i, (g, color, label) in enumerate(zip(self.response_curves, colors, labels)):
            ax.plot(np.arange(256), g, color=color, label=label, linewidth=2)
        
        ax.set_xlabel('像素值 Z', fontsize=12)
        ax.set_ylabel('log 曝光量 X', fontsize=12)
        ax.set_title('相机响应曲线 (加权最小二乘 + 正则化)', fontsize=13)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.response_fig.tight_layout()
        self.response_canvas.draw()
    
    def _plot_hdr_preview(self):
        self.hdr_fig.clear()
        
        if self.hdr_image is None:
            return
        
        hdr = self.hdr_image
        if len(hdr.shape) == 3:
            hdr_rgb = cv2.cvtColor(hdr, cv2.COLOR_BGR2RGB)
        else:
            hdr_rgb = hdr
        
        ax = self.hdr_fig.add_subplot(121)
        log_hdr = np.log(hdr_rgb + 1e-8)
        log_hdr_norm = (log_hdr - log_hdr.min()) / (log_hdr.max() - log_hdr.min() + 1e-8)
        ax.imshow(log_hdr_norm)
        ax.set_title('HDR 对数显示')
        ax.axis('off')
        
        ax2 = self.hdr_fig.add_subplot(122)
        lum = ToneMapper._compute_luminance(hdr)
        log_lum = np.log(lum + 1e-8)
        ax2.hist(log_lum.flatten(), bins=100, alpha=0.7, color='steelblue')
        ax2.set_title('亮度对数直方图')
        ax2.set_xlabel('log 亮度')
        ax2.set_ylabel('像素数')
        
        self.hdr_fig.tight_layout()
        self.hdr_canvas.draw()
    
    def _plot_result(self):
        self.result_fig.clear()
        
        if self.tonemapped_image is None:
            return
        
        img = self.tonemapped_image
        if len(img.shape) == 3:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = img
        
        ax = self.result_fig.add_subplot(121)
        ax.imshow(img_rgb)
        ax.set_title(f'色调映射结果 ({self.tone_method.get()} + 高光压缩)')
        ax.axis('off')
        
        ax2 = self.result_fig.add_subplot(122)
        if len(img.shape) == 3:
            for i, color in enumerate(['r', 'g', 'b']):
                ax2.hist(img[:, :, i].flatten(), bins=64, alpha=0.5, label=color, color=color)
        else:
            ax2.hist(img.flatten(), bins=64, alpha=0.7, color='gray')
        ax2.set_title('直方图')
        ax2.set_xlabel('像素值')
        ax2.set_ylabel('像素数')
        if len(img.shape) == 3:
            ax2.legend()
        
        self.result_fig.tight_layout()
        self.result_canvas.draw()
    
    def save_hdr(self):
        if self.hdr_image is None:
            messagebox.showwarning("警告", "没有可保存的 HDR 图像")
            return
        
        file = filedialog.asksaveasfilename(
            title="保存 HDR 图像",
            defaultextension=".hdr",
            filetypes=[("HDR 文件", "*.hdr"), ("Radiance HDR", "*.hdr")]
        )
        
        if file:
            cv2.imwrite(file, self.hdr_image)
            messagebox.showinfo("完成", f"HDR 图像已保存到:\n{file}")
    
    def save_ldr(self):
        if self.tonemapped_image is None:
            messagebox.showwarning("警告", "没有可保存的图像")
            return
        
        file = filedialog.asksaveasfilename(
            title="保存 LDR 图像",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("BMP 文件", "*.bmp")]
        )
        
        if file:
            cv2.imwrite(file, self.tonemapped_image)
            messagebox.showinfo("完成", f"图像已保存到:\n{file}")
    
    def save_response_plot(self):
        if self.response_curves is None:
            messagebox.showwarning("警告", "没有可保存的响应曲线")
            return
        
        file = filedialog.asksaveasfilename(
            title="保存响应曲线图",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("PDF 文件", "*.pdf")]
        )
        
        if file:
            self.response_fig.savefig(file, dpi=150, bbox_inches='tight')
            messagebox.showinfo("完成", f"响应曲线图已保存到:\n{file}")


def main():
    root = tk.Tk()
    app = HDRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
