import os
import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QPushButton, QCheckBox, QSpinBox, QGroupBox, QFileDialog,
    QMessageBox, QStatusBar, QProgressBar, QListWidget, QListWidgetItem,
    QScrollArea, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

from .style_transfer import StyleTransferModel, MultiStyleTransferModel
from .video_processor import VideoProcessor, RESOLUTION_PRESETS, CameraCapture
from .segmentation import InstanceSegmenter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("实时视频风格迁移 - Real-time Video Style Transfer")
        self.resize(1400, 850)

        self.style_model: Optional[StyleTransferModel] = None
        self.multi_style_model: Optional[MultiStyleTransferModel] = None
        self.segmenter: Optional[InstanceSegmenter] = None
        self.video_processor: Optional[VideoProcessor] = None
        self.available_styles: Dict[str, str] = {}
        self.current_frame: Optional[np.ndarray] = None
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

        self._init_ui()
        self._load_available_styles()
        self._detect_cameras()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        video_layout = QVBoxLayout()
        self.video_label = QLabel("点击'开始'按钮启动摄像头")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #222;
                border: 2px solid #444;
                border-radius: 8px;
                color: #888;
                font-size: 18px;
            }
        """)
        video_layout.addWidget(self.video_label)

        info_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS: 0")
        self.process_time_label = QLabel("处理时间: 0ms")
        self.resolution_label = QLabel("分辨率: -")
        self.complexity_label = QLabel("复杂度: -")
        info_layout.addWidget(self.fps_label)
        info_layout.addWidget(self.process_time_label)
        info_layout.addWidget(self.resolution_label)
        info_layout.addWidget(self.complexity_label)
        info_layout.addStretch()
        video_layout.addLayout(info_layout)

        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("帧缓冲:"))
        self.buffer_bar = QProgressBar()
        self.buffer_bar.setRange(0, 100)
        self.buffer_bar.setValue(0)
        self.buffer_bar.setFixedWidth(150)
        self.buffer_bar.setTextVisible(True)
        self.buffer_bar.setFormat("%v/%m")
        buffer_layout.addWidget(self.buffer_bar)
        buffer_layout.addStretch()
        video_layout.addLayout(buffer_layout)

        main_layout.addLayout(video_layout, stretch=3)

        control_layout = QVBoxLayout()
        control_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        camera_group = QGroupBox("摄像头设置")
        camera_layout = QVBoxLayout(camera_group)

        camera_select_layout = QHBoxLayout()
        camera_select_layout.addWidget(QLabel("摄像头:"))
        self.camera_combo = QComboBox()
        camera_select_layout.addWidget(self.camera_combo)
        camera_layout.addLayout(camera_select_layout)

        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("采集分辨率:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["自动", "360p", "480p", "720p", "1080p"])
        self.resolution_combo.setCurrentText("480p")
        resolution_layout.addWidget(self.resolution_combo)
        camera_layout.addLayout(resolution_layout)

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("目标FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(30)
        fps_layout.addWidget(self.fps_spin)
        camera_layout.addLayout(fps_layout)

        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self._toggle_capture)
        camera_layout.addWidget(self.start_btn)

        scroll_layout.addWidget(camera_group)

        mode_group = QGroupBox("模式")
        mode_layout = QVBoxLayout(mode_group)

        mode_select_layout = QHBoxLayout()
        mode_select_layout.addWidget(QLabel("风格模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["单风格", "多风格混合"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_select_layout.addWidget(self.mode_combo)
        mode_layout.addLayout(mode_select_layout)

        scroll_layout.addWidget(mode_group)

        style_group = QGroupBox("风格设置")
        style_layout = QVBoxLayout(style_group)

        self.style_tabs = QTabWidget()

        single_tab = QWidget()
        single_layout = QVBoxLayout(single_tab)

        style_select_layout = QHBoxLayout()
        style_select_layout.addWidget(QLabel("艺术风格:"))
        self.style_combo = QComboBox()
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        style_select_layout.addWidget(self.style_combo)
        single_layout.addLayout(style_select_layout)

        self.style_tabs.addTab(single_tab, "单风格")

        multi_tab = QWidget()
        multi_layout = QVBoxLayout(multi_tab)

        self.style_list = QListWidget()
        self.style_list.setSelectionMode(QListWidget.MultiSelection)
        self.style_list.setMaximumHeight(120)
        multi_layout.addWidget(QLabel("选择风格 (多选):"))
        multi_layout.addWidget(self.style_list)

        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("风格权重:"))
        self.weight_slider = QSlider(Qt.Horizontal)
        self.weight_slider.setRange(10, 100)
        self.weight_slider.setValue(50)
        self.weight_label = QLabel("0.50")
        self.weight_slider.valueChanged.connect(self._on_weight_changed)
        weight_layout.addWidget(self.weight_slider)
        weight_layout.addWidget(self.weight_label)
        multi_layout.addLayout(weight_layout)

        self.apply_multi_btn = QPushButton("应用多风格")
        self.apply_multi_btn.clicked.connect(self._apply_multi_styles)
        multi_layout.addWidget(self.apply_multi_btn)

        self.style_tabs.addTab(multi_tab, "多风格混合")

        style_layout.addWidget(self.style_tabs)

        strength_layout = QVBoxLayout()
        strength_layout.addWidget(QLabel("风格强度:"))
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(0, 100)
        self.strength_slider.setValue(100)
        self.strength_slider.valueChanged.connect(self._on_strength_changed)
        strength_layout.addWidget(self.strength_slider)
        self.strength_label = QLabel("100%")
        self.strength_label.setAlignment(Qt.AlignCenter)
        strength_layout.addWidget(self.strength_label)
        style_layout.addLayout(strength_layout)

        self.auto_strength_check = QCheckBox("自动强度调节 (根据内容复杂度)")
        self.auto_strength_check.stateChanged.connect(self._on_auto_strength_changed)
        style_layout.addWidget(self.auto_strength_check)

        proc_res_layout = QHBoxLayout()
        proc_res_layout.addWidget(QLabel("处理分辨率:"))
        self.proc_res_combo = QComboBox()
        self.proc_res_combo.addItems(["原始", "360p", "480p", "720p"])
        self.proc_res_combo.setCurrentText("480p")
        self.proc_res_combo.currentTextChanged.connect(self._on_proc_res_changed)
        proc_res_layout.addWidget(self.proc_res_combo)
        style_layout.addLayout(proc_res_layout)

        self.show_original_check = QCheckBox("显示原始画面")
        self.show_original_check.stateChanged.connect(self._on_show_original_changed)
        style_layout.addWidget(self.show_original_check)

        scroll_layout.addWidget(style_group)

        segmentation_group = QGroupBox("实例分割引导")
        seg_layout = QVBoxLayout(segmentation_group)

        self.segmentation_check = QCheckBox("启用分割 (前景/背景不同风格)")
        self.segmentation_check.stateChanged.connect(self._on_segmentation_changed)
        seg_layout.addWidget(self.segmentation_check)

        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("分割方法:"))
        self.seg_method_combo = QComboBox()
        self.seg_method_combo.addItems(["背景差", "肤色", "边缘"])
        self.seg_method_combo.currentTextChanged.connect(self._on_seg_method_changed)
        method_layout.addWidget(self.seg_method_combo)
        seg_layout.addLayout(method_layout)

        bg_style_layout = QHBoxLayout()
        bg_style_layout.addWidget(QLabel("背景风格:"))
        self.bg_style_combo = QComboBox()
        self.bg_style_combo.currentTextChanged.connect(self._on_bg_style_changed)
        bg_style_layout.addWidget(self.bg_style_combo)
        seg_layout.addLayout(bg_style_layout)

        self.show_mask_check = QCheckBox("显示分割遮罩")
        self.show_mask_check.stateChanged.connect(self._on_show_mask_changed)
        seg_layout.addWidget(self.show_mask_check)

        scroll_layout.addWidget(segmentation_group)

        tiling_group = QGroupBox("分块处理")
        tiling_layout = QVBoxLayout(tiling_group)

        self.tiling_check = QCheckBox("启用分块风格化 (高分辨率)")
        self.tiling_check.setChecked(True)
        tiling_layout.addWidget(self.tiling_check)

        tile_size_layout = QHBoxLayout()
        tile_size_layout.addWidget(QLabel("分块大小:"))
        self.tile_size_combo = QComboBox()
        self.tile_size_combo.addItems(["256", "384", "512", "640", "768"])
        self.tile_size_combo.setCurrentText("512")
        tile_size_layout.addWidget(self.tile_size_combo)
        tiling_layout.addLayout(tile_size_layout)

        overlap_layout = QHBoxLayout()
        overlap_layout.addWidget(QLabel("重叠像素:"))
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(16, 128)
        self.overlap_spin.setValue(64)
        self.overlap_spin.setSingleStep(16)
        overlap_layout.addWidget(self.overlap_spin)
        tiling_layout.addLayout(overlap_layout)

        self.apply_tiling_btn = QPushButton("应用分块设置")
        self.apply_tiling_btn.clicked.connect(self._apply_tiling_settings)
        tiling_layout.addWidget(self.apply_tiling_btn)

        scroll_layout.addWidget(tiling_group)

        accel_group = QGroupBox("加速设置")
        accel_layout = QVBoxLayout(accel_group)

        self.gpu_check = QCheckBox("使用GPU加速")
        self.gpu_check.setChecked(True)
        accel_layout.addWidget(self.gpu_check)

        self.tensorrt_check = QCheckBox("使用TensorRT加速")
        self.tensorrt_check.setChecked(False)
        accel_layout.addWidget(self.tensorrt_check)

        self.apply_accel_btn = QPushButton("应用加速设置")
        self.apply_accel_btn.clicked.connect(self._apply_accel_settings)
        accel_layout.addWidget(self.apply_accel_btn)

        scroll_layout.addWidget(accel_group)

        output_group = QGroupBox("输出")
        output_layout = QVBoxLayout(output_group)

        self.save_btn = QPushButton("保存当前帧")
        self.save_btn.clicked.connect(self._save_current_frame)
        output_layout.addWidget(self.save_btn)

        scroll_layout.addWidget(output_group)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        control_layout.addWidget(scroll_area)

        main_layout.addLayout(control_layout, stretch=1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")

    def _load_available_styles(self):
        self.style_combo.clear()
        self.style_combo.addItem("无")
        self.style_list.clear()
        self.bg_style_combo.clear()
        self.bg_style_combo.addItem("无")

        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
            return

        self.style_model = StyleTransferModel(
            use_gpu=self.gpu_check.isChecked(),
            use_tensorrt=self.tensorrt_check.isChecked(),
            use_tiling=self.tiling_check.isChecked(),
            tile_size=int(self.tile_size_combo.currentText()),
            overlap=self.overlap_spin.value()
        )
        self.available_styles = self.style_model.get_available_styles(self.models_dir)

        for style_name in sorted(self.available_styles.keys()):
            self.style_combo.addItem(style_name)
            item = QListWidgetItem(style_name)
            self.style_list.addItem(item)
            self.bg_style_combo.addItem(style_name)

        if self.available_styles:
            self.statusBar().showMessage(f"已加载 {len(self.available_styles)} 个风格模型")
        else:
            self.statusBar().showMessage("请将 .pth 风格模型放入 models 目录")

    def _detect_cameras(self):
        self.camera_combo.clear()
        cameras = CameraCapture.list_available_cameras()
        for cam_idx in cameras:
            self.camera_combo.addItem(f"摄像头 {cam_idx}", cam_idx)

        if not cameras:
            QMessageBox.warning(self, "警告", "未检测到可用摄像头")

    def _on_mode_changed(self, mode: str):
        pass

    def _on_style_changed(self, style_name: str):
        if self.style_model is None:
            return

        if style_name == "无":
            if self.video_processor is not None:
                self.video_processor.set_style_model(None)
            self.statusBar().showMessage("风格迁移已禁用")
            return

        if style_name in self.available_styles:
            model_path = self.available_styles[style_name]
            success = self.style_model.load_model(model_path, style_name)
            if success and self.video_processor is not None:
                self.video_processor.set_style_model(self.style_model)
                self.video_processor.set_use_multi_style(False)
                self.statusBar().showMessage(f"已加载风格: {style_name}")
            else:
                self.statusBar().showMessage(f"加载风格失败: {style_name}")

    def _on_weight_changed(self, value: int):
        weight = value / 100.0
        self.weight_label.setText(f"{weight:.2f}")

    def _apply_multi_styles(self):
        selected_items = self.style_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请至少选择一个风格")
            return

        if self.multi_style_model is None:
            self.multi_style_model = MultiStyleTransferModel(
                use_gpu=self.gpu_check.isChecked(),
                use_tensorrt=self.tensorrt_check.isChecked(),
                use_tiling=self.tiling_check.isChecked(),
                tile_size=int(self.tile_size_combo.currentText()),
                overlap=self.overlap_spin.value()
            )

        weight = self.weight_slider.value() / 100.0
        per_style_weight = weight / len(selected_items)

        for item in selected_items:
            style_name = item.text()
            if style_name in self.available_styles:
                model_path = self.available_styles[style_name]
                self.multi_style_model.add_style(model_path, style_name, per_style_weight)

        self.multi_style_model.set_auto_strength(
            self.auto_strength_check.isChecked()
        )

        if self.video_processor is not None:
            self.video_processor.set_multi_style_model(self.multi_style_model)
            self.video_processor.set_use_multi_style(True)
            self.video_processor.set_style_model(None)

        self.statusBar().showMessage(
            f"已应用多风格: {len(selected_items)} 个风格, 总权重={weight:.2f}"
        )

    def _on_strength_changed(self, value: int):
        strength = value / 100.0
        self.strength_label.setText(f"{value}%")
        if self.video_processor is not None:
            self.video_processor.set_style_strength(strength)

    def _on_auto_strength_changed(self, state: int):
        enabled = state == Qt.Checked
        if self.multi_style_model is not None:
            self.multi_style_model.set_auto_strength(enabled)
        if self.video_processor is not None:
            if self.multi_style_model is not None:
                self.multi_style_model.set_auto_strength(enabled)

    def _on_proc_res_changed(self, value: str):
        if value == "原始":
            proc_res = None
        else:
            proc_res = RESOLUTION_PRESETS.get(value)

        if self.video_processor is not None:
            self.video_processor.set_processing_resolution(proc_res)

    def _on_show_original_changed(self, state: int):
        if self.video_processor is not None:
            self.video_processor.set_show_original(state == Qt.Checked)

    def _on_segmentation_changed(self, state: int):
        enabled = state == Qt.Checked
        if self.segmenter is None:
            self.segmenter = InstanceSegmenter(use_gpu=self.gpu_check.isChecked())
        if self.video_processor is not None:
            self.video_processor.set_segmenter(self.segmenter if enabled else None)
            self.video_processor.set_use_segmentation(enabled)

    def _on_seg_method_changed(self, method: str):
        method_map = {
            "背景差": "background_subtraction",
            "肤色": "color_based",
            "边缘": "edge_based"
        }
        if self.segmenter is not None:
            self.segmenter.set_method(method_map.get(method, "background_subtraction"))

    def _on_bg_style_changed(self, style_name: str):
        if self.video_processor is not None:
            if style_name == "无":
                self.video_processor.set_bg_style_name(None)
            else:
                self.video_processor.set_bg_style_name(style_name)

    def _on_show_mask_changed(self, state: int):
        if self.video_processor is not None:
            self.video_processor.set_show_mask_overlay(state == Qt.Checked)

    def _apply_tiling_settings(self):
        use_tiling = self.tiling_check.isChecked()
        tile_size = int(self.tile_size_combo.currentText())
        overlap = self.overlap_spin.value()

        current_style = self.style_combo.currentText()
        use_gpu = self.gpu_check.isChecked()
        use_tensorrt = self.tensorrt_check.isChecked()

        self.style_model = StyleTransferModel(
            use_gpu=use_gpu,
            use_tensorrt=use_tensorrt,
            use_tiling=use_tiling,
            tile_size=tile_size,
            overlap=overlap
        )

        if self.multi_style_model is not None:
            self.multi_style_model.unload_all()
            self.multi_style_model = None

        if current_style != "无" and current_style in self.available_styles:
            model_path = self.available_styles[current_style]
            self.style_model.load_model(model_path, current_style)

        if self.video_processor is not None:
            self.video_processor.set_style_model(self.style_model)
            self.video_processor.set_multi_style_model(None)
            self.video_processor.set_use_multi_style(False)

        self.statusBar().showMessage(
            f"分块设置已应用: {'启用' if use_tiling else '禁用'}, size={tile_size}, overlap={overlap}"
        )

    def _apply_accel_settings(self):
        use_gpu = self.gpu_check.isChecked()
        use_tensorrt = self.tensorrt_check.isChecked()
        use_tiling = self.tiling_check.isChecked()
        tile_size = int(self.tile_size_combo.currentText())
        overlap = self.overlap_spin.value()

        self.style_model = StyleTransferModel(
            use_gpu=use_gpu,
            use_tensorrt=use_tensorrt,
            use_tiling=use_tiling,
            tile_size=tile_size,
            overlap=overlap
        )

        current_style = self.style_combo.currentText()
        if current_style != "无" and current_style in self.available_styles:
            model_path = self.available_styles[current_style]
            self.style_model.load_model(model_path, current_style)

        if self.video_processor is not None:
            self.video_processor.set_style_model(self.style_model)

        self.statusBar().showMessage(
            f"加速设置已应用: GPU={'开' if use_gpu else '关'}, TensorRT={'开' if use_tensorrt else '关'}"
        )

    def _toggle_capture(self):
        if self.video_processor is None or not self.video_processor.is_running:
            self._start_capture()
        else:
            self._stop_capture()

    def _start_capture(self):
        camera_index = self.camera_combo.currentData()
        if camera_index is None:
            QMessageBox.warning(self, "警告", "请先选择摄像头")
            return

        resolution_text = self.resolution_combo.currentText()
        resolution = None if resolution_text == "自动" else RESOLUTION_PRESETS.get(resolution_text)
        fps = self.fps_spin.value()

        self.video_processor = VideoProcessor(camera_index=camera_index)
        self.video_processor.frame_ready.connect(self._on_frame_ready)
        self.video_processor.fps_updated.connect(self._on_fps_updated)
        self.video_processor.buffer_status.connect(self._on_buffer_status)
        self.video_processor.complexity_updated.connect(self._on_complexity_updated)

        if self.style_combo.currentText() != "无" and self.mode_combo.currentText() == "单风格":
            self.video_processor.set_style_model(self.style_model)
        elif self.multi_style_model is not None and self.mode_combo.currentText() == "多风格混合":
            self.video_processor.set_multi_style_model(self.multi_style_model)
            self.video_processor.set_use_multi_style(True)

        if self.segmentation_check.isChecked():
            if self.segmenter is None:
                self.segmenter = InstanceSegmenter(use_gpu=self.gpu_check.isChecked())
            method_map = {
                "背景差": "background_subtraction",
                "肤色": "color_based",
                "边缘": "edge_based"
            }
            self.segmenter.set_method(method_map.get(self.seg_method_combo.currentText(), "background_subtraction"))
            self.video_processor.set_segmenter(self.segmenter)
            self.video_processor.set_use_segmentation(True)
            self.video_processor.set_bg_style_name(
                None if self.bg_style_combo.currentText() == "无" else self.bg_style_combo.currentText()
            )
            self.video_processor.set_show_mask_overlay(self.show_mask_check.isChecked())

        proc_res_text = self.proc_res_combo.currentText()
        proc_res = None if proc_res_text == "原始" else RESOLUTION_PRESETS.get(proc_res_text)
        self.video_processor.set_processing_resolution(proc_res)
        self.video_processor.set_style_strength(self.strength_slider.value() / 100.0)
        self.video_processor.set_show_original(self.show_original_check.isChecked())

        success = self.video_processor.start_capture(resolution=resolution, fps=fps)
        if success:
            self.start_btn.setText("停止")
            self.resolution_combo.setEnabled(False)
            self.fps_spin.setEnabled(False)
            self.camera_combo.setEnabled(False)
            self.statusBar().showMessage("摄像头已启动")

            actual_res = self.video_processor.get_camera_resolution()
            if actual_res:
                self.resolution_label.setText(f"分辨率: {actual_res[1]}x{actual_res[0]}")
        else:
            QMessageBox.critical(self, "错误", "无法启动摄像头")
            self.video_processor = None

    def _stop_capture(self):
        if self.video_processor is not None:
            self.video_processor.stop_capture()
            self.video_processor = None

        self.start_btn.setText("开始")
        self.resolution_combo.setEnabled(True)
        self.fps_spin.setEnabled(True)
        self.camera_combo.setEnabled(True)
        self.video_label.setText("点击'开始'按钮启动摄像头")
        self.fps_label.setText("FPS: 0")
        self.process_time_label.setText("处理时间: 0ms")
        self.resolution_label.setText("分辨率: -")
        self.complexity_label.setText("复杂度: -")
        self.buffer_bar.setValue(0)
        self.statusBar().showMessage("摄像头已停止")

    def _on_frame_ready(self, frame: np.ndarray, process_time: float):
        self.current_frame = frame.copy()

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

        self.process_time_label.setText(f"处理时间: {process_time:.1f}ms")

    def _on_fps_updated(self, fps: float):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    def _on_buffer_status(self, current: int, max_size: int):
        self.buffer_bar.setMaximum(max_size)
        self.buffer_bar.setValue(current)

    def _on_complexity_updated(self, complexity: float):
        self.complexity_label.setText(f"复杂度: {complexity:.2f}")

    def _save_current_frame(self):
        if self.current_frame is None:
            QMessageBox.information(self, "提示", "没有可保存的帧")
            return

        default_name = f"style_transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", default_name,
            "JPEG 图像 (*.jpg);;PNG 图像 (*.png)"
        )

        if file_path:
            cv2.imwrite(file_path, self.current_frame)
            self.statusBar().showMessage(f"已保存到: {file_path}")

    def closeEvent(self, event):
        self._stop_capture()
        if self.style_model is not None:
            self.style_model.unload()
        if self.multi_style_model is not None:
            self.multi_style_model.unload_all()
        event.accept()
