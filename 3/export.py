import subprocess
import os
import sys
import tempfile
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
_ffprobe_path = _find_tool("ffprobe")


class Clip:
    def __init__(self, file_path: str, start: float, end: float, 
                 timeline_start: float, volume: float = 1.0, track_index: int = 0):
        self.file_path = file_path
        self.start = start
        self.end = end
        self.timeline_start = timeline_start
        self.volume = volume
        self.track_index = track_index

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def timeline_end(self) -> float:
        return self.timeline_start + self.duration


class ExportConfig:
    def __init__(self):
        self.output_path = ""
        self.video_codec = "libx264"
        self.audio_codec = "aac"
        self.video_bitrate = "4M"
        self.audio_bitrate = "192k"
        self.fps = 30
        self.resolution = "1920x1080"
        self.preset = "medium"


class MediaInfo:
    def __init__(self):
        self.duration = 0.0
        self.has_video = False
        self.has_audio = False
        self.width = 0
        self.height = 0
        self.fps = 0.0

    @staticmethod
    def get_info(file_path: str) -> 'MediaInfo':
        info = MediaInfo()
        if not os.path.exists(file_path):
            return info

        cmd = [_ffprobe_path, "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", file_path]
        try:
            import json
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            data = json.loads(result.stdout)

            if "format" in data:
                info.duration = float(data["format"].get("duration", 0))

            if "streams" in data:
                for stream in data["streams"]:
                    if stream.get("codec_type") == "video":
                        info.has_video = True
                        info.width = int(stream.get("width", 0))
                        info.height = int(stream.get("height", 0))
                        r_frame_rate = stream.get("r_frame_rate", "0/1")
                        if "/" in r_frame_rate:
                            num, den = r_frame_rate.split("/")
                            if int(den) > 0:
                                info.fps = float(num) / float(den)
                    elif stream.get("codec_type") == "audio":
                        info.has_audio = True
        except Exception:
            pass
        return info


class ExportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)

    def __init__(self, clips, config: ExportConfig):
        super().__init__()
        self.clips = clips
        self.config = config
        self._canceled = False

    def cancel(self):
        self._canceled = True

    def run(self):
        if not self.clips:
            self.finished.emit(False, "没有可导出的片段")
            return

        output_dir = os.path.dirname(self.config.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        temp_dir = tempfile.mkdtemp()
        try:
            total_duration = self._get_total_duration()
            if total_duration <= 0:
                self.finished.emit(False, "总时长计算错误")
                return

            video_clips = [c for c in self.clips if MediaInfo.get_info(c.file_path).has_video]
            audio_clips = [c for c in self.clips if MediaInfo.get_info(c.file_path).has_audio]

            inputs = []
            filter_parts = []
            map_args = []
            index = 0

            for i, clip in enumerate(self.clips):
                clip_info = MediaInfo.get_info(clip.file_path)

                inputs.extend(["-i", clip.file_path])

                if clip_info.has_video:
                    v_filter = f"[{index}:v]trim=start={clip.start}:end={clip.end},"
                    v_filter += f"setpts=PTS-STARTPTS"
                    v_filter += f",scale={self.config.resolution}"
                    v_filter += f",fps={self.config.fps}"
                    v_filter += f"[v{i}]"
                    filter_parts.append(v_filter)

                if clip_info.has_audio:
                    a_filter = f"[{index}:a]atrim=start={clip.start}:end={clip.end},"
                    a_filter += f"asetpts=PTS-STARTPTS"
                    if clip.volume != 1.0:
                        a_filter += f",volume={clip.volume}"
                    a_filter += f"[a{i}]"
                    filter_parts.append(a_filter)

                index += 1

            video_inputs = [f"[v{i}]" for i, c in enumerate(self.clips) 
                          if MediaInfo.get_info(c.file_path).has_video]
            audio_inputs = [f"[a{i}]" for i, c in enumerate(self.clips) 
                          if MediaInfo.get_info(c.file_path).has_audio]

            if video_inputs:
                v_concat = "".join(video_inputs) + f"concat=n={len(video_inputs)}:v=1:a=0[outv]"
                filter_parts.append(v_concat)
                map_args.extend(["-map", "[outv]"])
            else:
                map_args.extend(["-f", "lavfi", "-i", "color=c=black:s={}:r={}:d={}".format(
                    self.config.resolution, self.config.fps, total_duration)])
                map_args.extend(["-map", f"{index}:v"])
                index += 1

            if audio_inputs:
                if len(audio_inputs) > 1:
                    a_concat = "".join(audio_inputs) + f"amix=inputs={len(audio_inputs)}[outa]"
                else:
                    a_concat = "".join(audio_inputs) + f"acopy[outa]"
                filter_parts.append(a_concat)
                map_args.extend(["-map", "[outa]"])
            else:
                map_args.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo:d={}".format(total_duration)])
                map_args.extend(["-map", f"{index}:a"])

            cmd = [_ffmpeg_path, "-y"]
            cmd.extend(inputs)

            if filter_parts:
                filter_complex = ";".join(filter_parts)
                cmd.extend(["-filter_complex", filter_complex])

            cmd.extend(map_args)
            cmd.extend([
                "-c:v", self.config.video_codec,
                "-b:v", self.config.video_bitrate,
                "-preset", self.config.preset,
                "-c:a", self.config.audio_codec,
                "-b:a", self.config.audio_bitrate,
                "-t", str(total_duration),
                self.config.output_path
            ])

            self.log.emit(f"执行命令: {' '.join(cmd)}")
            self.progress.emit(0)

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            last_percent = 0
            for line in process.stdout:
                if self._canceled:
                    process.terminate()
                    self.finished.emit(False, "已取消")
                    return
                if "time=" in line:
                    current = self._parse_time(line)
                    percent = min(int((current / total_duration) * 100), 99)
                    if percent != last_percent:
                        self.progress.emit(percent)
                        last_percent = percent

            process.wait()
            self.progress.emit(100)

            if process.returncode == 0:
                self.finished.emit(True, "导出成功")
            else:
                self.finished.emit(False, f"导出失败，错误码: {process.returncode}")

        except Exception as e:
            self.finished.emit(False, f"导出异常: {str(e)}")
        finally:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _get_total_duration(self) -> float:
        if not self.clips:
            return 0
        return max(c.timeline_end for c in self.clips)

    def _parse_time(self, line: str) -> float:
        try:
            idx = line.find("time=")
            if idx == -1:
                return 0
            time_str = line[idx + 5:].split(" ")[0]
            if ":" in time_str:
                parts = time_str.split(":")
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
                return h * 3600 + m * 60 + s
            return float(time_str)
        except:
            return 0


class WaveformPreprocessor:
    @staticmethod
    def pregenerate_waveform(file_path, samples_per_pixel=1000):
        if not os.path.exists(file_path):
            return None

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

        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break
            raw_data += chunk

        process.wait()

        if process.returncode != 0:
            return None

        if len(raw_data) < 4:
            return None

        try:
            import numpy as np
            samples = np.frombuffer(raw_data, dtype=np.int16)
            samples = samples.astype(np.float32) / 32768.0

            num_samples = len(samples)
            if num_samples < samples_per_pixel:
                peaks = []
                if num_samples > 0:
                    peak = max(float(np.max(samples)), abs(float(np.min(samples))))
                    peaks.append((peak, peak))
                return {
                    "peaks": peaks,
                    "duration": num_samples / 44100.0,
                    "samples_per_pixel": samples_per_pixel,
                    "valid": True
                }

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

            return {
                "peaks": peaks,
                "duration": num_samples / 44100.0,
                "samples_per_pixel": samples_per_pixel,
                "valid": True
            }
        except ImportError:
            return None
        except Exception:
            return None
