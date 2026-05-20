import importlib.util

_core_available = importlib.util.find_spec(".ms_peak_detector_core", package=__name__) is not None

if _core_available:
    try:
        from .ms_peak_detector_core import (
            Peak,
            BaselineCorrector as BaselineCorrectorFast,
            PeakDetector as PeakDetectorFast,
            ParallelProcessor,
        )
        _core_available = True
    except ImportError:
        _core_available = False

if not _core_available:
    from .baseline_correction import BaselineCorrector
    from .peak_detection import PeakDetector
    ParallelProcessor = None
    Peak = None
else:
    from .baseline_correction import BaselineCorrector as BaselineCorrectorPy
    from .peak_detection import PeakDetector as PeakDetectorPy

from .peak_alignment import PeakAligner, SpectrumAligner
from .isotope_detection import IsotopeDetector
from .core import MSPeakProcessor
from .processor import MSPeakAnalysisPipeline
from .spectral_library import SpectralLibrary, SpectralMatcher, create_example_library
from .ptm_identification import PTMDatabase, PeptideFragmenter, PTMIdentifier
from .quantitation import ReporterIonQuantitation, PeptideQuantitation, ProteinQuantitation, RatioCalculation, QuantitationPipeline
from .file_io import MzMLWriter, MzTabWriter, SimpleFileWriter, ResultExporter

def get_baseline_corrector(use_fast=True):
    if use_fast and _core_available:
        return BaselineCorrectorFast
    return BaselineCorrector

def get_peak_detector(use_fast=True):
    if use_fast and _core_available:
        return PeakDetectorFast
    return PeakDetector

__version__ = "0.2.0"
__core_available__ = _core_available
__all__ = [
    "BaselineCorrector",
    "PeakDetector",
    "PeakAligner",
    "SpectrumAligner",
    "IsotopeDetector",
    "MSPeakProcessor",
    "MSPeakAnalysisPipeline",
    "SpectralLibrary",
    "SpectralMatcher",
    "create_example_library",
    "PTMDatabase",
    "PeptideFragmenter",
    "PTMIdentifier",
    "ReporterIonQuantitation",
    "PeptideQuantitation",
    "ProteinQuantitation",
    "RatioCalculation",
    "QuantitationPipeline",
    "MzMLWriter",
    "MzTabWriter",
    "SimpleFileWriter",
    "ResultExporter",
    "ParallelProcessor",
    "Peak",
    "get_baseline_corrector",
    "get_peak_detector",
    "__core_available__",
]
