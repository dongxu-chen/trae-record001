import os
import glob
import numpy as np
import SimpleITK as sitk
import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Optional
from monai.transforms import (
    Compose,
    LoadImaged,
    EnsureChannelFirstd,
    Spacingd,
    Orientationd,
    ScaleIntensityRanged,
    CropForegroundd,
    ResizeWithPadOrCropd,
    ToTensord,
)
from monai.data import MetaTensor
from config import Config
from augmentation import get_inference_transforms


class DICOMDataset(Dataset):
    def __init__(
        self,
        image_paths: List[str],
        label_paths: List[str],
        transform: Optional[Compose] = None,
        config: Config = None,
    ):
        assert len(image_paths) == len(label_paths), "Image and label count mismatch"
        self.image_paths = image_paths
        self.label_paths = label_paths
        self.transform = transform
        self.config = config or Config()

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> dict:
        image_path = self.image_paths[idx]
        label_path = self.label_paths[idx]

        data = {
            "image": image_path,
            "label": label_path,
        }

        if self.transform:
            data = self.transform(data)

        return data


def load_dicom_series(dicom_dir: str) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()
    return image


def load_sitk_image(file_path: str) -> sitk.Image:
    if os.path.isdir(file_path):
        return load_dicom_series(file_path)
    return sitk.ReadImage(file_path)


def sitk_to_numpy(image: sitk.Image) -> np.ndarray:
    array = sitk.GetArrayFromImage(image)
    return array.astype(np.float32)


def get_file_paths(data_dir: str, suffix: str = "*.nii.gz") -> List[str]:
    pattern = os.path.join(data_dir, suffix)
    paths = sorted(glob.glob(pattern))
    if not paths:
        pattern = os.path.join(data_dir, "*")
        paths = sorted([p for p in glob.glob(pattern) if os.path.isdir(p) or p.endswith((".nii", ".nii.gz", ".mhd"))])
    return paths


def split_dataset(
    image_paths: List[str],
    label_paths: List[str],
    val_split: float = 0.2,
    test_split: float = 0.1,
    random_seed: int = 42,
) -> Tuple[Tuple[List[str], List[str]], Tuple[List[str], List[str]], Tuple[List[str], List[str]]]:
    np.random.seed(random_seed)
    indices = np.random.permutation(len(image_paths))

    num_test = int(len(indices) * test_split)
    num_val = int(len(indices) * val_split)
    num_train = len(indices) - num_val - num_test

    train_indices = indices[:num_train]
    val_indices = indices[num_train:num_train + num_val]
    test_indices = indices[num_train + num_val:]

    train_images = [image_paths[i] for i in train_indices]
    train_labels = [label_paths[i] for i in train_indices]
    val_images = [image_paths[i] for i in val_indices]
    val_labels = [label_paths[i] for i in val_indices]
    test_images = [image_paths[i] for i in test_indices]
    test_labels = [label_paths[i] for i in test_indices]

    return (train_images, train_labels), (val_images, val_labels), (test_images, test_labels)


def resample_to_isotropic(
    image: sitk.Image,
    target_spacing: float = 1.0,
    is_label: bool = False,
) -> sitk.Image:
    original_spacing = image.GetSpacing()
    original_size = image.GetSize()

    new_size = [
        int(round(original_size[i] * original_spacing[i] / target_spacing))
        for i in range(3)
    ]

    if is_label:
        interpolator = sitk.sitkNearestNeighbor
    else:
        interpolator = sitk.sitkBSpline

    resampler = sitk.ResampleImageFilter()
    resampler.SetOutputSpacing((target_spacing, target_spacing, target_spacing))
    resampler.SetSize(new_size)
    resampler.SetOutputDirection(image.GetDirection())
    resampler.SetOutputOrigin(image.GetOrigin())
    resampler.SetTransform(sitk.Transform())
    resampler.SetDefaultPixelValue(image.GetPixelIDValue())
    resampler.SetInterpolator(interpolator)

    if is_label:
        resampler.SetDefaultPixelValue(0)

    resampled_image = resampler.Execute(image)

    return resampled_image


