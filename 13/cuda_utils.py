try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    import numpy as cp

import numpy as np


def is_gpu_available():
    return CUPY_AVAILABLE


def get_array_module(arr):
    if CUPY_AVAILABLE and isinstance(arr, cp.ndarray):
        return cp
    return np


def to_gpu(arr):
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy 未安装，无法使用 GPU")
    if isinstance(arr, cp.ndarray):
        return arr
    return cp.asarray(arr)


def to_cpu(arr):
    if not CUPY_AVAILABLE:
        return arr
    if isinstance(arr, cp.ndarray):
        return arr.get()
    return arr


def synchronize():
    if CUPY_AVAILABLE:
        cp.cuda.stream.get_current_stream().synchronize()


class DeviceArray:
    def __init__(self, data=None, shape=None, dtype=np.float64):
        if data is not None:
            if CUPY_AVAILABLE:
                self._arr = cp.asarray(data)
            else:
                self._arr = np.asarray(data, dtype=dtype)
        elif shape is not None:
            if CUPY_AVAILABLE:
                self._arr = cp.zeros(shape, dtype=dtype)
            else:
                self._arr = np.zeros(shape, dtype=dtype)
        else:
            self._arr = None

    @property
    def array(self):
        return self._arr

    def to_cpu(self):
        if self._arr is None:
            return None
        return to_cpu(self._arr)

    def copy(self):
        new_obj = DeviceArray.__new__(DeviceArray)
        if self._arr is not None:
            new_obj._arr = self._arr.copy()
        else:
            new_obj._arr = None
        return new_obj

    @property
    def shape(self):
        return self._arr.shape if self._arr is not None else None

    @property
    def dtype(self):
        return self._arr.dtype if self._arr is not None else None
