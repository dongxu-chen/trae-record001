from .base import LinearAlgebraBackend, Array
from .numpy_backend import NumPyBackend
from .cupy_backend import CuPyBackend


_backends = {}
_default_backend = None


def get_backend(name: str = None) -> LinearAlgebraBackend:
    """获取指定后端，如果未指定则返回默认后端"""
    global _backends, _default_backend

    if name is None:
        if _default_backend is None:
            _init_backends()
        return _default_backend

    if name not in _backends:
        _init_backends()

    if name in _backends:
        return _backends[name]
    else:
        raise ValueError(f"未知后端: {name}. 可用后端: {list_available_backends()}")


def _init_backends():
    """初始化所有可用后端"""
    global _backends, _default_backend

    numpy_backend = NumPyBackend()
    _backends['numpy'] = numpy_backend
    _backends['numpy-cpu'] = numpy_backend

    cupy_backend = CuPyBackend()
    if cupy_backend.available:
        _backends['cupy'] = cupy_backend
        _backends['cupy-cuda'] = cupy_backend
        _default_backend = cupy_backend
    else:
        _default_backend = numpy_backend


def list_available_backends() -> list:
    """列出所有可用后端"""
    if not _backends:
        _init_backends()
    return list(_backends.keys())


def set_default_backend(name: str):
    """设置默认后端"""
    global _default_backend
    backend = get_backend(name)
    _default_backend = backend


def auto_select_backend(array=None) -> LinearAlgebraBackend:
    """根据输入数组类型和可用硬件自动选择后端

    Args:
        array: 输入数组，如果提供则根据数组类型选择
    """
    if array is not None:
        if hasattr(array, '__module__'):
            if 'cupy' in array.__module__:
                return get_backend('cupy')

    if not _backends:
        _init_backends()

    if 'cupy' in _backends:
        return _backends['cupy']
    return _backends['numpy']


__all__ = [
    'LinearAlgebraBackend',
    'Array',
    'NumPyBackend',
    'CuPyBackend',
    'get_backend',
    'list_available_backends',
    'set_default_backend',
    'auto_select_backend',
]
