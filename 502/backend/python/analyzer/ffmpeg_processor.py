import subprocess
import os
import json
import math


QUALITY_PRESETS = {
    "ultra": {
        "name": "超高品质",
        "crf": "15",
        "preset": "slow",
        "audio_bitrate": "256k",
        "description": "最大画质，文件较大",
        "approx_bitrate": "约 8-15 Mbps (1080p)"
    },
    "high": {
        "name": "高品质",
        "crf": "18",
        "preset": "medium",
        "audio_bitrate": "192k",
        "description": "画质与文件大小平衡",
        "approx_bitrate": "约 5-8 Mbps (1080p)"
    },
    "balanced": {
        "name": "均衡",
        "crf": "23",
        "preset": "medium",
        "audio_bitrate": "128k",
        "description": "推荐设置，画质与体积均衡",
        "approx_bitrate": "约 3-5 Mbps (1080p)"
    },
    "compact": {
        "name": "紧凑",
        "crf": "28",
        "preset": "fast",
        "audio_bitrate": "96k",
        "description": "较小文件，画质可接受",
        "approx_bitrate": "约 1.5-3 Mbps (1080p)"
    },
    "minimal": {
        "name": "最小体积",
        "crf": "32",
        "preset": "veryfast",
        "audio_bitrate": "64k",
        "description": "最小文件大小，画质有损失",
        "approx_bitrate": "约 0.5-1.5 Mbps (1080p)"
    }
}


