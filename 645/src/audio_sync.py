import numpy as np
import queue
import threading
import time
from typing import Dict, Optional, Tuple
from collections import deque

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class AudioFeatureExtractor:
    def __init__(self, sample_rate: int = 22050, hop_length: int = 512,
                 n_fft: int = 2048):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.n_fft = n_fft
        
        self.audio_buffer = deque(maxlen=int(sample_rate * 2))
        self.feature_buffer = deque(maxlen=100)
        
        self.running = False
        self.audio_thread = None
        
        self.volume = 0.0
        self.rms = 0.0
        self.zero_crossing_rate = 0.0
        self.spectral_centroid = 0.0
        self.spectral_bandwidth = 0.0
        self.mfccs = np.zeros(13)
        
        self.voice_activity = 0.0
        self.speech_intensity = 0.0
        
        self.smoothing_factor = 0.3
        
        self.mouth_open_correlation = 0.0
        
        self.pyaudio_instance = None
        self.audio_stream = None

    def extract_features_from_audio(self, audio_data: np.ndarray) -> Dict[str, float]:
        if len(audio_data) < self.n_fft:
            return {}
        
        features = {}
        
        rms = np.sqrt(np.mean(audio_data ** 2))
        features['rms'] = float(rms)
        
        volume_db = 20 * np.log10(rms + 1e-8) if rms > 0 else -80
        features['volume_db'] = float(volume_db)
        
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / (2 * len(audio_data))
        features['zero_crossing_rate'] = float(zero_crossings)
        
        if LIBROSA_AVAILABLE:
            try:
                spectral_centroids = librosa.feature.spectral_centroid(
                    y=audio_data, sr=self.sample_rate, n_fft=self.n_fft, hop_length=self.hop_length
                )
                features['spectral_centroid'] = float(np.mean(spectral_centroids))
                
                spectral_bandwidth = librosa.feature.spectral_bandwidth(
                    y=audio_data, sr=self.sample_rate, n_fft=self.n_fft, hop_length=self.hop_length
                )
                features['spectral_bandwidth'] = float(np.mean(spectral_bandwidth))
                
                mfccs = librosa.feature.mfcc(
                    y=audio_data, sr=self.sample_rate, n_mfcc=13,
                    n_fft=self.n_fft, hop_length=self.hop_length
                )
                features['mfcc_mean'] = float(np.mean(mfccs))
                features['mfcc_std'] = float(np.std(mfccs))
                
                spectral_rolloff = librosa.feature.spectral_rolloff(
                    y=audio_data, sr=self.sample_rate, n_fft=self.n_fft, hop_length=self.hop_length
                )
                features['spectral_rolloff'] = float(np.mean(spectral_rolloff))
                
            except Exception as e:
                    pass
        
        features['mouth_open_predicted'] = self._predict_mouth_open_from_audio(features)
        
        return features

    def _predict_mouth_open_from_audio(self, features: Dict[str, float]) -> float:
        rms = features.get('rms', 0.0)
        
        mouth_open = min(1.0, rms * 15.0)
        
        zcr = features.get('zero_crossing_rate', 0.0)
        if zcr > 0.1:
            mouth_open *= 0.5 + 0.5 * min(1.0, (zcr - 0.1) / 0.2)
        
        spectral_centroid = features.get('spectral_centroid', 0.0)
        if spectral_centroid > 1000:
            mouth_open *= 1.2
        
        return min(1.0, max(0.0, mouth_open))

    def audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print(f"音频状态警告:", status)
        
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        self.audio_buffer.extend(audio_data)
        
        features = self.extract_features_from_audio(audio_data)
        
        self._update_features(features)
        
        return (in_data, pyaudio.paContinue)

    def _update_features(self, features: Dict[str, float]):
        new_rms = features.get('rms', 0.0)
        self.rms = (1 - self.smoothing_factor) * self.rms + self.smoothing_factor * new_rms
        
        self.volume = 20 * np.log10(self.rms + 1e-8)
        
        new_zcr = features.get('zero_crossing_rate', 0.0)
        self.zero_crossing_rate = (1 - self.smoothing_factor) * self.zero_crossing_rate + self.smoothing_factor * new_zcr
        
        new_centroid = features.get('spectral_centroid', 0.0)
        self.spectral_centroid = (1 - self.smoothing_factor) * self.spectral_centroid + self.smoothing_factor * new_centroid
        
        new_bandwidth = features.get('spectral_bandwidth', 0.0)
        self.spectral_bandwidth = (1 - self.smoothing_factor) * self.spectral_bandwidth + self.smoothing_factor * new_bandwidth
        
        self.voice_activity = 1.0 if self.rms > 0.01 else 0.0
        
        predicted_mouth_open = features.get('mouth_open_predicted', 0.0)
        self.speech_intensity = (1 - self.smoothing_factor) * self.speech_intensity + self.smoothing_factor * predicted_mouth_open
        
        self.feature_buffer.append({
            'timestamp': time.time(),
            'rms': self.rms,
            'volume_db': self.volume,
            'mouth_open_predicted': predicted_mouth_open
        })

    def start_audio_capture(self):
        if not PYAUDIO_AVAILABLE:
            print("pyaudio 未安装，音频功能不可用")
            return
        
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.hop_length,
                stream_callback=self.audio_callback
            )
            
            self.audio_stream.start_stream()
            
            while self.running:
                time.sleep(0.01)
                
        except Exception as e:
            print(f"音频捕获错误: {e}")
        finally:
            self._cleanup()

    def _cleanup(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()

    def start(self):
        if self.running:
            return
        
        self.running = True
        self.audio_thread = threading.Thread(target=self.start_audio_capture, daemon=True)
        self.audio_thread.start()
        print("音频捕获已启动")

    def stop(self):
        self.running = False
        if self.audio_thread:
            self.audio_thread.join(timeout=1.0)
        self._cleanup()
        print("音频捕获已停止")

    def get_current_features(self) -> Dict[str, float]:
        return {
            'rms': self.rms,
            'volume_db': self.volume,
            'zero_crossing_rate': self.zero_crossing_rate,
            'spectral_centroid': self.spectral_centroid,
            'spectral_bandwidth': self.spectral_bandwidth,
            'voice_activity': self.voice_activity,
            'speech_intensity': self.speech_intensity,
            'mouth_open_from_audio': self.speech_intensity
        }

    def fuse_mouth_open(self, visual_mouth_open: float, 
                        audio_weight: float = 0.3) -> float:
        audio_mouth_open = self.speech_intensity
        
        fused = (1 - audio_weight) * visual_mouth_open + audio_weight * audio_mouth_open
        
        if self.voice_activity > 0.5:
            fused = max(fused, audio_mouth_open * 0.5)
        
        return min(1.0, max(0.0, fused))


class LipSyncAudio:
    def __init__(self):
        self.extractor = AudioFeatureExtractor()
        self.audio_weight = 0.3
        self.enable_audio_sync = True
        
    def start(self):
        if self.enable_audio_sync:
            self.extractor.start()
    
    def stop(self):
        self.extractor.stop()
    
    def get_fused_mouth_open(self, visual_mouth_open: float) -> float:
        if self.enable_audio_sync and PYAUDIO_AVAILABLE:
            return self.extractor.fuse_mouth_open(visual_mouth_open, self.audio_weight)
        return visual_mouth_open
    
    def get_audio_features(self) -> Dict[str, float]:
        return self.extractor.get_current_features()
