import argparse
import subprocess
from pathlib import Path
from typing import Optional

from format_detector import FormatDetector
from metadata import MetadataManager
from queue import ConversionQueue, TaskResult


class EbookConverter:
    def __init__(
        self,
        output_format: str,
        output_dir: Optional[str] = None,
        calibre_path: Optional[str] = None,
        max_workers: int = 4,
        chunk_size: int = 100,
        optimize_images: bool = False,
        image_quality: int = 85,
        image_max_width: Optional[int] = None,
        imagemagick_path: Optional[str] = None,
        generate_toc: bool = False
    ):
        self.output_format = output_format.lower()
        self.output_dir = Path(output_dir) if output_dir else None
        self.calibre_path = calibre_path
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.optimize_images = optimize_images
        self.image_quality = image_quality
        self.image_max_width = image_max_width
        self.imagemagick_path = imagemagick_path
        self.generate_toc = generate_toc

    def _get_ebook_convert_path(self) -> str:
        if self.calibre_path:
            return str(Path(self.calibre_path) / 'ebook-convert')
        return 'ebook-convert'

    def _build_convert_cmd(self, input_file: Path, output_file: Path) -> list[str]:
        cmd = [
            self._get_ebook_convert_path(),
            str(input_file),
            str(output_file)
        ]

        if self.generate_toc:
            cmd.extend([
                '--level1-toc', '//h:h1',
                '--level2-toc', '//h:h2',
                '--level3-toc', '//h:h3',
                '--use-auto-toc'
            ])

        return cmd

    def _post_process(self, output_path: str) -> str:
        if self.optimize_images and Path(output_path).suffix.lower() == '.epub':
            try:
                from image_optimizer import ImageOptimizer
                optimizer = ImageOptimizer(
                    imagemagick_path=self.imagemagick_path,
                    quality=self.image_quality,
                    max_width=self.image_max_width
                )
                optimizer.optimize_epub_images(output_path, output_path)
            except Exception:
                pass
        return output_path

    def convert_single(self, input_path: str) -> TaskResult:
        input_file = Path(input_path)

        if not input_file.exists():
            return TaskResult(
                success=False,
                input_path=input_path,
                error=f'Input file not found: {input_path}'
            )

        if not FormatDetector.is_supported(input_path):
            return TaskResult(
                success=False,
                input_path=input_path,
                error=f'Unsupported format: {input_file.suffix}'
            )

        output_dir = self.output_dir if self.output_dir else input_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f'{input_file.stem}.{self.output_format}'

        cmd = self._build_convert_cmd(input_file, output_file)

        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            ) as proc:
                _, stderr = proc.communicate(timeout=3600)
                if proc.returncode != 0:
                    return TaskResult(
                        success=False,
                        input_path=input_path,
                        error=stderr.strip() or f'Exit code: {proc.returncode}'
                    )

            self._post_process(str(output_file))

            return TaskResult(
                success=True,
                input_path=input_path,
                output_path=str(output_file)
            )
        except subprocess.TimeoutExpired:
            return TaskResult(
                success=False,
                input_path=input_path,
                error='Conversion timeout (60 minutes)'
            )
        except Exception as e:
            return TaskResult(
                success=False,
                input_path=input_path,
                error=str(e)
            )

    def batch_convert(self, input_paths: list[str]) -> list[TaskResult]:
        all_files = self._collect_files(input_paths)
        total_files = len(all_files)
        results: list[TaskResult] = []
        processed_count = 0

        def progress_callback(completed: int, total: int, result: TaskResult) -> None:
            nonlocal processed_count
            processed_count += 1
            status = '✓' if result.success else '✗'
            print(f'[{processed_count}/{total_files}] {status} {Path(result.input_path).name}')
            if not result.success and result.error:
                print(f'    Error: {result.error}')

        for i in range(0, len(all_files), self.chunk_size):
            chunk = all_files[i:i + self.chunk_size]
            queue = ConversionQueue(max_workers=self.max_workers)

            for file_path in chunk:
                queue.add_task(self.convert_single, file_path)

            chunk_results = queue.run(progress_callback=progress_callback)
            results.extend(chunk_results)
            queue.clear()

        return results

    def _collect_files(self, input_paths: list[str]) -> list[str]:
        files: list[str] = []
        for path in input_paths:
            p = Path(path)
            if p.is_dir():
                for file_path in p.rglob('*'):
                    if file_path.is_file() and FormatDetector.is_supported(str(file_path)):
                        files.append(str(file_path))
            elif p.is_file() and FormatDetector.is_supported(path):
                files.append(path)
        return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Batch convert ebook formats using Calibre'
    )
    parser.add_argument(
        'inputs',
        nargs='+',
        help='Input files or directories'
    )
    parser.add_argument(
        '-f', '--format',
        required=True,
        help='Output format (e.g., epub, mobi, pdf)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory (default: same as input)'
    )
    parser.add_argument(
        '--calibre-path',
        help='Path to Calibre installation directory'
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=4,
        help='Maximum number of concurrent workers (default: 4)'
    )
    parser.add_argument(
        '--list-formats',
        action='store_true',
        help='List supported formats and exit'
    )
    parser.add_argument(
        '--optimize-images',
        action='store_true',
        help='Optimize images in output EPUB using ImageMagick'
    )
    parser.add_argument(
        '--image-quality',
        type=int,
        default=85,
        help='Image quality (1-100, default: 85)'
    )
    parser.add_argument(
        '--image-max-width',
        type=int,
        help='Resize images wider than this (pixels)'
    )
    parser.add_argument(
        '--imagemagick-path',
        help='Path to ImageMagick installation'
    )
    parser.add_argument(
        '--generate-toc',
        action='store_true',
        help='Auto-generate TOC from h1/h2/h3 headings'
    )

    args = parser.parse_args()

    if args.list_formats:
        formats = FormatDetector.get_supported_input_formats()
        print('Supported formats:')
        for fmt in formats:
            print(f'  .{fmt}')
        return

    converter = EbookConverter(
        output_format=args.format,
        output_dir=args.output,
        calibre_path=args.calibre_path,
        max_workers=args.workers,
        optimize_images=args.optimize_images,
        image_quality=args.image_quality,
        image_max_width=args.image_max_width,
        imagemagick_path=args.imagemagick_path,
        generate_toc=args.generate_toc
    )

    print(f'Converting to {args.format.upper()}...')
    if args.optimize_images:
        print(f'  Image optimization enabled (quality={args.image_quality})')
    if args.generate_toc:
        print('  TOC generation enabled')

    results = converter.batch_convert(args.inputs)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print(f'\nConversion complete: {success_count} successful, {fail_count} failed')


if __name__ == '__main__':
    main()
