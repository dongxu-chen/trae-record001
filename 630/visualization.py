import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import time


class BeatVisualizer:
    def __init__(
        self,
        sr=44100,
        hop_length=512,
        window_duration=10,
        max_points=500,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.window_duration = window_duration
        self.max_points = max_points

        self.time_history = deque(maxlen=max_points)
        self.bpm_history = deque(maxlen=max_points)
        self.confidence_history = deque(maxlen=max_points)
        self.onset_history = deque(maxlen=max_points)
        self.beat_markers = deque(maxlen=100)
        self.downbeat_markers = deque(maxlen=25)

        self.fig, self.axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
        self.fig.suptitle('Music Beat Tracker - Real-time Visualization', fontsize=14, fontweight='bold')

        self.ax_onset, self.ax_bpm, self.ax_phase = self.axes

        self.onset_line, = self.ax_onset.plot([], [], 'b-', label='Onset Envelope', linewidth=1)
        self.beat_vlines = []
        self.downbeat_vlines = []
        self.ax_onset.set_ylabel('Onset Strength')
        self.ax_onset.set_title('Onset Envelope with Beat Markers')
        self.ax_onset.legend(loc='upper right')
        self.ax_onset.grid(True, alpha=0.3)

        self.bpm_line, = self.ax_bpm.plot([], [], 'r-', label='BPM', linewidth=2)
        self.bpm_target_line, = self.ax_bpm.plot([], [], 'g--', label='Locked BPM', linewidth=1.5, alpha=0.7)
        self.ax_bpm.set_ylabel('BPM')
        self.ax_bpm.set_title('BPM Tracking')
        self.ax_bpm.legend(loc='upper right')
        self.ax_bpm.grid(True, alpha=0.3)

        self.confidence_line, = self.ax_phase.plot([], [], 'purple', label='Confidence', linewidth=2)
        self.lock_line, = self.ax_phase.plot([], [], 'orange', label='Lock Status', linewidth=1.5, alpha=0.7)
        self.ax_phase.set_xlabel('Time (s)')
        self.ax_phase.set_ylabel('Confidence')
        self.ax_phase.set_title('Tracking Confidence and Lock Status')
        self.ax_phase.legend(loc='upper right')
        self.ax_phase.grid(True, alpha=0.3)

        self.phase_indicator = self.ax_phase.text(
            0.02, 0.95, '', transform=self.ax_phase.transAxes,
            fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )

        self.status_text = self.fig.text(
            0.02, 0.02, '', fontsize=11,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        )

        self.current_bpm = 0.0
        self.current_confidence = 0.0
        self.is_locked = False
        self.locked_bpm = 0.0
        self.beat_phase = 0.0
        self.start_time = time.time()

        self.anim = None
        self.is_running = False

    def update_data(
        self,
        onset_env=None,
        beat_times=None,
        downbeat_times=None,
        bpm=0.0,
        confidence=0.0,
        is_locked=False,
        locked_bpm=0.0,
        beat_phase=0.0,
    ):
        current_time = time.time() - self.start_time

        self.time_history.append(current_time)
        self.bpm_history.append(bpm)
        self.confidence_history.append(confidence)

        if onset_env is not None and len(onset_env) > 0:
            self.onset_history.append(np.mean(onset_env[-5:]))
        else:
            self.onset_history.append(0.0)

        if beat_times is not None and len(beat_times) > 0:
            for bt in beat_times[-5:]:
                if bt > current_time - self.window_duration:
                    self.beat_markers.append(bt)

        if downbeat_times is not None and len(downbeat_times) > 0:
            for dbt in downbeat_times[-2:]:
                if dbt > current_time - self.window_duration:
                    self.downbeat_markers.append(dbt)

        self.current_bpm = bpm
        self.current_confidence = confidence
        self.is_locked = is_locked
        self.locked_bpm = locked_bpm
        self.beat_phase = beat_phase

    def _init_plot(self):
        self.ax_onset.set_xlim(0, self.window_duration)
        self.ax_onset.set_ylim(0, 1.0)

        self.ax_bpm.set_ylim(40, 220)

        self.ax_phase.set_ylim(0, 1.0)

        for line in [self.onset_line, self.bpm_line, self.bpm_target_line, self.confidence_line, self.lock_line]:
            line.set_data([], [])

        for vline in self.beat_vlines + self.downbeat_vlines:
            vline.remove()
        self.beat_vlines = []
        self.downbeat_vlines = []

        return (
            self.onset_line, self.bpm_line, self.bpm_target_line,
            self.confidence_line, self.lock_line, self.phase_indicator, self.status_text
        )

    def _update_plot(self, frame):
        current_time = time.time() - self.start_time
        x_min = max(0, current_time - self.window_duration)
        x_max = x_min + self.window_duration

        for ax in self.axes:
            ax.set_xlim(x_min, x_max)

        for vline in self.beat_vlines + self.downbeat_vlines:
            vline.remove()
        self.beat_vlines = []
        self.downbeat_vlines = []

        time_array = np.array(self.time_history)
        mask = time_array >= x_min
        filtered_time = time_array[mask]

        if len(filtered_time) > 0:
            onset_array = np.array(self.onset_history)[mask]
            self.onset_line.set_data(filtered_time, onset_array)

            bpm_array = np.array(self.bpm_history)[mask]
            self.bpm_line.set_data(filtered_time, bpm_array)

            confidence_array = np.array(self.confidence_history)[mask]
            self.confidence_line.set_data(filtered_time, confidence_array)

            if self.is_locked and self.locked_bpm > 0:
                lock_y = np.ones_like(filtered_time) * 0.9
                self.lock_line.set_data(filtered_time, lock_y)
                target_y = np.ones_like(filtered_time) * self.locked_bpm
                self.bpm_target_line.set_data(filtered_time, target_y)
            else:
                self.lock_line.set_data([], [])
                self.bpm_target_line.set_data([], [])

        for bt in self.beat_markers:
            if x_min <= bt <= x_max:
                vline = self.ax_onset.axvline(bt, color='red', alpha=0.5, linestyle='--', linewidth=1)
                self.beat_vlines.append(vline)

        for dbt in self.downbeat_markers:
            if x_min <= dbt <= x_max:
                vline = self.ax_onset.axvline(dbt, color='green', alpha=0.8, linestyle='-', linewidth=2)
                self.downbeat_vlines.append(vline)

        phase_color = 'red' if self.beat_phase < 0.1 else 'green'
        self.phase_indicator.set_text(
            f'Phase: {self.beat_phase:.2f} | '
            f'Style: {getattr(self, "current_style", "generic")}'
        )
        self.phase_indicator.set_color(phase_color)

        lock_status = 'LOCKED' if self.is_locked else 'UNLOCKED'
        lock_color = 'green' if self.is_locked else 'red'
        self.status_text.set_text(
            f'BPM: {self.current_bpm:.1f} | '
            f'Locked BPM: {self.locked_bpm:.1f} | '
            f'Confidence: {self.current_confidence:.2f} | '
            f'Status: [{lock_status}]'
        )
        self.status_text.set_color(lock_color)

        return (
            self.onset_line, self.bpm_line, self.bpm_target_line,
            self.confidence_line, self.lock_line, self.phase_indicator, self.status_text
        )

    def start(self, interval=50):
        if self.is_running:
            return

        self.is_running = True
        self.anim = FuncAnimation(
            self.fig,
            self._update_plot,
            init_func=self._init_plot,
            interval=interval,
            blit=True,
        )
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        plt.show(block=False)

    def stop(self):
        self.is_running = False
        if self.anim is not None:
            self.anim.event_source.stop()
            self.anim = None

    def close(self):
        self.stop()
        plt.close(self.fig)

    def set_style(self, style):
        self.current_style = style

    def save_screenshot(self, filepath):
        self.fig.savefig(filepath, dpi=150, bbox_inches='tight')


class OfflineVisualizer:
    def __init__(self, sr=44100, hop_length=512):
        self.sr = sr
        self.hop_length = hop_length

    def plot_results(self, y, onset_env, beat_times, downbeat_times, bpm, confidence):
        fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
        fig.suptitle(
            f'Music Beat Tracking Results | BPM: {bpm:.1f} | Confidence: {confidence:.2f}',
            fontsize=14, fontweight='bold'
        )

        ax_wave, ax_onset, ax_beats, ax_spec = axes

        times = np.arange(len(y)) / self.sr
        ax_wave.plot(times, y, 'b-', linewidth=0.5, alpha=0.7)
        ax_wave.set_ylabel('Amplitude')
        ax_wave.set_title('Audio Waveform')
        ax_wave.grid(True, alpha=0.3)

        for bt in beat_times:
            ax_wave.axvline(bt, color='red', alpha=0.3, linestyle='--', linewidth=1)
        for dbt in downbeat_times:
            ax_wave.axvline(dbt, color='green', alpha=0.7, linestyle='-', linewidth=1.5)

        onset_times = np.arange(len(onset_env)) * self.hop_length / self.sr
        ax_onset.plot(onset_times, onset_env, 'b-', linewidth=1)
        ax_onset.set_ylabel('Onset Strength')
        ax_onset.set_title('Onset Envelope')
        ax_onset.grid(True, alpha=0.3)

        for bt in beat_times:
            ax_onset.axvline(bt, color='red', alpha=0.3, linestyle='--', linewidth=1)
        for dbt in downbeat_times:
            ax_onset.axvline(dbt, color='green', alpha=0.7, linestyle='-', linewidth=1.5)

        beat_intervals = np.diff(beat_times) if len(beat_times) > 1 else [0]
        ax_beats.stem(
            beat_times[:-1] if len(beat_times) > 1 else beat_times,
            beat_intervals,
            basefmt='b-',
            use_line_collection=True,
        )
        ax_beats.set_ylabel('Beat Interval (s)')
        ax_beats.set_title(f'Beat Intervals | Mean: {np.mean(beat_intervals):.3f}s | BPM: {bpm:.1f}')
        ax_beats.grid(True, alpha=0.3)

        D = librosa.amplitude_to_db(
            np.abs(librosa.stft(y, hop_length=self.hop_length)),
            ref=np.max
        )
        librosa.display.specshow(
            D,
            sr=self.sr,
            hop_length=self.hop_length,
            x_axis='time',
            y_axis='log',
            ax=ax_spec,
        )
        ax_spec.set_title('Spectrogram')
        ax_spec.set_ylabel('Frequency (Hz)')
        ax_spec.set_xlabel('Time (s)')

        for bt in beat_times:
            ax_spec.axvline(bt, color='white', alpha=0.3, linestyle='--', linewidth=1)
        for dbt in downbeat_times:
            ax_spec.axvline(dbt, color='red', alpha=0.7, linestyle='-', linewidth=1.5)

        plt.tight_layout()
        return fig

    def show(self):
        plt.show()

    def save(self, filepath):
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()


import librosa
import librosa.display
