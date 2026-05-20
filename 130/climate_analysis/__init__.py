from .data_reader import ClimateDataReader, optimal_chunks
from .eof_analysis import EOFAnalysis
from .trend_analysis import TrendAnalysis
from .visualization import ClimateVisualizer
from .interpolation import GridInterpolator, RegularGridInterpolator
from .mjo import MJOIndex
from .seasonal_prediction import CESMReader, SeasonalPredictor, HybridForecast
from .xai import SHAPExplainer, FeatureAttribution, PermutationImportance
from .cmip6 import CMIP6Search, CMIP6Downloader, CMIP6BiasCorrection, CMIP6Ensemble
from .cloud import (
    CloudDataStore,
    CMIP6Catalog,
    DaskGatewayCluster,
    create_s3_store,
    list_pangeo_datasets,
    create_kerchunk_index
)

__version__ = "0.3.0"

__all__ = [
    "ClimateDataReader",
    "optimal_chunks",
    "EOFAnalysis",
    "TrendAnalysis",
    "ClimateVisualizer",
    "GridInterpolator",
    "RegularGridInterpolator",
    "MJOIndex",
    "CESMReader",
    "SeasonalPredictor",
    "HybridForecast",
    "SHAPExplainer",
    "FeatureAttribution",
    "PermutationImportance",
    "CMIP6Search",
    "CMIP6Downloader",
    "CMIP6BiasCorrection",
    "CMIP6Ensemble",
    "CloudDataStore",
    "CMIP6Catalog",
    "DaskGatewayCluster",
    "create_s3_store",
    "list_pangeo_datasets",
    "create_kerchunk_index",
]
