import numpy as np
import torch
from monai.transforms import (
    Compose,
    LoadImaged,
    EnsureChannelFirstd,
    Spacingd,
    Orientationd,
    ScaleIntensityRanged,
    CropForegroundd,
    ResizeWithPadOrCropd,
    RandRotated,
    RandScaled,
    RandAffined,
    Rand3DElasticd,
    RandFlipd,
    RandGaussianNoised,
    RandGaussianSmoothd,
    RandAdjustContrastd,
    ToTensord,
    Transform,
)
from typing import Optional, Dict, Any
from config import Config


def calculate_elastic_sigma(
    epoch: int,
    config: Config,
) -> float:
    start_epoch = config.elastic_decay_start_epoch
    end_epoch = config.elastic_decay_end_epoch
    initial_sigma = config.elastic_deform_sigma
    min_sigma = config.elastic_deform_sigma_min

    if epoch < start_epoch:
        return initial_sigma
    elif epoch >= end_epoch:
        return min_sigma
    else:
        decay_ratio = (epoch - start_epoch) / (end_epoch - start_epoch)
        current_sigma = initial_sigma - (initial_sigma - min_sigma) * decay_ratio
        return max(current_sigma, min_sigma)


def calculate_elastic_magnitude(
    epoch: int,
    config: Config,
    initial_magnitude: float = 2.0,
    min_magnitude: float = 0.5,
) -> float:
    start_epoch = config.elastic_decay_start_epoch
    end_epoch = config.elastic_decay_end_epoch

    if epoch < start_epoch:
        return initial_magnitude
    elif epoch >= end_epoch:
        return min_magnitude
    else:
        decay_ratio = (epoch - start_epoch) / (end_epoch - start_epoch)
        current_magnitude = initial_magnitude - (initial_magnitude - min_magnitude) * decay_ratio
        return max(current_magnitude, min_magnitude)


class DynamicElasticTransform(Transform):
    def __init__(
        self,
        config: Config,
        keys: list = ["image", "label"],
    ):
        super().__init__()
        self.config = config
        self.keys = keys
        self.current_epoch = 0
        self._update_transform()

    def set_epoch(self, epoch: int):
        self.current_epoch = epoch
        self._update_transform()

    def _update_transform(self):
        sigma = calculate_elastic_sigma(self.current_epoch, self.config)
        magnitude = calculate_elastic_magnitude(self.current_epoch, self.config)
        prob = self.config.augmentation_prob

        if self.current_epoch >= self.config.elastic_decay_end_epoch:
            prob = prob * 0.3

        self.transform = Rand3DElasticd(
            keys=self.keys,
            sigma_x=sigma,
            sigma_y=sigma,
            sigma_z=sigma,
            magnitude_x=magnitude,
            magnitude_y=magnitude,
            magnitude_z=magnitude,
            prob=prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        )

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.transform(data)


class DynamicRotationTransform(Transform):
    def __init__(
        self,
        config: Config,
        keys: list = ["image", "label"],
    ):
        super().__init__()
        self.config = config
        self.keys = keys
        self.current_epoch = 0
        self._update_transform()

    def set_epoch(self, epoch: int):
        self.current_epoch = epoch
        self._update_transform()

    def _update_transform(self):
        decay_factor = max(0.3, 1.0 - self.current_epoch / self.config.elastic_decay_end_epoch)
        range_x = np.deg2rad(self.config.rotation_range[0]) * decay_factor
        range_y = np.deg2rad(self.config.rotation_range[1]) * decay_factor
        range_z = np.deg2rad(self.config.rotation_range[1]) * decay_factor
        prob = self.config.augmentation_prob

        if self.current_epoch >= self.config.elastic_decay_end_epoch:
            prob = prob * 0.5

        self.transform = RandRotated(
            keys=self.keys,
            range_x=range_x,
            range_y=range_y,
            range_z=range_z,
            prob=prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        )

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.transform(data)


