import subprocess
import os
import math
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VideoQualityMetrics:
    resolution: Tuple[int, int]
    fps: float
    bitrate_kbps: float
    bits_per_pixel: float
    motion_level: str
    complexity_level: str
    recommended_crf: int
    recommended_cq: int


class AdaptiveCRF:
    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def analyze_video(
        self,
        video_path: str,
        probe_info: Optional[Dict[str, Any]] = None,
        target_quality: str = 'medium'
    ) -> VideoQualityMetrics:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if probe_info is None:
            probe_info = self._probe_video(video_path)

        width = probe_info.get('width', 0)
        height = probe_info.get('height', 0)
        fps = probe_info.get('fps', 0)
        bitrate = probe_info.get('video_bit_rate', 0) or probe_info.get('bit_rate', 0)

        if bitrate == 0:
            file_size = probe_info.get('file_size', 0)
            duration = probe_info.get('duration', 0)
            if duration > 0:
                bitrate = (file_size * 8) / duration

        bitrate_kbps = bitrate / 1000 if bitrate > 0 else 0

        bits_per_pixel = 0.0
        if width > 0 and height > 0 and fps > 0:
            frame_pixels = width * height
            bits_per_frame = (bitrate / fps) if fps > 0 else 0
            bits_per_pixel = bits_per_frame / frame_pixels if frame_pixels > 0 else 0

        motion_level = self._estimate_motion_level(bits_per_pixel, fps)
        complexity_level = self._estimate_complexity(width, height, bits_per_pixel)

        recommended_crf, recommended_cq = self._calculate_crf(
            width=width,
            height=height,
            bits_per_pixel=bits_per_pixel,
            motion_level=motion_level,
            target_quality=target_quality
        )

        return VideoQualityMetrics(
            resolution=(width, height),
            fps=fps,
            bitrate_kbps=bitrate_kbps,
            bits_per_pixel=bits_per_pixel,
            motion_level=motion_level,
            complexity_level=complexity_level,
            recommended_crf=recommended_crf,
            recommended_cq=recommended_cq
        )

    def _probe_video(self, video_path: str) -> Dict[str, Any]:
        try:
            from probe import VideoProbe
            probe = VideoProbe(self.ffmpeg_path, self.ffprobe_path)
            return probe.probe(video_path)
        except Exception:
            return self._fallback_probe(video_path)

    def _fallback_probe(self, video_path: str) -> Dict[str, Any]:
        import json
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        format_info = data.get('format', {})
        streams = data.get('streams', [])

        info = {
            'file_size': int(format_info.get('size', 0)),
            'duration': float(format_info.get('duration', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else 0,
        }

        for stream in streams:
            if stream.get('codec_type') == 'video':
                info['width'] = int(stream.get('width', 0))
                info['height'] = int(stream.get('height', 0))
                frame_rate = stream.get('r_frame_rate', '0/1')
                try:
                    num, den = frame_rate.split('/')
                    info['fps'] = float(num) / float(den) if int(den) != 0 else 0.0
                except Exception:
                    info['fps'] = 0.0
                info['video_bit_rate'] = int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else 0
                break

        return info

    @staticmethod
    def _estimate_motion_level(bits_per_pixel: float, fps: float) -> str:
        if fps >= 60:
            if bits_per_pixel < 0.02:
                return 'very_high'
            elif bits_per_pixel < 0.05:
                return 'high'
            else:
                return 'medium'
        elif fps >= 30:
            if bits_per_pixel < 0.03:
                return 'high'
            elif bits_per_pixel < 0.08:
                return 'medium'
            else:
                return 'low'
        else:
            if bits_per_pixel < 0.05:
                return 'medium'
            else:
                return 'low'

    @staticmethod
    def _estimate_complexity(width: int, height: int, bits_per_pixel: float) -> str:
        total_pixels = width * height

        if bits_per_pixel <= 0:
            return 'medium'

        if total_pixels >= 2000000:
            if bits_per_pixel < 0.03:
                return 'high'
            elif bits_per_pixel < 0.08:
                return 'medium'
            else:
                return 'low'
        elif total_pixels >= 900000:
            if bits_per_pixel < 0.04:
                return 'high'
            elif bits_per_pixel < 0.1:
                return 'medium'
            else:
                return 'low'
        else:
            if bits_per_pixel < 0.05:
                return 'medium'
            else:
                return 'low'

    @staticmethod
    def _calculate_crf(
        width: int,
        height: int,
        bits_per_pixel: float,
        motion_level: str,
        target_quality: str
    ) -> Tuple[int, int]:
        quality_base_crf = {
            'low': 28,
            'medium': 23,
            'high': 20,
            'very_high': 18
        }

        base_crf = quality_base_crf.get(target_quality, 23)
        base_cq = base_crf + 2

        total_pixels = width * height

        if total_pixels >= 2000000:
            resolution_adjust = 0
        elif total_pixels >= 900000:
            resolution_adjust = -1
        else:
            resolution_adjust = -2

        motion_adjust = {
            'very_high': 2,
            'high': 1,
            'medium': 0,
            'low': -1
        }.get(motion_level, 0)

        if bits_per_pixel > 0:
            if bits_per_pixel < 0.03:
                bpp_adjust = 2
            elif bits_per_pixel < 0.06:
                bpp_adjust = 1
            elif bits_per_pixel < 0.12:
                bpp_adjust = 0
            elif bits_per_pixel < 0.2:
                bpp_adjust = -1
            else:
                bpp_adjust = -2
        else:
            bpp_adjust = 0

        final_crf = base_crf + resolution_adjust + motion_adjust + bpp_adjust
        final_crf = max(16, min(32, final_crf))

        final_cq = base_cq + resolution_adjust + motion_adjust + bpp_adjust
        final_cq = max(18, min(34, final_cq))

        return final_crf, final_cq

    def get_recommended_preset_name(
        self,
        video_path: str,
        probe_info: Optional[Dict[str, Any]] = None,
        hardware: str = 'cpu',
        target_quality: str = 'medium'
    ) -> Tuple[str, Dict[str, Any]]:
        metrics = self.analyze_video(video_path, probe_info, target_quality)
        width, height = metrics.resolution

        if width >= 1920 and height >= 1080:
            resolution_tag = '1080p'
        elif width >= 1280 and height >= 720:
            resolution_tag = '720p'
        elif width >= 854 and height >= 480:
            resolution_tag = '480p'
        else:
            resolution_tag = '360p'

        quality_tags = {
            'low': '_low',
            'medium': '_medium',
            'high': '_high',
            'very_high': '_high'
        }
        quality_tag = quality_tags.get(target_quality, '_medium')

        if hardware == 'nvenc':
            if target_quality == 'low':
                preset_name = f"{resolution_tag}_nvenc_low"
            elif target_quality == 'high':
                preset_name = f"{resolution_tag}_nvenc_high"
            else:
                preset_name = f"{resolution_tag}_nvenc_medium"
        else:
            if resolution_tag == '360p':
                preset_name = '360p'
            elif resolution_tag == '480p':
                preset_name = '480p'
            else:
                preset_name = f"{resolution_tag}{quality_tag}"

        overrides = {}
        if hardware == 'nvenc':
            overrides['cq'] = metrics.recommended_cq
        else:
            overrides['crf'] = metrics.recommended_crf

        return preset_name, overrides


if __name__ == '__main__':
    import sys
    import json
    import argparse

    parser = argparse.ArgumentParser(description='Adaptive CRF calculator')
    parser.add_argument('video_file', help='Input video file')
    parser.add_argument('-q', '--quality', default='medium', choices=['low', 'medium', 'high', 'very_high'],
                        help='Target quality level')
    parser.add_argument('--hardware', default='cpu', choices=['cpu', 'nvenc'], help='Hardware type')

    args = parser.parse_args()

    adaptive = AdaptiveCRF()
    try:
        metrics = adaptive.analyze_video(args.video_file, target_quality=args.quality)
        preset_name, overrides = adaptive.get_recommended_preset_name(
            args.video_file,
            hardware=args.hardware,
            target_quality=args.quality
        )

        result = {
            'video_file': args.video_file,
            'resolution': f"{metrics.resolution[0]}x{metrics.resolution[1]}",
            'fps': round(metrics.fps, 3),
            'bitrate_kbps': round(metrics.bitrate_kbps, 2),
            'bits_per_pixel': round(metrics.bits_per_pixel, 6),
            'motion_level': metrics.motion_level,
            'complexity_level': metrics.complexity_level,
            'target_quality': args.quality,
            'recommended_crf': metrics.recommended_crf,
            'recommended_cq': metrics.recommended_cq,
            'recommended_preset': preset_name,
            'overrides': overrides
        }

        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
