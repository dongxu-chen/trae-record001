import torch
from dataclasses import dataclass, field
from typing import Tuple, Optional, List


@dataclass
class InpaintingConfig:
    patch_size: int = 9
    alpha_threshold: float = 0.3
    max_iterations: int = 5000
    confidence_threshold: float = 0.01
    poisson_blending: bool = True
    use_telea: bool = True
    telea_radius: int = 5


@dataclass
class PolarizationConfig:
    estimate_from_image: bool = True
    use_traditional_method: bool = True
    polarization_model_path: Optional[str] = None
    dolp_threshold: float = 0.3
    fusion_weight: float = 0.3


@dataclass
class MOSConfig:
    enable_mos: bool = True
    subjective_weight: float = 0.6
    save_mos_report: bool = True
    mos_report_dir: str = "output/mos_analysis"


@dataclass
class VideoConfig:
    temporal_window: int = 5
    flow_method: str = 'farneback'
    consistency_weight: float = 0.4
    blend_factor: float = 0.3
    max_flow: float = 50.0
    gpu_acceleration: bool = False


@dataclass
class DetectionConfig:
    confidence_threshold: float = 0.5
    specular_threshold: float = 0.85
    edge_weight: float = 0.3
    color_weight: float = 0.3
    gradient_weight: float = 0.2
    structural_weight: float = 0.2
    min_reflection_area: float = 0.01
    use_deep_detector: bool = False
    deep_model_path: Optional[str] = None


@dataclass
class MultiTaskConfig:
    shared_channels: int = 64
    num_shared_blocks: int = 6
    task_heads: List[str] = field(default_factory=lambda: ['reflection', 'derain', 'dehaze'])
    reflection_weight: float = 1.0
    derain_weight: float = 0.8
    dehaze_weight: float = 0.8
    feature_sharing_ratio: float = 0.5


@dataclass
class ModelConfig:
    n_channels: int = 3
    bilinear: bool = False
    use_polarization: bool = False
    image_size: Tuple[int, int] = (256, 256)


@dataclass
class TrainingConfig:
    epochs: int = 100
    batch_size: int = 4
    learning_rate: float = 1e-4
    beta1: float = 0.5
    beta2: float = 0.999
    weight_decay: float = 1e-5
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    num_workers: int = 0
    save_interval: int = 10
    log_interval: int = 10


@dataclass
class InferenceConfig:
    checkpoint_path: Optional[str] = None
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    output_dir: str = "output"
    save_all_outputs: bool = True
    apply_post_processing: bool = True
    enable_texture_synthesis: bool = True
    enable_polarization_estimation: bool = True


@dataclass
class DataConfig:
    train_dir: str = "data/train/images"
    train_transmission_dir: Optional[str] = "data/train/transmission"
    train_reflection_dir: Optional[str] = "data/train/reflection"
    val_dir: str = "data/val/images"
    val_transmission_dir: Optional[str] = "data/val/transmission"
    val_reflection_dir: Optional[str] = "data/val/reflection"
    test_dir: str = "data/test/images"
    polarization_dir: Optional[str] = None
    image_size: Tuple[int, int] = (256, 256)


@dataclass
class EvalConfig:
    compute_psnr: bool = True
    compute_ssim: bool = True
    compute_lpips: bool = False
    compute_fid: bool = False
    save_metrics: bool = True
    metrics_output_path: str = "output/metrics.json"


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    data: DataConfig = field(default_factory=DataConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)
    inpainting: InpaintingConfig = field(default_factory=InpaintingConfig)
    polarization: PolarizationConfig = field(default_factory=PolarizationConfig)
    mos: MOSConfig = field(default_factory=MOSConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    multitask: MultiTaskConfig = field(default_factory=MultiTaskConfig)