def normalize_spacing(
    image_path: str,
    label_path: Optional[str] = None,
    target_spacing: float = 1.0,
    output_dir: Optional[str] = None,
) -> Tuple[sitk.Image, Optional[sitk.Image]]:
    image = load_sitk_image(image_path)

    original_spacing = image.GetSpacing()
    print(f"Original spacing: {original_spacing}")

    if original_spacing != (target_spacing, target_spacing, target_spacing):
        print(f"Resampling to isotropic spacing: {target_spacing}mm")
        image = resample_to_isotropic(image, target_spacing, is_label=False)
        print(f"New spacing: {image.GetSpacing()}")

    label = None
    if label_path is not None and os.path.exists(label_path):
        label = load_sitk_image(label_path)
        if original_spacing != (target_spacing, target_spacing, target_spacing):
            label = resample_to_isotropic(label, target_spacing, is_label=True)

    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        image_name = os.path.basename(image_path)
        sitk.WriteImage(image, os.path.join(output_dir, image_name))
        if label is not None:
            label_name = os.path.basename(label_path)
            sitk.WriteImage(label, os.path.join(output_dir, label_name))

    return image, label


def get_basic_transforms(config: Config, mode: str = "train") -> Compose:
    keys = ["image", "label"]

    target_spacing = config.spacing
    if config.isotropic_spacing:
        target_spacing = (config.target_spacing, config.target_spacing, config.target_spacing)

    if mode == "train":
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
            CropForegroundd(keys=keys, source_key="image"),
            ResizeWithPadOrCropd(keys=keys, spatial_size=config.image_size),
            ToTensord(keys=keys),
        ]
    else:
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


def create_data_loaders_from_paths(
    config: Config,
    train_images: List[str],
    train_labels: List[str],
    val_images: List[str],
    val_labels: List[str],
    test_images: List[str],
    test_labels: List[str],
    train_transform: Optional[Compose] = None,
    val_transform: Optional[Compose] = None,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    print(f"Train: {len(train_images)}, Val: {len(val_images)}, Test: {len(test_images)}")

    if train_transform is None:
        train_transform = get_basic_transforms(config, mode="train")
    if val_transform is None:
        val_transform = get_basic_transforms(config, mode="val")

    train_dataset = DICOMDataset(train_images, train_labels, train_transform, config)
    val_dataset = DICOMDataset(val_images, val_labels, val_transform, config)
    test_dataset = DICOMDataset(test_images, test_labels, val_transform, config)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader, test_loader


def create_data_loaders(
    config: Config,
    train_transform: Optional[Compose] = None,
    val_transform: Optional[Compose] = None,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    image_paths = get_file_paths(config.image_dir)
    label_paths = get_file_paths(config.label_dir)

    print(f"Found {len(image_paths)} images and {len(label_paths)} labels")

    (train_images, train_labels), (val_images, val_labels), (test_images, test_labels) = split_dataset(
        image_paths,
        label_paths,
        val_split=config.val_split,
        test_split=config.test_split,
        random_seed=config.random_seed,
    )

    return create_data_loaders_from_paths(
        config,
        train_images, train_labels,
        val_images, val_labels,
        test_images, test_labels,
        train_transform, val_transform,
    )


class UnlabeledDataset(Dataset):
    def __init__(
        self,
        image_paths: List[str],
        transform: Optional[Compose] = None,
        config: Config = None,
    ):
        self.image_paths = image_paths
        self.transform = transform
        self.config = config or Config()

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> dict:
        image_path = self.image_paths[idx]

        data = {
            "image": image_path,
        }

        if self.transform:
            data = self.transform(data)

        data["image_path"] = image_path
        return data


def get_unlabeled_paths(config: Config) -> List[str]:
    return get_file_paths(config.unlabeled_dir)


def create_unlabeled_loader(
    config: Config,
    transform: Optional[Compose] = None,
) -> DataLoader:
    unlabeled_paths = get_unlabeled_paths(config)
    print(f"Found {len(unlabeled_paths)} unlabeled images")

    if transform is None:
        transform = get_inference_transforms(config)

    dataset = UnlabeledDataset(unlabeled_paths, transform, config)

    loader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    return loader
