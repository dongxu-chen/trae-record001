"""
MRI Simulator - 磁共振成像模拟器
基于Bloch方程的完整MRI模拟，支持GPU加速
"""

from .phantom import Phantom, generate_shepp_logan
from .bloch import BlochSolver, BlochSolverGPU
from .sequences import SpinEcho, GradientEcho, InversionRecovery
from .kspace import KSpace
from .reconstruction import Reconstructor
from .visualization import MRIViewer

__version__ = "1.0.0"
__all__ = [
    "Phantom",
    "generate_shepp_logan",
    "BlochSolver",
    "BlochSolverGPU",
    "SpinEcho",
    "GradientEcho",
    "InversionRecovery",
    "KSpace",
    "Reconstructor",
    "MRIViewer",
]
