import numpy as np
import librosa
from collections import deque
from kalman_filter import AdaptiveBPMKalmanFilter, BPMKalmanFilter


class OnlineViterbiTracker:
    def __init__(
        self,
        sr=44100,
        hop_length=512,
        min_bpm=60,
        max_bpm=200,
        beam_width=10,
        state_history=200,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.beam_width = beam_width
        self.state_history = state_history

        self.min_interval = int(60.0 * sr / (max_bpm * hop_length))
        self.max_interval = int(60.0 * sr / (min_bpm * hop_length))

        self.hypotheses = []
        self.frame_count = 0
        self.global_beat_frames = []

        self.onset_buffer = deque(maxlen=state_history)
        self.dp_scores = deque(maxlen=state_history)
        self.backpointers = deque(maxlen=state_history)

        self.target_interval = int(60.0 * sr / (120.0 * hop_length))

    def reset(self):
        self.hypotheses = []
        self.frame_count = 0
        self.global_beat_frames = []
        self.onset_buffer.clear()
        self.dp_scores.clear()
        self.backpointers.clear()
        self.target_interval = int(60.0 * self.sr / (120.0 * self.hop_length))

    def update_target_interval(self, bpm):
        self.target_interval = int(60.0 * self.sr / (bpm * self.hop_length))

    def _compute_transition_cost(self, interval, prev_interval=None):
        target = self.target_interval
        deviation = abs(interval - target) / target
        cost = deviation * 1.0

        if prev_interval is not None and prev_interval > 0:
            ratio = interval / prev_interval
            regularity_cost = abs(ratio - 1.0) * 0.5
            cost += regularity_cost

        return cost

    def process_frame(self, onset_value, style_params=None):
        if style_params is None:
            style_params = {'onset_weight': 1.0, 'tempo_weight': 1.0, 'regularity_weight': 1.0}

        self.frame_count += 1
        self.onset_buffer.append(onset_value)

        onset_weight = style_params['onset_weight']
        tempo_weight = style_params['tempo_weight']
        regularity_weight = style_params['regularity_weight']

        frame_idx = self.frame_count - 1
        current_score = onset_weight * onset_value

        best_prev = -1
        best_score = current_score

        if frame_idx >= self.min_interval:
            search_start = max(0, frame_idx - self.max_interval)
            search_end = frame_idx - self.min_interval

            if search_end >= search_start and len(self.dp_scores) > search_start:
                j_range = np.arange(search_start, search_end + 1)
                valid_j = j_range[j_range < len(self.dp_scores)]

                if len(valid_j) > 0:
                    intervals = frame_idx - valid_j
                    interval_deviation = np.abs(intervals - self.target_interval) / self.target_interval
                    tempo_penalties = tempo_weight * interval_deviation

                    prev_scores = np.array([self.dp_scores[j] for j in valid_j])
                    scores = prev_scores + current_score - tempo_penalties

                    for idx, j in enumerate(valid_j):
                        if self.backpointers[j] >= 0:
                            prev_interval = j - self.backpointers[j]
                            if prev_interval > 0:
                                interval_ratio = intervals[idx] / prev_interval
                                regularity_penalty = regularity_weight * abs(interval_ratio - 1.0)
                                scores[idx] -= regularity_penalty

                    best_local_idx = np.argmax(scores)
                    if scores[best_local_idx] > best_score:
                        best_score = scores[best_local_idx]
                        best_prev = valid_j[best_local_idx]

        self.dp_scores.append(best_score)
        self.backpointers.append(best_prev)

        detected_beats = []
        if best_prev >= 0:
            current = frame_idx
            beats = []
            while current >= 0 and len(beats) < self.beam_width:
                beats.append(current)
                if current < len(self.backpointers):
                    prev = self.backpointers[current]
                    if prev < 0:
                        break
                    current = prev
                else:
                    break
            detected_beats = beats[::-1]

        return detected_beats, best_score


class EnergyPeakDetector:
    def __init__(
        self,
        sr=44100,
        frame_size=2048,
        hop_length=512,
        threshold=0.5,
        min_peak_distance=0.1,
        subband_emphasis=True,
    ):
        self.sr = sr
        self.frame_size = frame_size
        self.hop_length = hop_length
        self.threshold = threshold
        self.min_peak_distance = min_peak_distance
        self.subband_emphasis = subband_emphasis

        self.energy_buffer = deque(maxlen=int(sr / hop_length * 5))
        self.peak_history = deque(maxlen=100)
        self.smoothed_energy = deque(maxlen=int(sr / hop_length * 2))

    def reset(self):
        self.energy_buffer.clear()
        self.peak_history.clear()
        self.smoothed_energy.clear()

    def compute_subband_energy(self, y):
        if len(y) < self.frame_size:
            y = np.pad(y, (0, self.frame_size - len(y)))

        D = np.abs(librosa.stft(y, n_fft=self.frame_size, hop_length=self.hop_length))

        if self.subband_emphasis:
            n_bins = D.shape[0]
            low_band = D[:int(n_bins * 0.1), :]
            mid_band = D[int(n_bins * 0.1):int(n_bins * 0.5), :]
            high_band = D[int(n_bins * 0.5):, :]

            low_energy = np.mean(low_band**2, axis=0) * 2.0
            mid_energy = np.mean(mid_band**2, axis=0) * 1.0
            high_energy = np.mean(high_band**2, axis=0) * 0.5

            subband_energy = low_energy + mid_energy + high_energy
        else:
            subband_energy = np.mean(D**2, axis=0)

        return subband_energy

    def detect_peaks(self, energy_signal):
        if len(energy_signal) < 3:
            return []

        peaks = []
        min_peak_frames = int(self.min_peak_distance * self.sr / self.hop_length)

        for i in range(1, len(energy_signal) - 1):
            if (energy_signal[i] > energy_signal[i-1] and
                energy_signal[i] > energy_signal[i+1] and
                energy_signal[i] > self.threshold * np.max(energy_signal)):

                if len(peaks) == 0 or (i - peaks[-1]) >= min_peak_frames:
                    peaks.append(i)

        return peaks

    def process(self, y):
        subband_energy = self.compute_subband_energy(y)

        if len(self.smoothed_energy) > 0:
            alpha = 0.3
            smoothed = alpha * subband_energy + (1 - alpha) * np.array(self.smoothed_energy)[-len(subband_energy):]
        else:
            smoothed = subband_energy

        for e in smoothed:
            self.smoothed_energy.append(e)
            self.energy_buffer.append(e)

        peaks = self.detect_peaks(smoothed)

        for p in peaks:
            self.peak_history.append(p)

        peak_enhanced_onset = np.zeros_like(subband_energy)
        for p in peaks:
            if p < len(peak_enhanced_onset):
                peak_enhanced_onset[p] = 1.0

        return peak_enhanced_onset, smoothed, peaks


class BeatTracker:
    def __init__(
        self,
        sr=44100,
        hop_length=512,
        min_bpm=60,
        max_bpm=200,
        style='generic',
        use_kalman=True,
        streaming=False,
    ):
        self.sr = sr
        self.hop_length = hop_length
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.style = style
        self.use_kalman = use_kalman
        self.streaming = streaming

        self.onset_env = None
        self.beat_frames = []
        self.beat_times = []
        self.downbeat_frames = []
        self.downbeat_times = []
        self.bpm = 120.0
        self.confidence = 0.0

        self.onset_buffer = deque(maxlen=int(sr / hop_length * 10))
        self.beat_buffer = deque(maxlen=50)
        self.bpm_history = deque(maxlen=20)

        self.frame_offset = 0
        self.processed_samples = 0

        if use_kalman:
            self.bpm_kf = AdaptiveBPMKalmanFilter(initial_bpm=120.0)

        self.online_viterbi = OnlineViterbiTracker(
            sr=sr,
            hop_length=hop_length,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
        )

        self.energy_peak_detector = EnergyPeakDetector(
            sr=sr,
            frame_size=2048,
            hop_length=hop_length,
            threshold=0.4,
        )

        self.style_params = self._get_style_params(style)
        self._frame_count = 0

        self.speed_changing = False
        self.speed_change_magnitude = 0.0

    def _get_style_params(self, style):
        params = {
            'generic': {
                'onset_weight': 1.0, 'tempo_weight': 1.0, 'regularity_weight': 1.0,
                'use_energy_peaks': False, 'peak_emphasis': 0.0
            },
            'rock': {
                'onset_weight': 1.2, 'tempo_weight': 0.8, 'regularity_weight': 1.2,
                'use_energy_peaks': False, 'peak_emphasis': 0.0
            },
            'jazz': {
                'onset_weight': 0.8, 'tempo_weight': 1.2, 'regularity_weight': 0.7,
                'use_energy_peaks': False, 'peak_emphasis': 0.0
            },
            'electronic': {
                'onset_weight': 1.5, 'tempo_weight': 0.6, 'regularity_weight': 1.5,
                'use_energy_peaks': True, 'peak_emphasis': 0.3
            },
            'classical': {
                'onset_weight': 0.7, 'tempo_weight': 1.5, 'regularity_weight': 0.6,
                'use_energy_peaks': False, 'peak_emphasis': 0.0
            },
            'hiphop': {
                'onset_weight': 1.3, 'tempo_weight': 0.7, 'regularity_weight': 1.3,
                'use_energy_peaks': True, 'peak_emphasis': 0.4
            },
            'metal': {
                'onset_weight': 1.4, 'tempo_weight': 0.9, 'regularity_weight': 1.4,
                'use_energy_peaks': True, 'peak_emphasis': 0.8
            },
            'heavymetal': {
                'onset_weight': 1.6, 'tempo_weight': 0.8, 'regularity_weight': 1.3,
                'use_energy_peaks': True, 'peak_emphasis': 1.0
            },
        }
        return params.get(style, params['generic'])

    def set_style(self, style):
        self.style = style
        self.style_params = self._get_style_params(style)

    def _preprocess_heavy_metal(self, y):
        peak_enhanced, energy, peaks = self.energy_peak_detector.process(y)
        return peak_enhanced, energy, peaks

    def extract_onset_envelope(self, y):
        if self.style in ['metal', 'heavymetal'] or self.style_params.get('use_energy_peaks', False):
            peak_enhanced, energy, peaks = self._preprocess_heavy_metal(y)

            onset_env = librosa.onset.onset_strength(
                y=y,
                sr=self.sr,
                hop_length=self.hop_length,
                aggregate=np.median,
            )

            min_len = min(len(onset_env), len(peak_enhanced))
            peak_emphasis = self.style_params.get('peak_emphasis', 0.5)

            combined = (
                (1 - peak_emphasis) * onset_env[:min_len] +
                peak_emphasis * peak_enhanced[:min_len]
            )

            combined = librosa.util.normalize(combined)
            return combined
        else:
            onset_env = librosa.onset.onset_strength(
                y=y,
                sr=self.sr,
                hop_length=self.hop_length,
                aggregate=np.median,
            )
            onset_env = librosa.util.normalize(onset_env)
            return onset_env

    def estimate_tempo(self, onset_env):
        try:
            tempo = librosa.feature.rhythm.tempo(
                onset_envelope=onset_env,
                sr=self.sr,
                hop_length=self.hop_length,
                start_bpm=self.bpm,
                std_bpm=1.0,
            )
        except AttributeError:
            tempo = librosa.beat.tempo(
                onset_envelope=onset_env,
                sr=self.sr,
                hop_length=self.hop_length,
                start_bpm=self.bpm,
                std_bpm=1.0,
            )
        return float(tempo)

    def dp_beat_track(self, onset_env, estimated_tempo=None):
        if estimated_tempo is None:
            estimated_tempo = self.estimate_tempo(onset_env)

        estimated_tempo = max(self.min_bpm, min(self.max_bpm, estimated_tempo))

        n_frames = len(onset_env)
        if n_frames < 4:
            return [], estimated_tempo, 0.0

        target_interval = 60.0 * self.sr / (estimated_tempo * self.hop_length)
        min_interval = int(60.0 * self.sr / (self.max_bpm * self.hop_length))
        max_interval = int(60.0 * self.sr / (self.min_bpm * self.hop_length))
        search_range = max_interval - min_interval + 1

        dp = np.zeros(n_frames, dtype=np.float64)
        backpointer = np.full(n_frames, -1, dtype=np.int32)

        onset_weight = self.style_params['onset_weight']
        tempo_weight = self.style_params['tempo_weight']
        regularity_weight = self.style_params['regularity_weight']

        dp[:min_interval] = onset_weight * onset_env[:min_interval]

        for i in range(min_interval, n_frames):
            search_start = max(0, i - max_interval)
            search_end = i - min_interval

            if search_end < search_start:
                dp[i] = onset_weight * onset_env[i]
                continue

            j_range = np.arange(search_start, search_end + 1)
            intervals = i - j_range
            interval_deviation = np.abs(intervals - target_interval) / target_interval
            tempo_penalties = tempo_weight * interval_deviation

            prev_intervals = np.zeros_like(j_range, dtype=np.float64)
            mask = backpointer[j_range] >= 0
            prev_intervals[mask] = j_range[mask] - backpointer[j_range[mask]]

            regularity_penalties = np.zeros_like(j_range, dtype=np.float64)
            valid_mask = (prev_intervals > 0) & mask
            if np.any(valid_mask):
                interval_ratios = intervals[valid_mask] / prev_intervals[valid_mask]
                regularity_penalties[valid_mask] = regularity_weight * np.abs(interval_ratios - 1.0)

            scores = dp[j_range] + onset_weight * onset_env[i] - tempo_penalties - regularity_penalties

            best_idx = np.argmax(scores)
            max_score = scores[best_idx]
            best_j = j_range[best_idx]

            if max_score > onset_weight * onset_env[i]:
                dp[i] = max_score
                backpointer[i] = best_j
            else:
                dp[i] = onset_weight * onset_env[i]

        beats = []
        if n_frames > min_interval:
            search_start = min_interval
            current = np.argmax(dp[search_start:]) + search_start
        else:
            current = n_frames - 1

        max_beats = n_frames // min_interval
        while current >= 0 and len(beats) < max_beats:
            beats.append(current)
            if backpointer[current] < 0:
                break
            current = backpointer[current]

        beats = beats[::-1]

        if len(beats) >= 2:
            intervals = np.diff(beats)
            median_interval = np.median(intervals)
            estimated_tempo = 60.0 * self.sr / (median_interval * self.hop_length)
            estimated_tempo = max(self.min_bpm, min(self.max_bpm, estimated_tempo))

            interval_std = np.std(intervals)
            confidence = max(0.0, min(1.0, 1.0 - interval_std / (median_interval * 0.3)))
        else:
            confidence = 0.0

        return beats, estimated_tempo, confidence

    def online_viterbi_track(self, onset_env, estimated_tempo=None):
        if estimated_tempo is not None:
            self.online_viterbi.update_target_interval(estimated_tempo)

        all_beats = []
        for i, onset_val in enumerate(onset_env):
            beats, score = self.online_viterbi.process_frame(onset_val, self.style_params)
            if len(beats) > 0:
                all_beats = beats

        if len(all_beats) >= 2:
            intervals = np.diff(all_beats)
            median_interval = np.median(intervals)
            estimated_tempo = 60.0 * self.sr / (median_interval * self.hop_length)
            estimated_tempo = max(self.min_bpm, min(self.max_bpm, estimated_tempo))

            interval_std = np.std(intervals)
            confidence = max(0.0, min(1.0, 1.0 - interval_std / (median_interval * 0.3)))
        else:
            estimated_tempo = self.bpm if self.bpm > 0 else 120.0
            confidence = 0.0

        return all_beats, estimated_tempo, confidence

    def detect_downbeats(self, beats, onset_env):
        if len(beats) < 4:
            return []

        beat_strengths = [onset_env[b] if b < len(onset_env) else 0 for b in beats]

        best_offset = 0
        best_score = -np.inf

        for offset in range(4):
            score = 0.0
            for i in range(offset, len(beat_strengths), 4):
                if i < len(beat_strengths):
                    score += beat_strengths[i] * 2.0
                if i + 2 < len(beat_strengths):
                    score += beat_strengths[i + 2] * 0.5
            if score > best_score:
                best_score = score
                best_offset = offset

        downbeats = [beats[i] for i in range(best_offset, len(beats), 4)]
        return downbeats

    def process_stream(self, y_chunk):
        self.processed_samples += len(y_chunk)

        onset_env = self.extract_onset_envelope(y_chunk)
        self.onset_buffer.extend(onset_env)

        if len(self.onset_buffer) < int(self.sr / self.hop_length * 0.5):
            return None

        full_onset = np.array(self.onset_buffer)

        if self.streaming:
            raw_tempo = self.estimate_tempo(full_onset)
            beats, tempo, beat_confidence = self.online_viterbi_track(full_onset, raw_tempo)
        else:
            raw_tempo = self.estimate_tempo(full_onset)
            beats, tempo, beat_confidence = self.dp_beat_track(full_onset, raw_tempo)

        if self.use_kalman:
            filtered_bpm, kf_confidence = self.bpm_kf.update(tempo, beat_confidence)
            self.bpm = filtered_bpm
            self.confidence = kf_confidence

            self.speed_changing = self.bpm_kf.is_speed_changing()
            self.speed_change_magnitude = self.bpm_kf.get_speed_change_magnitude()

            if self.speed_changing:
                self.online_viterbi.update_target_interval(self.bpm)
        else:
            self.bpm = tempo
            self.confidence = beat_confidence
            self.speed_changing = False
            self.speed_change_magnitude = 0.0

        self.bpm_history.append(self.bpm)

        if len(beats) > 0:
            beat_times = librosa.frames_to_time(beats, sr=self.sr, hop_length=self.hop_length)
            downbeats = self.detect_downbeats(beats, full_onset)
            downbeat_times = librosa.frames_to_time(downbeats, sr=self.sr, hop_length=self.hop_length)

            self.beat_frames = beats
            self.beat_times = beat_times
            self.downbeat_frames = downbeats
            self.downbeat_times = downbeat_times

            return {
                'beats': beat_times,
                'downbeats': downbeat_times,
                'bpm': self.bpm,
                'confidence': self.confidence,
                'beat_frames': beats,
                'downbeat_frames': downbeats,
                'onset_env': full_onset,
                'speed_changing': self.speed_changing,
                'speed_change_magnitude': self.speed_change_magnitude,
            }

        return None

    def process_frame(self, y):
        return self.process_stream(y)

    def process_file(self, audio_path):
        y, sr = librosa.load(audio_path, sr=self.sr)
        return self.process_frame(y)

    def get_beat_sequence(self):
        return self.beat_times.copy()

    def get_downbeat_sequence(self):
        return self.downbeat_times.copy()

    def get_bpm(self):
        return self.bpm

    def get_confidence(self):
        return self.confidence

    def is_speed_changing(self):
        return self.speed_changing

    def get_speed_change_magnitude(self):
        return self.speed_change_magnitude

    def reset(self):
        self.onset_buffer.clear()
        self.beat_buffer.clear()
        self.bpm_history.clear()
        self.beat_frames = []
        self.beat_times = []
        self.downbeat_frames = []
        self.downbeat_times = []
        self.bpm = 120.0
        self.confidence = 0.0
        self.frame_offset = 0
        self.processed_samples = 0
        self.speed_changing = False
        self.speed_change_magnitude = 0.0

        self.online_viterbi.reset()
        self.energy_peak_detector.reset()

        if self.use_kalman:
            self.bpm_kf.reset(initial_bpm=120.0)
