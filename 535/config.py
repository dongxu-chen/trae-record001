from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class ReidConfig:
    model_name: str = "resnet50"
    feature_dim: int = 512
    input_size: tuple[int, int] = (256, 128)
    mean: tuple[float, float, float] = (0.485, 0.456, 0.406)
    std: tuple[float, float, float] = (0.229, 0.224, 0.225)
    device: str = "cuda"
    model_weights_path: str = ""
    use_domain_adaptation: bool = True
    da_learning_rate: float = 1e-4
    da_momentum: float = 0.9
    da_epochs: int = 5
    da_batch_size: int = 32


@dataclass
class FaissConfig:
    index_type: str = "FlatIP"
    nlist: int = 100
    nprobe: int = 10


@dataclass
class CameraPairConfig:
    time_window: float = 300.0
    spatial_weight: float = 0.3
    temporal_weight: float = 0.3
    transition_cost: float = 1.0


@dataclass
class STRankerConfig:
    default_time_window: float = 300.0
    default_spatial_weight: float = 0.3
    default_temporal_weight: float = 0.3
    visual_weight: float = 0.4
    camera_transition_matrix: Optional[dict[str, float]] = field(default_factory=dict)
    camera_pair_configs: dict[tuple[str, str], CameraPairConfig] = field(default_factory=dict)
    camera_positions: dict[str, tuple[float, float]] = field(default_factory=dict)

    def get_pair_config(self, cam_from: str, cam_to: str) -> CameraPairConfig:
        key = (cam_from, cam_to)
        if key in self.camera_pair_configs:
            return self.camera_pair_configs[key]
        return CameraPairConfig(
                time_window=self.default_time_window,
                spatial_weight=self.default_spatial_weight,
                temporal_weight=self.default_temporal_weight,
            )

    def set_pair_config(
        self,
        cam_from: str,
        cam_to: str,
        time_window: float | None = None,
        spatial_weight: float | None = None,
        temporal_weight: float | None = None,
        transition_cost: float | None = None,
    ) -> None:
        key = (cam_from, cam_to)
        if key not in self.camera_pair_configs:
            self.camera_pair_configs[key] = CameraPairConfig()
        cfg = self.camera_pair_configs[key]
        if time_window is not None:
            cfg.time_window = time_window
        if spatial_weight is not None:
            cfg.spatial_weight = spatial_weight
        if temporal_weight is not None:
            cfg.temporal_weight = temporal_weight
        if transition_cost is not None:
            cfg.transition_cost = transition_cost


@dataclass
class GalleryConfig:
    max_gallery_size: int = 100000
    persist_path: str = str(BASE_DIR / "gallery_data")
    enable_lru: bool = True
    lru_ttl_seconds: float = 86400 * 7
    cleanup_interval_seconds: float = 3600
    cleanup_batch_size: int = 1000


@dataclass
class TrajectoryConfig:
    max_trajectory_age: float = 3600 * 24
    min_track_length: int = 3
    max_track_gap: float = 300.0
    trajectory_merge_threshold: float = 0.75
    enable_cross_camera_tracking: bool = True
    camera_graph: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class MultiModalConfig:
    enable_gait_feature: bool = True
    enable_color_feature: bool = True
    gait_feature_dim: int = 128
    color_feature_dim: int = 64
    visual_feature_weight: float = 0.5
    gait_feature_weight: float = 0.25
    color_feature_weight: float = 0.25
    color_hist_bins: tuple[int, int, int] = (8, 8, 8)
    color_hist_normalize: bool = True


@dataclass
class SlidingWindowConfig:
    window_size: int = 1000
    window_overlap: int = 200
    enable_real_time_search: bool = True
    real_time_batch_size: int = 32
    real_time_interval: float = 0.1
    warmup_samples: int = 100
    cache_ttl_seconds: float = 60.0


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


reid_config = ReidConfig()
faiss_config = FaissConfig()
st_ranker_config = STRankerConfig()
gallery_config = GalleryConfig()
trajectory_config = TrajectoryConfig()
multi_modal_config = MultiModalConfig()
sliding_window_config = SlidingWindowConfig()
server_config = ServerConfig()
