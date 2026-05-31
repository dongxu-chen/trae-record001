import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from collections import deque
import time


class DanceModel:
    def __init__(self):
        self.joint_names = [
            'head', 'neck', 'torso',
            'shoulder_l', 'elbow_l', 'wrist_l',
            'shoulder_r', 'elbow_r', 'wrist_r',
            'hip_l', 'knee_l', 'ankle_l',
            'hip_r', 'knee_r', 'ankle_r',
        ]

        self.base_positions = {
            'head': np.array([0.0, 1.7, 0.0]),
            'neck': np.array([0.0, 1.55, 0.0]),
            'torso': np.array([0.0, 1.2, 0.0]),
            'shoulder_l': np.array([-0.35, 1.5, 0.0]),
            'elbow_l': np.array([-0.6, 1.2, 0.0]),
            'wrist_l': np.array([-0.8, 0.9, 0.0]),
            'shoulder_r': np.array([0.35, 1.5, 0.0]),
            'elbow_r': np.array([0.6, 1.2, 0.0]),
            'wrist_r': np.array([0.8, 0.9, 0.0]),
            'hip_l': np.array([-0.18, 0.9, 0.0]),
            'knee_l': np.array([-0.18, 0.5, 0.0]),
            'ankle_l': np.array([-0.18, 0.1, 0.0]),
            'hip_r': np.array([0.18, 0.9, 0.0]),
            'knee_r': np.array([0.18, 0.5, 0.0]),
            'ankle_r': np.array([0.18, 0.1, 0.0]),
        }

        self.bones = [
            ('head', 'neck'), ('neck', 'torso'),
            ('neck', 'shoulder_l'), ('shoulder_l', 'elbow_l'), ('elbow_l', 'wrist_l'),
            ('neck', 'shoulder_r'), ('shoulder_r', 'elbow_r'), ('elbow_r', 'wrist_r'),
            ('torso', 'hip_l'), ('hip_l', 'knee_l'), ('knee_l', 'ankle_l'),
            ('torso', 'hip_r'), ('hip_r', 'knee_r'), ('knee_r', 'ankle_r'),
        ]

        self.current_positions = self.base_positions.copy()
        self.dance_intensity = 0.0
        self.last_beat_time = 0.0
        self.beat_phase = 0.0
        self.is_downbeat = False

    def update(self, beat_phase, is_beat, is_downbeat, bpm, intensity=1.0):
        self.beat_phase = beat_phase
        self.is_downbeat = is_downbeat

        if is_beat:
            self.dance_intensity = min(1.0, self.dance_intensity + 0.3 * intensity)
        else:
            self.dance_intensity = max(0.0, self.dance_intensity - 0.02)

        beat_scale = np.sin(2 * np.pi * beat_phase) * self.dance_intensity

        for joint in self.joint_names:
            pos = self.base_positions[joint].copy()

            if 'head' in joint:
                pos[1] += beat_scale * 0.08
                pos[0] += np.sin(2 * np.pi * beat_phase * 2) * 0.03 * self.dance_intensity

            elif 'wrist' in joint:
                side = 1 if 'r' in joint else -1
                pos[1] += beat_scale * 0.2 * side
                pos[2] += np.sin(2 * np.pi * beat_phase * 4) * 0.05 * self.dance_intensity
                if is_downbeat and beat_phase < 0.2:
                    pos[1] -= 0.15 * intensity

            elif 'elbow' in joint:
                side = 1 if 'r' in joint else -1
                pos[1] += beat_scale * 0.1 * side
                pos[0] += np.sin(2 * np.pi * beat_phase) * 0.02 * self.dance_intensity

            elif 'ankle' in joint:
                side = 1 if 'r' in joint else -1
                if np.sin(2 * np.pi * beat_phase) > 0:
                    pos[1] += beat_scale * 0.1 * side * intensity
                pos[2] += np.sin(2 * np.pi * beat_phase * 2) * 0.03 * self.dance_intensity

            elif 'knee' in joint:
                side = 1 if 'r' in joint else -1
                pos[1] += beat_scale * 0.05 * side
                pos[0] += np.sin(2 * np.pi * beat_phase) * 0.02 * self.dance_intensity

            elif 'torso' in joint:
                pos[1] += beat_scale * 0.05
                pos[0] += np.sin(2 * np.pi * beat_phase) * 0.02 * self.dance_intensity
                pos[2] += np.sin(2 * np.pi * beat_phase * 0.5) * 0.03 * self.dance_intensity

            self.current_positions[joint] = pos

        return self.current_positions

    def get_bone_lines(self):
        lines = []
        for joint1, joint2 in self.bones:
            p1 = self.current_positions[joint1]
            p2 = self.current_positions[joint2]
            lines.append(([p1[0], p2[0]], [p1[2], p2[2]], [p1[1], p2[1]]))
        return lines

    def get_joint_points(self):
        xs = [self.current_positions[j][0] for j in self.joint_names]
        ys = [self.current_positions[j][2] for j in self.joint_names]
        zs = [self.current_positions[j][1] for j in self.joint_names]
        return xs, ys, zs


