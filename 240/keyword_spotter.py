import numpy as np
from typing import List, Callable, Optional, Dict
from collections import deque
import threading
import time
from dataclasses import dataclass


@dataclass
class KeywordResult:
    keyword: str
    confidence: float
    timestamp: float
    audio_chunk: Optional[np.ndarray] = None


class KeywordSpotter:
    def __init__(
        self,
        keywords: List[str],
        sample_rate: int = 16000,
        threshold: float = 0.7,
        cooldown: float = 2.0
    ):
        self.keywords = keywords
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.cooldown = cooldown
        
        self.keyword_phonemes: Dict[str, List[str]] = {}
        self._build_keyword_phonemes()
        
        self.audio_buffer: deque = deque(maxlen=int(sample_rate * 3))
        self.last_detection_time: Dict[str, float] = {kw: 0 for kw in keywords}
        
        self.detection_callback: Optional[Callable[[KeywordResult], None]] = None
        self._lock = threading.Lock()
        
        self.is_listening = True
        
    def _build_keyword_phonemes(self):
        for keyword in self.keywords:
            phonemes = list(keyword)
            self.keyword_phonemes[keyword] = phonemes
    
    def set_callback(self, callback: Callable[[KeywordResult], None]):
        self.detection_callback = callback
    
    def _extract_mfcc(self, audio: np.ndarray, n_mfcc: int = 13) -> np.ndarray:
        from scipy.fft import fft, dct
        
        frame_size = 512
        hop_size = 256
        n_frames = (len(audio) - frame_size) // hop_size + 1
        
        if n_frames <= 0:
            return np.zeros((n_mfcc, 1))
        
        mfccs = []
        window = np.hanning(frame_size)
        
        for i in range(n_frames):
            start = i * hop_size
            frame = audio[start:start + frame_size] * window
            
            fft_result = np.abs(fft(frame))[:frame_size // 2]
            fft_result = np.maximum(fft_result, 1e-10)
            
            mel_filter = self._mel_filterbank(frame_size // 2, 26, self.sample_rate)
            mel_spectrum = np.dot(mel_filter, fft_result ** 2)
            log_mel = np.log(np.maximum(mel_spectrum, 1e-10))
            
            mfcc = dct(log_mel, type=2, norm='ortho')[:n_mfcc]
            mfccs.append(mfcc)
        
        return np.array(mfccs).T
    
    def _mel_filterbank(self, n_filters: int, n_mels: int, sample_rate: int) -> np.ndarray:
        low_freq = 0
        high_freq = sample_rate / 2
        
        low_mel = 2595 * np.log10(1 + low_freq / 700)
        high_mel = 2595 * np.log10(1 + high_freq / 700)
        
        mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
        hz_points = 700 * (10 ** (mel_points / 2595) - 1)
        
        bins = np.floor((n_filters + 1) * hz_points / sample_rate).astype(int)
        
        filterbank = np.zeros((n_mels, n_filters))
        
        for m in range(1, n_mels + 1):
            left = bins[m - 1]
            center = bins[m]
            right = bins[m + 1]
            
            for k in range(left, center):
                if k < n_filters:
                    filterbank[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
            for k in range(center, right):
                if k < n_filters:
                    filterbank[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])
        
        return filterbank
    
    def _compute_template_score(self, audio: np.ndarray, keyword: str) -> float:
        if len(audio) < self.sample_rate * 0.3:
            return 0.0
        
        energy = np.sum(audio ** 2)
        energy_threshold = 0.01 * len(audio)
        
        if energy < energy_threshold:
            return 0.0
        
        rms = np.sqrt(np.mean(audio ** 2))
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2
        
        duration = len(audio) / self.sample_rate
        target_duration = len(keyword) * 0.15
        
        duration_score = max(0, 1 - abs(duration - target_duration) / target_duration)
        energy_score = min(1.0, energy / (energy_threshold * 5))
        zcr_score = 1.0 if 0.05 < zcr < 0.5 else 0.5
        
        base_score = (duration_score * 0.4 + energy_score * 0.3 + zcr_score * 0.3)
        
        keyword_lower = keyword.lower()
        if len(keyword_lower) >= 2:
            return base_score * (0.6 + 0.4 * (len(keyword_lower) / 10))
        
        return base_score * 0.5
    
    def process_audio(self, audio: np.ndarray) -> List[KeywordResult]:
        if not self.is_listening:
            return []
        
        with self._lock:
            self.audio_buffer.extend(audio)
        
        results = []
        current_time = time.time()
        
        buffer_array = np.array(self.audio_buffer)
        
        for keyword in self.keywords:
            if current_time - self.last_detection_time[keyword] < self.cooldown:
                continue
            
            score = self._compute_template_score(buffer_array, keyword)
            
            if score >= self.threshold:
                result = KeywordResult(
                    keyword=keyword,
                    confidence=score,
                    timestamp=current_time,
                    audio_chunk=buffer_array.copy()
                )
                results.append(result)
                self.last_detection_time[keyword] = current_time
                
                if self.detection_callback:
                    self.detection_callback(result)
        
        return results
    
    def reset(self):
        with self._lock:
            self.audio_buffer.clear()
            self.last_detection_time = {kw: 0 for kw in self.keywords}
    
    def pause(self):
        self.is_listening = False
    
    def resume(self):
        self.is_listening = True
        self.reset()


class WakeWordDetector:
    def __init__(
        self,
        wake_words: List[str] = ["开始录音", "你好", "唤醒"],
        sample_rate: int = 16000,
        threshold: float = 0.75,
        auto_start: bool = True
    ):
        self.wake_words = wake_words
        self.sample_rate = sample_rate
        self.threshold = threshold
        
        self.spotter = KeywordSpotter(wake_words, sample_rate, threshold)
        self.is_awake = False
        self.awake_duration = 30.0
        self.wake_time = 0
        
        self.wake_callback: Optional[Callable[[str], None]] = None
        self.sleep_callback: Optional[Callable[[], None]] = None
        
        self._lock = threading.Lock()
        self.auto_start = auto_start
        
    def set_wake_callback(self, callback: Callable[[str], None]):
        self.wake_callback = callback
    
    def set_sleep_callback(self, callback: Callable[[], None]):
        self.sleep_callback = callback
    
    def process(self, audio: np.ndarray) -> bool:
        if self.is_awake:
            if time.time() - self.wake_time > self.awake_duration:
                self.sleep()
            return False
        
        results = self.spotter.process_audio(audio)
        
        for result in results:
            if result.confidence >= self.threshold:
                self.wake(result.keyword)
                return True
        
        return False
    
    def wake(self, keyword: str):
        with self._lock:
            self.is_awake = True
            self.wake_time = time.time()
        
        print(f"[WakeWord] 检测到唤醒词: '{keyword}'，已唤醒！")
        
        if self.wake_callback:
            self.wake_callback(keyword)
    
    def sleep(self):
        with self._lock:
            if self.is_awake:
                self.is_awake = False
                self.spotter.reset()
                print("[WakeWord] 系统已进入休眠状态")
                
                if self.sleep_callback:
                    self.sleep_callback()
    
    def force_wake(self):
        self.is_awake = True
        self.wake_time = time.time()
        print("[WakeWord] 强制唤醒系统")
    
    def reset(self):
        self.is_awake = False
        self.spotter.reset()
    
    def set_wake_words(self, wake_words: List[str]):
        self.wake_words = wake_words
        self.spotter = KeywordSpotter(wake_words, self.sample_rate, self.threshold)
        self.reset()
        print(f"[WakeWord] 更新唤醒词列表: {wake_words}")
