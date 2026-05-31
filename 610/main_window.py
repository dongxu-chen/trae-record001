import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QFileDialog, QProgressBar, QGroupBox, QCheckBox, QTabWidget,
    QSlider, QRadioButton, QButtonGroup, QTextEdit, QScrollArea
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from psf_generator import PSFGenerator
from deconvolution import (RichardsonLucy, RichardsonLucyGPU,
                            BlindRichardsonLucy, calculate_psnr)
from deconvolution_3d import (RichardsonLucy3D, MultiChannelDeconvolver,
                               ZSliceDeconvolver, PSF3DGenerator)
from czi_reader import CZIReader, SimulatedCZIGenerator
from quality_metrics import (DeconvolutionQualityReport,
                              evaluate_3d_volume, evaluate_multichannel)
from image_utils import ImageProcessor


class DeconvolutionThread(QThread):
    progress = pyqtSignal(int, int)
    progress_blind = pyqtSignal(int, int, np.ndarray)
    progress_3d = pyqtSignal(int, int, int, str)
    finished = pyqtSignal(np.ndarray, object, object)
    error = pyqtSignal(str)

    def __init__(self, image, psf=None, num_iterations=50,
                 convergence_threshold=1e-4, use_gpu=False,
                 blind_mode=False, psf_size=21, num_outer_iterations=8,
                 tile_mode=False, tile_size=256,
                 mode_3d=False, mode_multichannel=False, psf_3d=None):
        super().__init__()
        self.image = image
        self.psf = psf
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold
        self.use_gpu = use_gpu
        self.blind_mode = blind_mode
        self.psf_size = psf_size
        self.num_outer_iterations = num_outer_iterations
        self.tile_mode = tile_mode
        self.tile_size = tile_size
        self.mode_3d = mode_3d
        self.mode_multichannel = mode_multichannel
        self.psf_3d = psf_3d

    def run(self):
        try:
            if self.mode_3d and self.mode_multichannel:
                self._run_multichannel_3d()
            elif self.mode_3d:
                self._run_3d()
            elif self.mode_multichannel:
                self._run_multichannel()
            elif self.blind_mode:
                self._run_blind()
            else:
                self._run_standard()
        except Exception as e:
            import traceback
            self.error.emit(str(e) + "\n" + traceback.format_exc())

    def _run_standard(self):
        if self.use_gpu:
            deconv = RichardsonLucyGPU(self.psf, self.num_iterations,
                                        self.convergence_threshold,
                                        tile_size=self.tile_size)
        else:
            deconv = RichardsonLucy(self.psf, self.num_iterations,
                                     self.convergence_threshold,
                                     tile_size=self.tile_size)

        def callback(iteration, total, img, change_rate):
            self.progress.emit(iteration + 1, total)

        if self.tile_mode:
            result = deconv.deconvolve_tiled(self.image, callback=callback)
        else:
            result = deconv.deconvolve(self.image, callback=callback)

        self.finished.emit(result, self.psf, None)

    def _run_blind(self):
        blind = BlindRichardsonLucy(
            psf_size=self.psf_size,
            num_outer_iterations=self.num_outer_iterations,
            num_inner_iterations=self.num_iterations,
            convergence_threshold=self.convergence_threshold,
            use_gpu=self.use_gpu,
            tile_size=self.tile_size
        )

        def callback(outer_i, total, img, psf):
            self.progress_blind.emit(outer_i + 1, total, psf)

        result, estimated_psf = blind.deconvolve(self.image, callback=callback)
        self.finished.emit(result, estimated_psf, None)

    def _run_3d(self):
        psf_3d = self.psf_3d
        if psf_3d is None:
            psf_3d = PSF3DGenerator.estimate_3d_from_image(self.image)

        rl3d = RichardsonLucy3D(psf_3d, self.num_iterations, self.convergence_threshold)

        def callback(iter_i, total, img, rate):
            self.progress.emit(iter_i + 1, total)

        result = rl3d.deconvolve(self.image, callback=callback)
        self.finished.emit(result, psf_3d, None)

    def _run_multichannel(self):
        mc = MultiChannelDeconvolver(
            num_iterations=self.num_iterations,
            convergence_threshold=self.convergence_threshold
        )

        def callback(c, total, img, progress, stage):
            if stage.startswith('iter'):
                self.progress_3d.emit(c, total, int(progress * 100), f"通道{c+1}迭代")
            elif stage.endswith('done'):
                self.progress_3d.emit(c + 1, total, 100, f"通道{c+1}完成")
            else:
                self.progress_3d.emit(c, total, 0, f"通道{c+1}开始")

        result = mc.deconvolve_channels(self.image, callback=callback)
        self.finished.emit(result, None, None)

    def _run_multichannel_3d(self):
        mc = MultiChannelDeconvolver(
            num_iterations=self.num_iterations,
            convergence_threshold=self.convergence_threshold
        )

        def callback(c, total, img, progress, stage):
            if stage.startswith('iter'):
                self.progress_3d.emit(c, total, int(progress * 100), f"通道{c+1}迭代")
            elif stage.endswith('done'):
                self.progress_3d.emit(c + 1, total, 100, f"通道{c+1}完成")
            else:
                self.progress_3d.emit(c, total, 0, f"通道{c+1}开始")

        result = mc.deconvolve_3d_channels(self.image, callback=callback)
        self.finished.emit(result, None, None)


