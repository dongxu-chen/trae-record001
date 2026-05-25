import numpy as np
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from scipy import fftpack
import threading


class FrequencyFilter:
    def __init__(self, root):
        self.root = root
        self.root.title("频域滤波器 - Frequency Domain Filter")
        self.root.geometry("1600x1000")
        
        self.original_image = None
        self.fft_image = None
        self.filtered_fft = None
        self.filter_mask = None
        self.current_filter = "理想低通"
        
        self.debounce_id = None
        self.debounce_delay = 150
        self.compute_lock = threading.Lock()
        self.compute_thread = None
        
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        control_panel = ttk.Frame(main_frame, padding="10")
        control_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Button(control_panel, text="加载图像", command=self.load_image).pack(fill=tk.X, pady=5)
        
        ttk.Label(control_panel, text="滤波器类型:").pack(anchor=tk.W, pady=(10, 5))
        self.filter_var = tk.StringVar(value="理想低通")
        filters = ["理想低通", "高斯低通", "巴特沃斯低通", "理想高通", "高斯高通", "巴特沃斯高通",
                   "带通", "带阻", "自适应低通", "自适应高通", "同态滤波"]
        filter_combo = ttk.Combobox(control_panel, textvariable=self.filter_var, values=filters, state="readonly")
        filter_combo.pack(fill=tk.X)
        filter_combo.bind("<<ComboboxSelected>>", self.on_filter_change)
        
        ttk.Label(control_panel, text="截止频率 D₀:").pack(anchor=tk.W, pady=(15, 5))
        self.cutoff_var = tk.IntVar(value=30)
        cutoff_scale = ttk.Scale(control_panel, from_=1, to=200, variable=self.cutoff_var, orient=tk.HORIZONTAL)
        cutoff_scale.pack(fill=tk.X)
        self.cutoff_label = ttk.Label(control_panel, text="30")
        self.cutoff_label.pack()
        cutoff_scale.configure(command=lambda v: self.on_param_change(v, "cutoff"))
        
        ttk.Label(control_panel, text="巴特沃斯阶数 n:").pack(anchor=tk.W, pady=(15, 5))
        self.order_var = tk.IntVar(value=2)
        order_scale = ttk.Scale(control_panel, from_=1, to=10, variable=self.order_var, orient=tk.HORIZONTAL)
        order_scale.pack(fill=tk.X)
        self.order_label = ttk.Label(control_panel, text="2")
        self.order_label.pack()
        order_scale.configure(command=lambda v: self.on_param_change(v, "order"))
        
        ttk.Label(control_panel, text="理想滤波器过渡宽度:").pack(anchor=tk.W, pady=(15, 5))
        self.transition_var = tk.IntVar(value=5)
        transition_scale = ttk.Scale(control_panel, from_=1, to=30, variable=self.transition_var, orient=tk.HORIZONTAL)
        transition_scale.pack(fill=tk.X)
        self.transition_label = ttk.Label(control_panel, text="5")
        self.transition_label.pack()
        transition_scale.configure(command=lambda v: self.on_param_change(v, "transition"))
        
        ttk.Label(control_panel, text="低频截止 D_low:").pack(anchor=tk.W, pady=(15, 5))
        self.band_low_var = tk.IntVar(value=20)
        band_low_scale = ttk.Scale(control_panel, from_=1, to=200, variable=self.band_low_var, orient=tk.HORIZONTAL)
        band_low_scale.pack(fill=tk.X)
        self.band_low_label = ttk.Label(control_panel, text="20")
        self.band_low_label.pack()
        band_low_scale.configure(command=lambda v: self.on_param_change(v, "band_low"))
        
        ttk.Label(control_panel, text="高频截止 D_high:").pack(anchor=tk.W, pady=(15, 5))
        self.band_high_var = tk.IntVar(value=50)
        band_high_scale = ttk.Scale(control_panel, from_=1, to=200, variable=self.band_high_var, orient=tk.HORIZONTAL)
        band_high_scale.pack(fill=tk.X)
        self.band_high_label = ttk.Label(control_panel, text="50")
        self.band_high_label.pack()
        band_high_scale.configure(command=lambda v: self.on_param_change(v, "band_high"))
        
        ttk.Label(control_panel, text="同态滤波 γL:").pack(anchor=tk.W, pady=(15, 5))
        self.gamma_l_var = tk.DoubleVar(value=0.5)
        gamma_l_scale = ttk.Scale(control_panel, from_=0.1, to=1.0, variable=self.gamma_l_var, orient=tk.HORIZONTAL)
        gamma_l_scale.pack(fill=tk.X)
        self.gamma_l_label = ttk.Label(control_panel, text="0.50")
        self.gamma_l_label.pack()
        gamma_l_scale.configure(command=lambda v: self.on_param_change(v, "gamma_l"))
        
        ttk.Label(control_panel, text="同态滤波 γH:").pack(anchor=tk.W, pady=(15, 5))
        self.gamma_h_var = tk.DoubleVar(value=2.0)
        gamma_h_scale = ttk.Scale(control_panel, from_=1.0, to=5.0, variable=self.gamma_h_var, orient=tk.HORIZONTAL)
        gamma_h_scale.pack(fill=tk.X)
        self.gamma_h_label = ttk.Label(control_panel, text="2.00")
        self.gamma_h_label.pack()
        gamma_h_scale.configure(command=lambda v: self.on_param_change(v, "gamma_h"))
        
        ttk.Label(control_panel, text="同态滤波 c:").pack(anchor=tk.W, pady=(15, 5))
        self.homo_c_var = tk.DoubleVar(value=1.0)
        homo_c_scale = ttk.Scale(control_panel, from_=0.1, to=5.0, variable=self.homo_c_var, orient=tk.HORIZONTAL)
        homo_c_scale.pack(fill=tk.X)
        self.homo_c_label = ttk.Label(control_panel, text="1.00")
        self.homo_c_label.pack()
        homo_c_scale.configure(command=lambda v: self.on_param_change(v, "homo_c"))
        
        ttk.Separator(control_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        ttk.Label(control_panel, text="=== 对比滤波 ===", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        ttk.Label(control_panel, text="传统滤波方法:").pack(anchor=tk.W, pady=(10, 5))
        self.spatial_filter_var = tk.StringVar(value="高斯模糊")
        spatial_filters = ["高斯模糊", "双边滤波", "中值滤波", "均值滤波", "非局部均值"]
        spatial_combo = ttk.Combobox(control_panel, textvariable=self.spatial_filter_var, values=spatial_filters, state="readonly")
        spatial_combo.pack(fill=tk.X)
        
        ttk.Label(control_panel, text="核大小:").pack(anchor=tk.W, pady=(10, 5))
        self.kernel_var = tk.IntVar(value=5)
        kernel_scale = ttk.Scale(control_panel, from_=1, to=21, variable=self.kernel_var, orient=tk.HORIZONTAL)
        kernel_scale.pack(fill=tk.X)
        self.kernel_label = ttk.Label(control_panel, text="5")
        self.kernel_label.pack()
        kernel_scale.configure(command=lambda v: self.on_param_change(v, "kernel"))
        
        ttk.Button(control_panel, text="应用滤波", command=self.apply_filter).pack(fill=tk.X, pady=20)
        ttk.Button(control_panel, text="对比滤波", command=self.apply_comparison).pack(fill=tk.X, pady=5)
        ttk.Button(control_panel, text="保存结果", command=self.save_result).pack(fill=tk.X, pady=5)
        
        display_panel = ttk.Frame(main_frame)
        display_panel.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        display_panel.columnconfigure(0, weight=1)
        display_panel.columnconfigure(1, weight=1)
        display_panel.rowconfigure(0, weight=1)
        display_panel.rowconfigure(1, weight=1)
        
        self.original_frame = ttk.LabelFrame(display_panel, text="原始图像", padding="5")
        self.original_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.original_label = ttk.Label(self.original_frame)
        self.original_label.pack(expand=True)
        
        self.fft_frame = ttk.LabelFrame(display_panel, text="傅里叶频谱", padding="5")
        self.fft_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.fft_label = ttk.Label(self.fft_frame)
        self.fft_label.pack(expand=True)
        
        self.filter_frame = ttk.LabelFrame(display_panel, text="滤波器掩模", padding="5")
        self.filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.filter_label = ttk.Label(self.filter_frame)
        self.filter_label.pack(expand=True)
        
        self.result_frame = ttk.LabelFrame(display_panel, text="频域滤波结果", padding="5")
        self.result_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.result_label = ttk.Label(self.result_frame)
        self.result_label.pack(expand=True)
        
        self.comparison_window = None
        self.comparison_labels = {}
    
    def on_param_change(self, value, param_type):
        if param_type == "cutoff":
            self.cutoff_label.config(text=f"{int(float(value))}")
        elif param_type == "order":
            self.order_label.config(text=f"{int(float(value))}")
        elif param_type == "transition":
            self.transition_label.config(text=f"{int(float(value))}")
        elif param_type == "band_low":
            self.band_low_label.config(text=f"{int(float(value))}")
        elif param_type == "band_high":
            self.band_high_label.config(text=f"{int(float(value))}")
        elif param_type == "gamma_l":
            self.gamma_l_label.config(text=f"{float(value):.2f}")
        elif param_type == "gamma_h":
            self.gamma_h_label.config(text=f"{float(value):.2f}")
        elif param_type == "homo_c":
            self.homo_c_label.config(text=f"{float(value):.2f}")
        elif param_type == "kernel":
            self.kernel_label.config(text=f"{int(float(value))}")
        
        if self.original_image is not None and param_type != "kernel":
            self.schedule_filter()
    
    def schedule_filter(self):
        if self.debounce_id is not None:
            try:
                self.root.after_cancel(self.debounce_id)
            except Exception:
                pass
        
        self.debounce_id = self.root.after(self.debounce_delay, self.apply_filter_async)
    
    def apply_filter_async(self):
        if self.compute_lock.locked():
            return
        
        self.compute_thread = threading.Thread(target=self._apply_filter_worker, daemon=True)
        self.compute_thread.start()
    
    def _apply_filter_worker(self):
        if not self.compute_lock.acquire(blocking=False):
            return
        try:
            if self.fft_image is None:
                return
            
            shape = self.fft_image.shape
            filter_type = self.filter_var.get()
            
            self.filter_mask = self.create_filter_mask(shape, filter_type)
            
            if filter_type == "同态滤波":
                self.filtered_fft = self.apply_homomorphic_filter()
            else:
                self.filtered_fft = self.fft_image * self.filter_mask
            
            fft_ishift = fftpack.ifftshift(self.filtered_fft)
            img_filtered = fftpack.ifft2(fft_ishift)
            img_filtered = np.abs(img_filtered)
            
            img_filtered = cv2.normalize(img_filtered, None, 0, 255, cv2.NORM_MINMAX)
            img_filtered = img_filtered.astype(np.uint8)
            
            h, w = self.original_image.shape
            img_filtered = img_filtered[:h, :w]
            
            self.root.after(0, self._update_display, img_filtered)
        except Exception as e:
            print(f"Filter error: {e}")
        finally:
            self.compute_lock.release()
    
    def _update_display(self, img_filtered):
        if self.filter_var.get() != "同态滤波":
            self.display_image(self.filter_mask, self.filter_label, normalize=True)
        self.display_image(img_filtered, self.result_label)
    
    def on_filter_change(self, event):
        self.current_filter = self.filter_var.get()
        if self.original_image is not None:
            self.apply_filter()
    
    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")]
        )
        if file_path:
            try:
                img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    raise ValueError("无法读取图像文件")
                
                max_size = 512
                h, w = img.shape
                if max(h, w) > max_size:
                    scale = max_size / max(h, w)
                    img = cv2.resize(img, (int(w * scale), int(h * scale)))
                
                self.original_image = img
                self.compute_fft()
                self.display_image(self.original_image, self.original_label)
                self.apply_filter()
            except Exception as e:
                messagebox.showerror("错误", f"加载图像失败: {str(e)}")
    
    def compute_fft(self):
        if self.original_image is None:
            return
        
        h, w = self.original_image.shape
        r = cv2.getOptimalDFTSize(h)
        c = cv2.getOptimalDFTSize(w)
        padded = cv2.copyMakeBorder(self.original_image, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
        
        self.fft_image = fftpack.fft2(padded)
        self.fft_image = fftpack.fftshift(self.fft_image)
        
        self.display_spectrum(self.fft_image, self.fft_label)
    
    def compute_adaptive_cutoff(self, is_lowpass=True):
        if self.fft_image is None:
            return 30
        
        spectrum = np.log(1 + np.abs(self.fft_image))
        rows, cols = spectrum.shape
        crow, ccol = rows // 2, cols // 2
        
        y, x = np.ogrid[:rows, :cols]
        dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
        
        radial_energy = np.zeros(int(dist.max()) + 1)
        for r in range(len(radial_energy)):
            mask = np.abs(dist - r) < 1
            if np.any(mask):
                radial_energy[r] = spectrum[mask].mean()
        
        cumsum = np.cumsum(radial_energy)
        total_energy = cumsum[-1]
        
        if is_lowpass:
            threshold = 0.95
        else:
            threshold = 0.05
        
        cutoff_idx = np.where(cumsum >= total_energy * threshold)[0]
        if len(cutoff_idx) > 0:
            adaptive_cutoff = int(cutoff_idx[0])
        else:
            adaptive_cutoff = 30
        
        return max(1, min(200, adaptive_cutoff))
    
    def apply_homomorphic_filter(self):
        if self.original_image is None or self.fft_image is None:
            return self.fft_image
        
        img_log = np.log1p(self.original_image.astype(np.float64))
        
        h, w = img_log.shape
        r = cv2.getOptimalDFTSize(h)
        c = cv2.getOptimalDFTSize(w)
        padded_log = cv2.copyMakeBorder(img_log, 0, r - h, 0, c - w, cv2.BORDER_CONSTANT, value=0)
        
        fft_log = fftpack.fft2(padded_log)
        fft_log = fftpack.fftshift(fft_log)
        
        rows, cols = fft_log.shape
        crow, ccol = rows // 2, cols // 2
        
        y, x = np.ogrid[:rows, :cols]
        dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
        
        d0 = self.cutoff_var.get()
        c = self.homo_c_var.get()
        gamma_l = self.gamma_l_var.get()
        gamma_h = self.gamma_h_var.get()
        
        homo_filter = gamma_h + (gamma_l - gamma_h) * (1 - np.exp(-c * (dist ** 2) / (d0 ** 2 + 1e-8)))
        
        filtered_fft = fft_log * homo_filter
        
        self.filter_mask = homo_filter.astype(np.float32)
        
        return filtered_fft
    
    def _hann_window_1d(self, size):
        if size <= 1:
            return np.ones(size)
        n = np.arange(size)
        return 0.5 - 0.5 * np.cos(2 * np.pi * n / (size - 1))
    
    def _create_ideal_lowpass(self, dist, cutoff, transition_width):
        if transition_width <= 0:
            mask = np.zeros_like(dist.shape, dtype=np.float32)
            mask[dist <= cutoff] = 1.0
            return mask
        
        mask = np.zeros_like(dist.shape, dtype=np.float32)
        
        inner_radius = max(0, cutoff - transition_width)
        outer_radius = cutoff + transition_width
        
        mask[dist <= inner_radius] = 1.0
        
        transition = np.logical_and(dist > inner_radius, dist <= outer_radius)
        transition_dist = dist[transition]
        normalized = (transition_dist - inner_radius) / (2 * transition_width)
        normalized = np.clip(normalized, 0, 1)
        hann_values = 0.5 - 0.5 * np.cos(np.pi * normalized)
        mask[transition] = 1.0 - hann_values
        
        return mask
    
    def _create_ideal_highpass(self, dist, cutoff, transition_width):
        return 1.0 - self._create_ideal_lowpass(dist, cutoff, transition_width)
    
    def _butterworth_lowpass(self, dist, cutoff, order):
        return 1.0 / (1.0 + (dist / cutoff) ** (2 * order))
    
    def _butterworth_highpass(self, dist, cutoff, order):
        return 1.0 / (1.0 + (cutoff / (dist + 1e-8)) ** (2 * order))
    
    def create_filter_mask(self, shape, filter_type):
        rows, cols = shape
        crow, ccol = rows // 2, cols // 2
        
        y, x = np.ogrid[:rows, :cols]
        dist = np.sqrt((x - ccol) ** 2 + (y - crow) ** 2)
        
        cutoff = self.cutoff_var.get()
        order = self.order_var.get()
        transition = self.transition_var.get()
        band_low = self.band_low_var.get()
        band_high = self.band_high_var.get()
        
        if filter_type == "自适应低通":
            cutoff = self.compute_adaptive_cutoff(is_lowpass=True)
            self.cutoff_var.set(cutoff)
            self.cutoff_label.config(text=str(cutoff))
            mask = self._butterworth_lowpass(dist, cutoff, order)
        
        elif filter_type == "自适应高通":
            cutoff = self.compute_adaptive_cutoff(is_lowpass=False)
            self.cutoff_var.set(cutoff)
            self.cutoff_label.config(text=str(cutoff))
            mask = self._butterworth_highpass(dist, cutoff, order)
        
        elif filter_type == "同态滤波":
            mask = np.ones((rows, cols), dtype=np.float32)
        
        elif filter_type == "理想低通":
            mask = self._create_ideal_lowpass(dist, cutoff, transition)
        
        elif filter_type == "理想高通":
            mask = self._create_ideal_highpass(dist, cutoff, transition)
        
        elif filter_type == "高斯低通":
            mask = np.exp(-(dist ** 2) / (2 * (cutoff ** 2)))
        
        elif filter_type == "高斯高通":
            mask = 1.0 - np.exp(-(dist ** 2) / (2 * (cutoff ** 2)))
        
        elif filter_type == "巴特沃斯低通":
            mask = self._butterworth_lowpass(dist, cutoff, order)
        
        elif filter_type == "巴特沃斯高通":
            mask = self._butterworth_highpass(dist, cutoff, order)
        
        elif filter_type == "带通":
            mask_low = self._butterworth_lowpass(dist, band_low, order)
            mask_high = self._butterworth_highpass(dist, band_high, order)
            mask = mask_high * (1.0 - mask_low)
            mask = np.clip(mask, 0, 1)
        
        elif filter_type == "带阻":
            mask_low_pass = self._butterworth_lowpass(dist, band_low, order)
            mask_high_pass = self._butterworth_highpass(dist, band_high, order)
            mask = mask_low_pass + mask_high_pass
            mask = np.clip(mask, 0, 1)
        
        else:
            mask = np.ones((rows, cols), dtype=np.float32)
        
        return mask
    
    def apply_filter(self):
        if self.fft_image is None:
            return
        
        shape = self.fft_image.shape
        filter_type = self.filter_var.get()
        
        self.filter_mask = self.create_filter_mask(shape, filter_type)
        
        if filter_type == "同态滤波":
            self.filtered_fft = self.apply_homomorphic_filter()
        else:
            self.filtered_fft = self.fft_image * self.filter_mask
        
        fft_ishift = fftpack.ifftshift(self.filtered_fft)
        img_filtered = fftpack.ifft2(fft_ishift)
        img_filtered = np.abs(img_filtered)
        
        img_filtered = cv2.normalize(img_filtered, None, 0, 255, cv2.NORM_MINMAX)
        img_filtered = img_filtered.astype(np.uint8)
        
        h, w = self.original_image.shape
        img_filtered = img_filtered[:h, :w]
        
        if filter_type != "同态滤波":
            self.display_image(self.filter_mask, self.filter_label, normalize=True)
        self.display_image(img_filtered, self.result_label)
    
    def apply_spatial_filter(self, img, filter_type, kernel_size):
        k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        
        if filter_type == "高斯模糊":
            return cv2.GaussianBlur(img, (k, k), 0)
        
        elif filter_type == "双边滤波":
            d = k
            sigma_color = sigma_space = k * 2
            return cv2.bilateralFilter(img, d, sigma_color, sigma_space)
        
        elif filter_type == "中值滤波":
            return cv2.medianBlur(img, k)
        
        elif filter_type == "均值滤波":
            kernel = np.ones((k, k), np.float32) / (k * k)
            return cv2.filter2D(img, -1, kernel)
        
        elif filter_type == "非局部均值":
            h = k * 2
            return cv2.fastNlMeansDenoising(img, None, h, 7, 21)
        
        else:
            return img.copy()
    
    def apply_comparison(self):
        if self.original_image is None:
            messagebox.showwarning("警告", "请先加载图像")
            return
        
        spatial_type = self.spatial_filter_var.get()
        kernel = self.kernel_var.get()
        
        spatial_result = self.apply_spatial_filter(self.original_image, spatial_type, kernel)
        
        self.apply_filter()
        
        freq_result = None
        if self.filtered_fft is not None:
            fft_ishift = fftpack.ifftshift(self.filtered_fft)
            img_filtered = fftpack.ifft2(fft_ishift)
            img_filtered = np.abs(img_filtered)
            img_filtered = cv2.normalize(img_filtered, None, 0, 255, cv2.NORM_MINMAX)
            img_filtered = img_filtered.astype(np.uint8)
            h, w = self.original_image.shape
            freq_result = img_filtered[:h, :w]
        
        if freq_result is None:
            freq_result = self.original_image.copy()
        
        self.show_comparison_window(spatial_result, freq_result, spatial_type)
    
    def show_comparison_window(self, spatial_img, freq_img, spatial_name):
        if self.comparison_window is None or not self.comparison_window.winfo_exists():
            self.comparison_window = tk.Toplevel(self.root)
            self.comparison_window.title("滤波对比 - Filter Comparison")
            self.comparison_window.geometry("900x450")
            
            frame = ttk.Frame(self.comparison_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
            frame.columnconfigure(2, weight=1)
            frame.rowconfigure(0, weight=1)
            
            self.comparison_labels = {}
            
            orig_frame = ttk.LabelFrame(frame, text="原始图像", padding="5")
            orig_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            self.comparison_labels['original'] = ttk.Label(orig_frame)
            self.comparison_labels['original'].pack(expand=True)
            
            spatial_frame = ttk.LabelFrame(frame, text=f"空间域: {spatial_name}", padding="5")
            spatial_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            self.comparison_labels['spatial'] = ttk.Label(spatial_frame)
            self.comparison_labels['spatial'].pack(expand=True)
            
            freq_frame = ttk.LabelFrame(frame, text=f"频域: {self.filter_var.get()}", padding="5")
            freq_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            self.comparison_labels['frequency'] = ttk.Label(freq_frame)
            self.comparison_labels['frequency'].pack(expand=True)
        
        self.comparison_window.focus_set()
        self.display_image(self.original_image, self.comparison_labels['original'])
        self.display_image(spatial_img, self.comparison_labels['spatial'])
        self.display_image(freq_img, self.comparison_labels['frequency'])
    
    def display_image(self, img, label, normalize=False):
        if img is None:
            return
        
        display_img = img.copy()
        
        if normalize:
            display_img = cv2.normalize(display_img, None, 0, 255, cv2.NORM_MINMAX)
        
        if display_img.dtype != np.uint8:
            display_img = np.clip(display_img, 0, 255).astype(np.uint8)
        
        max_size = 350
        h, w = display_img.shape
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            display_img = cv2.resize(display_img, (int(w * scale), int(h * scale)))
        
        pil_img = Image.fromarray(display_img)
        tk_img = ImageTk.PhotoImage(pil_img)
        label.config(image=tk_img)
        label.image = tk_img
    
    def display_spectrum(self, fft_img, label):
        spectrum = np.log(1 + np.abs(fft_img))
        spectrum = cv2.normalize(spectrum, None, 0, 255, cv2.NORM_MINMAX)
        spectrum = spectrum.astype(np.uint8)
        
        max_size = 350
        h, w = spectrum.shape
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            spectrum = cv2.resize(spectrum, (int(w * scale), int(h * scale)))
        
        pil_img = Image.fromarray(spectrum)
        tk_img = ImageTk.PhotoImage(pil_img)
        label.config(image=tk_img)
        label.image = tk_img
    
    def save_result(self):
        if self.filtered_fft is None:
            messagebox.showwarning("警告", "请先应用滤波")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图像", "*.png"), ("JPEG图像", "*.jpg"), ("BMP图像", "*.bmp")]
        )
        if file_path:
            fft_ishift = fftpack.ifftshift(self.filtered_fft)
            img_filtered = fftpack.ifft2(fft_ishift)
            img_filtered = np.abs(img_filtered)
            img_filtered = cv2.normalize(img_filtered, None, 0, 255, cv2.NORM_MINMAX)
            img_filtered = img_filtered.astype(np.uint8)
            
            h, w = self.original_image.shape
            img_filtered = img_filtered[:h, :w]
            
            cv2.imwrite(file_path, img_filtered)
            messagebox.showinfo("成功", "图像已保存")


def main():
    root = tk.Tk()
    app = FrequencyFilter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