class AugmentationScheduler:
    def __init__(self, config: Config, keys: list = ["image", "label"]):
        self.config = config
        self.keys = keys
        self.elastic_transform = DynamicElasticTransform(config, keys)
        self.rotation_transform = DynamicRotationTransform(config, keys)

    def set_epoch(self, epoch: int):
        self.elastic_transform.set_epoch(epoch)
        self.rotation_transform.set_epoch(epoch)

        sigma = calculate_elastic_sigma(epoch, config)
        magnitude = calculate_elastic_magnitude(epoch, config)
        print(f"Epoch {epoch + 1}: Elastic sigma={sigma:.2f}, magnitude={magnitude:.2f}")


def get_base_transforms(config: Config, mode: str = "train") -> list:
    keys = ["image", "label"]

    target_spacing = config.spacing
    if config.isotropic_spacing:
        target_spacing = (config.target_spacing, config.target_spacing, config.target_spacing)

    transforms = [
        LoadImaged(keys=keys),
        EnsureChannelFirstd(keys=keys),
        Orientationd(keys=keys, axcodes="RAS"),
        Spacingd(
            keys=keys,
            pixdim=target_spacing,
            mode=("bilinear", "nearest"),
            dtype=(torch.float32, torch.uint8),
        ),
        ScaleIntensityRanged(
            keys=["image"],
            a_min=config.window_level - config.window_width / 2,
            a_max=config.window_level + config.window_width / 2,
            b_min=0.0,
            b_max=1.0,
            clip=True,
        ),
    ]

    if mode == "train":
        transforms.append(CropForegroundd(keys=keys, source_key="image"))

    return transforms


