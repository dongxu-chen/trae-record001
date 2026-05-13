import os
import sys
import argparse
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Set

from compressor import VideoCompressor
from probe import VideoProbe
from thumbnail import ThumbnailGenerator


class BatchCompressor:
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.ts'}

    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe', presets_file='presets.json'):
        self.compressor = VideoCompressor(ffmpeg_path, ffprobe_path, presets_file)
        self.probe = VideoProbe(ffmpeg_path, ffprobe_path)
        self.thumbnail = ThumbnailGenerator(ffmpeg_path, ffprobe_path)

    def find_videos(self, directory: str, recursive: bool = False) -> List[str]:
        videos = []
        if not os.path.exists(directory):
            return videos

        if os.path.isfile(directory):
            if self._is_video_file(directory):
                return [directory]
            return videos

        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if self._is_video_file(file):
                        videos.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                full_path = os.path.join(directory, file)
                if os.path.isfile(full_path) and self._is_video_file(file):
                    videos.append(full_path)

        return sorted(videos)

    @classmethod
    def _is_video_file(cls, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.VIDEO_EXTENSIONS

    def compress_single(
        self,
        input_path: str,
        output_path: str,
        preset_name: str,
        show_progress: bool = False,
        use_temp_file: bool = True,
        crf_override: Optional[int] = None,
        cq_override: Optional[int] = None,
        preset_overrides: Optional[Dict[str, Any]] = None,
        generate_thumbnail: bool = False,
        thumbnail_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        target_output = output_path
        temp_output = None
        thumbnail_path = None

        try:
            if use_temp_file:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                name, ext = os.path.splitext(output_path)
                temp_filename = f"{name}.{uuid.uuid4().hex[:8]}.tmp{ext}"
                temp_output = os.path.join(output_dir or '.', temp_filename)

                result = self.compressor.compress(
                    input_path=input_path,
                    output_path=temp_output,
                    preset_name=preset_name,
                    show_progress=show_progress,
                    crf_override=crf_override,
                    cq_override=cq_override,
                    preset_overrides=preset_overrides
                )

                if os.path.exists(temp_output):
                    if os.path.exists(target_output):
                        os.remove(target_output)
                    os.rename(temp_output, target_output)
            else:
                result = self.compressor.compress(
                    input_path=input_path,
                    output_path=output_path,
                    preset_name=preset_name,
                    show_progress=show_progress,
                    crf_override=crf_override,
                    cq_override=cq_override,
                    preset_overrides=preset_overrides
                )

            if generate_thumbnail and os.path.exists(target_output):
                thumb_opts = thumbnail_options or {}
                thumbnail_dir = thumb_opts.get('directory') or os.path.dirname(target_output)
                if not os.path.exists(thumbnail_dir):
                    os.makedirs(thumbnail_dir, exist_ok=True)

                base_name = os.path.splitext(os.path.basename(target_output))[0]
                thumb_format = thumb_opts.get('format', 'jpg')
                thumbnail_path = os.path.join(thumbnail_dir, f"{base_name}.{thumb_format}")

                self.thumbnail.generate_thumbnail(
                    video_path=target_output,
                    output_path=thumbnail_path,
                    width=thumb_opts.get('width', 320),
                    height=thumb_opts.get('height'),
                    format=thumb_format,
                    quality=thumb_opts.get('quality', 85),
                    frame_position=thumb_opts.get('frame_position', 1.0)
                )

            return {
                'input': input_path,
                'output': target_output,
                'thumbnail': thumbnail_path,
                'success': True,
                'result': result
            }
        except Exception as e:
            if temp_output and os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except Exception:
                    pass
            return {
                'input': input_path,
                'output': target_output,
                'thumbnail': thumbnail_path,
                'success': False,
                'error': str(e)
            }

    def _generate_unique_output_path(
        self,
        input_path: str,
        output_directory: str,
        suffix: str,
        used_paths: Set[str],
        output_names: Dict[str, List[str]]
    ) -> str:
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        base_output_filename = f"{name}{suffix}{ext}"
        output_path = os.path.join(output_directory, base_output_filename)

        if output_path not in used_paths:
            return output_path

        input_dir = os.path.dirname(os.path.abspath(input_path))
        dir_hash = abs(hash(input_dir)) % 1000

        counter = 1
        while True:
            if counter <= 10:
                new_name = f"{name}{suffix}_{counter:02d}{ext}"
            else:
                new_name = f"{name}{suffix}_{dir_hash:03d}_{counter:02d}{ext}"
            new_path = os.path.join(output_directory, new_name)
            if new_path not in used_paths:
                return new_path
            counter += 1

    def compress_batch(
        self,
        video_files: List[str],
        output_directory: str,
        preset_name: str,
        max_workers: int = 2,
        overwrite: bool = False,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        suffix: str = '_compressed',
        auto_preset: bool = False,
        prefer_gpu: bool = True,
        target_quality: str = 'medium',
        generate_thumbnails: bool = False,
        thumbnail_options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(output_directory):
            os.makedirs(output_directory, exist_ok=True)

        used_paths: Set[str] = set()
        output_names: Dict[str, List[str]] = {}
        tasks = []

        for input_path in video_files:
            output_path = self._generate_unique_output_path(
                input_path,
                output_directory,
                suffix,
                used_paths,
                output_names
            )
            used_paths.add(output_path)

            if os.path.exists(output_path) and not overwrite:
                continue

            crf_override = None
            cq_override = None
            preset_overrides = None
            actual_preset = preset_name

            if auto_preset:
                try:
                    actual_preset, overrides, _ = self.compressor.get_auto_preset(
                        input_path,
                        prefer_gpu=prefer_gpu,
                        target_quality=target_quality
                    )
                    preset_overrides = overrides
                except Exception:
                    pass

            tasks.append((
                input_path,
                output_path,
                actual_preset,
                crf_override,
                cq_override,
                preset_overrides
            ))

        if not tasks:
            return []

        results = []
        if max_workers == 1:
            for input_path, output_path, actual_preset, crf_over, cq_over, preset_over in tasks:
                result = self.compress_single(
                    input_path,
                    output_path,
                    actual_preset,
                    show_progress=True,
                    use_temp_file=False,
                    crf_override=crf_over,
                    cq_override=cq_over,
                    preset_overrides=preset_over,
                    generate_thumbnail=generate_thumbnails,
                    thumbnail_options=thumbnail_options
                )
                results.append(result)
                if on_complete:
                    on_complete(result)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(
                        self.compress_single,
                        input_path,
                        output_path,
                        actual_preset,
                        False,
                        True,
                        crf_over,
                        cq_over,
                        preset_over,
                        generate_thumbnails,
                        thumbnail_options
                    ): (input_path, output_path)
                    for input_path, output_path, actual_preset, crf_over, cq_over, preset_over in tasks
                }

                for future in as_completed(future_map):
                    result = future.result()
                    results.append(result)
                    if on_complete:
                        on_complete(result)

        return results

    def get_batch_stats(self, video_files: List[str]) -> Dict[str, Any]:
        total_size = 0
        total_duration = 0
        count = 0

        for video_path in video_files:
            try:
                info = self.probe.probe(video_path)
                total_size += info.get('file_size', 0)
                total_duration += info.get('duration', 0)
                count += 1
            except Exception:
                continue

        return {
            'count': count,
            'total_size_bytes': total_size,
            'total_duration_seconds': total_duration,
            'total_size': self._format_size(total_size),
            'total_duration': self._format_duration(total_duration)
        }

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
    def _format_duration(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


def main():
    parser = argparse.ArgumentParser(description='Batch video compressor using FFmpeg')
    parser.add_argument('-i', '--input', required=True, help='Input directory or file')
    parser.add_argument('-o', '--output', required=True, help='Output directory')
    parser.add_argument('-p', '--preset', help='Compression preset name')
    parser.add_argument('-w', '--workers', type=int, default=2, help='Number of parallel workers (default: 2)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Search recursively in subdirectories')
    parser.add_argument('-f', '--overwrite', action='store_true', help='Overwrite existing output files')
    parser.add_argument('--suffix', default='_compressed', help='Suffix for output filenames (default: _compressed)')
    parser.add_argument('-l', '--list-presets', action='store_true', help='List all available presets')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without executing')

    parser.add_argument('--check-gpu', action='store_true', help='Check GPU/NVENC availability')
    parser.add_argument('--auto-preset', action='store_true', help='Auto-select preset for each video')
    parser.add_argument('--prefer-gpu', action='store_true', help='Prefer GPU when auto-selecting preset')
    parser.add_argument('--quality', default='medium', choices=['low', 'medium', 'high', 'very_high'],
                        help='Target quality for auto preset')

    parser.add_argument('--thumbnails', action='store_true', help='Generate thumbnails for compressed videos')
    parser.add_argument('--thumbnail-dir', help='Directory for thumbnails (default: same as output)')
    parser.add_argument('--thumbnail-width', type=int, default=320, help='Thumbnail width (default: 320)')
    parser.add_argument('--thumbnail-format', default='jpg', choices=['jpg', 'png', 'webp'],
                        help='Thumbnail format (default: jpg)')
    parser.add_argument('--thumbnail-quality', type=int, default=85, help='Thumbnail quality 1-100 (default: 85)')
    parser.add_argument('--thumbnail-time', type=float, default=1.0,
                        help='Frame position for thumbnail in seconds (default: 1.0)')

    args = parser.parse_args()

    batch = BatchCompressor()

    if args.check_gpu:
        gpu_info = batch.compressor.gpu_info
        import json
        print(json.dumps(gpu_info, indent=2, ensure_ascii=False))
        sys.exit(0 if gpu_info.get('nvenc_available') else 1)

    if args.list_presets:
        presets = batch.compressor.list_presets()
        print("Available presets:")
        for name, preset in presets.items():
            hardware = preset.get('hardware', 'cpu')
            print(f"  {name} [{hardware.upper()}]: {preset.get('description', 'No description')}")
        return 0

    videos = batch.find_videos(args.input, args.recursive)

    if not videos:
        print("No video files found.")
        return 1

    stats = batch.get_batch_stats(videos)
    print(f"Found {stats['count']} video(s) to compress")
    print(f"Total size: {stats['total_size']}")
    print(f"Total duration: {stats['total_duration']}")

    if args.auto_preset:
        print(f"Auto preset: enabled (quality: {args.quality})")
        if args.prefer_gpu:
            gpu_available = batch.compressor.is_nvenc_available()
            print(f"GPU available: {'Yes' if gpu_available else 'No'}")
    elif args.preset:
        print(f"Using preset: {args.preset}")
    else:
        print("Error: Either --preset or --auto-preset must be specified")
        return 1

    print(f"Parallel workers: {args.workers}")

    thumbnail_options = None
    if args.thumbnails:
        thumbnail_options = {
            'directory': args.thumbnail_dir,
            'width': args.thumbnail_width,
            'format': args.thumbnail_format,
            'quality': args.thumbnail_quality,
            'frame_position': args.thumbnail_time
        }
        print(f"Generate thumbnails: enabled")

    print()

    if args.dry_run:
        print("Dry run mode. The following files would be processed:")
        used_paths = set()
        output_names = {}
        for video in videos:
            output_path = batch._generate_unique_output_path(
                video,
                args.output,
                args.suffix,
                used_paths,
                output_names
            )
            used_paths.add(output_path)
            print(f"  {video} -> {output_path}")
        return 0

    completed = 0
    successful = 0
    failed = 0
    thumbnails_generated = 0

    def on_task_complete(result: Dict[str, Any]):
        nonlocal completed, successful, failed, thumbnails_generated
        completed += 1
        if result['success']:
            successful += 1
            thumb_info = ''
            if result.get('thumbnail'):
                thumbnails_generated += 1
                thumb_info = f" (+thumb)"
            print(f"[OK] {os.path.basename(result['input'])}{thumb_info}")
        else:
            failed += 1
            print(f"[FAILED] {os.path.basename(result['input'])}: {result.get('error', 'Unknown error')}")

    print("Starting compression...")
    print("-" * 60)

    results = batch.compress_batch(
        video_files=videos,
        output_directory=args.output,
        preset_name=args.preset or '1080p_medium',
        max_workers=args.workers,
        overwrite=args.overwrite,
        on_complete=on_task_complete,
        suffix=args.suffix,
        auto_preset=args.auto_preset,
        prefer_gpu=args.prefer_gpu,
        target_quality=args.quality,
        generate_thumbnails=args.thumbnails,
        thumbnail_options=thumbnail_options
    )

    print("-" * 60)
    print(f"Compression complete!")
    print(f"  Total processed: {completed}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    if args.thumbnails:
        print(f"  Thumbnails: {thumbnails_generated}")

    if failed > 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
