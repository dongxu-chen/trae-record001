from .models.unet import UNet
from .models.deeplabv3plus import DeepLabV3Plus
from .models.attention import SpatialAttention, ChannelAttention, CBAM, BoundaryAttention, AttentionGate, SCSEModule
from .models.temporal_models import ConvLSTMCell, ConvLSTM, TemporalEncoder, TemporalChangeDetection, SiameseLSTM
from .utils.difference import DifferenceCalculator
from .utils.segmentation import ChangeSegmenter
from .utils.metrics import Evaluator, PerClassEvaluator, compute_confusion_matrix, compute_class_metrics
from .utils.trainer import MixedPrecisionTrainer, DiceLoss, FocalLoss, CombinedLoss
from .utils.visualization import AttentionVisualizer
from .utils.active_learning import (
    QueryStrategy,
    EntropySampling,
    MarginSampling,
    LeastConfidence,
    VariationRatio,
    BALDDropout,
    PseudoLabeler,
    ActiveLearningManager
)
from .utils.geo_export import (
    GeoJSONExporter,
    ChangeStatistics,
    MultiTemporalChangeAnalyzer,
    visualize_change_regions
)
from .data.dataloader import ChangeDetectionDataset, MaskedNormalize, ImagePairLoader, get_transforms

__version__ = '0.3.0'
__all__ = [
    'UNet',
    'DeepLabV3Plus',
    'SpatialAttention',
    'ChannelAttention',
    'CBAM',
    'BoundaryAttention',
    'AttentionGate',
    'SCSEModule',
    'ConvLSTMCell',
    'ConvLSTM',
    'TemporalEncoder',
    'TemporalChangeDetection',
    'SiameseLSTM',
    'DifferenceCalculator',
    'ChangeSegmenter',
    'Evaluator',
    'PerClassEvaluator',
    'compute_confusion_matrix',
    'compute_class_metrics',
    'MixedPrecisionTrainer',
    'DiceLoss',
    'FocalLoss',
    'CombinedLoss',
    'AttentionVisualizer',
    'QueryStrategy',
    'EntropySampling',
    'MarginSampling',
    'LeastConfidence',
    'VariationRatio',
    'BALDDropout',
    'PseudoLabeler',
    'ActiveLearningManager',
    'GeoJSONExporter',
    'ChangeStatistics',
    'MultiTemporalChangeAnalyzer',
    'visualize_change_regions',
    'ChangeDetectionDataset',
    'MaskedNormalize',
    'ImagePairLoader',
    'get_transforms'
]
