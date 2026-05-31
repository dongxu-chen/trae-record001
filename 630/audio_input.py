import numpy as np
import pyaudio
import wave
import threading
from collections import deque
import time


class AudioInput:
    def __init__(
        self,
        sr=44100,
        chunk_size=1024,
        channels=1,
        format=pyaudio.paFloat32,
        buffer_seconds=10,
    ):
        self.sr = sr
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = format
        self.buffer_seconds = buffer_seconds

        self.buffer_size = int(sr * buffer_seconds)
        self.audio_buffer = deque(maxlen=self.buffer_size)

        self.p = None
        self.stream = None
        self.is_recording = False
        self.is_paused = False

        self.callback = None
        self.lock = threading.Lock()

        self.last_chunk_time = 0.0
        self.total_samples = 0

    def start_stream(self, callback=None):
        self.callback = callback
        self.p = pyaudio.PyAudio()

        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sr,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback,
        )

        self.is_recording = True
        self.stream.start_stream()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self.is_paused:
            return (in_data, pyaudio.paContinue)

        try:
            if self.format == pyaudio.paFloat32:
                audio_data = np.frombuffer(in_data, dtype=np.float32)
            elif self.format == pyaudio.paInt16:
                audio_data = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_data = np.frombuffer(in_data, dtype=np.float32)

            if self.channels > 1:
                audio_data = audio_data.reshape(-1, self.channels).mean(axis=1)

            with self.lock:
                self.audio_buffer.extend(audio_data)
                self.total_samples += len(audio_data)
                self.last_chunk_time = time.time()

            if self.callback is not None:
                self.callback(audio_data)

        except Exception as e:
            print(f"Audio callback error: {e}")

        return (in_data, pyaudio.paContinue)

    def stop_stream(self):
        self.is_recording = False
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        if self.p is not None:
            self.p.terminate()
        self.stream = None
        self.p = None

    def pause_stream(self):
        self.is_paused = True

    def resume_stream(self):
        self.is_paused = False

    def get_audio_data(self, duration=None):
        with self.lock:
            if duration is None:
                return np.array(self.audio_buffer)
            else:
                n_samples = int(duration * self.sr)
                if len(self.audio_buffer) < n_samples:
                    return np.array(self.audio_buffer)
                return np.array(list(self.audio_buffer)[-n_samples:])

    def get_recent_chunk(self, duration=1.0):
        return self.get_audio_data(duration)

    def clear_buffer(self):
        with self.lock:
            self.audio_buffer.clear()
            self.total_samples = 0

    def get_current_time(self):
        return self.total_samples / self.sr

    def save_to_wav(self, filepath, duration=None):
        audio_data = self.get_audio_data(duration)

        if len(audio_data) == 0:
            return False

        audio_int16 = (audio_data * 32767.0).astype(np.int16)

        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sr)
            wf.writeframes(audio_int16.tobytes())

        return True

    def list_input_devices(self):
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            if dev_info.get('maxInputChannels', 0) > 0:
                devices.append({
                    'index': i,
                    'name': dev_info['name'],
                    'channels': dev_info['maxInputChannels'],
                    'sample_rate': int(dev_info['defaultSampleRate']),
                })
        p.terminate()
        return devices

    def set_input_device(self, device_index):
        if self.is_recording:
            self.stop_stream()

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.sr,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback,
        )

        self.is_recording = True
        self.stream.start_stream()

    def is_active(self):
        return self.stream is not None and self.stream.is_active()
