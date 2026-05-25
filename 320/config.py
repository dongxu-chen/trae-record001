import os
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class Config:
    data_dir: str = "./data"
    image_dir: str = os.path.join(data_dir, "images")
    label_dir: str = os.path.join(data_dir, "labels")
    unlabeled_dir: str = os.path.join(data_dir, "unlabeled")
    output_dir: str = "./output"
    model_dir: str = os.path.join(output_dir, "models")
    log_dir: str = os.path.join(output_dir, "logs")
    result_dir: str = os.path.join(output_dir, "results")
    al_dir: str = os.path.join(output_dir, "active_learning")

    image_size: Tuple[int, int, int] = (64, 64, 64)
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    isotropic_spacing: bool = True
    target_spacing: float = 1.0

    num_classes: int = 7
    class_names: List[str] = [
        "background",
        "liver",
        "kidney_right",
        "kidney_left",
        "spleen",
        "pancreas",
        "tumor",
    ]

    multi_organ: bool = True
    save_separate_masks: bool = True

    batch_size: int = 2
    num_workers: int = 4
    num_epochs: int = 100
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5

    in_channels: int = 1
    channels: Tuple[int, ...] = (16, 32, 64, 128, 256)
    strides: Tuple[int, ...] = (2, 2, 2, 2)
    dropout: float = 0.2
    use_residual: bool = True
    use_checkpoint: bool = True

    use_amp: bool = True
    gradient_clip_val: float = 1.0
    gradient_accumulation_steps: int = 4
    early_stopping_patience: int = 15
    save_interval: int = 5

    val_split: float = 0.2
    test_split: float = 0.1
    random_seed: int = 42

    device: str = "cuda"
    device_ids: List[int] = None

    augmentation_prob: float = 0.5
    rotation_range: Tuple[float, float] = (-30.0, 30.0)
    scale_range: Tuple[float, float] = (0.9, 1.1)
    elastic_deform_sigma: float = 10.0
    elastic_deform_sigma_min: float = 2.0
    elastic_deform_points: int = 4
    elastic_decay_start_epoch: int = 30
    elastic_decay_end_epoch: int = 80

    window_level: float = 40.0
    window_width: float = 400.0

    use_post_processing: bool = True
    min_hole_size: int = 64
    min_object_size: int = 100

    use_active_learning: bool = True
    al_query_strategy: str = "uncertainty"
    al_initial_labeled_ratio: float = 0.2
    al_num_iterations: int = 5
    al_num_queries_per_iter: int = 3
    al_uncertainty_type: str = "entropy"

    def __post_init__(self):
        for dir_path in [
            self.output_dir, self.model_dir, self.log_dir, self.result_dir,
            self.al_dir, self.unlabeled_dir
        ]:
            os.makedirs(dir_path, exist_ok=True)
        if self.isotropic_spacing:
            self.spacing = (self.target_spacing, self.target_spacing, self.target_spacing)
