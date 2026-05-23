import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VADConfig:
    mode: int = 3
    sample_rate: int = 16000
    frame_duration: int = 30
    min_silence_duration: float = 0.5
    min_speech_duration: float = 0.3
    padding_duration: float = 0.3


@dataclass
class ASRConfig:
    model_name: str = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
    device: str = "cpu"
    sample_rate: int = 16000
    chunk_length_s: float = 5.0
    stride_length_s: float = 1.0
    batch_size: int = 1


@dataclass
class HotwordConfig:
    hotwords: List[str] = field(default_factory=list)
    boost_factor: float = 10.0
    use_hotwords: bool = True


@dataclass
class WebSocketConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    max_connections: int = 10
    timeout: int = 600


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    format: int = 8
    chunk: int = 1024
    input_device_index: Optional[int] = None


@dataclass
class NoiseSuppressionConfig:
    enable: bool = True
    sample_rate: int = 16000
    frame_size: int = 480


@dataclass
class WakeWordConfig:
    enable: bool = False
    wake_words: List[str] = field(default_factory=lambda: ["开始录音", "你好", "唤醒"])
    sample_rate: int = 16000
    threshold: float = 0.75
    cooldown: float = 2.0
    awake_duration: float = 30.0
    auto_start: bool = True


@dataclass
class SpeakerDiarizationConfig:
    enable: bool = False
    n_speakers: int = 2
    sample_rate: int = 16000
    segment_duration: float = 1.0
    speaker_names: dict = field(default_factory=lambda: {0: "说话人A", 1: "说话人B"})


@dataclass
class Config:
    vad: VADConfig = field(default_factory=VADConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    hotword: HotwordConfig = field(default_factory=HotwordConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    noise_suppression: NoiseSuppressionConfig = field(default_factory=NoiseSuppressionConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    speaker_diarization: SpeakerDiarizationConfig = field(default_factory=SpeakerDiarizationConfig)

    @classmethod
    def load_from_env(cls):
        config = cls()
        config.hotword.hotwords = os.getenv("HOTWORDS", "").split(",") if os.getenv("HOTWORDS") else []
        config.asr.device = os.getenv("DEVICE", config.asr.device)
        config.websocket.port = int(os.getenv("PORT", config.websocket.port))
        
        wake_words_env = os.getenv("WAKE_WORDS", "")
        if wake_words_env:
            config.wake_word.wake_words = [w.strip() for w in wake_words_env.split(",") if w.strip()]
            config.wake_word.enable = True
        
        config.noise_suppression.enable = os.getenv("NOISE_SUPPRESSION", "true").lower() == "true"
        config.speaker_diarization.enable = os.getenv("SPEAKER_DIARIZATION", "false").lower() == "true"
        
        return config
