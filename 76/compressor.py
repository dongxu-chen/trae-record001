import subprocess
import json
import os
import shlex
from typing import Optional, Dict, Any, Callable

from probe import VideoProbe
from progress import ProgressBar, FFmpegProgressParser, SilentProgress
from adaptive_crf import AdaptiveCRF


class VideoCompressor:
    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe', presets_file='presets.json'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.presets_file = presets_file
        self.presets_data = self._load_presets_file(presets_file)
        self.presets = self.presets_data.get('presets', {})
        self.probe = VideoProbe(ffmpeg_path, ffprobe_path)
        self.adaptive_crf = AdaptiveCRF(ffmpeg_path, ffprobe_path)
        self._gpu_info = None

    @property
    def gpu_info(self) -> Dict[str, Any]:
        if self._gpu_info is None:
            self._gpu_info = self.probe.check_gpu_availability()
        return self._gpu_info

    def is_nvenc_available(self) -> bool:
        return self.gpu_info.get('nvenc_available', False)

    def get_available_nvenc_codecs(self) -> list:
        return self.gpu_info.get('nvenc_codecs', [])

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0
        size = float(size_bytes)
        while size >= 1024.0 and index < len(units) - 1:
            size /= 1024.0
            index += 1
        return f"{size:.2f} {units[index]}"

    @staticmethod
    def _load_presets_file(presets_file: str) -> Dict[str, Any]:
        if not os.path.exists(presets_file):
            raise FileNotFoundError(f"Presets file not found: {presets_file}")

        with open(presets_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        if preset_name not in self.presets:
            raise ValueError(f"Preset '{preset_name}' not found. Available: {list(self.presets.keys())}")
        return dict(self.presets[preset_name])

    def list_presets(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.presets)

    def list_nvenc_presets(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: preset for name, preset in self.presets.items()
            if preset.get('hardware') == 'nvenc'
        }

    def list_cpu_presets(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: preset for name, preset in self.presets.items()
            if preset.get('hardware', 'cpu') == 'cpu'
        }

    def get_auto_preset(
        self,
        input_path: str,
        prefer_gpu: bool = True,
        target_quality: str = 'medium'
    ) -> tuple:
        probe_info = self.probe.probe(input_path)
        hardware = 'nvenc' if (prefer_gpu and self.is_nvenc_available()) else 'cpu'

        preset_name, overrides = self.adaptive_crf.get_recommended_preset_name(
            input_path,
            probe_info=probe_info,
            hardware=hardware,
            target_quality=target_quality
        )

        if preset_name not in self.presets:
            if hardware == 'nvenc':
                preset_name = '1080p_nvenc_medium'
            else:
                preset_name = '1080p_medium'

        return preset_name, overrides, hardware

    def compress(
        self,
        input_path: str,
        output_path: str,
        preset_name: str,
        show_progress: bool = True,
        progress_callback: Optional[Callable[[float], None]] = None,
        dry_run: bool = False,
        crf_override: Optional[int] = None,
        cq_override: Optional[int] = None,
        preset_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        preset = self.get_preset(preset_name)

        if preset_overrides:
            preset.update(preset_overrides)

        if crf_override is not None:
            preset['crf'] = crf_override
        if cq_override is not None:
            preset['cq'] = cq_override

        video_info = self.probe.probe(input_path)
        duration = video_info.get('duration', 0)

        cmd = self._build_ffmpeg_command(input_path, output_path, preset, video_info)

        if dry_run:
            def quote_arg(arg):
                if os.name == 'nt':
                    if ' ' in arg or '"' in arg:
                        return '"' + arg.replace('"', '""') + '"'
                    return arg
                else:
                    return shlex.quote(arg)

            return {
                'input_path': input_path,
                'output_path': output_path,
                'preset': preset_name,
                'hardware': preset.get('hardware', 'cpu'),
                'command': ' '.join(quote_arg(arg) for arg in cmd),
                'applied_overrides': preset_overrides,
                'dry_run': True
            }

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        progress = None
        ffmpeg_parser = None

        if show_progress or progress_callback:
            if show_progress:
                hardware_tag = '[GPU]' if preset.get('hardware') == 'nvenc' else '[CPU]'
                progress = ProgressBar(
                    total=duration,
                    description=f"{hardware_tag} Compressing {os.path.basename(input_path)}"
                )

            def on_progress(current_time: float):
                if progress:
                    progress.update(current_time)
                if progress_callback:
                    progress_callback(current_time)

            ffmpeg_parser = FFmpegProgressParser(duration, on_progress)

        try:
            result = self._run_ffmpeg(cmd, ffmpeg_parser)

            if progress:
                progress.close()

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {result.stderr}")

            output_info = None
            if os.path.exists(output_path):
                output_info = self.probe.probe(output_path)

            return {
                'input_path': input_path,
                'output_path': output_path,
                'preset': preset_name,
                'hardware': preset.get('hardware', 'cpu'),
                'input_info': video_info,
                'output_info': output_info,
                'success': True
            }

        except Exception as e:
            if progress:
                progress.close()
            raise e

    def _build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        preset: Dict[str, Any],
        input_info: Dict[str, Any]
    ) -> list:
        hardware = preset.get('hardware', 'cpu')
        is_nvenc = hardware == 'nvenc'

        cmd = [
            self.ffmpeg_path,
            '-hide_banner',
            '-y',
            '-i', input_path,
        ]

        width = preset.get('width')
        height = preset.get('height')

        if width and height:
            input_width = input_info.get('width', 0)
            input_height = input_info.get('height', 0)

            if input_width and input_height:
                input_aspect = input_width / input_height
                target_aspect = width / height

                if abs(input_aspect - target_aspect) > 0.01:
                    scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                else:
                    scale_filter = f"scale={width}:{height}"

                cmd.extend([
                    '-vf', scale_filter
                ])

        if is_nvenc:
            cmd.extend([
                '-c:v', preset.get('video_codec', 'h264_nvenc'),
                '-preset', preset.get('preset', 'p4'),
            ])

            cq = preset.get('cq')
            if cq is not None:
                cmd.extend(['-cq', str(cq)])

            rc = preset.get('rc', 'vbr')
            cmd.extend(['-rc', rc])

            bitrate = preset.get('video_bitrate')
            if bitrate:
                cmd.extend([
                    '-b:v', bitrate,
                    '-maxrate', bitrate,
                    '-bufsize', '8M',
                ])

            profile = preset.get('profile')
            if profile:
                cmd.extend(['-profile:v', profile])

            level = preset.get('level')
            if level:
                cmd.extend(['-level', str(level)])
        else:
            cmd.extend([
                '-c:v', preset.get('video_codec', 'libx264'),
                '-preset', preset.get('preset', 'medium'),
                '-crf', str(preset.get('crf', 23)),
                '-b:v', preset.get('video_bitrate', '4M'),
                '-maxrate', preset.get('video_bitrate', '4M'),
                '-bufsize', '8M',
            ])

        cmd.extend([
            '-c:a', preset.get('audio_codec', 'aac'),
            '-b:a', preset.get('audio_bitrate', '128k'),
            '-ac', '2',
        ])

        cmd.extend([
            '-movflags', '+faststart',
            output_path
        ])

        return cmd

    def _run_ffmpeg(self, cmd: list, parser: Optional[FFmpegProgressParser] = None):
        if parser:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            if process.stdout:
                for line in process.stdout:
                    parser.parse_line(line)

            process.wait()
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout='',
                stderr=''
            )
        else:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Video compressor using FFmpeg')
    parser.add_argument('-i', '--input', required=True, help='Input video file')
    parser.add_argument('-o', '--output', required=True, help='Output video file')
    parser.add_argument('-p', '--preset', help='Compression preset name')
    parser.add_argument('-l', '--list-presets', action='store_true', help='List all available presets')
    parser.add_argument('--list-nvenc-presets', action='store_true', help='List NVENC presets only')
    parser.add_argument('--list-cpu-presets', action='store_true', help='List CPU presets only')
    parser.add_argument('--check-gpu', action='store_true', help='Check GPU/NVENC availability')
    parser.add_argument('--dry-run', action='store_true', help='Show command without executing')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    parser.add_argument('--auto-preset', action='store_true', help='Auto-select preset based on source')
    parser.add_argument('--prefer-gpu', action='store_true', help='Prefer GPU when auto-selecting')
    parser.add_argument('--quality', default='medium', choices=['low', 'medium', 'high', 'very_high'],
                        help='Target quality for auto preset')
    parser.add_argument('--crf', type=int, help='Override CRF value (CPU)')
    parser.add_argument('--cq', type=int, help='Override CQ value (NVENC)')

    args = parser.parse_args()

    compressor = VideoCompressor()

    if args.check_gpu:
        gpu_info = compressor.gpu_info
        print(json.dumps(gpu_info, indent=2, ensure_ascii=False))
        sys.exit(0 if gpu_info.get('nvenc_available') else 1)

    if args.list_presets:
        presets = compressor.list_presets()
        print("Available presets:")
        for name, preset in presets.items():
            hardware = preset.get('hardware', 'cpu')
            print(f"  {name} [{hardware.upper()}]: {preset.get('description', 'No description')}")
            print(f"    Resolution: {preset.get('width')}x{preset.get('height')}")
            print(f"    Video bitrate: {preset.get('video_bitrate')}")
            print(f"    Audio bitrate: {preset.get('audio_bitrate')}")
            if hardware == 'nvenc':
                print(f"    NVENC preset: {preset.get('preset', 'p4')}, CQ: {preset.get('cq', 23)}")
            else:
                print(f"    x264 preset: {preset.get('preset', 'medium')}, CRF: {preset.get('crf', 23)}")
            print()
        sys.exit(0)

    if args.list_nvenc_presets:
        presets = compressor.list_nvenc_presets()
        print("NVENC presets:")
        for name, preset in presets.items():
            print(f"  {name}: {preset.get('description', 'No description')}")
        sys.exit(0)

    if args.list_cpu_presets:
        presets = compressor.list_cpu_presets()
        print("CPU presets:")
        for name, preset in presets.items():
            print(f"  {name}: {preset.get('description', 'No description')}")
        sys.exit(0)

    preset_name = args.preset
    preset_overrides = None

    if args.auto_preset or preset_name is None:
        print(f"Analyzing video: {args.input}")
        preset_name, overrides, hardware = compressor.get_auto_preset(
            args.input,
            prefer_gpu=args.prefer_gpu,
            target_quality=args.quality
        )
        preset_overrides = overrides
        print(f"Auto-selected preset: {preset_name} [{hardware.upper()}]")
        if overrides:
            print(f"Applied overrides: {overrides}")

    try:
        result = compressor.compress(
            input_path=args.input,
            output_path=args.output,
            preset_name=preset_name,
            show_progress=not args.no_progress,
            dry_run=args.dry_run,
            crf_override=args.crf,
            cq_override=args.cq,
            preset_overrides=preset_overrides
        )

        if args.dry_run:
            print("Dry run mode. Command that would be executed:")
            print(result['command'])
        else:
            input_info = result.get('input_info', {})
            output_info = result.get('output_info', {})

            input_size = input_info.get('file_size', 0)
            output_size = output_info.get('file_size', 0) if output_info else 0

            print("\nCompression completed successfully!")
            print(f"Hardware: {result.get('hardware', 'cpu').upper()}")
            print(f"Input:  {input_info.get('file_name')} - {VideoCompressor._format_size(input_size)}")
            if output_info:
                print(f"Output: {os.path.basename(result['output_path'])} - {VideoCompressor._format_size(output_size)}")
                if input_size > 0 and output_size > 0:
                    ratio = (1 - output_size / input_size) * 100
                    print(f"Compression ratio: {ratio:.1f}% reduction")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
