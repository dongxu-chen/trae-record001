import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QComboBox, QSpinBox, QSlider, QProgressBar, QMessageBox,
                             QSplitter, QGroupBox, QFormLayout, QListWidget,
                             QListWidgetItem, QFrame, QStatusBar, QDialog, QDialogButtonBox,
                             QAction, QMenuBar, QShortcut, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QKeySequence

from export import Clip, MediaInfo, ExportConfig, ExportWorker
from timeline import TimelineWidget, VolumeSlider
from waveform_worker import WaveformWorker, WaveformCache


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音视频剪辑工具")
        self.resize(1400, 900)
        self._worker = None
        self._waveform_worker = None
        self._current_clip = None
        self._total_duration = 0.0
        self._playhead_timer = QTimer()
        self._playhead_timer.timeout.connect(self._advance_playhead)
        self._playhead_step = 0.1
        self._is_playing = False
        self._init_ui()
        self._center_window()
        self._start_waveform_worker()

    def _center_window(self):
        screen = QApplication.primaryScreen().geometry()
        center_point = screen.center()
        self.move(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2)

    def _init_ui(self):
        self._create_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        tool_bar = QHBoxLayout()
        self._btn_add_video = QPushButton("导入视频")
        self._btn_add_video.setMinimumSize(QSize(100, 32))
        self._btn_add_video.clicked.connect(self._import_video)

        self._btn_add_audio = QPushButton("导入音频")
        self._btn_add_audio.setMinimumSize(QSize(100, 32))
        self._btn_add_audio.clicked.connect(self._import_audio)

        self._btn_export = QPushButton("导出项目")
        self._btn_export.setMinimumSize(QSize(100, 32))
        self._btn_export.clicked.connect(self._show_export_dialog)

        self._btn_clear = QPushButton("清空轨道")
        self._btn_clear.setMinimumSize(QSize(100, 32))
        self._btn_clear.clicked.connect(self._clear_timeline)

        zoom_label = QLabel("缩放:")
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setMinimum(10)
        self._zoom_slider.setMaximum(200)
        self._zoom_slider.setValue(50)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)

        self._zoom_value = QLabel("50px/s")
        self._zoom_value.setMinimumWidth(60)

        tool_bar.addWidget(self._btn_add_video)
        tool_bar.addWidget(self._btn_add_audio)
        tool_bar.addSpacing(20)

        self._btn_play = QPushButton("▶ 播放")
        self._btn_play.setMinimumSize(QSize(80, 32))
        self._btn_play.clicked.connect(self._toggle_play)

        self._btn_stop = QPushButton("⏹ 停止")
        self._btn_stop.setMinimumSize(QSize(80, 32))
        self._btn_stop.clicked.connect(self._stop_playhead)

        self._playhead_label = QLabel("播放头: 0.00 秒")
        self._playhead_label.setMinimumWidth(120)

        tool_bar.addWidget(self._btn_play)
        tool_bar.addWidget(self._btn_stop)
        tool_bar.addWidget(self._playhead_label)
        tool_bar.addSpacing(20)

        tool_bar.addWidget(self._btn_export)
        tool_bar.addWidget(self._btn_clear)
        tool_bar.addSpacing(20)
        tool_bar.addWidget(zoom_label)
        tool_bar.addWidget(self._zoom_slider)
        tool_bar.addWidget(self._zoom_value)
        tool_bar.addStretch()

        main_layout.addLayout(tool_bar)

        self._init_ui_remaining()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件")
        import_video_act = QAction("导入视频", self)
        import_video_act.setShortcut(QKeySequence("Ctrl+O"))
        import_video_act.triggered.connect(self._import_video)
        file_menu.addAction(import_video_act)

        import_audio_act = QAction("导入音频", self)
        import_audio_act.setShortcut(QKeySequence("Ctrl+Shift+O"))
        import_audio_act.triggered.connect(self._import_audio)
        file_menu.addAction(import_audio_act)

        file_menu.addSeparator()
        export_act = QAction("导出项目", self)
        export_act.setShortcut(QKeySequence("Ctrl+E"))
        export_act.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_act)

        file_menu.addSeparator()
        exit_act = QAction("退出", self)
        exit_act.setShortcut(QKeySequence("Ctrl+Q"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        edit_menu = menu_bar.addMenu("编辑")
        clear_act = QAction("清空轨道", self)
        clear_act.setShortcut(QKeySequence("Ctrl+Del"))
        clear_act.triggered.connect(self._clear_timeline)
        edit_menu.addAction(clear_act)

        edit_menu.addSeparator()
        add_track_act = QAction("添加轨道", self)
        add_track_act.setShortcut(QKeySequence("Ctrl+T"))
        add_track_act.triggered.connect(self._add_track)
        edit_menu.addAction(add_track_act)

        remove_track_act = QAction("移除最后轨道", self)
        remove_track_act.setShortcut(QKeySequence("Ctrl+Shift+T"))
        remove_track_act.triggered.connect(self._remove_track)
        edit_menu.addAction(remove_track_act)

        view_menu = menu_bar.addMenu("视图")
        zoom_in_act = QAction("放大", self)
        zoom_in_act.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_act.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_act)

        zoom_out_act = QAction("缩小", self)
        zoom_out_act.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_act.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_act)

        view_menu.addSeparator()
        reset_zoom_act = QAction("重置缩放", self)
        reset_zoom_act.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_act.triggered.connect(self._reset_zoom)
        view_menu.addAction(reset_zoom_act)

    def _zoom_in(self):
        current = self._zoom_slider.value()
        self._zoom_slider.setValue(min(current + 20, 200))

    def _zoom_out(self):
        current = self._zoom_slider.value()
        self._zoom_slider.setValue(max(current - 20, 10))

    def _reset_zoom(self):
        self._zoom_slider.setValue(50)

    def _start_waveform_worker(self):
        self._waveform_worker = WaveformWorker(self)
        self._waveform_worker.waveform_ready.connect(self._on_waveform_ready)
        self._timeline.set_waveform_worker(self._waveform_worker)
        self._waveform_worker.start()

    def _on_waveform_ready(self, file_path, data):
        if data and data.valid:
            self._timeline._on_waveform_ready(file_path, data)
        self._status.showMessage(f"波形生成完成: {os.path.basename(file_path)}")

    def _toggle_play(self):
        if self._is_playing:
            self._is_playing = False
            self._playhead_timer.stop()
            self._btn_play.setText("▶ 播放")
        else:
            clips = self._timeline.get_all_clips()
            if clips:
                self._total_duration = max(c.timeline_end for c in clips)
            else:
                self._total_duration = 60.0

            self._is_playing = True
            self._playhead_timer.start(int(self._playhead_step * 1000))
            self._btn_play.setText("⏸ 暂停")

    def _stop_playhead(self):
        self._is_playing = False
        self._playhead_timer.stop()
        self._timeline.set_playhead(0)
        self._playhead_label.setText("播放头: 0.00 秒")
        self._btn_play.setText("▶ 播放")

    def _advance_playhead(self):
        current = self._timeline.get_playhead()
        new_time = current + self._playhead_step
        if new_time >= self._total_duration:
            new_time = 0
        self._timeline.set_playhead(new_time)
        self._playhead_label.setText("播放头: {:.2f} 秒".format(new_time))

    def closeEvent(self, event):
        if self._waveform_worker:
            self._waveform_worker.stop()
        event.accept()

    def _init_ui_remaining(self):
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        media_group = QGroupBox("媒体库")
        media_layout = QVBoxLayout(media_group)

        self._media_list = QListWidget()
        self._media_list.itemDoubleClicked.connect(self._on_media_double_clicked)
        media_layout.addWidget(self._media_list)

        add_to_timeline_layout = QHBoxLayout()
        self._track_combo = QComboBox()
        self._track_combo.addItem("轨道 1", 0)
        self._track_combo.addItem("轨道 2", 1)
        self._btn_add_to_track = QPushButton("添加到轨道")
        self._btn_add_to_track.clicked.connect(self._add_selected_to_track)
        add_to_timeline_layout.addWidget(self._track_combo)
        add_to_timeline_layout.addWidget(self._btn_add_to_track)
        media_layout.addLayout(add_to_timeline_layout)

        left_layout.addWidget(media_group)

        clip_group = QGroupBox("片段设置")
        clip_layout = QFormLayout(clip_group)

        self._clip_name = QLabel("-")
        self._clip_start = QDoubleSpinBox()
        self._clip_start.setRange(0, 99999)
        self._clip_start.setDecimals(2)
        self._clip_start.setSingleStep(0.1)
        self._clip_start.setSuffix(" 秒")
        self._clip_start.valueChanged.connect(self._on_clip_start_changed)

        self._clip_end = QDoubleSpinBox()
        self._clip_end.setRange(0, 99999)
        self._clip_end.setDecimals(2)
        self._clip_end.setSingleStep(0.1)
        self._clip_end.setSuffix(" 秒")
        self._clip_end.valueChanged.connect(self._on_clip_end_changed)

        self._clip_timeline_start = QDoubleSpinBox()
        self._clip_timeline_start.setRange(0, 99999)
        self._clip_timeline_start.setDecimals(2)
        self._clip_timeline_start.setSingleStep(0.1)
        self._clip_timeline_start.setSuffix(" 秒")
        self._clip_timeline_start.valueChanged.connect(self._on_timeline_start_changed)

        volume_label = QLabel("音量:")
        self._volume_slider = QSlider(Qt.Horizontal)
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(200)
        self._volume_slider.setValue(100)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._volume_label = QLabel("100%")
        self._volume_label.setMinimumWidth(50)

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self._volume_slider)
        volume_layout.addWidget(self._volume_label)

        clip_layout.addRow("文件:", self._clip_name)
        clip_layout.addRow("剪切起点:", self._clip_start)
        clip_layout.addRow("剪切终点:", self._clip_end)
        clip_layout.addRow("轨道位置:", self._clip_timeline_start)
        clip_layout.addRow(volume_layout)

        self._btn_delete_clip = QPushButton("删除选中片段")
        self._btn_delete_clip.clicked.connect(self._delete_selected_clip)
        clip_layout.addRow(self._btn_delete_clip)

        left_layout.addWidget(clip_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        tracks_group = QGroupBox("轨道管理")
        tracks_layout = QHBoxLayout(tracks_group)

        self._btn_add_track = QPushButton("添加轨道")
        self._btn_add_track.clicked.connect(self._add_track)
        self._btn_remove_track = QPushButton("移除最后轨道")
        self._btn_remove_track.clicked.connect(self._remove_track)
        self._track_count_label = QLabel("轨道数: 2")
        tracks_layout.addWidget(self._btn_add_track)
        tracks_layout.addWidget(self._btn_remove_track)
        tracks_layout.addStretch()
        tracks_layout.addWidget(self._track_count_label)

        right_layout.addWidget(tracks_group)

        timeline_group = QGroupBox("时间线")
        timeline_layout = QVBoxLayout(timeline_group)
        self._timeline = TimelineWidget()
        timeline_layout.addWidget(self._timeline)
        right_layout.addWidget(timeline_group, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([350, 1000])

        main_layout.addWidget(splitter, 1)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 100)
        main_layout.addWidget(self._progress)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("就绪")

        self._refresh_track_combo()

    def _import_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv);;所有文件 (*.*)")
        if file_path:
            self._add_media_item(file_path)

    def _import_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", 
            "音频文件 (*.mp3 *.wav *.flac *.aac *.m4a *.ogg);;所有文件 (*.*)")
        if file_path:
            self._add_media_item(file_path)

    def _add_media_item(self, file_path):
        info = MediaInfo.get_info(file_path)
        if info.duration <= 0:
            QMessageBox.warning(self, "错误", "无法读取媒体文件，请确保已安装 FFmpeg")
            return

        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.UserRole, file_path)
        item.setData(Qt.UserRole + 1, info)

        if info.has_video:
            type_str = "视频"
        else:
            type_str = "音频"

        item.setToolTip(f"{file_path}\n{type_str} - 时长: {info.duration:.2f} 秒")
        self._media_list.addItem(item)
        self._status.showMessage(f"已导入: {os.path.basename(file_path)} ({info.duration:.2f}秒)")

    def _on_media_double_clicked(self, item):
        self._add_media_to_track(item, self._track_combo.currentData())

    def _add_selected_to_track(self):
        for item in self._media_list.selectedItems():
            self._add_media_to_track(item, self._track_combo.currentData())

    def _add_media_to_track(self, item, track_index):
        file_path = item.data(Qt.UserRole)
        info = item.data(Qt.UserRole + 1)

        track = self._timeline.tracks[track_index] if track_index < len(self._timeline.tracks) else None
        if not track:
            return

        start = 0
        end = info.duration
        timeline_start = 0

        for clip in track.clips:
            if clip.timeline_end > timeline_start:
                timeline_start = clip.timeline_end

        clip = Clip(file_path, start, end, timeline_start, 1.0, track_index)
        track.add_clip(clip)

        self._status.showMessage(f"已添加到轨道 {track_index + 1}: {os.path.basename(file_path)}")
        self._select_clip(clip)

    def _on_zoom_changed(self, value):
        self._timeline.set_zoom(value)
        self._zoom_value.setText(f"{value}px/s")

    def _select_clip(self, clip):
        self._current_clip = clip
        self._clip_name.setText(os.path.basename(clip.file_path))

        blocked = self._clip_start.blockSignals(True)
        self._clip_start.setValue(clip.start)
        self._clip_start.blockSignals(blocked)

        blocked = self._clip_end.blockSignals(True)
        self._clip_end.setValue(clip.end)
        self._clip_end.blockSignals(blocked)

        blocked = self._clip_timeline_start.blockSignals(True)
        self._clip_timeline_start.setValue(clip.timeline_start)
        self._clip_timeline_start.blockSignals(blocked)

        blocked = self._volume_slider.blockSignals(True)
        self._volume_slider.setValue(int(clip.volume * 100))
        self._volume_slider.blockSignals(blocked)
        self._volume_label.setText(f"{int(clip.volume * 100)}%")

    def _on_clip_start_changed(self, value):
        if self._current_clip and value < self._current_clip.end:
            self._current_clip.start = value
            self._timeline.update()

    def _on_clip_end_changed(self, value):
        if self._current_clip and value > self._current_clip.start:
            self._current_clip.end = value
            self._timeline.update()

    def _on_timeline_start_changed(self, value):
        if self._current_clip:
            self._current_clip.timeline_start = value
            self._timeline.update()

    def _on_volume_changed(self, value):
        if self._current_clip:
            self._current_clip.volume = value / 100.0
            self._volume_label.setText(f"{value}%")
            self._timeline.update()

    def _delete_selected_clip(self):
        if not self._current_clip:
            return

        for track in self._timeline.tracks:
            if self._current_clip in track.clips:
                track.remove_clip(self._current_clip)
                break

        self._current_clip = None
        self._clip_name.setText("-")
        self._timeline.update()

    def _add_track(self):
        track = self._timeline.add_track()
        self._track_combo.addItem(f"轨道 {track.index + 1}", track.index)
        self._track_count_label.setText(f"轨道数: {len(self._timeline.tracks)}")

    def _remove_track(self):
        if len(self._timeline.tracks) > 1:
            last_idx = len(self._timeline.tracks) - 1
            self._timeline.remove_track(last_idx)
            self._track_combo.removeItem(self._track_combo.count() - 1)
            self._track_count_label.setText(f"轨道数: {len(self._timeline.tracks)}")

    def _refresh_track_combo(self):
        self._track_combo.clear()
        for i in range(len(self._timeline.tracks)):
            self._track_combo.addItem(f"轨道 {i + 1}", i)
        self._track_count_label.setText(f"轨道数: {len(self._timeline.tracks)}")

    def _clear_timeline(self):
        self._timeline.clear_all_clips()
        self._current_clip = None
        self._clip_name.setText("-")
        self._status.showMessage("轨道已清空")

    def _show_export_dialog(self):
        clips = self._timeline.get_all_clips()
        if not clips:
            QMessageBox.information(self, "提示", "没有可导出的片段")
            return

        export_dialog = ExportDialog(self, clips)
        if export_dialog.exec_() == export_dialog.Accepted:
            self._start_export(export_dialog.config, export_dialog.output_path)

    def _start_export(self, config, output_path):
        if not output_path:
            return

        clips = self._timeline.get_all_clips()
        if not clips:
            return

        config.output_path = output_path

        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._btn_export.setEnabled(False)
        self._status.showMessage("开始导出...")

        self._worker = ExportWorker(clips, config)
        self._worker.progress.connect(self._on_export_progress)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.log.connect(lambda msg: print(msg))
        self._worker.start()

    def _on_export_progress(self, value):
        self._progress.setValue(value)
        self._status.showMessage(f"导出中... {value}%")

    def _on_export_finished(self, success, message):
        self._progress.setVisible(False)
        self._btn_export.setEnabled(True)
        if success:
            self._status.showMessage(message)
            QMessageBox.information(self, "完成", message)
        else:
            self._status.showMessage(message)
            QMessageBox.warning(self, "导出失败", message)


