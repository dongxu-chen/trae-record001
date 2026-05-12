"""
统一的计算后端选择器
支持 CuPy (GPU) 和 NumPy (CPU) 自动切换
"""

import contextlib

_CUPY_AVAILABLE = False
_NUMPY_AVAILABLE = True
_MPI4PY_AVAILABLE = False

_backend = None
_device = 'cpu'

try:
    import numpy as _np
    _NUMPY_AVAILABLE = True
except ImportError:
    pass

try:
    import cupy as _cp
    if _cp.cuda.is_available():
        _CUPY_AVAILABLE = True
except ImportError:
    pass

try:
    from mpi4py import MPI
    _MPI4PY_AVAILABLE = True
except ImportError:
    pass


def set_backend(backend_name='auto'):
    """
    设置计算后端

    参数:
    - backend_name: 'auto', 'cupy', 'numpy'
    """
    global _backend, _device

    if backend_name == 'auto':
        if _CUPY_AVAILABLE:
            backend_name = 'cupy'
        else:
            backend_name = 'numpy'

    if backend_name == 'cupy' and _CUPY_AVAILABLE:
        _backend = _cp
        _device = 'gpu'
    elif backend_name == 'numpy' and _NUMPY_AVAILABLE:
        _backend = _np
        _device = 'cpu'
    else:
        _backend = _np
        _device = 'cpu'


def get_backend():
    """获取当前计算后端"""
    global _backend
    if _backend is None:
        set_backend('auto')
    return _backend


def get_device():
    """获取当前设备"""
    return _device


def is_gpu_available():
    """检查 GPU 是否可用"""
    return _CUPY_AVAILABLE


def is_mpi_available():
    """检查 MPI 是否可用"""
    return _MPI4PY_AVAILABLE


def is_cupy_available():
    return _CUPY_AVAILABLE


def array(data, dtype=None):
    """创建数组（自动选择后端）"""
    xp = get_backend()
    if _device == 'gpu':
        if hasattr(data, '__array__'):
            return xp.asarray(data, dtype=dtype)
        return xp.array(data, dtype=dtype)
    return xp.array(data, dtype=dtype)


def to_numpy(arr):
    """将数组转换为 NumPy 数组"""
    if _CUPY_AVAILABLE and hasattr(arr, 'get'):
        return arr.get()
    return arr


def to_gpu(arr):
    """将数组传输到 GPU（如果可用）"""
    if _CUPY_AVAILABLE and _device == 'gpu':
        if hasattr(arr, 'get'):
            return arr
        return _cp.asarray(arr)
    return arr


def synchronize():
    """同步 GPU 操作（如果使用 GPU）"""
    if _CUPY_AVAILABLE and _device == 'gpu':
        _cp.cuda.Stream.null.synchronize()


def get_mpi_comm():
    """获取 MPI 通信器"""
    if _MPI4PY_AVAILABLE:
        return MPI.COMM_WORLD
    return None


def get_mpi_rank():
    """获取当前进程的 MPI rank"""
    if _MPI4PY_AVAILABLE:
        return MPI.COMM_WORLD.Get_rank()
    return 0


def get_mpi_size():
    """获取 MPI 进程总数"""
    if _MPI4PY_AVAILABLE:
        return MPI.COMM_WORLD.Get_size()
    return 1


def is_mpi_root():
    """检查是否是 MPI 根进程"""
    return get_mpi_rank() == 0


np = get_backend()


class VectorizedOperation:
    """
    向量化操作基类，支持多列和多波段计算
    """

    def __init__(self, n_columns=1, n_bands=1):
        self.n_columns = n_columns
        self.n_bands = n_bands
        self.xp = get_backend()

    def expand_dims(self, arr, target_ndim=3):
        """
        扩展数组维度以匹配目标维度
        目标形状: (n_columns, n_bands, n_levels) 或类似
        """
        arr = self.xp.asarray(arr)
        ndim = arr.ndim

        if ndim == 1:
            arr = arr[self.xp.newaxis, self.xp.newaxis, :]
            arr = self.xp.broadcast_to(arr, (self.n_columns, self.n_bands, arr.shape[-1]))
        elif ndim == 2:
            if arr.shape[0] == self.n_columns:
                arr = arr[:, self.xp.newaxis, :]
                arr = self.xp.broadcast_to(arr, (self.n_columns, self.n_bands, arr.shape[-1]))
            elif arr.shape[0] == self.n_bands:
                arr = arr[self.xp.newaxis, :, :]
                arr = self.xp.broadcast_to(arr, (self.n_columns, self.n_bands, arr.shape[-1]))
        elif ndim == 3:
            pass

        return arr

    def reduce_mean(self, arr, axis=None):
        """求均值"""
        return self.xp.mean(arr, axis=axis)

    def reduce_sum(self, arr, axis=None):
        """求和"""
        return self.xp.sum(arr, axis=axis)

    def batch_operation(self, operation, inputs):
        """
        对批量数据执行向量化操作

        参数:
        - operation: 操作函数
        - inputs: 输入参数字典

        返回:
        - 操作结果
        """
        xp = self.xp

        for key, val in inputs.items():
            inputs[key] = self.expand_dims(xp.asarray(val))

        result = operation(**inputs)

        return result


set_backend('auto')
