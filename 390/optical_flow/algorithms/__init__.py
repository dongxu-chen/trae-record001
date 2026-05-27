from .lucas_kanade import LucasKanade
from .farneback import Farneback

_RAFT = None
try:
    from .raft import RAFT as _RAFT
except ImportError:
    pass


def __getattr__(name):
    if name == 'RAFT':
        if _RAFT is not None:
            return _RAFT
        raise ImportError(
            'RAFT 算法需要 PyTorch, 请安装: pip install torch torchvision'
        )
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


__all__ = ['LucasKanade', 'Farneback', 'RAFT']