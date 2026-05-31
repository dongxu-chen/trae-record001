from dataclasses import dataclass, field
from typing import List, Optional
import json


@dataclass
class TrainConfig:
    architecture: str = "dcgan"
    dataset: str = "cifar10"
    data_root: str = "./data"
    img_size: int = 32
    img_channels: int = 3
    batch_size: int = 64
    num_workers: int = 4
    z_dim: int = 128
    g_lr: float = 2e-4
    d_lr: float = 2e-4
    beta1: float = 0.0
    beta2: float = 0.999
    num_epochs: int = 200
    n_critic: int = 1
    lambda_gp: float = 10.0
    d_spectral_norm: bool = False
    g_spectral_norm: bool = False
    style_dim: int = 512
    n_layers_style: int = 8
    checkpoint_dir: str = "./checkpoints"
    sample_dir: str = "./samples"
    log_dir: str = "./runs"
    sample_interval: int = 1000
    checkpoint_interval: int = 5000
    num_sample_images: int = 64
    seed: int = 42
    device: str = "cuda"
    use_ema: bool = False
    ema_decay: float = 0.999
    g_base_channels: int = 64
    d_base_channels: int = 64
    stylegan2_lr: float = 2e-3
    stylegan2_r1_gamma: float = 10.0
    stylegan2_path_reg_gamma: float = 2.0
    lazy_reg_interval: int = 16
    gp_edge_ratio: float = 0.3
    gp_edge_threshold: float = 0.15
    gp_edge_weight: float = 2.0
    mapping_dropout: float = 0.2
    checkpoint_max_keep: int = 5
    checkpoint_expire_seconds: float = 86400.0
    use_amp: bool = False
    fid_kid_enabled: bool = False
    fid_num_samples: int = 10000
    fid_batch_size: int = 128
    kid_num_samples: int = 1000
    kid_subsets: int = 100
    kid_subset_size: int = 1000
    interpolation_frames: int = 120
    interpolation_fps: int = 30
    num_eval_images: int = 50000

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TrainConfig":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_args(cls, args) -> "TrainConfig":
        kwargs = {}
        for f_name in cls.__dataclass_fields__:
            val = getattr(args, f_name, None)
            if val is not None:
                kwargs[f_name] = val
        return cls(**kwargs)
