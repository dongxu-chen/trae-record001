import sys
import os
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QSlider,
    QScrollArea,
    QMessageBox,
    QStatusBar,
    QAction,
    QMenuBar,
    QGridLayout,
    QHeaderView,
    QAbstractItemView,
    QButtonGroup,
    QRadioButton,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor
from batch_processor import BatchProcessor


class ProcessingWorker(QThread):
    progress = pyqtSignal(int, int, str, dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, batch_proc, input_path, output_path, params, is_batch, pattern):
        super().__init__()
        self.batch_proc = batch_proc
        self.input_path = input_path
        self.output_path = output_path
        self.params = params
        self.is_batch = is_batch
        self.pattern = pattern

    def run(self):
        try:
            if self.is_batch:
                results = self.batch_proc.process_batch(
                    self.input_path,
                    self.output_path,
                    pattern=self.pattern,
                    params=self.params,
                    callback=self._callback,
                )
            else:
                result = self.batch_proc.process_single(
                    self.input_path, self.output_path, self.params
                )
                results = [result]
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def _callback(self, current, total, filepath, result):
        self.progress.emit(current, total, filepath, result)


class InteractiveSliceView(QWidget):
    brush_drawn = pyqtSignal()
    seed_added = pyqtSignal(int, int, int)

    def __init__(self, title="Axial", parent=None):
        super().__init__(parent)
        self.title = title
        self.volume = None
        self.overlay_volume = None
        self.current_slice = 0
        self.display_min = 0
        self.display_max = 1
        self.edit_mode = "view"
        self.brush_radius = 3
        self.brush_label = 1
        self.seeds = []
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.last_pos = None
        self.brush_path = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(256, 256)
        self.image_label.setStyleSheet("background-color: #1a1a2e; border: 1px solid #333;")
        self.image_label.setMouseTracking(True)
        layout.addWidget(self.image_label)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setMinimum(0)
        self.slice_slider.setMaximum(0)
        self.slice_slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slice_slider)
        self.slice_label = QLabel("0 / 0")
        self.slice_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.slice_label)
        self.mode_label = QLabel("Mode: View")
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setStyleSheet("color: #aaa;")
        layout.addWidget(self.mode_label)

    def set_volume(self, volume: np.ndarray):
        self.volume = volume
        self.seeds = []
        if volume is not None and volume.ndim >= 1:
            self.slice_slider.setMaximum(volume.shape[0] - 1)
            self.current_slice = volume.shape[0] // 2
            self.slice_slider.setValue(self.current_slice)
            self._update_display()
        else:
            self.slice_slider.setMaximum(0)
            self.image_label.clear()
            self.slice_label.setText("0 / 0")

    def set_overlay(self, overlay: np.ndarray):
        self.overlay_volume = overlay
        self._update_display()

    def set_edit_mode(self, mode: str):
        self.edit_mode = mode
        mode_names = {
            "view": "View",
            "draw": "Draw (Add Mask)",
            "erase": "Erase (Remove Mask)",
            "seed": "Seed Grow (Click to Add)",
        }
        self.mode_label.setText(f"Mode: {mode_names.get(mode, mode)}")

    def set_brush_radius(self, r: int):
        self.brush_radius = r

    def set_brush_label(self, lbl: int):
        self.brush_label = lbl

    def clear_seeds(self):
        self.seeds = []
        self._update_display()

    def _on_slider(self, value):
        self.current_slice = value
        self._update_display()

    def _update_display(self):
        if self.volume is None:
            return
        s = self.current_slice
        if s >= self.volume.shape[0]:
            return
        slice_data = self.volume[s]
        if slice_data.dtype != np.uint8:
            vmin = slice_data.min()
            vmax = slice_data.max()
            if vmax == vmin:
                slice_data = np.zeros_like(slice_data, dtype=np.uint8)
            else:
                slice_data = ((slice_data - vmin) / (vmax - vmin) * 200).astype(
                    np.uint8
                )
        else:
            slice_data = (slice_data.astype(np.float32) / np.maximum(1, slice_data.max()) * 200).astype(np.uint8)
        h, w = slice_data.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = slice_data
        rgb[:, :, 1] = slice_data
        rgb[:, :, 2] = slice_data
        if self.overlay_volume is not None and s < self.overlay_volume.shape[0]:
            overlay_slice = self.overlay_volume[s]
            labels = np.unique(overlay_slice)
            labels = labels[labels != 0]
            for lbl in labels:
                mask_bin = overlay_slice == lbl
                color = self._label_color(int(lbl))
                alpha = 0.5
                for c in range(3):
                    rgb[:, :, c] = np.where(
                        mask_bin,
                        (rgb[:, :, c] * (1 - alpha) + color[c] * alpha).astype(
                            np.uint8
                        ),
                        rgb[:, :, c],
                    )
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        if self.seeds:
            painter = QPainter(pixmap)
            pen = QPen(QColor(255, 0, 0), 3)
            painter.setPen(pen)
            for (z, y, x) in self.seeds:
                if z == s:
                    painter.drawEllipse(QPoint(x, y), 4, 4)
            painter.end()
        scaled = pixmap.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.slice_label.setText(f"{s} / {self.volume.shape[0] - 1}")

    def _img_to_pix(self, img_y: int, img_x: int) -> QPoint:
        if self.volume is None:
            return QPoint(img_x, img_y)
        s = self.current_slice
        h, w = self.volume.shape[1], self.volume.shape[2]
        label_size = self.image_label.size()
        scale_w = label_size.width() / w
        scale_h = label_size.height() / h
        scale = min(scale_w, scale_h)
        offset_x = (label_size.width() - w * scale) / 2
        offset_y = (label_size.height() - h * scale) / 2
        return QPoint(int(img_x * scale + offset_x), int(img_y * scale + offset_y))

    def _pix_to_img(self, pos: QPoint) -> Tuple[int, int]:
        if self.volume is None:
            return 0, 0
        s = self.current_slice
        h, w = self.volume.shape[1], self.volume.shape[2]
        label_size = self.image_label.size()
        scale_w = label_size.width() / w
        scale_h = label_size.height() / h
        scale = min(scale_w, scale_h)
        offset_x = (label_size.width() - w * scale) / 2
        offset_y = (label_size.height() - h * scale) / 2
        img_x = int((pos.x() - offset_x) / scale)
        img_y = int((pos.y() - offset_y) / scale)
        img_y = max(0, min(h - 1, img_y))
        img_x = max(0, min(w - 1, img_x))
        return img_y, img_x

    def mousePressEvent(self, event):
        if self.volume is None:
            return
        pos = self.image_label.mapFrom(self, event.pos())
        img_y, img_x = self._pix_to_img(pos)
        if self.edit_mode == "seed" and event.button() == Qt.LeftButton:
            self.seeds.append((self.current_slice, img_y, img_x))
            self.seed_added.emit(self.current_slice, img_y, img_x)
            self._update_display()
        elif self.edit_mode in ["draw", "erase"]:
            self.brush_path = [(img_y, img_x)]
            self._apply_brush(img_y, img_x)
        elif self.edit_mode == "view":
            self.last_pos = event.pos()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.volume is None:
            return
        if self.edit_mode in ["draw", "erase"]:
            pos = self.image_label.mapFrom(self, event.pos())
            img_y, img_x = self._pix_to_img(pos)
            if (img_y, img_x) not in self.brush_path:
                self.brush_path.append((img_y, img_x))
                self._apply_brush(img_y, img_x)
        elif self.edit_mode == "view" and self.last_pos:
            super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.edit_mode in ["draw", "erase"] and self.brush_path:
            self.brush_drawn.emit()
            self.brush_path = []
        elif self.edit_mode == "view":
            self.last_pos = None
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def _apply_brush(self, y: int, x: int):
        if self.overlay_volume is None:
            self.overlay_volume = np.zeros_like(self.volume, dtype=np.uint8)
        if self.current_slice >= self.overlay_volume.shape[0]:
            return
        r = self.brush_radius
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dy * dy + dx * dx <= r * r:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.overlay_volume.shape[1] and 0 <= nx < self.overlay_volume.shape[2]:
                        if self.edit_mode == "draw":
                            self.overlay_volume[self.current_slice, ny, nx] = self.brush_label
                        elif self.edit_mode == "erase":
                            self.overlay_volume[self.current_slice, ny, nx] = 0
        self._update_display()

    @staticmethod
    def _label_color(label: int):
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
            (255, 128, 0),
            (128, 0, 255),
            (0, 128, 255),
            (255, 128, 128),
            (128, 255, 128),
            (128, 128, 255),
            (200, 200, 0),
            (200, 0, 200),
            (0, 200, 200),
        ]
        return colors[(label - 1) % len(colors)]


