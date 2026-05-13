import subprocess
import json
import os
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Dict, Any, List

getcontext().prec = 20


class VideoProbe:
    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def probe(self, video_path):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            return self._parse_probe_data(data, video_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFprobe failed: {e.stderr}")
        except json.JSONDecodeError:
            raise RuntimeError("Failed to parse FFprobe output")

    def _parse_probe_data(self, data, video_path):
        format_info = data.get('format', {})
        streams = data.get('streams', [])

        video_stream = None
        audio_stream = None

        for stream in streams:
            if stream.get('codec_type') == 'video':
                video_stream = stream
            elif stream.get('codec_type') == 'audio':
                audio_stream = stream

        info = {
            'file_path': video_path,
            'file_name': os.path.basename(video_path),
            'file_size': int(format_info.get('size', 0)),
            'duration': float(format_info.get('duration', 0)),
            'format_name': format_info.get('format_name', ''),
            'bit_rate': int(format_info.get('bit_rate', 0)) if format_info.get('bit_rate') else 0,
        }

        if video_stream:
            info.update({
                'video_codec': video_stream.get('codec_name', ''),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                'video_bit_rate': int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else 0,
                'pixel_format': video_stream.get('pix_fmt', ''),
            })

        if audio_stream:
            info.update({
                'audio_codec': audio_stream.get('codec_name', ''),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'audio_bit_rate': int(audio_stream.get('bit_rate', 0)) if audio_stream.get('bit_rate') else 0,
            })

        return info

    @staticmethod
    def _parse_frame_rate(frame_rate_str):
        try:
            num, den = frame_rate_str.split('/')
            num_int = int(num)
            den_int = int(den)
            if den_int == 0:
                return 0.0
            fraction = Fraction(num_int, den_int)
            return float(fraction)
        except (ValueError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _parse_frame_rate_decimal(frame_rate_str):
        try:
            num, den = frame_rate_str.split('/')
            num_dec = Decimal(num)
            den_dec = Decimal(den)
            if den_dec == 0:
                return Decimal('0')
            return num_dec / den_dec
        except (ValueError, ZeroDivisionError):
            return Decimal('0')

    def get_video_duration(self, video_path):
        info = self.probe(video_path)
        return info['duration']

    def get_video_resolution(self, video_path):
        info = self.probe(video_path)
        return (info.get('width', 0), info.get('height', 0))

    def check_gpu_availability(self) -> Dict[str, Any]:
        result = {
            'nvenc_available': False,
            'nvenc_codecs': [],
            'cuda_available': False,
            'gpu_info': None
        }

        try:
            cmd = [self.ffmpeg_path, '-hide_banner', '-encoders']
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = proc.stdout

            nvenc_codecs = []
            for line in output.split('\n'):
                line = line.strip()
                if 'h264_nvenc' in line:
                    nvenc_codecs.append('h264_nvenc')
                if 'hevc_nvenc' in line:
                    nvenc_codecs.append('hevc_nvenc')
                if 'av1_nvenc' in line:
                    nvenc_codecs.append('av1_nvenc')

            result['nvenc_codecs'] = sorted(list(set(nvenc_codecs)))
            result['nvenc_available'] = len(nvenc_codecs) > 0
        except Exception as e:
            result['error'] = str(e)

        try:
            cmd = [self.ffmpeg_path, '-hide_banner', '-init_hw_device', 'list']
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = proc.stdout + proc.stderr

            if 'cuda' in output.lower() or 'nvenc' in output.lower():
                result['cuda_available'] = True
        except Exception:
            pass

        return result

    def get_nvenc_presets(self, codec: str = 'h264_nvenc') -> List[str]:
        try:
            cmd = [self.ffmpeg_path, '-hide_banner', '-h', f'encoder={codec}']
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = proc.stdout

            presets = []
            for line in output.split('\n'):
                line = line.strip()
                if 'preset' in line.lower() and 'p1' in line:
                    for p in ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'slow', 'medium', 'fast', 'hp', 'hq', 'bd', 'll', 'llhq', 'llhp', 'lossless', 'losslesshp']:
                        if p in line:
                            presets.append(p)
                    break

            return presets if presets else ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']
        except Exception:
            return ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Video probe using FFprobe')
    parser.add_argument('video_file', nargs='?', help='Input video file')
    parser.add_argument('--check-gpu', action='store_true', help='Check GPU/NVENC availability')
    parser.add_argument('--list-nvenc-presets', action='store_true', help='List available NVENC presets')

    args = parser.parse_args()

    probe = VideoProbe()

    if args.check_gpu:
        gpu_info = probe.check_gpu_availability()
        print(json.dumps(gpu_info, indent=2, ensure_ascii=False))
        sys.exit(0 if gpu_info.get('nvenc_available') else 1)

    if args.list_nvenc_presets:
        presets = probe.get_nvenc_presets()
        print("Available NVENC presets:")
        for p in presets:
            print(f"  {p}")
        sys.exit(0)

    if not args.video_file:
        parser.print_help()
        sys.exit(1)

    try:
        info = probe.probe(args.video_file)
        print(json.dumps(info, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
