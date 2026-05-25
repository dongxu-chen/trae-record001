"""PyQt5 GUI for the camera calibration tool.

Launch it with::

    python -m camera_calib.gui
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

import cv2
import numpy as np

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyQt5 is required to run the GUI. Install it with:\n"
        "    pip install PyQt5"
    ) from exc

from .calibrator import (
    CameraCalibrator,
    CalibrationResult,
    PatternType,
    StereoCalibrator,
    StereoCalibrationResult,
    SUPPORTED_EXT,
)
from .visualizer import (
    bgr_to_rgb,
    build_undistort_preview,
    plot_reprojection_errors,
)


IMAGE_EXTS = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXT))


def _np_to_qpixmap(rgb: np.ndarray, max_size: int = 900) -> QtGui.QPixmap:
    """Convert an RGB numpy array to a ``QPixmap``, scaling if necessary."""
    h, w = rgb.shape[:2]
    scale = 1.0
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    if scale != 1.0:
        rgb = cv2.resize(rgb, (new_w, new_h))
    qimg = QtGui.QImage(
        rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3,
        QtGui.QImage.Format_RGB888,
    )
    return QtGui.QPixmap.fromImage(qimg.copy())


class CalibrationGUI(QtWidgets.QMainWindow):
    """Main window of the calibration tool."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Camera Calibration Tool")
        self.resize(1280, 800)

        self._calibrator: Optional[CameraCalibrator] = None
        self._result: Optional[CalibrationResult] = None

        self._build_ui()
        self._reset_state()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)

        # --- Left: controls & image list --------------------------------
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left.setFixedWidth(360)

        grp_pattern = QtWidgets.QGroupBox("Calibration pattern")
        form = QtWidgets.QFormLayout(grp_pattern)
        self.cmb_pattern_type = QtWidgets.QComboBox()
        self.cmb_pattern_type.addItem("Chessboard", PatternType.CHESSBOARD.value)
        self.cmb_pattern_type.addItem("Symmetric circles", PatternType.CIRCLES_SYMMETRIC.value)
        self.cmb_pattern_type.addItem("Asymmetric circles", PatternType.CIRCLES_ASYMMETRIC.value)
        self.sp_corners_x = QtWidgets.QSpinBox()
        self.sp_corners_x.setRange(3, 30)
        self.sp_corners_x.setValue(9)
        self.sp_corners_y = QtWidgets.QSpinBox()
        self.sp_corners_y.setRange(3, 30)
        self.sp_corners_y.setValue(6)
        self.sp_square = QtWidgets.QDoubleSpinBox()
        self.sp_square.setRange(0.1, 10000.0)
        self.sp_square.setDecimals(3)
        self.sp_square.setSingleStep(1.0)
        self.sp_square.setValue(25.0)
        self.sp_square.setSuffix(" mm")
        self.lbl_spacing = QtWidgets.QLabel("Square / circle spacing:")
        form.addRow("Pattern type:", self.cmb_pattern_type)
        form.addRow("Corners / circles X:", self.sp_corners_x)
        form.addRow("Corners / circles Y:", self.sp_corners_y)
        form.addRow(self.lbl_spacing, self.sp_square)

        grp_preprocess = QtWidgets.QGroupBox("Preprocessing")
        prep_form = QtWidgets.QFormLayout(grp_preprocess)
        self.chk_clahe = QtWidgets.QCheckBox("Enable CLAHE (adaptive histogram equalization)")
        self.chk_clahe.setChecked(True)
        self.sp_clahe_clip = QtWidgets.QDoubleSpinBox()
        self.sp_clahe_clip.setRange(0.5, 20.0)
        self.sp_clahe_clip.setDecimals(2)
        self.sp_clahe_clip.setSingleStep(0.5)
        self.sp_clahe_clip.setValue(2.0)
        self.sp_clahe_grid = QtWidgets.QSpinBox()
        self.sp_clahe_grid.setRange(2, 32)
        self.sp_clahe_grid.setValue(8)
        self.sp_clahe_grid.setSuffix(" px")
        prep_form.addRow(self.chk_clahe)
        prep_form.addRow("CLAHE clip limit:", self.sp_clahe_clip)
        prep_form.addRow("CLAHE tile size:", self.sp_clahe_grid)

        grp_alpha = QtWidgets.QGroupBox("Undistortion")
        alpha_form = QtWidgets.QFormLayout(grp_alpha)
        self.sp_alpha = QtWidgets.QDoubleSpinBox()
        self.sp_alpha.setRange(0.0, 1.0)
        self.sp_alpha.setDecimals(2)
        self.sp_alpha.setSingleStep(0.05)
        self.sp_alpha.setValue(0.5)
        self.sl_alpha = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sl_alpha.setRange(0, 100)
        self.sl_alpha.setValue(50)
        self.sl_alpha.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.sl_alpha.setTickInterval(10)
        self.lbl_alpha_desc = QtWidgets.QLabel("0 = crop valid pixels,  1 = full FOV,  0.5 = balanced")
        self.lbl_alpha_desc.setStyleSheet("QLabel { color: #666; font-size: 9pt; }")
        self.lbl_alpha_desc.setWordWrap(True)
        alpha_row = QtWidgets.QHBoxLayout()
        alpha_row.addWidget(self.sp_alpha)
        alpha_row.addWidget(self.sl_alpha, stretch=1)
        alpha_form.addRow("Alpha (FOV balance):", alpha_row)
        alpha_form.addRow(self.lbl_alpha_desc)

        # --- Mono / Stereo workflow tabs --------------------------------
        self.workflow_tabs = QtWidgets.QTabWidget()

        # --- Mono workflow tab
        mono_tab = QtWidgets.QWidget()
        mono_layout = QtWidgets.QVBoxLayout(mono_tab)

        grp_images = QtWidgets.QGroupBox("Calibration images (mono)")
        img_layout = QtWidgets.QVBoxLayout(grp_images)
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add_files = QtWidgets.QPushButton("Add files…")
        self.btn_add_dir = QtWidgets.QPushButton("Add folder…")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        btn_row.addWidget(self.btn_add_files)
        btn_row.addWidget(self.btn_add_dir)
        btn_row.addWidget(self.btn_clear)
        img_layout.addLayout(btn_row)

        self.list_images = QtWidgets.QListWidget()
        self.list_images.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        img_layout.addWidget(self.list_images)

        grp_actions = QtWidgets.QGroupBox("Calibration (mono)")
        act_layout = QtWidgets.QVBoxLayout(grp_actions)
        self.btn_calibrate = QtWidgets.QPushButton("Run mono calibration")
        self.btn_calibrate.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; }"
        )
        self.btn_save_json = QtWidgets.QPushButton("Save result (JSON)…")
        self.btn_save_errors = QtWidgets.QPushButton("Save error plot…")
        self.btn_save_undistort = QtWidgets.QPushButton("Export undistorted…")
        self.btn_save_json.setEnabled(False)
        self.btn_save_errors.setEnabled(False)
        self.btn_save_undistort.setEnabled(False)
        act_layout.addWidget(self.btn_calibrate)
        act_layout.addWidget(self.btn_save_json)
        act_layout.addWidget(self.btn_save_errors)
        act_layout.addWidget(self.btn_save_undistort)

        mono_layout.addWidget(grp_images, stretch=1)
        mono_layout.addWidget(grp_actions)

        # --- Stereo workflow tab
        stereo_tab = QtWidgets.QWidget()
        stereo_layout = QtWidgets.QVBoxLayout(stereo_tab)

        grp_stereo_images = QtWidgets.QGroupBox("Stereo image pairs (left / right)")
        stereo_img_layout = QtWidgets.QVBoxLayout(grp_stereo_images)
        btn_row_stereo = QtWidgets.QHBoxLayout()
        self.btn_stereo_add_pair = QtWidgets.QPushButton("Add pair…")
        self.btn_stereo_add_dirs = QtWidgets.QPushButton("Add folders…")
        self.btn_stereo_clear = QtWidgets.QPushButton("Clear")
        btn_row_stereo.addWidget(self.btn_stereo_add_pair)
        btn_row_stereo.addWidget(self.btn_stereo_add_dirs)
        btn_row_stereo.addWidget(self.btn_stereo_clear)
        stereo_img_layout.addLayout(btn_row_stereo)

        self.list_stereo_pairs = QtWidgets.QListWidget()
        self.list_stereo_pairs.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        stereo_img_layout.addWidget(self.list_stereo_pairs)

        grp_stereo_actions = QtWidgets.QGroupBox("Stereo calibration")
        stereo_act_layout = QtWidgets.QVBoxLayout(grp_stereo_actions)
        self.btn_stereo_calibrate = QtWidgets.QPushButton("Run stereo calibration")
        self.btn_stereo_calibrate.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; }"
        )
        self.btn_stereo_save = QtWidgets.QPushButton("Save stereo result (JSON)…")
        self.btn_stereo_save.setEnabled(False)
        self.btn_stereo_disp = QtWidgets.QPushButton("Compute & view disparity…")
        self.btn_stereo_disp.setEnabled(False)
        stereo_act_layout.addWidget(self.btn_stereo_calibrate)
        stereo_act_layout.addWidget(self.btn_stereo_save)
        stereo_act_layout.addWidget(self.btn_stereo_disp)

        stereo_layout.addWidget(grp_stereo_images, stretch=1)
        stereo_layout.addWidget(grp_stereo_actions)

        self.workflow_tabs.addTab(mono_tab, "Mono")
        self.workflow_tabs.addTab(stereo_tab, "Stereo")

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)

        left_layout.addWidget(grp_pattern)
        left_layout.addWidget(grp_preprocess)
        left_layout.addWidget(grp_alpha)
        left_layout.addWidget(self.workflow_tabs, stretch=1)
        left_layout.addWidget(self.log)

        # --- Right: preview & results -----------------------------------
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        self.tabs = QtWidgets.QTabWidget()
        self.preview_label = QtWidgets.QLabel("No image loaded.")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; }"
        )
        self.preview_label.setMinimumSize(640, 400)

        self.preview_undistorted = QtWidgets.QLabel("Run calibration to preview.")
        self.preview_undistorted.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_undistorted.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; }"
        )
        self.preview_undistorted.setMinimumSize(640, 400)

        self.errors_label = QtWidgets.QLabel("Run calibration to see errors.")
        self.errors_label.setAlignment(QtCore.Qt.AlignCenter)
        self.errors_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; }"
        )
        self.errors_label.setMinimumSize(640, 300)

        self.quality_label = QtWidgets.QLabel("Run calibration to see quality report.")
        self.quality_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.quality_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #ddd; padding: 10px; }"
        )
        self.quality_label.setMinimumSize(640, 300)
        self.quality_label.setWordWrap(True)

        self.stereo_label = QtWidgets.QLabel("Run stereo calibration to see disparity preview.")
        self.stereo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.stereo_label.setStyleSheet(
            "QLabel { background-color: #1e1e1e; color: #888; }"
        )
        self.stereo_label.setMinimumSize(640, 400)

        self.tabs.addTab(self.preview_label, "Detected features")
        self.tabs.addTab(self.preview_undistorted, "Undistorted preview")
        self.tabs.addTab(self.errors_label, "Reprojection error")
        self.tabs.addTab(self.quality_label, "Quality report")
        self.tabs.addTab(self.stereo_label, "Stereo disparity")

        self.result_text = QtWidgets.QPlainTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Calibration output will appear here.")
        self.result_text.setFixedHeight(180)

        right_layout.addWidget(self.tabs, stretch=1)
        right_layout.addWidget(self.result_text)

        main_layout.addWidget(left)
        main_layout.addWidget(right, stretch=1)

        # --- Wiring -----------------------------------------------------
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_add_dir.clicked.connect(self._on_add_dir)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_calibrate.clicked.connect(self._on_calibrate)
        self.btn_save_json.clicked.connect(self._on_save_json)
        self.btn_save_errors.clicked.connect(self._on_save_errors)
        self.btn_save_undistort.clicked.connect(self._on_save_undistort)
        self.list_images.currentItemChanged.connect(self._on_image_selected)
        self.list_images.itemSelectionChanged.connect(self._on_image_selected)

        self.btn_stereo_add_pair.clicked.connect(self._on_stereo_add_pair)
        self.btn_stereo_add_dirs.clicked.connect(self._on_stereo_add_dirs)
        self.btn_stereo_clear.clicked.connect(self._on_stereo_clear)
        self.btn_stereo_calibrate.clicked.connect(self._on_stereo_calibrate)
        self.btn_stereo_save.clicked.connect(self._on_stereo_save)
        self.btn_stereo_disp.clicked.connect(self._on_stereo_disp)

        self.cmb_pattern_type.currentIndexChanged.connect(self._on_pattern_type_changed)
        self.sp_corners_x.valueChanged.connect(self._on_pattern_param_changed)
        self.sp_corners_y.valueChanged.connect(self._on_pattern_param_changed)
        self.sp_square.valueChanged.connect(self._on_pattern_param_changed)

        self.sp_alpha.valueChanged.connect(self._sync_alpha_from_spin)
        self.sl_alpha.valueChanged.connect(self._sync_alpha_from_slider)
        self.sp_alpha.valueChanged.connect(self._on_alpha_changed)
        self.chk_clahe.toggled.connect(self._on_preprocess_param_changed)
        self.sp_clahe_clip.valueChanged.connect(self._on_preprocess_param_changed)
        self.sp_clahe_grid.valueChanged.connect(self._on_preprocess_param_changed)

        # Shortcuts
        QtWidgets.QShortcut(QtGui.QKeySequence("Del"), self,
                            activated=self._on_remove_selected)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _reset_state(self) -> None:
        self._calibrator = self._make_calibrator()
        self._stereo_calibrator = None
        self._result = None
        self._stereo_result = None
        self.btn_save_json.setEnabled(False)
        self.btn_save_errors.setEnabled(False)
        self.btn_save_undistort.setEnabled(False)
        self.btn_stereo_save.setEnabled(False)
        self.btn_stereo_disp.setEnabled(False)
        self.preview_label.setText("No image loaded.")
        self.preview_label.setPixmap(QtGui.QPixmap())
        self.preview_undistorted.setText("Run calibration to preview.")
        self.preview_undistorted.setPixmap(QtGui.QPixmap())
        self.errors_label.setText("Run calibration to see errors.")
        self.errors_label.setPixmap(QtGui.QPixmap())
        self.quality_label.setText("Run calibration to see quality report.")
        self.quality_label.setPixmap(QtGui.QPixmap())
        self.stereo_label.setText("Run stereo calibration to see disparity preview.")
        self.stereo_label.setPixmap(QtGui.QPixmap())
        self.result_text.clear()

    def _current_pattern_type(self) -> PatternType:
        value = self.cmb_pattern_type.currentData()
        return PatternType(value)

    def _make_calibrator(self) -> CameraCalibrator:
        grid_size = self.sp_clahe_grid.value()
        return CameraCalibrator(
            pattern_size=(self.sp_corners_x.value(), self.sp_corners_y.value()),
            square_size=self.sp_square.value(),
            use_clahe=self.chk_clahe.isChecked(),
            clahe_clip=self.sp_clahe_clip.value(),
            clahe_grid=(grid_size, grid_size),
            pattern_type=self._current_pattern_type(),
        )

    def _make_stereo_calibrator(self) -> StereoCalibrator:
        grid_size = self.sp_clahe_grid.value()
        return StereoCalibrator(
            pattern_size=(self.sp_corners_x.value(), self.sp_corners_y.value()),
            square_size=self.sp_square.value(),
            use_clahe=self.chk_clahe.isChecked(),
            clahe_clip=self.sp_clahe_clip.value(),
            clahe_grid=(grid_size, grid_size),
            pattern_type=self._current_pattern_type(),
        )

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)

    # ------------------------------------------------------------------
    # Alpha sync helpers
    # ------------------------------------------------------------------

    def _sync_alpha_from_spin(self, value: float) -> None:
        pct = int(round(value * 100))
        if self.sl_alpha.value() != pct:
            self.sl_alpha.blockSignals(True)
            self.sl_alpha.setValue(pct)
            self.sl_alpha.blockSignals(False)

    def _sync_alpha_from_slider(self, value: int) -> None:
        alpha = value / 100.0
        if abs(self.sp_alpha.value() != alpha):
            self.sp_alpha.blockSignals(True)
            self.sp_alpha.setValue(alpha)
            self.sp_alpha.blockSignals(False)

    def _on_preprocess_param_changed(self) -> None:
        if self.list_images.count() == 0 and self.list_stereo_pairs.count() == 0:
            self._reset_state()
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Preprocessing changed",
            "Preprocessing parameters changed. Re-detect features for all images?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            existing_paths = [
                self.list_images.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_images.count())
            ]
            existing_pairs = [
                self.list_stereo_pairs.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_stereo_pairs.count())
            ]
            self._reset_state()
            self._add_paths(existing_paths)
            for pair in existing_pairs:
                if isinstance(pair, tuple) and len(pair) == 2:
                    self._add_stereo_pair(pair[0], pair[1])

    def _on_pattern_type_changed(self) -> None:
        self._on_pattern_param_changed()

    def _on_pattern_param_changed(self) -> None:
        if self.list_images.count() == 0 and self.list_stereo_pairs.count() == 0:
            self._reset_state()
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Pattern changed",
            "Pattern parameters changed. Re-detect features for all images?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            existing_paths = [
                self.list_images.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_images.count())
            ]
            existing_pairs = [
                self.list_stereo_pairs.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.list_stereo_pairs.count())
            ]
            self._reset_state()
            self._add_paths(existing_paths)
            for pair in existing_pairs:
                if isinstance(pair, tuple) and len(pair) == 2:
                    self._add_stereo_pair(pair[0], pair[1])

    def _on_alpha_changed(self) -> None:
        if self._result is None:
            return
        alpha = self.sp_alpha.value()
        self._result.alpha = float(alpha)
        self._result.new_camera_matrix = None
        self._result._compute_new_camera_matrix(self._result.image_size)
        self._on_image_selected()
        self._show_result()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select calibration images",
            "",
            f"Images ({IMAGE_EXTS});;All files (*.*)",
        )
        if not files:
            return
        self._add_paths(files)

    def _on_add_dir(self) -> None:
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select folder with calibration images"
        )
        if not directory:
            return
        paths = sorted(
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        if not paths:
            self._log(f"No supported images found in {directory}.")
            return
        self._add_paths(paths)

    def _add_paths(self, paths: List[str]) -> None:
        grid = self.sp_clahe_grid.value()
        params_changed = self._calibrator is None or (
            (self.sp_corners_x.value(), self.sp_corners_y.value()
        ) != self._calibrator.pattern_size or \
                self.sp_square.value() != self._calibrator.square_size or \
                self.chk_clahe.isChecked() != self._calibrator.use_clahe or \
                (self._calibrator.clahe is not None and (
                    abs(self._calibrator.clahe.getClipLimit() - self.sp_clahe_clip.value()) > 1e-6 or
                    self._calibrator.clahe.getTilesGridSize() != (grid, grid)))
        )
        if params_changed:
            self._calibrator = self._make_calibrator()

        existing = {
            self.list_images.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_images.count())
        }
        added, failed, skipped = 0, 0, 0
        for p in paths:
            if p in existing:
                skipped += 1
                continue
            ok, msg = self._calibrator.add_image(p)
            item = QtWidgets.QListWidgetItem(
                f"{'✓' if ok else '✗'} {os.path.basename(p)}"
            )
            item.setData(QtCore.Qt.UserRole, p)
            item.setForeground(QtGui.QColor("#2e7d32" if ok else "#c62828"))
            item.setToolTip(msg if not ok else p)
            self.list_images.addItem(item)
            if ok:
                added += 1
            else:
                failed += 1
                self._log(f"[skip] {p}: {msg}")
        self._log(
            f"Added {added} images ({failed} failed, {skipped} duplicates)."
        )

    def _on_clear(self) -> None:
        if self.list_images.count() == 0:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Clear",
            "Remove all loaded images and reset calibration?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self.list_images.clear()
        self._reset_state()

    def _on_remove_selected(self) -> None:
        selected = self.list_images.selectedItems()
        if not selected:
            return
        for item in selected:
            self.list_images.takeItem(self.list_images.row(item))
        # Rebuild the calibrator from the remaining items.
        remaining = [
            self.list_images.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_images.count())
            if self.list_images.item(i).foreground().color().name() == "#2e7d32"
        ]
        self._calibrator = self._make_calibrator()
        for p in remaining:
            self._calibrator.add_image(p)

    def _on_image_selected(self, *args) -> None:
        item = self.list_images.currentItem()
        if item is None or self._calibrator is None:
            return
        path = item.data(QtCore.Qt.UserRole)
        annotated = self._calibrator.annotated_images.get(path)
        if annotated is None:
            self.preview_label.setText("No pattern features detected for this image.")
            self.preview_label.setPixmap(QtGui.QPixmap())
        else:
            rgb = bgr_to_rgb(annotated)
            self.preview_label.setPixmap(_np_to_qpixmap(rgb))
            self.preview_label.setText("")

        # Refresh undistorted preview when a calibration exists.
        if self._result is not None:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                preview = build_undistort_preview(img, self._result)
                self.preview_undistorted.setPixmap(
                    _np_to_qpixmap(bgr_to_rgb(preview))
                )
                self.preview_undistorted.setText("")

    def _on_calibrate(self) -> None:
        if self._calibrator is None:
            self._log("No calibrator initialised.")
            return
        if self._calibrator.num_valid_images < 2:
            QtWidgets.QMessageBox.warning(
                self, "Not enough images",
                "At least 2 images with detected pattern features are required.",
            )
            return

        self.setCursor(QtCore.Qt.WaitCursor)
        try:
            self._result = self._calibrator.calibrate(alpha=self.sp_alpha.value())
        except Exception as exc:  # pragma: no cover
            self.setCursor(QtCore.Qt.ArrowCursor)
            QtWidgets.QMessageBox.critical(
                self, "Calibration failed", str(exc)
            )
            return
        finally:
            self.setCursor(QtCore.Qt.ArrowCursor)

        self.btn_save_json.setEnabled(True)
        self.btn_save_errors.setEnabled(True)
        self.btn_save_undistort.setEnabled(True)

        self._show_result()
        self._show_errors_plot()
        self._show_quality_report()
        self._on_image_selected()  # refresh undistort preview

    def _show_result(self) -> None:
        if self._result is None:
            return
        r = self._result
        fx, fy = r.focal_lengths_px
        cx, cy = r.principal_point_px
        k1, k2, p1, p2, k3 = r.dist_coeffs.ravel().tolist()[:5]

        lines = [
            "=== Calibration result ===",
            f"Pattern type       : {r.pattern_type.value}",
            f"Images used        : {len(r.image_paths)}",
            f"Image size         : {r.image_size[0]} x {r.image_size[1]}",
            f"Pattern size       : {r.pattern_size}",
            f"Spacing            : {r.square_size} mm",
            f"Undistort alpha    : {r.alpha:.2f} (FOV balance)",
            "",
            "--- Intrinsics ---",
            f"fx                 : {fx:.4f} px",
            f"fy                 : {fy:.4f} px",
            f"cx                 : {cx:.4f} px",
            f"cy                 : {cy:.4f} px",
            "",
            "--- Distortion (k1, k2, p1, p2, k3) ---",
            f"k1 = {k1:.6f}   k2 = {k2:.6f}",
            f"p1 = {p1:.6f}   p2 = {p2:.6f}",
            f"k3 = {k3:.6f}",
            "",
            "--- Quality ---",
            f"Mean reproj. error : {r.reprojection_error:.4f} px",
            f"Per-view errors    : {[round(e, 4) for e in r.per_view_errors]}",
        ]
        self.result_text.setPlainText("\n".join(lines))
        self._log(f"Calibration done. RMS = {r.reprojection_error:.4f} px")

    def _show_quality_report(self) -> None:
        if self._result is None:
            return
        try:
            report = self._result.quality_report()
        except Exception as exc:  # pragma: no cover
            self.quality_label.setText(f"Failed to build quality report: {exc}")
            return
        self.quality_label.setText(report.format_text())
        color = {
            "Excellent": "#2e7d32",
            "Good": "#689f38",
            "Fair": "#f9a825",
            "Poor": "#c62828",
        }.get(report.confidence_label, "#ddd")
        self.quality_label.setStyleSheet(
            f"QLabel {{ background-color: #1e1e1e; color: {color}; padding: 10px; }}"
        )

    def _show_errors_plot(self) -> None:
        if self._result is None:
            return
        rgb = plot_reprojection_errors(self._result)
        self.errors_label.setPixmap(_np_to_qpixmap(rgb, max_size=1000))
        self.errors_label.setText("")

    def _on_save_json(self) -> None:
        if self._result is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save calibration", "calibration.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            self._result.save(path)
            self._log(f"Saved calibration to {path}")
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def _on_save_errors(self) -> None:
        if self._result is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save error plot", "reprojection_errors.png",
            "PNG (*.png);;SVG (*.svg)",
        )
        if not path:
            return
        try:
            plot_reprojection_errors(self._result, save_path=path)
            self._log(f"Saved error plot to {path}")
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def _on_save_undistort(self) -> None:
        if self._result is None:
            return
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select output folder for undistorted images"
        )
        if not directory:
            return
        n = 0
        for p in self._result.image_paths:
            img = cv2.imread(p, cv2.IMREAD_COLOR)
            if img is None:
                continue
            undist = self._result.undistort(img)
            base = os.path.splitext(os.path.basename(p))[0] + "_undistorted.png"
            out = os.path.join(directory, base)
            cv2.imwrite(out, undist)
            n += 1
        self._log(f"Exported {n} undistorted images to {directory}")

    # ------------------------------------------------------------------
    # Stereo workflow slots
    # ------------------------------------------------------------------

    def _on_stereo_add_pair(self) -> None:
        left, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select LEFT camera image", "", f"Images ({IMAGE_EXTS})",
        )
        if not left:
            return
        right, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select RIGHT camera image", "", f"Images ({IMAGE_EXTS})",
        )
        if not right:
            return
        self._add_stereo_pair(left, right)

    def _on_stereo_add_dirs(self) -> None:
        left_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select folder with LEFT camera images"
        )
        if not left_dir:
            return
        right_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select folder with RIGHT camera images"
        )
        if not right_dir:
            return
        left_files = sorted(
            os.path.join(left_dir, f) for f in os.listdir(left_dir)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        right_files = sorted(
            os.path.join(right_dir, f) for f in os.listdir(right_dir)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        n = min(len(left_files), len(right_files))
        if n == 0:
            self._log("No images found in one of the folders.")
            return
        if len(left_files) != len(right_files):
            self._log(
                f"WARNING: left has {len(left_files)} files, right has "
                f"{len(right_files)}; using first {n} from each."
            )
        for l, r in zip(left_files[:n], right_files[:n]):
            self._add_stereo_pair(l, r)

    def _on_stereo_clear(self) -> None:
        if self.list_stereo_pairs.count() == 0:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Clear",
            "Remove all stereo image pairs and reset calibration?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self.list_stereo_pairs.clear()
        self._stereo_calibrator = None
        self._stereo_result = None
        self.btn_stereo_save.setEnabled(False)
        self.btn_stereo_disp.setEnabled(False)

    def _add_stereo_pair(self, left_path: str, right_path: str) -> None:
        if self._stereo_calibrator is None:
            self._stereo_calibrator = self._make_stereo_calibrator()

        # Prevent duplicate pairs.
        existing_pairs = {
            self.list_stereo_pairs.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.list_stereo_pairs.count())
        }
        pair = (left_path, right_path)
        if pair in existing_pairs:
            return

        ok, msg = self._stereo_calibrator.add_image_pair(left_path, right_path)
        label = (
            f"{'✓' if ok else '✗'} L: {os.path.basename(left_path)}  |  "
            f"R: {os.path.basename(right_path)}"
        )
        item = QtWidgets.QListWidgetItem(label)
        item.setData(QtCore.Qt.UserRole, pair)
        item.setForeground(QtGui.QColor("#2e7d32" if ok else "#c62828"))
        item.setToolTip(msg if not ok else f"{left_path}\n{right_path}")
        self.list_stereo_pairs.addItem(item)
        if not ok:
            self._log(f"[skip] stereo pair: {msg}")

    def _on_stereo_calibrate(self) -> None:
        if self._stereo_calibrator is None:
            self._log("No stereo calibrator initialised.")
            return
        if self._stereo_calibrator.num_valid_pairs < 2:
            QtWidgets.QMessageBox.warning(
                self, "Not enough pairs",
                "At least 2 valid stereo pairs are required.",
            )
            return

        self.setCursor(QtCore.Qt.WaitCursor)
        try:
            self._stereo_result = self._stereo_calibrator.calibrate(
                alpha=self.sp_alpha.value(),
            )
        except Exception as exc:  # pragma: no cover
            self.setCursor(QtCore.Qt.ArrowCursor)
            QtWidgets.QMessageBox.critical(
                self, "Stereo calibration failed", str(exc)
            )
            return
        finally:
            self.setCursor(QtCore.Qt.ArrowCursor)

        self.btn_stereo_save.setEnabled(True)
        self.btn_stereo_disp.setEnabled(True)
        self._show_stereo_result()

    def _show_stereo_result(self) -> None:
        if self._stereo_result is None:
            return
        st = self._stereo_result
        left_rms = st.left.reprojection_error
        right_rms = st.right.reprojection_error
        baseline = st.baseline_mm

        lines = [
            "=== Stereo calibration result ===",
            f"Stereo RMS         : {st.rms:.4f} px",
            f"Left mono RMS      : {left_rms:.4f} px",
            f"Right mono RMS     : {right_rms:.4f} px",
            f"Baseline           : {baseline:.3f} mm",
            "",
            "--- Left camera intrinsics ---",
            f"fx = {st.left.focal_lengths_px[0]:.4f} px   "
            f"fy = {st.left.focal_lengths_px[1]:.4f} px",
            f"cx = {st.left.principal_point_px[0]:.4f} px   "
            f"cy = {st.left.principal_point_px[1]:.4f} px",
            "",
            "--- Right camera intrinsics ---",
            f"fx = {st.right.focal_lengths_px[0]:.4f} px   "
            f"fy = {st.right.focal_lengths_px[1]:.4f} px",
            f"cx = {st.right.principal_point_px[0]:.4f} px   "
            f"cy = {st.right.principal_point_px[1]:.4f} px",
            "",
            "--- Extrinsics (left → right) ---",
            f"Rotation matrix R :",
        ]
        for row in st.R:
            lines.append("    " + "  ".join(f"{v: .6f}" for v in row))
        lines += [
            f"Translation T (mm) : {st.T.ravel().tolist()}",
            "",
            "--- Depth parameters ---",
            f"f_left (rectified) : {st.focal_length_left_px:.4f} px",
            f"f_right (rectified): {st.focal_length_right_px:.4f} px",
            f"Depth formula      : Z = f * {baseline:.2f} / d  (d in px, Z in mm)",
        ]
        self.result_text.setPlainText("\n".join(lines))
        self._log(
            f"Stereo calibration done. RMS = {st.rms:.4f} px, "
            f"baseline = {baseline:.3f} mm"
        )

    def _on_stereo_save(self) -> None:
        if self._stereo_result is None:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save stereo calibration", "stereo_calibration.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            self._stereo_result.save(path)
            self._log(f"Saved stereo calibration to {path}")
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))

    def _on_stereo_disp(self) -> None:
        if self._stereo_result is None:
            return
        # Pick a valid stereo pair.
        left_path = None
        right_path = None
        for i in range(self.list_stereo_pairs.count()):
            item = self.list_stereo_pairs.item(i)
            if item.foreground().color().name() == "#2e7d32":
                pair = item.data(QtCore.Qt.UserRole)
                left_path, right_path = pair[0], pair[1]
                break
        if left_path is None:
            QtWidgets.QMessageBox.warning(
                self, "No valid pair",
                "Select a valid stereo pair first.",
            )
            return
        left_img = cv2.imread(left_path, cv2.IMREAD_COLOR)
        right_img = cv2.imread(right_path, cv2.IMREAD_COLOR)
        if left_img is None or right_img is None:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to read images.")
            return

        try:
            left_rect, right_rect = self._stereo_result.rectify(left_img, right_img)
            disp = self._stereo_result.compute_disparity(left_rect, right_rect)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Disparity failed", str(exc))
            return

        # Render disparity as colour map.
        disp_vis = disp.copy()
        disp_vis[disp_vis <= 0] = np.nanmin(disp_vis[disp_vis > 0]) if np.any(disp_vis > 0) else 0
        dmin = float(np.nanmin(disp_vis))
        dmax = float(np.nanmax(disp_vis))
        if dmax > dmin:
            disp_norm = (disp_vis - dmin) / (dmax - dmin)
        else:
            disp_norm = np.zeros_like(disp_vis)
        disp_uint8 = np.clip(disp_norm * 255.0, 0, 255).astype(np.uint8)
        disp_color = cv2.applyColorMap(disp_uint8, cv2.COLORMAP_TURBO)

        # Build a side-by-side composite: rectified left, rectified right, disparity.
        h = left_rect.shape[0]
        target_h = 400
        scale = target_h / h if h > 0 else 1.0
        pieces = []
        for img in (left_rect, right_rect, disp_color):
            new_w = max(1, int(round(img.shape[1] * scale)))
            new_h = max(1, int(round(img.shape[0] * scale)))
            pieces.append(cv2.resize(img, (new_w, new_h)))
        composite = cv2.hconcat(pieces)

        rgb = bgr_to_rgb(composite)
        self.stereo_label.setPixmap(_np_to_qpixmap(rgb, max_size=1400))
        self.stereo_label.setText("")
        self.tabs.setCurrentWidget(self.stereo_label)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = CalibrationGUI()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
