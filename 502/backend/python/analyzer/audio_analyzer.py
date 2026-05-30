import numpy as np
from scipy.signal import find_peaks
import json
import os
import subprocess
import tempfile


class AudioAnalyzer:
    def __init__(self, sensitivity=1.0):
        self.sensitivity = sensitivity

    def extract_audio(self, video_path, output_path=None):
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"audio_{os.path.basename(video_path)}.wav")

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "22050",
            "-ac", "1",
            "-y",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"FFmpeg audio extraction error: {result.stderr}")
                return None
            return output_path
        except subprocess.TimeoutExpired:
            print("FFmpeg audio extraction timed out")
            return None
        except FileNotFoundError:
            print("FFmpeg not found, skipping audio analysis")
            return None

    def analyze_audio_energy(self, audio_path):
        try:
            import librosa
            y, sr = librosa.load(audio_path, sr=22050)

            frame_length = int(sr * 0.025)
            hop_length = int(sr * 0.01)

            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            timestamps = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=hop_length)[0]

            min_len = min(len(rms), len(spectral_centroid), len(spectral_bandwidth))
            rms = rms[:min_len]
            timestamps = timestamps[:min_len]
            spectral_centroid = spectral_centroid[:min_len]
            spectral_bandwidth = spectral_bandwidth[:min_len]

            energy_data = []
            for i in range(min_len):
                energy_data.append({
                    "timestamp": float(timestamps[i]),
                    "energy": float(rms[i]),
                    "spectral_centroid": float(spectral_centroid[i]),
                    "spectral_bandwidth": float(spectral_bandwidth[i])
                })

            return energy_data
        except ImportError:
            print("librosa not installed, using fallback audio analysis")
            return self._fallback_audio_analysis(audio_path)
        except Exception as e:
            print(f"Audio analysis error: {e}")
            return self._fallback_audio_analysis(audio_path)

    def _fallback_audio_analysis(self, audio_path):
        try:
            import soundfile as sf
            y, sr = sf.read(audio_path)
            if len(y.shape) > 1:
                y = y.mean(axis=1)

            frame_size = int(sr * 0.025)
            hop_size = int(sr * 0.01)

            energy_data = []
            for i in range(0, len(y) - frame_size, hop_size):
                frame = y[i:i + frame_size]
                energy = float(np.sqrt(np.mean(frame ** 2)))
                timestamp = i / sr
                energy_data.append({
                    "timestamp": timestamp,
                    "energy": energy,
                    "spectral_centroid": 0.0,
                    "spectral_bandwidth": 0.0
                })

            return energy_data
        except ImportError:
            print("soundfile not installed, skipping audio analysis")
            return []
        except Exception as e:
            print(f"Fallback audio analysis error: {e}")
            return []

    def detect_audio_highlights(self, energy_data, fps=30):
        if not energy_data:
            return []

        energies = [e["energy"] for e in energy_data]
        highlights = []

        threshold = np.mean(energies) + self.sensitivity * np.std(energies)
        peaks, properties = find_peaks(
            energies,
            height=threshold,
            distance=int(fps * 3),
            prominence=0.01
        )

        for peak_idx in peaks:
            peak_time = energy_data[peak_idx]["timestamp"]
            start_time = max(0, peak_time - 2.0)
            end_time = peak_time + 2.0

            highlights.append({
                "type": "audio_peak",
                "start_time": start_time,
                "end_time": end_time,
                "confidence": min(1.0, float(energies[peak_idx]) / (threshold * 2)),
                "peak_score": float(energies[peak_idx])
            })

        return highlights

    def detect_laughter(self, energy_data):
        if not energy_data:
            return []

        energies = [e["energy"] for e in energy_data]
        highlights = []

        if len(energies) < 10:
            return highlights

        window_size = 5
        short_term_energy = np.convolve(energies, np.ones(window_size) / window_size, mode="same")
        long_term_energy = np.convolve(energies, np.ones(window_size * 4) / (window_size * 4), mode="same")

        flux = np.abs(short_term_energy - long_term_energy)

        threshold = np.mean(flux) + self.sensitivity * np.std(flux)
        peaks, _ = find_peaks(
            flux,
            height=threshold,
            distance=30
        )

        for peak_idx in peaks:
            peak_time = energy_data[peak_idx]["timestamp"]
            start_time = max(0, peak_time - 1.5)
            end_time = peak_time + 2.0

            highlights.append({
                "type": "laughter",
                "start_time": start_time,
                "end_time": end_time,
                "confidence": min(1.0, float(flux[peak_idx]) / (threshold * 2)),
                "peak_score": float(flux[peak_idx])
            })

        return highlights

    def compute_audio_energy_timeline(self, energy_data, video_duration, sample_fps):
        if not energy_data:
            return {}

        timeline = {}
        for entry in energy_data:
            t = entry["timestamp"]
            frame_idx = int(t * sample_fps)
            timeline[frame_idx] = {
                "energy": entry["energy"],
                "spectral_centroid": entry.get("spectral_centroid", 0.0),
                "spectral_bandwidth": entry.get("spectral_bandwidth", 0.0)
            }

        return timeline

    def detect_spectral_highlights(self, energy_data, fps=30):
        if not energy_data:
            return []

        centroids = [e.get("spectral_centroid", 0) for e in energy_data]
        bandwidths = [e.get("spectral_bandwidth", 0) for e in energy_data]
        energies = [e["energy"] for e in energy_data]

        highlights = []

        if len(centroids) < 10 or all(c == 0 for c in centroids):
            return highlights

        centroid_arr = np.array(centroids)
        centroid_diff = np.abs(np.diff(centroid_arr, prepend=centroid_arr[0]))

        energy_arr = np.array(energies)
        energy_norm = energy_arr / (np.max(energy_arr) + 1e-10)

        bandwidth_arr = np.array(bandwidths)
        bandwidth_norm = bandwidth_arr / (np.max(bandwidth_arr) + 1e-10)

        combined_score = 0.3 * energy_norm + 0.4 * (centroid_diff / (np.max(centroid_diff) + 1e-10)) + 0.3 * bandwidth_norm

        threshold = np.mean(combined_score) + self.sensitivity * np.std(combined_score)
        peaks, _ = find_peaks(
            combined_score,
            height=threshold,
            distance=int(fps * 2),
            prominence=0.02
        )

        for peak_idx in peaks:
            peak_time = energy_data[peak_idx]["timestamp"]
            start_time = max(0, peak_time - 1.5)
            end_time = peak_time + 1.5

            highlights.append({
                "type": "spectral_change",
                "start_time": start_time,
                "end_time": end_time,
                "confidence": min(1.0, float(combined_score[peak_idx]) / (threshold * 1.5)),
                "peak_score": float(combined_score[peak_idx])
            })

        return highlights

    def boost_visual_highlights_with_audio(self, visual_highlights, audio_timeline, sample_fps, boost_weight=0.3):
        if not audio_timeline or not visual_highlights:
            return visual_highlights

        boosted = []
        for h in visual_highlights:
            highlight = h.copy()

            start_frame = int(h["start_time"] * sample_fps)
            end_frame = int(h["end_time"] * sample_fps)

            audio_scores = []
            for frame_idx in range(start_frame, end_frame + 1):
                if frame_idx in audio_timeline:
                    audio_scores.append(audio_timeline[frame_idx]["energy"])

            if audio_scores:
                avg_audio_energy = np.mean(audio_scores)
                max_audio_energy = max(audio_timeline[f]["energy"] for f in audio_timeline) if audio_timeline else 1.0
                normalized_audio = avg_audio_energy / (max_audio_energy + 1e-10)

                original_confidence = h.get("confidence", 0.5)
                boosted_confidence = original_confidence * (1.0 - boost_weight) + normalized_audio * boost_weight

                highlight["confidence"] = min(1.0, boosted_confidence)
                highlight["audio_boosted"] = True
                highlight["audio_energy"] = round(float(avg_audio_energy), 4)
                highlight["original_confidence"] = round(original_confidence, 3)

            boosted.append(highlight)

        return boosted

    def detect_audio_visual_highlights(self, visual_highlights, energy_data, sample_fps, video_duration):
        if not energy_data or not visual_highlights:
            return visual_highlights

        audio_timeline = self.compute_audio_energy_timeline(energy_data, video_duration, sample_fps)

        boosted = self.boost_visual_highlights_with_audio(
            visual_highlights, audio_timeline, sample_fps, boost_weight=0.3
        )

        spectral_highlights = self.detect_spectral_highlights(energy_data, fps=sample_fps)
        boosted.extend(spectral_highlights)

        return boosted
