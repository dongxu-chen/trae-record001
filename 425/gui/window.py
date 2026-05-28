import os
import sys
import numpy as np
import cv2

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QFileDialog, QGroupBox, QVBoxLayout,
    QHBoxLayout, QGridLayout, QSplitter, QTextEdit, QProgressBar, QTabWidget,
    QSlider, QMessageBox, QSizePolicy, QScrollArea, QFrame, QDesktopWidget,
)

from binarization.core import binarize_pipeline, sauvola_threshold, niblack_threshold
from binarization.batch import batch_binarize, collect_images
from binarization.ocr_eval import evaluate_binarization, ocr_confidence, TESSERACT_AVAILABLE
from binarization.noise_detection import detect_noise_type
from binarization.dl_binarization import (
    dbnet_binarize,
    binarize_with_fusion,
    BinarizationFusion,
    fuse_binarization_results,
    DBNET_AVAILABLE,
)
from binarization.color import (
    binarize_color_channel,
    binarize_color_multi_channel,
    binarize_color_by_clustering,
    preserve_colored_text,
)


def numpy_to_qimage(arr: np.ndarray) -> QImage:
    if arr.ndim == 2:
        h, w = arr.shape
        bytes_per_line = w
        q_img = QImage(arr.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        return q_img.copy()
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return q_img.copy()


def numpy_to_qpixmap(arr: np.ndarray, max_size: int = 600) -> QPixmap:
    q_img = numpy_to_qimage(arr)
    pixmap = QPixmap.fromImage(q_img)
    if pixmap.width() > max_size or pixmap.height() > max_size:
        pixmap = pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap


class BatchWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)

    def __init__(self, input_dir: str, output_dir: str, params: dict):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.params = params

    def run(self):
        def on_progress(current: int, total: int, msg: str):
            self.progress.emit(current, total, msg)
        results = batch_binarize(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            progress_callback=on_progress,
            **self.params,
        )
        self.finished.emit(results)


