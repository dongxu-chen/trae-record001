import numpy as np
import pywt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import os
import hashlib
from collections import Counter


class WaveletTransformApp:
    def __init__(self, root):
        self.root = root
        self.root.title("二维小波变换 DWT/IDWT 交互式演示系统")
        self.root.geometry("1500x1000")
        
        self.wavelet_list = ['haar', 'db2', 'sym2']
        self.wavelet_names = {'haar': 'Haar', 'db2': 'Daubechies 2 (Db2)', 'sym2': 'Symlet 2 (Sym2)'}
        self.boundary_modes = ['periodization', 'symmetric', 'reflect', 'constant']
        self.boundary_names = {
            'periodization': '周期延拓 (最低误差)',
            'symmetric': '对称延拓',
            'reflect': '反射延拓',
            'constant': '常数填充'
        }
        
        self.current_image = None
        self.original_image = None
        self.coeffs = None
        self.coeffs_original = None
        self.reconstructed = None
        self.level = 1
        self.wavelet = 'haar'
        self.boundary_mode = 'periodization'
        self.threshold_mode = 'soft'
        self.threshold_value = 0.1
        
        self.wp_coeffs = None
        self.wp_level = 2
        self.direction_features = None
        self.fingerprint_features = None
        self.fingerprint_database = []
        
        self._cache = {}
        self._cache_max_size = 10
        
        self.setup_ui()
        self.load_sample_image()
    
    def _get_cache_key(self, func_name, **kwargs):
        key_data = f"{func_name}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def _cache_get(self, key):
        if key in self._cache:
            return self._cache[key]
        return None
    
    def _cache_set(self, key, value):
        if len(self._cache) >= self._cache_max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value
    
    def _cache_clear(self):
        self._cache.clear()
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tab1 = ttk.Frame(notebook)
        tab2 = ttk.Frame(notebook)
        tab3 = ttk.Frame(notebook)
        
        notebook.add(tab1, text="  小波变换 DWT/IDWT  ")
        notebook.add(tab2, text="  小波包分解 & 方向分析  ")
        notebook.add(tab3, text="  指纹识别应用  ")
        
        self.setup_dwt_tab(tab1)
        self.setup_wp_tab(tab2)
        self.setup_fp_tab(tab3)
        
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def setup_dwt_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="小波基:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.wavelet_var = tk.StringVar(value='haar')
        wavelet_combo = ttk.Combobox(control_frame, textvariable=self.wavelet_var, 
                                      values=self.wavelet_list, state='readonly', width=15)
        wavelet_combo.grid(row=0, column=1, padx=5, pady=5)
        wavelet_combo.bind('<<ComboboxSelected>>', self.on_wavelet_change)
        
        ttk.Label(control_frame, text="边界模式:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.boundary_var = tk.StringVar(value='periodization')
        boundary_combo = ttk.Combobox(control_frame, textvariable=self.boundary_var,
                                       values=self.boundary_modes, state='readonly', width=20)
        boundary_combo.grid(row=0, column=3, padx=5, pady=5)
        boundary_combo.bind('<<ComboboxSelected>>', self.on_boundary_change)
        
        ttk.Label(control_frame, text="分解层数:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.level_var = tk.IntVar(value=1)
        level_spin = ttk.Spinbox(control_frame, from_=1, to=5, textvariable=self.level_var, width=10)
        level_spin.grid(row=0, column=5, padx=5, pady=5)
        level_spin.bind('<Return>', self.on_level_change)
        
        ttk.Button(control_frame, text="加载图片", command=self.load_image).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(control_frame, text="加载示例", command=self.load_sample_image).grid(row=0, column=7, padx=5, pady=5)
        ttk.Button(control_frame, text="执行DWT", command=self.perform_dwt).grid(row=0, column=8, padx=5, pady=5)
        ttk.Button(control_frame, text="执行IDWT", command=self.perform_idwt).grid(row=0, column=9, padx=5, pady=5)
        
        threshold_frame = ttk.LabelFrame(control_frame, text="自适应阈值去噪", padding="5")
        threshold_frame.grid(row=1, column=0, columnspan=10, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(threshold_frame, text="去噪模式:").grid(row=0, column=0, padx=5, pady=5)
        self.denoise_mode_var = tk.StringVar(value='bayes')
        denoise_combo = ttk.Combobox(threshold_frame, textvariable=self.denoise_mode_var,
                                      values=['bayes', 'sure', 'universal', 'manual'], 
                                      state='readonly', width=12)
        denoise_combo.grid(row=0, column=1, padx=5, pady=5)
        denoise_combo.bind('<<ComboboxSelected>>', self.on_denoise_mode_change)
        
        ttk.Label(threshold_frame, text="阈值类型:").grid(row=0, column=2, padx=5, pady=5)
        self.thresh_mode_var = tk.StringVar(value='soft')
        thresh_combo = ttk.Combobox(threshold_frame, textvariable=self.thresh_mode_var,
                                     values=['soft', 'hard'], state='readonly', width=10)
        thresh_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(threshold_frame, text="强度:").grid(row=0, column=4, padx=5, pady=5)
        self.thresh_value_var = tk.DoubleVar(value=1.0)
        thresh_scale = ttk.Scale(threshold_frame, from_=0.1, to=3.0, orient=tk.HORIZONTAL,
                                  variable=self.thresh_value_var, length=200, command=self.update_thresh_label)
        thresh_scale.grid(row=0, column=5, padx=5, pady=5)
        self.thresh_label = ttk.Label(threshold_frame, text="1.00x")
        self.thresh_label.grid(row=0, column=6, padx=5, pady=5)
        
        ttk.Button(threshold_frame, text="应用去噪", command=self.apply_denoise).grid(row=0, column=7, padx=5, pady=5)
        ttk.Button(threshold_frame, text="重置系数", command=self.reset_coeffs).grid(row=0, column=8, padx=5, pady=5)
        
        self.denoise_info_var = tk.StringVar(value="BayesShrink: 基于噪声估计的自适应贝叶斯阈值")
        info_label = ttk.Label(threshold_frame, textvariable=self.denoise_info_var, foreground="blue")
        info_label.grid(row=1, column=0, columnspan=10, padx=5, pady=5, sticky=tk.W)
        
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        self.figure = Figure(figsize=(14, 7), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.canvas, plot_frame)
        toolbar.update()
        toolbar.pack(fill=tk.X)
    
    def setup_wp_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.LabelFrame(main_frame, text="小波包分解控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="分解层数:").grid(row=0, column=0, padx=5, pady=5)
        self.wp_level_var = tk.IntVar(value=2)
        wp_level_spin = ttk.Spinbox(control_frame, from_=1, to=4, textvariable=self.wp_level_var, width=10)
        wp_level_spin.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="排序方式:").grid(row=0, column=2, padx=5, pady=5)
        self.wp_order_var = tk.StringVar(value='natural')
        order_combo = ttk.Combobox(control_frame, textvariable=self.wp_order_var,
                                    values=['natural', 'frequency'], state='readonly', width=15)
        order_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(control_frame, text="执行小波包分解", command=self.perform_wp_decompose).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(control_frame, text="重构图像", command=self.perform_wp_reconstruct).grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(control_frame, text="方向分析", command=self.analyze_direction).grid(row=0, column=6, padx=5, pady=5)
        
        direction_frame = ttk.LabelFrame(control_frame, text="方向性特征", padding="5")
        direction_frame.grid(row=1, column=0, columnspan=7, padx=5, pady=5, sticky=tk.EW)
        
        self.direction_info_var = tk.StringVar(value="执行方向分析以提取纹理特征")
        ttk.Label(direction_frame, textvariable=self.direction_info_var, foreground="darkgreen").grid(row=0, column=0, padx=5, pady=5)
        
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        self.wp_figure = Figure(figsize=(14, 7), dpi=100)
        self.wp_canvas = FigureCanvasTkAgg(self.wp_figure, master=plot_frame)
        self.wp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.wp_canvas, plot_frame)
        toolbar.update()
        toolbar.pack(fill=tk.X)
    
    def setup_fp_tab(self, parent):
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.LabelFrame(main_frame, text="指纹识别控制面板", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="特征提取层数:").grid(row=0, column=0, padx=5, pady=5)
        self.fp_level_var = tk.IntVar(value=3)
        fp_level_spin = ttk.Spinbox(control_frame, from_=1, to=5, textvariable=self.fp_level_var, width=10)
        fp_level_spin.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(control_frame, text="提取指纹特征", command=self.extract_fingerprint).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(control_frame, text="添加到数据库", command=self.add_to_database).grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(control_frame, text="生成示例指纹库", command=self.generate_sample_db).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(control_frame, text="清除数据库", command=self.clear_database).grid(row=0, column=5, padx=5, pady=5)
        
        match_frame = ttk.LabelFrame(control_frame, text="匹配结果", padding="5")
        match_frame.grid(row=1, column=0, columnspan=6, padx=5, pady=5, sticky=tk.EW)
        
        self.match_info_var = tk.StringVar(value="提取指纹特征后，自动与数据库进行匹配")
        ttk.Label(match_frame, textvariable=self.match_info_var, foreground="darkblue", font=('Arial', 10)).grid(row=0, column=0, padx=5, pady=5)
        
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fp_figure = Figure(figsize=(14, 7), dpi=100)
        self.fp_canvas = FigureCanvasTkAgg(self.fp_figure, master=plot_frame)
        self.fp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.fp_canvas, plot_frame)
        toolbar.update()
        toolbar.pack(fill=tk.X)
    
    def update_thresh_label(self, value):
        self.thresh_label.config(text=f"{float(value):.2f}x")
    
    def on_denoise_mode_change(self, event):
        mode = self.denoise_mode_var.get()
        info_texts = {
            'bayes': 'BayesShrink: 基于噪声估计的自适应贝叶斯阈值 (每层不同阈值)',
            'sure': 'SURE: Stein无偏风险估计阈值',
            'universal': '通用阈值: σ√(2logN)',
            'manual': '手动模式: 统一阈值滑块调节'
        }
        self.denoise_info_var.set(info_texts.get(mode, ''))
    
    def estimate_noise_sigma(self, coeffs, level_idx=None):
        cache_key = self._get_cache_key('noise_sigma', coeffs_hash=id(coeffs), level=level_idx)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
        if level_idx is None:
            detail_coeffs = []
            for i in range(1, len(coeffs)):
                cH, cV, cD = coeffs[i]
                detail_coeffs.append(cD.flatten())
            detail_coeffs = np.concatenate(detail_coeffs)
        else:
            cH, cV, cD = coeffs[level_idx]
            detail_coeffs = cD.flatten()
        
        sigma = np.median(np.abs(detail_coeffs)) / 0.6745
        self._cache_set(cache_key, sigma)
        return sigma
    
    def bayes_shrink_threshold(self, coeff, sigma):
        cache_key = self._get_cache_key('bayes_thresh', coeff_hash=id(coeff), sigma=sigma)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
        coeff_abs = np.abs(coeff)
        var_y = np.mean(coeff_abs**2)
        sigma_w = max(sigma**2, 0)
        var_signal = max(var_y - sigma_w, 0)
        
        if var_signal > 0:
            threshold = sigma_w / np.sqrt(var_signal)
        else:
            threshold = np.max(coeff_abs)
        
        threshold = min(threshold, np.max(coeff_abs))
        self._cache_set(cache_key, threshold)
        return threshold
    
    def sure_threshold(self, coeff, sigma):
        cache_key = self._get_cache_key('sure_thresh', coeff_hash=id(coeff), sigma=sigma)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        
        coeff_flat = coeff.flatten()
        n = len(coeff_flat)
        coeff_sorted = np.sort(np.abs(coeff_flat))**2
        
        risks = np.zeros(n)
        for i in range(n):
            t = coeff_sorted[i]
            mask = coeff_sorted <= t
            n_small = np.sum(mask)
            sum_small = np.sum(coeff_sorted[mask])
            risk = (n - 2 * n_small + sum_small + np.sum(np.minimum(coeff_sorted, t))) / n
            risks[i] = risk
        
        idx_min = np.argmin(risks)
        threshold = np.sqrt(coeff_sorted[idx_min])
        self._cache_set(cache_key, threshold)
        return threshold
    
    def universal_threshold(self, coeff, sigma):
        n = coeff.size
        return sigma * np.sqrt(2 * np.log(n))
    
    def load_sample_image(self):
        self._cache_clear()
        
        size = 256
        x = np.linspace(0, 4*np.pi, size)
        y = np.linspace(0, 4*np.pi, size)
        X, Y = np.meshgrid(x, y)
        
        clean = np.sin(X) * np.cos(Y) + 0.5 * np.sin(2*X) * np.cos(2*Y)
        noise = 0.3 * np.random.normal(0, 0.5, clean.shape)
        image = clean + noise
        
        image = (image - image.min()) / (image.max() - image.min())
        self.original_image = image
        self.current_image = image.copy()
        self.clean_image = (clean - clean.min()) / (clean.max() - clean.min())
        
        self.coeffs = None
        self.coeffs_original = None
        self.reconstructed = None
        self.wp_coeffs = None
        
        self.update_display()
        self.update_wp_display()
        self.update_fp_display()
        self.status_var.set("已加载示例图像 (256x256) - 含高斯噪声")
    
    def load_image(self):
        self._cache_clear()
        
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            try:
                img = Image.open(file_path).convert('L')
                img = img.resize((256, 256), Image.LANCZOS)
                image = np.array(img, dtype=np.float64) / 255.0
                
                self.original_image = image
                self.current_image = image.copy()
                self.clean_image = None
                
                self.coeffs = None
                self.coeffs_original = None
                self.reconstructed = None
                self.wp_coeffs = None
                
                self.update_display()
                self.update_wp_display()
                self.update_fp_display()
                self.status_var.set(f"已加载图片: {os.path.basename(file_path)} (256x256)")
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片: {str(e)}")
    
    def on_wavelet_change(self, event):
        self.wavelet = self.wavelet_var.get()
        self._cache_clear()
        if self.coeffs is not None:
            self.perform_dwt()
    
    def on_boundary_change(self, event):
        self.boundary_mode = self.boundary_var.get()
        self._cache_clear()
        if self.coeffs is not None:
            self.perform_dwt()
    
    def on_level_change(self, event):
        self.level = self.level_var.get()
        self._cache_clear()
        if self.coeffs is not None:
            self.perform_dwt()
    
    def perform_dwt(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "请先加载图像")
            return
        
        self.wavelet = self.wavelet_var.get()
        self.level = self.level_var.get()
        self.boundary_mode = self.boundary_var.get()
        
        try:
            self.coeffs = pywt.wavedec2(
                self.current_image, 
                wavelet=self.wavelet, 
                level=self.level,
                mode=self.boundary_mode
            )
            
            self.coeffs_original = [c if isinstance(c, np.ndarray) else tuple(x.copy() for x in c) 
                                    for c in self.coeffs]
            for i in range(len(self.coeffs_original)):
                if isinstance(self.coeffs_original[i], np.ndarray):
                    self.coeffs_original[i] = self.coeffs_original[i].copy()
            
            self.update_display()
            self.analyze_energy()
            
            boundary_name = self.boundary_names[self.boundary_mode]
            self.status_var.set(f"DWT分解完成 - {self.wavelet_names[self.wavelet]}, {self.level}层, {boundary_name}")
        except Exception as e:
            messagebox.showerror("错误", f"DWT分解失败: {str(e)}")
    
    def perform_idwt(self):
        if self.coeffs is None:
            messagebox.showwarning("警告", "请先执行DWT分解")
            return
        
        try:
            self.reconstructed = pywt.waverec2(
                self.coeffs, 
                wavelet=self.wavelet,
                mode=self.boundary_mode
            )
            self.reconstructed = np.clip(self.reconstructed, 0, 1)
            
            h, w = self.current_image.shape
            recon_display = self.reconstructed[:h, :w]
            
            mse = np.mean((self.current_image - recon_display)**2)
            psnr = 10 * np.log10(1.0 / mse) if mse > 0 else 100
            
            boundary_name = self.boundary_names[self.boundary_mode]
            self.status_var.set(f"IDWT重构完成 - MSE: {mse:.8f}, PSNR: {psnr:.2f} dB ({boundary_name})")
            
            self.update_display()
        except Exception as e:
            messagebox.showerror("错误", f"IDWT重构失败: {str(e)}")
    
    def apply_denoise(self):
        if self.coeffs is None or self.coeffs_original is None:
            messagebox.showwarning("警告", "请先执行DWT分解")
            return
        
        mode = self.denoise_mode_var.get()
        thresh_mode = self.thresh_mode_var.get()
        strength = self.thresh_value_var.get()
        
        try:
            denoised_coeffs = []
            denoised_coeffs.append(self.coeffs_original[0].copy())
            
            sigma_global = self.estimate_noise_sigma(self.coeffs_original)
            threshold_info = []
            
            for i in range(1, len(self.coeffs_original)):
                cH, cV, cD = self.coeffs_original[i]
                
                if mode == 'bayes':
                    sigma = self.estimate_noise_sigma(self.coeffs_original, i)
                    tH = self.bayes_shrink_threshold(cH, sigma) * strength
                    tV = self.bayes_shrink_threshold(cV, sigma) * strength
                    tD = self.bayes_shrink_threshold(cD, sigma) * strength
                elif mode == 'sure':
                    sigma = self.estimate_noise_sigma(self.coeffs_original, i)
                    tH = self.sure_threshold(cH, sigma) * strength
                    tV = self.sure_threshold(cV, sigma) * strength
                    tD = self.sure_threshold(cD, sigma) * strength
                elif mode == 'universal':
                    t = self.universal_threshold(cH, sigma_global) * strength
                    tH = tV = tD = t
                else:
                    max_val = max(np.max(np.abs(cH)), np.max(np.abs(cV)), np.max(np.abs(cD)))
                    t = strength * 0.1 * max_val
                    tH = tV = tD = t
                
                cH_denoised = pywt.threshold(cH, tH, mode=thresh_mode)
                cV_denoised = pywt.threshold(cV, tV, mode=thresh_mode)
                cD_denoised = pywt.threshold(cD, tD, mode=thresh_mode)
                
                denoised_coeffs.append((cH_denoised, cV_denoised, cD_denoised))
                threshold_info.append(f"L{i}: {tH:.4f}")
            
            self.coeffs = denoised_coeffs
            
            denoised = pywt.waverec2(self.coeffs, wavelet=self.wavelet, mode=self.boundary_mode)
            denoised = np.clip(denoised, 0, 1)
            h, w = self.original_image.shape
            self.current_image = denoised[:h, :w]
            
            if hasattr(self, 'clean_image') and self.clean_image is not None:
                denoised_clean = self.current_image[:self.clean_image.shape[0], :self.clean_image.shape[1]]
                rmse = np.sqrt(np.mean((self.clean_image - denoised_clean)**2))
                psnr_denoised = 10 * np.log10(1.0 / (rmse**2)) if rmse > 0 else 100
                self.status_var.set(f"去噪完成 - {mode.upper()} - RMSE: {rmse:.4f}, PSNR: {psnr_denoised:.2f} dB")
            else:
                self.status_var.set(f"去噪完成 - {mode.upper()} - 阈值: {', '.join(threshold_info)}")
            
            self.update_display()
            self.analyze_energy()
            
        except Exception as e:
            messagebox.showerror("错误", f"去噪失败: {str(e)}")
    
    def reset_coeffs(self):
        if self.coeffs_original is not None:
            self.coeffs = [c if isinstance(c, np.ndarray) else tuple(x.copy() for x in c) 
                          for c in self.coeffs_original]
            for i in range(len(self.coeffs)):
                if isinstance(self.coeffs[i], np.ndarray):
                    self.coeffs[i] = self.coeffs[i].copy()
            
            self.current_image = self.original_image.copy()
            self.reconstructed = None
            
            self.update_display()
            self.status_var.set("系数已重置")
    
    def analyze_energy(self):
        if self.coeffs is None:
            return
        
        cache_key = self._get_cache_key('energy', coeffs_hash=id(self.coeffs))
        cached = self._cache_get(cache_key)
        if cached is not None:
            self.energy_info = cached
            return cached
        
        energy_info = []
        total_energy = np.sum(self.original_image**2)
        
        cA = self.coeffs[0]
        approx_energy = np.sum(cA**2)
        energy_info.append(("近似系数", approx_energy, approx_energy/total_energy*100))
        
        for level in range(1, len(self.coeffs)):
            cH, cV, cD = self.coeffs[level]
            eH = np.sum(cH**2)
            eV = np.sum(cV**2)
            eD = np.sum(cD**2)
            
            energy_info.append((f"第{level}层 - 水平", eH, eH/total_energy*100))
            energy_info.append((f"第{level}层 - 垂直", eV, eV/total_energy*100))
            energy_info.append((f"第{level}层 - 对角", eD, eD/total_energy*100))
        
        self.energy_info = energy_info
        self._cache_set(cache_key, energy_info)
        return energy_info
    
    def perform_wp_decompose(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "请先加载图像")
            return
        
        self.wavelet = self.wavelet_var.get()
        self.wp_level = self.wp_level_var.get()
        self.boundary_mode = self.boundary_var.get()
        order = self.wp_order_var.get()
        
        try:
            wp = pywt.WaveletPacket2D(
                data=self.current_image,
                wavelet=self.wavelet,
                mode=self.boundary_mode,
                maxlevel=self.wp_level
            )
            
            self.wp_coeffs = wp
            self.update_wp_display()
            
            nodes = [node.path for node in wp.get_level(self.wp_level, order=order)]
            self.status_var.set(f"小波包分解完成 - {self.wp_level}层, {len(nodes)}个子带")
            
        except Exception as e:
            messagebox.showerror("错误", f"小波包分解失败: {str(e)}")
    
    def perform_wp_reconstruct(self):
        if self.wp_coeffs is None:
            messagebox.showwarning("警告", "请先执行小波包分解")
            return
        
        try:
            reconstructed = self.wp_coeffs.reconstruct(update=False)
            reconstructed = np.clip(reconstructed, 0, 1)
            
            h, w = self.original_image.shape
            self.wp_reconstructed = reconstructed[:h, :w]
            
            mse = np.mean((self.original_image - self.wp_reconstructed)**2)
            psnr = 10 * np.log10(1.0 / mse) if mse > 0 else 100
            
            self.update_wp_display()
            self.status_var.set(f"小波包重构完成 - MSE: {mse:.8f}, PSNR: {psnr:.2f} dB")
            
        except Exception as e:
            messagebox.showerror("错误", f"小波包重构失败: {str(e)}")
    
    def analyze_direction(self):
        if self.coeffs is None and self.wp_coeffs is None:
            messagebox.showwarning("警告", "请先执行DWT或小波包分解")
            return
        
        try:
            if self.wp_coeffs is not None:
                self._analyze_wp_direction()
            elif self.coeffs is not None:
                self._analyze_dwt_direction()
            
            self.update_wp_display()
            
        except Exception as e:
            messagebox.showerror("错误", f"方向分析失败: {str(e)}")
    
    def _analyze_dwt_direction(self):
        direction_energy = {'水平': 0, '垂直': 0, '对角': 0}
        total_detail = 0
        
        for level in range(1, len(self.coeffs)):
            cH, cV, cD = self.coeffs[level]
            eH = np.sum(cH**2)
            eV = np.sum(cV**2)
            eD = np.sum(cD**2)
            
            direction_energy['水平'] += eH
            direction_energy['垂直'] += eV
            direction_energy['对角'] += eD
            total_detail += eH + eV + eD
        
        if total_detail > 0:
            for key in direction_energy:
                direction_energy[key] = direction_energy[key] / total_detail * 100
        
        dominant = max(direction_energy, key=direction_energy.get)
        
        self.direction_features = {
            'energies': direction_energy,
            'dominant_direction': dominant,
            'total_detail_energy': total_detail
        }
        
        info = f"主导方向: {dominant} (水平: {direction_energy['水平']:.1f}%, "
        info += f"垂直: {direction_energy['垂直']:.1f}%, 对角: {direction_energy['对角']:.1f}%)"
        self.direction_info_var.set(info)
    
    def _analyze_wp_direction(self):
        order = self.wp_order_var.get()
        nodes = [node.path for node in self.wp_coeffs.get_level(self.wp_level, order=order)]
        
        direction_counts = Counter()
        direction_energy = {'水平': 0, '垂直': 0, '对角': 0}
        
        for node_path in nodes:
            coeff = self.wp_coeffs[node_path].data
            energy = np.sum(coeff**2)
            
            last_char = node_path[-1] if node_path else 'a'
            if last_char == 'h':
                direction_counts['水平'] += 1
                direction_energy['水平'] += energy
            elif last_char == 'v':
                direction_counts['垂直'] += 1
                direction_energy['垂直'] += energy
            elif last_char == 'd':
                direction_counts['对角'] += 1
                direction_energy['对角'] += energy
        
        total = sum(direction_energy.values())
        if total > 0:
            for key in direction_energy:
                direction_energy[key] = direction_energy[key] / total * 100
        
        dominant = max(direction_energy, key=direction_energy.get)
        
        self.direction_features = {
            'energies': direction_energy,
            'dominant_direction': dominant,
            'direction_counts': dict(direction_counts)
        }
        
        info = f"主导方向: {dominant} (水平: {direction_energy['水平']:.1f}%, "
        info += f"垂直: {direction_energy['垂直']:.1f}%, 对角: {direction_energy['对角']:.1f}%)"
        self.direction_info_var.set(info)
    
    def extract_fingerprint(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "请先加载图像")
            return
        
        self.wavelet = self.wavelet_var.get()
        level = self.fp_level_var.get()
        
        try:
            coeffs = pywt.wavedec2(
                self.current_image,
                wavelet=self.wavelet,
                level=level,
                mode=self.boundary_mode
            )
            
            features = []
            features.append(coeffs[0].flatten())
            
            for i in range(1, len(coeffs)):
                cH, cV, cD = coeffs[i]
                features.append(cH.flatten())
                features.append(cV.flatten())
                features.append(cD.flatten())
            
            feature_vector = np.concatenate(features)
            
            feature_vector = np.abs(feature_vector)
            
            if feature_vector.max() > 0:
                feature_vector = feature_vector / feature_vector.max()
            
            self.fingerprint_features = feature_vector
            
            self.update_fp_display()
            
            match_info = self.match_fingerprint(feature_vector)
            self.match_info_var.set(match_info)
            
            self.status_var.set(f"指纹特征提取完成 - 特征维度: {len(feature_vector)}")
            
        except Exception as e:
            messagebox.showerror("错误", f"特征提取失败: {str(e)}")
    
    def generate_sample_db(self):
        self.fingerprint_database = []
        self.wavelet = self.wavelet_var.get()
        level = self.fp_level_var.get()
        
        templates = ['指纹A', '指纹B', '指纹C', '指纹D', '指纹E']
        
        for name in templates:
            size = 256
            x = np.linspace(0, 4*np.pi, size)
            y = np.linspace(0, 4*np.pi, size)
            X, Y = np.meshgrid(x, y)
            
            img = (np.sin(X + np.random.rand()*np.pi) * np.cos(Y + np.random.rand()*np.pi) +
                   0.5 * np.sin(2*X + np.random.rand()) * np.cos(2*Y + np.random.rand()))
            img = (img - img.min()) / (img.max() - img.min())
            
            coeffs = pywt.wavedec2(img, wavelet=self.wavelet, level=level, mode=self.boundary_mode)
            
            features = [coeffs[0].flatten()]
            for i in range(1, len(coeffs)):
                cH, cV, cD = coeffs[i]
                features.extend([cH.flatten(), cV.flatten(), cD.flatten()])
            
            feature_vector = np.concatenate(features)
            feature_vector = np.abs(feature_vector)
            if feature_vector.max() > 0:
                feature_vector = feature_vector / feature_vector.max()
            
            self.fingerprint_database.append({
                'name': name,
                'features': feature_vector,
                'image': img
            })
        
        self.update_fp_display()
        self.status_var.set(f"已生成示例指纹数据库 ({len(templates)}个样本)")
    
    def add_to_database(self):
        if self.fingerprint_features is None:
            messagebox.showwarning("警告", "请先提取指纹特征")
            return
        
        name = f"指纹_{len(self.fingerprint_database)+1}"
        self.fingerprint_database.append({
            'name': name,
            'features': self.fingerprint_features,
            'image': self.current_image.copy()
        })
        
        self.update_fp_display()
        self.status_var.set(f"已添加到数据库: {name}")
    
    def clear_database(self):
        self.fingerprint_database = []
        self.update_fp_display()
        self.status_var.set("指纹数据库已清空")
    
    def match_fingerprint(self, query_features):
        if len(self.fingerprint_database) == 0:
            return "数据库为空，请先添加或生成指纹样本"
        
        distances = []
        for entry in self.fingerprint_database:
            db_features = entry['features']
            
            min_len = min(len(query_features), len(db_features))
            distance = np.sqrt(np.sum((query_features[:min_len] - db_features[:min_len])**2))
            
            similarity = 1.0 / (1.0 + distance) * 100
            distances.append((entry['name'], similarity, distance))
        
        distances.sort(key=lambda x: x[1], reverse=True)
        
        best_match = distances[0]
        info = f"最佳匹配: {best_match[0]} (相似度: {best_match[1]:.2f}%, 距离: {best_match[2]:.4f})"
        
        return info
    
    def update_display(self):
        self.figure.clear()
        
        wavelet_name = self.wavelet_names.get(self.wavelet, self.wavelet)
        
        if self.coeffs is not None:
            gs = self.figure.add_gridspec(2, 4, hspace=0.3, wspace=0.2)
            ax1 = self.figure.add_subplot(gs[0, 0])
            ax2 = self.figure.add_subplot(gs[0, 1])
            ax3 = self.figure.add_subplot(gs[0, 2])
            ax4 = self.figure.add_subplot(gs[0, 3])
            ax5 = self.figure.add_subplot(gs[1, 0])
            ax6 = self.figure.add_subplot(gs[1, 1])
            ax7 = self.figure.add_subplot(gs[1, 2])
            ax8 = self.figure.add_subplot(gs[1, 3])
            
            if self.original_image is not None:
                ax1.imshow(self.original_image, cmap='gray')
                ax1.set_title('原始图像 (含噪)', fontsize=9, fontweight='bold')
                ax1.axis('off')
            
            coeff_arr, slices = pywt.coeffs_to_array(self.coeffs)
            coeff_display = np.log1p(np.abs(coeff_arr))
            coeff_display = (coeff_display - coeff_display.min()) / (coeff_display.max() - coeff_display.min() + 1e-10)
            
            ax2.imshow(coeff_display, cmap='viridis')
            ax2.set_title(f'小波系数 ({wavelet_name}, L={self.level})', fontsize=9, fontweight='bold')
            ax2.axis('off')
            
            self.plot_coeffs_details(ax3)
            
            if hasattr(self, 'energy_info'):
                self.plot_energy_distribution(ax4)
            
            self.plot_coeffs_histogram(ax5)
            
            ax6.imshow(self.current_image, cmap='gray')
            ax6.set_title('当前处理结果', fontsize=9, fontweight='bold')
            ax6.axis('off')
            
            if self.reconstructed is not None:
                h, w = self.original_image.shape
                recon_display = self.reconstructed[:h, :w]
                ax7.imshow(recon_display, cmap='gray')
                ax7.set_title('IDWT重构图像', fontsize=9, fontweight='bold')
                ax7.axis('off')
                
                diff = np.abs(self.original_image - recon_display) * 10
                ax8.imshow(diff, cmap='hot', vmin=0, vmax=0.5)
                ax8.set_title('误差放大 (×10)', fontsize=9, fontweight='bold')
                ax8.axis('off')
            else:
                ax7.text(0.5, 0.5, '执行IDWT重构\n以查看结果', 
                        ha='center', va='center', fontsize=10, transform=ax7.transAxes)
                ax7.set_title('重构结果', fontsize=9, fontweight='bold')
                ax7.axis('off')
                
                ax8.text(0.5, 0.5, f'边界模式:\n{self.boundary_names[self.boundary_mode]}', 
                        ha='center', va='center', fontsize=9, transform=ax8.transAxes,
                        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
                ax8.set_title('边界模式', fontsize=9, fontweight='bold')
                ax8.axis('off')
            
        else:
            gs = self.figure.add_gridspec(2, 2, hspace=0.3, wspace=0.2)
            ax1 = self.figure.add_subplot(gs[0, 0])
            ax2 = self.figure.add_subplot(gs[0, 1])
            ax3 = self.figure.add_subplot(gs[1, 0])
            ax4 = self.figure.add_subplot(gs[1, 1])
            
            if self.original_image is not None:
                ax1.imshow(self.original_image, cmap='gray')
                ax1.set_title('原始图像', fontsize=12, fontweight='bold')
                ax1.axis('off')
                
                ax2.hist(self.original_image.flatten(), bins=50, color='steelblue', alpha=0.7, edgecolor='black')
                ax2.set_title('灰度直方图', fontsize=12, fontweight='bold')
                ax2.set_xlabel('灰度值', fontsize=10)
                ax2.set_ylabel('频数', fontsize=10)
                ax2.grid(True, alpha=0.3)
                
                self.plot_wavelet_basis(ax3)
                
                ax4.text(0.5, 0.5, '点击"执行DWT"\n开始小波变换', 
                        ha='center', va='center', fontsize=14, transform=ax4.transAxes, 
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
                ax4.set_title('操作提示', fontsize=12, fontweight='bold')
                ax4.axis('off')
        
        self.canvas.draw()
    
    def update_wp_display(self):
        self.wp_figure.clear()
        
        if self.wp_coeffs is not None:
            gs = self.wp_figure.add_gridspec(2, 3, hspace=0.3, wspace=0.2)
            ax1 = self.wp_figure.add_subplot(gs[0, 0])
            ax2 = self.wp_figure.add_subplot(gs[0, 1])
            ax3 = self.wp_figure.add_subplot(gs[0, 2])
            ax4 = self.wp_figure.add_subplot(gs[1, 0])
            ax5 = self.wp_figure.add_subplot(gs[1, 1])
            ax6 = self.wp_figure.add_subplot(gs[1, 2])
            
            if self.original_image is not None:
                ax1.imshow(self.original_image, cmap='gray')
                ax1.set_title('原始图像', fontsize=9, fontweight='bold')
                ax1.axis('off')
            
            self.plot_wp_coeffs(ax2)
            
            if self.direction_features is not None:
                self.plot_direction_analysis(ax3)
            
            self.plot_wp_energy_distribution(ax4)
            
            if hasattr(self, 'wp_reconstructed'):
                ax5.imshow(self.wp_reconstructed, cmap='gray')
                ax5.set_title('小波包重构', fontsize=9, fontweight='bold')
                ax5.axis('off')
                
                diff = np.abs(self.original_image - self.wp_reconstructed) * 10
                ax6.imshow(diff, cmap='hot', vmin=0, vmax=0.5)
                ax6.set_title('重构误差 (×10)', fontsize=9, fontweight='bold')
                ax6.axis('off')
            else:
                ax5.text(0.5, 0.5, '执行小波包重构', ha='center', va='center', 
                        fontsize=10, transform=ax5.transAxes)
                ax5.set_title('重构结果', fontsize=9, fontweight='bold')
                ax5.axis('off')
                
                ax6.text(0.5, 0.5, '点击"方向分析"\n提取纹理特征', 
                        ha='center', va='center', fontsize=10, transform=ax6.transAxes)
                ax6.set_title('方向分析', fontsize=9, fontweight='bold')
                ax6.axis('off')
                
        else:
            gs = self.wp_figure.add_gridspec(1, 2, hspace=0.3, wspace=0.2)
            ax1 = self.wp_figure.add_subplot(gs[0, 0])
            ax2 = self.wp_figure.add_subplot(gs[0, 1])
            
            if self.original_image is not None:
                ax1.imshow(self.original_image, cmap='gray')
                ax1.set_title('原始图像', fontsize=12, fontweight='bold')
                ax1.axis('off')
                
                ax2.text(0.5, 0.5, '选择分解层数\n点击"执行小波包分解"', 
                        ha='center', va='center', fontsize=14, transform=ax2.transAxes,
                        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
                ax2.set_title('小波包分解', fontsize=12, fontweight='bold')
                ax2.axis('off')
        
        self.wp_canvas.draw()
    
    def update_fp_display(self):
        self.fp_figure.clear()
        
        n_db = len(self.fingerprint_database)
        if n_db > 0:
            n_cols = min(n_db + 1, 4)
            n_rows = 2
            
            gs = self.fp_figure.add_gridspec(n_rows, n_cols, hspace=0.3, wspace=0.2)
            
            ax = self.fp_figure.add_subplot(gs[0, 0])
            if self.original_image is not None:
                ax.imshow(self.original_image, cmap='gray')
                ax.set_title('查询指纹', fontsize=9, fontweight='bold')
                ax.axis('off')
            
            for i, entry in enumerate(self.fingerprint_database[:n_cols-1]):
                ax = self.fp_figure.add_subplot(gs[0, i+1])
                ax.imshow(entry['image'], cmap='gray')
                ax.set_title(f"{entry['name']}", fontsize=9, fontweight='bold')
                ax.axis('off')
            
            if self.fingerprint_features is not None:
                ax = self.fp_figure.add_subplot(gs[1, 0])
                self.plot_feature_vector(ax, self.fingerprint_features, '查询特征')
                
                for i, entry in enumerate(self.fingerprint_database[:n_cols-1]):
                    ax = self.fp_figure.add_subplot(gs[1, i+1])
                    
                    if i == 0 and len(self.fingerprint_database) > 0:
                        self.plot_feature_comparison(ax, self.fingerprint_features, entry['features'], entry['name'])
                    else:
                        self.plot_feature_vector(ax, entry['features'], f"{entry['name']}特征")
        else:
            gs = self.fp_figure.add_gridspec(1, 2, hspace=0.3, wspace=0.2)
            ax1 = self.fp_figure.add_subplot(gs[0, 0])
            ax2 = self.fp_figure.add_subplot(gs[0, 1])
            
            if self.original_image is not None:
                ax1.imshow(self.original_image, cmap='gray')
                ax1.set_title('查询指纹', fontsize=12, fontweight='bold')
                ax1.axis('off')
            
            ax2.text(0.5, 0.5, '点击"生成示例指纹库"\n或"添加到数据库"', 
                    ha='center', va='center', fontsize=12, transform=ax2.transAxes,
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            ax2.set_title('指纹数据库', fontsize=12, fontweight='bold')
            ax2.axis('off')
        
        self.fp_canvas.draw()
    
    def plot_wp_coeffs(self, ax):
        if self.wp_coeffs is None:
            return
        
        order = self.wp_order_var.get()
        nodes = [node.path for node in self.wp_coeffs.get_level(self.wp_level, order=order)]
        
        n = len(nodes)
        n_cols = int(np.ceil(np.sqrt(n)))
        n_rows = int(np.ceil(n / n_cols))
        
        coeff_grid = None
        target_h = target_w = 0
        
        for i, node_path in enumerate(nodes):
            coeff = self.wp_coeffs[node_path].data
            coeff_norm = np.log1p(np.abs(coeff))
            if coeff_norm.max() > 0:
                coeff_norm = coeff_norm / coeff_norm.max()
            
            if i == 0:
                target_h, target_w = coeff_norm.shape
                coeff_grid = np.zeros((n_rows * target_h, n_cols * target_w))
            
            row = i // n_cols
            col = i % n_cols
            
            if coeff_norm.shape == (target_h, target_w):
                coeff_grid[row*target_h:(row+1)*target_h, col*target_w:(col+1)*target_w] = coeff_norm
        
        if coeff_grid is not None:
            ax.imshow(coeff_grid, cmap='viridis')
            ax.set_title(f'小波包子带 ({len(nodes)}个)', fontsize=9, fontweight='bold')
            ax.axis('off')
    
    def plot_direction_analysis(self, ax):
        if self.direction_features is None:
            return
        
        energies = self.direction_features['energies']
        dominant = self.direction_features['dominant_direction']
        
        directions = list(energies.keys())
        values = [energies[d] for d in directions]
        colors = ['#ff6b6b', '#4ecdc4', '#ffe66d']
        
        bars = ax.bar(directions, values, color=colors, edgecolor='black', linewidth=0.5)
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=8)
        
        ax.set_title(f'方向性分析 (主导: {dominant})', fontsize=9, fontweight='bold')
        ax.set_ylabel('能量占比 (%)', fontsize=8)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3, axis='y')
    
    def plot_wp_energy_distribution(self, ax):
        if self.wp_coeffs is None:
            return
        
        order = self.wp_order_var.get()
        nodes = [node.path for node in self.wp_coeffs.get_level(self.wp_level, order=order)]
        
        energies = []
        labels = []
        for node_path in nodes:
            coeff = self.wp_coeffs[node_path].data
            energy = np.sum(coeff**2)
            energies.append(energy)
            labels.append(node_path)
        
        total = sum(energies)
        if total > 0:
            energies = [e/total*100 for e in energies]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(energies)))
        ax.barh(range(len(energies)), energies, color=colors, edgecolor='black', linewidth=0.5)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=6)
        ax.set_title('子带能量分布', fontsize=9, fontweight='bold')
        ax.set_xlabel('能量占比 (%)', fontsize=8)
        ax.grid(True, alpha=0.3, axis='x')
    
    def plot_feature_vector(self, ax, features, title):
        n = min(len(features), 512)
        ax.plot(range(n), features[:n], 'b-', linewidth=0.5)
        ax.set_title(title, fontsize=9, fontweight='bold')
        ax.set_xlabel('特征索引', fontsize=7)
        ax.set_ylabel('幅值', fontsize=7)
        ax.grid(True, alpha=0.3)
    
    def plot_feature_comparison(self, ax, feat1, feat2, name):
        min_len = min(len(feat1), len(feat2), 256)
        
        ax.plot(range(min_len), feat1[:min_len], 'b-', linewidth=0.5, label='查询')
        ax.plot(range(min_len), feat2[:min_len], 'r-', linewidth=0.5, label=name, alpha=0.7)
        
        distance = np.sqrt(np.sum((feat1[:min_len] - feat2[:min_len])**2))
        similarity = 1.0 / (1.0 + distance) * 100
        
        ax.set_title(f'对比: {name} (相似度: {similarity:.1f}%)', fontsize=8, fontweight='bold')
        ax.set_xlabel('特征索引', fontsize=7)
        ax.set_ylabel('幅值', fontsize=7)
        ax.legend(fontsize=6)
        ax.grid(True, alpha=0.3)
    
    def plot_coeffs_details(self, ax):
        if self.coeffs is None or len(self.coeffs) < 2:
            return
        
        cA = self.coeffs[0]
        cH, cV, cD = self.coeffs[-1]
        
        titles = ['近似 cA', '水平 cH', '垂直 cV', '对角 cD']
        coeffs_list = [cA, cH, cV, cD]
        
        h, w = cA.shape
        display_img = np.zeros((h * 2, w * 2))
        
        for i, (coeff, title) in enumerate(zip(coeffs_list, titles)):
            row = i // 2
            col = i % 2
            
            coeff_norm = np.abs(coeff)
            coeff_norm = np.log1p(coeff_norm)
            if coeff_norm.max() > 0:
                coeff_norm = coeff_norm / coeff_norm.max()
            
            resized = np.array(Image.fromarray(coeff_norm).resize((w, h), Image.NEAREST))
            display_img[row*h:(row+1)*h, col*w:(col+1)*w] = resized
            
            ax.text(col*w + w/2, row*h + 15, title, 
                   ha='center', va='center', color='red', 
                   fontsize=8, fontweight='bold',
                   bbox=dict(facecolor='white', alpha=0.8))
        
        ax.imshow(display_img, cmap='plasma')
        ax.set_title(f'各子带系数 (最细尺度)', fontsize=9, fontweight='bold')
        ax.axis('off')
    
    def plot_energy_distribution(self, ax):
        if not hasattr(self, 'energy_info'):
            return
        
        names = [item[0] for item in self.energy_info]
        percentages = [item[2] for item in self.energy_info]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(names)))
        bars = ax.bar(range(len(names)), percentages, color=colors, edgecolor='black', linewidth=0.5)
        
        ax.set_title('能量分布 (%)', fontsize=9, fontweight='bold')
        ax.set_ylabel('能量占比 (%)', fontsize=8)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha='right', fontsize=6)
        ax.grid(True, alpha=0.3, axis='y')
        
        for bar, pct in zip(bars, percentages):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{pct:.1f}%', ha='center', va='bottom', fontsize=6)
    
    def plot_coeffs_histogram(self, ax):
        if self.coeffs is None:
            return
        
        all_coeffs = []
        cA = self.coeffs[0]
        all_coeffs.append(cA.flatten())
        
        for i in range(1, len(self.coeffs)):
            cH, cV, cD = self.coeffs[i]
            all_coeffs.append(cH.flatten())
            all_coeffs.append(cV.flatten())
            all_coeffs.append(cD.flatten())
        
        all_coeffs = np.concatenate(all_coeffs)
        all_coeffs = all_coeffs[np.abs(all_coeffs) > 1e-10]
        
        ax.hist(np.abs(all_coeffs), bins=100, color='coral', alpha=0.7, 
                edgecolor='black', linewidth=0.5, log=True)
        ax.set_title('系数幅值分布 (对数坐标)', fontsize=9, fontweight='bold')
        ax.set_xlabel('|系数|', fontsize=8)
        ax.set_ylabel('频数 (log)', fontsize=8)
        ax.grid(True, alpha=0.3)
        
        nonzero_ratio = np.sum(np.abs(all_coeffs) > 1e-10) / len(all_coeffs) * 100
        ax.text(0.95, 0.95, f'非零系数: {nonzero_ratio:.1f}%', 
                transform=ax.transAxes, ha='right', va='top',
                fontsize=8, bbox=dict(facecolor='white', alpha=0.8))
    
    def plot_wavelet_basis(self, ax):
        wavelet = pywt.Wavelet(self.wavelet)
        phi, psi, x = wavelet.wavefun(level=8)
        
        ax.plot(x, phi, 'b-', linewidth=2, label='尺度函数 φ(t)')
        ax.plot(x, psi, 'r-', linewidth=2, label='小波函数 ψ(t)')
        ax.set_title(f'{self.wavelet_names[self.wavelet]} 小波基函数', fontsize=10, fontweight='bold')
        ax.set_xlabel('时间 t', fontsize=9)
        ax.set_ylabel('幅值', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)


def main():
    root = tk.Tk()
    app = WaveletTransformApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
