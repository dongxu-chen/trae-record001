import numpy as np
from typing import Union, Tuple, Callable, Optional
from .structuring_element import StructuringElement
from .core import erode, dilate, open_op, close_op, top_hat, black_hat, morphological_gradient


def process_large_image(
    image: np.ndarray,
    structure: Union[np.ndarray, StructuringElement],
    operation: str,
    block_size: Tuple[int, int] = (1024, 1024),
    progress_callback: Callable[[float], None] = None,
    out: Optional[np.ndarray] = None
) -> np.ndarray:
    if isinstance(structure, StructuringElement):
        kernel = structure.kernel
        anchor = structure.anchor
    else:
        kernel = np.asarray(structure, dtype=np.uint8)
        anchor = (kernel.shape[0] // 2, kernel.shape[1] // 2)

    overlap_rows = kernel.shape[0] - 1
    overlap_cols = kernel.shape[1] - 1

    if len(image.shape) == 2:
        rows, cols = image.shape
    else:
        rows, cols, _ = image.shape

    if out is None:
        out = np.empty_like(image)
    elif out.shape != image.shape or out.dtype != image.dtype:
        raise ValueError(f"out must have same shape and dtype as image. Got {out.shape} and {out.dtype}, expected {image.shape} and {image.dtype}")

    block_rows, block_cols = block_size
    num_blocks_vert = (rows + block_rows - 1) // block_rows
    num_blocks_horiz = (cols + block_cols - 1) // block_cols
    total_blocks = num_blocks_vert * num_blocks_horiz
    current_block = 0

    operations = {
        'erode': (erode, False),
        'dilate': (dilate, False),
        'open': (open_op, True),
        'close': (close_op, True),
        'top_hat': (top_hat, True),
        'black_hat': (black_hat, True),
        'gradient': (morphological_gradient, True)
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}. Available: {list(operations.keys())}")

    op_func, needs_temp = operations[operation]
    temp_buffer = None

    for i in range(num_blocks_vert):
        for j in range(num_blocks_horiz):
            start_row = i * block_rows
            end_row = min((i + 1) * block_rows + overlap_rows, rows)
            start_col = j * block_cols
            end_col = min((j + 1) * block_cols + overlap_cols, cols)

            block_view = image[start_row:end_row, start_col:end_col]

            result_start_row = start_row
            result_end_row = min(start_row + block_rows, rows)
            result_start_col = start_col
            result_end_col = min(start_col + block_cols, cols)

            out_view = out[result_start_row:result_end_row, result_start_col:result_end_col]

            actual_block_rows = result_end_row - result_start_row
            actual_block_cols = result_end_col - result_start_col

            if needs_temp:
                if temp_buffer is None or temp_buffer.shape != block_view.shape:
                    temp_buffer = np.empty_like(block_view)
                temp2 = temp_buffer[:actual_block_rows, :actual_block_cols] if operation == 'gradient' else None
                op_func(block_view, kernel, out=out_view, temp=temp_buffer)
            else:
                op_func(block_view, kernel, out=out_view)

            current_block += 1
            if progress_callback is not None:
                progress_callback(current_block / total_blocks)

    return out


class LargeImageProcessor:
    def __init__(self, block_size: Tuple[int, int] = (1024, 1024)):
        self.block_size = block_size
        self.progress = 0.0
        self._temp_buffer = None

    def _update_progress(self, value: float):
        self.progress = value

    def _get_buffer(self, shape: Tuple, dtype: np.dtype) -> np.ndarray:
        if self._temp_buffer is None or self._temp_buffer.shape != shape or self._temp_buffer.dtype != dtype:
            self._temp_buffer = np.empty(shape, dtype=dtype)
        return self._temp_buffer

    def erode(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'erode', self.block_size, self._update_progress, out=out)

    def dilate(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'dilate', self.block_size, self._update_progress, out=out)

    def open_op(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'open', self.block_size, self._update_progress, out=out)

    def close_op(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'close', self.block_size, self._update_progress, out=out)

    def top_hat(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'top_hat', self.block_size, self._update_progress, out=out)

    def black_hat(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'black_hat', self.block_size, self._update_progress, out=out)

    def morphological_gradient(self, image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: Optional[np.ndarray] = None) -> np.ndarray:
        self.progress = 0.0
        return process_large_image(image, structure, 'gradient', self.block_size, self._update_progress, out=out)

    def get_progress(self) -> float:
        return self.progress

    def clear_buffers(self):
        self._temp_buffer = None
