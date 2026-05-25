import numpy as np
import SimpleITK as sitk
from scipy import ndimage
from skimage import morphology
from typing import Optional, Tuple, Dict, List
from config import Config


def fill_holes_3d(
    mask: np.ndarray,
    min_hole_size: int = 64,
) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got {mask.ndim}D")

    mask = mask.astype(np.uint8)
    unique_labels = np.unique(mask)
    unique_labels = unique_labels[unique_labels != 0]

    filled_mask = np.zeros_like(mask)

    for label in unique_labels:
        binary_mask = (mask == label).astype(np.uint8)

        if min_hole_size > 0:
            binary_filled = morphology.remove_small_holes(
                binary_mask.astype(bool),
                area_threshold=min_hole_size,
            )
        else:
            binary_filled = ndimage.binary_fill_holes(binary_mask)

        filled_mask[binary_filled] = label

    return filled_mask


def remove_small_objects_3d(
    mask: np.ndarray,
    min_object_size: int = 100,
    connectivity: int = 3,
) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got {mask.ndim}D")

    mask = mask.astype(np.uint8)
    unique_labels = np.unique(mask)
    unique_labels = unique_labels[unique_labels != 0]

    cleaned_mask = np.zeros_like(mask)

    for label in unique_labels:
        binary_mask = (mask == label).astype(np.uint8)

        labeled, num_features = ndimage.label(binary_mask, structure=np.ones((3, 3, 3)))

        sizes = ndimage.sum(binary_mask, labeled, range(1, num_features + 1))

        if len(sizes) == 0:
            continue

        valid_labels = np.where(sizes >= min_object_size)[0] + 1

        if len(valid_labels) > 0:
            binary_cleaned = np.isin(labeled, valid_labels)
            cleaned_mask[binary_cleaned] = label

    return cleaned_mask


def smooth_mask_3d(
    mask: np.ndarray,
    sigma: float = 0.5,
) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got {mask.ndim}D")

    mask = mask.astype(np.uint8)
    unique_labels = np.unique(mask)
    unique_labels = unique_labels[unique_labels != 0]

    smoothed_mask = np.zeros_like(mask)
    prob_maps = np.zeros((len(unique_labels),) + mask.shape, dtype=np.float32)

    for i, label in enumerate(unique_labels):
        binary_mask = (mask == label).astype(np.float32)
        smoothed = ndimage.gaussian_filter(binary_mask, sigma=sigma)
        prob_maps[i] = smoothed

    if len(unique_labels) > 0:
        max_indices = np.argmax(prob_maps, axis=0)
        max_values = np.max(prob_maps, axis=0)

        for i, label in enumerate(unique_labels):
            smoothed_mask[(max_indices == i) & (max_values > 0.3)] = label

    return smoothed_mask


def keep_largest_component(
    mask: np.ndarray,
) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got {mask.ndim}D")

    mask = mask.astype(np.uint8)
    unique_labels = np.unique(mask)
    unique_labels = unique_labels[unique_labels != 0]

    cleaned_mask = np.zeros_like(mask)

    for label in unique_labels:
        binary_mask = (mask == label).astype(np.uint8)

        labeled, num_features = ndimage.label(binary_mask, structure=np.ones((3, 3, 3)))

        if num_features == 0:
            continue

        sizes = ndimage.sum(binary_mask, labeled, range(1, num_features + 1))
        largest_idx = np.argmax(sizes) + 1

        cleaned_mask[labeled == largest_idx] = label

    return cleaned_mask


def post_process_segmentation(
    mask: np.ndarray,
    config: Config,
) -> np.ndarray:
    if not config.use_post_processing:
        return mask

    processed = mask.copy()

    if config.min_object_size > 0:
        processed = remove_small_objects_3d(
            processed,
            min_object_size=config.min_object_size,
        )

    if config.min_hole_size > 0:
        processed = fill_holes_3d(
            processed,
            min_hole_size=config.min_hole_size,
        )

    processed = keep_largest_component(processed)

    processed = smooth_mask_3d(processed, sigma=0.5)

    return processed


def extract_separate_masks(
    mask: np.ndarray,
    class_names: List[str],
) -> Dict[str, np.ndarray]:
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got {mask.ndim}D")

    separate_masks = {}
    unique_labels = np.unique(mask)

    for idx, class_name in enumerate(class_names):
        if idx == 0:
            continue
        binary_mask = (mask == idx).astype(np.uint8)
        separate_masks[class_name] = binary_mask

    return separate_masks


def save_separate_masks(
    separate_masks: Dict[str, np.ndarray],
    output_dir: str,
    base_name: str,
    reference_image: Optional[sitk.Image] = None,
) -> None:
    import os
    os.makedirs(output_dir, exist_ok=True)

    for organ_name, mask_array in separate_masks.items():
        mask_sitk = sitk.GetImageFromArray(mask_array)

        if reference_image is not None:
            mask_sitk.CopyInformation(reference_image)

        output_path = os.path.join(output_dir, f"{base_name}_{organ_name}.nii.gz")
        sitk.WriteImage(mask_sitk, output_path)


def sitk_post_processing(
    mask_sitk: sitk.Image,
    config: Config,
) -> sitk.Image:
    mask_array = sitk.GetArrayFromImage(mask_sitk)
    processed_array = post_process_segmentation(mask_array, config)
    processed_sitk = sitk.GetImageFromArray(processed_array)
    processed_sitk.CopyInformation(mask_sitk)
    return processed_sitk


def apply_morphological_operations(
    mask: np.ndarray,
    class_idx: int,
    operation: str = "closing",
    kernel_size: int = 3,
) -> np.ndarray:
    binary_mask = (mask == class_idx).astype(np.uint8)
    kernel = morphology.ball(kernel_size)

    if operation == "closing":
        processed = morphology.closing(binary_mask, kernel)
    elif operation == "opening":
        processed = morphology.opening(binary_mask, kernel)
    elif operation == "dilation":
        processed = morphology.dilation(binary_mask, kernel)
    elif operation == "erosion":
        processed = morphology.erosion(binary_mask, kernel)
    else:
        raise ValueError(f"Unknown operation: {operation}")

    result = mask.copy()
    result[binary_mask > 0] = 0
    result[processed > 0] = class_idx

    return result
