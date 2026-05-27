import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import *
import cv2
import numpy as np
from skimage import color, filters, feature
from skimage.segmentation import slic
from skimage.util import img_as_ubyte
import os
import json
from PIL import Image, ImageTk
from scipy import ndimage


class NPRTool:
    def __init__(self, root):
        self.root = root
        self.root.title("非真实感渲染工具")
        self.root.geometry("1200x800")
        
        self.image = None
        self.processed_image = None
        self.image_path = None
        self.batch_files = []
        
        self.style_var = tk.StringVar(value="pencil")
        self.brush_size = tk.IntVar(value=5)
        self.style_intensity = tk.IntVar(value=5)
        self.pencil_noise = tk.IntVar(value=3)
        self.pencil_rotation = tk.IntVar(value=5)
        
        self.edge_method = tk.StringVar(value="canny")
        self.edge_intensity = tk.IntVar(value=5)
        self.show_contour = tk.BooleanVar(value=True)
        
        self.color_count = tk.IntVar(value=8)
        self.quant_method = tk.StringVar(value="slic")
        self.slic_segments = tk.IntVar(value=200)
        
        self.video_style = tk.StringVar(value="pencil")
        self.temporal_smooth = tk.IntVar(value=3)
        self.max_frames = tk.IntVar(value=100)
        
        self.content_weight = tk.IntVar(value=5)
        self.style_weight = tk.IntVar(value=5)
        self.preserve_color = tk.BooleanVar(value=False)
        
        self.artist_style = tk.StringVar(value="vangogh")
        self.artist_intensity = tk.IntVar(value=7)
        
        self.batch_style = tk.StringVar(value="pencil")
        self.use_individual_params = tk.BooleanVar(value=False)
        
        self.content_image = None
        self.style_image = None
        self.custom_artist_image = None
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W + tk.E + tk.N + tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky=(tk.W + tk.E + tk.N + tk.S), padx=5)
        
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=0, column=1, sticky=(tk.W + tk.E + tk.N + tk.S))
        display_frame.columnconfigure(0, weight=1)
        display_frame.rowconfigure(0, weight=1)
        
        self.setup_controls(control_frame)
        self.setup_display(display_frame)
        
    def setup_controls(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        style_frame = ttk.Frame(notebook, padding="10")
        edge_frame = ttk.Frame(notebook, padding="10")
        color_frame = ttk.Frame(notebook, padding="10")
        video_frame = ttk.Frame(notebook, padding="10")
        transfer_frame = ttk.Frame(notebook, padding="10")
        artist_frame = ttk.Frame(notebook, padding="10")
        batch_frame = ttk.Frame(notebook, padding="10")
        
        notebook.add(style_frame, text="风格渲染")
        notebook.add(edge_frame, text="边缘检测")
        notebook.add(color_frame, text="颜色量化")
        notebook.add(video_frame, text="视频风格化")
        notebook.add(transfer_frame, text="风格迁移")
        notebook.add(artist_frame, text="艺术家风格")
        notebook.add(batch_frame, text="批量处理")
        
        self.setup_style_controls(style_frame)
        self.setup_edge_controls(edge_frame)
        self.setup_color_controls(color_frame)
        self.setup_video_controls(video_frame)
        self.setup_transfer_controls(transfer_frame)
        self.setup_artist_controls(artist_frame)
        self.setup_batch_controls(batch_frame)
        
    def setup_style_controls(self, parent):
        ttk.Label(parent, text="风格选择", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        self.style_var = tk.StringVar(value="pencil")
        styles = [("铅笔画", "pencil"), ("油画", "oil"), ("水彩", "watercolor")]
        
        for text, value in styles:
            ttk.Radiobutton(parent, text=text, variable=self.style_var, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="笔触大小", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.brush_size = tk.IntVar(value=5)
        ttk.Scale(parent, from_=1, to=20, variable=self.brush_size, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.brush_size).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="风格强度", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.style_intensity = tk.IntVar(value=5)
        ttk.Scale(parent, from_=1, to=10, variable=self.style_intensity, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.style_intensity).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="铅笔画参数", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Label(parent, text="扰动噪声").pack(anchor=tk.W)
        self.pencil_noise = tk.IntVar(value=3)
        ttk.Scale(parent, from_=0, to=10, variable=self.pencil_noise, orient='horizontal').pack(fill='x', pady=2)
        ttk.Label(parent, textvariable=self.pencil_noise).pack(anchor=tk.W)
        
        ttk.Label(parent, text="线条旋转").pack(anchor=tk.W)
        self.pencil_rotation = tk.IntVar(value=5)
        ttk.Scale(parent, from_=0, to=20, variable=self.pencil_rotation, orient='horizontal').pack(fill='x', pady=2)
        ttk.Label(parent, textvariable=self.pencil_rotation).pack(anchor=tk.W)
        
        ttk.Button(parent, text="应用风格", command=self.apply_style).pack(fill='x', pady=10)
        
    def setup_edge_controls(self, parent):
        ttk.Label(parent, text="边缘检测方法", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        self.edge_method = tk.StringVar(value="canny")
        methods = [("Canny", "canny"), ("Sobel", "sobel"), ("Laplacian", "laplacian")]
        
        for text, value in methods:
            ttk.Radiobutton(parent, text=text, variable=self.edge_method, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="线条强度", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.edge_intensity = tk.IntVar(value=5)
        ttk.Scale(parent, from_=1, to=10, variable=self.edge_intensity, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.edge_intensity).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        self.show_contour = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="显示轮廓线", variable=self.show_contour).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="检测边缘", command=self.apply_edge_detection).pack(fill='x', pady=10)
        
    def setup_color_controls(self, parent):
        ttk.Label(parent, text="颜色量化", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Label(parent, text="颜色数量", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.color_count = tk.IntVar(value=8)
        ttk.Scale(parent, from_=2, to=32, variable=self.color_count, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.color_count).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        self.quant_method = tk.StringVar(value="slic")
        methods = [("超像素+多数投票(快)", "slic"), ("K-Means", "kmeans"), ("中位数切割", "median")]
        
        for text, value in methods:
            ttk.Radiobutton(parent, text=text, variable=self.quant_method, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Label(parent, text="超像素数量", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.slic_segments = tk.IntVar(value=200)
        ttk.Scale(parent, from_=50, to=1000, variable=self.slic_segments, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.slic_segments).pack(anchor=tk.W)
        
        ttk.Button(parent, text="量化颜色", command=self.apply_color_quantization).pack(fill='x', pady=10)
        
    def setup_video_controls(self, parent):
        ttk.Label(parent, text="视频风格化", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="选择视频", command=self.load_video).pack(fill='x', pady=5)
        
        self.video_label = ttk.Label(parent, text="未选择视频")
        self.video_label.pack(anchor=tk.W, pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="视频处理风格", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.video_style = tk.StringVar(value="pencil")
        video_styles = [("铅笔画", "pencil"), ("油画", "oil"), ("水彩", "watercolor"), ("边缘检测", "edge"), ("颜色量化", "quant"), ("艺术家风格", "artist")]
        
        for text, value in video_styles:
            ttk.Radiobutton(parent, text=text, variable=self.video_style, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="时间连续性", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.temporal_smooth = tk.IntVar(value=3)
        ttk.Scale(parent, from_=0, to=10, variable=self.temporal_smooth, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.temporal_smooth).pack(anchor=tk.W)
        
        ttk.Label(parent, text="处理帧数", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.max_frames = tk.IntVar(value=100)
        ttk.Scale(parent, from_=10, to=1000, variable=self.max_frames, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.max_frames).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(parent, text="开始处理视频", command=self.process_video).pack(fill='x', pady=10)
        
        self.video_progress = ttk.Progressbar(parent, orient='horizontal', mode='determinate')
        self.video_progress.pack(fill='x', pady=5)
        
        self.video_status = ttk.Label(parent, text="")
        self.video_status.pack(anchor=tk.W, pady=5)
        
    def setup_transfer_controls(self, parent):
        ttk.Label(parent, text="风格迁移融合", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="选择内容图", command=self.load_content_image).pack(fill='x', pady=2)
        self.content_label = ttk.Label(parent, text="未选择内容图")
        self.content_label.pack(anchor=tk.W, pady=2)
        
        ttk.Button(parent, text="选择风格图", command=self.load_style_image).pack(fill='x', pady=2)
        self.style_label = ttk.Label(parent, text="未选择风格图")
        self.style_label.pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="内容权重", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.content_weight = tk.IntVar(value=5)
        ttk.Scale(parent, from_=0, to=10, variable=self.content_weight, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.content_weight).pack(anchor=tk.W)
        
        ttk.Label(parent, text="风格权重", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.style_weight = tk.IntVar(value=5)
        ttk.Scale(parent, from_=0, to=10, variable=self.style_weight, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.style_weight).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        self.preserve_color = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="保留内容图颜色", variable=self.preserve_color).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="应用风格迁移", command=self.apply_style_transfer).pack(fill='x', pady=10)
        
    def setup_artist_controls(self, parent):
        ttk.Label(parent, text="艺术家风格库", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        self.artist_style = tk.StringVar(value="vangogh")
        artists = [
            ("梵高 (星月夜)", "vangogh"),
            ("毕加索 (立体主义)", "picasso"),
            ("莫奈 (印象派)", "monet"),
            ("达芬奇 (素描)", "davinci"),
            ("达利 (超现实)", "dali"),
            ("毕沙罗 (点彩)", "pissarro"),
            ("自定义风格图", "custom")
        ]
        
        for text, value in artists:
            ttk.Radiobutton(parent, text=text, variable=self.artist_style, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(parent, text="加载自定义风格图", command=self.load_custom_artist_style).pack(fill='x', pady=5)
        
        ttk.Label(parent, text="风格强度", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.artist_intensity = tk.IntVar(value=7)
        ttk.Scale(parent, from_=1, to=10, variable=self.artist_intensity, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(parent, textvariable=self.artist_intensity).pack(anchor=tk.W)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(parent, text="应用艺术家风格", command=self.apply_artist_style).pack(fill='x', pady=10)
        
    def setup_batch_controls(self, parent):
        ttk.Label(parent, text="批量图像处理", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="选择文件夹", command=self.select_batch_folder).pack(fill='x', pady=5)
        
        self.batch_label = ttk.Label(parent, text="已选择: 0 张图片")
        self.batch_label.pack(anchor=tk.W, pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="参数配置", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        ttk.Button(parent, text="保存当前参数", command=self.save_current_params).pack(fill='x', pady=2)
        ttk.Button(parent, text="加载参数文件", command=self.load_params_file).pack(fill='x', pady=2)
        
        self.use_individual_params = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="使用独立参数文件(每图一个json)", variable=self.use_individual_params).pack(anchor=tk.W, pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(parent, text="默认处理风格", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.batch_style = tk.StringVar(value="pencil")
        batch_styles = [("铅笔画", "pencil"), ("油画", "oil"), ("水彩", "watercolor"), ("边缘检测", "edge"), ("颜色量化", "quant")]
        
        for text, value in batch_styles:
            ttk.Radiobutton(parent, text=text, variable=self.batch_style, value=value).pack(anchor=tk.W, pady=2)
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(parent, text="开始批量处理", command=self.start_batch_processing).pack(fill='x', pady=10)
        
        self.progress = ttk.Progressbar(parent, orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', pady=5)
        
        self.batch_status = ttk.Label(parent, text="")
        self.batch_status.pack(anchor=tk.W, pady=5)
        
    def setup_display(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="打开图片", command=self.load_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="保存图片", command=self.save_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置", command=self.reset_image).pack(side=tk.LEFT, padx=5)
        
        image_frame = ttk.Frame(parent)
        image_frame.pack(fill=tk.BOTH, expand=True)
        image_frame.columnconfigure(0, weight=1)
        image_frame.columnconfigure(1, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        original_frame = ttk.LabelFrame(image_frame, text="原图")
        original_frame.grid(row=0, column=0, sticky=(tk.W + tk.E + tk.N + tk.S), padx=5)
        original_frame.columnconfigure(0, weight=1)
        original_frame.rowconfigure(0, weight=1)
        
        processed_frame = ttk.LabelFrame(image_frame, text="处理后")
        processed_frame.grid(row=0, column=1, sticky=(tk.W + tk.E + tk.N + tk.S), padx=5)
        processed_frame.columnconfigure(0, weight=1)
        processed_frame.rowconfigure(0, weight=1)
        
        self.original_canvas = tk.Canvas(original_frame, bg='gray')
        self.original_canvas.grid(row=0, column=0, sticky=(tk.W + tk.E + tk.N + tk.S))
        
        self.processed_canvas = tk.Canvas(processed_frame, bg='gray')
        self.processed_canvas.grid(row=0, column=0, sticky=(tk.W + tk.E + tk.N + tk.S))
        
    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            self.image_path = file_path
            self.image = cv2.imread(file_path)
            self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            self.processed_image = self.image.copy()
            self.display_images()
            
    def display_images(self):
        if self.image is not None:
            self.display_on_canvas(self.image, self.original_canvas)
        if self.processed_image is not None:
            self.display_on_canvas(self.processed_image, self.processed_canvas)
            
    def display_on_canvas(self, img, canvas):
        canvas.update()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 400, 400
        
        img_h, img_w = img.shape[:2]
        scale = min(canvas_width / img_w, canvas_height / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        
        resized = cv2.resize(img, (new_w, new_h))
        
        pil_image = Image.fromarray(resized)
        tk_image = ImageTk.PhotoImage(pil_image)
        
        canvas.delete("all")
        x = (canvas_width - new_w) // 2
        y = (canvas_height - new_h) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=tk_image)
        canvas.image = tk_image
        
    def save_image(self):
        if self.processed_image is not None:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG文件", "*.png"), ("JPEG文件", "*.jpg")]
            )
            if file_path:
                save_img = cv2.cvtColor(self.processed_image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(file_path, save_img)
                messagebox.showinfo("成功", "图片已保存！")
                
    def reset_image(self):
        if self.image is not None:
            self.processed_image = self.image.copy()
            self.display_images()
            
    def apply_style(self):
        if self.image is None:
            messagebox.showwarning("警告", "请先打开图片！")
            return
            
        style = self.style_var.get()
        brush = self.brush_size.get()
        intensity = self.style_intensity.get()
        
        if style == "pencil":
            noise = self.pencil_noise.get()
            rotation = self.pencil_rotation.get()
            self.processed_image = self.pencil_sketch(self.image, brush, intensity, noise, rotation)
        elif style == "oil":
            self.processed_image = self.oil_painting(self.image, brush, intensity)
        elif style == "watercolor":
            self.processed_image = self.watercolor(self.image, brush, intensity)
            
        self.display_images()
        
    def pencil_sketch(self, img, brush, intensity, noise=3, rotation=5):
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        
        sketch = cv2.divide(gray, blurred, scale=256.0)
        
        if rotation > 0:
            angle_range = rotation * 0.1
            h, w = sketch.shape
            center = (w // 2, h // 2)
            random_angle = np.random.uniform(-angle_range, angle_range)
            M = cv2.getRotationMatrix2D(center, random_angle, 1.0)
            sketch = cv2.warpAffine(sketch, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        
        if noise > 0:
            noise_level = noise * 2
            noise_arr = np.random.normal(0, noise_level, sketch.shape)
            sketch = np.clip(sketch + noise_arr, 0, 255)
        
        sketch = sketch.astype(np.uint8)
        
        sketch = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)
        
        if intensity > 5:
            edges = cv2.Canny(gray, 50, 150)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            sketch = cv2.subtract(sketch, edges * (intensity - 5) / 10)
            sketch = np.clip(sketch, 0, 255).astype(np.uint8)
            
        return sketch
        
    def oil_painting(self, img, brush, intensity):
        kernel_size = brush * 2 + 1
        result = cv2.medianBlur(img, kernel_size)
        
        lab = cv2.cvtColor(result, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=intensity/2, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l,a,b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        
        edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), 50, 150)
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        enhanced = cv2.subtract(enhanced, edges_colored * (intensity / 20))
        enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
        
        return enhanced
        
    def watercolor(self, img, brush, intensity):
        bilateral = cv2.bilateralFilter(img, d=brush*2, sigmaColor=intensity*10, sigmaSpace=intensity*5)
        
        lab = cv2.cvtColor(bilateral, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l,a,b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        
        kernel = np.ones((3,3), np.float32)/9
        smoothed = cv2.filter2D(enhanced, -1, kernel)
        
        return smoothed
        
    def apply_edge_detection(self):
        if self.image is None:
            messagebox.showwarning("警告", "请先打开图片！")
            return
            
        method = self.edge_method.get()
        intensity = self.edge_intensity.get()
        
        gray = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)
        
        if method == "canny":
            low = 50 - intensity * 5
            high = 150 - intensity * 10
            edges = cv2.Canny(gray, low, high)
        elif method == "sobel":
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobelx**2 + sobely**2)
            edges = np.uint8(edges / edges.max() * 255)
        elif method == "laplacian":
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.absolute(edges)
            edges = np.uint8(edges / edges.max() * 255)
        
        edges = cv2.multiply(edges, intensity / 5)
        edges = np.clip(edges, 0, 255).astype(np.uint8)
        
        if self.show_contour.get():
            result = np.ones_like(self.image) * 255
            result[edges > 50] = 0
            self.processed_image = result.astype(np.uint8)
        else:
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            self.processed_image = edges_colored
            
        self.display_images()
        
    def apply_color_quantization(self):
        if self.image is None:
            messagebox.showwarning("警告", "请先打开图片！")
            return
            
        n_colors = self.color_count.get()
        method = self.quant_method.get()
        
        if method == "slic":
            n_segments = self.slic_segments.get()
            self.processed_image = self.quantize_slic(self.image, n_colors, n_segments)
        elif method == "kmeans":
            self.processed_image = self.quantize_kmeans(self.image, n_colors)
        elif method == "median":
            self.processed_image = self.quantize_median(self.image, n_colors)
            
        self.display_images()
        
    def quantize_slic(self, img, n_colors, n_segments=200):
        segments = slic(img, n_segments=n_segments, compactness=10, sigma=1, start_label=0)
        
        result = np.zeros_like(img, dtype=np.uint8)
        
        for segment_id in np.unique(segments):
            mask = (segments == segment_id)
            segment_pixels = img[mask]
            
            if len(segment_pixels) > 0:
                pixels_float = np.float32(segment_pixels)
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
                _, labels, centers = cv2.kmeans(pixels_float, min(n_colors, len(segment_pixels)), None, criteria, 3, cv2.KMEANS_RANDOM_CENTERS)
                
                label_counts = np.bincount(labels.flatten())
                majority_label = np.argmax(label_counts)
                majority_color = centers[majority_label]
                
                result[mask] = majority_color.astype(np.uint8)
        
        return result
        
    def quantize_kmeans(self, img, n_colors):
        pixels = img.reshape((-1, 3))
        pixels = np.float32(pixels)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        centers = np.uint8(centers)
        result = centers[labels.flatten()]
        result = result.reshape(img.shape)
        
        return result
        
    def quantize_median(self, img, n_colors):
        result = img.copy()
        for i in range(3):
            channel = result[:,:,i]
            levels = np.linspace(0, 255, n_colors + 1)
            for j in range(n_colors):
                mask = (channel >= levels[j]) & (channel < levels[j+1])
                result[:,:,i][mask] = (levels[j] + levels[j+1]) // 2
        return result
        
    def get_current_params(self):
        params = {
            'style': self.style_var.get(),
            'brush_size': self.brush_size.get(),
            'style_intensity': self.style_intensity.get(),
            'pencil_noise': self.pencil_noise.get(),
            'pencil_rotation': self.pencil_rotation.get(),
            'edge_method': self.edge_method.get(),
            'edge_intensity': self.edge_intensity.get(),
            'show_contour': self.show_contour.get(),
            'color_count': self.color_count.get(),
            'quant_method': self.quant_method.get(),
            'slic_segments': self.slic_segments.get(),
            'batch_style': self.batch_style.get(),
            'video_style': self.video_style.get(),
            'temporal_smooth': self.temporal_smooth.get(),
            'content_weight': self.content_weight.get(),
            'style_weight': self.style_weight.get(),
            'preserve_color': self.preserve_color.get(),
            'artist_style': self.artist_style.get(),
            'artist_intensity': self.artist_intensity.get()
        }
        return params
        
    def apply_params(self, params):
        self.style_var.set(params.get('style', 'pencil'))
        self.brush_size.set(params.get('brush_size', 5))
        self.style_intensity.set(params.get('style_intensity', 5))
        self.pencil_noise.set(params.get('pencil_noise', 3))
        self.pencil_rotation.set(params.get('pencil_rotation', 5))
        self.edge_method.set(params.get('edge_method', 'canny'))
        self.edge_intensity.set(params.get('edge_intensity', 5))
        self.show_contour.set(params.get('show_contour', True))
        self.color_count.set(params.get('color_count', 8))
        self.quant_method.set(params.get('quant_method', 'slic'))
        self.slic_segments.set(params.get('slic_segments', 200))
        self.batch_style.set(params.get('batch_style', 'pencil'))
        self.video_style.set(params.get('video_style', 'pencil'))
        self.temporal_smooth.set(params.get('temporal_smooth', 3))
        self.content_weight.set(params.get('content_weight', 5))
        self.style_weight.set(params.get('style_weight', 5))
        self.preserve_color.set(params.get('preserve_color', False))
        self.artist_style.set(params.get('artist_style', 'vangogh'))
        self.artist_intensity.set(params.get('artist_intensity', 7))
        
    def save_current_params(self):
        params = self.get_current_params()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", "参数已保存！")
            
    def load_params_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                params = json.load(f)
            self.apply_params(params)
            messagebox.showinfo("成功", "参数已加载！")
            
    def select_batch_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.batch_files = []
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                    self.batch_files.append(os.path.join(folder_path, filename))
            self.batch_label.config(text=f"已选择: {len(self.batch_files)} 张图片")
            
    def process_image_with_params(self, img, params):
        style = params.get('batch_style', 'pencil')
        
        if style == "pencil":
            brush = params.get('brush_size', 5)
            intensity = params.get('style_intensity', 5)
            noise = params.get('pencil_noise', 3)
            rotation = params.get('pencil_rotation', 5)
            return self.pencil_sketch(img, brush, intensity, noise, rotation)
        elif style == "oil":
            brush = params.get('brush_size', 5)
            intensity = params.get('style_intensity', 5)
            return self.oil_painting(img, brush, intensity)
        elif style == "watercolor":
            brush = params.get('brush_size', 5)
            intensity = params.get('style_intensity', 5)
            return self.watercolor(img, brush, intensity)
        elif style == "edge":
            method = params.get('edge_method', 'canny')
            intensity = params.get('edge_intensity', 5)
            show_contour = params.get('show_contour', True)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            if method == "canny":
                low = 50 - intensity * 5
                high = 150 - intensity * 10
                edges = cv2.Canny(gray, low, high)
            elif method == "sobel":
                sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                edges = np.sqrt(sobelx**2 + sobely**2)
                edges = np.uint8(edges / edges.max() * 255)
            elif method == "laplacian":
                edges = cv2.Laplacian(gray, cv2.CV_64F)
                edges = np.absolute(edges)
                edges = np.uint8(edges / edges.max() * 255)
            
            edges = cv2.multiply(edges, intensity / 5)
            edges = np.clip(edges, 0, 255).astype(np.uint8)
            
            if show_contour:
                result = np.ones_like(img) * 255
                result[edges > 50] = 0
                return result.astype(np.uint8)
            else:
                return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        elif style == "quant":
            n_colors = params.get('color_count', 8)
            method = params.get('quant_method', 'slic')
            n_segments = params.get('slic_segments', 200)
            
            if method == "slic":
                return self.quantize_slic(img, n_colors, n_segments)
            elif method == "kmeans":
                return self.quantize_kmeans(img, n_colors)
            else:
                return self.quantize_median(img, n_colors)
        
        return img
            
    def start_batch_processing(self):
        if not self.batch_files:
            messagebox.showwarning("警告", "请先选择文件夹！")
            return
            
        output_folder = filedialog.askdirectory(title="选择输出文件夹")
        if not output_folder:
            return
            
        default_params = self.get_current_params()
        use_individual = self.use_individual_params.get()
        total = len(self.batch_files)
        
        self.progress['maximum'] = total
        self.progress['value'] = 0
        
        success_count = 0
        error_count = 0
        
        for i, file_path in enumerate(self.batch_files):
            try:
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)
                self.batch_status.config(text=f"处理中: {filename}")
                
                img = cv2.imread(file_path)
                if img is None:
                    error_count += 1
                    continue
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                params = default_params.copy()
                if use_individual:
                    param_file = os.path.join(os.path.dirname(file_path), f"{name}.json")
                    if os.path.exists(param_file):
                        with open(param_file, 'r', encoding='utf-8') as f:
                            individual_params = json.load(f)
                        params.update(individual_params)
                
                result = self.process_image_with_params(img, params)
                
                style = params.get('batch_style', 'pencil')
                output_path = os.path.join(output_folder, f"{name}_{style}{ext}")
                
                result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
                cv2.imwrite(output_path, result_bgr)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"处理 {file_path} 时出错: {e}")
            
            self.progress['value'] = i + 1
            self.root.update()
        
        self.batch_status.config(text="")
        messagebox.showinfo("完成", f"批量处理完成！成功: {success_count} 张, 失败: {error_count} 张")
        
    def load_video(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if file_path:
            self.video_path = file_path
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.video_label.config(text=f"{os.path.basename(file_path)}\n{width}x{height}, {fps}fps, {total_frames}帧")
                cap.release()
    
    def process_video(self):
        if not hasattr(self, 'video_path') or not os.path.exists(self.video_path):
            messagebox.showwarning("警告", "请先选择视频！")
            return
            
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("AVI文件", "*.avi")]
        )
        if not output_path:
            return
            
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件！")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), self.max_frames.get())
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        style = self.video_style.get()
        temporal_window = self.temporal_smooth.get()
        frame_buffer = []
        
        self.video_progress['maximum'] = total_frames
        self.video_progress['value'] = 0
        
        frame_count = 0
        success_count = 0
        
        while frame_count < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.video_status.config(text=f"处理帧 {frame_count+1}/{total_frames}")
            
            try:
                params = self.get_current_params()
                params['batch_style'] = style
                
                if style == "artist":
                    processed = self.apply_artist_style_to_image(frame_rgb)
                else:
                    processed = self.process_image_with_params(frame_rgb, params)
                
                if temporal_window > 0 and len(frame_buffer) > 0:
                    alpha = 1.0 / (temporal_window + 1)
                    for prev_frame in frame_buffer[-temporal_window:]:
                        processed = cv2.addWeighted(processed, 1 - alpha, prev_frame, alpha, 0)
                
                frame_buffer.append(processed.copy())
                if len(frame_buffer) > temporal_window + 1:
                    frame_buffer.pop(0)
                
                processed_bgr = cv2.cvtColor(processed, cv2.COLOR_RGB2BGR)
                out.write(processed_bgr)
                success_count += 1
                
            except Exception as e:
                print(f"处理帧 {frame_count} 时出错: {e}")
                out.write(frame)
            
            frame_count += 1
            self.video_progress['value'] = frame_count
            self.root.update()
        
        cap.release()
        out.release()
        
        self.video_status.config(text="")
        messagebox.showinfo("完成", f"视频处理完成！成功处理 {success_count} 帧\n输出: {output_path}")
        
    def load_content_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            self.content_image = cv2.imread(file_path)
            self.content_image = cv2.cvtColor(self.content_image, cv2.COLOR_BGR2RGB)
            self.content_label.config(text=os.path.basename(file_path))
            self.image = self.content_image
            self.processed_image = self.content_image.copy()
            self.display_images()
    
    def load_style_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            self.style_image = cv2.imread(file_path)
            self.style_image = cv2.cvtColor(self.style_image, cv2.COLOR_BGR2RGB)
            self.style_label.config(text=os.path.basename(file_path))
    
    def apply_style_transfer(self):
        if not hasattr(self, 'content_image') or self.content_image is None:
            messagebox.showwarning("警告", "请先选择内容图！")
            return
        if not hasattr(self, 'style_image') or self.style_image is None:
            messagebox.showwarning("警告", "请先选择风格图！")
            return
            
        content_w = self.content_weight.get()
        style_w = self.style_weight.get()
        total_w = content_w + style_w
        if total_w == 0:
            messagebox.showwarning("警告", "内容权重和风格权重不能同时为0！")
            return
            
        content_alpha = content_w / total_w
        style_alpha = style_w / total_w
        
        content = self.content_image
        style_img = cv2.resize(self.style_image, (content.shape[1], content.shape[0]))
        
        content_lab = cv2.cvtColor(content, cv2.COLOR_RGB2LAB)
        style_lab = cv2.cvtColor(style_img, cv2.COLOR_RGB2LAB)
        
        content_l, content_a, content_b = cv2.split(content_lab)
        style_l, style_a, style_b = cv2.split(style_lab)
        
        if self.preserve_color.get():
            result_l = cv2.addWeighted(content_l, content_alpha, style_l, style_alpha, 0)
            result_a = content_a
            result_b = content_b
        else:
            result_l = cv2.addWeighted(content_l, content_alpha, style_l, style_alpha, 0)
            result_a = cv2.addWeighted(content_a, content_alpha, style_a, style_alpha, 0)
            result_b = cv2.addWeighted(content_b, content_alpha, style_b, style_alpha, 0)
        
        content_segments = slic(content, n_segments=200, compactness=10, sigma=1, start_label=0)
        
        for segment_id in np.unique(content_segments):
            mask = (content_segments == segment_id)
            segment_content = content[mask]
            segment_style = style_img[mask]
            
            content_mean = np.mean(segment_content, axis=0)
            style_mean = np.mean(segment_style, axis=0)
            
            blended = content_mean * content_alpha + style_mean * style_alpha
            result_lab = cv2.merge([result_l, result_a, result_b])
            result_rgb = cv2.cvtColor(result_lab, cv2.COLOR_LAB2RGB)
            
            result_rgb[mask] = result_rgb[mask] * 0.7 + blended * 0.3
        
        result_rgb = np.clip(result_rgb, 0, 255).astype(np.uint8)
        
        blurred_content = cv2.GaussianBlur(content, (15, 15), 0)
        blurred_style = cv2.GaussianBlur(style_img, (15, 15), 0)
        
        content_edges = cv2.Canny(cv2.cvtColor(content, cv2.COLOR_RGB2GRAY), 50, 150)
        style_texture = cv2.Laplacian(cv2.cvtColor(style_img, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
        style_texture = np.uint8(np.absolute(style_texture))
        
        result_detail = cv2.addWeighted(blurred_content, content_alpha, blurred_style, style_alpha, 0)
        
        content_edges_colored = cv2.cvtColor(content_edges, cv2.COLOR_GRAY2RGB)
        style_texture_colored = cv2.cvtColor(style_texture, cv2.COLOR_GRAY2RGB)
        
        result_detail = cv2.add(result_detail, content_edges_colored * (content_alpha * 0.3))
        result_detail = cv2.add(result_detail, style_texture_colored * (style_alpha * 0.3))
        
        final_result = cv2.addWeighted(result_rgb, 0.6, result_detail, 0.4, 0)
        final_result = np.clip(final_result, 0, 255).astype(np.uint8)
        
        self.processed_image = final_result
        self.display_images()
    
    def load_custom_artist_style(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        if file_path:
            self.custom_artist_image = cv2.imread(file_path)
            self.custom_artist_image = cv2.cvtColor(self.custom_artist_image, cv2.COLOR_BGR2RGB)
            self.artist_style.set("custom")
    
    def get_artist_presets(self):
        presets = {
            'vangogh': {
                'name': '梵高',
                'color_shift': np.array([30, 20, -10]),
                'brush_size': 7,
                'contrast': 1.3,
                'saturation': 1.5,
                'edge_intensity': 8,
                'texture_level': 7
            },
            'picasso': {
                'name': '毕加索',
                'color_shift': np.array([-20, 10, 30]),
                'brush_size': 5,
                'contrast': 1.5,
                'saturation': 0.8,
                'edge_intensity': 6,
                'texture_level': 5
            },
            'monet': {
                'name': '莫奈',
                'color_shift': np.array([20, 30, 10]),
                'brush_size': 9,
                'contrast': 0.9,
                'saturation': 1.2,
                'edge_intensity': 3,
                'texture_level': 8
            },
            'davinci': {
                'name': '达芬奇',
                'color_shift': np.array([0, 0, 0]),
                'brush_size': 3,
                'contrast': 1.2,
                'saturation': 0.3,
                'edge_intensity': 7,
                'texture_level': 4
            },
            'dali': {
                'name': '达利',
                'color_shift': np.array([40, -10, -20]),
                'brush_size': 6,
                'contrast': 1.6,
                'saturation': 1.4,
                'edge_intensity': 9,
                'texture_level': 9
            },
            'pissarro': {
                'name': '毕沙罗',
                'color_shift': np.array([15, 25, 5]),
                'brush_size': 8,
                'contrast': 1.1,
                'saturation': 1.3,
                'edge_intensity': 4,
                'texture_level': 10
            }
        }
        return presets
    
    def apply_artist_style_to_image(self, img):
        artist = self.artist_style.get()
        intensity = self.artist_intensity.get() / 10.0
        
        if artist == 'custom' and hasattr(self, 'custom_artist_image') and self.custom_artist_image is not None:
            style_img = cv2.resize(self.custom_artist_image, (img.shape[1], img.shape[0]))
            
            result_lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
            style_lab = cv2.cvtColor(style_img, cv2.COLOR_RGB2LAB)
            
            result_l, result_a, result_b = cv2.split(result_lab)
            style_l, style_a, style_b = cv2.split(style_lab)
            
            result_l = cv2.addWeighted(result_l, 1 - intensity, style_l, intensity, 0)
            result_a = cv2.addWeighted(result_a, 1 - intensity, style_a, intensity, 0)
            result_b = cv2.addWeighted(result_b, 1 - intensity, style_b, intensity, 0)
            
            result = cv2.merge([result_l, result_a, result_b])
            result = cv2.cvtColor(result, cv2.COLOR_LAB2RGB)
            
            return np.clip(result, 0, 255).astype(np.uint8)
        
        presets = self.get_artist_presets()
        preset = presets.get(artist, presets['vangogh'])
        
        result = img.copy()
        
        result = result.astype(np.float32)
        color_shift = preset['color_shift'] * intensity
        for i in range(3):
            result[:,:,i] = np.clip(result[:,:,i] + color_shift[i], 0, 255)
        
        result = cv2.convertScaleAbs(result, alpha=preset['contrast'], beta=0)
        
        hsv = cv2.cvtColor(result, cv2.COLOR_RGB2HSV)
        hsv[:,:,1] = np.clip(hsv[:,:,1] * preset['saturation'], 0, 255)
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        brush = preset['brush_size']
        if brush > 0:
            kernel_size = brush * 2 + 1
            result = cv2.medianBlur(result, kernel_size)
        
        if preset['texture_level'] > 0:
            texture = np.random.normal(0, preset['texture_level'] * intensity * 2, result.shape)
            result = np.clip(result.astype(np.float32) + texture, 0, 255).astype(np.uint8)
        
        if preset['edge_intensity'] > 0:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            edge_strength = preset['edge_intensity'] * intensity * 0.05
            result = cv2.subtract(result, (edges_colored * edge_strength).astype(np.uint8))
            result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def apply_artist_style(self):
        if self.image is None:
            messagebox.showwarning("警告", "请先打开图片！")
            return
            
        if self.artist_style.get() == 'custom' and (not hasattr(self, 'custom_artist_image') or self.custom_artist_image is None):
            messagebox.showwarning("警告", "请先加载自定义风格图！")
            return
            
        self.processed_image = self.apply_artist_style_to_image(self.image)
        self.display_images()


if __name__ == "__main__":
    root = tk.Tk()
    app = NPRTool(root)
    root.mainloop()
