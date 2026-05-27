import numpy as np
from typing import Union, Tuple
from .structuring_element import StructuringElement


def _get_kernel(structure: Union[np.ndarray, StructuringElement]) -> Tuple[np.ndarray, Tuple[int, int]]:
    if isinstance(structure, StructuringElement):
        return structure.kernel, structure.anchor
    else:
        kernel = np.asarray(structure, dtype=np.uint8)
        anchor = (kernel.shape[0] // 2, kernel.shape[1] // 2)
        return kernel, anchor


def _pad_image(image: np.ndarray, kernel_shape: Tuple[int, int], anchor: Tuple[int, int]) -> np.ndarray:
    pad_top = anchor[0]
    pad_bottom = kernel_shape[0] - anchor[0] - 1
    pad_left = anchor[1]
    pad_right = kernel_shape[1] - anchor[1] - 1

    if len(image.shape) == 2:
        return np.pad(image, ((pad_top, pad_bottom), (pad_left, pad_right)), mode='reflect')
    else:
        return np.pad(image, ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)), mode='reflect')


def _get_sliding_window_view(arr: np.ndarray, window_shape: Tuple[int, int]) -> np.ndarray:
    if len(arr.shape) == 2:
        rows, cols = arr.shape
        k_rows, k_cols = window_shape
        new_shape = (rows - k_rows + 1, cols - k_cols + 1, k_rows, k_cols)
        new_strides = (arr.strides[0], arr.strides[1], arr.strides[0], arr.strides[1])
        return np.lib.stride_tricks.as_strided(arr, shape=new_shape, strides=new_strides)
    else:
        rows, cols, channels = arr.shape
        k_rows, k_cols = window_shape
        new_shape = (rows - k_rows + 1, cols - k_cols + 1, channels, k_rows, k_cols)
        new_strides = (arr.strides[0], arr.strides[1], arr.strides[2], arr.strides[0], arr.strides[1])
        return np.lib.stride_tricks.as_strided(arr, shape=new_shape, strides=new_strides)


def erode(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None) -> np.ndarray:
    kernel, anchor = _get_kernel(structure)
    k_rows, k_cols = kernel.shape

    if k_rows == 1 and k_cols == 1:
        if out is not None:
            out[:] = image
            return out
        return image.copy()

    padded = _pad_image(image, (k_rows, k_cols), anchor)
    kernel_positions = np.where(kernel == 1)

    if out is None:
        out = np.empty_like(image)

    if len(image.shape) == 2:
        windows = _get_sliding_window_view(padded, (k_rows, k_cols))
        out[:] = np.min(windows[:, :, kernel_positions[0], kernel_positions[1]], axis=-1)
    else:
        windows = _get_sliding_window_view(padded, (k_rows, k_cols))
        out[:] = np.min(windows[:, :, :, kernel_positions[0], kernel_positions[1]], axis=-1)

    return out


def dilate(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None) -> np.ndarray:
    kernel, anchor = _get_kernel(structure)
    k_rows, k_cols = kernel.shape

    if k_rows == 1 and k_cols == 1:
        if out is not None:
            out[:] = image
            return out
        return image.copy()

    padded = _pad_image(image, (k_rows, k_cols), anchor)
    kernel_positions = np.where(kernel == 1)

    if out is None:
        out = np.empty_like(image)

    if len(image.shape) == 2:
        windows = _get_sliding_window_view(padded, (k_rows, k_cols))
        out[:] = np.max(windows[:, :, kernel_positions[0], kernel_positions[1]], axis=-1)
    else:
        windows = _get_sliding_window_view(padded, (k_rows, k_cols))
        out[:] = np.max(windows[:, :, :, kernel_positions[0], kernel_positions[1]], axis=-1)

    return out


def open_op(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None, temp: np.ndarray = None) -> np.ndarray:
    if temp is None:
        temp = np.empty_like(image)
    erode(image, structure, out=temp)
    return dilate(temp, structure, out=out)


def close_op(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None, temp: np.ndarray = None) -> np.ndarray:
    if temp is None:
        temp = np.empty_like(image)
    dilate(image, structure, out=temp)
    return erode(temp, structure, out=out)


def top_hat(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None, temp: np.ndarray = None) -> np.ndarray:
    if temp is None:
        temp = np.empty_like(image)
    opened = open_op(image, structure, out=temp)
    if out is None:
        out = np.empty_like(image)
    np.clip(image.astype(np.int32) - opened.astype(np.int32), 0, 255, out=out.astype(np.int32))
    return out.astype(np.uint8)


def black_hat(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None, temp: np.ndarray = None) -> np.ndarray:
    if temp is None:
        temp = np.empty_like(image)
    closed = close_op(image, structure, out=temp)
    if out is None:
        out = np.empty_like(image)
    np.clip(closed.astype(np.int32) - image.astype(np.int32), 0, 255, out=out.astype(np.int32))
    return out.astype(np.uint8)


def morphological_gradient(image: np.ndarray, structure: Union[np.ndarray, StructuringElement], out: np.ndarray = None, temp1: np.ndarray = None, temp2: np.ndarray = None) -> np.ndarray:
    if temp1 is None:
        temp1 = np.empty_like(image)
    if temp2 is None:
        temp2 = np.empty_like(image)
    dilated = dilate(image, structure, out=temp1)
    eroded = erode(image, structure, out=temp2)
    if out is None:
        out = np.empty_like(image)
    np.clip(dilated.astype(np.int32) - eroded.astype(np.int32), 0, 255, out=out.astype(np.int32))
    return out.astype(np.uint8)
