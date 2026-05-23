import pyaudio
import numpy as np
import threading
import queue
import time
from typing import Optional, Callable
from config import (
    AudioConfig, VADConfig, NoiseSuppressionConfig,
    WakeWordConfig, SpeakerDiarizationConfig
)
from vad import DoubleBufferVAD, AudioSegment
from noise_suppression import NoiseSuppressor
from keyword_spotter import WakeWordDetector
from speaker_diarization import RealTimeSpeakerDiarizer, SpeakerSegment


class AudioCapture:
    def __init__(
        self,
        audio_config: AudioConfig,
        vad_config: VADConfig,
        noise_config: Optional[NoiseSuppressionConfig] = None,
        wakeword_config: Optional[WakeWordConfig] = None,
        speaker_config: Optional[SpeakerDiarizationConfig] = None
    ):
        self.audio_config = audio_config
        self.vad_config = vad_config
        self.noise_config = noise_config
        self.wakeword_config = wakeword_config
        self.speaker_config = speaker_config
        
        self.vad = DoubleBufferVAD(vad_config)
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        
        self.frame_size = self.vad.frame_size
        self.frame_buffer = b''
        
        self.noise_suppressor: Optional[NoiseSuppressor] = None
        if noise_config and noise_config.enable:
            self.noise_suppressor = NoiseSuppressor(
                sample_rate=noise_config.sample_rate,
                enable=noise_config.enable
            )
        
        self.wakeword_detector: Optional[WakeWordDetector] = None
        if wakeword_config and wakeword_config.enable:
            self.wakeword_detector = WakeWordDetector(
                wake_words=wakeword_config.wake_words,
                sample_rate=wakeword_config.sample_rate,
                threshold=wakeword_config.threshold,
                auto_start=wakeword_config.auto_start
            )
            self.wakeword_detector.awake_duration = wakeword_config.awake_duration
        
        self.speaker_diarizer: Optional[RealTimeSpeakerDiarizer] = None
        if speaker_config and speaker_config.enable:
            self.speaker_diarizer = RealTimeSpeakerDiarizer(
                n_speakers=speaker_config.n_speakers,
                sample_rate=speaker_config.sample_rate,
                enable=speaker_config.enable
            )
            self.speaker_diarizer.diarizer.set_speaker_names(speaker_config.speaker_names)
        
        self.partial_callback: Optional[Callable] = None
        self.final_callback: Optional[Callable] = None
        self.wakeword_callback: Optional[Callable[[str], None]] = None
        self.speaker_change_callback: Optional[Callable[[int, SpeakerSegment], None]] = None
        
    def list_devices(self):
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        devices = []
        for i in range(0, num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                devices.append({
                    'index': i,
                    'name': device_info.get('name'),
                    'sample_rate': int(device_info.get('defaultSampleRate'))
                })
        return devices
    
    def set_wakeword_callback(self, callback: Callable[[str], None]):
        self.wakeword_callback = callback
        if self.wakeword_detector:
            self.wakeword_detector.set_wake_callback(callback)
    
    def set_speaker_change_callback(self, callback: Callable[[int, SpeakerSegment], None]):
        self.speaker_change_callback = callback
        if self.speaker_diarizer:
            self.speaker_diarizer.set_speaker_change_callback(callback)
    
    def start_stream(
        self,
        final_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None
    ):
        self.final_callback = final_callback
        self.partial_callback = partial_callback
        
        self.vad.start(
            recognition_callback=self._on_final_segment,
            partial_callback=self._on_partial_segment
        )
        
        self.is_running = True
        
        self.stream = self.audio.open(
            format=self.audio_config.format,
            channels=self.audio_config.channels,
            rate=self.audio_config.sample_rate,
            input=True,
            input_device_index=self.audio_config.input_device_index,
            frames_per_buffer=self.audio_config.chunk,
            stream_callback=self._audio_callback
        )
        
        self.stream.start_stream()
        print("[Audio] 音频流已启动")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            print(f"[Audio] 状态: {status}")
        
        self.frame_buffer += in_data
        frame_bytes = self.frame_size * 2
        
        while len(self.frame_buffer) >= frame_bytes:
            frame = self.frame_buffer[:frame_bytes]
            self.frame_buffer = self.frame_buffer[frame_bytes:]
            
            audio_float = DoubleBufferVAD.pcm16_to_float(frame)
            
            if self.noise_suppressor:
                audio_float = self.noise_suppressor.process(audio_float)
                frame = DoubleBufferVAD.float_to_pcm16(audio_float)
            
            if self.wakeword_detector:
                self.wakeword_detector.process(audio_float)
            
            if self.speaker_diarizer:
                self.speaker_diarizer.process(audio_float)
            
            if self.wakeword_detector and not self.wakeword_detector.is_awake:
                continue
            
            self.vad.put_audio_frame(frame)
        
        return (in_data, pyaudio.paContinue)
    
    def _on_final_segment(self, segment: AudioSegment):
        if self.final_callback:
            audio_float = DoubleBufferVAD.pcm16_to_float(segment.audio_bytes)
            
            extra_info = {}
            if self.speaker_diarizer:
                extra_info['speaker_id'] = self.speaker_diarizer.get_current_speaker()
                extra_info['speaker_name'] = self.speaker_diarizer.get_speaker_name(
                    extra_info['speaker_id']
                )
            
            self.final_callback(audio_float, segment, extra_info)
    
    def _on_partial_segment(self, segment: AudioSegment):
        if self.partial_callback:
            audio_float = DoubleBufferVAD.pcm16_to_float(segment.audio_bytes)
            
            extra_info = {}
            if self.speaker_diarizer:
                extra_info['speaker_id'] = self.speaker_diarizer.get_current_speaker()
                extra_info['speaker_name'] = self.speaker_diarizer.get_speaker_name(
                    extra_info['speaker_id']
                )
            
            self.partial_callback(audio_float, segment, extra_info)
    
    def get_current_speaker(self) -> Optional[int]:
        if self.speaker_diarizer:
            return self.speaker_diarizer.get_current_speaker()
        return None
    
    def is_awake(self) -> bool:
        if self.wakeword_detector:
            return self.wakeword_detector.is_awake
        return True
    
    def force_wake(self):
        if self.wakeword_detector:
            self.wakeword_detector.force_wake()
    
    def stop_stream(self):
        self.is_running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        self.vad.stop()
        self.frame_buffer = b''
        
        if self.noise_suppressor:
            self.noise_suppressor.reset()
        
        print("[Audio] 音频流已停止")
    
    def reset_context(self):
        self.vad.reset()
        if self.noise_suppressor:
            self.noise_suppressor.reset()
        if self.speaker_diarizer:
            self.speaker_diarizer.reset()
        print("[Audio] 上下文已重置")
    
    def close(self):
        self.stop_stream()
        self.audio.terminate()


class RealtimeASRCapture:
    def __init__(
        self,
        audio_config: AudioConfig,
        vad_config: VADConfig,
        asr_model,
        noise_config: Optional[NoiseSuppressionConfig] = None,
        wakeword_config: Optional[WakeWordConfig] = None,
        speaker_config: Optional[SpeakerDiarizationConfig] = None
    ):
        self.audio_capture = AudioCapture(
            audio_config, vad_config, noise_config, wakeword_config, speaker_config
        )
        self.asr_model = asr_model
        self.result_callback: Optional[Callable] = None
        self.partial_callback: Optional[Callable] = None
        self.accumulated_text = ""
        
        self.audio_capture.set_wakeword_callback(self._on_wakeword)
        self.audio_capture.set_speaker_change_callback(self._on_speaker_change)
        
        self.speaker_texts: dict = {}
    
    def _on_wakeword(self, keyword: str):
        print(f"[WakeWord] 检测到唤醒词: {keyword}")
    
    def _on_speaker_change(self, speaker_id: int, segment: SpeakerSegment):
        speaker_name = self.audio_capture.speaker_diarizer.get_speaker_name(speaker_id)
        print(f"[Speaker] 说话人切换: {speaker_name}")
    
    def _on_final_segment(self, audio_float: np.ndarray, segment: AudioSegment, extra_info: dict):
        result = self.asr_model.transcribe(audio_float, self.accumulated_text)
        self.accumulated_text += result['text']
        
        result['full_text'] = self.accumulated_text
        result['is_partial'] = False
        result['segment_timestamp'] = segment.timestamp
        result.update(extra_info)
        
        speaker_id = extra_info.get('speaker_id')
        if speaker_id is not None:
            if speaker_id not in self.speaker_texts:
                self.speaker_texts[speaker_id] = ""
            self.speaker_texts[speaker_id] += result['text']
            result['speaker_text'] = self.speaker_texts[speaker_id]
            
            if self.audio_capture.speaker_diarizer:
                self.audio_capture.speaker_diarizer.add_transcription(result['text'], speaker_id)
        
        if self.result_callback:
            self.result_callback(result)
        
        matched_hotwords = result.get('matched_hotwords', [])
        hotword_info = f", 热词: {matched_hotwords}" if matched_hotwords else ""
        
        speaker_info = ""
        if 'speaker_name' in extra_info:
            speaker_info = f", {extra_info['speaker_name']}"
        
        print(f"[最终]{speaker_info} {result['text']} (置信度: {result['confidence']:.2%}){hotword_info}")
    
    def _on_partial_segment(self, audio_float: np.ndarray, segment: AudioSegment, extra_info: dict):
        result = self.asr_model.transcribe(audio_float, self.accumulated_text)
        
        result['full_text'] = self.accumulated_text + result['text']
        result['is_partial'] = True
        result['segment_timestamp'] = segment.timestamp
        result.update(extra_info)
        
        if self.partial_callback:
            self.partial_callback(result)
        
        if result['text']:
            speaker_info = ""
            if 'speaker_name' in extra_info:
                speaker_info = f"[{extra_info['speaker_name']}] "
            print(f"\r[部分] {speaker_info}{result['text']} (置信度: {result['confidence']:.2%})", end='', flush=True)
    
    def start(
        self,
        result_callback: Optional[Callable] = None,
        partial_callback: Optional[Callable] = None
    ):
        self.result_callback = result_callback
        self.partial_callback = partial_callback
        self.accumulated_text = ""
        self.speaker_texts = {}
        
        if self.audio_capture.wakeword_detector and self.audio_capture.wakeword_detector.auto_start:
            self.audio_capture.force_wake()
        
        self.audio_capture.start_stream(
            final_callback=self._on_final_segment,
            partial_callback=self._on_partial_segment
        )
    
    def stop(self):
        self.audio_capture.stop_stream()
    
    def reset_context(self):
        self.accumulated_text = ""
        self.speaker_texts = {}
        self.audio_capture.reset_context()
        print("[ASR] 识别上下文已重置")
    
    def get_speaker_transcripts(self) -> dict:
        return self.speaker_texts.copy()
    
    def close(self):
        self.audio_capture.close()
