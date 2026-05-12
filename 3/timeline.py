import os
from PyQt5.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSlider, QPushButton, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient

from export import Clip, MediaInfo
from waveform_worker import WaveformCache


class VolumeSlider(QSlider):
    def __init__(self, clip, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.clip = clip
        self.setMinimum(0)
        self.setMaximum(200)
        self.setValue(int(clip.volume * 100))
        self.setToolTip("音量: {}%".format(int(clip.volume * 100)))
        self.valueChanged.connect(self._on_value_changed)
        self.setFixedWidth(80)

    def _on_value_changed(self, value):
        self.clip.volume = value / 100.0
        self.setToolTip("音量: {}%".format(value))


class TrackWidget(QFrame):
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self.index = index
        self._clips = []
        self._clip_info_cache = {}
        self._pixel_per_second = 50
        self._track_height = 60
        self._header_width = 120
        self.setMinimumHeight(self._track_height)
        self._selected_clip = None
        self._hover_clip = None
        self._drag_clip = None
        self._drag_offset = 0
        self._resizing = None
        self._resize_side = None
        self._playhead = 0
        self._last_rects = {}
        self._colors = {}
        self._painter_path = QPainterPath()

    def add_clip(self, clip):
        self._clips.append(clip)
        self.update()

    def remove_clip(self, clip):
        if clip in self._clips:
            self._clips.remove(clip)
        self.update()

    def clear_clips(self):
        self._clips.clear()
        self.update()

    @property
    def clips(self):
        return self._clips

    def set_pixel_per_second(self, value):
        self._pixel_per_second = value
        self.update()

    def _clip_rect(self, clip):
        x = self._header_width + int(clip.timeline_start * self._pixel_per_second)
        width = max(int(clip.duration * self._pixel_per_second), 20)
        return QRect(x, 5, width, self._track_height - 10)

    def _clip_at(self, pos):
        for clip in reversed(self._clips):
            rect = self._clip_rect(clip)
            if rect.contains(pos):
                return clip, rect
        return None, None

    def _get_cached_info(self, clip):
        fp = clip.file_path
        if fp not in self._clip_info_cache:
            self._clip_info_cache[fp] = MediaInfo.get_info(fp)
        return self._clip_info_cache[fp]

    def _draw_waveform(self, painter, clip, rect):
        cache = WaveformCache.instance()
        waveform = cache.get(clip.file_path)

        if not waveform or not waveform.valid or not waveform.peaks:
            painter.setPen(QPen(QColor(180, 180, 200, 100), 1, Qt.DashLine))
            mid_y = rect.top() + rect.height() / 2
            painter.drawLine(rect.left() + 4, int(mid_y), rect.right() - 4, int(mid_y))
            return

        clip_start = clip.start
        clip_end = clip.end
        clip_duration = clip_end - clip_start

        samples_per_pixel = waveform.samples_per_pixel
        total_pixels = len(waveform.peaks)
        actual_duration = waveform.duration

        if actual_duration <= 0 or total_pixels == 0:
            return

        pixels_per_second = total_pixels / actual_duration
        wave_start_pixel = int(clip_start * pixels_per_second)
        wave_end_pixel = int(clip_end * pixels_per_second)
        wave_pixel_count = max(wave_end_pixel - wave_start_pixel, 1)

        clip_pixel_width = rect.width()
        scale = clip_pixel_width / wave_pixel_count if wave_pixel_count > 0 else 1

        mid_y = rect.top() + rect.height() / 2
        max_amplitude = rect.height() / 2 - 3

        color = QColor(200, 220, 255, 200)
        pen = QPen(color, 1)
        painter.setPen(pen)

        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)

        first = True
        for i in range(wave_pixel_count):
            wave_idx = wave_start_pixel + i
            if wave_idx < 0 or wave_idx >= len(waveform.peaks):
                continue

            peak_pos, peak_neg = waveform.peaks[wave_idx]
            x = rect.left() + int(i * scale)

            y_pos = mid_y - abs(peak_pos) * max_amplitude
            y_neg = mid_y + abs(peak_neg) * max_amplitude

            if first:
                path.moveTo(x, y_pos)
                first = False
            else:
                path.lineTo(x, y_pos)

        for i in range(wave_pixel_count - 1, -1, -1):
            wave_idx = wave_start_pixel + i
            if wave_idx < 0 or wave_idx >= len(waveform.peaks):
                continue

            peak_pos, peak_neg = waveform.peaks[wave_idx]
            x = rect.left() + int(i * scale)

            y_neg = mid_y + abs(peak_neg) * max_amplitude
            path.lineTo(x, y_neg)

        path.closeSubpath()

        gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        gradient.setColorAt(0, QColor(100, 180, 255, 120))
        gradient.setColorAt(0.5, QColor(150, 200, 255, 80))
        gradient.setColorAt(1, QColor(100, 180, 255, 120))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        painter.setPen(QPen(QColor(180, 220, 255, 200), 1))
        painter.drawLine(rect.left(), int(mid_y), rect.right(), int(mid_y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        clip_rect = event.rect()

        painter.fillRect(clip_rect, QColor(45, 45, 48))

        header_rect = QRect(0, 0, self._header_width, self.height())
        if header_rect.intersects(clip_rect):
            painter.fillRect(header_rect & clip_rect, QColor(35, 35, 38))

        painter.setPen(QColor(60, 60, 64))
        painter.drawLine(self._header_width, 0, self._header_width, self.height())

        painter.setPen(QColor(200, 200, 200))
        painter.drawText(10, 20, "轨道 {}".format(self.index + 1))

        white_pen = QPen(QColor(255, 255, 255), 1, Qt.SolidLine)
        text_color = QColor(230, 230, 230)
        vol_color = QColor(255, 215, 0)

        for clip in self._clips:
            rect = self._clip_rect(clip)
            if not rect.intersects(clip_rect):
                continue

            info = self._get_cached_info(clip)
            is_video = info.has_video

            if clip == self._selected_clip:
                color = QColor(100, 149, 237)
            elif clip == self._hover_clip:
                color = QColor(80, 80, 120)
            elif is_video:
                color = QColor(70, 130, 180)
            else:
                color = QColor(70, 150, 100)

            painter.setPen(white_pen)
            painter.setBrush(QBrush(color))
            self._painter_path = QPainterPath()
            self._painter_path.addRoundedRect(rect, 4, 4)
            painter.drawPath(self._painter_path)

            inner_rect = rect.adjusted(2, 2, -2, -2)
            self._draw_waveform(painter, clip, inner_rect)

            name = os.path.basename(clip.file_path)
            painter.setPen(text_color)
            text_rect = rect.adjusted(8, 0, -8, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextSingleLine, name)

            if clip.volume != 1.0:
                painter.setPen(vol_color)
                painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, 
                             "  音量: {}%".format(int(clip.volume * 100)))

        if self._playhead > 0:
            x = self._header_width + int(self._playhead * self._pixel_per_second)
            painter.setPen(QPen(QColor(255, 80, 80), 2))
            painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            clip, rect = self._clip_at(event.pos())
            if clip:
                self._selected_clip = clip
                self._drag_clip = clip
                self._drag_offset = event.pos().x() - rect.left()

                if event.pos().x() <= rect.left() + 8:
                    self._resizing = clip
                    self._resize_side = "left"
                elif event.pos().x() >= rect.right() - 8:
                    self._resizing = clip
                    self._resize_side = "right"
                else:
                    self._resizing = None
                self.update()

    def _repaint_clip_area(self, clip):
        if not clip:
            return
        rect = self._clip_rect(clip)
        repaint_rect = rect.adjusted(-20, -2, 20, 2)
        self.update(repaint_rect)

    def mouseMoveEvent(self, event):
        active_clip = self._drag_clip or self._resizing
        old_rect = None

        if active_clip:
            old_rect = self._clip_rect(active_clip)

        clip, rect = self._clip_at(event.pos())
        if self._resizing:
            self._handle_resize(event)
        elif self._drag_clip:
            self._handle_drag(event)
        else:
            if self._hover_clip != clip:
                old_hover = self._hover_clip
                self._hover_clip = clip
                if old_hover:
                    self._repaint_clip_area(old_hover)
                if clip:
                    self._repaint_clip_area(clip)
                return
            return

        if active_clip:
            new_rect = self._clip_rect(active_clip)
            union = old_rect.united(new_rect)
            union_rect = union.adjusted(-20, -2, 20, 2)
            self.update(union_rect)

    def mouseReleaseEvent(self, event):
        active_clip = self._drag_clip or self._resizing
        self._drag_clip = None
        self._resizing = None
        if active_clip:
            self._repaint_clip_area(active_clip)

    def _handle_drag(self, event):
        if self._drag_clip:
            new_x = event.pos().x() - self._header_width
            new_start = max(0, new_x / self._pixel_per_second)
            self._drag_clip.timeline_start = new_start

    def _handle_resize(self, event):
        if not self._resizing:
            return

        clip = self._resizing
        pos = event.pos().x() - self._header_width
        time = pos / self._pixel_per_second

        if self._resize_side == "left":
            old_start = clip.timeline_start
            new_start = max(0, time)
            if new_start < clip.timeline_start + clip.duration - 0.5:
                clip.start += (new_start - old_start)
                clip.timeline_start = new_start
        else:
            new_end = max(clip.start + 0.5, time)
            clip.end = clip.start + (new_end - clip.timeline_start)


class TimelineWidget(QWidget):
    clip_selected = pyqtSignal(object)
    clip_changed = pyqtSignal()
    playhead_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks = []
        self._pixel_per_second = 50
        self._playhead = 0
        self._total_duration = 60
        self._waveform_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_contents = QWidget()
        self._tracks_layout = QVBoxLayout(self._scroll_contents)
        self._tracks_layout.setContentsMargins(0, 0, 0, 0)
        self._tracks_layout.setSpacing(2)
        self._tracks_layout.addStretch()
        self._scroll.setWidget(self._scroll_contents)
        layout.addWidget(self._scroll)

        self.add_track()
        self.add_track()

    def set_waveform_worker(self, worker):
        self._waveform_worker = worker

    def _request_waveform_for_clip(self, clip):
        if self._waveform_worker:
            from waveform_worker import WaveformCache
            cache = WaveformCache.instance()
            if not cache.get(clip.file_path) and not cache.is_pending(clip.file_path):
                self._waveform_worker.request_waveform(clip.file_path)

    def _on_waveform_ready(self, file_path, data):
        for track in self._tracks:
            for clip in track.clips:
                if clip.file_path == file_path:
                    track._repaint_clip_area(clip)

    def add_track(self):
        track = TrackWidget(len(self._tracks))
        self._tracks.append(track)
        self._tracks_layout.insertWidget(len(self._tracks_layout) - 1, track)
        return track

    def remove_track(self, index):
        if 0 <= index < len(self._tracks):
            track = self._tracks.pop(index)
            track.deleteLater()

    def add_clip(self, track_index, clip):
        if 0 <= track_index < len(self._tracks):
            self._tracks[track_index].add_clip(clip)
            self._request_waveform_for_clip(clip)

    def get_all_clips(self):
        clips = []
        for track in self._tracks:
            clips.extend(track.clips)
        return clips

    def clear_all_clips(self):
        for track in self._tracks:
            track.clear_clips()

    def set_zoom(self, value):
        self._pixel_per_second = max(10, min(200, value))
        for track in self._tracks:
            track.set_pixel_per_second(self._pixel_per_second)

    def set_playhead(self, time_sec):
        self._playhead = max(0, time_sec)
        for track in self._tracks:
            track._playhead = self._playhead
            track.update()
        self.playhead_changed.emit(self._playhead)

    def get_playhead(self):
        return self._playhead

    def refresh_waveforms(self):
        for track in self._tracks:
            for clip in track.clips:
                self._request_waveform_for_clip(clip)

    @property
    def tracks(self):
        return self._tracks

    @property
    def playhead(self):
        return self._playhead

    @playhead.setter
    def playhead(self, value):
        self.set_playhead(value)