class OverlaySliceView(QWidget):
    def __init__(self, title="Overlay", parent=None):
        super().__init__(parent)
        self.title = title
        self.base_volume = None
        self.mask_volume = None
        self.current_slice = 0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(256, 256)
        self.image_label.setStyleSheet("background-color: #1a1a2e; border: 1px solid #333;")
        layout.addWidget(self.image_label)
        self.slice_slider = QSlider(Qt.Horizontal)
        self.slice_slider.setMinimum(0)
        self.slice_slider.setMaximum(0)
        self.slice_slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slice_slider)
        self.slice_label = QLabel("0 / 0")
        self.slice_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.slice_label)

    def set_volumes(self, base: np.ndarray, mask: np.ndarray):
        self.base_volume = base
        self.mask_volume = mask
        if base is not None and base.ndim >= 1:
            self.slice_slider.setMaximum(base.shape[0] - 1)
            self.current_slice = base.shape[0] // 2
            self.slice_slider.setValue(self.current_slice)
            self._update_display()

    def _on_slider(self, value):
        self.current_slice = value
        self._update_display()

    def _update_display(self):
        if self.base_volume is None or self.mask_volume is None:
            return
        s = self.current_slice
        base_slice = self.base_volume[s]
        mask_slice = self.mask_volume[s]
        if base_slice.dtype != np.uint8:
            vmin, vmax = base_slice.min(), base_slice.max()
            if vmax == vmin:
                base_norm = np.zeros_like(base_slice, dtype=np.float32)
            else:
                base_norm = (base_slice - vmin) / (vmax - vmin)
        else:
            base_norm = base_slice.astype(np.float32) / 255.0
        rgb = np.zeros((*base_norm.shape, 3), dtype=np.uint8)
        rgb[:, :, 0] = (base_norm * 200).astype(np.uint8)
        rgb[:, :, 1] = (base_norm * 200).astype(np.uint8)
        rgb[:, :, 2] = (base_norm * 200).astype(np.uint8)
        labels = np.unique(mask_slice)
        labels = labels[labels != 0]
        for lbl in labels:
            color = self._label_color(int(lbl))
            mask_bin = mask_slice == lbl
            alpha = 0.4
            for c in range(3):
                rgb[:, :, c] = np.where(
                    mask_bin,
                    (rgb[:, :, c] * (1 - alpha) + color[c] * alpha).astype(np.uint8),
                    rgb[:, :, c],
                )
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.slice_label.setText(f"{s} / {self.base_volume.shape[0] - 1}")

    @staticmethod
    def _label_color(label: int):
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
            (255, 128, 0),
            (128, 0, 255),
            (0, 128, 255),
            (255, 128, 128),
            (128, 255, 128),
            (128, 128, 255),
            (200, 200, 0),
            (200, 0, 200),
            (0, 200, 200),
        ]
        return colors[(label - 1) % len(colors)]


