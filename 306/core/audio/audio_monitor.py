import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import threading
import math


@dataclass
class AudioAnalysisResult:
    timestamp: str
    volume_db: float
    is_speech: bool
    speech_probability: float
    has_suspicious_sound: bool
    suspicious_type: Optional[str]
    background_noise_level: float
    alert_level: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'volume_db': self.volume_db,
            'is_speech': self.is_speech,
            'speech_probability': self.speech_probability,
            'has_suspicious_sound': self.has_suspicious_sound,
            'suspicious_type': self.suspicious_type,
            'background_noise_level': self.background_noise_level,
            'alert_level': self.alert_level
        }


@dataclass
class StudentAudioStats:
    student_id: str
    exam_id: str
    total_chunks: int = 0
    speech_detected_count: int = 0
    suspicious_count: int = 0
    avg_volume: float = 0.0
    max_volume: float = 0.0
    speech_events: List[Dict[str, Any]] = field(default_factory=list)
    suspicious_events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'total_chunks': self.total_chunks,
            'speech_detected_count': self.speech_detected_count,
            'suspicious_count': self.suspicious_count,
            'avg_volume': self.avg_volume,
            'max_volume': self.max_volume,
            'speech_events': self.speech_events,
            'suspicious_events': self.suspicious_events
        }


