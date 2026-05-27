import numpy as np
from typing import Union, Tuple, List, Callable, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import os
import warnings

from .structuring_element import StructuringElement
from .core import erode, dilate, open_op, close_op, top_hat, black_hat, morphological_gradient
from .reconstruction import fill_holes, extract_boundary, remove_small_objects


class BatchProcessor:
    def __init__(self, max_workers: Optional[int] = None):
        if max_workers is None:
            max_workers = max(1, os.cpu_count() - 1)
        self.max_workers = max_workers

    def process_batch(
        self,
        images: List[np.ndarray],
        operation: str,
        structure: Union[np.ndarray, StructuringElement],
        **kwargs
    ) -> List[np.ndarray]:
        operation_funcs = {
            'erode': erode,
            'dilate': dilate,
            'open': open_op,
            'close': close_op,
            'top_hat': top_hat,
            'black_hat': black_hat,
            'gradient': morphological_gradient,
            'fill_holes': fill_holes,
            'boundary': extract_boundary,
            'remove_small': remove_small_objects
        }

        if operation not in operation_funcs:
            raise ValueError(f"Unknown operation: {operation}")

        func = operation_funcs[operation]

        results = [None] * len(images)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for idx, img in enumerate(images):
                future = executor.submit(func, img, structure, **kwargs)
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    warnings.warn(f"Error processing image {idx}: {e}")
                    results[idx] = images[idx].copy()

        return results

    def process_batch_custom(
        self,
        images: List[np.ndarray],
        custom_func: Callable[[np.ndarray], np.ndarray]
    ) -> List[np.ndarray]:
        results = [None] * len(images)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for idx, img in enumerate(images):
                future = executor.submit(custom_func, img)
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    warnings.warn(f"Error processing image {idx}: {e}")
                    results[idx] = images[idx].copy()

        return results


def parallel_pipeline(
    image: np.ndarray,
    operations: List[Tuple[str, Union[np.ndarray, StructuringElement], dict]],
    max_workers: Optional[int] = None
) -> np.ndarray:
    result = image.copy()

    for op_name, structure, kwargs in operations:
        if max_workers and max_workers > 1:
            processor = BatchProcessor(max_workers=1)
            result = processor.process_batch([result], op_name, structure, **kwargs)[0]
        else:
            operation_funcs = {
                'erode': erode,
                'dilate': dilate,
                'open': open_op,
                'close': close_op,
                'top_hat': top_hat,
                'black_hat': black_hat,
                'gradient': morphological_gradient,
                'fill_holes': fill_holes,
                'boundary': extract_boundary,
                'remove_small': remove_small_objects
            }
            func = operation_funcs[op_name]
            result = func(result, structure, **kwargs)

    return result


class Pipeline:
    def __init__(self, operations: List[Tuple[str, Union[np.ndarray, StructuringElement], dict]] = None):
        self.operations = operations or []

    def add(self, operation: str, structure: Union[np.ndarray, StructuringElement], **kwargs):
        self.operations.append((operation, structure, kwargs))
        return self

    def apply(self, image: np.ndarray, parallel: bool = False, max_workers: Optional[int] = None) -> np.ndarray:
        if parallel:
            return parallel_pipeline(image, self.operations, max_workers)
        else:
            return parallel_pipeline(image, self.operations, max_workers=1)

    def apply_batch(self, images: List[np.ndarray], max_workers: Optional[int] = None) -> List[np.ndarray]:
        processor = BatchProcessor(max_workers=max_workers)
        func = partial(self.apply, parallel=False)
        return processor.process_batch_custom(images, func)


def split_image_for_parallel(
    image: np.ndarray,
    num_splits: int,
    overlap: int = 0
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    if len(image.shape) == 2:
        height, width = image.shape
    else:
        height, width, _ = image.shape

    tiles = []
    split_height = (height + num_splits - 1) // num_splits

    for i in range(num_splits):
        start_row = max(0, i * split_height - overlap)
        end_row = min(height, (i + 1) * split_height + overlap)

        tile = image[start_row:end_row, :]
        tiles.append((tile, (start_row, end_row, 0, width)))

    return tiles


def merge_tiles(
    tiles: List[Tuple[np.ndarray, Tuple[int, int, int, int]]],
    output_shape: Tuple[int, ...]
) -> np.ndarray:
    result = np.zeros(output_shape, dtype=np.uint8)

    for tile, (start_row, end_row, start_col, end_col) in tiles:
        result[start_row:end_row, start_col:end_col] = tile

    return result


def parallel_large_image(
    image: np.ndarray,
    operation: str,
    structure: Union[np.ndarray, StructuringElement],
    num_splits: int = 4,
    max_workers: Optional[int] = None
) -> np.ndarray:
    overlap = max(structure.shape) if isinstance(structure, StructuringElement) else max(structure.shape)

    tiles_info = split_image_for_parallel(image, num_splits, overlap=overlap)
    tiles = [tile for tile, _ in tiles_info]

    processor = BatchProcessor(max_workers=max_workers)
    processed_tiles = processor.process_batch(tiles, operation, structure)

    result_tiles = [(processed_tiles[i], tiles_info[i][1]) for i in range(len(tiles))]
    return merge_tiles(result_tiles, image.shape)
