import os
import glob
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tone_mapping import ToneMapper, ToneMappingOperator


class BatchProcessor:
    def __init__(self, use_gpu: bool = False, max_workers: int = 4):
        self.tonemapper = ToneMapper(use_gpu=use_gpu)
        self.max_workers = max_workers
        self._is_running = False
        self._is_cancelled = False

    def set_operator_params(self, op: ToneMappingOperator, params: Dict[str, float]):
        for name, value in params.items():
            self.tonemapper.set_param(op, name, value)

    def find_hdr_files(self, directory: str, recursive: bool = True) -> List[str]:
        extensions = ['*.hdr', '*.exr', '*.tif', '*.tiff']
        files = []
        for ext in extensions:
            pattern = os.path.join(directory, '**', ext) if recursive else os.path.join(directory, ext)
            files.extend(glob.glob(pattern, recursive=recursive))
        return sorted(files)

    def process_single_file(
        self,
        input_path: str,
        output_dir: str,
        op: ToneMappingOperator,
        output_format: str = 'png'
    ) -> Dict[str, Any]:
        try:
            filename = os.path.basename(input_path)
            name_without_ext = os.path.splitext(filename)[0]
            output_filename = f"{name_without_ext}_{op.value}.{output_format}"
            output_path = os.path.join(output_dir, output_filename)

            hdr_img = ToneMapper.load_hdr(input_path)
            ldr_img = self.tonemapper.process(hdr_img, op)
            ToneMapper.save_ldr(output_path, ldr_img)

            return {
                'success': True,
                'input': input_path,
                'output': output_path,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'input': input_path,
                'output': None,
                'error': str(e)
            }

    def process_batch(
        self,
        input_files: List[str],
        output_dir: str,
        op: ToneMappingOperator,
        output_format: str = 'png',
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        if not input_files:
            return []

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        self._is_running = True
        self._is_cancelled = False
        results = []
        total = len(input_files)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.process_single_file,
                    input_path,
                    output_dir,
                    op,
                    output_format
                ): input_path
                for input_path in input_files
            }

            for future in as_completed(futures):
                if self._is_cancelled:
                    for f in futures:
                        f.cancel()
                    break

                result = future.result()
                results.append(result)
                completed += 1

                if progress_callback:
                    status = "成功" if result['success'] else f"失败: {result['error']}"
                    progress_callback(completed, total, status)

        self._is_running = False
        return results

    def cancel(self):
        self._is_cancelled = True

    @property
    def is_running(self) -> bool:
        return self._is_running

    @staticmethod
    def get_supported_formats() -> List[str]:
        return ['png', 'jpg', 'jpeg', 'bmp', 'tiff']