def get_fixed_augmentations(config: Config) -> list:
    keys = ["image", "label"]

    augmentations = [
        RandFlipd(
            keys=keys,
            spatial_axis=0,
            prob=config.augmentation_prob,
        ),
        RandFlipd(
            keys=keys,
            spatial_axis=1,
            prob=config.augmentation_prob,
        ),
        RandFlipd(
            keys=keys,
            spatial_axis=2,
            prob=config.augmentation_prob,
        ),
        RandScaled(
            keys=keys,
            scale_range=config.scale_range,
            prob=config.augmentation_prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
        RandAffined(
            keys=keys,
            rotate_range=(0, 0, np.deg2rad(15)),
            shear_range=(0.1, 0.1, 0.1),
            translate_range=(5, 5, 5),
            scale_range=config.scale_range,
            prob=config.augmentation_prob * 0.5,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
    ]

    intensity_augmentations = [
        RandGaussianNoised(
            keys=["image"],
            mean=0.0,
            std=0.01,
            prob=config.augmentation_prob * 0.5,
        ),
        RandGaussianSmoothd(
            keys=["image"],
            sigma_x=(0.5, 1.0),
            sigma_y=(0.5, 1.0),
            sigma_z=(0.5, 1.0),
            prob=config.augmentation_prob * 0.5,
        ),
        RandAdjustContrastd(
            keys=["image"],
            gamma=(0.9, 1.1),
            prob=config.augmentation_prob * 0.5,
        ),
    ]

    return augmentations + intensity_augmentations


def get_final_transforms(config: Config) -> list:
    keys = ["image", "label"]
    return [
        ResizeWithPadOrCropd(keys=keys, spatial_size=config.image_size),
        ToTensord(keys=keys),
    ]


def get_train_transforms(config: Config) -> Compose:
    keys = ["image", "label"]

    transforms = get_base_transforms(config, mode="train")

    augmentations = [
        RandFlipd(
            keys=keys,
            spatial_axis=0,
            prob=config.augmentation_prob,
        ),
        RandFlipd(
            keys=keys,
            spatial_axis=1,
            prob=config.augmentation_prob,
        ),
        RandFlipd(
            keys=keys,
            spatial_axis=2,
            prob=config.augmentation_prob,
        ),
        RandRotated(
            keys=keys,
            range_x=np.deg2rad(config.rotation_range[0]),
            range_y=np.deg2rad(config.rotation_range[1]),
            range_z=np.deg2rad(config.rotation_range[1]),
            prob=config.augmentation_prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
        RandScaled(
            keys=keys,
            scale_range=config.scale_range,
            prob=config.augmentation_prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
        Rand3DElasticd(
            keys=keys,
            sigma_x=config.elastic_deform_sigma,
            sigma_y=config.elastic_deform_sigma,
            sigma_z=config.elastic_deform_sigma,
            magnitude_x=2.0,
            magnitude_y=2.0,
            magnitude_z=2.0,
            prob=config.augmentation_prob,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
        RandAffined(
            keys=keys,
            rotate_range=(0, 0, np.deg2rad(15)),
            shear_range=(0.1, 0.1, 0.1),
            translate_range=(5, 5, 5),
            scale_range=config.scale_range,
            prob=config.augmentation_prob * 0.5,
            mode=("bilinear", "nearest"),
            padding_mode="zeros",
        ),
    ]

    intensity_augmentations = [
        RandGaussianNoised(
            keys=["image"],
            mean=0.0,
            std=0.01,
            prob=config.augmentation_prob * 0.5,
        ),
        RandGaussianSmoothd(
            keys=["image"],
            sigma_x=(0.5, 1.0),
            sigma_y=(0.5, 1.0),
            sigma_z=(0.5, 1.0),
            prob=config.augmentation_prob * 0.5,
        ),
        RandAdjustContrastd(
            keys=["image"],
            gamma=(0.9, 1.1),
            prob=config.augmentation_prob * 0.5,
        ),
    ]

    final_transforms = [
        ResizeWithPadOrCropd(keys=keys, spatial_size=config.image_size),
        ToTensord(keys=keys),
    ]

    all_transforms = transforms + augmentations + intensity_augmentations + final_transforms

    return Compose(all_transforms)


def create_dynamic_train_transforms(config: Config) -> Tuple[Compose, AugmentationScheduler]:
    keys = ["image", "label"]

    scheduler = AugmentationScheduler(config, keys)

    base_transforms = get_base_transforms(config, mode="train")
    fixed_augmentations = get_fixed_augmentations(config)
    dynamic_augmentations = [scheduler.rotation_transform, scheduler.elastic_transform]
    final_transforms = get_final_transforms(config)

    all_transforms = (
        base_transforms +
        fixed_augmentations +
        dynamic_augmentations +
        final_transforms
    )

    return Compose(all_transforms), scheduler


def get_val_transforms(config: Config) -> Compose:
    keys = ["image", "label"]

    target_spacing = config.spacing
    if config.isotropic_spacing:
        target_spacing = (config.target_spacing, config.target_spacing, config.target_spacing)

    transforms = [
        LoadImaged(keys=keys),
        EnsureChannelFirstd(keys=keys),
        Orientationd(keys=keys, axcodes="RAS"),
        Spacingd(
            keys=keys,
            pixdim=target_spacing,
            mode=("bilinear", "nearest"),
            dtype=(torch.float32, torch.uint8),
        ),
        ScaleIntensityRanged(
            keys=["image"],
            a_min=config.window_level - config.window_width / 2,
            a_max=config.window_level + config.window_width / 2,
            b_min=0.0,
            b_max=1.0,
            clip=True,
        ),
        ResizeWithPadOrCropd(keys=keys, spatial_size=config.image_size),
        ToTensord(keys=keys),
    ]

    return Compose(transforms)


def get_inference_transforms(config: Config) -> Compose:
    keys = ["image"]

    target_spacing = config.spacing
    if config.isotropic_spacing:
        target_spacing = (config.target_spacing, config.target_spacing, config.target_spacing)

    transforms = [
        LoadImaged(keys=keys),
        EnsureChannelFirstd(keys=keys),
        Orientationd(keys=keys, axcodes="RAS"),
        Spacingd(
            keys=keys,
            pixdim=target_spacing,
            mode=("bilinear",),
            dtype=(torch.float32,),
        ),
        ScaleIntensityRanged(
            keys=["image"],
            a_min=config.window_level - config.window_width / 2,
            a_max=config.window_level + config.window_width / 2,
            b_min=0.0,
            b_max=1.0,
            clip=True,
        ),
        ResizeWithPadOrCropd(keys=keys, spatial_size=config.image_size),
        ToTensord(keys=keys),
    ]

    return Compose(transforms)
