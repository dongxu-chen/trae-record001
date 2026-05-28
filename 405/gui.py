import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import cv2
from PIL import Image, ImageTk
from poisson_editing import PoissonEditing, VideoPoissonEditor, HAS_CUDA
from typing import List, Tuple, Optional


class MaskItem:
    def __init__(self, mask: np.ndarray, offset: Tuple[int, int] = (0, 0), mix_weight: float = 1.0):
        self.mask = mask
        self.offset = offset
        self.mix_weight = mix_weight
        self.visible = True
        self.color = np.random.randint(0, 255, 3).tolist()


class OffscreenCanvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.mask_buffer = np.zeros((height, width), dtype=np.uint8)
        self.display_buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self.dirty_region = None

    def set_base_image(self, image: np.ndarray):
        if len(image.shape) == 3:
            self.display_buffer = image.copy()
        else:
            self.display_buffer = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        self.mask_buffer = np.zeros((self.height, self.width), dtype=np.uint8)
        self.dirty_region = (0, 0, self.width, self.height)

    def draw_brush(self, x: int, y: int, size: int, color: int = 255):
        x, y = int(x), int(y)
        cv2.circle(self.mask_buffer, (x, y), size, color, -1)
        
        x1, y1 = max(0, x - size - 1), max(0, y - size - 1)
        x2, y2 = min(self.width, x + size + 1), min(self.height, y + size + 1)
        
        self._update_dirty_region(x1, y1, x2, y2)

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, size: int, color: int = 255):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        cv2.line(self.mask_buffer, (x1, y1), (x2, y2), color, size)
        
        px1, py1 = min(x1, x2) - size, min(y1, y2) - size
        px2, py2 = max(x1, x2) + size, max(y1, y2) + size
        self._update_dirty_region(px1, py1, px2, py2)

    def _update_dirty_region(self, x1: int, y1: int, x2: int, y2: int):
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(self.width, x2), min(self.height, y2)
        
        if self.dirty_region is None:
            self.dirty_region = (x1, y1, x2, y2)
        else:
            dx1, dy1, dx2, dy2 = self.dirty_region
            self.dirty_region = (
                min(dx1, x1), min(dy1, y1),
                max(dx2, x2), max(dy2, y2)
            )

    def clear_dirty_region(self):
        self.dirty_region = None

    def get_dirty_region(self) -> Optional[Tuple[int, int, int, int]]:
        return self.dirty_region

    def get_mask(self) -> np.ndarray:
        return self.mask_buffer.copy()

    def set_mask(self, mask: np.ndarray):
        self.mask_buffer = mask.copy()
        self.dirty_region = (0, 0, self.width, self.height)

    def clear_mask(self):
        self.mask_buffer.fill(0)
        self.dirty_region = (0, 0, self.width, self.height)


class ImageCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs, highlightthickness=0)
        
        self.image: Optional[np.ndarray] = None
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.mask_items: List[MaskItem] = []
        self.offscreen: Optional[OffscreenCanvas] = None
        
        self.drawing = False
        self.last_point: Optional[Tuple[int, int]] = None
        self.brush_size = 20
        self.tool = "brush"
        self.scale = 1.0
        self.scroll_x = 0
        self.scroll_y = 0
        
        self.overlay_photo: Optional[ImageTk.PhotoImage] = None
        self._is_updating = False
        self._pending_update = False
        
        self.bind("<Button-1>", self.on_mouse_down)
        self.bind("<B1-Motion>", self.on_mouse_move)
        self.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.bind("<MouseWheel>", self.on_scroll)
        self.bind("<Configure>", self.on_resize)
        
        self.canvas_x = 0
        self.canvas_y = 0

    def set_image(self, image: np.ndarray):
        self.image = image
        self.mask_items = []
        
        h, w = image.shape[:2]
        self.offscreen = OffscreenCanvas(w, h)
        self.offscreen.set_base_image(image)
        
        self.config(scrollregion=(0, 0, w, h))
        self.update_display(full_refresh=True)

    def add_mask(self, mask: np.ndarray, offset: Tuple[int, int] = (0, 0), mix_weight: float = 1.0):
        self.mask_items.append(MaskItem(mask, offset, mix_weight))
        self.update_display(full_refresh=True)

    def clear_masks(self):
        self.mask_items = []
        if self.offscreen:
            self.offscreen.clear_mask()
        self.update_display(full_refresh=True)

    def screen_to_image(self, sx: int, sy: int) -> Tuple[int, int]:
        x = int((sx + self.canvas_x) / self.scale)
        y = int((sy + self.canvas_y) / self.scale)
        return x, y

    def image_to_screen(self, ix: int, iy: int) -> Tuple[int, int]:
        x = int(ix * self.scale - self.canvas_x)
        y = int(iy * self.scale - self.canvas_y)
        return x, y

    def _render_full(self) -> np.ndarray:
        if self.image is None:
            return np.zeros((1, 1, 3), dtype=np.uint8)
        
        display_img = self.image.copy()
        
        for mask_item in self.mask_items:
            if mask_item.visible:
                self._apply_mask_overlay(display_img, mask_item)
        
        if self.offscreen is not None and self.offscreen.mask_buffer.sum() > 0:
            overlay = display_img.copy()
            alpha = 0.3
            color = np.array([0, 255, 0], dtype=np.uint8)
            mask = self.offscreen.mask_buffer
            overlay[mask > 127] = (1 - alpha) * overlay[mask > 127] + alpha * color
            display_img = overlay
        
        return display_img

    def _apply_mask_overlay(self, display_img: np.ndarray, mask_item: MaskItem):
        mask = mask_item.mask
        dy, dx = mask_item.offset
        h, w = mask.shape[:2]
        
        img_h, img_w = display_img.shape[:2]
        y1, y2 = max(0, dy), min(img_h, dy + h)
        x1, x2 = max(0, dx), min(img_w, dx + w)
        
        my1, my2 = max(0, -dy), min(h, img_h - dy)
        mx1, mx2 = max(0, -dx), min(w, img_w - dx)
        
        if y2 > y1 and x2 > x1:
            mask_roi = mask[my1:my2, mx1:mx2]
            overlay = display_img[y1:y2, x1:x2].copy()
            alpha = 0.4
            color = np.array(mask_item.color, dtype=np.uint8)
            overlay[mask_roi > 127] = (1 - alpha) * overlay[mask_roi > 127] + alpha * color
            display_img[y1:y2, x1:x2] = overlay
            
            contours, _ = cv2.findContours(mask_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                cnt[:, :, 0] += x1
                cnt[:, :, 1] += y1
            cv2.drawContours(display_img, contours, -1, color.tolist(), 2)

    def update_display(self, full_refresh: bool = False):
        if self.image is None or self._is_updating:
            self._pending_update = not full_refresh
            return
        
        self._is_updating = True
        self._pending_update = False
        
        try:
            display_img = self._render_full()
            
            if len(display_img.shape) == 3:
                display_img = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
            
            h, w = display_img.shape[:2]
            new_h, new_w = int(h * self.scale), int(w * self.scale)
            
            if new_h > 0 and new_w > 0:
                if self.scale != 1.0:
                    display_img = cv2.resize(display_img, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            
            self.photo = ImageTk.PhotoImage(Image.fromarray(display_img))
            self.delete("all")
            self.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.config(scrollregion=(0, 0, new_w, new_h))
            
            if self.offscreen:
                self.offscreen.clear_dirty_region()
        finally:
            self._is_updating = False
    
    def on_mouse_down(self, event):
        if self.image is None or self.offscreen is None:
            return
        
        x, y = self.screen_to_image(event.x, event.y)
        self.drawing = True
        self.last_point = (x, y)
        
        color = 255 if self.tool in ["brush", "circle", "rect"] else 0
        if self.tool in ["brush", "eraser", "circle"]:
            self.offscreen.draw_brush(x, y, self.brush_size, color)
        elif self.tool == "rect":
            size = self.brush_size
            cv2.rectangle(self.offscreen.mask_buffer, 
                        (x - size, y - size), (x + size, y + size), color, -1)
            self.offscreen.dirty_region = (x - size, y - size, x + size, y + size)
        
        self.after_idle(self._incremental_update)

    def on_mouse_move(self, event):
        if not self.drawing or self.offscreen is None:
            return
        
        x, y = self.screen_to_image(event.x, event.y)
        
        if self.last_point is not None:
            color = 255 if self.tool in ["brush", "circle", "rect"] else 0
            if self.tool in ["brush", "eraser"]:
                self.offscreen.draw_line(
                    self.last_point[0], self.last_point[1],
                    x, y, self.brush_size * 2 + 1, color
                )
            elif self.tool in ["circle", "rect"]:
                self.offscreen.draw_brush(x, y, self.brush_size, color)
        
        self.last_point = (x, y)
        
        if not self._pending_update:
            self._pending_update = True
            self.after(16, self._incremental_update)

    def on_mouse_up(self, event):
        self.drawing = False
        self.last_point = None
        
        if self._pending_update:
            self.after_idle(self._incremental_update)

    def _incremental_update(self):
        self.update_display(full_refresh=False)

    def on_scroll(self, event):
        if event.delta > 0:
            self.scale = min(3.0, self.scale * 1.1)
        else:
            self.scale = max(0.2, self.scale / 1.1)
        self.update_display(full_refresh=True)

    def on_resize(self, event):
        pass

    def save_current_mask(self) -> bool:
        if self.offscreen is None or self.offscreen.mask_buffer.sum() == 0:
            return False
        
        self.mask_items.append(MaskItem(self.offscreen.get_mask()))
        self.offscreen.clear_mask()
        self.update_display(full_refresh=True)
        return True

    def get_all_masks(self) -> List[MaskItem]:
        return [item for item in self.mask_items if item.visible]


class PoissonEditingGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("泊松图像编辑 (多网格法+羽化) - Poisson Image Editing")
        self.root.geometry("1200x800")
        
        self.src_img: Optional[np.ndarray] = None
        self.dst_img: Optional[np.ndarray] = None
        self.result_img: Optional[np.ndarray] = None
        self.poisson = PoissonEditing(solver_type='multigrid', use_gpu=HAS_CUDA)
        self.video_editor: Optional[VideoPoissonEditor] = None
        self.video_path: Optional[str] = None
        self.is_processing_video = False
        
        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)
        
        self.center_panel = tk.Frame(main_frame)
        self.center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_panel = tk.Frame(main_frame, width=250)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        self.setup_left_panel(left_panel)
        self.setup_center_panel()
        self.setup_right_panel(right_panel)

    def setup_left_panel(self, parent: tk.Frame):
        tk.Label(parent, text="图像操作", font=("Arial", 12, "bold")).pack(pady=10)
        
        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="加载源图像", command=self.load_source, 
                 width=20, height=2).pack(pady=2)
        tk.Button(btn_frame, text="加载目标图像", command=self.load_target,
                 width=20, height=2).pack(pady=2)
        tk.Button(btn_frame, text="交换图像", command=self.swap_images,
                 width=20, height=2).pack(pady=2)
        tk.Button(btn_frame, text="保存结果", command=self.save_result,
                 width=20, height=2).pack(pady=2)
        
        tk.Label(parent, text="视频操作", font=("Arial", 12, "bold")).pack(pady=5)
        video_btn_frame = tk.Frame(parent)
        video_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(video_btn_frame, text="加载目标视频", command=self.load_target_video,
                 width=20, height=2).pack(pady=2)
        tk.Button(video_btn_frame, text="处理视频", command=self.process_video,
                 width=20, height=2, bg="#FF9800", fg="white").pack(pady=2)
        
        self.video_status = tk.Label(parent, text="无视频", fg="gray", font=("Arial", 9))
        self.video_status.pack(pady=2)
        
        tk.Label(parent, text="", font=("Arial", 12, "bold")).pack(pady=5)
        tk.Label(parent, text="显示模式", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.display_mode = tk.StringVar(value="source")
        mode_frame = tk.Frame(parent)
        mode_frame.pack(fill=tk.X, padx=10)
        tk.Radiobutton(mode_frame, text="源图像", variable=self.display_mode, 
                      value="source", command=self.update_canvas).pack(anchor=tk.W)
        tk.Radiobutton(mode_frame, text="目标图像", variable=self.display_mode,
                      value="target", command=self.update_canvas).pack(anchor=tk.W)
        tk.Radiobutton(mode_frame, text="结果", variable=self.display_mode,
                      value="result", command=self.update_canvas).pack(anchor=tk.W)
        
        tk.Label(parent, text="缩放: {:.1f}x".format(1.0), 
                font=("Arial", 10)).pack(pady=5)
        tk.Button(parent, text="重置缩放", command=self.reset_zoom,
                 width=15).pack(pady=2)

    def setup_center_panel(self):
        top_frame = tk.Frame(self.center_panel)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(top_frame, text="工具:").pack(side=tk.LEFT)
        self.tool_var = tk.StringVar(value="brush")
        tools = [("画笔", "brush"), ("橡皮擦", "eraser"), ("圆形", "circle"), ("矩形", "rect")]
        for text, value in tools:
            tk.Radiobutton(top_frame, text=text, variable=self.tool_var, 
                          value=value, command=self.on_tool_change).pack(side=tk.LEFT, padx=2)
        
        tk.Label(top_frame, text="   笔刷大小:").pack(side=tk.LEFT)
        self.brush_scale = tk.Scale(top_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                                   length=150, command=self.on_brush_size_change)
        self.brush_scale.set(20)
        self.brush_scale.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="保存掩膜", command=self.save_mask).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="清除掩膜", command=self.clear_masks).pack(side=tk.LEFT, padx=5)
        
        canvas_frame = tk.Frame(self.center_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.scroll_x = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.scroll_y = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = ImageCanvas(canvas_frame, 
                                 xscrollcommand=self.scroll_x.set,
                                 yscrollcommand=self.scroll_y.set,
                                 bg="gray")
        
        self.scroll_x.config(command=self.canvas.xview)
        self.scroll_y.config(command=self.canvas.yview)
        
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def setup_right_panel(self, parent: tk.Frame):
        tk.Label(parent, text="融合设置", font=("Arial", 12, "bold")).pack(pady=10)
        
        tk.Label(parent, text="梯度混合权重:").pack(anchor=tk.W, padx=10)
        self.mix_weight = tk.DoubleVar(value=1.0)
        self.mix_slider = tk.Scale(parent, from_=0.0, to=1.0, resolution=0.1,
                                  orient=tk.HORIZONTAL, variable=self.mix_weight,
                                  length=200)
        self.mix_slider.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(parent, text="0.0=目标梯度, 1.0=源梯度").pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Label(parent, text="边界羽化半径:").pack(anchor=tk.W, padx=10)
        self.feather_radius = tk.IntVar(value=5)
        self.feather_slider = tk.Scale(parent, from_=0, to=20, resolution=1,
                                      orient=tk.HORIZONTAL, variable=self.feather_radius,
                                      length=200, command=self.on_feather_change)
        self.feather_slider.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(parent, text="多网格设置", font=("Arial", 12, "bold")).pack(pady=5)
        
        tk.Label(parent, text="网格层数:").pack(anchor=tk.W, padx=10)
        self.grid_levels = tk.IntVar(value=4)
        tk.Entry(parent, textvariable=self.grid_levels, width=10).pack(anchor=tk.W, padx=10)
        
        tk.Label(parent, text="循环类型:").pack(anchor=tk.W, padx=10)
        self.cycle_type = tk.StringVar(value="V")
        cycle_frame = tk.Frame(parent)
        cycle_frame.pack(anchor=tk.W, padx=10)
        tk.Radiobutton(cycle_frame, text="V循环", variable=self.cycle_type, 
                      value="V").pack(side=tk.LEFT)
        tk.Radiobutton(cycle_frame, text="W循环", variable=self.cycle_type,
                      value="W").pack(side=tk.LEFT)
        
        tk.Label(parent, text="GPU加速:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.use_gpu = tk.BooleanVar(value=HAS_CUDA)
        gpu_text = "启用GPU (CUDA可用)" if HAS_CUDA else "启用GPU (需要CUDA+Numba)"
        gpu_check = tk.Checkbutton(parent, text=gpu_text, variable=self.use_gpu, 
                                  command=self.on_gpu_change)
        gpu_check.pack(anchor=tk.W, padx=10)
        if not HAS_CUDA:
            gpu_check.config(state=tk.DISABLED, fg="gray")
        
        tk.Label(parent, text="视频时间平滑:").pack(anchor=tk.W, padx=10)
        self.temporal_smoothing = tk.DoubleVar(value=0.3)
        self.smooth_slider = tk.Scale(parent, from_=0.0, to=0.9, resolution=0.1,
                                     orient=tk.HORIZONTAL, variable=self.temporal_smoothing,
                                     length=200)
        self.smooth_slider.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(parent, text="").pack(pady=5)
        
        tk.Button(parent, text="执行泊松融合", command=self.run_poisson_fusion,
                 width=20, height=2, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold")).pack(pady=5)
        
        tk.Label(parent, text="掩膜列表", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.mask_listbox = tk.Listbox(parent, height=8)
        self.mask_listbox.pack(fill=tk.X, padx=10)
        
        tk.Button(parent, text="删除选中掩膜", command=self.delete_selected_mask,
                 width=15).pack(pady=5)
        
        self.status_label = tk.Label(parent, text="就绪", fg="blue", font=("Arial", 10))
        self.status_label.pack(pady=10, side=tk.BOTTOM)

    def on_tool_change(self):
        self.canvas.tool = self.tool_var.get()

    def on_brush_size_change(self, value):
        self.canvas.brush_size = int(value)

    def on_feather_change(self, value):
        self.poisson.feather_radius = int(value)

    def on_gpu_change(self):
        if HAS_CUDA:
            self.poisson = PoissonEditing(solver_type='multigrid', use_gpu=self.use_gpu.get())
            self.set_status(f"GPU加速: {'启用' if self.use_gpu.get() else '禁用'}")

    def load_source(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
            ("All files", "*.*")
        ])
        if path:
            img = cv2.imread(path)
            if img is not None:
                self.src_img = img
                self.set_status("源图像已加载: {}".format(path.split('/')[-1]))
                if self.display_mode.get() == "source":
                    self.canvas.set_image(self.src_img)

    def load_target(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
            ("All files", "*.*")
        ])
        if path:
            img = cv2.imread(path)
            if img is not None:
                self.dst_img = img
                self.set_status("目标图像已加载: {}".format(path.split('/')[-1]))
                if self.display_mode.get() == "target":
                    self.canvas.set_image(self.dst_img)

    def swap_images(self):
        self.src_img, self.dst_img = self.dst_img, self.src_img
        self.set_status("图像已交换")
        self.update_canvas()

    def load_target_video(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv"),
            ("All files", "*.*")
        ])
        if path:
            self.video_path = path
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                ret, frame = cap.read()
                if ret:
                    self.dst_img = frame
                    if self.display_mode.get() == "target":
                        self.canvas.set_image(self.dst_img)
                
                cap.release()
                self.video_status.config(text=f"{width}x{height}, {fps:.1f}fps, {total_frames}帧", fg="green")
                self.set_status(f"视频已加载: {path.split('/')[-1]}")
            else:
                messagebox.showerror("错误", "无法打开视频文件")

    def process_video(self):
        if self.video_path is None:
            messagebox.showwarning("警告", "请先加载目标视频")
            return
        
        if self.src_img is None:
            messagebox.showwarning("警告", "请先加载源图像")
            return
        
        mask_items = self.canvas.get_all_masks()
        if not mask_items:
            messagebox.showwarning("警告", "请至少创建一个掩膜")
            return
        
        output_path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                                   filetypes=[("MP4 files", "*.mp4"),
                                                             ("AVI files", "*.avi"),
                                                             ("All files", "*.*")])
        if not output_path:
            return
        
        self.is_processing_video = True
        self.set_status("正在处理视频...")
        self.root.update()
        
        try:
            if self.video_editor is None:
                self.video_editor = VideoPoissonEditor(
                    use_gpu=self.use_gpu.get(), 
                    temporal_smoothing=self.temporal_smoothing.get()
                )
            
            mask = mask_items[0].mask
            offset = mask_items[0].offset
            
            success = self.video_editor.process_video(
                src_img=self.src_img,
                video_path=self.video_path,
                output_path=output_path,
                mask=mask,
                offset=offset,
                mix_weight=self.mix_weight.get()
            )
            
            if success:
                messagebox.showinfo("完成", f"视频处理完成!\n输出: {output_path}")
                self.set_status("视频处理完成!")
            else:
                messagebox.showerror("错误", "视频处理失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_processing_video = False

    def save_result(self):
        if self.result_img is None:
            messagebox.showwarning("警告", "没有可保存的结果图像")
            return
        
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                           filetypes=[("PNG files", "*.png"),
                                                     ("JPEG files", "*.jpg"),
                                                     ("All files", "*.*")])
        if path:
            cv2.imwrite(path, self.result_img)
            self.set_status("结果已保存到: {}".format(path.split('/')[-1]))

    def update_canvas(self):
        mode = self.display_mode.get()
        if mode == "source" and self.src_img is not None:
            self.canvas.set_image(self.src_img)
        elif mode == "target" and self.dst_img is not None:
            self.canvas.set_image(self.dst_img)
        elif mode == "result" and self.result_img is not None:
            self.canvas.set_image(self.result_img)
        self.update_mask_listbox()

    def reset_zoom(self):
        self.canvas.scale = 1.0
        self.canvas.update_display(full_refresh=True)

    def save_mask(self):
        if self.canvas.save_current_mask():
            self.update_mask_listbox()
            self.set_status("掩膜已保存")
        else:
            messagebox.showwarning("警告", "当前没有绘制掩膜")

    def clear_masks(self):
        self.canvas.clear_masks()
        self.update_mask_listbox()
        self.set_status("掩膜已清除")

    def update_mask_listbox(self):
        self.mask_listbox.delete(0, tk.END)
        for i, mask_item in enumerate(self.canvas.mask_items):
            status = "可见" if mask_item.visible else "隐藏"
            self.mask_listbox.insert(tk.END, 
                f"掩膜 {i+1}: 权重={mask_item.mix_weight:.1f}, {status}")

    def delete_selected_mask(self):
        selection = self.mask_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.canvas.mask_items[idx]
            self.canvas.update_display(full_refresh=True)
            self.update_mask_listbox()
            self.set_status("掩膜已删除")

    def run_poisson_fusion(self):
        if self.src_img is None or self.dst_img is None:
            messagebox.showerror("错误", "请先加载源图像和目标图像")
            return
        
        mask_items = self.canvas.get_all_masks()
        if not mask_items:
            messagebox.showerror("错误", "请至少创建一个掩膜")
            return
        
        self.set_status("正在执行多网格泊松融合...")
        self.root.update()
        
        try:
            self.poisson.multigrid.max_levels = self.grid_levels.get()
            self.poisson.multigrid.cycle_type = self.cycle_type.get()
            
            masks = [item.mask for item in mask_items]
            offsets = [item.offset for item in mask_items]
            mix_weights = [self.mix_weight.get() for _ in mask_items]
            
            result = self.poisson.fuse(
                self.src_img, self.dst_img, masks, offsets, mix_weights, feather=True
            )
            
            self.result_img = result
            self.display_mode.set("result")
            self.update_canvas()
            self.set_status("泊松融合完成 (多网格法)!")
            
        except Exception as e:
            messagebox.showerror("错误", f"融合失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self.set_status("融合失败")

    def set_status(self, text: str):
        self.status_label.config(text=text)


def main():
    root = tk.Tk()
    app = PoissonEditingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
