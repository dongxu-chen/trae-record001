import os
import cv2
import numpy as np
from typing import Dict, Any, Optional, List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QDoubleSpinBox, QGroupBox, QFileDialog, QListWidget,
    QListWidgetItem, QProgressBar, QMessageBox, QInputDialog, QSplitter,
    QCheckBox, QStatusBar, QAction, QMenuBar, QToolBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QIcon, QMouseEvent

from tone_mapping import ToneMapper, ToneMappingOperator
from presets import PresetManager
from batch_processor import BatchProcessor
from scene_analyzer import SceneAnalyzer, SceneType, SceneFeatures
from inverse_mapping import HDRInverseMapper, InverseMappingMethod
from video_processor import HDRVideoProcessor, StabilizationMode, VideoFrameInfo


class DebouncedSlider(QSlider):
    sliderReleased = pyqtSignal()

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._is_dragging = False

    def mousePressEvent(self, event: QMouseEvent):
        self._is_dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False
        super().mouseReleaseEvent(event)
        self.sliderReleased.emit()

    def isDragging(self) -> bool:
        return self._is_dragging


class ParamWidget(QWidget):
    valueChanged = pyqtSignal(str, float)
    valueApplied = pyqtSignal(str, float)

    def __init__(self, name: str, min_val: float, max_val: float, default_val: float, step: float = 0.01):
        super().__init__()
        self.name = name
        self._current_value = default_val

        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QLabel(f"{name}:")
        self.label.setFixedWidth(100)

        self.slider = DebouncedSlider(Qt.Horizontal)
        self.slider.setMinimum(int(min_val / step))
        self.slider.setMaximum(int(max_val / step))
        self.slider.setValue(int(default_val / step))
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(int((max_val - min_val) / step / 10))

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setSingleStep(step)
        self.spinbox.setValue(default_val)
        self.spinbox.setDecimals(3)
        self.spinbox.setFixedWidth(80)

        self.slider.valueChanged.connect(lambda v: self._on_slider_changed(v, step))
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        self.spinbox.editingFinished.connect(self._on_spinbox_finished)

        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spinbox)

        self.setLayout(layout)

    def _on_slider_changed(self, value: int, step: float):
        actual_value = value * step
        self._current_value = actual_value
        if abs(self.spinbox.value() - actual_value) > 0.0001:
            self.spinbox.blockSignals(True)
            self.spinbox.setValue(actual_value)
            self.spinbox.blockSignals(False)
        self.valueChanged.emit(self.name, actual_value)

    def _on_slider_released(self):
        self.valueApplied.emit(self.name, self._current_value)

    def _on_spinbox_changed(self, value: float):
        step = self.spinbox.singleStep()
        slider_val = int(value / step)
        self._current_value = value
        if self.slider.value() != slider_val:
            self.slider.blockSignals(True)
            self.slider.setValue(slider_val)
            self.slider.blockSignals(False)
        self.valueChanged.emit(self.name, value)

    def _on_spinbox_finished(self):
        self.valueApplied.emit(self.name, self._current_value)

    def set_value(self, value: float):
        self.spinbox.setValue(value)

    def get_value(self) -> float:
        return self.spinbox.value()

    def is_dragging(self) -> bool:
        return self.slider.isDragging()


class PreviewWorker(QThread):
    finished = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, tonemapper: ToneMapper, hdr_image: np.ndarray, op: ToneMappingOperator):
        super().__init__()
        self.tonemapper = tonemapper
        self.hdr_image = hdr_image
        self.op = op

    def run(self):
        try:
            result = self.tonemapper.process(self.hdr_image, self.op)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SceneAnalysisWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, analyzer: SceneAnalyzer, files: List[str]):
        super().__init__()
        self.analyzer = analyzer
        self.files = files
        self._cancelled = False

    def run(self):
        try:
            results = {}
            total = len(self.files)
            from tone_mapping import ToneMapper

            for i, path in enumerate(self.files):
                if self._cancelled:
                    break

                self.progress.emit(i + 1, total, f"分析中: {os.path.basename(path)}")

                try:
                    img = ToneMapper.load_hdr(path)
                    features = self.analyzer.analyze_image(img)
                    results[path] = features
                except Exception as e:
                    print(f"Error analyzing {path}: {e}")

            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True


class SceneBatchWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, processor: BatchProcessor, scene_groups: Dict[SceneType, List[str]],
                 scene_params: Dict[SceneType, Dict[str, Any]], output_dir: str, output_format: str):
        super().__init__()
        self.processor = processor
        self.scene_groups = scene_groups
        self.scene_params = scene_params
        self.output_dir = output_dir
        self.output_format = output_format
        self._cancelled = False

    def run(self):
        try:
            all_results = []
            total_files = sum(len(files) for files in self.scene_groups.values())
            processed = 0

            from tone_mapping import ToneMapper, ToneMappingOperator

            for scene_type, files in self.scene_groups.items():
                if self._cancelled:
                    break

                if not files:
                    continue

                params_config = self.scene_params.get(scene_type)
                if not params_config:
                    continue

                op = ToneMappingOperator(params_config['operator'])
                params = params_config['params']

                for name, value in params.items():
                    self.processor.set_operator_params(op, {name: value})

                scene_output_dir = os.path.join(self.output_dir, scene_type.value)
                os.makedirs(scene_output_dir, exist_ok=True)

                for file_path in files:
                    if self._cancelled:
                        break

                    processed += 1
                    self.progress.emit(processed, total_files, f"[{scene_type.value}] {os.path.basename(file_path)}")

                    result = self.processor.process_single_file(file_path, scene_output_dir, op, self.output_format)
                    all_results.append(result)

            self.finished.emit(all_results)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True


class InverseWorker(QThread):
    finished = pyqtSignal(np.ndarray, np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, mapper: HDRInverseMapper, ldr_image: np.ndarray):
        super().__init__()
        self.mapper = mapper
        self.ldr_image = ldr_image

    def run(self):
        try:
            hdr, recovered = self.mapper.recover_overexposed_details(self.ldr_image)
            self.finished.emit(hdr, recovered)
        except Exception as e:
            self.error.emit(str(e))


class VideoWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, processor: HDRVideoProcessor, input_path: str, output_path: str,
                 auto_operator: bool = True, fixed_operator: Optional[ToneMappingOperator] = None):
        super().__init__()
        self.processor = processor
        self.input_path = input_path
        self.output_path = output_path
        self.auto_operator = auto_operator
        self.fixed_operator = fixed_operator
        self._cancelled = False

    def run(self):
        try:
            result = self.processor.process_video(
                self.input_path,
                self.output_path,
                auto_operator=self.auto_operator,
                fixed_operator=self.fixed_operator,
                progress_callback=lambda c, t, s: self.progress.emit(c, t, s)
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancelled = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HDR Tone Mapping Tool Ultimate")
        self.resize(1700, 1050)

        self.tonemapper = ToneMapper(use_gpu=False)
        self.preset_manager = PresetManager()
        self.batch_processor = BatchProcessor(use_gpu=False, max_workers=4)
        self.scene_analyzer = SceneAnalyzer()
        self.inverse_mapper = HDRInverseMapper()
        self.video_processor = HDRVideoProcessor(use_gpu=False, stabilization_mode=StabilizationMode.MEDIUM)

        self.current_hdr_image: Optional[np.ndarray] = None
        self.current_preview: Optional[np.ndarray] = None
        self.current_ldr_image: Optional[np.ndarray] = None
        self.current_recovered_hdr: Optional[np.ndarray] = None
        self.current_operator = ToneMappingOperator.REINHARD
        self.current_scene_features: Optional[SceneFeatures] = None
        self.auto_operator_enabled = False
        self.param_widgets: Dict[str, ParamWidget] = {}

        self.preview_worker: Optional[PreviewWorker] = None
        self.scene_worker: Optional[SceneAnalysisWorker] = None
        self.batch_worker: Optional[SceneBatchWorker] = None
        self.inverse_worker: Optional[InverseWorker] = None
        self.video_worker: Optional[VideoWorker] = None

        self.pending_preview = False
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._process_preview)

        self._create_menu()
        self._create_toolbar()
        self._create_ui()
        self._connect_signals()
        self._update_param_panel()

    def _create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("打开HDR图像...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

        save_action = QAction("保存结果...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        batch_menu = file_menu.addMenu("批量处理")
        batch_open_action = QAction("智能批量处理...", self)
        batch_open_action.triggered.connect(self.show_smart_batch_dialog)
        batch_menu.addAction(batch_open_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图(&V)")
        self.toggle_gpu_action = QAction("使用GPU加速", self, checkable=True)
        self.toggle_gpu_action.setChecked(False)
        self.toggle_gpu_action.triggered.connect(self.toggle_gpu)
        view_menu.addAction(self.toggle_gpu_action)

        preset_menu = menubar.addMenu("预设(&P)")
        save_preset_action = QAction("保存当前参数为预设...", self)
        save_preset_action.triggered.connect(self.save_preset)
        preset_menu.addAction(save_preset_action)

        import_preset_action = QAction("导入预设...", self)
        import_preset_action.triggered.connect(self.import_presets)
        preset_menu.addAction(import_preset_action)

        export_preset_action = QAction("导出所有预设...", self)
        export_preset_action.triggered.connect(self.export_presets)
        preset_menu.addAction(export_preset_action)

        scene_menu = menubar.addMenu("场景(&S)")
        analyze_action = QAction("分析当前图像场景", self)
        analyze_action.triggered.connect(self.analyze_current_scene)
        scene_menu.addAction(analyze_action)

        apply_scene_params_action = QAction("应用场景推荐参数", self)
        apply_scene_params_action.triggered.connect(self.apply_scene_recommended_params)
        scene_menu.addAction(apply_scene_params_action)

        scene_menu.addSeparator()

        self.auto_operator_action = QAction("自动选择最优算子", self, checkable=True)
        self.auto_operator_action.setChecked(False)
        self.auto_operator_action.triggered.connect(self.toggle_auto_operator)
        scene_menu.addAction(self.auto_operator_action)

        inverse_menu = menubar.addMenu("逆映射(&I)")
        open_ldr_action = QAction("打开LDR图像并恢复...", self)
        open_ldr_action.triggered.connect(self.open_ldr_and_recover)
        inverse_menu.addAction(open_ldr_action)

        inverse_method_menu = inverse_menu.addMenu("逆映射方法")
        self.inverse_method_actions = {}
        for method in InverseMappingMethod:
            action = QAction(method.value, self, checkable=True)
            action.setChecked(method == InverseMappingMethod.CHANNEL_RECOVERY)
            action.triggered.connect(lambda checked, m=method: self.set_inverse_method(m))
            self.inverse_method_actions[method] = action
            inverse_method_menu.addAction(action)

        video_menu = menubar.addMenu("视频(&V)")
        process_video_action = QAction("处理HDR视频...", self)
        process_video_action.triggered.connect(self.process_hdr_video)
        video_menu.addAction(process_video_action)

        video_menu.addSeparator()

        stab_menu = video_menu.addMenu("帧间稳定性")
        self.stab_actions = {}
        for mode in StabilizationMode:
            action = QAction(mode.value, self, checkable=True)
            action.setChecked(mode == StabilizationMode.MEDIUM)
            action.triggered.connect(lambda checked, m=mode: self.set_stabilization_mode(m))
            self.stab_actions[mode] = action
            stab_menu.addAction(action)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        toolbar = QToolBar("主工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("打开HDR", self)
        open_action.triggered.connect(self.open_image)
        toolbar.addAction(open_action)

        open_ldr_action = QAction("打开LDR", self)
        open_ldr_action.triggered.connect(self.open_ldr_and_recover)
        toolbar.addAction(open_ldr_action)

        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_image)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        analyze_action = QAction("分析场景", self)
        analyze_action.triggered.connect(self.analyze_current_scene)
        toolbar.addAction(analyze_action)

        apply_scene_action = QAction("应用场景参数", self)
        apply_scene_action.triggered.connect(self.apply_scene_recommended_params)
        toolbar.addAction(apply_scene_action)

        toolbar.addSeparator()

        self.auto_operator_btn = QPushButton("自动算子: OFF")
        self.auto_operator_btn.setCheckable(True)
        self.auto_operator_btn.clicked.connect(self.toggle_auto_operator)
        toolbar.addWidget(self.auto_operator_btn)

        toolbar.addSeparator()

        self.gpu_button = QPushButton("GPU: OFF")
        self.gpu_button.setCheckable(True)
        self.gpu_button.clicked.connect(self.toggle_gpu)
        toolbar.addWidget(self.gpu_button)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = self._create_left_panel()
        center_panel = self._create_center_panel()
        right_panel = self._create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        op_group = QGroupBox("色调映射算子")
        op_layout = QVBoxLayout(op_group)

        self.op_combo = QComboBox()
        self.op_combo.addItem("Reinhard", ToneMappingOperator.REINHARD)
        self.op_combo.addItem("Filmic", ToneMappingOperator.FILMIC)
        self.op_combo.addItem("ACES", ToneMappingOperator.ACES)
        op_layout.addWidget(self.op_combo)

        layout.addWidget(op_group)

        preset_group = QGroupBox("参数预设")
        preset_layout = QVBoxLayout(preset_group)

        self.preset_combo = QComboBox()
        self._refresh_preset_combo()
        preset_layout.addWidget(self.preset_combo)

        preset_buttons = QHBoxLayout()
        self.apply_preset_btn = QPushButton("应用")
        self.apply_preset_btn.clicked.connect(self.apply_preset)
        self.del_preset_btn = QPushButton("删除")
        self.del_preset_btn.clicked.connect(self.delete_preset)
        preset_buttons.addWidget(self.apply_preset_btn)
        preset_buttons.addWidget(self.del_preset_btn)
        preset_layout.addLayout(preset_buttons)

        layout.addWidget(preset_group)

        scene_info_group = QGroupBox("场景分析")
        scene_info_layout = QVBoxLayout(scene_info_group)
        self.scene_info_label = QLabel("未分析")
        self.scene_info_label.setWordWrap(True)
        scene_info_layout.addWidget(self.scene_info_label)

        self.analyze_btn = QPushButton("分析当前图像")
        self.analyze_btn.clicked.connect(self.analyze_current_scene)
        scene_info_layout.addWidget(self.analyze_btn)

        self.apply_scene_btn = QPushButton("应用推荐参数")
        self.apply_scene_btn.clicked.connect(self.apply_scene_recommended_params)
        self.apply_scene_btn.setEnabled(False)
        scene_info_layout.addWidget(self.apply_scene_btn)

        layout.addWidget(scene_info_group)

        auto_op_group = QGroupBox("自动算子选择")
        auto_op_layout = QVBoxLayout(auto_op_group)
        self.auto_op_info_label = QLabel("自动选择: 关闭")
        self.auto_op_info_label.setWordWrap(True)
        auto_op_layout.addWidget(self.auto_op_info_label)

        self.toggle_auto_op_btn = QPushButton("启用自动算子选择")
        self.toggle_auto_op_btn.setCheckable(True)
        self.toggle_auto_op_btn.clicked.connect(self.toggle_auto_operator)
        auto_op_layout.addWidget(self.toggle_auto_op_btn)

        self.apply_auto_op_btn = QPushButton("立即应用最优算子")
        self.apply_auto_op_btn.clicked.connect(self.apply_optimal_operator)
        self.apply_auto_op_btn.setEnabled(False)
        auto_op_layout.addWidget(self.apply_auto_op_btn)

        layout.addWidget(auto_op_group)

        inverse_group = QGroupBox("LDR→HDR逆映射")
        inverse_layout = QVBoxLayout(inverse_group)
        self.inverse_info_label = QLabel("未处理")
        self.inverse_info_label.setWordWrap(True)
        inverse_layout.addWidget(self.inverse_info_label)

        inverse_method_layout = QHBoxLayout()
        inverse_method_layout.addWidget(QLabel("方法:"))
        self.inverse_method_combo = QComboBox()
        for method in InverseMappingMethod:
            self.inverse_method_combo.addItem(method.value, method)
        self.inverse_method_combo.setCurrentIndex(3)
        self.inverse_method_combo.currentIndexChanged.connect(self._on_inverse_method_changed)
        inverse_method_layout.addWidget(self.inverse_method_combo)
        inverse_layout.addLayout(inverse_method_layout)

        self.recover_details_btn = QPushButton("从LDR恢复过曝细节")
        self.recover_details_btn.clicked.connect(self.recover_overexposed_details)
        self.recover_details_btn.setEnabled(False)
        inverse_layout.addWidget(self.recover_details_btn)

        layout.addWidget(inverse_group)

        self.param_group = QGroupBox("参数调节 (松手后更新预览)")
        self.param_layout = QVBoxLayout(self.param_group)
        self.param_layout.setSpacing(5)
        layout.addWidget(self.param_group, 1)

        return panel

    def _create_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        image_splitter = QSplitter(Qt.Vertical)

        hdr_group = QGroupBox("HDR 原图")
        hdr_layout = QVBoxLayout(hdr_group)
        self.hdr_label = QLabel("请打开HDR图像")
        self.hdr_label.setAlignment(Qt.AlignCenter)
        self.hdr_label.setMinimumSize(400, 300)
        self.hdr_label.setStyleSheet("QLabel { background-color: #222; color: #888; border: 1px solid #444; }")
        hdr_layout.addWidget(self.hdr_label)
        image_splitter.addWidget(hdr_group)

        ldr_group = QGroupBox("LDR 预览结果")
        ldr_layout = QVBoxLayout(ldr_group)
        self.ldr_label = QLabel("调整参数以查看预览")
        self.ldr_label.setAlignment(Qt.AlignCenter)
        self.ldr_label.setMinimumSize(400, 300)
        self.ldr_label.setStyleSheet("QLabel { background-color: #222; color: #888; border: 1px solid #444; }")
        ldr_layout.addWidget(self.ldr_label)
        image_splitter.addWidget(ldr_group)

        layout.addWidget(image_splitter, 1)

        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.batch_tabs = QTabWidget()

        simple_batch_tab = self._create_simple_batch_tab()
        smart_batch_tab = self._create_smart_batch_tab()
        video_tab = self._create_video_tab()
        inverse_tab = self._create_inverse_tab()

        self.batch_tabs.addTab(simple_batch_tab, "简单批量")
        self.batch_tabs.addTab(smart_batch_tab, "智能批量(场景分类)")
        self.batch_tabs.addTab(video_tab, "视频处理")
        self.batch_tabs.addTab(inverse_tab, "LDR→HDR逆映射")

        layout.addWidget(self.batch_tabs)

        return panel

    def _create_video_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        select_video_btn = QPushButton("选择HDR视频...")
        select_video_btn.clicked.connect(self.select_hdr_video)
        layout.addWidget(select_video_btn)

        self.video_path_label = QLabel("未选择视频")
        self.video_path_label.setWordWrap(True)
        self.video_path_label.setStyleSheet("color: #888;")
        layout.addWidget(self.video_path_label)

        auto_op_layout = QHBoxLayout()
        auto_op_layout.addWidget(QLabel("算子选择:"))
        self.video_op_combo = QComboBox()
        self.video_op_combo.addItem("自动选择", "auto")
        self.video_op_combo.addItem("Reinhard", ToneMappingOperator.REINHARD)
        self.video_op_combo.addItem("Filmic", ToneMappingOperator.FILMIC)
        self.video_op_combo.addItem("ACES", ToneMappingOperator.ACES)
        auto_op_layout.addWidget(self.video_op_combo)
        layout.addLayout(auto_op_layout)

        stab_layout = QHBoxLayout()
        stab_layout.addWidget(QLabel("帧间稳定性:"))
        self.video_stab_combo = QComboBox()
        for mode in StabilizationMode:
            self.video_stab_combo.addItem(mode.value, mode)
        self.video_stab_combo.setCurrentIndex(2)
        stab_layout.addWidget(self.video_stab_combo)
        layout.addLayout(stab_layout)

        self.video_output_btn = QPushButton("选择输出目录...")
        self.video_output_btn.clicked.connect(self.select_video_output)
        layout.addWidget(self.video_output_btn)

        self.video_output_label = QLabel("未选择")
        self.video_output_label.setStyleSheet("color: #888;")
        self.video_output_label.setWordWrap(True)
        layout.addWidget(self.video_output_label)

        self.video_progress = QProgressBar()
        self.video_progress.setVisible(False)
        layout.addWidget(self.video_progress)

        self.video_status_label = QLabel("")
        self.video_status_label.setWordWrap(True)
        layout.addWidget(self.video_status_label)

        self.start_video_btn = QPushButton("开始视频处理")
        self.start_video_btn.clicked.connect(self.start_video_processing)
        self.start_video_btn.setEnabled(False)
        layout.addWidget(self.start_video_btn)

        self.cancel_video_btn = QPushButton("取消")
        self.cancel_video_btn.setVisible(False)
        self.cancel_video_btn.clicked.connect(self.cancel_video_processing)
        layout.addWidget(self.cancel_video_btn)

        self.video_input_path = ""
        self.video_output_dir = ""
        return tab

    def _create_inverse_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        select_ldr_btn = QPushButton("选择LDR图像...")
        select_ldr_btn.clicked.connect(self.select_ldr_for_inverse)
        layout.addWidget(select_ldr_btn)

        self.inverse_file_label = QLabel("未选择图像")
        self.inverse_file_label.setWordWrap(True)
        self.inverse_file_label.setStyleSheet("color: #888;")
        layout.addWidget(self.inverse_file_label)

        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("逆映射方法:"))
        self.inverse_tab_method = QComboBox()
        for method in InverseMappingMethod:
            self.inverse_tab_method.addItem(method.value, method)
        self.inverse_tab_method.setCurrentIndex(3)
        method_layout.addWidget(self.inverse_tab_method)
        layout.addLayout(method_layout)

        gamma_layout = QHBoxLayout()
        gamma_layout.addWidget(QLabel("Gamma:"))
        self.inverse_gamma_spin = QDoubleSpinBox()
        self.inverse_gamma_spin.setRange(1.0, 5.0)
        self.inverse_gamma_spin.setSingleStep(0.1)
        self.inverse_gamma_spin.setValue(2.2)
        gamma_layout.addWidget(self.inverse_gamma_spin)
        layout.addLayout(gamma_layout)

        max_bright_layout = QHBoxLayout()
        max_bright_layout.addWidget(QLabel("最大亮度:"))
        self.inverse_max_bright_spin = QDoubleSpinBox()
        self.inverse_max_bright_spin.setRange(1.0, 100.0)
        self.inverse_max_bright_spin.setSingleStep(0.5)
        self.inverse_max_bright_spin.setValue(10.0)
        max_bright_layout.addWidget(self.inverse_max_bright_spin)
        layout.addLayout(max_bright_layout)

        self.inverse_progress = QProgressBar()
        self.inverse_progress.setVisible(False)
        layout.addWidget(self.inverse_progress)

        self.inverse_status_label = QLabel("")
        layout.addWidget(self.inverse_status_label)

        self.start_inverse_btn = QPushButton("执行逆映射")
        self.start_inverse_btn.clicked.connect(self.execute_inverse_mapping)
        self.start_inverse_btn.setEnabled(False)
        layout.addWidget(self.start_inverse_btn)

        self.save_inverse_btn = QPushButton("保存HDR结果")
        self.save_inverse_btn.clicked.connect(self.save_inverse_result)
        self.save_inverse_btn.setEnabled(False)
        layout.addWidget(self.save_inverse_btn)

        self.ldr_for_inverse: Optional[np.ndarray] = None
        self.inverse_result_hdr: Optional[np.ndarray] = None
        return tab

    def _create_simple_batch_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        select_files_btn = QPushButton("选择文件...")
        select_files_btn.clicked.connect(self.select_batch_files)
        layout.addWidget(select_files_btn)

        select_folder_btn = QPushButton("选择文件夹...")
        select_folder_btn.clicked.connect(self.select_batch_folder)
        layout.addWidget(select_folder_btn)

        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.batch_list, 1)

        remove_btn = QPushButton("移除选中")
        remove_btn.clicked.connect(self.remove_selected_files)
        layout.addWidget(remove_btn)

        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_batch_files)
        layout.addWidget(clear_btn)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        for fmt in BatchProcessor.get_supported_formats():
            self.format_combo.addItem(fmt.upper(), fmt)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        self.output_dir_edit = QPushButton("选择输出目录...")
        self.output_dir_edit.clicked.connect(self.select_output_dir)
        layout.addWidget(self.output_dir_edit)

        self.output_dir_label = QLabel("未选择")
        self.output_dir_label.setStyleSheet("color: #888;")
        self.output_dir_label.setWordWrap(True)
        layout.addWidget(self.output_dir_label)

        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        layout.addWidget(self.batch_progress)

        self.batch_status_label = QLabel("")
        self.batch_status_label.setWordWrap(True)
        layout.addWidget(self.batch_status_label)

        self.start_batch_btn = QPushButton("开始批量处理")
        self.start_batch_btn.clicked.connect(self.start_simple_batch)
        layout.addWidget(self.start_batch_btn)

        self.cancel_batch_btn = QPushButton("取消")
        self.cancel_batch_btn.setVisible(False)
        self.cancel_batch_btn.clicked.connect(self.cancel_batch_processing)
        layout.addWidget(self.cancel_batch_btn)

        self.output_dir = ""
        return tab

    def _create_smart_batch_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        self.smart_batch_files: List[str] = []
        self.scene_analysis_results: Dict[str, SceneFeatures] = {}
        self.scene_groups: Dict[SceneType, List[str]] = {st: [] for st in SceneType}

        add_files_btn = QPushButton("添加文件...")
        add_files_btn.clicked.connect(self.smart_add_files)
        layout.addWidget(add_files_btn)

        add_folder_btn = QPushButton("添加文件夹...")
        add_folder_btn.clicked.connect(self.smart_add_folder)
        layout.addWidget(add_folder_btn)

        self.analyze_scenes_btn = QPushButton("分析所有场景")
        self.analyze_scenes_btn.clicked.connect(self.analyze_all_scenes)
        layout.addWidget(self.analyze_scenes_btn)

        self.smart_progress = QProgressBar()
        self.smart_progress.setVisible(False)
        layout.addWidget(self.smart_progress)

        self.smart_status_label = QLabel("请添加文件")
        layout.addWidget(self.smart_status_label)

        self.scene_table = QTableWidget()
        self.scene_table.setColumnCount(3)
        self.scene_table.setHorizontalHeaderLabels(["场景类型", "文件数", "算子"])
        self.scene_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.scene_table)

        self.edit_scene_params_btn = QPushButton("编辑场景参数...")
        self.edit_scene_params_btn.clicked.connect(self.edit_scene_parameters)
        self.edit_scene_params_btn.setEnabled(False)
        layout.addWidget(self.edit_scene_params_btn)

        self.smart_output_dir = ""
        self.smart_output_btn = QPushButton("选择输出目录...")
        self.smart_output_btn.clicked.connect(self.select_smart_output_dir)
        layout.addWidget(self.smart_output_btn)

        self.smart_output_label = QLabel("未选择")
        self.smart_output_label.setStyleSheet("color: #888;")
        layout.addWidget(self.smart_output_label)

        self.start_smart_batch_btn = QPushButton("开始智能批量处理")
        self.start_smart_batch_btn.clicked.connect(self.start_smart_batch)
        self.start_smart_batch_btn.setEnabled(False)
        layout.addWidget(self.start_smart_batch_btn)

        self.cancel_smart_btn = QPushButton("取消")
        self.cancel_smart_btn.setVisible(False)
        self.cancel_smart_btn.clicked.connect(self.cancel_smart_batch)
        layout.addWidget(self.cancel_smart_btn)

        return tab

    def _connect_signals(self):
        self.op_combo.currentIndexChanged.connect(self._on_operator_changed)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)

    def _update_param_panel(self):
        while self.param_layout.count() > 0:
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.param_widgets.clear()

        param_definitions = {
            ToneMappingOperator.REINHARD: [
                ('intensity', -8.0, 8.0, 0.0, 0.01),
                ('light_adapt', 0.0, 1.0, 1.0, 0.01),
                ('color_adapt', 0.0, 1.0, 0.0, 0.01),
                ('gamma', 0.1, 5.0, 2.2, 0.1)
            ],
            ToneMappingOperator.FILMIC: [
                ('contrast', 0.1, 3.0, 1.0, 0.01),
                ('shoulder', 0.0, 1.0, 0.5, 0.01),
                ('linear', 0.0, 0.5, 0.1, 0.001),
                ('linear_angle', 0.0, 1.0, 0.1, 0.01),
                ('toe_num_a', 0.0, 2.0, 0.55, 0.01),
                ('toe_num_b', 0.0, 0.1, 0.01, 0.001),
                ('toe_den_a', 0.0, 2.0, 0.4, 0.01),
                ('toe_den_b', 0.0, 0.1, 0.02, 0.001),
                ('gamma', 0.1, 5.0, 2.2, 0.1)
            ],
            ToneMappingOperator.ACES: [
                ('exposure', 0.1, 5.0, 1.0, 0.01),
                ('saturation', 0.0, 3.0, 1.0, 0.01),
                ('gamma', 0.1, 5.0, 2.2, 0.1)
            ]
        }

        params = param_definitions.get(self.current_operator, [])
        current_params = self.tonemapper.get_params(self.current_operator)

        for name, min_val, max_val, default_val, step in params:
            value = current_params.get(name, default_val)
            param_widget = ParamWidget(name, min_val, max_val, value, step)
            param_widget.valueChanged.connect(self._on_param_preview)
            param_widget.valueApplied.connect(self._on_param_applied)
            self.param_widgets[name] = param_widget
            self.param_layout.addWidget(param_widget)

        self.param_layout.addStretch(1)

        save_btn = QPushButton("保存当前参数为预设...")
        save_btn.clicked.connect(self.save_preset)
        self.param_layout.addWidget(save_btn)

    def _on_operator_changed(self, index: int):
        self.current_operator = self.op_combo.currentData()
        self._update_param_panel()
        self._refresh_preset_combo()
        self._schedule_preview()

    def _on_param_preview(self, name: str, value: float):
        self.tonemapper.set_param(self.current_operator, name, value)
        self.pending_preview = True

    def _on_param_applied(self, name: str, value: float):
        self.tonemapper.set_param(self.current_operator, name, value)
        self._process_preview()

    def _schedule_preview(self):
        self.pending_preview = True
        self.debounce_timer.start()

    def _process_preview(self):
        if self.current_hdr_image is None:
            return

        if self.preview_worker is not None and self.preview_worker.isRunning():
            return

        self.statusBar.showMessage("正在处理...")

        self.preview_worker = PreviewWorker(
            self.tonemapper,
            self.current_hdr_image.copy(),
            self.current_operator
        )
        self.preview_worker.finished.connect(self._on_preview_finished)
        self.preview_worker.error.connect(self._on_preview_error)
        self.preview_worker.start()

    def _on_preview_finished(self, result: np.ndarray):
        self.current_preview = result
        self._display_image(self.ldr_label, result)
        self.statusBar.showMessage("处理完成")

    def _on_preview_error(self, error: str):
        self.statusBar.showMessage(f"处理错误: {error}")

    def _display_image(self, label: QLabel, img: np.ndarray):
        if img is None:
            return

        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        h, w, ch = img.shape
        bytes_per_line = ch * w
        qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        label.setPixmap(scaled_pixmap)

    def open_image(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "打开HDR图像",
            "",
            "HDR Images (*.hdr *.exr *.tif *.tiff);;All Files (*.*)"
        )
        if filepath:
            try:
                self.statusBar.showMessage(f"正在加载: {filepath}")
                self.current_hdr_image = ToneMapper.load_hdr(filepath)
                self.current_scene_features = None
                self.scene_info_label.setText("未分析")
                self.apply_scene_btn.setEnabled(False)

                preview = np.clip(self.current_hdr_image * 255.0, 0, 255).astype(np.uint8)
                self._display_image(self.hdr_label, preview)

                self._process_preview()
                self.statusBar.showMessage(f"已加载: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载图像: {e}")

    def save_image(self):
        if self.current_preview is None:
            QMessageBox.warning(self, "警告", "没有可保存的图像")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "保存LDR图像",
            "",
            "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;BMP Images (*.bmp);;TIFF Images (*.tif *.tiff)"
        )
        if filepath:
            try:
                ToneMapper.save_ldr(filepath, self.current_preview)
                self.statusBar.showMessage(f"已保存到: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存图像: {e}")

    def toggle_gpu(self, checked: bool):
        self.toggle_gpu_action.setChecked(checked)
        self.gpu_button.setChecked(checked)
        self.gpu_button.setText("GPU: ON" if checked else "GPU: OFF")

        self.tonemapper = ToneMapper(use_gpu=checked)
        self.batch_processor = BatchProcessor(use_gpu=checked, max_workers=4)

        for name, widget in self.param_widgets.items():
            self.tonemapper.set_param(self.current_operator, name, widget.get_value())

        if checked:
            if self.tonemapper.use_gpu:
                self.statusBar.showMessage("GPU加速已启用")
            else:
                QMessageBox.warning(self, "GPU不可用", "未检测到支持CUDA的GPU，已回退到CPU模式")
                self.toggle_gpu(False)
                return
        else:
            self.statusBar.showMessage("GPU加速已禁用")

        self._process_preview()

    def _refresh_preset_combo(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("-- 选择预设 --", None)

        for name in self.preset_manager.get_preset_names():
            self.preset_combo.addItem(name, name)

        self.preset_combo.blockSignals(False)

    def apply_preset(self):
        preset_name = self.preset_combo.currentData()
        if not preset_name:
            return

        preset = self.preset_manager.load_preset(preset_name)
        if preset:
            self.current_operator = preset["operator"]
            self.op_combo.setCurrentIndex(self.op_combo.findData(preset["operator"]))

            for name, value in preset["params"].items():
                if name in self.param_widgets:
                    self.param_widgets[name].set_value(value)

            self._process_preview()
            self.statusBar.showMessage(f"已应用预设: {preset_name}")

    def save_preset(self):
        name, ok = QInputDialog.getText(self, "保存预设", "输入预设名称:")
        if ok and name:
            params = {name: w.get_value() for name, w in self.param_widgets.items()}
            self.preset_manager.save_preset(name, self.current_operator, params)
            self._refresh_preset_combo()
            self.preset_combo.setCurrentIndex(self.preset_combo.findData(name))
            self.statusBar.showMessage(f"预设已保存: {name}")

    def delete_preset(self):
        preset_name = self.preset_combo.currentData()
        if not preset_name:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除预设 '{preset_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.preset_manager.delete_preset(preset_name)
            self._refresh_preset_combo()
            self.statusBar.showMessage(f"预设已删除: {preset_name}")

    def import_presets(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入预设", "", "JSON Files (*.json)"
        )
        if filepath:
            reply = QMessageBox.question(
                self, "导入方式",
                "是否合并到现有预设？\nYes: 合并\nNo: 替换现有预设",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return

            merge = (reply == QMessageBox.Yes)
            if self.preset_manager.import_presets(filepath, merge):
                self._refresh_preset_combo()
                self.statusBar.showMessage("预设导入成功")
            else:
                QMessageBox.critical(self, "错误", "预设导入失败")

    def export_presets(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出预设", "", "JSON Files (*.json)"
        )
        if filepath:
            if self.preset_manager.export_presets(filepath):
                self.statusBar.showMessage(f"预设已导出到: {filepath}")
            else:
                QMessageBox.critical(self, "错误", "预设导出失败")

    def analyze_current_scene(self):
        if self.current_hdr_image is None:
            QMessageBox.warning(self, "警告", "请先打开HDR图像")
            return

        try:
            self.statusBar.showMessage("正在分析场景...")
            self.current_scene_features = self.scene_analyzer.analyze_image(self.current_hdr_image)

            scene_name = self.scene_analyzer.get_scene_name(self.current_scene_features.scene_type)
            info_text = (
                f"场景类型: {scene_name}\n"
                f"置信度: {self.current_scene_features.confidence:.1%}\n"
                f"平均亮度: {self.current_scene_features.mean_brightness:.2f}\n"
                f"对比度: {self.current_scene_features.std_brightness:.2f}\n"
                f"动态范围: {self.current_scene_features.dynamic_range:.2f}\n"
                f"色温: {self.current_scene_features.color_temperature:.0f}K\n"
                f"饱和度: {self.current_scene_features.saturation_mean:.2f}"
            )
            self.scene_info_label.setText(info_text)
            self.apply_scene_btn.setEnabled(True)
            self.statusBar.showMessage(f"场景分析完成: {scene_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"场景分析失败: {e}")

    def apply_scene_recommended_params(self):
        if self.current_scene_features is None:
            QMessageBox.warning(self, "警告", "请先分析场景")
            return

        params_config = self.scene_analyzer.get_scene_params(self.current_scene_features.scene_type)

        op = ToneMappingOperator(params_config['operator'])
        self.current_operator = op
        self.op_combo.setCurrentIndex(self.op_combo.findData(op))

        for name, value in params_config['params'].items():
            if name in self.param_widgets:
                self.param_widgets[name].set_value(value)

        self._process_preview()
        scene_name = self.scene_analyzer.get_scene_name(self.current_scene_features.scene_type)
        self.statusBar.showMessage(f"已应用 {scene_name} 推荐参数")

    def select_batch_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择HDR文件",
            "",
            "HDR Images (*.hdr *.exr *.tif *.tiff);;All Files (*.*)"
        )
        for f in files:
            if not self._is_file_in_batch(f):
                item = QListWidgetItem(f)
                self.batch_list.addItem(item)
        self._update_batch_status()

    def select_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含HDR文件的文件夹")
        if folder:
            recursive = QMessageBox.question(
                self, "递归搜索",
                "是否递归搜索子文件夹？",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes

            files = self.batch_processor.find_hdr_files(folder, recursive=recursive)
            for f in files:
                if not self._is_file_in_batch(f):
                    item = QListWidgetItem(f)
                    self.batch_list.addItem(item)
            self._update_batch_status()

    def _is_file_in_batch(self, filepath: str) -> bool:
        for i in range(self.batch_list.count()):
            if self.batch_list.item(i).text() == filepath:
                return True
        return False

    def remove_selected_files(self):
        for item in self.batch_list.selectedItems():
            self.batch_list.takeItem(self.batch_list.row(item))
        self._update_batch_status()

    def clear_batch_files(self):
        self.batch_list.clear()
        self._update_batch_status()

    def select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_dir = folder
            self.output_dir_label.setText(folder)
            self.output_dir_label.setStyleSheet("color: #000;")

    def start_simple_batch(self):
        files = [self.batch_list.item(i).text() for i in range(self.batch_list.count())]
        if not files:
            QMessageBox.warning(self, "警告", "请先选择要处理的文件")
            return

        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请先选择输出目录")
            return

        op = self.current_operator
        output_format = self.format_combo.currentData()

        for name, widget in self.param_widgets.items():
            self.batch_processor.set_operator_params(op, {name: widget.get_value()})

        self.batch_progress.setVisible(True)
        self.batch_progress.setMaximum(len(files))
        self.batch_progress.setValue(0)
        self.start_batch_btn.setVisible(False)
        self.cancel_batch_btn.setVisible(True)
        self.batch_status_label.setText("处理中...")

        self.batch_worker = BatchWorker(
            self.batch_processor, files, self.output_dir, op, output_format
        )
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_finished)
        self.batch_worker.error.connect(self._on_batch_error)
        self.batch_worker.start()

    def cancel_batch_processing(self):
        if self.batch_processor.is_running:
            self.batch_processor.cancel()
            self.batch_status_label.setText("正在取消...")

    def _on_batch_progress(self, completed: int, total: int, status: str):
        self.batch_progress.setValue(completed)
        self.batch_status_label.setText(f"处理中 ({completed}/{total}): {status}")

    def _on_batch_finished(self, results: list):
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - sum(1 for r in results if r['success'])

        self.batch_progress.setVisible(False)
        self.start_batch_btn.setVisible(True)
        self.cancel_batch_btn.setVisible(False)
        self.batch_status_label.setText(f"完成！成功: {success_count}, 失败: {fail_count}")

        if fail_count > 0:
            errors = "\n".join([f"{r['input']}: {r['error']}" for r in results if not r['success']])
            QMessageBox.warning(
                self, "处理完成",
                f"处理完成！\n成功: {success_count}\n失败: {fail_count}\n\n失败详情:\n{errors[:500]}"
            )
        else:
            QMessageBox.information(self, "处理完成", f"所有文件处理成功！共 {success_count} 个文件。")

    def _on_batch_error(self, error: str):
        self.batch_progress.setVisible(False)
        self.start_batch_btn.setVisible(True)
        self.cancel_batch_btn.setVisible(False)
        self.batch_status_label.setText(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"批量处理出错: {error}")

    def _update_batch_status(self):
        count = self.batch_list.count()
        self.statusBar.showMessage(f"待处理文件: {count} 个")

    def smart_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择HDR文件",
            "",
            "HDR Images (*.hdr *.exr *.tif *.tiff);;All Files (*.*)"
        )
        for f in files:
            if f not in self.smart_batch_files:
                self.smart_batch_files.append(f)
        self.smart_status_label.setText(f"已添加 {len(self.smart_batch_files)} 个文件")

    def smart_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含HDR文件的文件夹")
        if folder:
            recursive = QMessageBox.question(
                self, "递归搜索",
                "是否递归搜索子文件夹？",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes

            files = self.batch_processor.find_hdr_files(folder, recursive=recursive)
            for f in files:
                if f not in self.smart_batch_files:
                    self.smart_batch_files.append(f)
            self.smart_status_label.setText(f"已添加 {len(self.smart_batch_files)} 个文件")

    def analyze_all_scenes(self):
        if not self.smart_batch_files:
            QMessageBox.warning(self, "警告", "请先添加文件")
            return

        self.smart_progress.setVisible(True)
        self.smart_progress.setMaximum(len(self.smart_batch_files))
        self.smart_progress.setValue(0)
        self.analyze_scenes_btn.setEnabled(False)
        self.smart_status_label.setText("分析中...")

        self.scene_worker = SceneAnalysisWorker(self.scene_analyzer, self.smart_batch_files)
        self.scene_worker.progress.connect(self._on_scene_analysis_progress)
        self.scene_worker.finished.connect(self._on_scene_analysis_finished)
        self.scene_worker.error.connect(self._on_scene_analysis_error)
        self.scene_worker.start()

    def _on_scene_analysis_progress(self, completed: int, total: int, status: str):
        self.smart_progress.setValue(completed)
        self.smart_status_label.setText(status)

    def _on_scene_analysis_finished(self, results: Dict[str, SceneFeatures]):
        self.scene_analysis_results = results

        self.scene_groups = {st: [] for st in SceneType}
        for path, features in results.items():
            self.scene_groups[features.scene_type].append(path)

        self._update_scene_table()

        self.smart_progress.setVisible(False)
        self.analyze_scenes_btn.setEnabled(True)
        self.edit_scene_params_btn.setEnabled(True)
        self.start_smart_batch_btn.setEnabled(True)
        self.smart_status_label.setText(f"分析完成，共 {len(results)} 个文件")

    def _on_scene_analysis_error(self, error: str):
        self.smart_progress.setVisible(False)
        self.analyze_scenes_btn.setEnabled(True)
        self.smart_status_label.setText(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"场景分析出错: {error}")

    def _update_scene_table(self):
        self.scene_table.setRowCount(len(SceneType))

        for i, scene_type in enumerate(SceneType):
            scene_name = self.scene_analyzer.get_scene_name(scene_type)
            file_count = len(self.scene_groups[scene_type])
            params_config = self.scene_analyzer.get_scene_params(scene_type)
            op_name = params_config['operator']

            self.scene_table.setItem(i, 0, QTableWidgetItem(scene_name))
            self.scene_table.setItem(i, 1, QTableWidgetItem(str(file_count)))
            self.scene_table.setItem(i, 2, QTableWidgetItem(op_name))

    def edit_scene_parameters(self):
        QMessageBox.information(self, "提示", "场景参数编辑功能可通过代码配置。\n\n当前使用默认场景参数配置。")

    def select_smart_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.smart_output_dir = folder
            self.smart_output_label.setText(folder)
            self.smart_output_label.setStyleSheet("color: #000;")

    def start_smart_batch(self):
        if not self.smart_output_dir:
            QMessageBox.warning(self, "警告", "请先选择输出目录")
            return

        total_files = sum(len(files) for files in self.scene_groups.values())
        if total_files == 0:
            QMessageBox.warning(self, "警告", "没有可处理的文件")
            return

        output_format = self.format_combo.currentData()

        self.smart_progress.setVisible(True)
        self.smart_progress.setMaximum(total_files)
        self.smart_progress.setValue(0)
        self.start_smart_batch_btn.setVisible(False)
        self.cancel_smart_btn.setVisible(True)
        self.smart_status_label.setText("智能批量处理中...")

        self.batch_worker = SceneBatchWorker(
            self.batch_processor,
            self.scene_groups,
            {st: self.scene_analyzer.get_scene_params(st) for st in SceneType},
            self.smart_output_dir,
            output_format
        )
        self.batch_worker.progress.connect(self._on_smart_batch_progress)
        self.batch_worker.finished.connect(self._on_smart_batch_finished)
        self.batch_worker.error.connect(self._on_smart_batch_error)
        self.batch_worker.start()

    def _on_smart_batch_progress(self, completed: int, total: int, status: str):
        self.smart_progress.setValue(completed)
        self.smart_status_label.setText(status)

    def _on_smart_batch_finished(self, results: list):
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - sum(1 for r in results if r['success'])

        self.smart_progress.setVisible(False)
        self.start_smart_batch_btn.setVisible(True)
        self.cancel_smart_btn.setVisible(False)
        self.smart_status_label.setText(f"完成！成功: {success_count}, 失败: {fail_count}")

        if fail_count > 0:
            QMessageBox.warning(
                self, "处理完成",
                f"智能批量处理完成！\n成功: {success_count}\n失败: {fail_count}"
            )
        else:
            QMessageBox.information(self, "处理完成", f"智能批量处理成功！共 {success_count} 个文件。\n\n按场景分类保存在不同子目录中。")

    def _on_smart_batch_error(self, error: str):
        self.smart_progress.setVisible(False)
        self.start_smart_batch_btn.setVisible(True)
        self.cancel_smart_btn.setVisible(False)
        self.smart_status_label.setText(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"智能批量处理出错: {error}")

    def cancel_smart_batch(self):
        if self.batch_worker is not None:
            self.batch_worker.cancel()
            self.smart_status_label.setText("正在取消...")

    def show_smart_batch_dialog(self):
        self.batch_tabs.setCurrentIndex(1)

    def toggle_auto_operator(self, checked: bool):
        self.auto_operator_enabled = checked
        self.auto_operator_action.setChecked(checked)
        self.auto_operator_btn.setChecked(checked)
        self.auto_operator_btn.setText("自动算子: ON" if checked else "自动算子: OFF")
        self.toggle_auto_op_btn.setChecked(checked)
        self.toggle_auto_op_btn.setText("关闭自动算子选择" if checked else "启用自动算子选择")

        if checked:
            self.auto_op_info_label.setText("自动选择: 已启用")
            if self.current_scene_features is not None:
                self.apply_optimal_operator()
            self.statusBar.showMessage("自动算子选择已启用")
        else:
            self.auto_op_info_label.setText("自动选择: 关闭")
            self.statusBar.showMessage("自动算子选择已禁用")

        self.apply_auto_op_btn.setEnabled(checked and self.current_scene_features is not None)

    def apply_optimal_operator(self):
        if self.current_scene_features is None:
            QMessageBox.warning(self, "警告", "请先分析场景")
            return

        try:
            best_op, params, confidence = self.scene_analyzer.select_optimal_operator(
                self.current_scene_features
            )

            self.current_operator = best_op
            self.op_combo.setCurrentIndex(self.op_combo.findData(best_op))

            for name, value in params.items():
                if name in self.param_widgets:
                    self.param_widgets[name].set_value(value)

            self._process_preview()

            info_text = (
                f"自动选择: {best_op.value}\n"
                f"置信度: {confidence:.1%}"
            )
            if self.auto_operator_enabled:
                info_text = "自动选择: 已启用\n" + info_text
            self.auto_op_info_label.setText(info_text)

            self.statusBar.showMessage(f"已应用最优算子: {best_op.value} (置信度: {confidence:.1%})")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"算子选择失败: {e}")

    def _on_inverse_method_changed(self, index: int):
        method = self.inverse_method_combo.currentData()
        self.set_inverse_method(method)

    def set_inverse_method(self, method: InverseMappingMethod):
        self.inverse_mapper.set_method(method)

        for m, action in self.inverse_method_actions.items():
            action.setChecked(m == method)

        self.inverse_method_combo.setCurrentIndex(self.inverse_method_combo.findData(method))
        self.inverse_tab_method.setCurrentIndex(self.inverse_tab_method.findData(method))

        self.statusBar.showMessage(f"逆映射方法已设置为: {method.value}")

    def set_stabilization_mode(self, mode: StabilizationMode):
        self.video_processor.set_stabilization_mode(mode)

        for m, action in self.stab_actions.items():
            action.setChecked(m == mode)

        self.video_stab_combo.setCurrentIndex(self.video_stab_combo.findData(mode))
        self.statusBar.showMessage(f"帧间稳定性已设置为: {mode.value}")

    def open_ldr_and_recover(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "打开LDR图像",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All Files (*.*)"
        )
        if filepath:
            try:
                self.statusBar.showMessage(f"正在加载: {filepath}")
                self.current_ldr_image = HDRInverseMapper.load_ldr(filepath)
                self.recover_details_btn.setEnabled(True)
                self.inverse_info_label.setText(f"已加载: {os.path.basename(filepath)}")

                preview = self.current_ldr_image
                self._display_image(self.hdr_label, preview)

                self.statusBar.showMessage(f"已加载: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载图像: {e}")

    def recover_overexposed_details(self):
        if self.current_ldr_image is None:
            QMessageBox.warning(self, "警告", "请先加载LDR图像")
            return

        try:
            self.statusBar.showMessage("正在恢复过曝细节...")

            method = self.inverse_method_combo.currentData()
            self.inverse_mapper.set_method(method)

            self.inverse_worker = InverseWorker(self.inverse_mapper, self.current_ldr_image.copy())
            self.inverse_worker.finished.connect(self._on_inverse_finished)
            self.inverse_worker.error.connect(self._on_inverse_error)
            self.inverse_worker.start()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复细节失败: {e}")

    def _on_inverse_finished(self, hdr: np.ndarray, recovered: np.ndarray):
        self.current_recovered_hdr = hdr
        self.current_hdr_image = hdr

        self._display_image(self.ldr_label, recovered)

        overexposed = np.max(self.current_ldr_image.astype(np.float32) / 255.0, axis=2) > self.inverse_mapper.saturation_threshold
        overexposed_count = np.sum(overexposed)
        total_pixels = overexposed.size

        self.inverse_info_label.setText(
            f"恢复完成!\n"
            f"过曝像素: {overexposed_count}/{total_pixels} ({overexposed_count/total_pixels:.1%})\n"
            f"HDR范围: [{hdr.min():.2f}, {hdr.max():.2f}]"
        )

        self.analyze_current_scene()
        self.apply_auto_op_btn.setEnabled(self.auto_operator_enabled)

        self.statusBar.showMessage("过曝细节恢复完成")

    def _on_inverse_error(self, error: str):
        self.statusBar.showMessage(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"逆映射失败: {error}")

    def select_hdr_video(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择HDR视频",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.mxf);;All Files (*.*)"
        )
        if filepath:
            self.video_input_path = filepath
            self.video_path_label.setText(filepath)
            self.video_path_label.setStyleSheet("color: #000;")
            self.start_video_btn.setEnabled(bool(self.video_output_dir))
            self.statusBar.showMessage(f"已选择视频: {os.path.basename(filepath)}")

    def select_video_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择视频输出目录")
        if folder:
            self.video_output_dir = folder
            self.video_output_label.setText(folder)
            self.video_output_label.setStyleSheet("color: #000;")
            self.start_video_btn.setEnabled(bool(self.video_input_path))

    def start_video_processing(self):
        if not self.video_input_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件")
            return

        if not self.video_output_dir:
            QMessageBox.warning(self, "警告", "请先选择输出目录")
            return

        stab_mode = self.video_stab_combo.currentData()
        self.video_processor.set_stabilization_mode(stab_mode)

        op_choice = self.video_op_combo.currentData()
        auto_operator = op_choice == "auto"
        fixed_operator = None if auto_operator else op_choice

        output_filename = os.path.splitext(os.path.basename(self.video_input_path))[0] + "_tonemapped.mp4"
        output_path = os.path.join(self.video_output_dir, output_filename)

        self.video_progress.setVisible(True)
        self.video_progress.setValue(0)
        self.start_video_btn.setVisible(False)
        self.cancel_video_btn.setVisible(True)
        self.video_status_label.setText("处理中...")

        self.video_worker = VideoWorker(
            self.video_processor,
            self.video_input_path,
            output_path,
            auto_operator=auto_operator,
            fixed_operator=fixed_operator
        )
        self.video_worker.progress.connect(self._on_video_progress)
        self.video_worker.finished.connect(self._on_video_finished)
        self.video_worker.error.connect(self._on_video_error)
        self.video_worker.start()

    def _on_video_progress(self, completed: int, total: int, status: str):
        self.video_progress.setMaximum(total)
        self.video_progress.setValue(completed)
        self.video_status_label.setText(status)

    def _on_video_finished(self, result: Dict[str, Any]):
        self.video_progress.setVisible(False)
        self.start_video_btn.setVisible(True)
        self.cancel_video_btn.setVisible(False)
        self.video_status_label.setText(
            f"完成! 处理了 {result['total_frames']} 帧\n"
            f"输出: {result['output_path']}"
        )
        QMessageBox.information(
            self, "处理完成",
            f"视频处理完成!\n"
            f"帧数: {result['total_frames']}\n"
            f"输出: {result['output_path']}"
        )

    def _on_video_error(self, error: str):
        self.video_progress.setVisible(False)
        self.start_video_btn.setVisible(True)
        self.cancel_video_btn.setVisible(False)
        self.video_status_label.setText(f"错误: {error}")
        QMessageBox.critical(self, "错误", f"视频处理出错: {error}")

    def cancel_video_processing(self):
        if self.video_worker is not None:
            self.video_worker.cancel()
            self.video_status_label.setText("正在取消...")

    def select_ldr_for_inverse(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择LDR图像",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff);;All Files (*.*)"
        )
        if filepath:
            try:
                self.ldr_for_inverse = HDRInverseMapper.load_ldr(filepath)
                self.inverse_file_label.setText(filepath)
                self.inverse_file_label.setStyleSheet("color: #000;")
                self.start_inverse_btn.setEnabled(True)
                self.statusBar.showMessage(f"已加载: {os.path.basename(filepath)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载图像: {e}")

    def execute_inverse_mapping(self):
        if self.ldr_for_inverse is None:
            QMessageBox.warning(self, "警告", "请先选择LDR图像")
            return

        try:
            self.statusBar.showMessage("正在执行逆映射...")
            self.inverse_progress.setVisible(True)
            self.inverse_progress.setValue(50)

            method = self.inverse_tab_method.currentData()
            gamma = self.inverse_gamma_spin.value()
            max_bright = self.inverse_max_bright_spin.value()

            self.inverse_mapper.set_method(method)
            self.inverse_mapper.set_params(gamma=gamma, max_brightness=max_bright)

            self.inverse_result_hdr = self.inverse_mapper.map(self.ldr_for_inverse)

            self.inverse_progress.setValue(100)
            self.inverse_progress.setVisible(False)
            self.save_inverse_btn.setEnabled(True)

            self.inverse_status_label.setText(
                f"逆映射完成!\n"
                f"方法: {method.value}\n"
                f"HDR范围: [{self.inverse_result_hdr.min():.2f}, {self.inverse_result_hdr.max():.2f}]"
            )

            self.current_hdr_image = self.inverse_result_hdr
            preview = np.clip(self.inverse_result_hdr * 255.0 / max_bright, 0, 255).astype(np.uint8)
            self._display_image(self.hdr_label, preview)

            self.analyze_current_scene()
            self.statusBar.showMessage("逆映射完成")
        except Exception as e:
            self.inverse_progress.setVisible(False)
            QMessageBox.critical(self, "错误", f"逆映射失败: {e}")

    def save_inverse_result(self):
        if self.inverse_result_hdr is None:
            QMessageBox.warning(self, "警告", "没有可保存的HDR结果")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "保存HDR图像",
            "",
            "HDR Images (*.hdr *.exr *.tif *.tiff);;All Files (*.*)"
        )
        if filepath:
            try:
                HDRInverseMapper.save_hdr(filepath, self.inverse_result_hdr)
                self.statusBar.showMessage(f"已保存到: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存: {e}")

    def process_hdr_video(self):
        self.batch_tabs.setCurrentIndex(2)

    def _on_operator_changed(self, index: int):
        self.current_operator = self.op_combo.currentData()
        self._update_param_panel()
        self._refresh_preset_combo()

        if self.auto_operator_enabled and self.current_scene_features is not None:
            pass
        else:
            self._schedule_preview()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 HDR Tone Mapping Tool Ultimate",
            "HDR 色调映射实时调优工具 终极版\n\n"
            "支持的色调映射算子:\n"
            "  - Reinhard\n"
            "  - Filmic\n"
            "  - ACES (含饱和度控制)\n\n"
            "核心功能:\n"
            "  - 自适应算子选择 (按图像特征自动选最优)\n"
            "  - HDR视频色调映射 (帧间稳定性)\n"
            "  - LDR→HDR逆映射 (恢复过曝区域细节)\n"
            "  - 异步计算+防抖+松手触发\n"
            "  - 智能场景分析分类\n"
            "  - 按场景独立参数批量处理\n"
            "  - GPU加速 (CUDA)\n"
            "  - 参数预设管理\n\n"
            "使用 OpenCV + PyQt 构建"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_hdr_image is not None:
            preview = np.clip(self.current_hdr_image * 255.0, 0, 255).astype(np.uint8)
            self._display_image(self.hdr_label, preview)
        if self.current_preview is not None:
            self._display_image(self.ldr_label, self.current_preview)


class BatchWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, processor: BatchProcessor, files: list, output_dir: str,
                 op: ToneMappingOperator, output_format: str):
        super().__init__()
        self.processor = processor
        self.files = files
        self.output_dir = output_dir
        self.op = op
        self.output_format = output_format

    def run(self):
        try:
            results = self.processor.process_batch(
                self.files,
                self.output_dir,
                self.op,
                self.output_format,
                lambda c, t, s: self.progress.emit(c, t, s)
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
