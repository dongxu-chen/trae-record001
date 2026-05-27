import numpy as np
from typing import Tuple


class StructuringElement:
    def __init__(self, kernel: np.ndarray, anchor: Tuple[int, int] = None):
        self.kernel = kernel.astype(np.uint8)
        if anchor is None:
            self.anchor = (kernel.shape[0] // 2, kernel.shape[1] // 2)
        else:
            self.anchor = anchor

    @property
    def shape(self) -> Tuple[int, int]:
        return self.kernel.shape

    @property
    def size(self) -> int:
        return self.kernel.size

    def __array__(self) -> np.ndarray:
        return self.kernel


def create_rect(ksize: Tuple[int, int]) -> StructuringElement:
    kernel = np.ones(ksize, dtype=np.uint8)
    return StructuringElement(kernel)


def create_ellipse(ksize: Tuple[int, int]) -> StructuringElement:
    rows, cols = ksize
    kernel = np.zeros((rows, cols), dtype=np.uint8)
    center_r, center_c = rows // 2, cols // 2
    a, b = center_r + 1, center_c + 1

    for r in range(rows):
        for c in range(cols):
            if ((r - center_r) ** 2) / (a ** 2) + ((c - center_c) ** 2) / (b ** 2) <= 1:
                kernel[r, c] = 1

    return StructuringElement(kernel)


def create_cross(ksize: Tuple[int, int]) -> StructuringElement:
    rows, cols = ksize
    kernel = np.zeros((rows, cols), dtype=np.uint8)
    center_r, center_c = rows // 2, cols // 2

    kernel[center_r, :] = 1
    kernel[:, center_c] = 1

    return StructuringElement(kernel)
