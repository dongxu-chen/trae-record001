import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from raster_to_vector import RasterToVector


class BatchProcessor:
    def __init__(self, input_dir: str, output_dir: str, max_workers: int = None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.max_workers = max_workers or os.cpu_count() or 4
        self.results: List[Dict] = []
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}

    def discover_images(self) -> List[str]:
        images = []
        for ext in self.supported_formats:
            pattern = os.path.join(self.input_dir, f'*{ext}')
            images.extend(glob.glob(pattern))
            pattern_upper = os.path.join(self.input_dir, f'*{ext.upper()}')
            images.extend(glob.glob(pattern_upper))
        return sorted(set(images))

    def _process_single(self, args: tuple) -> Dict:
        image_path, output_dir, convert_kwargs = args
        basename = os.path.splitext(os.path.basename(image_path))[0]
        output_svg = os.path.join(output_dir, f'{basename}.svg')

        result = {
            'input': image_path,
            'output': output_svg,
            'success': False,
            'contours': 0,
            'error': None
        }

        try:
            converter = RasterToVector(image_path)
            converter.convert(output_svg, **convert_kwargs)
            result['success'] = True
            result['contours'] = len(converter.contours) if converter.contours else 0
        except Exception as e:
            result['error'] = str(e)

        return result

    def run(self, convert_kwargs: Optional[Dict] = None, progress_callback=None) -> List[Dict]:
        if convert_kwargs is None:
            convert_kwargs = {}

        os.makedirs(self.output_dir, exist_ok=True)

        images = self.discover_images()
        if not images:
            print(f"未发现支持的图像文件: {self.input_dir}")
            return []

        print(f"发现 {len(images)} 个图像文件，使用 {self.max_workers} 个工作线程")

        tasks = [(img, self.output_dir, convert_kwargs) for img in images]

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_single, task): task[0] for task in tasks}

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)
                completed += 1

                status = "✓" if result['success'] else "✗"
                contours_info = f" ({result['contours']} 轮廓)" if result['success'] else f" ({result['error']})"
                print(f"  [{completed}/{len(images)}] {status} {os.path.basename(result['input'])}{contours_info}")

                if progress_callback:
                    progress_callback(completed, len(images), result)

        return self.results

    def get_summary(self) -> Dict:
        if not self.results:
            return {'total': 0, 'success': 0, 'failed': 0}

        success = sum(1 for r in self.results if r['success'])
        failed = sum(1 for r in self.results if not r['success'])
        total_contours = sum(r['contours'] for r in self.results if r['success'])

        return {
            'total': len(self.results),
            'success': success,
            'failed': failed,
            'total_contours': total_contours,
            'failed_files': [r['input'] for r in self.results if not r['success']]
        }
