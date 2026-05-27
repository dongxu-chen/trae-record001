from .visualization import flow_to_hsv, visualize_flow
from .metrics import compute_epe, compute_aee
from .algorithms import LucasKanade, Farneback
from .algorithms import _RAFT as _raft_module
from .dense_interpolation import DenseInterpolator, SparseToDense
from .motion_segmentation import MotionSegmentation, MotionAnalyzer
from .scene_flow import SceneFlowEstimator, DepthFlowFusion

_HAS_RAFT = _raft_module is not None
if _HAS_RAFT:
    RAFT = _raft_module
else:
    RAFT = None

__all__ = [
    'LucasKanade',
    'Farneback',
    'RAFT',
    'flow_to_hsv',
    'visualize_flow',
    'compute_epe',
    'compute_aee',
    'DenseInterpolator',
    'SparseToDense',
    'MotionSegmentation',
    'MotionAnalyzer',
    'SceneFlowEstimator',
    'DepthFlowFusion',
]