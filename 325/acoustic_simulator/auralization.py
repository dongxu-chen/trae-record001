import numpy as np
from typing import Optional, Union, Tuple, Dict, List
from scipy.signal import fftconvolve, resample
from dataclasses import dataclass
import logging
import wave
import struct

logger = logging.getLogger(__name__)


@dataclass
class AuralizationResult:
    dry_signal: np.ndarray
    wet_signal: np.ndarray
    impulse_response: np.ndarray
    fs: int
    receiver_idx: int = 0
    source_idx: int = 0

    def get_duration(self) -> float:
        return float(len(self.wet_signal) / self.fs)

    def get_peak_amplitude(self) -> float:
        return float(np.max(np.abs(self.wet_signal)))

    def normalize(self, target_peak: float = 0.95) -> None:
        peak = self.get_peak_amplitude()
        if peak > 0:
            self.wet_signal *= target_peak / peak

    def apply_master_gain(self, gain_db: float) -> None:
        gain_linear = 10 ** (gain_db / 20)
        self.wet_signal *= gain_linear


class Auralizer:
    def __init__(self, fs: int = 44100):
        self.fs = fs
        self._default_dry_signal = None

    def generate_dry_signal(self,
                            signal_type: str = "sine",
                            duration: float = 1.0,
                            frequency: float = 440.0,
                            **kwargs) -> np.ndarray:
        t = np.arange(int(duration * self.fs)) / self.fs

        if signal_type == "sine":
            signal = np.sin(2 * np.pi * frequency * t)
        elif signal_type == "square":
            signal = np.sign(np.sin(2 * np.pi * frequency * t)) * 0.5
        elif signal_type == "sawtooth":
            signal = 2 * (t * frequency - np.floor(t * frequency + 0.5))
        elif signal_type == "triangle":
            signal = 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
        elif signal_type == "white_noise":
            signal = np.random.randn(len(t)) * 0.5
        elif signal_type == "pink_noise":
            signal = self._generate_pink_noise(len(t))
        elif signal_type == "impulse":
            signal = np.zeros(len(t))
            signal[0] = 1.0
        elif signal_type == "speech_like":
            signal = self._generate_speech_like(t, frequency, **kwargs)
        else:
            raise ValueError(f"Unknown signal type: {signal_type}")

        fade_samples = min(int(0.01 * self.fs), len(signal) // 10)
        if fade_samples > 0:
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            signal[:fade_samples] *= fade_in
            signal[-fade_samples:] *= fade_out

        max_amp = np.max(np.abs(signal))
        if max_amp > 0:
            signal = signal / max_amp * 0.9

        return signal.astype(np.float64)

    def _generate_pink_noise(self, n_samples: int) -> np.ndarray:
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1.0, -2.494956002, 2.017265875, -0.522189400]

        white = np.random.randn(n_samples + 100) * 0.5
        pink = np.zeros_like(white)

        for i in range(4, len(white)):
            pink[i] = (b[0] * white[i] + b[1] * white[i - 1] + b[2] * white[i - 2] + b[3] * white[i - 3]
                       - a[1] * pink[i - 1] - a[2] * pink[i - 2] - a[3] * pink[i - 3])

        return pink[100:]

    def _generate_speech_like(self, t: np.ndarray, base_freq: float, **kwargs) -> np.ndarray:
        mod_freq = kwargs.get('mod_freq', 4.0)
        n_harmonics = kwargs.get('n_harmonics', 5)

        signal = np.zeros_like(t)
        for h in range(1, n_harmonics + 1):
            amp = 1.0 / h
            freq = base_freq * h
            vib = 1 + 0.02 * np.sin(2 * np.pi * 5 * t)
            signal += amp * np.sin(2 * np.pi * freq * vib * t)

        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
        envelope = np.maximum(envelope, 0.2)
        signal *= envelope

        return signal

    def convolve_ir(self,
                    dry_signal: np.ndarray,
                    impulse_response: np.ndarray,
                    normalize_dry: bool = True,
                    method: str = "fft") -> np.ndarray:
        if normalize_dry:
            max_amp = np.max(np.abs(dry_signal))
            if max_amp > 0:
                dry_signal = dry_signal / max_amp * 0.9

        ir_for_conv = impulse_response.copy()
        if np.max(np.abs(ir_for_conv)) > 0:
            ir_for_conv = ir_for_conv / np.max(np.abs(ir_for_conv))

        if method == "fft":
            wet_signal = fftconvolve(dry_signal, ir_for_conv, mode='full')
        elif method == "direct":
            wet_signal = np.convolve(dry_signal, ir_for_conv, mode='full')
        elif method == "overlap_add":
            wet_signal = self._overlap_add_convolve(dry_signal, ir_for_conv)
        else:
            raise ValueError(f"Unknown convolution method: {method}")

        return wet_signal.astype(np.float64)

    def _overlap_add_convolve(self, x: np.ndarray, h: np.ndarray, block_size: int = 2048) -> np.ndarray:
        len_x = len(x)
        len_h = len(h)
        len_y = len_x + len_h - 1

        y = np.zeros(len_y, dtype=np.float64)
        h_fft = np.fft.rfft(h, n=block_size + len_h - 1)

        for i in range(0, len_x, block_size):
            block = x[i:i + block_size]
            if len(block) < block_size:
                block = np.pad(block, (0, block_size - len(block)))

            block_fft = np.fft.rfft(block, n=block_size + len_h - 1)
            conv_fft = block_fft * h_fft
            conv_block = np.fft.irfft(conv_fft)

            start = i
            end = min(i + len(conv_block), len_y)
            y[start:end] += conv_block[:end - start]

        return y

    def auralize(self,
                 impulse_response: np.ndarray,
                 dry_signal: Optional[np.ndarray] = None,
                 dry_signal_type: str = "speech_like",
                 dry_duration: float = 2.0,
                 dry_frequency: float = 440.0,
                 receiver_idx: int = 0,
                 source_idx: int = 0,
                 **kwargs) -> AuralizationResult:
        if dry_signal is None:
            dry_signal = self.generate_dry_signal(
                dry_signal_type, dry_duration, dry_frequency, **kwargs
            )

        ir_single = impulse_response
        if ir_single.ndim > 1:
            while ir_single.ndim > 1 and ir_single.shape[0] == 1:
                ir_single = ir_single[0]
            while ir_single.ndim > 1 and ir_single.shape[1] == 1:
                ir_single = ir_single[:, 0]
            if ir_single.ndim > 1:
                ir_single = ir_single[receiver_idx, source_idx] if ir_single.ndim == 2 else ir_single[0]

        if self.fs != kwargs.get('ir_fs', self.fs):
            ir_fs = kwargs.get('ir_fs', self.fs)
            if ir_fs != self.fs:
                new_len = int(len(ir_single) * self.fs / ir_fs)
                ir_single = resample(ir_single, new_len)

        wet_signal = self.convolve_ir(dry_signal, ir_single)

        return AuralizationResult(
            dry_signal=dry_signal,
            wet_signal=wet_signal,
            impulse_response=ir_single,
            fs=self.fs,
            receiver_idx=receiver_idx,
            source_idx=source_idx
        )

    def auralize_bands(self,
                       band_irs: np.ndarray,
                       dry_signal: np.ndarray,
                       frequencies: np.ndarray,
                       receiver_idx: int = 0,
                       source_idx: int = 0,
                       **kwargs) -> AuralizationResult:
        from scipy.signal import butter, filtfilt

        n_bands = len(frequencies)
        n_samples = len(dry_signal)
        wet_signal = np.zeros(n_samples + np.max([len(band_irs[receiver_idx, source_idx, i, :]) for i in range(n_bands)]) - 1)

        for band_idx in range(n_bands):
            freq = frequencies[band_idx]
            ir = band_irs[receiver_idx, source_idx, band_idx, :]

            low = freq / np.sqrt(2)
            high = freq * np.sqrt(2)
            nyquist = self.fs / 2

            try:
                if high >= nyquist:
                    b, a = butter(4, low / nyquist, btype='highpass')
                elif low <= 0:
                    b, a = butter(4, high / nyquist, btype='lowpass')
                else:
                    b, a = butter(4, [low / nyquist, high / nyquist], btype='band')

                filtered_dry = filtfilt(b, a, dry_signal)
            except:
                filtered_dry = dry_signal

            band_wet = fftconvolve(filtered_dry, ir, mode='full')

            if len(band_wet) < len(wet_signal):
                band_wet = np.pad(band_wet, (0, len(wet_signal) - len(band_wet)))
            else:
                band_wet = band_wet[:len(wet_signal)]

            wet_signal += band_wet

        return AuralizationResult(
            dry_signal=dry_signal,
            wet_signal=wet_signal,
            impulse_response=np.sum(band_irs[receiver_idx, source_idx, :, :], axis=0),
            fs=self.fs,
            receiver_idx=receiver_idx,
            source_idx=source_idx
        )

    def save_wav(self,
                 file_path: str,
                 signal: np.ndarray,
                 sample_width: int = 2,
                 normalize: bool = True) -> None:
        signal_to_save = signal.copy()

        if normalize:
            max_amp = np.max(np.abs(signal_to_save))
            if max_amp > 0:
                signal_to_save = signal_to_save / max_amp * 0.95

        if sample_width == 1:
            int_signal = np.clip(signal_to_save * 127 + 128, 0, 255).astype(np.uint8)
            fmt = 'B'
        elif sample_width == 2:
            int_signal = np.clip(signal_to_save * 32767, -32768, 32767).astype(np.int16)
            fmt = 'h'
        elif sample_width == 4:
            int_signal = np.clip(signal_to_save * 2147483647, -2147483648, 2147483647).astype(np.int32)
            fmt = 'i'
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        with wave.open(file_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(self.fs)
            wav_file.setnframes(len(int_signal))

            for sample in int_signal:
                wav_file.writeframes(struct.pack(fmt, sample))

        logger.info(f"Audio saved to {file_path}")

    def load_wav(self, file_path: str) -> Tuple[np.ndarray, int]:
        with wave.open(file_path, 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            fs = wav_file.getframerate()
            n_frames = wav_file.getnframes()

            raw_data = wav_file.readframes(n_frames)

            if sample_width == 1:
                fmt = f'{n_frames * n_channels}B'
                signal = np.array(struct.unpack(fmt, raw_data), dtype=np.float64)
                signal = (signal - 128) / 127.0
            elif sample_width == 2:
                fmt = f'{n_frames * n_channels}h'
                signal = np.array(struct.unpack(fmt, raw_data), dtype=np.float64) / 32767.0
            elif sample_width == 4:
                fmt = f'{n_frames * n_channels}i'
                signal = np.array(struct.unpack(fmt, raw_data), dtype=np.float64) / 2147483647.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width}")

            if n_channels > 1:
                signal = signal.reshape(-1, n_channels).mean(axis=1)

            if fs != self.fs:
                new_len = int(len(signal) * self.fs / fs)
                signal = resample(signal, new_len)

            return signal.astype(np.float64), self.fs

    def apply_eq(self, signal: np.ndarray, eq_settings: Dict[float, float]) -> np.ndarray:
        from scipy.signal import butter, filtfilt

        result = signal.copy()
        nyquist = self.fs / 2

        for freq, gain_db in eq_settings.items():
            gain_linear = 10 ** (gain_db / 20)
            low = freq / np.sqrt(2)
            high = freq * np.sqrt(2)

            try:
                if high >= nyquist:
                    b, a = butter(2, low / nyquist, btype='highpass')
                elif low <= 0:
                    b, a = butter(2, high / nyquist, btype='lowpass')
                else:
                    b, a = butter(2, [low / nyquist, high / nyquist], btype='band')

                filtered = filtfilt(b, a, signal)
                result += (gain_linear - 1.0) * filtered
            except:
                continue

        return result