class DanceVisualizer:
    def __init__(self, sr=44100, hop_length=512, window_duration=10):
        self.sr = sr
        self.hop_length = hop_length
        self.window_duration = window_duration

        self.fig = plt.figure(figsize=(16, 8))
        self.fig.suptitle('Beat-Driven Dance Visualization', fontsize=14, fontweight='bold')

        self.ax1 = self.fig.add_subplot(1, 2, 1, projection='3d')
        self.ax2 = self.fig.add_subplot(1, 2, 2)

        self.ax1.set_title('3D Dance Model')
        self.ax1.set_xlabel('X')
        self.ax1.set_ylabel('Z')
        self.ax1.set_zlabel('Y')
        self.ax1.set_xlim(-1.5, 1.5)
        self.ax1.set_ylim(-1.5, 1.5)
        self.ax1.set_zlim(0, 2.5)
        self.ax1.grid(True, alpha=0.3)

        self.ax2.set_title('Beat Activity & Intensity')
        self.ax2.set_xlabel('Time (s)')
        self.ax2.set_ylabel('Intensity')
        self.ax2.set_ylim(0, 1.1)
        self.ax2.grid(True, alpha=0.3)

        self.dance_model = DanceModel()

        self.bone_lines = []
        for _ in self.dance_model.bones:
            line, = self.ax1.plot([], [], [], 'b-', linewidth=2, alpha=0.8)
            self.bone_lines.append(line)

        self.joint_points, = self.ax1.plot([], [], [], 'ro', markersize=6, alpha=0.8)
        self.head_point, = self.ax1.plot([], [], [], 'go', markersize=12, alpha=0.9)

        self.intensity_line, = self.ax2.plot([], [], 'r-', linewidth=2, label='Dance Intensity')
        self.onset_line, = self.ax2.plot([], [], 'b-', linewidth=1, alpha=0.5, label='Onset Strength')
        self.beat_vlines = []
        self.downbeat_vlines = []
        self.ax2.legend(loc='upper right')

        self.time_history = deque(maxlen=500)
        self.intensity_history = deque(maxlen=500)
        self.onset_history = deque(maxlen=500)
        self.beat_markers = deque(maxlen=100)
        self.downbeat_markers = deque(maxlen=25)

        self.status_text = self.fig.text(
            0.02, 0.02, '', fontsize=11,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        )

        self.current_bpm = 0.0
        self.current_confidence = 0.0
        self.beat_phase = 0.0
        self.is_locked = False
        self.start_time = time.time()

        self.anim = None
        self.is_running = False
        self.last_beat_time = 0.0
        self.beat_count = 0

        self.view_angle = 0
        self.auto_rotate = True

    def update_data(
        self,
        onset_env=None,
        beat_times=None,
        downbeat_times=None,
        bpm=0.0,
        confidence=0.0,
        is_locked=False,
        beat_phase=0.0,
        structure_segments=None,
    ):
        current_time = time.time() - self.start_time

        self.time_history.append(current_time)
        self.current_bpm = bpm
        self.current_confidence = confidence
        self.is_locked = is_locked
        self.beat_phase = beat_phase

        if onset_env is not None and len(onset_env) > 0:
            onset_val = float(np.mean(onset_env[-5:])) if len(onset_env) >= 5 else float(onset_env[-1])
            self.onset_history.append(onset_val)
        else:
            self.onset_history.append(0.0)

        intensity = self.dance_model.dance_intensity
        self.intensity_history.append(intensity)

        is_beat = False
        is_downbeat = False

        if beat_times is not None and len(beat_times) > 0:
            for bt in beat_times[-5:]:
                if bt > self.last_beat_time + 0.1:
                    self.beat_markers.append(bt)
                    is_beat = True
                    self.beat_count += 1
                    self.last_beat_time = bt

        if downbeat_times is not None and len(downbeat_times) > 0:
            for dbt in downbeat_times[-2:]:
                if dbt > self.last_beat_time:
                    self.downbeat_markers.append(dbt)
                    is_downbeat = True

        self.dance_model.update(
            beat_phase=beat_phase,
            is_beat=is_beat,
            is_downbeat=is_downbeat,
            bpm=bpm,
            intensity=confidence,
        )

    def _init_plot(self):
        for line in self.bone_lines:
            line.set_data([], [])
            line.set_3d_properties([])

        self.joint_points.set_data([], [])
        self.joint_points.set_3d_properties([])

        self.head_point.set_data([], [])
        self.head_point.set_3d_properties([])

        self.intensity_line.set_data([], [])
        self.onset_line.set_data([], [])

        for vline in self.beat_vlines + self.downbeat_vlines:
            vline.remove()
        self.beat_vlines = []
        self.downbeat_vlines = []

        return (
            *self.bone_lines, self.joint_points, self.head_point,
            self.intensity_line, self.onset_line, self.status_text
        )

    def _update_plot(self, frame):
        current_time = time.time() - self.start_time
        x_min = max(0, current_time - self.window_duration)
        x_max = x_min + self.window_duration

        self.ax2.set_xlim(x_min, x_max)

        if self.auto_rotate:
            self.view_angle += 0.5
            self.ax1.view_init(elev=20, azim=self.view_angle % 360)

        bone_lines = self.dance_model.get_bone_lines()
        for i, (xs, ys, zs) in enumerate(bone_lines):
            self.bone_lines[i].set_data(xs, ys)
            self.bone_lines[i].set_3d_properties(zs)

        xs, ys, zs = self.dance_model.get_joint_points()
        self.joint_points.set_data(xs, ys)
        self.joint_points.set_3d_properties(zs)

        head_pos = self.dance_model.current_positions['head']
        self.head_point.set_data([head_pos[0]], [head_pos[2]])
        self.head_point.set_3d_properties([head_pos[1]])

        for vline in self.beat_vlines + self.downbeat_vlines:
            vline.remove()
        self.beat_vlines = []
        self.downbeat_vlines = []

        time_array = np.array(self.time_history)
        mask = time_array >= x_min
        filtered_time = time_array[mask]

        if len(filtered_time) > 0:
            intensity_array = np.array(self.intensity_history)[mask]
            self.intensity_line.set_data(filtered_time, intensity_array)

            onset_array = np.array(self.onset_history)[mask]
            if len(onset_array) > 0:
                onset_norm = onset_array / (np.max(onset_array) + 1e-6)
                self.onset_line.set_data(filtered_time, onset_norm)

        for bt in self.beat_markers:
            if x_min <= bt <= x_max:
                vline = self.ax2.axvline(bt, color='red', alpha=0.5, linestyle='--', linewidth=1)
                self.beat_vlines.append(vline)

        for dbt in self.downbeat_markers:
            if x_min <= dbt <= x_max:
                vline = self.ax2.axvline(dbt, color='green', alpha=0.8, linestyle='-', linewidth=2)
                self.downbeat_vlines.append(vline)

        lock_status = 'LOCKED' if self.is_locked else 'UNLOCKED'
        lock_color = 'green' if self.is_locked else 'red'

        self.status_text.set_text(
            f'BPM: {self.current_bpm:.1f} | '
            f'Confidence: {self.current_confidence:.2f} | '
            f'Phase: {self.beat_phase:.2f} | '
            f'Beats: {self.beat_count} | '
            f'Status: [{lock_status}]'
        )
        self.status_text.set_color(lock_color)

        return (
            *self.bone_lines, self.joint_points, self.head_point,
            self.intensity_line, self.onset_line, self.status_text
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

    def save_screenshot(self, filepath):
        self.fig.savefig(filepath, dpi=150, bbox_inches='tight')


class OfflineDanceAnimator:
    def __init__(self, sr=44100, hop_length=512):
        self.sr = sr
        self.hop_length = hop_length

    def animate(self, beat_times, downbeat_times, bpm, duration, output_file=None):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        ax.set_title(f'Dance Animation | BPM: {bpm:.1f}')
        ax.set_xlabel('X')
        ax.set_ylabel('Z')
        ax.set_zlabel('Y')
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_zlim(0, 2.5)
        ax.grid(True, alpha=0.3)

        dance_model = DanceModel()

        bone_lines = []
        for _ in dance_model.bones:
            line, = ax.plot([], [], [], 'b-', linewidth=2, alpha=0.8)
            bone_lines.append(line)

        joint_points, = ax.plot([], [], [], 'ro', markersize=6, alpha=0.8)
        head_point, = ax.plot([], [], [], 'go', markersize=12, alpha=0.9)

        beat_set = set(np.round(beat_times, 2))
        downbeat_set = set(np.round(downbeat_times, 2))

        def update(frame):
            t = frame * 0.05
            beat_period = 60.0 / bpm if bpm > 0 else 0.5
            beat_phase = (t % beat_period) / beat_period

            is_beat = np.round(t, 2) in beat_set
            is_downbeat = np.round(t, 2) in downbeat_set

            dance_model.update(beat_phase, is_beat, is_downbeat, bpm, intensity=1.0)

            bone_data = dance_model.get_bone_lines()
            for i, (xs, ys, zs) in enumerate(bone_data):
                bone_lines[i].set_data(xs, ys)
                bone_lines[i].set_3d_properties(zs)

            xs, ys, zs = dance_model.get_joint_points()
            joint_points.set_data(xs, ys)
            joint_points.set_3d_properties(zs)

            head_pos = dance_model.current_positions['head']
            head_point.set_data([head_pos[0]], [head_pos[2]])
            head_point.set_3d_properties([head_pos[1]])

            ax.view_init(elev=20, azim=(t * 30) % 360)

            return (*bone_lines, joint_points, head_point)

        frames = int(duration / 0.05)
        anim = FuncAnimation(fig, update, frames=frames, interval=50, blit=True)

        if output_file is not None:
            try:
                import matplotlib.animation as animation
                Writer = animation.writers['ffmpeg']
                writer = Writer(fps=20, metadata=dict(artist='BeatTracker'), bitrate=1800)
                anim.save(output_file, writer=writer)
                print(f'Dance animation saved to: {output_file}')
            except Exception as e:
                print(f'Could not save video (ffmpeg may not be installed): {e}')

        plt.tight_layout()
        return fig, anim
