import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ImageOptimizationResult:
    success: bool
    input_path: str
    output_path: Optional[str] = None
    original_size: int = 0
    optimized_size: int = 0
    compression_ratio: float = 0.0
    error: Optional[str] = None


class ImageOptimizer:
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}

    def __init__(
        self,
        imagemagick_path: Optional[str] = None,
        quality: int = 85,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None
    ):
        self.imagemagick_path = imagemagick_path
        self.quality = quality
        self.max_width = max_width
        self.max_height = max_height

    def _get_convert_path(self) -> str:
        if self.imagemagick_path:
            magick_exe = Path(self.imagemagick_path) / 'magick.exe'
            if magick_exe.exists():
                return str(magick_exe)
            convert_exe = Path(self.imagemagick_path) / 'convert.exe'
            if convert_exe.exists():
                return str(convert_exe)
            return str(Path(self.imagemagick_path) / 'convert')
        magick = shutil.which('magick')
        if magick:
            return magick
        convert = shutil.which('convert')
        return convert or 'convert'

    def optimize_single(self, image_path: str, output_path: Optional[str] = None) -> ImageOptimizationResult:
        input_file = Path(image_path)

        if not input_file.exists():
            return ImageOptimizationResult(
                success=False,
                input_path=image_path,
                error=f'Image not found: {image_path}'
            )

        if input_file.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return ImageOptimizationResult(
                success=False,
                input_path=image_path,
                error=f'Unsupported image format: {input_file.suffix}'
            )

        original_size = input_file.stat().st_size

        if output_path is None:
            output_path = image_path

        cmd = [self._get_convert_path(), str(input_file)]

        if self.max_width or self.max_height:
            w = self.max_width or ''
            h = self.max_height or ''
            cmd.extend(['-resize', f'{w}x{h}>'])

        cmd.extend(['-quality', str(self.quality)])
        cmd.append(output_path)

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True
            )

            optimized_size = Path(output_path).stat().st_size
            ratio = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0

            return ImageOptimizationResult(
                success=True,
                input_path=image_path,
                output_path=output_path,
                original_size=original_size,
                optimized_size=optimized_size,
                compression_ratio=ratio
            )
        except subprocess.CalledProcessError as e:
            return ImageOptimizationResult(
                success=False,
                input_path=image_path,
                error=e.stderr.strip() or str(e)
            )
        except Exception as e:
            return ImageOptimizationResult(
                success=False,
                input_path=image_path,
                error=str(e)
            )

    def optimize_epub_images(self, epub_path: str, output_epub_path: Optional[str] = None) -> list[ImageOptimizationResult]:
        input_file = Path(epub_path)

        if not input_file.exists():
            return [ImageOptimizationResult(
                success=False,
                input_path=epub_path,
                error=f'EPUB not found: {epub_path}'
            )]

        if output_epub_path is None:
            output_epub_path = epub_path

        results: list[ImageOptimizationResult] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            with zipfile.ZipFile(input_file, 'r') as zf:
                zf.extractall(tmp_path)

            for image_file in tmp_path.rglob('*'):
                if image_file.is_file() and image_file.suffix.lower() in self.IMAGE_EXTENSIONS:
                    result = self.optimize_single(str(image_file), str(image_file))
                    results.append(result)

            with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for item in tmp_path.rglob('*'):
                    if item.is_file():
                        arcname = item.relative_to(tmp_path)
                        zf.write(item, arcname)

        return results