class ExportDialog(QDialog):
    def __init__(self, parent, clips):
        super().__init__(parent)
        self._clips = clips
        self.config = ExportConfig()
        self.output_path = ""

        self.setWindowTitle("导出设置")
        self.resize(450, 350)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self._codec_combo = QComboBox()
        self._codec_combo.addItem("H.264 (libx264)", "libx264")
        self._codec_combo.addItem("H.265 (libx265)", "libx265")
        self._codec_combo.addItem("VP9", "libvpx-vp9")

        self._audio_combo = QComboBox()
        self._audio_combo.addItem("AAC", "aac")
        self._audio_combo.addItem("MP3", "libmp3lame")
        self._audio_combo.addItem("Opus", "libopus")

        self._resolution_combo = QComboBox()
        self._resolution_combo.addItem("1920x1080 (1080p)", "1920x1080")
        self._resolution_combo.addItem("1280x720 (720p)", "1280x720")
        self._resolution_combo.addItem("3840x2160 (4K)", "3840x2160")
        self._resolution_combo.addItem("854x480 (480p)", "854x480")

        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 120)
        self._fps_spin.setValue(30)
        self._fps_spin.setSuffix(" fps")

        self._video_bitrate_combo = QComboBox()
        self._video_bitrate_combo.addItem("2 Mbps", "2M")
        self._video_bitrate_combo.addItem("4 Mbps (推荐)", "4M")
        self._video_bitrate_combo.addItem("8 Mbps", "8M")
        self._video_bitrate_combo.addItem("12 Mbps", "12M")
        self._video_bitrate_combo.addItem("16 Mbps", "16M")
        self._video_bitrate_combo.setCurrentIndex(1)

        self._audio_bitrate_combo = QComboBox()
        self._audio_bitrate_combo.addItem("128 kbps", "128k")
        self._audio_bitrate_combo.addItem("192 kbps (推荐)", "192k")
        self._audio_bitrate_combo.addItem("256 kbps", "256k")
        self._audio_bitrate_combo.addItem("320 kbps", "320k")
        self._audio_bitrate_combo.setCurrentIndex(1)

        self._preset_combo = QComboBox()
        self._preset_combo.addItem("ultrafast", "ultrafast")
        self._preset_combo.addItem("veryfast", "veryfast")
        self._preset_combo.addItem("fast", "fast")
        self._preset_combo.addItem("medium (平衡)", "medium")
        self._preset_combo.addItem("slow", "slow")
        self._preset_combo.addItem("veryslow", "veryslow")
        self._preset_combo.setCurrentIndex(3)

        form.addRow("视频编码器:", self._codec_combo)
        form.addRow("音频编码器:", self._audio_combo)
        form.addRow("分辨率:", self._resolution_combo)
        form.addRow("帧率:", self._fps_spin)
        form.addRow("视频码率:", self._video_bitrate_combo)
        form.addRow("音频码率:", self._audio_bitrate_combo)
        form.addRow("编码预设:", self._preset_combo)

        layout.addLayout(form)

        output_layout = QHBoxLayout()
        self._output_edit = QPushButton("点击选择输出文件...")
        self._output_edit.clicked.connect(self._select_output)
        output_layout.addWidget(self._output_edit, 1)
        layout.addLayout(output_layout)

        info = QLabel(f"将导出 {len(self._clips)} 个片段")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        layout.addStretch()

        btns = QHBoxLayout()
        self._btn_ok = QPushButton("开始导出")
        self._btn_ok.clicked.connect(self._on_ok)
        self._btn_ok.setEnabled(False)
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.clicked.connect(self.close)
        btns.addStretch()
        btns.addWidget(self._btn_ok)
        btns.addWidget(self._btn_cancel)
        layout.addLayout(btns)

    def _select_output(self):
        default_name = "output.mp4"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存为", default_name, "MP4 视频 (*.mp4);;MKV 视频 (*.mkv);;所有文件 (*.*)")
        if file_path:
            self.output_path = file_path
            self._output_edit.setText(os.path.basename(file_path))
            self._btn_ok.setEnabled(True)

    def _on_ok(self):
        self.config.video_codec = self._codec_combo.currentData()
        self.config.audio_codec = self._audio_combo.currentData()
        self.config.resolution = self._resolution_combo.currentData()
        self.config.fps = self._fps_spin.value()
        self.config.video_bitrate = self._video_bitrate_combo.currentData()
        self.config.audio_bitrate = self._audio_bitrate_combo.currentData()
        self.config.preset = self._preset_combo.currentData()
        self.close()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