class ImageLabel(QLabel):
    def __init__(self, title=""):
        super().__init__()
        self.title = title
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(280, 280)
        self.setStyleSheet("QLabel { border: 1px solid #ccc; background-color: #f0f0f0; }")
        self.image = None

    def set_image(self, image):
        self.image = image
        if image is not None:
            qimg = self.numpy_to_qimage(image)
            pixmap = QPixmap.fromImage(qimg)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
        else:
            self.setText(f"{self.title}\n\n(等待图像)")

    def numpy_to_qimage(self, image):
        if len(image.shape) == 2:
            img = (np.clip(image, 0, 1) * 255).astype(np.uint8)
            h, w = img.shape
            qimg = QImage(w, h, QImage.Format_Grayscale8)
            for y in range(h):
                qimg.scanLine(y).asarray(w)[:] = img[y].tobytes()
            return qimg
        else:
            img = (np.clip(image, 0, 1) * 255).astype(np.uint8)
            h, w, c = img.shape
            qimg = QImage(w, h, QImage.Format_RGB888)
            for y in range(h):
                qimg.scanLine(y).asarray(w * 3)[:] = img[y].tobytes()
            return qimg

    def resizeEvent(self, event):
        if self.image is not None:
            self.set_image(self.image)
        super().resizeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("荧光显微镜3D去卷积工具")
        self.setGeometry(100, 100, 1400, 900)

        self.original_image = None
        self.deconvolved_image = None
        self.current_psf = None
        self.current_psf_3d = None
        self.deconv_thread = None
        self.quality_report = None
        self.current_channel = 0
        self.current_z = 0
        self.is_3d = False
        self.is_multichannel = False
        self.czi_metadata = {}

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        control_panel = self.create_control_panel()
        control_panel.setFixedWidth(380)
        main_layout.addWidget(control_panel)

        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel)

    def create_control_panel(self):
        scroll = QScrollArea()
        panel = QWidget()
        layout = QVBoxLayout(panel)

        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout()
        self.btn_load = QPushButton("加载2D图像")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_load_czi = QPushButton("加载CZI (3D/多通道)")
        self.btn_load_czi.clicked.connect(self.load_czi)
        self.btn_generate_test = QPushButton("生成2D测试图像")
        self.btn_generate_test.clicked.connect(self.generate_test_image)
        self.btn_generate_3d = QPushButton("生成3D/多通道测试数据")
        self.btn_generate_3d.clicked.connect(self.generate_3d_test)
        self.btn_save = QPushButton("保存结果")
        self.btn_save.clicked.connect(self.save_result)
        self.btn_save.setEnabled(False)
        file_layout.addWidget(self.btn_load)
        file_layout.addWidget(self.btn_load_czi)
        file_layout.addWidget(self.btn_generate_test)
        file_layout.addWidget(self.btn_generate_3d)
        file_layout.addWidget(self.btn_save)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        data_group = QGroupBox("数据信息")
        data_layout = QVBoxLayout()
        self.data_info_label = QLabel("未加载数据")
        self.data_info_label.setWordWrap(True)
        data_layout.addWidget(self.data_info_label)
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(QLabel("Z层:"))
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.valueChanged.connect(self.update_3d_view)
        self.z_slider.setEnabled(False)
        nav_layout.addWidget(self.z_slider)
        data_layout.addLayout(nav_layout)
        ch_layout = QHBoxLayout()
        ch_layout.addWidget(QLabel("通道:"))
        self.channel_combo = QComboBox()
        self.channel_combo.currentIndexChanged.connect(self.update_3d_view)
        self.channel_combo.setEnabled(False)
        ch_layout.addWidget(self.channel_combo)
        data_layout.addLayout(ch_layout)
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        mode_group = QGroupBox("去卷积模式")
        mode_layout = QVBoxLayout()
        self.mode_btn_group = QButtonGroup()
        self.radio_blind = QRadioButton("盲去卷积（2D）")
        self.radio_standard = QRadioButton("标准去卷积（2D）")
        self.radio_3d = QRadioButton("3D去卷积")
        self.radio_mc = QRadioButton("多通道去卷积")
        self.radio_blind.setChecked(True)
        self.mode_btn_group.addButton(self.radio_blind, 0)
        self.mode_btn_group.addButton(self.radio_standard, 1)
        self.mode_btn_group.addButton(self.radio_3d, 2)
        self.mode_btn_group.addButton(self.radio_mc, 3)
        mode_layout.addWidget(self.radio_blind)
        mode_layout.addWidget(self.radio_standard)
        mode_layout.addWidget(self.radio_3d)
        mode_layout.addWidget(self.radio_mc)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        psf_group = QGroupBox("PSF设置")
        psf_layout = QVBoxLayout()
        psf_layout.addWidget(QLabel("PSF大小:"))
        self.psf_size_spin = QSpinBox()
        self.psf_size_spin.setRange(5, 51)
        self.psf_size_spin.setSingleStep(2)
        self.psf_size_spin.setValue(21)
        self.psf_size_spin.valueChanged.connect(self.update_psf)
        psf_layout.addWidget(self.psf_size_spin)
        psf_layout.addWidget(QLabel("PSF Z大小:"))
        self.psf_z_spin = QSpinBox()
        self.psf_z_spin.setRange(3, 15)
        self.psf_z_spin.setSingleStep(2)
        self.psf_z_spin.setValue(5)
        self.psf_z_spin.valueChanged.connect(self.update_psf)
        psf_layout.addWidget(self.psf_z_spin)
        psf_layout.addWidget(QLabel("XY Sigma:"))
        self.psf_sigma_xy = QDoubleSpinBox()
        self.psf_sigma_xy.setRange(0.5, 10.0)
        self.psf_sigma_xy.setSingleStep(0.1)
        self.psf_sigma_xy.setValue(2.0)
        self.psf_sigma_xy.valueChanged.connect(self.update_psf)
        psf_layout.addWidget(self.psf_sigma_xy)
        psf_layout.addWidget(QLabel("Z Sigma:"))
        self.psf_sigma_z = QDoubleSpinBox()
        self.psf_sigma_z.setRange(0.5, 5.0)
        self.psf_sigma_z.setSingleStep(0.1)
        self.psf_sigma_z.setValue(1.0)
        self.psf_sigma_z.valueChanged.connect(self.update_psf)
        psf_layout.addWidget(self.psf_sigma_z)
        self.btn_update_psf = QPushButton("生成/更新PSF")
        self.btn_update_psf.clicked.connect(self.update_psf)
        psf_layout.addWidget(self.btn_update_psf)
        psf_group.setLayout(psf_layout)
        layout.addWidget(psf_group)

        deconv_group = QGroupBox("去卷积设置")
        deconv_layout = QVBoxLayout()
        iter_layout = QHBoxLayout()
        iter_layout.addWidget(QLabel("最大迭代:"))
        self.iter_spin = QSpinBox()
        self.iter_spin.setRange(1, 200)
        self.iter_spin.setValue(30)
        iter_layout.addWidget(self.iter_spin)
        deconv_layout.addLayout(iter_layout)
        conv_layout = QHBoxLayout()
        conv_layout.addWidget(QLabel("收敛阈值:"))
        self.convergence_spin = QDoubleSpinBox()
        self.convergence_spin.setRange(1e-7, 1e-1)
        self.convergence_spin.setDecimals(7)
        self.convergence_spin.setValue(1e-4)
        conv_layout.addWidget(self.convergence_spin)
        deconv_layout.addLayout(conv_layout)
        outer_layout = QHBoxLayout()
        outer_layout.addWidget(QLabel("盲去卷积外循环:"))
        self.outer_iter_spin = QSpinBox()
        self.outer_iter_spin.setRange(1, 20)
        self.outer_iter_spin.setValue(5)
        outer_layout.addWidget(self.outer_iter_spin)
        deconv_layout.addLayout(outer_layout)
        self.gpu_checkbox = QCheckBox("使用GPU加速")
        deconv_layout.addWidget(self.gpu_checkbox)
        self.btn_deconvolve = QPushButton("开始去卷积")
        self.btn_deconvolve.clicked.connect(self.start_deconvolution)
        self.btn_deconvolve.setEnabled(False)
        deconv_layout.addWidget(self.btn_deconvolve)
        self.progress_bar = QProgressBar()
        deconv_layout.addWidget(self.progress_bar)
        deconv_group.setLayout(deconv_layout)
        layout.addWidget(deconv_group)

        quality_group = QGroupBox("质量评估")
        quality_layout = QVBoxLayout()
        self.btn_evaluate = QPushButton("计算质量指标")
        self.btn_evaluate.clicked.connect(self.evaluate_quality)
        self.btn_evaluate.setEnabled(False)
        quality_layout.addWidget(self.btn_evaluate)
        self.quality_text = QTextEdit()
        self.quality_text.setReadOnly(True)
        self.quality_text.setMaximumHeight(200)
        quality_layout.addWidget(self.quality_text)
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        self.info_label = QLabel("准备就绪")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addStretch()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        return scroll

    def create_display_panel(self):
        panel = QTabWidget()

        tab1 = QWidget()
        tab1_layout = QHBoxLayout(tab1)
        self.original_label = ImageLabel("原始图像")
        self.deconv_label = ImageLabel("去卷积结果")
        tab1_layout.addWidget(self.original_label)
        tab1_layout.addWidget(self.deconv_label)
        panel.addTab(tab1, "对比视图")

        tab2 = QWidget()
        tab2_layout = QHBoxLayout(tab2)
        self.psf_label = ImageLabel("PSF (中心Z层)")
        tab2_layout.addWidget(self.psf_label)
        panel.addTab(tab2, "PSF视图")

        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        self.mip_original_label = ImageLabel("原始 MIP")
        self.mip_deconv_label = ImageLabel("去卷积 MIP")
        mip_layout = QHBoxLayout()
        mip_layout.addWidget(self.mip_original_label)
        mip_layout.addWidget(self.mip_deconv_label)
        tab3_layout.addLayout(mip_layout)
        panel.addTab(tab3, "3D MIP视图")

        return panel

    def load_image(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择图像", "", "图像文件 (*.png *.jpg *.bmp *.tif *.tiff)"
        )
        if filepath:
            try:
                self.original_image = ImageProcessor.load_image(filepath)
                self.is_3d = False
                self.is_multichannel = False
                self._update_display()
                self.btn_deconvolve.setEnabled(True)
                self.btn_save.setEnabled(False)
                self.btn_evaluate.setEnabled(False)
                self.info_label.setText(f"已加载2D图像: {self.original_image.shape}")
            except Exception as e:
                import traceback
                self.info_label.setText(f"加载失败: {str(e)}\n{traceback.format_exc()}")

    def load_czi(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择CZI文件", "", "CZI文件 (*.czi)"
        )
        if filepath:
            try:
                if CZIReader.available():
                    image, metadata = CZIReader.read_czi(filepath)
                    image = CZIReader.normalize_to_float(image)
                    self.czi_metadata = metadata
                else:
                    raise ImportError("czifile not installed. Install with: pip install czifile")

                self.original_image = image
                self._setup_3d_multichannel()
                self.info_label.setText(f"已加载CZI: {image.shape}, Metadata: {metadata}")
            except Exception as e:
                import traceback
                self.info_label.setText(f"加载失败: {str(e)}\n{traceback.format_exc()}")

    def generate_test_image(self):
        self.original_image = ImageProcessor.generate_test_image(size=256, num_spots=15)
        test_psf = PSFGenerator.gaussian_psf(21, sigma=3.0)
        self.original_image = ImageProcessor.generate_blurred_image(
            self.original_image, test_psf, noise_std=0.005
        )
        self.is_3d = False
        self.is_multichannel = False
        self._update_display()
        self.btn_deconvolve.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_evaluate.setEnabled(False)
        self.info_label.setText(f"已生成2D测试图像: {self.original_image.shape}")

    def generate_3d_test(self):
        self.original_image = SimulatedCZIGenerator.generate_test_3d(
            size_z=8, size_y=128, size_x=128, num_channels=2, num_spots_per_slice=6
        )
        test_psf_3d = PSF3DGenerator.gaussian_3d(15, 5, 2.0, 1.0)
        self.original_image = SimulatedCZIGenerator.generate_blurred_3d(
            self.original_image, test_psf_3d[test_psf_3d.shape[0]//2],
            psf_z=test_psf_3d[:, test_psf_3d.shape[1]//2, test_psf_3d.shape[2]//2]
        )
        self._setup_3d_multichannel()
        self.info_label.setText(f"已生成3D多通道测试数据: {self.original_image.shape}")

    def _setup_3d_multichannel(self):
        if self.original_image.ndim == 4:
            self.is_3d = True
            self.is_multichannel = True
            num_channels, num_z, _, _ = self.original_image.shape
            self.channel_combo.clear()
            for c in range(num_channels):
                self.channel_combo.addItem(f"通道 {c+1}")
            self.channel_combo.setEnabled(num_channels > 1)
            self.z_slider.setRange(0, num_z - 1)
            self.z_slider.setEnabled(num_z > 1)
        elif self.original_image.ndim == 3:
            self.is_3d = True
            self.is_multichannel = False
            num_z, _, _ = self.original_image.shape
            self.channel_combo.clear()
            self.channel_combo.addItem("单通道")
            self.channel_combo.setEnabled(False)
            self.z_slider.setRange(0, num_z - 1)
            self.z_slider.setEnabled(num_z > 1)
        else:
            self.is_3d = False
            self.is_multichannel = False

        self.current_channel = 0
        self.current_z = 0
        self.z_slider.setValue(0)
        self._update_display()
        self.btn_deconvolve.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_evaluate.setEnabled(False)
        info = f"数据形状: {self.original_image.shape}"
        if self.is_3d:
            info += f" | 3D模式"
        if self.is_multichannel:
            info += f" | 多通道模式"
        self.data_info_label.setText(info)

    def _update_display(self):
        orig_display = self._get_current_slice(self.original_image)
        self.original_label.set_image(orig_display)

        if self.deconvolved_image is not None:
            deconv_display = self._get_current_slice(self.deconvolved_image)
            self.deconv_label.set_image(deconv_display)
        else:
            self.deconv_label.setText("去卷积结果\n\n(等待处理)")

        if self.is_3d:
            orig_mip = self._compute_mip(self.original_image)
            self.mip_original_label.set_image(orig_mip)
            if self.deconvolved_image is not None:
                deconv_mip = self._compute_mip(self.deconvolved_image)
                self.mip_deconv_label.set_image(deconv_mip)
            else:
                self.mip_deconv_label.setText("去卷积 MIP\n\n(等待处理)")

        if self.current_psf_3d is not None:
            psf_display = self.current_psf_3d[self.current_psf_3d.shape[0] // 2]
            self.psf_label.set_image(ImageProcessor.normalize(psf_display))
        elif self.current_psf is not None:
            self.psf_label.set_image(ImageProcessor.normalize(self.current_psf))

    def _get_current_slice(self, image):
        if image is None:
            return None
        if self.is_multichannel and self.is_3d:
            return image[self.current_channel, self.current_z]
        elif self.is_multichannel:
            return image[self.current_channel]
        elif self.is_3d:
            return image[self.current_z]
        else:
            return image

    def _compute_mip(self, image):
        if image is None:
            return None
        if self.is_multichannel:
            return np.max(image[self.current_channel], axis=0)
        else:
            return np.max(image, axis=0)

    def update_3d_view(self):
        self.current_channel = self.channel_combo.currentIndex() if self.channel_combo.isEnabled() else 0
        self.current_z = self.z_slider.value() if self.z_slider.isEnabled() else 0
        self._update_display()

    def update_psf(self):
        size_xy = self.psf_size_spin.value()
        size_z = self.psf_z_spin.value()
        sigma_xy = self.psf_sigma_xy.value()
        sigma_z = self.psf_sigma_z.value()

        self.current_psf_3d = PSF3DGenerator.gaussian_3d(size_xy, size_z, sigma_xy, sigma_z)
        self.current_psf = self.current_psf_3d[size_z // 2]

        psf_display = ImageProcessor.normalize(self.current_psf)
        self.psf_label.set_image(psf_display)
        self.info_label.setText(f"PSF已更新: {self.current_psf_3d.shape}")

    def start_deconvolution(self):
        if self.original_image is None:
            return

        self.btn_deconvolve.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        if self.radio_3d.isChecked():
            self.info_label.setText("3D去卷积中...")
            input_data = self.original_image[self.current_channel] if self.is_multichannel else self.original_image
        elif self.radio_mc.isChecked():
            self.info_label.setText("多通道去卷积中...")
            input_data = self.original_image
        else:
            self.info_label.setText("去卷积中...")
            input_data = self._get_current_slice(self.original_image)

        self.deconv_thread = DeconvolutionThread(
            input_data,
            psf=self.current_psf,
            psf_3d=self.current_psf_3d,
            num_iterations=self.iter_spin.value(),
            convergence_threshold=self.convergence_spin.value(),
            use_gpu=self.gpu_checkbox.isChecked(),
            blind_mode=self.radio_blind.isChecked(),
            psf_size=self.psf_size_spin.value(),
            num_outer_iterations=self.outer_iter_spin.value(),
            mode_3d=self.radio_3d.isChecked(),
            mode_multichannel=self.radio_mc.isChecked()
        )
        self.deconv_thread.progress.connect(self.update_progress)
        self.deconv_thread.progress_blind.connect(self.update_blind_progress)
        self.deconv_thread.progress_3d.connect(self.update_3d_progress)
        self.deconv_thread.finished.connect(self.deconvolution_finished)
        self.deconv_thread.error.connect(self.deconvolution_error)
        self.deconv_thread.start()

    def update_progress(self, current, total):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.info_label.setText(f"迭代进度: {current}/{total}")

    def update_blind_progress(self, current, total, psf):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        if psf is not None:
            self.current_psf = psf
            self.psf_label.set_image(ImageProcessor.normalize(psf))
        self.info_label.setText(f"盲去卷积外循环: {current}/{total}")

    def update_3d_progress(self, channel, total, sub_progress, message):
        self.progress_bar.setRange(0, total * 100)
        self.progress_bar.setValue(channel * 100 + sub_progress)
        self.info_label.setText(f"{message}: {sub_progress}%")

    def deconvolution_finished(self, result, psf, report):
        self.deconvolved_image = result
        if psf is not None:
            if psf.ndim == 3:
                self.current_psf_3d = psf
                self.current_psf = psf[psf.shape[0] // 2]
            else:
                self.current_psf = psf
                psf_display = ImageProcessor.normalize(psf)
                self.psf_label.set_image(psf_display)

        if self.radio_3d.isChecked() and self.is_multichannel:
            temp = self.original_image.copy()
            temp[self.current_channel] = result
            self.deconvolved_image = temp

        self._update_display()
        self.btn_deconvolve.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_evaluate.setEnabled(True)
        self.info_label.setText("去卷积完成! 可点击'计算质量指标'查看评估")

    def deconvolution_error(self, error_msg):
        self.info_label.setText(f"错误: {error_msg}")
        self.btn_deconvolve.setEnabled(True)

    def evaluate_quality(self):
        if self.deconvolved_image is None:
            return

        self.quality_text.clear()
        self.quality_text.append("正在计算质量指标...\n")
        QApplication.processEvents()

        try:
            if self.is_3d or self.is_multichannel:
                orig_flat = self._get_current_slice(self.original_image)
                deconv_flat = self._get_current_slice(self.deconvolved_image)
                report = DeconvolutionQualityReport()
                report.evaluate(orig_flat, deconv_flat)
                self.quality_text.setText(report.generate_report_text())

                if self.is_3d and not self.is_multichannel:
                    slice_reports, avg_imp = evaluate_3d_volume(self.original_image, self.deconvolved_image)
                    self.quality_text.append("\n【3D体积平均提升】")
                    self.quality_text.append(f"  SNR平均提升: {avg_imp['snr_gain_db']:.2f} dB")
                    self.quality_text.append(f"  CNR平均提升: {avg_imp['cnr_gain']:.2f}")
                    self.quality_text.append(f"  锐度平均提升: {avg_imp['sharpness_gain_pct']:.1f}%")
            else:
                report = DeconvolutionQualityReport()
                report.evaluate(self.original_image, self.deconvolved_image)
                self.quality_text.setText(report.generate_report_text())
        except Exception as e:
            import traceback
            self.quality_text.setText(f"评估错误: {str(e)}\n{traceback.format_exc()}")

    def save_result(self):
        if self.deconvolved_image is None:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "PNG图像 (*.png);;TIFF图像 (*.tif);;NumPy数据 (*.npy)"
        )
        if filepath:
            try:
                if filepath.endswith('.npy'):
                    np.save(filepath, self.deconvolved_image)
                else:
                    display = self._get_current_slice(self.deconvolved_image)
                    ImageProcessor.save_image(filepath, display)
                self.info_label.setText(f"已保存至: {filepath}")
            except Exception as e:
                self.info_label.setText(f"保存失败: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
