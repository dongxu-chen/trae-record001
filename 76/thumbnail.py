import subprocess
import os
from typing import Optional, Dict, Any, Tuple


class ThumbnailGenerator:
    DEFAULT_WIDTH = 320
    DEFAULT_HEIGHT = 180
    DEFAULT_FORMAT = 'jpg'
    DEFAULT_QUALITY = 85

    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def generate_thumbnail(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        width: int = DEFAULT_WIDTH,
        height: Optional[int] = None,
        frame_position: Optional[float] = None,
        format: str = DEFAULT_FORMAT,
        quality: int = DEFAULT_QUALITY,
        auto_size: bool = True
    ) -> str:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_path is None:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}.thumb.{format}"

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        if auto_size:
            actual_width, actual_height = self._calculate_thumbnail_size(
                video_path,
                target_width=width,
                target_height=height
            )
        else:
            actual_width = width
            actual_height = height if height else -1

        if frame_position is None:
            frame_position = 1.0

        cmd = self._build_command(
            video_path=video_path,
            output_path=output_path,
            width=actual_width,
            height=actual_height,
            frame_position=frame_position,
            format=format,
            quality=quality
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Thumbnail generation failed: {result.stderr}")

        if not os.path.exists(output_path):
            raise RuntimeError(f"Thumbnail file was not created: {output_path}")

        return output_path

    def generate_batch(
        self,
        video_files: list,
        output_directory: str,
        width: int = DEFAULT_WIDTH,
        height: Optional[int] = None,
        format: str = DEFAULT_FORMAT,
        quality: int = DEFAULT_QUALITY,
        frame_position: Optional[float] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(output_directory):
            os.makedirs(output_directory, exist_ok=True)

        results = {
            'success': [],
            'failed': [],
            'thumbnails': {}
        }

        for video_path in video_files:
            try:
                filename = os.path.basename(video_path)
                name, _ = os.path.splitext(filename)
                output_path = os.path.join(output_directory, f"{name}.{format}")

                thumb_path = self.generate_thumbnail(
                    video_path=video_path,
                    output_path=output_path,
                    width=width,
                    height=height,
                    frame_position=frame_position,
                    format=format,
                    quality=quality
                )

                results['success'].append(video_path)
                results['thumbnails'][video_path] = thumb_path
            except Exception as e:
                results['failed'].append({
                    'file': video_path,
                    'error': str(e)
                })

        return results

    def _calculate_thumbnail_size(
        self,
        video_path: str,
        target_width: int,
        target_height: Optional[int]
    ) -> Tuple[int, int]:
        try:
            width, height = self._get_video_dimensions(video_path)
            if width == 0 or height == 0:
                return target_width, target_height if target_height else -1

            aspect_ratio = width / height

            if target_height is None:
                calc_height = int(target_width / aspect_ratio)
                calc_height = calc_height - (calc_height % 2)
                return target_width, calc_height
            else:
                target_aspect = target_width / target_height
                if abs(aspect_ratio - target_aspect) < 0.01:
                    return target_width, target_height
                else:
                    scale_w = target_width / width
                    scale_h = target_height / height
                    scale = min(scale_w, scale_h)
                    final_w = int(width * scale)
                    final_h = int(height * scale)
                    final_w = final_w - (final_w % 2)
                    final_h = final_h - (final_h % 2)
                    return final_w, final_h
        except Exception:
            return target_width, target_height if target_height else -1

    def _get_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        try:
            from probe import VideoProbe
            probe = VideoProbe(self.ffmpeg_path, self.ffprobe_path)
            info = probe.probe(video_path)
            return info.get('width', 0), info.get('height', 0)
        except Exception:
            return 0, 0

    def _build_command(
        self,
        video_path: str,
        output_path: str,
        width: int,
        height: int,
        frame_position: float,
        format: str,
        quality: int
    ) -> list:
        cmd = [
            self.ffmpeg_path,
            '-y',
            '-hide_banner',
            '-loglevel', 'error',
        ]

        if frame_position > 0:
            cmd.extend([
                '-ss', str(frame_position)
            ])

        cmd.extend([
            '-i', video_path,
            '-vframes', '1',
        ])

        if width > 0 or (height and height > 0):
            w = width if width > 0 else -1
            h = height if (height and height > 0) else -1
            if w != -1:
                w = w - (w % 2)
            if h != -1:
                h = h - (h % 2)
            cmd.extend(['-vf', f'scale={w}:{h}'])

        if format.lower() in ['jpg', 'jpeg']:
            cmd.extend([
                '-q:v', str(max(1, int(31 - (quality / 100 * 30))))
            ])
        elif format.lower() == 'png':
            pass
        elif format.lower() == 'webp':
            cmd.extend([
                '-quality', str(quality)
            ])

        cmd.append(output_path)

        return cmd

    def get_thumbnail_info(self, thumbnail_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(thumbnail_path):
            return None

        size = os.path.getsize(thumbnail_path)

        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            thumbnail_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(result.stdout)
            streams = data.get('streams', [])

            if streams:
                stream = streams[0]
                return {
                    'path': thumbnail_path,
                    'size_bytes': size,
                    'width': int(stream.get('width', 0)),
                    'height': int(stream.get('height', 0)),
                    'codec': stream.get('codec_name', ''),
                    'format': stream.get('codec_name', ''),
                    'size_kb': round(size / 1024, 2)
                }
        except Exception:
            pass

        return {
            'path': thumbnail_path,
            'size_bytes': size,
            'size_kb': round(size / 1024, 2)
        }


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Generate video thumbnails')
    parser.add_argument('-i', '--input', required=True, help='Input video file')
    parser.add_argument('-o', '--output', help='Output thumbnail path')
    parser.add_argument('-W', '--width', type=int, default=320, help='Thumbnail width')
    parser.add_argument('-H', '--height', type=int, help='Thumbnail height')
    parser.add_argument('-f', '--format', default='jpg', choices=['jpg', 'jpeg', 'png', 'webp'],
                        help='Output format')
    parser.add_argument('-q', '--quality', type=int, default=85, help='Quality (1-100)')
    parser.add_argument('-t', '--time', type=float, default=1.0,
                        help='Frame position in seconds')
    parser.add_argument('--no-auto-size', action='store_true',
                        help='Disable automatic aspect ratio calculation')

    args = parser.parse_args()

    generator = ThumbnailGenerator()

    try:
        thumb_path = generator.generate_thumbnail(
            video_path=args.input,
            output_path=args.output,
            width=args.width,
            height=args.height,
            frame_position=args.time,
            format=args.format,
            quality=args.quality,
            auto_size=not args.no_auto_size
        )

        info = generator.get_thumbnail_info(thumb_path)
        if info:
            print(f"Thumbnail generated: {thumb_path}")
            print(f"  Size: {info.get('size_kb', 0)} KB")
            if 'width' in info and info['width']:
                print(f"  Resolution: {info['width']}x{info['height']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
