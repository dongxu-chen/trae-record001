import numpy as np
from scipy import signal
from scipy.fft import fft, ifft
from typing import Optional
import threading


class RNNoise:
    def __init__(self, sample_rate: int = 16000, frame_size: int = 480):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.fft_size = 512
        self.hop_size = frame_size // 2
        
        self.window = np.hanning(frame_size)
        self.noise_estimate = np.zeros(self.fft_size // 2 + 1)
        self.is_initialized = False
        self.init_frames = 0
        self.max_init_frames = 20
        
        self.alpha = 0.95
        self.beta = 0.05
        self.gain_min = 0.05
        
        self._lock = threading.Lock()
        
    def _compute_powspec(self, frame: np.ndarray) -> np.ndarray:
        frame_padded = np.pad(frame * self.window, (0, self.fft_size - self.frame_size))
        fft_result = fft(frame_padded)
        mag = np.abs(fft_result[:self.fft_size // 2 + 1])
        return mag ** 2
    
    def _estimate_noise(self, powspec: np.ndarray):
        if not self.is_initialized:
            self.noise_estimate += powspec
            self.init_frames += 1
            if self.init_frames >= self.max_init_frames:
                self.noise_estimate /= self.init_frames
                self.is_initialized = True
                print(f"[RNNoise] 噪声估计完成，使用了 {self.init_frames} 帧")
        else:
            self.noise_estimate = self.alpha * self.noise_estimate + (1 - self.alpha) * powspec
    
    def _compute_gain(self, powspec: np.ndarray) -> np.ndarray:
        if not self.is_initialized:
            return np.ones_like(powspec)
        
        snr = powspec / (self.noise_estimate + 1e-10)
        
        gain = np.ones_like(snr)
        mask = snr > 1.0
        gain[mask] = 1 - 1 / snr[mask]
        gain[~mask] = self.beta
        
        gain = np.maximum(gain, self.gain_min)
        return gain
    
    def _apply_gain(self, frame: np.ndarray, gain: np.ndarray) -> np.ndarray:
        frame_padded = np.pad(frame * self.window, (0, self.fft_size - self.frame_size))
        fft_result = fft(frame_padded)
        
        mag = np.abs(fft_result)
        phase = np.angle(fft_result)
        
        new_mag = mag.copy()
        new_mag[:self.fft_size // 2 + 1] *= gain
        new_mag[self.fft_size // 2 + 1:] = new_mag[1:self.fft_size // 2][::-1]
        
        new_fft = new_mag * np.exp(1j * phase)
        enhanced_frame = np.real(ifft(new_fft))[:self.frame_size]
        
        return enhanced_frame
    
    def process_frame(self, audio: np.ndarray) -> np.ndarray:
        with self._lock:
            if len(audio) != self.frame_size:
                audio = np.pad(audio, (0, max(0, self.frame_size - len(audio))))[:self.frame_size]
            
            powspec = self._compute_powspec(audio)
            
            if not self.is_initialized:
                self._estimate_noise(powspec)
                return audio
            
            self._estimate_noise(powspec)
            gain = self._compute_gain(powspec)
            enhanced = self._apply_gain(audio, gain)
            
            return enhanced
    
    def process_audio(self, audio: np.ndarray) -> np.ndarray:
        audio_len = len(audio)
        output = np.zeros(audio_len)
        
        num_frames = (audio_len - self.frame_size) // self.hop_size + 1
        
        for i in range(num_frames):
            start = i * self.hop_size
            end = start + self.frame_size
            
            if end > audio_len:
                break
            
            frame = audio[start:end]
            enhanced = self.process_frame(frame)
            
            output[start:end] += enhanced * self.window[:end - start]
        
        return output
    
    def reset_noise_estimate(self):
        with self._lock:
            self.noise_estimate = np.zeros(self.fft_size // 2 + 1)
            self.is_initialized = False
            self.init_frames = 0
            print("[RNNoise] 噪声估计已重置")
    
    def force_noise_estimate(self, noise_audio: np.ndarray):
        with self._lock:
            num_frames = len(noise_audio) // self.frame_size
            total_powspec = np.zeros(self.fft_size // 2 + 1)
            
            for i in range(num_frames):
                start = i * self.frame_size
                end = start + self.frame_size
                frame = noise_audio[start:end]
                total_powspec += self._compute_powspec(frame)
            
            if num_frames > 0:
                self.noise_estimate = total_powspec / num_frames
                self.is_initialized = True
                print(f"[RNNoise] 强制噪声估计完成，使用了 {num_frames} 帧")


class NoiseSuppressor:
    def __init__(self, sample_rate: int = 16000, enable: bool = True):
        self.enable = enable
        self.sample_rate = sample_rate
        self.rnnoise = RNNoise(sample_rate)
        self.frame_buffer = np.array([], dtype=np.float32)
        self.frame_size = 480
        
    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enable:
            return audio
        
        self.frame_buffer = np.concatenate([self.frame_buffer, audio])
        
        output = np.array([], dtype=np.float32)
        
        while len(self.frame_buffer) >= self.frame_size:
            frame = self.frame_buffer[:self.frame_size]
            self.frame_buffer = self.frame_buffer[self.frame_size:]
            
            enhanced = self.rnnoise.process_frame(frame)
            output = np.concatenate([output, enhanced[:self.frame_size // 2]])
        
        return output
    
    def reset(self):
        self.frame_buffer = np.array([], dtype=np.float32)
        self.rnnoise.reset_noise_estimate()
    
    def set_enable(self, enable: bool):
        self.enable = enable
        if enable:
            print("[NoiseSuppressor] 噪声抑制已启用")
        else:
            print("[NoiseSuppressor] 噪声抑制已禁用")
