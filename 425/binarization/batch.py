import os
import numpy as np
import cv2
from typing import List, Dict, Callable, Optional
from .core import binarize_pipeline

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pgm", ".ppm"}


def collect_images(input_dir: str) -> List[str]:
    image_paths = []
    if not os.path.isdir(input_dir):
        return image_paths
    for fname in os.listdir(input_dir):
        ext = os.path.splitext(fname)[1].lower()
        if ext in SUPPORTED_FORMATS:
            image_paths.append(os.path.join(input_dir, fname))
    image_paths.sort()
    return image_paths


def batch_binarize(
    input_dir: str,
    output_dir: str,
    method: str = "sauvola",
    denoise: bool = True,
    denoise_method: str = "wavelet",
    bg_estimation: str = "none",
    bg_kernel_size: int = 51,
    bg_degree: int = 2,
    window_size: int = 15,
    k: float = 0.2,
    r: float = 128.0,
    block_size: int = 11,
    C: int = 2,
    post_process: bool = True,
    morph_kernel: int = 1,
    output_prefix: str = "bin_",
    output_format: str = ".png",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    image_paths = collect_images(input_dir)
    total = len(image_paths)
    results: Dict[str, str] = {}

    for idx, src_path in enumerate(image_paths):
        try:
            img = cv2.imdecode(np.fromfile(src_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                img = cv2.imdecode(np.fromfile(src_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if img is None:
                if progress_callback:
                    progress_callback(idx + 1, total, f"[跳过] 无法读取: {os.path.basename(src_path)}")
                continue

            binary = binarize_pipeline(
                img,
                method=method,
                denoise=denoise,
                denoise_method=denoise_method,
                bg_estimation=bg_estimation,
                bg_kernel_size=bg_kernel_size,
                bg_degree=bg_degree,
                window_size=window_size,
                k=k,
                r=r,
                block_size=block_size,
                C=C,
                post_process=post_process,
                morph_kernel=morph_kernel,
            )

            base = os.path.splitext(os.path.basename(src_path))[0]
            out_name = f"{output_prefix}{base}{output_format}"
            out_path = os.path.join(output_dir, out_name)

            ext = os.path.splitext(out_path)[1].lower()
            if ext == ".jpg" or ext == ".jpeg":
                cv2.imencode(ext, binary, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tofile(out_path)
            else:
                cv2.imencode(ext, binary)[1].tofile(out_path)

            results[src_path] = out_path
            if progress_callback:
                progress_callback(idx + 1, total, f"[完成] {os.path.basename(src_path)}")
        except Exception as e:
            results[src_path] = f"ERROR: {str(e)}"
            if progress_callback:
                progress_callback(idx + 1, total, f"[错误] {os.path.basename(src_path)}: {str(e)}")

    return results