class ImagePreviewWidget(QLabel):
    clicked = pyqtSignal()

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        self.setText(f"<h2 style='color:#888;'>{self.title}</h2>")
        self._pixmap = None
        self._image_data = None

    def set_image(self, arr: np.ndarray):
        self._image_data = arr
        self._pixmap = numpy_to_qpixmap(arr, max_size=800)
        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)

    def resizeEvent(self, event):
        if self._pixmap:
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class BinarizationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文档图像二值化工具")
        self.current_image = None
        self.current_binary = None
        self.current_image_path = None
        self.batch_worker = None
        self.image_dpi = 96
        self.base_font_size = 13
        self.noise_detection_result = None
        self._calculate_window_size()
        self._init_ui()
        self._apply_styles()

    def _calculate_window_size(self):
        desk = QDesktopWidget().availableGeometry()
        screen_w = desk.width()
        screen_h = desk.height()

        app = QApplication.instance()
        if app:
            font = app.font()
            fm = QFontMetrics(font)
            self.base_font_size = fm.height()

        base_w = min(1400, int(screen_w * 0.9))
        base_h = min(900, int(screen_h * 0.85))

        scale_factor = self.base_font_size / 13.0
        final_w = int(base_w * min(scale_factor, 1.3))
        final_h = int(base_h * min(scale_factor, 1.3))

        x = (screen_w - final_w) // 2
        y = (screen_h - final_h) // 2
        self.setGeometry(x, y, final_w, final_h)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        method_group = QGroupBox("二值化方法")
        method_layout = QGridLayout(method_group)
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Sauvola", "Niblack", "Otsu", "Adaptive",
            "DBNet (传统模拟)", "DBNet (深度学习)", "多方法融合",
            "彩色-通道二值化", "彩色-多通道融合", "彩色-聚类",
        ])
        self.method_combo.setCurrentIndex(0)
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_layout.addWidget(QLabel("方法:"), 0, 0)
        method_layout.addWidget(self.method_combo, 0, 1)

        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(3, 101)
        self.window_size_spin.setValue(15)
        self.window_size_spin.setSingleStep(2)
        method_layout.addWidget(QLabel("窗口大小:"), 1, 0)
        method_layout.addWidget(self.window_size_spin, 1, 1)

        self.k_spin = QDoubleSpinBox()
        self.k_spin.setRange(-1.0, 1.0)
        self.k_spin.setValue(0.2)
        self.k_spin.setSingleStep(0.05)
        self.k_spin.setDecimals(3)
        method_layout.addWidget(QLabel("k 值:"), 2, 0)
        method_layout.addWidget(self.k_spin, 2, 1)

        self.r_spin = QDoubleSpinBox()
        self.r_spin.setRange(1.0, 255.0)
        self.r_spin.setValue(128.0)
        self.r_spin.setSingleStep(1.0)
        method_layout.addWidget(QLabel("R 值:"), 3, 0)
        method_layout.addWidget(self.r_spin, 3, 1)

        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(3, 101)
        self.block_size_spin.setValue(11)
        self.block_size_spin.setSingleStep(2)
        self.block_size_spin.setEnabled(False)
        method_layout.addWidget(QLabel("Block 大小:"), 4, 0)
        method_layout.addWidget(self.block_size_spin, 4, 1)

        self.c_spin = QSpinBox()
        self.c_spin.setRange(-20, 20)
        self.c_spin.setValue(2)
        self.c_spin.setEnabled(False)
        method_layout.addWidget(QLabel("C 值:"), 5, 0)
        method_layout.addWidget(self.c_spin, 5, 1)

        self.color_channel_combo = QComboBox()
        self.color_channel_combo.addItems(["l", "r", "g", "b", "gray", "saturation"])
        self.color_channel_combo.setCurrentIndex(0)
        self.color_channel_combo.setEnabled(False)
        method_layout.addWidget(QLabel("彩色通道:"), 6, 0)
        method_layout.addWidget(self.color_channel_combo, 6, 1)

        self.color_preserve_check = QCheckBox("保留颜色信息")
        self.color_preserve_check.setChecked(True)
        self.color_preserve_check.setEnabled(False)
        method_layout.addWidget(self.color_preserve_check, 7, 0, 1, 2)

        self.color_combo_combo = QComboBox()
        self.color_combo_combo.addItems(["intersection", "union", "majority", "l_weighted"])
        self.color_combo_combo.setCurrentIndex(0)
        self.color_combo_combo.setEnabled(False)
        method_layout.addWidget(QLabel("多通道组合:"), 8, 0)
        method_layout.addWidget(self.color_combo_combo, 8, 1)

        self.fusion_method_combo = QComboBox()
        self.fusion_method_combo.addItems([
            "weighted", "intersection", "union", "majority_vote",
            "dl_with_traditional_refine", "traditional_with_dl_refine", "confidence_based"
        ])
        self.fusion_method_combo.setCurrentIndex(0)
        self.fusion_method_combo.setEnabled(False)
        method_layout.addWidget(QLabel("融合方式:"), 9, 0)
        method_layout.addWidget(self.fusion_method_combo, 9, 1)

        self.dbnet_shrink_spin = QDoubleSpinBox()
        self.dbnet_shrink_spin.setRange(0.1, 1.0)
        self.dbnet_shrink_spin.setValue(0.6)
        self.dbnet_shrink_spin.setSingleStep(0.1)
        self.dbnet_shrink_spin.setEnabled(False)
        method_layout.addWidget(QLabel("DBNet收缩率:"), 10, 0)
        method_layout.addWidget(self.dbnet_shrink_spin, 10, 1)

        self.dbnet_thresh_spin = QDoubleSpinBox()
        self.dbnet_thresh_spin.setRange(0.05, 0.95)
        self.dbnet_thresh_spin.setValue(0.3)
        self.dbnet_thresh_spin.setSingleStep(0.05)
        self.dbnet_thresh_spin.setEnabled(False)
        method_layout.addWidget(QLabel("DBNet阈值:"), 11, 0)
        method_layout.addWidget(self.dbnet_thresh_spin, 11, 1)

        left_layout.addWidget(method_group)

        preprocess_group = QGroupBox("预处理")
        pre_layout = QGridLayout(preprocess_group)

        self.denoise_check = QCheckBox("启用去噪")
        self.denoise_check.setChecked(True)
        pre_layout.addWidget(self.denoise_check, 0, 0, 1, 2)

        self.denoise_combo = QComboBox()
        self.denoise_combo.addItems(["wavelet", "bilateral", "gaussian", "median"])
        self.denoise_combo.setCurrentIndex(0)
        pre_layout.addWidget(QLabel("去噪方式:"), 1, 0)
        pre_layout.addWidget(self.denoise_combo, 1, 1)

        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["none", "morph", "poly"])
        self.bg_combo.setCurrentIndex(0)
        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)
        pre_layout.addWidget(QLabel("背景估计:"), 2, 0)
        pre_layout.addWidget(self.bg_combo, 2, 1)

        self.bg_kernel_spin = QSpinBox()
        self.bg_kernel_spin.setRange(5, 201)
        self.bg_kernel_spin.setValue(51)
        self.bg_kernel_spin.setSingleStep(2)
        self.bg_kernel_spin.setEnabled(False)
        pre_layout.addWidget(QLabel("背景核大小:"), 3, 0)
        pre_layout.addWidget(self.bg_kernel_spin, 3, 1)

        self.bg_degree_spin = QSpinBox()
        self.bg_degree_spin.setRange(1, 3)
        self.bg_degree_spin.setValue(2)
        self.bg_degree_spin.setEnabled(False)
        pre_layout.addWidget(QLabel("多项式阶数:"), 4, 0)
        pre_layout.addWidget(self.bg_degree_spin, 4, 1)

        self.bg_texture_check = QCheckBox("启用纹理抑制")
        self.bg_texture_check.setChecked(True)
        self.bg_texture_check.setEnabled(False)
        self.bg_texture_check.stateChanged.connect(self._on_bg_changed)
        pre_layout.addWidget(self.bg_texture_check, 5, 0, 1, 2)

        self.bg_texture_method_combo = QComboBox()
        self.bg_texture_method_combo.addItems(["median", "gaussian", "bilateral", "morph", "wavelet"])
        self.bg_texture_method_combo.setCurrentIndex(0)
        self.bg_texture_method_combo.setEnabled(False)
        pre_layout.addWidget(QLabel("纹理抑制方式:"), 6, 0)
        pre_layout.addWidget(self.bg_texture_method_combo, 6, 1)

        self.bg_texture_kernel_spin = QSpinBox()
        self.bg_texture_kernel_spin.setRange(3, 31)
        self.bg_texture_kernel_spin.setValue(7)
        self.bg_texture_kernel_spin.setSingleStep(2)
        self.bg_texture_kernel_spin.setEnabled(False)
        pre_layout.addWidget(QLabel("纹理核大小:"), 7, 0)
        pre_layout.addWidget(self.bg_texture_kernel_spin, 7, 1)

        self.bg_smooth_spin = QDoubleSpinBox()
        self.bg_smooth_spin.setRange(0.0, 10.0)
        self.bg_smooth_spin.setValue(3.0)
        self.bg_smooth_spin.setSingleStep(0.5)
        self.bg_smooth_spin.setDecimals(1)
        self.bg_smooth_spin.setEnabled(False)
        pre_layout.addWidget(QLabel("背景平滑σ:"), 8, 0)
        pre_layout.addWidget(self.bg_smooth_spin, 8, 1)

        self.bg_downsample_spin = QSpinBox()
        self.bg_downsample_spin.setRange(1, 8)
        self.bg_downsample_spin.setValue(4)
        self.bg_downsample_spin.setEnabled(False)
        pre_layout.addWidget(QLabel("降采样系数:"), 9, 0)
        pre_layout.addWidget(self.bg_downsample_spin, 9, 1)

        left_layout.addWidget(preprocess_group)

        noise_group = QGroupBox("噪声检测与推荐")
        noise_layout = QGridLayout(noise_group)

        self.detect_noise_btn = QPushButton("检测噪声类型")
        self.detect_noise_btn.clicked.connect(self._detect_noise)
        noise_layout.addWidget(self.detect_noise_btn, 0, 0, 1, 2)

        self.noise_result_label = QLabel("未检测")
        self.noise_result_label.setWordWrap(True)
        self.noise_result_label.setStyleSheet("color: #90caf9;")
        noise_layout.addWidget(self.noise_result_label, 1, 0, 1, 2)

        self.apply_recommended_btn = QPushButton("应用推荐参数")
        self.apply_recommended_btn.clicked.connect(self._apply_recommended_params)
        self.apply_recommended_btn.setEnabled(False)
        noise_layout.addWidget(self.apply_recommended_btn, 2, 0, 1, 2)

        self.auto_noise_check = QCheckBox("处理时自动检测并选择最佳方法")
        self.auto_noise_check.setChecked(False)
        noise_layout.addWidget(self.auto_noise_check, 3, 0, 1, 2)

        left_layout.addWidget(noise_group)

        postprocess_group = QGroupBox("后处理")
        post_layout = QGridLayout(postprocess_group)

        self.postprocess_check = QCheckBox("启用形态学后处理")
        self.postprocess_check.setChecked(True)
        post_layout.addWidget(self.postprocess_check, 0, 0, 1, 2)

        self.morph_kernel_spin = QSpinBox()
        self.morph_kernel_spin.setRange(0, 10)
        self.morph_kernel_spin.setValue(1)
        post_layout.addWidget(QLabel("形态学核:"), 1, 0)
        post_layout.addWidget(self.morph_kernel_spin, 1, 1)

        left_layout.addWidget(postprocess_group)

        action_group = QGroupBox("操作")
        action_layout = QGridLayout(action_group)

        self.load_btn = QPushButton("加载图像")
        self.load_btn.clicked.connect(self._load_image)
        action_layout.addWidget(self.load_btn, 0, 0)

        self.process_btn = QPushButton("处理当前图像")
        self.process_btn.clicked.connect(self._process_current)
        action_layout.addWidget(self.process_btn, 0, 1)

        self.save_btn = QPushButton("保存二值图")
        self.save_btn.clicked.connect(self._save_binary)
        action_layout.addWidget(self.save_btn, 1, 0)

        self.compare_btn = QPushButton("并排对比")
        self.compare_btn.clicked.connect(self._compare_view)
        action_layout.addWidget(self.compare_btn, 1, 1)

        left_layout.addWidget(action_group)

        left_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_panel)
        scroll.setFixedWidth(380)
        main_layout.addWidget(scroll)

        right_panel = QTabWidget()

        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_splitter = QSplitter(Qt.Horizontal)

        self.orig_preview = ImagePreviewWidget("原始图像")
        self.bin_preview = ImagePreviewWidget("二值化结果")

        preview_splitter.addWidget(self.orig_preview)
        preview_splitter.addWidget(self.bin_preview)
        preview_splitter.setSizes([500, 500])
        preview_layout.addWidget(preview_splitter)

        right_panel.addTab(preview_tab, "图像预览")

        batch_tab = QWidget()
        batch_layout = QVBoxLayout(batch_tab)

        batch_dir_layout = QHBoxLayout()
        batch_dir_layout.addWidget(QLabel("输入目录:"))
        self.batch_input_edit = QLabel("未选择")
        self.batch_input_edit.setStyleSheet("color: #bbb;")
        self.batch_input_edit.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.batch_input_edit.setMinimumWidth(200)
        batch_dir_layout.addWidget(self.batch_input_edit)
        self.batch_input_btn = QPushButton("选择...")
        self.batch_input_btn.clicked.connect(self._select_batch_input)
        batch_dir_layout.addWidget(self.batch_input_btn)
        batch_layout.addLayout(batch_dir_layout)

        batch_out_layout = QHBoxLayout()
        batch_out_layout.addWidget(QLabel("输出目录:"))
        self.batch_output_edit = QLabel("未选择")
        self.batch_output_edit.setStyleSheet("color: #bbb;")
        self.batch_output_edit.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.batch_output_edit.setMinimumWidth(200)
        batch_out_layout.addWidget(self.batch_output_edit)
        self.batch_output_btn = QPushButton("选择...")
        self.batch_output_btn.clicked.connect(self._select_batch_output)
        batch_out_layout.addWidget(self.batch_output_btn)
        batch_layout.addLayout(batch_out_layout)

        batch_opt_layout = QHBoxLayout()
        batch_opt_layout.addWidget(QLabel("输出格式:"))
        self.batch_fmt_combo = QComboBox()
        self.batch_fmt_combo.addItems([".png", ".jpg", ".bmp", ".tif"])
        self.batch_fmt_combo.setCurrentIndex(0)
        batch_opt_layout.addWidget(self.batch_fmt_combo)
        batch_opt_layout.addWidget(QLabel("文件名前缀:"))
        self.batch_prefix_edit = QLabel("bin_")
        self.batch_prefix_edit.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.batch_prefix_edit.setMinimumWidth(80)
        batch_opt_layout.addWidget(self.batch_prefix_edit)
        batch_layout.addLayout(batch_opt_layout)

        self.batch_run_btn = QPushButton("开始批量处理")
        self.batch_run_btn.clicked.connect(self._run_batch)
        batch_layout.addWidget(self.batch_run_btn)

        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        batch_layout.addWidget(self.batch_progress)

        self.batch_log = QTextEdit()
        self.batch_log.setReadOnly(True)
        self.batch_log.setMinimumHeight(200)
        batch_layout.addWidget(self.batch_log)

        right_panel.addTab(batch_tab, "批量处理")

        ocr_tab = QWidget()
        ocr_layout = QVBoxLayout(ocr_tab)

        ocr_opt_layout = QGridLayout()
        ocr_opt_layout.addWidget(QLabel("OCR 语言:"), 0, 0)
        self.ocr_lang_combo = QComboBox()
        self.ocr_lang_combo.addItems(["eng", "chi_sim", "chi_tra", "eng+chi_sim"])
        self.ocr_lang_combo.setCurrentIndex(0)
        ocr_opt_layout.addWidget(self.ocr_lang_combo, 0, 1)

        ocr_opt_layout.addWidget(QLabel("PSM 模式:"), 1, 0)
        self.ocr_psm_combo = QComboBox()
        self.ocr_psm_combo.addItems([str(i) for i in range(14)])
        self.ocr_psm_combo.setCurrentIndex(6)
        ocr_opt_layout.addWidget(self.ocr_psm_combo, 1, 1)

        ocr_opt_layout.addWidget(QLabel("参考文本 (可选):"), 2, 0)
        self.ocr_ref_edit = QTextEdit()
        self.ocr_ref_edit.setPlaceholderText("输入参考文本以计算字符准确率...")
        self.ocr_ref_edit.setMaximumHeight(60)
        ocr_opt_layout.addWidget(self.ocr_ref_edit, 2, 1, 1, 2)

        ocr_layout.addLayout(ocr_opt_layout)

        self.ocr_evaluate_btn = QPushButton("评估 OCR 准确率提升")
        self.ocr_evaluate_btn.clicked.connect(self._evaluate_ocr)
        ocr_layout.addWidget(self.ocr_evaluate_btn)

        self.ocr_result_text = QTextEdit()
        self.ocr_result_text.setReadOnly(True)
        ocr_layout.addWidget(self.ocr_result_text)

        right_panel.addTab(ocr_tab, "OCR 评估")

        main_layout.addWidget(right_panel, 1)

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; font-size: 13px; }
            QGroupBox { border: 1px solid #444; border-radius: 6px; margin-top: 12px;
                         padding-top: 16px; font-weight: bold; color: #e0e0e0; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #4fc3f7; }
            QPushButton { background-color: #0d47a1; border: none; border-radius: 4px;
                          padding: 8px 16px; color: white; font-weight: bold; }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:pressed { background-color: #0a3380; }
            QPushButton:disabled { background-color: #555; color: #888; }
            QComboBox { background-color: #2b2b2b; border: 1px solid #555; border-radius: 4px;
                        padding: 5px 10px; color: #e0e0e0; }
            QComboBox:hover { border-color: #4fc3f7; }
            QComboBox::drop-down { width: 20px; }
            QComboBox QAbstractItemView { background-color: #2b2b2b; border: 1px solid #555;
                                           selection-background-color: #1565c0; }
            QSpinBox, QDoubleSpinBox { background-color: #2b2b2b; border: 1px solid #555;
                                       border-radius: 4px; padding: 4px; color: #e0e0e0; }
            QSpinBox:focus, QDoubleSpinBox:focus { border-color: #4fc3f7; }
            QCheckBox { color: #e0e0e0; }
            QProgressBar { border: 1px solid #555; border-radius: 4px; text-align: center;
                           background-color: #2b2b2b; color: #e0e0e0; }
            QProgressBar::chunk { background-color: #4fc3f7; border-radius: 3px; }
            QTextEdit { background-color: #2b2b2b; border: 1px solid #555; border-radius: 4px;
                        color: #e0e0e0; }
            QTabWidget::pane { border: 1px solid #444; border-radius: 6px; }
            QTabBar::tab { background-color: #2b2b2b; border: 1px solid #444; border-bottom: none;
                           border-top-left-radius: 6px; border-top-right-radius: 6px;
                           padding: 8px 20px; color: #e0e0e0; }
            QTabBar::tab:selected { background-color: #1565c0; color: white; }
            QTabBar::tab:hover:!selected { background-color: #388e3c; }
            QScrollArea { border: none; background-color: #1e1e1e; }
            QLabel { color: #e0e0e0; }
            QSplitter::handle { background-color: #444; }
        """)

    def _on_method_changed(self, idx: int):
        method = self.method_combo.currentText()
        is_adaptive = method == "Adaptive"
        is_global = method == "Otsu"
        is_dbnet_trad = method == "DBNet (传统模拟)"
        is_dbnet_dl = method == "DBNet (深度学习)"
        is_fusion = method == "多方法融合"
        is_color_channel = method == "彩色-通道二值化"
        is_color_multi = method == "彩色-多通道融合"
        is_color_cluster = method == "彩色-聚类"
        is_color = is_color_channel or is_color_multi or is_color_cluster

        self.window_size_spin.setEnabled(not is_adaptive and not is_global and not is_dbnet_trad and not is_dbnet_dl and not is_color_cluster)
        self.k_spin.setEnabled(not is_adaptive and not is_global and not is_dbnet_trad and not is_dbnet_dl and not is_color_cluster)
        self.r_spin.setEnabled(method == "Sauvola")
        self.block_size_spin.setEnabled(is_adaptive)
        self.c_spin.setEnabled(is_adaptive)

        self.color_channel_combo.setEnabled(is_color_channel)
        self.color_preserve_check.setEnabled(is_color)
        self.color_combo_combo.setEnabled(is_color_multi)

        self.fusion_method_combo.setEnabled(is_fusion or is_dbnet_dl)
        self.dbnet_shrink_spin.setEnabled(is_dbnet_trad or is_dbnet_dl)
        self.dbnet_thresh_spin.setEnabled(is_dbnet_trad or is_dbnet_dl)

    def _on_bg_changed(self, idx: int):
        bg_type = self.bg_combo.currentText()
        bg_enabled = bg_type != "none"
        self.bg_kernel_spin.setEnabled(bg_type == "morph")
        self.bg_degree_spin.setEnabled(bg_type == "poly")
        self.bg_texture_check.setEnabled(bg_enabled)
        self.bg_texture_method_combo.setEnabled(bg_enabled and self.bg_texture_check.isChecked())
        self.bg_texture_kernel_spin.setEnabled(bg_enabled and self.bg_texture_check.isChecked())
        self.bg_smooth_spin.setEnabled(bg_type == "morph")
        self.bg_downsample_spin.setEnabled(bg_type == "poly")

    def _detect_noise(self):
        if self.current_image is None:
            QMessageBox.warning(self, "提示", "请先加载一张图像！")
            return

        try:
            self.noise_result_label.setText("正在检测噪声...")
            QApplication.processEvents()

            self.noise_detection_result = detect_noise_type(self.current_image)

            noise_scores = self.noise_detection_result.get("noise_scores", {})
            primary = self.noise_detection_result.get("primary_noise", "unknown")
            recommended_method = self.noise_detection_result.get("recommended_method", "sauvola")
            recommended_params = self.noise_detection_result.get("recommended_params", {})

            noise_text = f"主噪声类型: <b>{primary}</b><br>"
            noise_text += f"推荐方法: <b>{recommended_method}</b><br><br>"
            noise_text += "各噪声评分:<br>"
            for noise_type in ["illumination_uneven", "gaussian", "salt_pepper", "poisson", "periodic", "blur", "jpeg_compression"]:
                score = noise_scores.get(noise_type, 0)
                bar = "█" * int(score * 20)
                noise_text += f"{noise_type}: {score:.2f} {bar}<br>"

            self.noise_result_label.setText(noise_text)
            self.apply_recommended_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"噪声检测失败: {str(e)}")

    def _apply_recommended_params(self):
        if self.noise_detection_result is None:
            QMessageBox.warning(self, "提示", "请先检测噪声类型！")
            return

        try:
            recommended_method = self.noise_detection_result.get("recommended_method", "sauvola")
            recommended_params = self.noise_detection_result.get("recommended_params", {})

            method_map = {
                "sauvola": "Sauvola",
                "niblack": "Niblack",
                "otsu": "Otsu",
                "adaptive": "Adaptive",
            }
            if recommended_method in method_map:
                idx = self.method_combo.findText(method_map[recommended_method])
                if idx >= 0:
                    self.method_combo.setCurrentIndex(idx)

            if "window_size" in recommended_params:
                self.window_size_spin.setValue(recommended_params["window_size"])
            if "k" in recommended_params:
                self.k_spin.setValue(recommended_params["k"])
            if "block_size" in recommended_params:
                self.block_size_spin.setValue(recommended_params["block_size"])
            if "C" in recommended_params:
                self.c_spin.setValue(recommended_params["C"])
            if "denoise" in recommended_params:
                self.denoise_check.setChecked(recommended_params["denoise"])
            if "denoise_method" in recommended_params:
                idx = self.denoise_combo.findText(recommended_params["denoise_method"])
                if idx >= 0:
                    self.denoise_combo.setCurrentIndex(idx)
            if "bg_estimation" in recommended_params:
                idx = self.bg_combo.findText(recommended_params["bg_estimation"])
                if idx >= 0:
                    self.bg_combo.setCurrentIndex(idx)
            if "post_process" in recommended_params:
                self.postprocess_check.setChecked(recommended_params["post_process"])
            if "morph_kernel" in recommended_params:
                self.morph_kernel_spin.setValue(recommended_params["morph_kernel"])

            QMessageBox.information(self, "成功", "已应用推荐参数")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用参数失败: {str(e)}")

    def _load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文档图像", "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.pgm *.ppm)"
        )
        if not file_path:
            return
        try:
            img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if img is None:
                QMessageBox.warning(self, "错误", "无法读取图像文件！")
                return
            self.current_image = img
            self.current_image_path = file_path

            try:
                from PIL import Image
                with Image.open(file_path) as pil_img:
                    dpi_info = pil_img.info.get('dpi', (96, 96))
                    self.image_dpi = int(sum(dpi_info) / 2)
            except (ImportError, Exception):
                self.image_dpi = 96

            self._adjust_window_for_image(img.shape[1], img.shape[0])
            self.orig_preview.set_image(img)
            self.bin_preview.setText("<h2 style='color:#888;'>二值化结果</h2>")
            self.bin_preview._pixmap = None
            self.bin_preview._image_data = None
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载图像失败: {str(e)}")

    def _adjust_window_for_image(self, img_w: int, img_h: int):
        desk = QDesktopWidget().availableGeometry()
        screen_w = desk.width()
        screen_h = desk.height()

        max_img_w = int(screen_w * 0.45)
        max_img_h = int(screen_h * 0.6)

        scale = min(max_img_w / img_w, max_img_h / img_h, 1.0)

        base_panel_w = 380
        min_w = base_panel_w + int(img_w * scale * 2) + 40
        min_h = int(img_h * scale) + 200

        current_w = max(self.width(), min_w)
        current_h = max(self.height(), min_h)

        final_w = min(current_w, int(screen_w * 0.95))
        final_h = min(current_h, int(screen_h * 0.9))

        x = max(desk.x() + (screen_w - final_w) // 2, 0)
        y = max(desk.y() + (screen_h - final_h) // 2, 0)
        self.setGeometry(x, y, final_w, final_h)

    def _get_params(self) -> dict:
        method = self.method_combo.currentText().lower()
        return {
            "method": method,
            "denoise": self.denoise_check.isChecked(),
            "denoise_method": self.denoise_combo.currentText(),
            "bg_estimation": self.bg_combo.currentText(),
            "bg_kernel_size": self.bg_kernel_spin.value(),
            "bg_degree": self.bg_degree_spin.value(),
            "bg_texture_suppress": self.bg_texture_check.isChecked(),
            "bg_texture_kernel": self.bg_texture_kernel_spin.value(),
            "bg_texture_method": self.bg_texture_method_combo.currentText(),
            "bg_smooth_sigma": self.bg_smooth_spin.value(),
            "bg_downsample": self.bg_downsample_spin.value(),
            "window_size": self.window_size_spin.value(),
            "k": self.k_spin.value(),
            "r": self.r_spin.value(),
            "block_size": self.block_size_spin.value(),
            "C": self.c_spin.value(),
            "post_process": self.postprocess_check.isChecked(),
            "morph_kernel": self.morph_kernel_spin.value(),
        }

    def _process_current(self):
        if self.current_image is None:
            QMessageBox.warning(self, "提示", "请先加载一张图像！")
            return
        try:
            method = self.method_combo.currentText()
            params = self._get_params()

            if self.auto_noise_check.isChecked():
                if self.noise_detection_result is None:
                    self.noise_detection_result = detect_noise_type(self.current_image)

            binary = None

            if method == "DBNet (传统模拟)":
                from binarization.dl_binarization import DBNetTraditional
                dbnet = DBNetTraditional(
                    shrink_ratio=self.dbnet_shrink_spin.value(),
                    threshold=self.dbnet_thresh_spin.value(),
                    adaptive=True,
                )
                binary, _ = dbnet(self.current_image)

            elif method == "DBNet (深度学习)":
                binary, prob_map = dbnet_binarize(
                    self.current_image,
                    use_traditional_fallback=True,
                )

            elif method == "多方法融合":
                noise_result = self.noise_detection_result or detect_noise_type(self.current_image)
                binary = binarize_with_fusion(
                    self.current_image,
                    noise_result,
                    use_dl=DBNET_AVAILABLE,
                    fusion_method=self.fusion_method_combo.currentText(),
                )

            elif method == "彩色-通道二值化":
                if self.current_image.ndim != 3:
                    QMessageBox.warning(self, "提示", "请加载彩色图像以使用彩色二值化方法！")
                    return
                binary = binarize_color_channel(
                    self.current_image,
                    method=params["method"],
                    channel=self.color_channel_combo.currentText(),
                    preserve_color=self.color_preserve_check.isChecked(),
                    window_size=params["window_size"],
                    k=params["k"],
                    r=params["r"],
                    block_size=params["block_size"],
                    C=params["C"],
                )

            elif method == "彩色-多通道融合":
                if self.current_image.ndim != 3:
                    QMessageBox.warning(self, "提示", "请加载彩色图像以使用彩色二值化方法！")
                    return
                binary = binarize_color_multi_channel(
                    self.current_image,
                    method=params["method"],
                    combination=self.color_combo_combo.currentText(),
                    preserve_color=self.color_preserve_check.isChecked(),
                    window_size=params["window_size"],
                    k=params["k"],
                    r=params["r"],
                    block_size=params["block_size"],
                    C=params["C"],
                )

            elif method == "彩色-聚类":
                if self.current_image.ndim != 3:
                    QMessageBox.warning(self, "提示", "请加载彩色图像以使用彩色二值化方法！")
                    return
                binary = binarize_color_by_clustering(
                    self.current_image,
                    num_clusters=3,
                    preserve_color=self.color_preserve_check.isChecked(),
                )

            else:
                binary = binarize_pipeline(self.current_image, **params)

            self.current_binary = binary
            self.bin_preview.set_image(binary)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理失败: {str(e)}")

    def _save_binary(self):
        if self.current_binary is None:
            QMessageBox.warning(self, "提示", "没有可保存的二值化结果！")
            return
        default_name = "binary.png"
        if self.current_image_path:
            base = os.path.splitext(os.path.basename(self.current_image_path))[0]
            default_name = f"bin_{base}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存二值化图像", default_name,
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;BMP 图像 (*.bmp);;TIFF 图像 (*.tif)"
        )
        if not file_path:
            return
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cv2.imencode(ext, self.current_binary, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tofile(file_path)
            else:
                cv2.imencode(ext, self.current_binary)[1].tofile(file_path)
            QMessageBox.information(self, "成功", f"图像已保存到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def _compare_view(self):
        if self.current_image is None or self.current_binary is None:
            QMessageBox.warning(self, "提示", "请先加载并处理图像！")
            return

        from PyQt5.QtWidgets import QDialog

        dialog = QDialog(self)
        dialog.setWindowTitle("并排对比 - 原始 vs 二值化")
        dialog.setMinimumSize(1200, 700)

        orig_pix = numpy_to_qpixmap(self.current_image, max_size=550)
        bin_pix = numpy_to_qpixmap(self.current_binary, max_size=550)

        layout = QVBoxLayout(dialog)

        label_row = QHBoxLayout()
        orig_label = QLabel("原始图像")
        orig_label.setAlignment(Qt.AlignCenter)
        orig_label.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 14px;")
        bin_label = QLabel("二值化结果")
        bin_label.setAlignment(Qt.AlignCenter)
        bin_label.setStyleSheet("color: #4fc3f7; font-weight: bold; font-size: 14px;")
        label_row.addWidget(orig_label)
        label_row.addWidget(bin_label)

        img_row = QHBoxLayout()
        left = QLabel()
        left.setAlignment(Qt.AlignCenter)
        left.setPixmap(orig_pix)
        left.setStyleSheet("border: 2px solid #4fc3f7; padding: 4px;")
        right = QLabel()
        right.setAlignment(Qt.AlignCenter)
        right.setPixmap(bin_pix)
        right.setStyleSheet("border: 2px solid #4fc3f7; padding: 4px;")
        img_row.addWidget(left)
        img_row.addWidget(right)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addStretch()

        layout.addLayout(label_row)
        layout.addLayout(img_row)
        layout.addLayout(btn_row)

        dialog.exec_()

    def _select_batch_input(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if dir_path:
            self.batch_input_edit.setText(dir_path)

    def _select_batch_output(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.batch_output_edit.setText(dir_path)

    def _run_batch(self):
        input_dir = self.batch_input_edit.text()
        output_dir = self.batch_output_edit.text()
        if input_dir == "未选择" or not os.path.isdir(input_dir):
            QMessageBox.warning(self, "提示", "请选择有效的输入目录！")
            return
        if output_dir == "未选择" or not output_dir:
            QMessageBox.warning(self, "提示", "请选择有效的输出目录！")
            return

        images = collect_images(input_dir)
        if not images:
            QMessageBox.warning(self, "提示", f"输入目录中没有找到支持的图像文件！")
            return

        params = self._get_params()
        params["output_prefix"] = self.batch_prefix_edit.text()
        params["output_format"] = self.batch_fmt_combo.currentText()

        self.batch_run_btn.setEnabled(False)
        self.batch_progress.setValue(0)
        self.batch_log.clear()
        self.batch_log.append(f"找到 {len(images)} 张图像，开始处理...")

        self.batch_worker = BatchWorker(input_dir, output_dir, params)
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.finished.connect(self._on_batch_finished)
        self.batch_worker.start()

    def _on_batch_progress(self, current: int, total: int, msg: str):
        pct = int(current / total * 100) if total > 0 else 0
        self.batch_progress.setValue(pct)
        self.batch_log.append(f"[{current}/{total}] {msg}")
        sb = self.batch_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_batch_finished(self, results: dict):
        self.batch_run_btn.setEnabled(True)
        success = sum(1 for v in results.values() if not str(v).startswith("ERROR"))
        failed = sum(1 for v in results.values() if str(v).startswith("ERROR"))
        self.batch_log.append(f"\n处理完成！成功: {success}, 失败: {failed}")

    def _evaluate_ocr(self):
        if self.current_image is None:
            QMessageBox.warning(self, "提示", "请先加载一张图像！")
            return
        if not TESSERACT_AVAILABLE:
            QMessageBox.warning(
                self, "Tesseract 未安装",
                "未检测到 pytesseract。请安装 Tesseract OCR 引擎和 pytesseract 包。"
            )
            return

        params = self._get_params()
        lang = self.ocr_lang_combo.currentText()
        psm = int(self.ocr_psm_combo.currentText())
        ref_text = self.ocr_ref_edit.toPlainText().strip() or None

        self.ocr_result_text.clear()
        self.ocr_result_text.append("正在评估 OCR 准确率，请稍候...")
        QApplication.processEvents()

        try:
            result = evaluate_binarization(
                self.current_image_path or "",
                lang=lang,
                psm=psm,
                reference_text=ref_text,
                **params,
            )
            self._display_ocr_result(result)
        except Exception as e:
            self.ocr_result_text.append(f"评估失败: {str(e)}")

    def _display_ocr_result(self, result: dict):
        self.ocr_result_text.clear()
        if "error" in result:
            self.ocr_result_text.append(f"错误: {result['error']}")
            return

        orig = result.get('original', {})
        binary = result.get('binary', {})

        self.ocr_result_text.append("=" * 60)
        self.ocr_result_text.append("  OCR 准确率评估结果")
        self.ocr_result_text.append("=" * 60)
        self.ocr_result_text.append(f"方法: {result.get('method', 'N/A')}")
        self.ocr_result_text.append(f"图像 DPI: {self.image_dpi}")
        self.ocr_result_text.append("")

        self.ocr_result_text.append("--- 原始图像 ---")
        self.ocr_result_text.append(f"平均置信度: {orig.get('avg_confidence', 0):.2f}%")
        self.ocr_result_text.append(f"识别单词数: {orig.get('num_words', 0)}")
        self.ocr_result_text.append(f"识别行数: {orig.get('num_lines', 0)}")
        self.ocr_result_text.append(f"字符总数: {orig.get('char_count', 0)}")
        self.ocr_result_text.append(
            f"高置信度单词比例: {orig.get('high_conf_ratio', 0):.2%}"
        )
        self.ocr_result_text.append(f"识别文本:\n{orig.get('text', '')}")
        self.ocr_result_text.append("")

        self.ocr_result_text.append("--- 二值化图像 ---")
        self.ocr_result_text.append(f"平均置信度: {binary.get('avg_confidence', 0):.2f}%")
        self.ocr_result_text.append(f"识别单词数: {binary.get('num_words', 0)}")
        self.ocr_result_text.append(f"识别行数: {binary.get('num_lines', 0)}")
        self.ocr_result_text.append(f"字符总数: {binary.get('char_count', 0)}")
        self.ocr_result_text.append(
            f"高置信度单词比例: {binary.get('high_conf_ratio', 0):.2%}"
        )
        self.ocr_result_text.append(f"识别文本:\n{binary.get('text', '')}")
        self.ocr_result_text.append("")

        self.ocr_result_text.append("--- 提升效果 ---")
        conf_imp = result.get('confidence_improvement', 0)
        arrow = "↑" if conf_imp > 0 else ("↓" if conf_imp < 0 else "→")
        self.ocr_result_text.append(f"置信度提升: {conf_imp:+.2f}% {arrow}")

        word_imp = result.get('word_count_improvement', 0)
        arrow = "↑" if word_imp > 0 else ("↓" if word_imp < 0 else "→")
        self.ocr_result_text.append(f"识别单词数变化: {word_imp:+d} {arrow}")

        hc_imp = result.get('high_conf_ratio_improvement', 0)
        arrow = "↑" if hc_imp > 0 else ("↓" if hc_imp < 0 else "→")
        self.ocr_result_text.append(f"高置信度比例提升: {hc_imp:+.4f} {arrow}")

        if "char_accuracy_improvement" in result:
            self.ocr_result_text.append("")
            self.ocr_result_text.append("--- 字符级准确率 (对比参考文本) ---")
            self.ocr_result_text.append(
                f"原始图像 CER: {result.get('char_error_rate_original', 0):.4f} ({result.get('original_char_accuracy', 0):.2%})"
            )
            self.ocr_result_text.append(
                f"二值化图像 CER: {result.get('char_error_rate_binary', 0):.4f} ({result.get('binary_char_accuracy', 0):.2%})"
            )
            char_imp = result.get('char_accuracy_improvement', 0)
            arrow = "↑" if char_imp > 0 else ("↓" if char_imp < 0 else "→")
            self.ocr_result_text.append(f"准确率提升: {char_imp:+.4f} {arrow}")

            orig_align = result.get('original_char_alignment', {})
            if orig_align:
                self.ocr_result_text.append("")
                self.ocr_result_text.append("--- 原始图像错误详情 ---")
                self.ocr_result_text.append(f"正确字符: {orig_align.get('correct', 0)}")
                self.ocr_result_text.append(f"插入错误: {orig_align.get('insertions', 0)}")
                self.ocr_result_text.append(f"删除错误: {orig_align.get('deletions', 0)}")
                self.ocr_result_text.append(f"替换错误: {orig_align.get('substitutions', 0)}")
                self.ocr_result_text.append(f"编辑距离: {orig_align.get('edit_distance', 0)}")

            bin_align = result.get('binary_char_alignment', {})
            if bin_align:
                self.ocr_result_text.append("")
                self.ocr_result_text.append("--- 二值化图像错误详情 ---")
                self.ocr_result_text.append(f"正确字符: {bin_align.get('correct', 0)}")
                self.ocr_result_text.append(f"插入错误: {bin_align.get('insertions', 0)}")
                self.ocr_result_text.append(f"删除错误: {bin_align.get('deletions', 0)}")
                self.ocr_result_text.append(f"替换错误: {bin_align.get('substitutions', 0)}")
                self.ocr_result_text.append(f"编辑距离: {bin_align.get('edit_distance', 0)}")