class VoiceActivityDetector:
    def __init__(self, sample_rate: int = 16000, frame_size: int = 512):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.energy_threshold = 0.01
        self.spectral_flatness_threshold = 0.5
        self.pitch_min = 80
        self.pitch_max = 400

    def _calculate_energy(self, audio: np.ndarray) -> float:
        return np.sqrt(np.mean(audio ** 2))

    def _calculate_spectral_flatness(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        spectrum = np.abs(np.fft.fft(audio))
        spectrum = spectrum[:len(spectrum) // 2]
        spectrum = spectrum + 1e-10
        log_spectrum = np.log(spectrum)
        geometric_mean = np.exp(np.mean(log_spectrum))
        arithmetic_mean = np.mean(spectrum)
        if arithmetic_mean == 0:
            return 0.0
        return geometric_mean / arithmetic_mean

    def _detect_pitch(self, audio: np.ndarray) -> Optional[float]:
        if len(audio) < self.frame_size:
            return None
        try:
            autocorr = np.correlate(audio, audio, mode='full')
            autocorr = autocorr[len(autocorr) // 2:]
            d = np.diff(autocorr)
            try:
                start = np.where(d > 0)[0][0]
            except IndexError:
                return None
            peak = np.argmax(autocorr[start:]) + start
            if peak == 0 or peak >= len(autocorr) - 1:
                return None
            if autocorr[peak] < autocorr[0] * 0.3:
                return None
            pitch = self.sample_rate / peak
            if self.pitch_min <= pitch <= self.pitch_max:
                return pitch
        except Exception:
            pass
        return None

    def detect(self, audio: np.ndarray) -> Tuple[bool, float]:
        if len(audio) == 0:
            return False, 0.0

        energy = self._calculate_energy(audio)
        spectral_flatness = self._calculate_spectral_flatness(audio)
        pitch = self._detect_pitch(audio)

        score = 0.0
        if energy > self.energy_threshold:
            score += 0.4
        if spectral_flatness < self.spectral_flatness_threshold:
            score += 0.3
        if pitch is not None:
            score += 0.3

        is_speech = score > 0.5
        return is_speech, score


class SuspiciousSoundDetector:
    def __init__(self):
        self.tone_threshold = 0.7
        self.click_threshold = 0.8
        self.beep_pattern_threshold = 0.6

    def _detect_tones(self, audio: np.ndarray, sample_rate: int) -> bool:
        if len(audio) < 256:
            return False
        spectrum = np.abs(np.fft.fft(audio))
        spectrum = spectrum[:len(spectrum) // 2]
        if len(spectrum) == 0:
            return False
        peaks = np.where(spectrum > np.max(spectrum) * 0.7)[0]
        if len(peaks) > 0 and len(peaks) < 10:
            peak_ratio = len(peaks) / len(spectrum)
            return peak_ratio < 0.01
        return False

    def _detect_clicks(self, audio: np.ndarray) -> bool:
        if len(audio) < 128:
            return False
        diff = np.abs(np.diff(audio))
        if len(diff) == 0:
            return False
        threshold = np.mean(diff) * 5
        spikes = np.sum(diff > threshold)
        return spikes > 3

    def _detect_beep_pattern(self, audio: np.ndarray, sample_rate: int) -> bool:
        if len(audio) < sample_rate // 4:
            return False
        energy = np.array([
            np.sqrt(np.mean(audio[i:i + 256] ** 2))
            for i in range(0, len(audio) - 256, 256)
        ])
        if len(energy) < 4:
            return False
        threshold = np.mean(energy) * 1.5
        peaks = energy > threshold
        transitions = np.sum(np.abs(np.diff(peaks.astype(int))))
        return transitions >= 4

    def detect(self, audio: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, Optional[str], float]:
        confidence = 0.0
        sound_type = None

        has_tone = self._detect_tones(audio, sample_rate)
        if has_tone:
            confidence = max(confidence, self.tone_threshold)
            sound_type = 'tone'

        has_click = self._detect_clicks(audio)
        if has_click:
            confidence = max(confidence, self.click_threshold)
            sound_type = 'click'

        has_beep = self._detect_beep_pattern(audio, sample_rate)
        if has_beep:
            confidence = max(confidence, self.beep_pattern_threshold)
            sound_type = 'beep_pattern'

        return confidence > 0.5, sound_type, confidence


class AudioMonitor:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 4096):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._vad = VoiceActivityDetector(sample_rate, chunk_size // 4)
        self._suspicious_detector = SuspiciousSoundDetector()
        self._lock = threading.Lock()
        self._students: Dict[str, StudentAudioStats] = {}
        self._volume_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        self._speech_threshold = 0.6
        self._high_volume_threshold = 0.5
        self._suspicious_threshold = 0.7
        self._background_noise_window = 50

    def _audio_to_db(self, audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio ** 2))
        if rms <= 0:
            return -60.0
        return 20 * math.log10(rms + 1e-10)

    def _calculate_background_noise(self, student_id: str) -> float:
        history = self._volume_history.get(student_id)
        if not history or len(history) < 10:
            return 0.0
        volumes = list(history)[:self._background_noise_window]
        if not volumes:
            return 0.0
        return np.percentile(volumes, 20)

    def _determine_alert_level(self, 
                                 volume_db: float, 
                                 is_speech: bool, 
                                 speech_prob: float,
                                 has_suspicious: bool,
                                 suspicious_conf: float,
                                 bg_noise: float) -> str:
        if has_suspicious and suspicious_conf > 0.8:
            return 'critical'
        if is_speech and speech_prob > 0.8:
            return 'high'
        if volume_db > -20 and bg_noise > -30:
            return 'medium'
        return 'low'

    def register_student(self, student_id: str, exam_id: str) -> bool:
        with self._lock:
            if student_id in self._students:
                return False
            self._students[student_id] = StudentAudioStats(
                student_id=student_id,
                exam_id=exam_id
            )
            self._volume_history[student_id].clear()
            return True

    def unregister_student(self, student_id: str) -> bool:
        with self._lock:
            if student_id in self._students:
                del self._students[student_id]
                if student_id in self._volume_history:
                    del self._volume_history[student_id]
                return True
            return False

    def process_audio_chunk(self, 
                            student_id: str, 
                            audio: np.ndarray,
                            exam_id: str = "") -> AudioAnalysisResult:
        with self._lock:
            if student_id not in self._students:
                self.register_student(student_id, exam_id)

            stats = self._students[student_id]
            stats.total_chunks += 1

        volume_db = self._audio_to_db(audio)
        volume_norm = max(0.0, (volume_db + 60) / 60)

        with self._lock:
            self._volume_history[student_id].append(volume_db)
            bg_noise = self._calculate_background_noise(student_id)

        is_speech, speech_prob = self._vad.detect(audio)
        has_suspicious, sound_type, suspicious_conf = self._suspicious_detector.detect(
            audio, self.sample_rate
        )

        alert_level = self._determine_alert_level(
            volume_db, is_speech, speech_prob,
            has_suspicious, suspicious_conf, bg_noise
        )

        with self._lock:
            stats.max_volume = max(stats.max_volume, volume_norm)
            stats.avg_volume = (stats.avg_volume * (stats.total_chunks - 1) + volume_norm) / stats.total_chunks

            if is_speech and speech_prob > self._speech_threshold:
                stats.speech_detected_count += 1
                stats.speech_events.append({
                    'timestamp': datetime.now().isoformat(),
                    'volume_db': volume_db,
                    'probability': speech_prob
                })

            if has_suspicious and suspicious_conf > self._suspicious_threshold:
                stats.suspicious_count += 1
                stats.suspicious_events.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': sound_type,
                    'confidence': suspicious_conf
                })

        return AudioAnalysisResult(
            timestamp=datetime.now().isoformat(),
            volume_db=volume_db,
            is_speech=is_speech and speech_prob > self._speech_threshold,
            speech_probability=speech_prob,
            has_suspicious_sound=has_suspicious and suspicious_conf > self._suspicious_threshold,
            suspicious_type=sound_type,
            background_noise_level=bg_noise,
            alert_level=alert_level
        )

    def get_student_audio_stats(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if student_id in self._students:
                return self._students[student_id].to_dict()
            return None

    def get_all_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_students = len(self._students)
            total_chunks = sum(s.total_chunks for s in self._students.values())
            total_speech = sum(s.speech_detected_count for s in self._students.values())
            total_suspicious = sum(s.suspicious_count for s in self._students.values())

            active_students = [
                s.to_dict() for s in self._students.values()
                if s.total_chunks > 0
            ]

            return {
                'total_students': total_students,
                'total_chunks_processed': total_chunks,
                'total_speech_events': total_speech,
                'total_suspicious_events': total_suspicious,
                'active_students': active_students,
                'students_with_speech': [
                    s.student_id for s in self._students.values()
                    if s.speech_detected_count > 0
                ],
                'students_with_suspicious': [
                    s.student_id for s in self._students.values()
                    if s.suspicious_count > 0
                ]
            }

    def set_thresholds(self, speech_threshold: Optional[float] = None,
                       high_volume_threshold: Optional[float] = None,
                       suspicious_threshold: Optional[float] = None) -> None:
        if speech_threshold is not None:
            self._speech_threshold = speech_threshold
        if high_volume_threshold is not None:
            self._high_volume_threshold = high_volume_threshold
        if suspicious_threshold is not None:
            self._suspicious_threshold = suspicious_threshold
