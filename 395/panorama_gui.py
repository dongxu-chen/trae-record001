import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider, CheckButtons
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from tkinter import filedialog, Tk
from typing import List, Optional
from panorama_stitcher import PanoramaStitcher


class PanoramaGUI:
    def __init__(self):
        self.image_paths: List[str] = []
        self.images: List[np.ndarray] = []
        self.stitcher: Optional[PanoramaStitcher] = None
        self.panorama: Optional[np.ndarray] = None
        
        self.projection_type = 'plane'
        self.blend_type = 'multiband'
        self.auto_crop = True
        
        self._setup_gui()

    def _setup_gui(self):
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle('全景图拼接工具 - Panorama Stitching Tool', fontsize=16, fontweight='bold')
        
        gs = self.fig.add_gridspec(4, 3, hspace=0.3, wspace=0.2)
        
        self.ax_input = self.fig.add_subplot(gs[0:2, 0:2])
        self.ax_input.set_title('输入图像 (点击切换查看)')
        self.ax_input.axis('off')
        
        self.ax_output = self.fig.add_subplot(gs[2:4, 0:2])
        self.ax_output.set_title('拼接结果')
        self.ax_output.axis('off')
        
        self.ax_controls = self.fig.add_subplot(gs[0:4, 2])
        self.ax_controls.axis('off')
        self.ax_controls.set_title('控制面板', fontsize=12, fontweight='bold')
        
        self._create_controls()
        
        self.current_image_idx = 0
        self._update_input_display()

    def _create_controls(self):
        control_y = 0.95
        spacing = 0.07
        
        ax_btn_load = plt.axes([0.70, control_y, 0.25, 0.05])
        self.btn_load = Button(ax_btn_load, '加载图像', color='#4CAF50', hovercolor='#45a049')
        self.btn_load.on_clicked(self._load_images)
        control_y -= spacing
        
        ax_proj_label = plt.axes([0.68, control_y, 0.30, 0.03])
        ax_proj_label.axis('off')
        ax_proj_label.text(0.5, 0.5, '投影方式:', ha='center', va='center', fontsize=10)
        control_y -= 0.04
        
        ax_proj = plt.axes([0.70, control_y - 0.08, 0.25, 0.10])
        self.radio_proj = RadioButtons(ax_proj, ('平面', '柱面', '球面'),
                                       active=0, activecolor='#2196F3')
        self.radio_proj.on_clicked(self._on_projection_change)
        control_y -= 0.15
        
        ax_blend_label = plt.axes([0.68, control_y, 0.30, 0.03])
        ax_blend_label.axis('off')
        ax_blend_label.text(0.5, 0.5, '融合方式:', ha='center', va='center', fontsize=10)
        control_y -= 0.04
        
        ax_blend = plt.axes([0.70, control_y - 0.10, 0.25, 0.12])
        self.radio_blend = RadioButtons(ax_blend, ('多波段', '羽化', '简单'),
                                       active=0, activecolor='#FF9800')
        self.radio_blend.on_clicked(self._on_blend_change)
        control_y -= 0.17
        
        ax_crop = plt.axes([0.70, control_y - 0.03, 0.25, 0.05])
        self.check_crop = CheckButtons(ax_crop, ['自动裁剪'], [True])
        self.check_crop.on_clicked(self._on_crop_change)
        control_y -= spacing
        
        ax_btn_stitch = plt.axes([0.70, control_y, 0.25, 0.06])
        self.btn_stitch = Button(ax_btn_stitch, '开始拼接', color='#2196F3', hovercolor='#1976D2')
        self.btn_stitch.on_clicked(self._stitch_images)
        control_y -= spacing
        
        ax_btn_save = plt.axes([0.70, control_y, 0.25, 0.05])
        self.btn_save = Button(ax_btn_save, '保存结果', color='#FF9800', hovercolor='#F57C00')
        self.btn_save.on_clicked(self._save_result)
        control_y -= spacing
        
        ax_btn_clear = plt.axes([0.70, control_y, 0.25, 0.05])
        self.btn_clear = Button(ax_btn_clear, '清除全部', color='#f44336', hovercolor='#d32f2f')
        self.btn_clear.on_clicked(self._clear_all)
        
        self.fig.canvas.mpl_connect('button_press_event', self._on_canvas_click)

    def _load_images(self, event):
        root = Tk()
        root.withdraw()
        file_paths = filedialog.askopenfilenames(
            title='选择图像文件',
            filetypes=[('图像文件', '*.jpg *.jpeg *.png *.bmp *.tiff'),
                       ('所有文件', '*.*')]
        )
        root.destroy()
        
        if file_paths:
            self.image_paths = list(file_paths)
            self.images = []
            for path in self.image_paths:
                img = cv2.imread(path)
                if img is not None:
                    self.images.append(img)
            
            self.current_image_idx = 0
            self._update_input_display()
            self.ax_output.clear()
            self.ax_output.set_title('拼接结果')
            self.ax_output.axis('off')
            plt.draw()

    def _on_projection_change(self, label):
        mapping = {'平面': 'plane', '柱面': 'cylindrical', '球面': 'spherical'}
        self.projection_type = mapping[label]

    def _on_blend_change(self, label):
        mapping = {'多波段': 'multiband', '羽化': 'feather', '简单': 'simple'}
        self.blend_type = mapping[label]

    def _on_crop_change(self, label):
        self.auto_crop = not self.auto_crop

    def _stitch_images(self, event):
        if len(self.images) < 2:
            self._show_status('请至少加载2张图像!')
            return
        
        try:
            self._show_status('正在拼接...')
            plt.draw()
            
            self.stitcher = PanoramaStitcher(
                projection_type=self.projection_type,
                blend_type=self.blend_type
            )
            
            self.panorama = self.stitcher.stitch(images=self.images)
            
            if self.auto_crop:
                self.panorama = self.stitcher.crop_black_borders(self.panorama)
            
            self._update_output_display()
            self._show_status('拼接完成!')
            
        except Exception as e:
            self._show_status(f'拼接失败: {str(e)}')
            import traceback
            traceback.print_exc()

    def _save_result(self, event):
        if self.panorama is None:
            self._show_status('没有可保存的结果!')
            return
        
        root = Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title='保存全景图',
            defaultextension='.jpg',
            filetypes=[('JPEG图像', '*.jpg'), ('PNG图像', '*.png'), ('所有文件', '*.*')]
        )
        root.destroy()
        
        if file_path:
            cv2.imwrite(file_path, self.panorama)
            self._show_status(f'已保存到: {os.path.basename(file_path)}')

    def _clear_all(self, event):
        self.image_paths = []
        self.images = []
        self.stitcher = None
        self.panorama = None
        self.current_image_idx = 0
        
        self.ax_input.clear()
        self.ax_input.set_title('输入图像 (点击切换查看)')
        self.ax_input.axis('off')
        
        self.ax_output.clear()
        self.ax_output.set_title('拼接结果')
        self.ax_output.axis('off')
        
        self._show_status('已清除')
        plt.draw()

    def _on_canvas_click(self, event):
        if event.inaxes == self.ax_input and len(self.images) > 1:
            self.current_image_idx = (self.current_image_idx + 1) % len(self.images)
            self._update_input_display()
            plt.draw()

    def _update_input_display(self):
        self.ax_input.clear()
        
        if len(self.images) > 0:
            img_rgb = cv2.cvtColor(self.images[self.current_image_idx], cv2.COLOR_BGR2RGB)
            self.ax_input.imshow(img_rgb)
            self.ax_input.set_title(
                f'输入图像 {self.current_image_idx + 1}/{len(self.images)} - '
                f'{os.path.basename(self.image_paths[self.current_image_idx]) if self.image_paths else ""}'
            )
        else:
            self.ax_input.text(0.5, 0.5, '点击"加载图像"按钮选择图片',
                             ha='center', va='center', fontsize=14, color='gray')
        
        self.ax_input.axis('off')

    def _update_output_display(self):
        self.ax_output.clear()
        
        if self.panorama is not None:
            panorama_rgb = cv2.cvtColor(self.panorama, cv2.COLOR_BGR2RGB)
            self.ax_output.imshow(panorama_rgb)
            h, w = self.panorama.shape[:2]
            self.ax_output.set_title(f'拼接结果 ({w}x{h})')
        
        self.ax_output.axis('off')
        plt.draw()

    def _show_status(self, message: str):
        if hasattr(self, 'status_text'):
            self.status_text.remove()
        self.status_text = self.fig.text(0.02, 0.02, message, fontsize=10, color='#333')
        plt.draw()

    def run(self):
        plt.tight_layout()
        plt.show()


def run_gui():
    gui = PanoramaGUI()
    gui.run()


if __name__ == '__main__':
    run_gui()