class FFmpegProcessor:
    @staticmethod
    def get_video_info(video_path):
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None

            info = json.loads(result.stdout)
            video_stream = None
            audio_stream = None

            for stream in info.get("streams", []):
                if stream["codec_type"] == "video" and video_stream is None:
                    video_stream = stream
                elif stream["codec_type"] == "audio" and audio_stream is None:
                    audio_stream = stream

            duration = float(info.get("format", {}).get("duration", 0))
            fps = 30
            if video_stream:
                r_frame_rate = video_stream.get("r_frame_rate", "30/1")
                if "/" in r_frame_rate:
                    num, den = r_frame_rate.split("/")
                    if int(den) > 0:
                        fps = int(num) / int(den)

            return {
                "duration": duration,
                "fps": fps,
                "width": int(video_stream.get("width", 0)) if video_stream else 0,
                "height": int(video_stream.get("height", 0)) if video_stream else 0,
                "video_codec": video_stream.get("codec_name", "") if video_stream else "",
                "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
                "bit_rate": int(info.get("format", {}).get("bit_rate", 0)),
                "format_name": info.get("format", {}).get("format_name", "")
            }
        except Exception as e:
            print(f"FFprobe error: {e}")
            return None

    @staticmethod
    def extract_clip(video_path, start_time, end_time, output_path, quality_preset="balanced"):
        duration = end_time - start_time
        preset = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["balanced"])

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", preset["preset"],
            "-crf", preset["crf"],
            "-c:a", "aac",
            "-b:a", preset["audio_bitrate"],
            "-y",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("FFmpeg clip extraction timed out")
            return False
        except FileNotFoundError:
            print("FFmpeg not found")
            return False

    @staticmethod
    def concatenate_clips(clip_paths, output_path, transition="none", transition_duration=0.5):
        if transition == "none" or len(clip_paths) < 2:
            return FFmpegProcessor._concatenate_simple(clip_paths, output_path)
        elif transition == "crossfade":
            return FFmpegProcessor._concatenate_crossfade(clip_paths, output_path, transition_duration)
        elif transition == "fade":
            return FFmpegProcessor._concatenate_fade(clip_paths, output_path, transition_duration)
        elif transition == "zoom":
            return FFmpegProcessor._concatenate_zoom(clip_paths, output_path, transition_duration)
        else:
            return FFmpegProcessor._concatenate_simple(clip_paths, output_path)

    @staticmethod
    def _concatenate_simple(clip_paths, output_path):
        list_file = os.path.join(os.path.dirname(output_path), "concat_list.txt")

        with open(list_file, "w", encoding="utf-8") as f:
            for clip_path in clip_paths:
                safe_path = clip_path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-y",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if os.path.exists(list_file):
                os.remove(list_file)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("FFmpeg concatenation timed out")
            if os.path.exists(list_file):
                os.remove(list_file)
            return False
        except FileNotFoundError:
            print("FFmpeg not found")
            if os.path.exists(list_file):
                os.remove(list_file)
            return False

    @staticmethod
    def _get_uniform_clips(clip_paths, temp_dir):
        uniform_paths = []
        target_width = None
        target_height = None

        for path in clip_paths:
            info = FFmpegProcessor.get_video_info(path)
            if info and (target_width is None):
                target_width = info["width"]
                target_height = info["height"]

        if target_width is None:
            target_width = 1920
            target_height = 1080

        for i, path in enumerate(clip_paths):
            info = FFmpegProcessor.get_video_info(path)
            if info and (info["width"] != target_width or info["height"] != target_height):
                uniform_path = os.path.join(temp_dir, f"uniform_{i:04d}.mp4")
                cmd = [
                    "ffmpeg", "-i", path,
                    "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2",
                    "-y", uniform_path
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        uniform_paths.append(uniform_path)
                    else:
                        uniform_paths.append(path)
                except Exception:
                    uniform_paths.append(path)
            else:
                recode_path = os.path.join(temp_dir, f"uniform_{i:04d}.mp4")
                cmd = [
                    "ffmpeg", "-i", path,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2",
                    "-y", recode_path
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        uniform_paths.append(recode_path)
                    else:
                        uniform_paths.append(path)
                except Exception:
                    uniform_paths.append(path)

        return uniform_paths

    @staticmethod
    def _concatenate_crossfade(clip_paths, output_path, transition_duration=0.5):
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_transition")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            uniform_paths = FFmpegProcessor._get_uniform_clips(clip_paths, temp_dir)

            if len(uniform_paths) == 1:
                import shutil
                shutil.copy2(uniform_paths[0], output_path)
                return True

            clip_infos = []
            for p in uniform_paths:
                info = FFmpegProcessor.get_video_info(p)
                clip_infos.append(info or {"duration": 5.0})

            cmd = ["ffmpeg"]
            for p in uniform_paths:
                cmd.extend(["-i", p])

            filter_parts = []
            n = len(uniform_paths)
            offset = 0.0

            for i in range(n):
                dur = clip_infos[i]["duration"]
                if i == 0:
                    offset = 0
                else:
                    prev_dur = clip_infos[i - 1]["duration"]
                    offset = offset + prev_dur - transition_duration

                fade_in = f"fade=t=in:st=0:d={transition_duration}" if i > 0 else ""
                fade_out_start = max(0, dur - transition_duration)
                fade_out = f"fade=t=out:st={fade_out_start}:d={transition_duration}" if i < n - 1 else ""

                filters = []
                if fade_in:
                    filters.append(fade_in)
                if fade_out:
                    filters.append(fade_out)
                if filters:
                    filter_parts.append(f"[{i}:v]{','.join(filters)}[v{i}]")
                else:
                    filter_parts.append(f"[{i}:v]null[v{i}]")

            mix_inputs = "".join(f"[v{i}]" for i in range(n))
            filter_parts.append(f"{mix_inputs}mix=n={n}:duration=first:dropout_transition={int(transition_duration * 30)}[vout]")

            audio_parts = []
            for i in range(n):
                audio_parts.append(f"[{i}:a]")

            audio_mix = "".join(audio_parts)
            filter_parts.append(f"{audio_mix}amix=inputs={n}:duration=first:dropout_transition={int(transition_duration * 30)}[aout]")

            filter_complex = ";".join(filter_parts)

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                output_path
            ])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0

        except Exception as e:
            print(f"Crossfade error: {e}")
            return FFmpegProcessor._concatenate_simple(clip_paths, output_path)
        finally:
            import shutil
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except OSError:
                pass

    @staticmethod
    def _concatenate_fade(clip_paths, output_path, transition_duration=0.5):
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_transition")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            faded_paths = []
            for i, clip_path in enumerate(clip_paths):
                info = FFmpegProcessor.get_video_info(clip_path)
                dur = info["duration"] if info else 5.0

                faded_path = os.path.join(temp_dir, f"faded_{i:04d}.mp4")

                vf_parts = []
                af_parts = []

                if i > 0:
                    vf_parts.append(f"fade=t=in:st=0:d={transition_duration}")
                    af_parts.append(f"afade=t=in:st=0:d={transition_duration}")

                if i < len(clip_paths) - 1:
                    fade_out_st = max(0, dur - transition_duration)
                    vf_parts.append(f"fade=t=out:st={fade_out_st}:d={transition_duration}")
                    af_parts.append(f"afade=t=out:st={fade_out_st}:d={transition_duration}")

                cmd = ["ffmpeg", "-i", clip_path]

                if vf_parts:
                    cmd.extend(["-vf", ",".join(vf_parts)])
                if af_parts:
                    cmd.extend(["-af", ",".join(af_parts)])

                cmd.extend([
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "128k",
                    "-y", faded_path
                ])

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        faded_paths.append(faded_path)
                    else:
                        faded_paths.append(clip_path)
                except Exception:
                    faded_paths.append(clip_path)

            return FFmpegProcessor._concatenate_simple(faded_paths, output_path)

        except Exception as e:
            print(f"Fade transition error: {e}")
            return FFmpegProcessor._concatenate_simple(clip_paths, output_path)
        finally:
            import shutil
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except OSError:
                pass

    @staticmethod
    def _concatenate_zoom(clip_paths, output_path, transition_duration=0.5):
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_transition")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            zoom_paths = []
            for i, clip_path in enumerate(clip_paths):
                info = FFmpegProcessor.get_video_info(clip_path)
                dur = info["duration"] if info else 5.0
                fps = info["fps"] if info else 30
                w = info["width"] if info else 1920
                h = info["height"] if info else 1080

                zoom_path = os.path.join(temp_dir, f"zoom_{i:04d}.mp4")

                vf_parts = []
                af_parts = []

                if i > 0:
                    zoom_in_frames = int(transition_duration * fps)
                    vf_parts.append(
                        f"zoompan=z='min(1+{zoom_in_frames}*on/{zoom_in_frames},1+0.5*on/{zoom_in_frames})':"
                        f"d={zoom_in_frames}:s={w}x{h}:fps={fps}"
                    )
                    af_parts.append(f"afade=t=in:st=0:d={transition_duration}")

                if i < len(clip_paths) - 1:
                    fade_out_st = max(0, dur - transition_duration)
                    vf_parts.append(f"fade=t=out:st={fade_out_st}:d={transition_duration}")
                    af_parts.append(f"afade=t=out:st={fade_out_st}:d={transition_duration}")

                if not vf_parts:
                    zoom_paths.append(clip_path)
                    continue

                cmd = ["ffmpeg", "-i", clip_path]

                if vf_parts:
                    cmd.extend(["-vf", ",".join(vf_parts)])
                if af_parts:
                    cmd.extend(["-af", ",".join(af_parts)])

                cmd.extend([
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "128k",
                    "-y", zoom_path
                ])

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        zoom_paths.append(zoom_path)
                    else:
                        zoom_paths.append(clip_path)
                except Exception:
                    zoom_paths.append(clip_path)

            return FFmpegProcessor._concatenate_simple(zoom_paths, output_path)

        except Exception as e:
            print(f"Zoom transition error: {e}")
            return FFmpegProcessor._concatenate_simple(clip_paths, output_path)
        finally:
            import shutil
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except OSError:
                pass

    @staticmethod
    def export_video(video_path, output_path, format_type="mp4", resolution="original", quality="balanced"):
        codec_map = {
            "mp4": {"vcodec": "libx264", "acodec": "aac", "ext": "mp4"},
            "webm": {"vcodec": "libvpx-vp9", "acodec": "libopus", "ext": "webm"},
            "avi": {"vcodec": "libx264", "acodec": "mp3", "ext": "avi"},
            "mov": {"vcodec": "libx264", "acodec": "aac", "ext": "mov"},
            "gif": {"vcodec": "gif", "acodec": None, "ext": "gif"}
        }

        fmt = codec_map.get(format_type, codec_map["mp4"])

        preset_data = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["balanced"])
        crf = preset_data["crf"]
        encoding_preset = preset_data["preset"]
        audio_bitrate = preset_data["audio_bitrate"]

        if format_type == "webm":
            encoding_preset = "medium"

        resolution_filter = ""
        if resolution != "original":
            res_map = {
                "4k": "3840:2160",
                "1080p": "1920:1080",
                "720p": "1280:720",
                "480p": "854:480"
            }
            if resolution in res_map:
                resolution_filter = f"-vf scale={res_map[resolution]}"

        cmd = ["ffmpeg", "-i", video_path]

        if fmt["vcodec"] == "gif":
            cmd.extend([
                "-vf", "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                "-y", output_path
            ])
        else:
            cmd.extend(["-c:v", fmt["vcodec"]])
            cmd.extend(["-preset", encoding_preset])
            cmd.extend(["-crf", crf])
            if fmt["acodec"]:
                cmd.extend(["-c:a", fmt["acodec"], "-b:a", audio_bitrate])
            if resolution_filter:
                cmd.extend(resolution_filter.split())
            cmd.extend(["-y", output_path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("FFmpeg export timed out")
            return False
        except FileNotFoundError:
            print("FFmpeg not found")
            return False

    @staticmethod
    def generate_thumbnail(video_path, output_path, timestamp=0):
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(timestamp),
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_quality_presets():
        return {
            key: {
                "name": val["name"],
                "description": val["description"],
                "approx_bitrate": val["approx_bitrate"],
                "crf": val["crf"]
            }
            for key, val in QUALITY_PRESETS.items()
        }

    @staticmethod
    def estimate_file_size(duration_seconds, quality="balanced", resolution="1080p"):
        bitrate_map = {
            "4k": {"ultra": 15000, "high": 10000, "balanced": 6000, "compact": 3000, "minimal": 1500},
            "1080p": {"ultra": 12000, "high": 7000, "balanced": 4000, "compact": 2000, "minimal": 800},
            "720p": {"ultra": 6000, "high": 4000, "balanced": 2500, "compact": 1200, "minimal": 500},
            "480p": {"ultra": 3000, "high": 2000, "balanced": 1500, "compact": 800, "minimal": 400},
            "original": {"ultra": 12000, "high": 7000, "balanced": 4000, "compact": 2000, "minimal": 800}
        }

        res = bitrate_map.get(resolution, bitrate_map["1080p"])
        bitrate_kbps = res.get(quality, res["balanced"])

        size_bytes = (bitrate_kbps * 1000 / 8) * duration_seconds
        return {
            "estimated_bytes": int(size_bytes),
            "estimated_mb": round(size_bytes / (1024 * 1024), 1),
            "bitrate_kbps": bitrate_kbps
        }
