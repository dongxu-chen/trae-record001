import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque, defaultdict
from scipy.fft import fft, dct
from scipy.spatial.distance import cosine
import threading
import time
from dataclasses import dataclass


@dataclass
class SpeakerSegment:
    speaker_id: int
    start_time: float
    end_time: float
    audio: np.ndarray
    embedding: Optional[np.ndarray] = None


class SpeakerEmbeddingExtractor:
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 20):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.frame_size = 512
        self.hop_size = 256
        self.window = np.hanning(self.frame_size)
    
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
    
    def extract_mfcc(self, audio: np.ndarray) -> np.ndarray:
        n_frames = (len(audio) - self.frame_size) // self.hop_size + 1
        
        if n_frames <= 0:
            return np.zeros((self.n_mfcc,))
        
        mfccs = []
        mel_filter = self._mel_filterbank(self.frame_size // 2, 26, self.sample_rate)
        
        for i in range(n_frames):
            start = i * self.hop_size
            frame = audio[start:start + self.frame_size] * self.window
            
            fft_result = np.abs(fft(frame))[:self.frame_size // 2]
            fft_result = np.maximum(fft_result, 1e-10)
            
            mel_spectrum = np.dot(mel_filter, fft_result ** 2)
            log_mel = np.log(np.maximum(mel_spectrum, 1e-10))
            
            mfcc = dct(log_mel, type=2, norm='ortho')[:self.n_mfcc]
            mfccs.append(mfcc)
        
        mfcc_array = np.array(mfccs)
        return np.mean(mfcc_array, axis=0)
    
    def extract_pitch_features(self, audio: np.ndarray) -> np.ndarray:
        if len(audio) < self.frame_size:
            return np.zeros((3,))
        
        autocorr = np.correlate(audio, audio, mode='full')
        autocorr = autocorr[len(autocorr) // 2:]
        
        peak_idx = np.argmax(autocorr[20:200]) + 20
        pitch = self.sample_rate / peak_idx if peak_idx > 0 else 0
        
        rms = np.sqrt(np.mean(audio ** 2))
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2
        
        return np.array([pitch, rms, zcr])
    
    def extract_embedding(self, audio: np.ndarray) -> np.ndarray:
        mfcc = self.extract_mfcc(audio)
        pitch = self.extract_pitch_features(audio)
        return np.concatenate([mfcc, pitch])


class SpeakerClusterer:
    def __init__(self, n_speakers: int = 2, threshold: float = 0.7):
        self.n_speakers = n_speakers
        self.threshold = threshold
        self.embeddings: List[np.ndarray] = []
        self.speaker_centers: List[np.ndarray] = []
        self.speaker_counts: List[int] = []
        
    def reset(self):
        self.embeddings = []
        self.speaker_centers = []
        self.speaker_counts = []
    
    def add_embedding(self, embedding: np.ndarray) -> int:
        if len(self.speaker_centers) < self.n_speakers:
            self.speaker_centers.append(embedding.copy())
            self.speaker_counts.append(1)
            return len(self.speaker_centers) - 1
        
        distances = [cosine(embedding, center) for center in self.speaker_centers]
        min_dist_idx = np.argmin(distances)
        
        if distances[min_dist_idx] < self.threshold:
            alpha = 1.0 / (self.speaker_counts[min_dist_idx] + 1)
            self.speaker_centers[min_dist_idx] = (
                (1 - alpha) * self.speaker_centers[min_dist_idx] + alpha * embedding
            )
            self.speaker_counts[min_dist_idx] += 1
            return min_dist_idx
        else:
            return min_dist_idx
    
    def get_speaker_id(self, embedding: np.ndarray) -> int:
        if not self.speaker_centers:
            return 0
        
        distances = [cosine(embedding, center) for center in self.speaker_centers]
        return np.argmin(distances)


class SpeakerDiarizer:
    def __init__(
        self,
        n_speakers: int = 2,
        sample_rate: int = 16000,
        segment_duration: float = 1.0,
        min_segment_duration: float = 0.3
    ):
        self.n_speakers = n_speakers
        self.sample_rate = sample_rate
        self.segment_duration = segment_duration
        self.min_segment_duration = min_segment_duration
        
        self.embedding_extractor = SpeakerEmbeddingExtractor(sample_rate)
        self.clusterer = SpeakerClusterer(n_speakers)
        
        self.audio_buffer: deque = deque(maxlen=int(sample_rate * 5))
        self.current_speaker = 0
        self.current_segment_start = 0.0
        self.current_segment_audio: List[float] = []
        
        self.segments: List[SpeakerSegment] = []
        self.speaker_transcriptions: Dict[int, List[str]] = defaultdict(list)
        
        self._lock = threading.Lock()
        self.start_time = time.time()
        
        self.speaker_names = {
            0: "说话人A",
            1: "说话人B"
        }
    
    def set_speaker_names(self, names: Dict[int, str]):
        self.speaker_names.update(names)
    
    def get_speaker_name(self, speaker_id: int) -> str:
        return self.speaker_names.get(speaker_id, f"说话人{speaker_id}")
    
    def process_audio(self, audio: np.ndarray) -> List[SpeakerSegment]:
        with self._lock:
            self.audio_buffer.extend(audio)
            self.current_segment_audio.extend(audio)
            
            new_segments = []
            segment_samples = int(self.segment_duration * self.sample_rate)
            
            while len(self.current_segment_audio) >= segment_samples:
                segment_audio = np.array(self.current_segment_audio[:segment_samples])
                self.current_segment_audio = self.current_segment_audio[segment_samples // 2:]
                
                embedding = self.embedding_extractor.extract_embedding(segment_audio)
                speaker_id = self.clusterer.add_embedding(embedding)
                
                current_time = time.time() - self.start_time
                
                if speaker_id != self.current_speaker:
                    if len(self.segments) > 0:
                        self.segments[-1].end_time = current_time
                    
                    segment = SpeakerSegment(
                        speaker_id=speaker_id,
                        start_time=current_time,
                        end_time=current_time,
                        audio=segment_audio.copy(),
                        embedding=embedding
                    )
                    self.segments.append(segment)
                    new_segments.append(segment)
                    
                    self.current_speaker = speaker_id
                elif self.segments:
                    self.segments[-1].audio = np.concatenate([
                        self.segments[-1].audio,
                        segment_audio
                    ])
                    self.segments[-1].end_time = current_time
            
            return new_segments
    
    def add_transcription(self, text: str, speaker_id: Optional[int] = None):
        if speaker_id is None:
            speaker_id = self.current_speaker
        
        self.speaker_transcriptions[speaker_id].append(text)
    
    def get_current_speaker(self) -> int:
        return self.current_speaker
    
    def get_segments(self) -> List[SpeakerSegment]:
        return self.segments.copy()
    
    def get_transcriptions(self) -> Dict[int, List[str]]:
        return dict(self.speaker_transcriptions)
    
    def get_full_transcript(self) -> str:
        lines = []
        for segment in self.segments:
            speaker_name = self.get_speaker_name(segment.speaker_id)
            transcriptions = self.speaker_transcriptions.get(segment.speaker_id, [])
            if transcriptions:
                text = ' '.join(transcriptions[-1:])
            else:
                text = "(音频片段)"
            lines.append(f"[{segment.start_time:.1f}s - {segment.end_time:.1f}s] {speaker_name}: {text}")
        return '\n'.join(lines)
    
    def reset(self):
        with self._lock:
            self.audio_buffer.clear()
            self.current_speaker = 0
            self.current_segment_start = 0.0
            self.current_segment_audio = []
            self.segments = []
            self.speaker_transcriptions.clear()
            self.clusterer.reset()
            self.start_time = time.time()
            print("[SpeakerDiarizer] 说话人分离已重置")


class RealTimeSpeakerDiarizer:
    def __init__(
        self,
        n_speakers: int = 2,
        sample_rate: int = 16000,
        enable: bool = True
    ):
        self.enable = enable
        self.diarizer = SpeakerDiarizer(n_speakers, sample_rate)
        self.speaker_change_callback = None
    
    def set_speaker_change_callback(self, callback):
        self.speaker_change_callback = callback
    
    def process(self, audio: np.ndarray) -> Tuple[int, Optional[SpeakerSegment]]:
        if not self.enable:
            return 0, None
        
        old_speaker = self.diarizer.get_current_speaker()
        segments = self.diarizer.process_audio(audio)
        new_speaker = self.diarizer.get_current_speaker()
        
        changed_segment = None
        if segments and self.speaker_change_callback:
            for seg in segments:
                if seg.speaker_id != old_speaker:
                    changed_segment = seg
                    self.speaker_change_callback(seg.speaker_id, seg)
        
        return new_speaker, changed_segment
    
    def add_transcription(self, text: str, speaker_id: Optional[int] = None):
        if self.enable:
            self.diarizer.add_transcription(text, speaker_id)
    
    def get_current_speaker(self) -> int:
        return self.diarizer.get_current_speaker()
    
    def get_speaker_name(self, speaker_id: int) -> str:
        return self.diarizer.get_speaker_name(speaker_id)
    
    def reset(self):
        self.diarizer.reset()
    
    def set_enable(self, enable: bool):
        self.enable = enable
        if enable:
            print("[SpeakerDiarizer] 说话人分离已启用")
        else:
            print("[SpeakerDiarizer] 说话人分离已禁用")