class ParamPanel(QWidget):
    params_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(6)

        cca_group = QGroupBox("Connected Component Analysis")
        cca_layout = QGridLayout()
        self.cca_enabled = QCheckBox("Enable")
        self.cca_enabled.setChecked(True)
        cca_layout.addWidget(self.cca_enabled, 0, 0, 1, 2)
        cca_layout.addWidget(QLabel("Min Volume (base):"), 1, 0)
        self.cca_min_volume = QSpinBox()
        self.cca_min_volume.setRange(1, 100000)
        self.cca_min_volume.setValue(100)
        cca_layout.addWidget(self.cca_min_volume, 1, 1)
        self.cca_keep_largest = QCheckBox("Keep Largest Only")
        self.cca_keep_largest.setChecked(False)
        cca_layout.addWidget(self.cca_keep_largest, 2, 0, 1, 2)
        self.cca_adaptive = QCheckBox("Adaptive (small organ lenient)")
        self.cca_adaptive.setChecked(True)
        cca_layout.addWidget(self.cca_adaptive, 3, 0, 1, 2)
        cca_layout.addWidget(QLabel("Volume Ratio:"), 4, 0)
        self.cca_volume_ratio = QDoubleSpinBox()
        self.cca_volume_ratio.setRange(0.001, 1.0)
        self.cca_volume_ratio.setSingleStep(0.01)
        self.cca_volume_ratio.setValue(0.05)
        self.cca_volume_ratio.setDecimals(3)
        cca_layout.addWidget(self.cca_volume_ratio, 4, 1)
        cca_group.setLayout(cca_layout)
        layout.addWidget(cca_group)

        hole_group = QGroupBox("Hole Filling")
        hole_layout = QGridLayout()
        self.hole_fill_enabled = QCheckBox("Enable")
        self.hole_fill_enabled.setChecked(True)
        hole_layout.addWidget(self.hole_fill_enabled, 0, 0, 1, 2)
        self.hole_fill_2d = QCheckBox("Fill 2D Slices")
        self.hole_fill_2d.setChecked(True)
        hole_layout.addWidget(self.hole_fill_2d, 1, 0, 1, 2)
        self.hole_fill_3d = QCheckBox("Fill 3D Volume")
        self.hole_fill_3d.setChecked(False)
        hole_layout.addWidget(self.hole_fill_3d, 2, 0, 1, 2)
        self.hole_fill_multiseed = QCheckBox("Multi-Seed Traversal")
        self.hole_fill_multiseed.setChecked(True)
        hole_layout.addWidget(self.hole_fill_multiseed, 3, 0, 1, 2)
        hole_layout.addWidget(QLabel("Seed Spacing:"), 4, 0)
        self.hole_fill_seed_spacing = QSpinBox()
        self.hole_fill_seed_spacing.setRange(2, 50)
        self.hole_fill_seed_spacing.setValue(8)
        hole_layout.addWidget(self.hole_fill_seed_spacing, 4, 1)
        hole_layout.addWidget(QLabel("Enclosure Thresh:"), 5, 0)
        self.hole_fill_enclosure_thresh = QDoubleSpinBox()
        self.hole_fill_enclosure_thresh.setRange(0.0, 1.0)
        self.hole_fill_enclosure_thresh.setSingleStep(0.05)
        self.hole_fill_enclosure_thresh.setValue(0.5)
        self.hole_fill_enclosure_thresh.setDecimals(2)
        hole_layout.addWidget(self.hole_fill_enclosure_thresh, 5, 1)
        hole_group.setLayout(hole_layout)
        layout.addWidget(hole_group)

        morph_group = QGroupBox("Morphological Operation")
        morph_layout = QGridLayout()
        morph_layout.addWidget(QLabel("Operation:"), 0, 0)
        self.morph_operation = QComboBox()
        self.morph_operation.addItems(["None", "close", "open", "dilate", "erode"])
        self.morph_operation.setCurrentIndex(0)
        morph_layout.addWidget(self.morph_operation, 0, 1)
        morph_layout.addWidget(QLabel("Radius:"), 1, 0)
        self.morph_radius = QSpinBox()
        self.morph_radius.setRange(1, 10)
        self.morph_radius.setValue(1)
        morph_layout.addWidget(self.morph_radius, 1, 1)
        morph_group.setLayout(morph_layout)
        layout.addWidget(morph_group)

        smooth_group = QGroupBox("Edge Smoothing")
        smooth_layout = QGridLayout()
        self.smooth_enabled = QCheckBox("Enable")
        self.smooth_enabled.setChecked(True)
        smooth_layout.addWidget(self.smooth_enabled, 0, 0, 1, 2)
        smooth_layout.addWidget(QLabel("Method:"), 1, 0)
        self.smooth_method = QComboBox()
        self.smooth_method.addItems(["gaussian", "median", "sitk_curvature"])
        smooth_layout.addWidget(self.smooth_method, 1, 1)
        smooth_layout.addWidget(QLabel("Sigma:"), 2, 0)
        self.smooth_sigma = QDoubleSpinBox()
        self.smooth_sigma.setRange(0.1, 5.0)
        self.smooth_sigma.setSingleStep(0.1)
        self.smooth_sigma.setValue(0.5)
        smooth_layout.addWidget(self.smooth_sigma, 2, 1)
        smooth_layout.addWidget(QLabel("Iterations (base):"), 3, 0)
        self.smooth_iterations = QSpinBox()
        self.smooth_iterations.setRange(1, 10)
        self.smooth_iterations.setValue(1)
        smooth_layout.addWidget(self.smooth_iterations, 3, 1)
        self.smooth_adaptive = QCheckBox("Adaptive (large organ more)")
        self.smooth_adaptive.setChecked(True)
        smooth_layout.addWidget(self.smooth_adaptive, 4, 0, 1, 2)
        smooth_layout.addWidget(QLabel("Ref Surface Area:"), 5, 0)
        self.smooth_ref_surface = QDoubleSpinBox()
        self.smooth_ref_surface.setRange(10.0, 100000.0)
        self.smooth_ref_surface.setSingleStep(100.0)
        self.smooth_ref_surface.setValue(1000.0)
        self.smooth_ref_surface.setDecimals(0)
        smooth_layout.addWidget(self.smooth_ref_surface, 5, 1)
        smooth_group.setLayout(smooth_layout)
        layout.addWidget(smooth_group)

        layout.addStretch()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        for cb in [
            self.cca_enabled,
            self.cca_keep_largest,
            self.cca_adaptive,
            self.hole_fill_enabled,
            self.hole_fill_2d,
            self.hole_fill_3d,
            self.hole_fill_multiseed,
            self.smooth_enabled,
            self.smooth_adaptive,
        ]:
            cb.stateChanged.connect(self._emit_params)
        for sp in [
            self.cca_min_volume,
            self.hole_fill_seed_spacing,
            self.morph_radius,
            self.smooth_iterations,
        ]:
            sp.valueChanged.connect(self._emit_params)
        for dsp in [
            self.cca_volume_ratio,
            self.hole_fill_enclosure_thresh,
            self.smooth_sigma,
            self.smooth_ref_surface,
        ]:
            dsp.valueChanged.connect(self._emit_params)
        for combo in [self.morph_operation, self.smooth_method]:
            combo.currentIndexChanged.connect(self._emit_params)

    def get_params(self) -> dict:
        morph_op = self.morph_operation.currentText()
        if morph_op == "None":
            morph_op = None
        return {
            "cca_enabled": self.cca_enabled.isChecked(),
            "cca_min_volume": self.cca_min_volume.value(),
            "cca_keep_largest": self.cca_keep_largest.isChecked(),
            "cca_adaptive": self.cca_adaptive.isChecked(),
            "cca_volume_ratio": self.cca_volume_ratio.value(),
            "hole_fill_enabled": self.hole_fill_enabled.isChecked(),
            "hole_fill_2d": self.hole_fill_2d.isChecked(),
            "hole_fill_3d": self.hole_fill_3d.isChecked(),
            "hole_fill_multiseed": self.hole_fill_multiseed.isChecked(),
            "hole_fill_seed_spacing": self.hole_fill_seed_spacing.value(),
            "hole_fill_enclosure_thresh": self.hole_fill_enclosure_thresh.value(),
            "morph_operation": morph_op,
            "morph_radius": self.morph_radius.value(),
            "smooth_enabled": self.smooth_enabled.isChecked(),
            "smooth_method": self.smooth_method.currentText(),
            "smooth_sigma": self.smooth_sigma.value(),
            "smooth_iterations": self.smooth_iterations.value(),
            "smooth_adaptive": self.smooth_adaptive.isChecked(),
            "smooth_ref_surface": self.smooth_ref_surface.value(),
        }

    def set_params(self, params: dict):
        self.cca_enabled.setChecked(params.get("cca_enabled", True))
        self.cca_min_volume.setValue(params.get("cca_min_volume", 100))
        self.cca_keep_largest.setChecked(params.get("cca_keep_largest", False))
        self.cca_adaptive.setChecked(params.get("cca_adaptive", True))
        self.cca_volume_ratio.setValue(params.get("cca_volume_ratio", 0.05))
        self.hole_fill_enabled.setChecked(params.get("hole_fill_enabled", True))
        self.hole_fill_2d.setChecked(params.get("hole_fill_2d", True))
        self.hole_fill_3d.setChecked(params.get("hole_fill_3d", False))
        self.hole_fill_multiseed.setChecked(params.get("hole_fill_multiseed", True))
        self.hole_fill_seed_spacing.setValue(params.get("hole_fill_seed_spacing", 8))
        self.hole_fill_enclosure_thresh.setValue(
            params.get("hole_fill_enclosure_thresh", 0.5)
        )
        morph_op = params.get("morph_operation", "None")
        if morph_op is None:
            morph_op = "None"
        idx = self.morph_operation.findText(morph_op)
        if idx >= 0:
            self.morph_operation.setCurrentIndex(idx)
        self.morph_radius.setValue(params.get("morph_radius", 1))
        self.smooth_enabled.setChecked(params.get("smooth_enabled", True))
        idx2 = self.smooth_method.findText(params.get("smooth_method", "gaussian"))
        if idx2 >= 0:
            self.smooth_method.setCurrentIndex(idx2)
        self.smooth_sigma.setValue(params.get("smooth_sigma", 0.5))
        self.smooth_iterations.setValue(params.get("smooth_iterations", 1))
        self.smooth_adaptive.setChecked(params.get("smooth_adaptive", True))
        self.smooth_ref_surface.setValue(params.get("smooth_ref_surface", 1000.0))

    def _emit_params(self):
        self.params_changed.emit(self.get_params())


