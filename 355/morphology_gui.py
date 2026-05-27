import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QSlider, QFileDialog,
    QProgressBar, QGroupBox, QGridLayout, QCheckBox, QTabWidget
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

from morphology_lib import (
    erode, dilate, open_op, close_op,
    top_hat, black_hat, morphological_gradient,
    create_rect, create_ellipse, create_cross,
    LargeImageProcessor,
    fill_holes, extract_connected_components, remove_small_objects, extract_boundary,
    gradient_internal, gradient_external, gradient_basic, laplacian_gradient,
    sobel_like_gradient, edge_detection, canny_like
)


class ProcessingThread(QThread):
    finished = pyqtSignal(np.ndarray)
    progress = pyqtSignal(int)

    def __init__(self, image, operation, structure, use_large_image=False, block_size=1024, **kwargs):
        super().__init__()
        self.image = image
        self.operation = operation
        self.structure = structure
        self.use_large_image = use_large_image
        self.block_size = block_size
        self.kwargs = kwargs

    def run(self):
        if self.use_large_image and self.image.size > 1024 * 1024 * 3:
            processor = LargeImageProcessor(block_size=(self.block_size, self.block_size))
            operations = {
                'erode': processor.erode,
                'dilate': processor.dilate,
                'open': processor.open_op,
                'close': processor.close_op,
                'top_hat': processor.top_hat,
                'black_hat': processor.black_hat,
                'gradient': processor.morphological_gradient
            }
            result = operations[self.operation](self.image, self.structure)
        else:
            operations = {
                'erode': erode,
                'dilate': dilate,
                'open': open_op,
                'close': close_op,
                'top_hat': top_hat,
                'black_hat': black_hat,
                'gradient': morphological_gradient,
                'fill_holes': fill_holes,
                'remove_small': remove_small_objects,
                'boundary': extract_boundary,
                'grad_internal': gradient_internal,
                'grad_external': gradient_external,
                'grad_basic': gradient_basic,
                'grad_laplacian': laplacian_gradient,
                'grad_sobel': sobel_like_gradient,
                'edge_detect': edge_detection,
                'canny': canny_like
            }
            result = operations[self.operation](self.image, self.structure, **self.kwargs)

        self.finished.emit(result)


class MorphologyGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('形态学图像处理工具 v2.0')
        self.setGeometry(100, 100, 1600, 1000)

        self.original_image = None
        self.preview_image = None
        self.processed_image = None
        self.processing_thread = None
        self.preview_processing_thread = None
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.update_preview)
        self.debounce_delay = 300

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        control_panel = self.create_control_panel()
        image_panel = self.create_image_panel()

        main_layout.addWidget(control_panel, 1)
        main_layout.addWidget(image_panel, 3)

    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        file_group = QGroupBox('文件操作')
        file_layout = QVBoxLayout()
        self.btn_load = QPushButton('加载图像')
        self.btn_load.clicked.connect(self.load_image)
        self.btn_save = QPushButton('保存结果')
        self.btn_save.clicked.connect(self.save_image)
        self.btn_save.setEnabled(False)
        file_layout.addWidget(self.btn_load)
        file_layout.addWidget(self.btn_save)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        tab_widget = QTabWidget()

        basic_tab = self.create_basic_tab()
        recon_tab = self.create_reconstruction_tab()
        edge_tab = self.create_edge_tab()

        tab_widget.addTab(basic_tab, '基础操作')
        tab_widget.addTab(recon_tab, '形态学重建')
        tab_widget.addTab(edge_tab, '边缘检测')

        tab_widget.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(tab_widget)

        options_group = QGroupBox('选项')
        options_layout = QVBoxLayout()

        self.chk_live_preview = QCheckBox('实时预览（松手后更新）')
        self.chk_live_preview.setChecked(True)
        self.chk_live_preview.stateChanged.connect(self.on_live_preview_changed)
        options_layout.addWidget(self.chk_live_preview)

        self.chk_large_image = QCheckBox('大图像分块处理')
        self.chk_large_image.setChecked(False)
        options_layout.addWidget(self.chk_large_image)

        self.btn_process = QPushButton('完整处理（高分辨率）')
        self.btn_process.clicked.connect(self.process_image_full)
        self.btn_process.setEnabled(False)
        options_layout.addWidget(self.btn_process)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel('就绪')
        layout.addWidget(self.lbl_status)

        layout.addStretch()
        self.update_kernel_preview()

        return panel

    def create_basic_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        kernel_group = QGroupBox('结构元素')
        kernel_layout = QGridLayout()

        kernel_layout.addWidget(QLabel('类型:'), 0, 0)
        self.cb_kernel_type = QComboBox()
        self.cb_kernel_type.addItems(['矩形', '椭圆', '十字形'])
        self.cb_kernel_type.currentIndexChanged.connect(self.on_parameter_changed)
        kernel_layout.addWidget(self.cb_kernel_type, 0, 1)

        kernel_layout.addWidget(QLabel('宽度:'), 1, 0)
        self.spin_kernel_w = QSpinBox()
        self.spin_kernel_w.setRange(1, 51)
        self.spin_kernel_w.setValue(3)
        self.spin_kernel_w.setSingleStep(2)
        self.spin_kernel_w.valueChanged.connect(self.on_parameter_changed)
        kernel_layout.addWidget(self.spin_kernel_w, 1, 1)

        kernel_layout.addWidget(QLabel('高度:'), 2, 0)
        self.spin_kernel_h = QSpinBox()
        self.spin_kernel_h.setRange(1, 51)
        self.spin_kernel_h.setValue(3)
        self.spin_kernel_h.setSingleStep(2)
        self.spin_kernel_h.valueChanged.connect(self.on_parameter_changed)
        kernel_layout.addWidget(self.spin_kernel_h, 2, 1)

        self.kernel_preview_label = QLabel()
        self.kernel_preview_label.setAlignment(Qt.AlignCenter)
        kernel_layout.addWidget(self.kernel_preview_label, 3, 0, 1, 2)

        kernel_group.setLayout(kernel_layout)
        layout.addWidget(kernel_group)

        op_group = QGroupBox('形态学操作')
        op_layout = QVBoxLayout()
        self.cb_operation = QComboBox()
        self.cb_operation.addItems([
            '腐蚀 (Erode)', '膨胀 (Dilate)',
            '开运算 (Open)', '闭运算 (Close)',
            '顶帽 (Top Hat)', '黑帽 (Black Hat)',
            '形态学梯度 (Gradient)'
        ])
        self.cb_operation.currentIndexChanged.connect(self.on_parameter_changed)
        op_layout.addWidget(self.cb_operation)

        op_group.setLayout(op_layout)
        layout.addWidget(op_group)

        layout.addStretch()
        return tab

    def create_reconstruction_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        recon_group = QGroupBox('重建操作')
        recon_layout = QVBoxLayout()

        self.cb_recon_operation = QComboBox()
        self.cb_recon_operation.addItems([
            '孔洞填充 (Fill Holes)',
            '移除小物体 (Remove Small Objects)',
            '提取边界 (Extract Boundary)'
        ])
        self.cb_recon_operation.currentIndexChanged.connect(self.on_parameter_changed)
        recon_layout.addWidget(self.cb_recon_operation)

        recon_layout.addWidget(QLabel('最小物体大小:'))
        self.spin_min_size = QSpinBox()
        self.spin_min_size.setRange(1, 10000)
        self.spin_min_size.setValue(100)
        self.spin_min_size.valueChanged.connect(self.on_parameter_changed)
        recon_layout.addWidget(self.spin_min_size)

        recon_group.setLayout(recon_layout)
        layout.addWidget(recon_group)

        layout.addStretch()
        return tab

    def create_edge_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        edge_group = QGroupBox('边缘检测')
        edge_layout = QVBoxLayout()

        self.cb_edge_method = QComboBox()
        self.cb_edge_method.addItems([
            '基本梯度 (Basic)',
            '内部梯度 (Internal)',
            '外部梯度 (External)',
            '拉普拉斯梯度 (Laplacian)',
            'Sobel类梯度',
            '二值化边缘 (Basic + Threshold)',
            'Canny类边缘检测'
        ])
        self.cb_edge_method.currentIndexChanged.connect(self.on_parameter_changed)
        edge_layout.addWidget(self.cb_edge_method)

        edge_layout.addWidget(QLabel('阈值:'))
        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(0, 255)
        self.slider_threshold.setValue(30)
        self.slider_threshold.valueChanged.connect(self.on_parameter_changed)
        edge_layout.addWidget(self.slider_threshold)
        self.lbl_threshold = QLabel('阈值: 30')
        self.slider_threshold.valueChanged.connect(
            lambda v: self.lbl_threshold.setText(f'阈值: {v}')
        )
        edge_layout.addWidget(self.lbl_threshold)

        edge_layout.addWidget(QLabel('高阈值 (Canny):'))
        self.slider_high_threshold = QSlider(Qt.Horizontal)
        self.slider_high_threshold.setRange(0, 255)
        self.slider_high_threshold.setValue(80)
        self.slider_high_threshold.valueChanged.connect(self.on_parameter_changed)
        edge_layout.addWidget(self.slider_high_threshold)
        self.lbl_high_threshold = QLabel('高阈值: 80')
        self.slider_high_threshold.valueChanged.connect(
            lambda v: self.lbl_high_threshold.setText(f'高阈值: {v}')
        )
        edge_layout.addWidget(self.lbl_high_threshold)

        edge_group.setLayout(edge_layout)
        layout.addWidget(edge_group)

        layout.addStretch()
        return tab

    def create_image_panel(self):
        panel = QWidget()
        layout = QGridLayout(panel)

        layout.addWidget(QLabel('原始图像'), 0, 0, Qt.AlignCenter)
        layout.addWidget(QLabel('实时预览（低分辨率）'), 0, 1, Qt.AlignCenter)
        layout.addWidget(QLabel('最终结果'), 0, 2, Qt.AlignCenter)

        self.lbl_original = QLabel()
        self.lbl_original.setAlignment(Qt.AlignCenter)
        self.lbl_original.setStyleSheet('border: 2px solid #ccc;')
        self.lbl_original.setMinimumSize(350, 350)

        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet('border: 2px solid #00a8e8;')
        self.lbl_preview.setMinimumSize(350, 350)

        self.lbl_processed = QLabel()
        self.lbl_processed.setAlignment(Qt.AlignCenter)
        self.lbl_processed.setStyleSheet('border: 2px solid #00c853;')
        self.lbl_processed.setMinimumSize(350, 350)

        layout.addWidget(self.lbl_original, 1, 0)
        layout.addWidget(self.lbl_preview, 1, 1)
        layout.addWidget(self.lbl_processed, 1, 2)

        self.lbl_original_info = QLabel('')
        self.lbl_preview_info = QLabel('')
        self.lbl_processed_info = QLabel('')
        layout.addWidget(self.lbl_original_info, 2, 0, Qt.AlignCenter)
        layout.addWidget(self.lbl_preview_info, 2, 1, Qt.AlignCenter)
        layout.addWidget(self.lbl_processed_info, 2, 2, Qt.AlignCenter)

        return panel

    def on_tab_changed(self):
        self.on_parameter_changed()

    def on_parameter_changed(self):
        self.update_kernel_preview()
        if self.chk_live_preview.isChecked() and self.original_image is not None:
            self.debounce_timer.start(self.debounce_delay)

    def on_live_preview_changed(self):
        if self.chk_live_preview.isChecked() and self.original_image is not None:
            self.update_preview()

    def update_kernel_preview(self):
        ktype = self.cb_kernel_type.currentText()
        kw = self.spin_kernel_w.value()
        kh = self.spin_kernel_h.value()

        if ktype == '矩形':
            se = create_rect((kh, kw))
        elif ktype == '椭圆':
            se = create_ellipse((kh, kw))
        else:
            se = create_cross((kh, kw))

        kernel = se.kernel
        scale = 10
        preview = np.zeros((kh * scale, kw * scale, 3), dtype=np.uint8)

        for r in range(kh):
            for c in range(kw):
                color = (255, 255, 255) if kernel[r, c] == 1 else (50, 50, 50)
                preview[r * scale:(r + 1) * scale, c * scale:(c + 1) * scale] = color

        for r in range(kh + 1):
            cv2.line(preview, (0, r * scale), (kw * scale, r * scale), (100, 100, 100), 1)
        for c in range(kw + 1):
            cv2.line(preview, (c * scale, 0), (c * scale, kh * scale), (100, 100, 100), 1)

        ar = se.anchor
        cv2.rectangle(preview,
                      (ar[1] * scale + 2, ar[0] * scale + 2),
                      ((ar[1] + 1) * scale - 3, (ar[0] + 1) * scale - 3),
                      (255, 0, 0), 2)

        qimg = QImage(preview.data, preview.shape[1], preview.shape[0],
                      preview.strides[0], QImage.Format_RGB888)
        self.kernel_preview_label.setPixmap(QPixmap.fromImage(qimg))

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择图像', '',
            '图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)'
        )
        if file_path:
            self.original_image = cv2.imread(file_path)
            if self.original_image is not None:
                self.display_image(self.original_image, self.lbl_original)
                self.lbl_original_info.setText(
                    f'尺寸: {self.original_image.shape[1]}x{self.original_image.shape[0]}'
                )
                self.lbl_preview.clear()
                self.lbl_preview_info.setText('')
                self.lbl_processed.clear()
                self.lbl_processed_info.setText('')
                self.btn_process.setEnabled(True)
                self.btn_save.setEnabled(False)
                self.processed_image = None
                self.lbl_status.setText('图像已加载')

                if self.chk_live_preview.isChecked():
                    self.update_preview()

    def display_image(self, image, label):
        if len(image.shape) == 2:
            display_img = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        label_size = label.size()
        h, w = display_img.shape[:2]

        scale = min(label_size.width() / w, label_size.height() / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)

        if scale < 1.0:
            display_img = cv2.resize(display_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        qimg = QImage(display_img.data, display_img.shape[1], display_img.shape[0],
                      display_img.strides[0], QImage.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(qimg))

    def get_current_params(self):
        tab_index = self.sender()
        if isinstance(tab_index, int):
            pass
        return None

    def get_current_structure(self):
        ktype = self.cb_kernel_type.currentText()
        kw = self.spin_kernel_w.value()
        kh = self.spin_kernel_h.value()

        if ktype == '矩形':
            return create_rect((kh, kw))
        elif ktype == '椭圆':
            return create_ellipse((kh, kw))
        else:
            return create_cross((kh, kw))

    def get_current_operation_and_params(self):
        tab_widget = self.findChild(QTabWidget)
        current_tab = tab_widget.currentIndex()

        if current_tab == 0:
            op_index = self.cb_operation.currentIndex()
            operations = ['erode', 'dilate', 'open', 'close', 'top_hat', 'black_hat', 'gradient']
            return operations[op_index], {}
        elif current_tab == 1:
            recon_index = self.cb_recon_operation.currentIndex()
            recon_ops = ['fill_holes', 'remove_small', 'boundary']
            op = recon_ops[recon_index]
            params = {}
            if op == 'remove_small':
                params['min_size'] = self.spin_min_size.value()
            return op, params
        else:
            edge_index = self.cb_edge_method.currentIndex()
            edge_ops = ['grad_basic', 'grad_internal', 'grad_external', 'grad_laplacian',
                        'grad_sobel', 'edge_detect', 'canny']
            op = edge_ops[edge_index]
            params = {}
            if op == 'edge_detect':
                params['method'] = 'basic'
                params['threshold'] = self.slider_threshold.value()
            elif op == 'canny':
                params['low_threshold'] = self.slider_threshold.value()
                params['high_threshold'] = self.slider_high_threshold.value()
            return op, params

    def update_preview(self):
        if self.original_image is None:
            return

        if self.preview_processing_thread and self.preview_processing_thread.isRunning():
            return

        h, w = self.original_image.shape[:2]
        max_preview_size = 400
        scale = min(max_preview_size / w, max_preview_size / h, 1.0)

        if scale < 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            preview_img = cv2.resize(self.original_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            preview_img = self.original_image.copy()

        se = self.get_current_structure()
        operation, params = self.get_current_operation_and_params()

        self.lbl_status.setText('预览处理中...')
        self.preview_processing_thread = ProcessingThread(
            preview_img, operation, se, False, **params
        )
        self.preview_processing_thread.finished.connect(self.on_preview_finished)
        self.preview_processing_thread.start()

    def on_preview_finished(self, result):
        self.preview_image = result
        self.display_image(self.preview_image, self.lbl_preview)
        self.lbl_preview_info.setText(
            f'预览尺寸: {self.preview_image.shape[1]}x{self.preview_image.shape[0]}'
        )
        self.lbl_status.setText('就绪')

    def process_image_full(self):
        if self.original_image is None:
            return

        if self.processing_thread and self.processing_thread.isRunning():
            return

        se = self.get_current_structure()
        operation, params = self.get_current_operation_and_params()

        self.btn_process.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText('完整处理中...')

        self.processing_thread = ProcessingThread(
            self.original_image, operation, se,
            self.chk_large_image.isChecked(),
            **params
        )
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.start()

    def on_processing_finished(self, result):
        self.processed_image = result
        self.display_image(self.processed_image, self.lbl_processed)
        self.lbl_processed_info.setText(
            f'最终尺寸: {self.processed_image.shape[1]}x{self.processed_image.shape[0]}'
        )
        self.btn_process.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText('处理完成')

    def save_image(self):
        if self.processed_image is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存图像', '',
            'PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp);;TIFF (*.tif)'
        )
        if file_path:
            cv2.imwrite(file_path, self.processed_image)
            self.lbl_status.setText('图像已保存')


def main():
    app = QApplication(sys.argv)
    window = MorphologyGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
