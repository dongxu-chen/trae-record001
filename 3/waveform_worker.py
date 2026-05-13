import subprocess
import os
import sys
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition


def _find_tool(name):
    tool_exe = name + (".exe" if sys.platform == "win32" else "")
    if os.path.exists(tool_exe):
        return os.path.abspath(tool_exe)

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    common_dirs = [
        r"C:\Program Files\FFmpeg\bin",
        r"C:\Program Files (x86)\FFmpeg\bin",
        os.path.join(os.path.dirname(sys.executable), "ffmpeg"),
        os.path.join(os.getcwd(), "bin"),
    ]
    search_dirs = path_dirs + common_dirs if sys.platform == "win32" else path_dirs

    for directory in search_dirs:
        candidate = os.path.join(directory, tool_exe)
        if os.path.exists(candidate):
            return candidate

    return name


_ffmpeg_path = _find_tool("ffmpeg")


class WaveformData:
    def __init__(self):
        self.peaks = []
        self.duration = 0.0
        self.samples_per_pixel = 0
        self.valid = False


class WaveformCache:
    _instance = None
    _cache = {}
    _pending = set()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = WaveformCache()
        return cls._instance

    def get(self, file_path):
        if file_path in self._cache:
            return self._cache[file_path]
        return None

    def set(self, file_path, data):
        self._cache[file_path] = data

    def is_pending(self, file_path):
        return file_path in self._pending

    def mark_pending(self, file_path, pending):
        if pending:
            self._pending.add(file_path)
        else:
            self._pending.discard(file_path)


class WaveformWorker(QThread):
    waveform_ready = pyqtSignal(str, object)
    progress = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._requests = []
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._running = True
        self._samples_per_pixel = 1000

    def request_waveform(self, file_path, samples_per_pixel=1000):
        cache = WaveformCache.instance()
        if cache.get(file_path):
            return

        self._mutex.lock()
        if file_path not in self._requests:
            self._requests.append(file_path)
        self._samples_per_pixel = samples_per_pixel
        cache.mark_pending(file_path, True)
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def stop(self):
        self._mutex.lock()
        self._running = False
        self._wait_condition.wakeAll()
        self._mutex.unlock()
        self.wait(2000)

    def run(self):
        while self._running:
            self._mutex.lock()
            if not self._requests:
                self._wait_condition.wait(self._mutex, 100)
                if not self._requests and self._running:
                    self._mutex.unlock()
                    continue

            if self._requests:
                file_path = self._requests.pop(0)
            else:
                self._mutex.unlock()
                continue
            self._mutex.unlock()

            try:
                data = self._generate_waveform(file_path)
                cache = WaveformCache.instance()
                cache.set(file_path, data)
                cache.mark_pending(file_path, False)
                self.waveform_ready.emit(file_path, data)
            except Exception as e:
                cache = WaveformCache.instance()
                cache.mark_pending(file_path, False)
                print(f"Waveform generation failed for {file_path}: {e}")

    def _generate_waveform(self, file_path):
        waveform_data = WaveformData()

        if not os.path.exists(file_path):
            return waveform_data

        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

        cmd = [
            _ffmpeg_path, "-v", "quiet",
            "-i", file_path,
            "-f", "s16le",
            "-ac", "1",
            "-ar", "44100",
            "-acodec", "pcm_s16le",
            "-"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        raw_data = b""
        chunk_size = 65536
        read_count = 0

        while self._running:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            raw_data += chunk
            read_count += 1
            if read_count % 10 == 0:
                self.progress.emit(min(read_count // 5, 90))

        process.wait()

        if process.returncode != 0:
            stderr = process.stderr.read().decode("utf-8", errors="ignore")
            print(f"FFmpeg waveform error: {stderr}")
            return waveform_data

        if len(raw_data) < 4:
            return waveform_data

        samples = np.frombuffer(raw_data, dtype=np.int16)
        samples = samples.astype(np.float32) / 32768.0

        samples_per_pixel = self._samples_per_pixel
        num_samples = len(samples)

        if num_samples < samples_per_pixel:
            peaks = []
            if num_samples > 0:
                peak = max(np.max(samples), abs(np.min(samples)))
                peaks.append((peak, peak))
            waveform_data.peaks = peaks
            waveform_data.duration = num_samples / 44100.0
            waveform_data.samples_per_pixel = samples_per_pixel
            waveform_data.valid = True
            return waveform_data

        num_pixels = num_samples // samples_per_pixel
        if num_pixels == 0:
            num_pixels = 1

        peaks = []
        for i in range(num_pixels):
            start = i * samples_per_pixel
            end = min(start + samples_per_pixel, num_samples)
            segment = samples[start:end]
            if len(segment) > 0:
                peak_pos = float(np.max(segment))
                peak_neg = float(np.min(segment))
                peaks.append((peak_pos, peak_neg))

        waveform_data.peaks = peaks
        waveform_data.duration = num_samples / 44100.0
        waveform_data.samples_per_pixel = samples_per_pixel
        waveform_data.valid = True

        self.progress.emit(100)
        return waveform_data