class EditToolPanel(QWidget):
    mode_changed = pyqtSignal(str)
    brush_changed = pyqtSignal(int, int)
    clear_seeds = pyqtSignal()
    apply_region_grow = pyqtSignal()
    save_edits = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        mode_group = QGroupBox("Edit Mode")
        mode_layout = QVBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.radio_view = QRadioButton("View (Browse only)")
        self.radio_view.setChecked(True)
        self.radio_view.clicked.connect(lambda: self.mode_changed.emit("view"))
        self.mode_group.addButton(self.radio_view, 0)
        mode_layout.addWidget(self.radio_view)
        self.radio_draw = QRadioButton("Draw (Add to mask)")
        self.radio_draw.clicked.connect(lambda: self.mode_changed.emit("draw"))
        self.mode_group.addButton(self.radio_draw, 1)
        mode_layout.addWidget(self.radio_draw)
        self.radio_erase = QRadioButton("Erase (Remove from mask)")
        self.radio_erase.clicked.connect(lambda: self.mode_changed.emit("erase"))
        self.mode_group.addButton(self.radio_erase, 2)
        mode_layout.addWidget(self.radio_erase)
        self.radio_seed = QRadioButton("Seed Growing (Click to add seeds)")
        self.radio_seed.clicked.connect(lambda: self.mode_changed.emit("seed"))
        self.mode_group.addButton(self.radio_seed, 3)
        mode_layout.addWidget(self.radio_seed)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        brush_group = QGroupBox("Brush Settings")
        brush_layout = QGridLayout()
        brush_layout.addWidget(QLabel("Radius:"), 0, 0)
        self.brush_radius = QSpinBox()
        self.brush_radius.setRange(1, 20)
        self.brush_radius.setValue(3)
        self.brush_radius.valueChanged.connect(self._on_brush_changed)
        brush_layout.addWidget(self.brush_radius, 0, 1)
        brush_layout.addWidget(QLabel("Label:"), 1, 0)
        self.brush_label = QSpinBox()
        self.brush_label.setRange(1, 255)
        self.brush_label.setValue(1)
        self.brush_label.valueChanged.connect(self._on_brush_changed)
        brush_layout.addWidget(self.brush_label, 1, 1)
        brush_group.setLayout(brush_layout)
        layout.addWidget(brush_group)

        seed_group = QGroupBox("Region Growing")
        seed_layout = QGridLayout()
        seed_layout.addWidget(QLabel("Lower:"), 0, 0)
        self.grow_lower = QDoubleSpinBox()
        self.grow_lower.setRange(-1000, 5000)
        self.grow_lower.setValue(-100)
        self.grow_lower.setDecimals(0)
        seed_layout.addWidget(self.grow_lower, 0, 1)
        seed_layout.addWidget(QLabel("Upper:"), 1, 0)
        self.grow_upper = QDoubleSpinBox()
        self.grow_upper.setRange(-1000, 5000)
        self.grow_upper.setValue(200)
        self.grow_upper.setDecimals(0)
        seed_layout.addWidget(self.grow_upper, 1, 1)
        seed_layout.addWidget(QLabel("Connectivity:"), 2, 0)
        self.grow_connect = QComboBox()
        self.grow_connect.addItems(["6-connect", "18-connect"])
        seed_layout.addWidget(self.grow_connect, 2, 1)
        self.btn_clear_seeds = QPushButton("Clear Seeds")
        self.btn_clear_seeds.clicked.connect(self.clear_seeds.emit)
        seed_layout.addWidget(self.btn_clear_seeds, 3, 0)
        self.btn_apply_grow = QPushButton("Apply Region Grow")
        self.btn_apply_grow.clicked.connect(self.apply_region_grow.emit)
        self.btn_apply_grow.setStyleSheet("QPushButton{background:#FF9800;color:white;font-weight:bold;}")
        seed_layout.addWidget(self.btn_apply_grow, 3, 1)
        seed_group.setLayout(seed_layout)
        layout.addWidget(seed_group)

        self.btn_save_edits = QPushButton("Save Edits to Volume")
        self.btn_save_edits.setStyleSheet("QPushButton{background:#E91E63;color:white;font-weight:bold;padding:8px;}")
        self.btn_save_edits.clicked.connect(self.save_edits.emit)
        layout.addWidget(self.btn_save_edits)

        layout.addStretch()

    def get_grow_params(self):
        conn = 6 if self.grow_connect.currentIndex() == 0 else 18
        return {
            "lower": self.grow_lower.value(),
            "upper": self.grow_upper.value(),
            "connectivity": conn,
        }

    def _on_brush_changed(self):
        self.brush_changed.emit(self.brush_radius.value(), self.brush_label.value())


