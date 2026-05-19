from .trajectory_reader import TrajectoryReader
from .rmsd_calculator import RMSDCalculator
from .rg_calculator import RgCalculator
from .report_generator import ReportGenerator
from .hbond_analyzer import HydrogenBondAnalyzer
from .xtc_parser import XTCParser, PrecisionConverter, StreamingAnalyzer
from .pca_analyzer import PCAAnalyzer, FreeEnergySurface, compute_rmsf, compute_correlation_matrix

try:
    from .dask_analysis import (
        MemoryMappedTrajectory,
        DistributedAnalyzer,
        DaskPCA,
        estimate_memory_usage,
        create_dask_cluster_info
    )
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

__version__ = "0.4.0"
__all__ = [
    "TrajectoryReader", "RMSDCalculator", "RgCalculator", 
    "ReportGenerator", "HydrogenBondAnalyzer", "XTCParser", 
    "PrecisionConverter", "StreamingAnalyzer", "PCAAnalyzer",
    "FreeEnergySurface", "compute_rmsf", "compute_correlation_matrix"
]

if DASK_AVAILABLE:
    __all__.extend([
        "MemoryMappedTrajectory",
        "DistributedAnalyzer",
        "DaskPCA",
        "estimate_memory_usage",
        "create_dask_cluster_info"
    ])

