from dataclasses import dataclass, field
from typing import Tuple, Optional, List


@dataclass
class CameraCalibrationConfig:
    fx: float = 525.0
    fy: float = 525.0
    cx: Optional[float] = None
    cy: Optional[float] = None
    image_width: int = 640
    image_height: int = 480
    distortion_coeffs: Optional[List[float]] = None
    depth_scale: float = 1.0
    min_metric_depth: float = 0.1
    max_metric_depth: float = 10.0
    calibration_file: Optional[str] = None
    apply_undistortion: bool = True


@dataclass
class AlignmentConfig:
    apply_alignment: bool = True
    rgb_offset_x: int = 0
    rgb_offset_y: int = 0
    scale_depth_to_rgb: bool = True
    interpolation: int = 1
    generate_aligned_output: bool = True
    colormap: int = 2
    alpha_blend: float = 0.5
    edge_threshold: float = 0.1


@dataclass
class ARConfig:
    enabled: bool = True
    object_scale: float = 1.0
    object_color: Tuple[int, int, int] = (0, 255, 0)
    object_alpha: float = 0.7
    occlusion_threshold: float = 0.05
    shadow_enabled: bool = True
    shadow_alpha: float = 0.3
    wireframe: bool = False
    place_on_surface: bool = True
    surface_offset: float = 0.0
    min_depth_for_placement: float = 0.1
    max_depth_for_placement: float = 10.0
    object_type: str = 'cube'


@dataclass
class ModelConfig:
    model_type: str = "DPT_Large"
    model_path: Optional[str] = None
    onnx_path: Optional[str] = None
    use_onnx: bool = False
    device: str = "cuda"
    precision: str = "fp32"


@dataclass
class PostProcessingConfig:
    apply_bilateral_filter: bool = True
    bilateral_d: int = 9
    bilateral_sigma_color: float = 75.0
    bilateral_sigma_space: float = 75.0
    apply_median_filter: bool = False
    median_kernel_size: int = 5
    apply_gaussian_filter: bool = False
    gaussian_kernel_size: int = 5
    gaussian_sigma: float = 0.0
    apply_edge_guided_filter: bool = True
    edge_guided_r: int = 7
    edge_guided_eps: float = 0.01
    edge_guided_edge_weight: float = 0.7
    fill_holes: bool = True
    hole_fill_kernel: int = 3
    normalize: bool = True
    min_depth: float = 0.1
    max_depth: float = 10.0


@dataclass
class TemporalSmoothingConfig:
    apply_temporal_smoothing: bool = True
    alpha: float = 0.3
    edge_threshold: float = 0.5
    max_history: int = 5
    motion_compensation: bool = True
    motion_threshold: float = 5.0
    adaptive_alpha: bool = True


@dataclass
class TemporalHoleFillingConfig:
    apply_temporal_hole_filling: bool = True
    num_frames: int = 3
    min_valid_frames: int = 2
    max_depth_diff: float = 0.5
    use_warping: bool = True
    fallback_to_spatial: bool = True


@dataclass
class VideoConfig:
    source: str = "0"
    output_path: Optional[str] = None
    show_fps: bool = True
    target_fps: int = 30
    target_size: Tuple[int, int] = (640, 480)
    display_depth: bool = True
    colormap: int = 2
    save_video: bool = False
    temporal_smoothing: TemporalSmoothingConfig = field(default_factory=TemporalSmoothingConfig)
    temporal_hole_filling: TemporalHoleFillingConfig = field(default_factory=TemporalHoleFillingConfig)


@dataclass
class PointCloudConfig:
    fx: float = 525.0
    fy: float = 525.0
    cx: Optional[float] = None
    cy: Optional[float] = None
    depth_scale: float = 1000.0
    min_depth: float = 0.1
    max_depth: float = 10.0
    downsample: bool = True
    downsample_voxel_size: float = 0.01
    remove_outliers: bool = True
    nb_neighbors: int = 20
    std_ratio: float = 2.0
    save_path: Optional[str] = None
    show: bool = True


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    post_processing: PostProcessingConfig = field(default_factory=PostProcessingConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    point_cloud: PointCloudConfig = field(default_factory=PointCloudConfig)
    camera_calibration: CameraCalibrationConfig = field(default_factory=CameraCalibrationConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    ar: ARConfig = field(default_factory=ARConfig)
