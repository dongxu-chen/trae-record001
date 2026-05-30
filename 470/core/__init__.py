from .post_processing import (
    postprocess_saliency_map,
    refine_edges,
    segment_salient_object,
    apply_mask,
    overlay_saliency
)
from .guided_filter import (
    guided_filter,
    guided_filter_color,
    fast_guided_filter,
    guided_filter_refine,
    guided_edge_refinement,
    GuidedFilterRefiner
)
from .dynamic_batch import (
    GPUMemoryMonitor,
    DynamicBatchProcessor,
    MemoryInfo,
    BatchConfig,
    ProcessingStats,
    process_with_dynamic_batch,
    check_oom_safe
)

__all__ = [
    'SaliencyInferencer',
    'postprocess_saliency_map',
    'refine_edges',
    'segment_salient_object',
    'apply_mask',
    'overlay_saliency',
    'BatchProcessor',
    'guided_filter',
    'guided_filter_color',
    'fast_guided_filter',
    'guided_filter_refine',
    'guided_edge_refinement',
    'GuidedFilterRefiner',
    'GPUMemoryMonitor',
    'DynamicBatchProcessor',
    'MemoryInfo',
    'BatchConfig',
    'ProcessingStats',
    'process_with_dynamic_batch',
    'check_oom_safe',
    'FrameSmoother',
    'VideoSaliencyDetector',
    'FrameResult',
    'VideoResult',
    'smooth_saliency_sequence',
    'ImageEditor',
    'SaliencyInpainter',
    'fill_salient_region',
    'blur_salient_region',
    'replace_salient_region',
    'adjust_salient_region',
    'AttentionHeatmap',
    'ModelExplainer',
    'generate_attention_heatmap',
    'visualize_feature_maps',
    'generate_gradcam',
    'explain_prediction'
]

def __getattr__(name):
    if name == 'SaliencyInferencer':
        from .inferencer import SaliencyInferencer
        return SaliencyInferencer
    elif name == 'BatchProcessor':
        from .batch_processor import BatchProcessor
        return BatchProcessor
    elif name in ['FrameSmoother', 'VideoSaliencyDetector', 'FrameResult', 'VideoResult', 'smooth_saliency_sequence']:
        from .video_saliency import (
            FrameSmoother, VideoSaliencyDetector, FrameResult, VideoResult,
            smooth_saliency_sequence
        )
        return locals()[name]
    elif name in ['ImageEditor', 'SaliencyInpainter', 'FillMethod', 'BlendMode',
                  'fill_salient_region', 'blur_salient_region',
                  'replace_salient_region', 'adjust_salient_region']:
        from .image_editor import (
            ImageEditor, SaliencyInpainter, FillMethod, BlendMode,
            fill_salient_region, blur_salient_region,
            replace_salient_region, adjust_salient_region
        )
        return locals()[name]
    elif name in ['AttentionHeatmap', 'ModelExplainer', 'generate_attention_heatmap',
                  'visualize_feature_maps', 'generate_gradcam', 'explain_prediction']:
        from .attention_heatmap import (
            AttentionHeatmap, ModelExplainer, generate_attention_heatmap,
            visualize_feature_maps, generate_gradcam, explain_prediction
        )
        return locals()[name]
    raise AttributeError(f"module 'core' has no attribute '{name}'")
