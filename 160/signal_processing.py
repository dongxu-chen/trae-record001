import numpy as np
from scipy import signal
from collections import deque
from threading import Lock
from typing import Optional, List, Callable
from brainflow_acquisition import EEGData


class EEGFilter:
    def __init__(self, sampling_rate: int, num_channels: int):
        self.sampling_rate = sampling_rate
        self.num_channels = num_channels
        self._filter_state: Optional[np.ndarray] = None
        
    def create_bandpass(self, low_freq: float, high_freq: float, order: int = 4):
        nyquist = self.sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist
        b, a = signal.butter(order, [low, high], btype='band')
        return b, a
        
    def create_notch(self, freq: float = 50.0, quality: float = 30.0):
        nyquist = self.sampling_rate / 2
        b, a = signal.iirnotch(freq / nyquist, quality)
        return b, a
        
    def apply_filter(self, data: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
        if self._filter_state is None:
            self._filter_state = np.zeros((max(len(a), len(b)) - 1, self.num_channels))
            
        filtered_data, self._filter_state = signal.lfilter(
            b, a, data, zi=self._filter_state, axis=0
        )
        return filtered_data
        
    def reset(self):
        self._filter_state = None


class BandPowerExtractor:
    def __init__(self, sampling_rate: int, window_size: int = 256):
        self.sampling_rate = sampling_rate
        self.window_size = window_size
        
        self.freq_bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 50)
        }
        
    def compute_band_powers(self, data: np.ndarray) -> dict:
        n = len(data)
        if n < self.window_size:
            return {band: 0.0 for band in self.freq_bands}
            
        windowed_data = data[-self.window_size:]
        
        fft_vals = np.fft.rfft(windowed_data * np.hanning(self.window_size))
        fft_freqs = np.fft.rfftfreq(self.window_size, 1.0 / self.sampling_rate)
        power_spectrum = np.abs(fft_vals) ** 2
        
        band_powers = {}
        total_power = np.sum(power_spectrum)
        
        for band, (low, high) in self.freq_bands.items():
            mask = (fft_freqs >= low) & (fft_freqs < high)
            band_power = np.sum(power_spectrum[mask])
            band_powers[band] = band_power / total_power if total_power > 0 else 0.0
            
        return band_powers


class RealtimePipeline:
    def __init__(self, sampling_rate: int, num_channels: int):
        self.sampling_rate = sampling_rate
        self.num_channels = num_channels
        
        self.eeg_filter = EEGFilter(sampling_rate, num_channels)
        self.band_extractor = BandPowerExtractor(sampling_rate)
        
        self._lock = Lock()
        self._raw_buffer = deque(maxlen=5000)
        self._filtered_buffer = deque(maxlen=5000)
        
        self.bp_b, self.bp_a = self.eeg_filter.create_bandpass(1.0, 50.0)
        self.notch_b, self.notch_a = self.eeg_filter.create_notch(50.0)
        
        self._callbacks: List[Callable[[np.ndarray, dict], None]] = []
        
        self.sample_count = 0
        
    def process_sample(self, eeg_data: EEGData) -> np.ndarray:
        with self._lock:
            data = eeg_data.eeg_data * 1e6
            
            self._raw_buffer.append(data.copy())
            
            filtered_data = self.eeg_filter.apply_filter(data, self.bp_b, self.bp_a)
            filtered_data = self.eeg_filter.apply_filter(filtered_data, self.notch_b, self.notch_a)
            
            self._filtered_buffer.append(filtered_data.copy())
            
            self.sample_count += 1
            
            if self.sample_count % 10 == 0:
                band_powers = self.band_extractor.compute_band_powers(
                    np.array(list(self._filtered_buffer))
                )
                
                for callback in self._callbacks:
                    callback(filtered_data, band_powers)
                    
            return filtered_data
            
    def get_raw_data(self, num_samples: int = 1000) -> np.ndarray:
        with self._lock:
            data = list(self._raw_buffer)[-num_samples:]
        return np.array(data).T if data else np.array([])
        
    def get_filtered_data(self, num_samples: int = 1000) -> np.ndarray:
        with self._lock:
            data = list(self._filtered_buffer)[-num_samples:]
        return np.array(data).T if data else np.array([])
        
    def add_callback(self, callback: Callable[[np.ndarray, dict], None]):
        self._callbacks.append(callback)
        
    def reset(self):
        with self._lock:
            self.eeg_filter.reset()
            self._raw_buffer.clear()
            self._filtered_buffer.clear()
            self.sample_count = 0