class MetricsPanel(QWidget):
    compute_metrics = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gt_path = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        io_group = QGroupBox("Ground Truth")
        io_layout = QVBoxLayout()
        self.gt_label = QLabel("GT: (not loaded)")
        self.gt_label.setWordWrap(True)
        io_layout.addWidget(self.gt_label)
        self.btn_browse_gt = QPushButton("Load Ground Truth")
        self.btn_browse_gt.clicked.connect(self._browse_gt)
        io_layout.addWidget(self.btn_browse_gt)
        io_group.setLayout(io_layout)
        layout.addWidget(io_group)

        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(7)
        self.metrics_table.setHorizontalHeaderLabels(
            ["Label", "Organ", "Dice", "HD95", "HD100", "Pred Vol", "GT Vol"]
        )
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.metrics_table, 1)

        self.btn_compute = QPushButton("Compute Metrics")
        self.btn_compute.setStyleSheet("QPushButton{background:#9C27B0;color:white;font-weight:bold;padding:8px;}")
        self.btn_compute.clicked.connect(self.compute_metrics.emit)
        layout.addWidget(self.btn_compute)

    def _browse_gt(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Ground Truth",
            "",
            "Medical Images (*.nii.gz *.nii *.mha *.mhd *.nrrd);;All Files (*)",
        )
        if filepath:
            self.gt_path = filepath
            self.gt_label.setText(f"GT: {os.path.basename(filepath)}")

    def set_metrics(self, metrics: dict):
        from batch_processor import BatchProcessor

        self.metrics_table.setRowCount(len(metrics))
        for i, (label, m) in enumerate(metrics.items()):
            organ_name = BatchProcessor.ORGAN_NAMES.get(label, f"Organ_{label}")
            self.metrics_table.setItem(i, 0, QTableWidgetItem(str(label)))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(organ_name))
            self.metrics_table.setItem(i, 2, QTableWidgetItem(str(m.get("dice", ""))))
            self.metrics_table.setItem(i, 3, QTableWidgetItem(str(m.get("hd95", ""))))
            self.metrics_table.setItem(i, 4, QTableWidgetItem(str(m.get("hd100", ""))))
            self.metrics_table.setItem(
                i, 5, QTableWidgetItem(str(m.get("pred_volume", "")))
            )
            self.metrics_table.setItem(
                i, 6, QTableWidgetItem(str(m.get("gt_volume", "")))
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Medical Image Segmentation Post-Processor")
        self.setMinimumSize(1400, 900)
        self.batch_proc = BatchProcessor()
        self.input_path = ""
        self.output_path = ""
        self.original_mask = None
        self.processed_mask = None
        self.edited_mask = None
        self.raw_image = None
        self.gt_mask = None
        self.spacing = None
        self.worker = None
        self._init_ui()
        self._init_menu()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_splitter = QSplitter(Qt.Vertical)
        self.tab_widget = QTabWidget()
        self.original_view = InteractiveSliceView("Original")
        self.processed_view = InteractiveSliceView("Processed")
        self.overlay_view = OverlaySliceView("Overlay")
        self.edit_view = InteractiveSliceView("Edit Mode")
        self.edit_view.brush_drawn.connect(self._on_brush_drawn)
        self.edit_view.seed_added.connect(self._on_seed_added)
        self.tab_widget.addTab(self.original_view, "Original")
        self.tab_widget.addTab(self.processed_view, "Processed")
        self.tab_widget.addTab(self.overlay_view, "Overlay")
        self.tab_widget.addTab(self.edit_view, "Edit")
        left_splitter.addWidget(self.tab_widget)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(6)
        self.stats_table.setHorizontalHeaderLabels(
            ["Label", "Organ", "Orig Vol", "Proc Vol", "Changed", "Dice"]
        )
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        left_splitter.addWidget(self.stats_table)
        left_splitter.setSizes([500, 150])

        mid_splitter = QSplitter(Qt.Horizontal)
        mid_splitter.addWidget(left_splitter)

        self.metrics_panel = MetricsPanel()
        self.metrics_panel.compute_metrics.connect(self._compute_metrics)
        mid_splitter.addWidget(self.metrics_panel)
        mid_splitter.setSizes([600, 350])

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(6)

        io_group = QGroupBox("File I/O")
        io_layout = QVBoxLayout()
        input_row = QHBoxLayout()
        self.input_label = QLabel("Input: (not selected)")
        self.input_label.setWordWrap(True)
        input_row.addWidget(self.input_label)
        self.btn_browse_input = QPushButton("Browse File")
        self.btn_browse_input.clicked.connect(self._browse_input)
        input_row.addWidget(self.btn_browse_input)
        io_layout.addLayout(input_row)
        self.btn_browse_input_dir = QPushButton("Browse Input Directory (Batch)")
        self.btn_browse_input_dir.clicked.connect(self._browse_input_dir)
        io_layout.addWidget(self.btn_browse_input_dir)
        output_row = QHBoxLayout()
        self.output_label = QLabel("Output: (not selected)")
        self.output_label.setWordWrap(True)
        output_row.addWidget(self.output_label)
        self.btn_browse_output = QPushButton("Browse Output")
        self.btn_browse_output.clicked.connect(self._browse_output)
        output_row.addWidget(self.btn_browse_output)
        io_layout.addLayout(output_row)
        io_group.setLayout(io_layout)
        right_layout.addWidget(io_group)

        self.right_tabs = QTabWidget()
        self.param_panel = ParamPanel()
        self.param_panel.params_changed.connect(self._on_params_changed)
        self.right_tabs.addTab(self.param_panel, "Post-Processing")
        self.edit_panel = EditToolPanel()
        self.edit_panel.mode_changed.connect(self._on_edit_mode_changed)
        self.edit_panel.brush_changed.connect(self._on_brush_changed)
        self.edit_panel.clear_seeds.connect(self._clear_seeds)
        self.edit_panel.apply_region_grow.connect(self._apply_region_grow)
        self.edit_panel.save_edits.connect(self._save_edits)
        self.right_tabs.addTab(self.edit_panel, "Edit / Seed Grow")
        right_layout.addWidget(self.right_tabs, 1)

        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Apply (Single)")
        self.btn_apply.setStyleSheet(
            "QPushButton{background:#2196F3;color:white;font-weight:bold;padding:8px;}"
            "QPushButton:hover{background:#1976D2;}"
        )
        self.btn_apply.clicked.connect(self._apply_single)
        btn_layout.addWidget(self.btn_apply)
        self.btn_batch = QPushButton("Apply (Batch)")
        self.btn_batch.setStyleSheet(
            "QPushButton{background:#4CAF50;color:white;font-weight:bold;padding:8px;}"
            "QPushButton:hover{background:#388E3C;}"
        )
        self.btn_batch.clicked.connect(self._apply_batch)
        btn_layout.addWidget(self.btn_batch)
        right_layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.btn_save_params = QPushButton("Save Parameters")
        self.btn_save_params.clicked.connect(self._save_params)
        self.btn_load_params = QPushButton("Load Parameters")
        self.btn_load_params.clicked.connect(self._load_params)
        param_io_layout = QHBoxLayout()
        param_io_layout.addWidget(self.btn_save_params)
        param_io_layout.addWidget(self.btn_load_params)
        right_layout.addLayout(param_io_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(mid_splitter)
        splitter.addWidget(right_panel)
        splitter.setSizes([950, 350])
        main_layout.addWidget(splitter)

        self.statusBar().showMessage("Ready")

    def _init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Segmentation", self)
        open_action.triggered.connect(self._browse_input)
        file_menu.addAction(open_action)
        save_action = QAction("Save Result", self)
        save_action.triggered.connect(self._browse_output)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _browse_input(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Segmentation Mask",
            "",
            "Medical Images (*.nii.gz *.nii *.mha *.mhd *.nrrd);;All Files (*)",
        )
        if filepath:
            self.input_path = filepath
            self.input_label.setText(f"Input: {os.path.basename(filepath)}")
            self._load_and_preview(filepath)

    def _browse_input_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if dirpath:
            self.input_path = dirpath
            self.input_label.setText(f"Input Dir: {dirpath}")

    def _browse_output(self):
        if self.input_path and os.path.isdir(self.input_path):
            dirpath = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if dirpath:
                self.output_path = dirpath
                self.output_label.setText(f"Output Dir: {dirpath}")
        else:
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Processed Mask",
                "",
                "Medical Images (*.nii.gz *.nii *.mha *.mhd *.nrrd);;All Files (*)",
            )
            if filepath:
                self.output_path = filepath
                self.output_label.setText(f"Output: {os.path.basename(filepath)}")

    def _load_and_preview(self, filepath: str):
        try:
            arr, spacing = self.batch_proc.load_mask(filepath)
            self.original_mask = arr
            self.processed_mask = None
            self.edited_mask = None
            self.spacing = spacing
            self.raw_image = arr.astype(np.float32)
            self.original_view.set_volume(arr)
            self.processed_view.set_volume(None)
            self.edit_view.set_volume(arr)
            self.edit_view.set_overlay(arr.copy())
            self.overlay_view.set_volumes(arr, arr)
            labels = np.unique(arr)
            labels = labels[labels != 0]
            self.statusBar().showMessage(
                f"Loaded: {os.path.basename(filepath)} | Shape: {arr.shape} | "
                f"Labels: {list(labels.astype(int))} | Spacing: {spacing}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    def _on_params_changed(self, params: dict):
        self.batch_proc.set_global_params(params)

    def _on_edit_mode_changed(self, mode: str):
        self.edit_view.set_edit_mode(mode)
        self.right_tabs.setCurrentIndex(1)

    def _on_brush_changed(self, radius: int, label: int):
        self.edit_view.set_brush_radius(radius)
        self.edit_view.set_brush_label(label)

    def _on_brush_drawn(self):
        pass

    def _on_seed_added(self, z: int, y: int, x: int):
        self.statusBar().showMessage(f"Seed added at ({z}, {y}, {x})")

    def _clear_seeds(self):
        self.edit_view.clear_seeds()
        self.statusBar().showMessage("Seeds cleared")

    def _apply_region_grow(self):
        if self.raw_image is None or not self.edit_view.seeds:
            QMessageBox.warning(self, "Warning", "Please load image and add seeds first.")
            return
        params = self.edit_panel.get_grow_params()
        from postprocessor import PostProcessor

        pp = PostProcessor()
        grown = pp.region_grow_3d(
            self.raw_image,
            self.edit_view.seeds,
            lower_thresh=params["lower"],
            upper_thresh=params["upper"],
            connectivity=params["connectivity"],
        )
        if self.edit_view.overlay_volume is None:
            self.edit_view.overlay_volume = grown
        else:
            self.edit_view.overlay_volume = np.maximum(self.edit_view.overlay_volume, grown)
        self.edit_view._update_display()
        vol = int(np.sum(grown > 0))
        self.statusBar().showMessage(f"Region grown: {vol} voxels")

    def _save_edits(self):
        if self.edit_view.overlay_volume is not None:
            self.edited_mask = self.edit_view.overlay_volume.copy()
            if self.processed_mask is None:
                self.processed_mask = self.edited_mask.copy()
            self.processed_view.set_volume(self.processed_mask)
            self.overlay_view.set_volumes(self.original_mask, self.processed_mask)
            self.statusBar().showMessage("Edits saved")
            QMessageBox.information(self, "Info", "Edits saved to processed mask!")

    def _compute_metrics(self):
        if self.processed_mask is None:
            QMessageBox.warning(self, "Warning", "Please apply post-processing first.")
            return
        if not self.metrics_panel.gt_path:
            QMessageBox.warning(self, "Warning", "Please load Ground Truth first.")
            return
        try:
            gt_arr, _ = self.batch_proc.load_mask(self.metrics_panel.gt_path)
            self.gt_mask = gt_arr
            from postprocessor import PostProcessor

            pp = PostProcessor()
            metrics = pp.compute_metrics(self.processed_mask, gt_arr, self.spacing)
            self.metrics_panel.set_metrics(metrics)
            self.statusBar().showMessage("Metrics computed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to compute metrics:\n{e}")

    def _apply_single(self):
        if not self.input_path or not os.path.isfile(self.input_path):
            QMessageBox.warning(self, "Warning", "Please select an input file first.")
            return
        if not self.output_path:
            base, ext = os.path.splitext(self.input_path)
            if ext == ".gz":
                base2, ext2 = os.path.splitext(base)
                ext = ext2 + ext
                base = base2
            self.output_path = base + "_processed" + ext
            self.output_label.setText(f"Output: {os.path.basename(self.output_path)}")
        params = self.param_panel.get_params()
        self._start_processing(params, is_batch=False)

    def _apply_batch(self):
        if not self.input_path or not os.path.isdir(self.input_path):
            QMessageBox.warning(
                self, "Warning", "Please select an input directory for batch processing."
            )
            return
        if not self.output_path:
            self.output_path = QFileDialog.getExistingDirectory(
                self, "Select Output Directory"
            )
            if not self.output_path:
                return
            self.output_label.setText(f"Output Dir: {self.output_path}")
        params = self.param_panel.get_params()
        self._start_processing(params, is_batch=True)

    def _start_processing(self, params: dict, is_batch: bool):
        self.btn_apply.setEnabled(False)
        self.btn_batch.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage("Processing...")
        self.worker = ProcessingWorker(
            self.batch_proc,
            self.input_path,
            self.output_path,
            params,
            is_batch,
            "*.nii.gz",
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, filepath, result):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"Processing [{current}/{total}]: {os.path.basename(filepath)}")

    def _on_finished(self, results):
        self.btn_apply.setEnabled(True)
        self.btn_batch.setEnabled(True)
        self.progress_bar.setVisible(False)
        if results and not results[0].get("error"):
            if not isinstance(self.input_path, str) or not os.path.isdir(self.input_path):
                try:
                    arr, spacing = self.batch_proc.load_mask(self.output_path)
                    self.processed_mask = arr
                    self.processed_view.set_volume(arr)
                    self.edit_view.set_overlay(arr.copy())
                    if self.original_mask is not None:
                        self.overlay_view.set_volumes(self.original_mask, arr)
                except Exception:
                    pass
            stats = []
            for r in results:
                if "labels" in r:
                    stats.extend(r["labels"])
            self._update_stats_table(stats)
            self.statusBar().showMessage(f"Processing complete. {len(results)} file(s) processed.")
        else:
            self.statusBar().showMessage("Processing completed with errors.")

    def _on_error(self, err_msg):
        self.btn_apply.setEnabled(True)
        self.btn_batch.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Processing failed:\n{err_msg}")
        self.statusBar().showMessage("Processing failed.")

    def _update_stats_table(self, stats: list):
        self.stats_table.setRowCount(len(stats))
        for i, s in enumerate(stats):
            self.stats_table.setItem(i, 0, QTableWidgetItem(str(s.get("label", ""))))
            self.stats_table.setItem(i, 1, QTableWidgetItem(s.get("name", "")))
            self.stats_table.setItem(
                i, 2, QTableWidgetItem(str(s.get("original_volume", "")))
            )
            self.stats_table.setItem(
                i, 3, QTableWidgetItem(str(s.get("processed_volume", "")))
            )
            self.stats_table.setItem(
                i, 4, QTableWidgetItem(str(s.get("changed_voxels", "")))
            )
            self.stats_table.setItem(i, 5, QTableWidgetItem(str(s.get("dice", ""))))

    def _save_params(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Parameters", "", "JSON Files (*.json)"
        )
        if filepath:
            self.batch_proc.default_params = self.param_panel.get_params()
            self.batch_proc.save_params(filepath)
            self.statusBar().showMessage(f"Parameters saved to {filepath}")

    def _load_params(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Parameters", "", "JSON Files (*.json)"
        )
        if filepath:
            self.batch_proc.load_params(filepath)
            self.param_panel.set_params(self.batch_proc.default_params)
            self.statusBar().showMessage(f"Parameters loaded from {filepath}")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About",
            "3D Medical Image Segmentation Post-Processor\n\n"
            "Features:\n"
            "  - Connected Component Analysis (adaptive)\n"
            "  - Hole Filling (multi-seed traversal)\n"
            "  - Edge Smoothing (adaptive iterations)\n"
            "  - Morphological Operations\n"
            "  - Multi-organ Support\n"
            "  - Batch Processing\n"
            "  - Interactive Brush / Erase Tool\n"
            "  - Region Growing (semi-automatic)\n"
            "  - Quality Metrics (Dice / Hausdorff)\n\n"
            "Built with SimpleITK + NumPy + SciPy + PyQt5",
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    from PyQt5.QtGui import QPalette, QColor

    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
