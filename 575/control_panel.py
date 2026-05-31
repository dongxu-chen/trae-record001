from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QSlider, QLabel, QPushButton, QDoubleSpinBox,
                             QCheckBox, QFileDialog, QMessageBox, QComboBox)
from PyQt5.QtCore import Qt


class ControlPanel(QWidget):
    def __init__(self, gl_widget, parent=None):
        super().__init__(parent)
        self.gl_widget = gl_widget
        self._exporting = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        layout.addWidget(self._create_spectrum_group())
        layout.addWidget(self._create_wave_group())
        layout.addWidget(self._create_foam_group())
        layout.addWidget(self._create_ship_group())
        layout.addWidget(self._create_camera_group())
        layout.addWidget(self._create_animation_group())
        layout.addWidget(self._create_export_group())

        layout.addStretch()
        self.setLayout(layout)

        self.setFixedWidth(280)

    def _create_spectrum_group(self):
        group = QGroupBox('海浪谱模型')
        layout = QVBoxLayout()

        spectrum_layout = QHBoxLayout()
        spectrum_layout.addWidget(QLabel('谱类型'))
        self.spectrum_combo = QComboBox()
        self.spectrum_combo.addItems(['Phillips', 'JONSWAP', 'Pierson-Moskowitz'])
        self.spectrum_combo.currentIndexChanged.connect(self._on_spectrum_changed)
        spectrum_layout.addWidget(self.spectrum_combo)
        layout.addLayout(spectrum_layout)

        spectrum_info = QLabel('Phillips: 经典波浪谱\nJONSWAP: 北海海况\nPM: 充分发展海浪')
        spectrum_info.setStyleSheet('color: #666; font-size: 10px;')
        layout.addWidget(spectrum_info)

        group.setLayout(layout)
        return group

    def _create_wave_group(self):
        group = QGroupBox('波浪参数')
        layout = QVBoxLayout()

        layout.addLayout(self._create_slider_spin(
            '风速', 5.0, 80.0, 30.0, 0.5,
            self.gl_widget.set_wind_speed
        ))

        layout.addLayout(self._create_slider_spin(
            '风向', 0.0, 360.0, 0.0, 1.0,
            self.gl_widget.set_wind_angle
        ))

        layout.addLayout(self._create_slider_spin(
            '振幅', 0.00001, 0.001, 0.0002, 0.00001,
            self.gl_widget.set_wave_amplitude, 6
        ))

        layout.addLayout(self._create_slider_spin(
            '波浪起伏', 0.0, 4.0, 1.5, 0.1,
            self.gl_widget.set_choppy_factor
        ))

        group.setLayout(layout)
        return group

    def _create_foam_group(self):
        group = QGroupBox('泡沫效果')
        layout = QVBoxLayout()

        layout.addLayout(self._create_slider_spin(
            '泡沫阈值', 0.1, 1.0, 0.7, 0.05,
            self.gl_widget.set_foam_threshold
        ))

        layout.addLayout(self._create_slider_spin(
            '泡沫强度', 0.0, 2.0, 1.0, 0.1,
            self.gl_widget.set_foam_intensity
        ))

        group.setLayout(layout)
        return group

    def _create_ship_group(self):
        group = QGroupBox('船舶浮体')
        layout = QVBoxLayout()

        self.ship_checkbox = QCheckBox('显示船舶')
        self.ship_checkbox.setChecked(True)
        self.ship_checkbox.toggled.connect(self.gl_widget.set_ship_visible)
        layout.addWidget(self.ship_checkbox)

        ship_info = QLabel('船随波浪起伏、横摇和纵摇')
        ship_info.setStyleSheet('color: #666; font-size: 10px;')
        layout.addWidget(ship_info)

        group.setLayout(layout)
        return group

    def _create_camera_group(self):
        group = QGroupBox('相机控制')
        layout = QVBoxLayout()

        info_label = QLabel(
            '左键拖拽: 旋转\n'
            '中键拖拽: 平移\n'
            '右键拖拽: 升降\n'
            '滚轮: 缩放'
        )
        info_label.setStyleSheet('color: #666; font-size: 11px;')
        layout.addWidget(info_label)

        self.underwater_label = QLabel('视角: 水面上')
        self.underwater_label.setStyleSheet('font-weight: bold; color: #2196F3;')
        layout.addWidget(self.underwater_label)

        reset_btn = QPushButton('重置视角')
        reset_btn.clicked.connect(self._reset_view)
        layout.addWidget(reset_btn)

        underwater_btn = QPushButton('潜入水下')
        underwater_btn.clicked.connect(self._toggle_underwater)
        layout.addWidget(underwater_btn)
        self.underwater_btn = underwater_btn

        group.setLayout(layout)
        return group

    def _create_animation_group(self):
        group = QGroupBox('动画控制')
        layout = QVBoxLayout()

        layout.addLayout(self._create_slider_spin(
            '时间缩放', 0.0, 5.0, 1.0, 0.1,
            self.gl_widget.set_time_scale
        ))

        self.play_btn = QPushButton('暂停')
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)

        group.setLayout(layout)
        return group

    def _create_export_group(self):
        group = QGroupBox('导出动画')
        layout = QVBoxLayout()

        self.export_btn = QPushButton('导出视频...')
        self.export_btn.clicked.connect(self._export_video)
        layout.addWidget(self.export_btn)

        export_info = QLabel('格式: MP4\n帧率: 30 FPS')
        export_info.setStyleSheet('color: #666; font-size: 11px;')
        layout.addWidget(export_info)

        group.setLayout(layout)
        return group

    def _create_slider_spin(self, label, min_val, max_val, default, step, callback, decimals=2):
        layout = QHBoxLayout()

        lbl = QLabel(label)
        lbl.setFixedWidth(80)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(int(min_val / step), int(max_val / step))
        slider.setValue(int(default / step))
        slider.setSingleStep(1)

        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setFixedWidth(80)

        slider.valueChanged.connect(lambda v: spin.setValue(v * step))
        spin.valueChanged.connect(lambda v: slider.setValue(int(v / step)))
        spin.valueChanged.connect(callback)

        layout.addWidget(lbl)
        layout.addWidget(slider)
        layout.addWidget(spin)

        return layout

    def _on_spectrum_changed(self, index):
        spectrum_types = ['phillips', 'jonswap', 'pm']
        if 0 <= index < len(spectrum_types):
            self.gl_widget.set_spectrum_type(spectrum_types[index])

    def _toggle_play(self):
        is_playing = self.gl_widget.toggle_play()
        self.play_btn.setText('暂停' if is_playing else '播放')

    def _reset_view(self):
        self.gl_widget.reset_view()
        self.underwater_label.setText('视角: 水面上')
        self.underwater_label.setStyleSheet('font-weight: bold; color: #2196F3;')
        self.underwater_btn.setText('潜入水下')

    def _toggle_underwater(self):
        camera = self.gl_widget.camera
        if camera.is_underwater:
            camera.target[1] = max(camera.target[1], 20.0)
            camera._distance = 120.0
            camera._pitch = -30.0
            camera._update_position_from_angles()
            self.underwater_label.setText('视角: 水面上')
            self.underwater_label.setStyleSheet('font-weight: bold; color: #2196F3;')
            self.underwater_btn.setText('潜入水下')
        else:
            camera.target[1] = -15.0
            camera._distance = 30.0
            camera._pitch = 10.0
            camera._update_position_from_angles()
            self.underwater_label.setText('视角: 水面下')
            self.underwater_label.setStyleSheet('font-weight: bold; color: #00BCD4;')
            self.underwater_btn.setText('浮出水面')

    def _export_video(self):
        if self._exporting:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, '导出视频', 'water_animation.mp4',
            'MP4 Video (*.mp4);;AVI Video (*.avi)'
        )

        if not filename:
            return

        self._exporting = True
        self.export_btn.setEnabled(False)
        self.export_btn.setText('导出中...')

        try:
            from video_export import VideoExporter
            exporter = VideoExporter(self.gl_widget, filename)
            exporter.export_animation(
                duration=5.0,
                fps=30,
                callback=self._export_progress
            )
            QMessageBox.information(self, '导出完成', f'视频已保存至:\n{filename}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', str(e))
        finally:
            self._exporting = False
            self.export_btn.setEnabled(True)
            self.export_btn.setText('导出视频...')

    def _export_progress(self, current, total):
        progress = int((current / total) * 100)
        self.export_btn.setText(f'导出中... {progress}%')
