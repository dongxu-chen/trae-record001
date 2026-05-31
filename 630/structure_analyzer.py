import numpy as np
import librosa
from collections import deque
from scipy.ndimage import median_filter, gaussian_filter1d
from scipy.signal import find_peaks
from scipy.spatial.distance import cosine
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class MusicStructureAnalyzer:
    def __init__(self, sr=44100, hop_length=512, n_mfcc=13):
        self.sr = sr
        self.hop_length = hop_length
        self.n_mfcc = n_mfcc

        self.segment_types = ['intro', 'verse', 'pre_chorus', 'chorus', 'bridge', 'breakdown', 'solo', 'outro']

        self.feature_buffer = deque(maxlen=int(sr / hop_length * 30))
        self.segment_history = deque(maxlen=20)
        self.current_segment = None
        self.segment_start_time = 0.0

    def reset(self):
        self.feature_buffer.clear()
        self.segment_history.clear()
        self.current_segment = None
        self.segment_start_time = 0.0

    def extract_features(self, y):
        features = {}

        mfcc = librosa.feature.mfcc(y=y, sr=self.sr, n_mfcc=self.n_mfcc, hop_length=self.hop_length)
        features['mfcc'] = np.mean(mfcc, axis=1)
        features['mfcc_delta'] = np.mean(librosa.feature.delta(mfcc), axis=1)

        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=self.sr, hop_length=self.hop_length)
        features['spectral_centroid'] = np.mean(spectral_centroid)

        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=self.sr, hop_length=self.hop_length)
        features['spectral_bandwidth'] = np.mean(spectral_bandwidth)

        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=self.sr, hop_length=self.hop_length)
        features['spectral_contrast'] = np.mean(spectral_contrast, axis=1)

        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=self.sr, hop_length=self.hop_length)
        features['spectral_rolloff'] = np.mean(spectral_rolloff)

        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)
        features['rms'] = np.mean(rms)

        zero_crossing = librosa.feature.zero_crossing_rate(y, hop_length=self.hop_length)
        features['zero_crossing'] = np.mean(zero_crossing)

        chroma = librosa.feature.chroma_stft(y=y, sr=self.sr, hop_length=self.hop_length)
        features['chroma'] = np.mean(chroma, axis=1)

        onset_env = librosa.onset.onset_strength(y=y, sr=self.sr, hop_length=self.hop_length)
        features['onset_strength'] = np.mean(onset_env)
        features['onset_std'] = np.std(onset_env)

        return features

    def features_to_vector(self, features):
        vector = []
        for key in ['mfcc', 'mfcc_delta', 'spectral_contrast', 'chroma']:
            vector.extend(features[key])
        vector.extend([
            features['spectral_centroid'],
            features['spectral_bandwidth'],
            features['spectral_rolloff'],
            features['rms'],
            features['zero_crossing'],
            features['onset_strength'],
            features['onset_std'],
        ])
        return np.array(vector)

    def compute_similarity_matrix(self, feature_vectors):
        n = len(feature_vectors)
        sim_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                sim_matrix[i, j] = 1 - cosine(feature_vectors[i], feature_vectors[j])

        return sim_matrix

    def detect_boundaries(self, feature_vectors, window_size=3, threshold=0.2):
        if len(feature_vectors) < window_size * 2:
            return []

        n = len(feature_vectors)
        novelty_scores = np.zeros(n)

        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(feature_vectors)

        for i in range(window_size, n - window_size):
            left_features = features_scaled[i - window_size:i]
            right_features = features_scaled[i:i + window_size]

            left_mean = np.mean(left_features, axis=0)
            right_mean = np.mean(right_features, axis=0)

            novelty_scores[i] = cosine(left_mean, right_mean)

        if np.max(novelty_scores) > 0:
            novelty_scores = novelty_scores / np.max(novelty_scores)

        novelty_scores = gaussian_filter1d(novelty_scores, sigma=1.5)

        dynamic_threshold = threshold
        if np.max(novelty_scores) > 0.5:
            dynamic_threshold = min(threshold, 0.3 * np.max(novelty_scores))

        peaks, _ = find_peaks(novelty_scores, height=dynamic_threshold, distance=max(2, window_size))

        return peaks

    def cluster_segments(self, feature_vectors, boundaries, n_clusters=None):
        if len(boundaries) < 2:
            return []

        segment_features = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            if end > start and start < len(feature_vectors) and end <= len(feature_vectors):
                seg_features = np.mean(feature_vectors[start:end], axis=0)
                segment_features.append(seg_features)
            else:
                segment_features.append(np.zeros_like(feature_vectors[0]))

        if len(segment_features) < 2:
            return [0] * len(segment_features)

        if n_clusters is None:
            n_segments = len(segment_features)
            if n_segments >= 6:
                n_clusters = min(4, n_segments // 2)
            elif n_segments >= 4:
                n_clusters = min(3, n_segments // 2)
            else:
                n_clusters = min(2, n_segments)
            n_clusters = max(2, n_clusters)

        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(segment_features)

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(scaled_features)
        except Exception:
            labels = list(range(len(segment_features)))

        return labels

    def classify_segment(self, features, segment_index, total_segments):
        rms = features.get('rms', 0)
        onset_strength = features.get('onset_strength', 0)
        spectral_centroid = features.get('spectral_centroid', 0)
        zero_crossing = features.get('zero_crossing', 0)

        rms_norm = min(1.0, rms / 0.1)
        onset_norm = min(1.0, onset_strength / 2.0)
        centroid_norm = min(1.0, spectral_centroid / 5000)
        zcr_norm = min(1.0, zero_crossing / 0.5)

        scores = {}

        scores['intro'] = (1.0 - rms_norm) * 0.3 + (1.0 - onset_norm) * 0.3
        scores['outro'] = scores['intro']

        scores['verse'] = rms_norm * 0.2 + (1.0 - centroid_norm) * 0.2
        scores['pre_chorus'] = rms_norm * 0.3 + centroid_norm * 0.2
        scores['chorus'] = rms_norm * 0.4 + onset_norm * 0.4 + centroid_norm * 0.2
        scores['bridge'] = (1.0 - rms_norm) * 0.3 + centroid_norm * 0.3
        scores['breakdown'] = (1.0 - rms_norm) * 0.4 + zcr_norm * 0.2
        scores['solo'] = centroid_norm * 0.4 + onset_norm * 0.3

        if segment_index <= 1:
            scores['intro'] += 0.5
            scores['verse'] += 0.2
        elif segment_index >= total_segments - 2:
            scores['outro'] += 0.5
        else:
            scores['chorus'] += 0.3
            scores['verse'] += 0.2

        return max(scores, key=scores.get)

    def analyze_offline(self, y, beat_times=None, downbeat_times=None, bpm=120.0):
        duration = len(y) / self.sr

        frame_duration = 2.0
        hop_sec = 1.0
        frame_samples = int(frame_duration * self.sr)
        hop_samples = int(hop_sec * self.sr)

        feature_vectors = []
        feature_list = []
        times = []

        for i in range(0, len(y) - frame_samples, hop_samples):
            frame = y[i:i + frame_samples]
            features = self.extract_features(frame)
            feature_list.append(features)
            feature_vectors.append(self.features_to_vector(features))
            times.append(i / self.sr)

        if len(feature_vectors) < 4:
            segments = [{
                'type': 'verse',
                'start': 0.0,
                'end': duration,
                'start_beat': 0,
                'end_beat': len(beat_times) if beat_times is not None else 0,
                'confidence': 0.5,
            }]
            return segments

        boundaries = self.detect_boundaries(feature_vectors, window_size=3, threshold=0.15)
        boundaries = [0] + list(boundaries) + [len(feature_vectors) - 1]
        boundaries = sorted(set(boundaries))

        cluster_labels = self.cluster_segments(feature_vectors, boundaries)

        segments = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]

            start_time = times[start_idx] if start_idx < len(times) else 0
            end_time = times[end_idx] if end_idx < len(times) else duration

            seg_features = feature_list[start_idx] if start_idx < len(feature_list) else {}
            seg_type = self.classify_segment(seg_features, i, len(boundaries) - 1)

            if len(self.segment_history) > 0 and seg_type == self.segment_history[-1]['type']:
                if len(segments) > 0:
                    segments[-1]['end'] = end_time
                    continue

            start_beat = 0
            end_beat = 0
            if beat_times is not None and len(beat_times) > 0:
                start_beat = np.searchsorted(beat_times, start_time)
                end_beat = np.searchsorted(beat_times, end_time)

            confidence = self._compute_segment_confidence(
                feature_vectors, start_idx, end_idx, cluster_labels, i
            )

            segment = {
                'type': seg_type,
                'start': start_time,
                'end': end_time,
                'start_beat': start_beat,
                'end_beat': end_beat,
                'confidence': confidence,
                'cluster': cluster_labels[i] if i < len(cluster_labels) else 0,
            }

            segments.append(segment)
            self.segment_history.append(segment)

        segments = self._refine_segments(segments, beat_times, bpm)

        return segments

    def _compute_segment_confidence(self, feature_vectors, start_idx, end_idx, cluster_labels, seg_idx):
        if end_idx - start_idx < 2:
            return 0.5

        seg_features = feature_vectors[start_idx:end_idx]
        within_var = np.mean([np.var(f) for f in seg_features])

        other_features = []
        for j, (s, e) in enumerate(zip([0] + list(range(len(cluster_labels))), list(range(1, len(cluster_labels) + 1)))):
            if j != seg_idx and s < len(feature_vectors) and e < len(feature_vectors):
                other_features.extend(feature_vectors[s:e])

        if len(other_features) > 0:
            seg_mean = np.mean(seg_features, axis=0)
            other_mean = np.mean(other_features, axis=0)
            between_dist = cosine(seg_mean, other_mean)
        else:
            between_dist = 0.5

        confidence = 0.5 + 0.5 * between_dist
        return max(0.1, min(0.95, confidence))

    def _refine_segments(self, segments, beat_times=None, bpm=120.0):
        if len(segments) < 2:
            return segments

        beat_duration = 60.0 / bpm if bpm > 0 else 0.5
        min_segment_duration = beat_duration * 4

        merged_segments = []
        i = 0

        while i < len(segments):
            seg = segments[i]
            duration = seg['end'] - seg['start']

            if duration < min_segment_duration and i < len(segments) - 1:
                next_seg = segments[i + 1]

                if seg['type'] == next_seg['type']:
                    merged = {
                        'type': seg['type'],
                        'start': seg['start'],
                        'end': next_seg['end'],
                        'start_beat': seg['start_beat'],
                        'end_beat': next_seg['end_beat'],
                        'confidence': (seg['confidence'] + next_seg['confidence']) / 2,
                        'cluster': seg.get('cluster', 0),
                    }
                    merged_segments.append(merged)
                    i += 2
                    continue

            if beat_times is not None and len(beat_times) > 0:
                snap_start = np.searchsorted(beat_times, seg['start'])
                if snap_start < len(beat_times):
                    seg['start'] = beat_times[snap_start]
                    seg['start_beat'] = snap_start

                snap_end = np.searchsorted(beat_times, seg['end']) - 1
                if snap_end >= 0 and snap_end < len(beat_times):
                    seg['end'] = beat_times[snap_end]
                    seg['end_beat'] = snap_end

            merged_segments.append(seg)
            i += 1

        return merged_segments

    def analyze_stream(self, y_chunk, current_time, beat_times=None, bpm=120.0):
        features = self.extract_features(y_chunk)
        feature_vec = self.features_to_vector(features)
        self.feature_buffer.append((current_time, feature_vec, features))

        if len(self.feature_buffer) < 10:
            return None

        times = [f[0] for f in self.feature_buffer]
        vectors = [f[1] for f in self.feature_buffer]
        feature_list = [f[2] for f in self.feature_buffer]

        boundaries = self.detect_boundaries(vectors, window_size=3, threshold=0.3)

        if len(boundaries) > 0 and boundaries[-1] == len(vectors) - 1:
            if self.current_segment is not None:
                segment = {
                    'type': self.current_segment,
                    'start': self.segment_start_time,
                    'end': current_time,
                    'confidence': 0.7,
                }
                self.segment_history.append(segment)

            new_segment_type = self.classify_segment(
                features, len(self.segment_history), len(self.segment_history) + 1
            )
            self.current_segment = new_segment_type
            self.segment_start_time = current_time

            return {
                'new_segment': True,
                'segment_type': new_segment_type,
                'start_time': current_time,
            }

        if self.current_segment is None:
            self.current_segment = self.classify_segment(
                features, 0, 1
            )
            self.segment_start_time = current_time

        return {
            'new_segment': False,
            'current_segment': self.current_segment,
            'start_time': self.segment_start_time,
            'duration': current_time - self.segment_start_time,
        }

    def get_current_structure(self):
        segments = list(self.segment_history)
        if self.current_segment is not None:
            segments.append({
                'type': self.current_segment,
                'start': self.segment_start_time,
                'end': None,
                'current': True,
            })
        return segments

    def print_structure(self, segments):
        print('\n' + '=' * 60)
        print('  MUSIC STRUCTURE ANALYSIS')
        print('=' * 60)
        print(f'  {"#":<3} {"Type":<12} {"Start":>8} {"End":>8} {"Dur":>6} {"Conf":>6}')
        print('-' * 60)

        for i, seg in enumerate(segments):
            seg_type = seg.get('type', 'unknown')
            start = seg.get('start', 0)
            end = seg.get('end', 0)
            duration = end - start if end is not None else 0
            confidence = seg.get('confidence', 0)

            marker = '◄' if seg.get('current', False) else ''

            print(f'  {i+1:<3} {seg_type:<12} {start:>7.2f}s {end:>7.2f}s {duration:>5.1f}s {confidence:>5.2f} {marker}')

        print('=' * 60 + '\n')

    def visualize_structure(self, segments, y=None, sr=None, ax=None):
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 4))

        colors = {
            'intro': '#66c2a5',
            'verse': '#8da0cb',
            'pre_chorus': '#ffd92f',
            'chorus': '#e78ac3',
            'bridge': '#a6d854',
            'breakdown': '#fc8d62',
            'solo': '#ff8c00',
            'outro': '#66c2a5',
            'unknown': '#b3b3b3',
        }

        if y is not None and sr is not None:
            times = np.arange(len(y)) / sr
            ax.plot(times, y, 'k-', alpha=0.3, linewidth=0.5)

        for seg in segments:
            seg_type = seg.get('type', 'unknown')
            start = seg.get('start', 0)
            end = seg.get('end', start + 5)

            if end is None:
                end = start + 5

            color = colors.get(seg_type, colors['unknown'])
            ax.axvspan(start, end, alpha=0.3, color=color, label=seg_type)

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Amplitude')
        ax.set_title('Music Structure Segmentation')
        ax.grid(True, alpha=0.3)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper right')

        return ax
