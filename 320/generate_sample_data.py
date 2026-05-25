import os
import numpy as np
import SimpleITK as sitk
from typing import Tuple, List, Dict
from config import Config


ORGAN_DEFAULTS = {
    "liver": {"label": 1, "intensity": (80, 120), "size": (10, 18, 12, 20, 10, 18)},
    "kidney_right": {"label": 2, "intensity": (60, 100), "size": (4, 7, 8, 12, 4, 7)},
    "kidney_left": {"label": 3, "intensity": (60, 100), "size": (4, 7, 8, 12, 4, 7)},
    "spleen": {"label": 4, "intensity": (70, 110), "size": (3, 5, 10, 16, 3, 5)},
    "pancreas": {"label": 5, "intensity": (50, 90), "size": (2, 4, 10, 16, 2, 4)},
    "tumor": {"label": 6, "intensity": (120, 180), "size": (3, 6, 3, 6, 3, 6)},
}


def generate_3d_ellipsoid(
    shape: Tuple[int, int, int],
    center: Tuple[float, float, float],
    radii: Tuple[float, float, float],
) -> np.ndarray:
    z, y, x = np.ogrid[:shape[0], :shape[1], :shape[2]]
    z0, y0, x0 = center
    rz, ry, rx = radii

    ellipsoid = ((z - z0) ** 2) / (rz ** 2) + \
                ((y - y0) ** 2) / (ry ** 2) + \
                ((x - x0) ** 2) / (rx ** 2) <= 1

    return ellipsoid.astype(np.uint8)


def get_organ_position(
    image_size: Tuple[int, int, int],
    organ_name: str,
    liver_center: Tuple[float, float, float] = None,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    z_size, y_size, x_size = image_size

    if organ_name == "liver":
        center = (
            np.random.uniform(z_size * 0.35, z_size * 0.55),
            np.random.uniform(y_size * 0.45, y_size * 0.65),
            np.random.uniform(x_size * 0.35, x_size * 0.55),
        )
        radii = (
            np.random.uniform(10, 18),
            np.random.uniform(12, 20),
            np.random.uniform(10, 18),
        )
    elif organ_name == "kidney_right":
        if liver_center is None:
            center = (
                np.random.uniform(z_size * 0.3, z_size * 0.5),
                np.random.uniform(y_size * 0.2, y_size * 0.35),
                np.random.uniform(x_size * 0.25, x_size * 0.4),
            )
        else:
            center = (
                liver_center[0] + np.random.uniform(-3, 3),
                liver_center[1] - np.random.uniform(10, 15),
                liver_center[2] - np.random.uniform(8, 12),
            )
        radii = (
            np.random.uniform(4, 7),
            np.random.uniform(8, 12),
            np.random.uniform(4, 7),
        )
    elif organ_name == "kidney_left":
        if liver_center is None:
            center = (
                np.random.uniform(z_size * 0.3, z_size * 0.5),
                np.random.uniform(y_size * 0.65, y_size * 0.8),
                np.random.uniform(x_size * 0.6, x_size * 0.75),
            )
        else:
            center = (
                liver_center[0] + np.random.uniform(-3, 3),
                liver_center[1] + np.random.uniform(10, 15),
                liver_center[2] + np.random.uniform(8, 12),
            )
        radii = (
            np.random.uniform(4, 7),
            np.random.uniform(8, 12),
            np.random.uniform(4, 7),
        )
    elif organ_name == "spleen":
        if liver_center is None:
            center = (
                np.random.uniform(z_size * 0.4, z_size * 0.6),
                np.random.uniform(y_size * 0.7, y_size * 0.85),
                np.random.uniform(x_size * 0.3, x_size * 0.45),
            )
        else:
            center = (
                liver_center[0] + np.random.uniform(2, 6),
                liver_center[1] + np.random.uniform(12, 18),
                liver_center[2] + np.random.uniform(-6, -2),
            )
        radii = (
            np.random.uniform(3, 5),
            np.random.uniform(10, 16),
            np.random.uniform(3, 5),
        )
    elif organ_name == "pancreas":
        if liver_center is None:
            center = (
                np.random.uniform(z_size * 0.45, z_size * 0.6),
                np.random.uniform(y_size * 0.4, y_size * 0.6),
                np.random.uniform(x_size * 0.5, x_size * 0.65),
            )
        else:
            center = (
                liver_center[0] + np.random.uniform(3, 7),
                liver_center[1] + np.random.uniform(5, 10),
                liver_center[2] + np.random.uniform(3, 7),
            )
        radii = (
            np.random.uniform(2, 4),
            np.random.uniform(10, 16),
            np.random.uniform(2, 4),
        )
    elif organ_name == "tumor":
        if liver_center is None:
            center = (
                np.random.uniform(z_size * 0.35, z_size * 0.55),
                np.random.uniform(y_size * 0.45, y_size * 0.65),
                np.random.uniform(x_size * 0.35, x_size * 0.55),
            )
        else:
            center = (
                liver_center[0] + np.random.uniform(-5, 5),
                liver_center[1] + np.random.uniform(-5, 5),
                liver_center[2] + np.random.uniform(-5, 5),
            )
        radii = (
            np.random.uniform(3, 6),
            np.random.uniform(3, 6),
            np.random.uniform(3, 6),
        )
    else:
        raise ValueError(f"Unknown organ: {organ_name}")

    return center, radii


def generate_multi_organ_sample(
    image_size: Tuple[int, int, int],
    class_names: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    image = np.random.normal(-100, 400, image_size).astype(np.float32)
    label = np.zeros(image_size, dtype=np.uint8)

    organ_masks = {}
    liver_center = None

    if "liver" in class_names:
        organ_idx = class_names.index("liver")
        center, radii = get_organ_position(image_size, "liver")
        liver_center = center
        mask = generate_3d_ellipsoid(image_size, center, radii)
        organ_masks["liver"] = mask
        intensity = ORGAN_DEFAULTS["liver"]["intensity"]
        image[mask == 1] += np.random.uniform(intensity[0], intensity[1])
        label[mask == 1] = organ_idx

    for organ_name in class_names:
        if organ_name in ["background", "liver"]:
            continue

        organ_idx = class_names.index(organ_name)

        if organ_name in ORGAN_DEFAULTS:
            center, radii = get_organ_position(image_size, organ_name, liver_center)
            mask = generate_3d_ellipsoid(image_size, center, radii)

            for existing_name, existing_mask in organ_masks.items():
                overlap = mask & existing_mask
                mask = mask & (~overlap)

            if organ_name == "tumor" and "liver" in organ_masks:
                mask = mask & organ_masks["liver"]

            if np.sum(mask) > 0:
                organ_masks[organ_name] = mask
                intensity = ORGAN_DEFAULTS[organ_name]["intensity"]
                image[mask == 1] += np.random.uniform(intensity[0], intensity[1])
                label[mask == 1] = organ_idx

    noise = np.random.normal(0, 20, image_size)
    image += noise
    image = np.clip(image, -200, 500)

    return image, label


def generate_sample_data(
    output_dir: str,
    num_samples: int = 10,
    image_size: Tuple[int, int, int] = (64, 64, 64),
    multi_organ: bool = True,
    class_names: List[str] = None,
    num_unlabeled: int = 0,
) -> None:
    image_dir = os.path.join(output_dir, "images")
    label_dir = os.path.join(output_dir, "labels")
    unlabeled_dir = os.path.join(output_dir, "unlabeled")

    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)
    if num_unlabeled > 0:
        os.makedirs(unlabeled_dir, exist_ok=True)

    if class_names is None:
        if multi_organ:
            class_names = [
                "background", "liver", "kidney_right",
                "kidney_left", "spleen", "pancreas", "tumor"
            ]
        else:
            class_names = ["background", "liver", "tumor"]

    print(f"Generating {num_samples} labeled and {num_unlabeled} unlabeled sample 3D images...")
    print(f"Classes: {class_names}")

    for i in range(num_samples):
        if multi_organ:
            image, label = generate_multi_organ_sample(image_size, class_names)
        else:
            image = np.random.normal(-100, 400, image_size).astype(np.float32)
            label = np.zeros(image_size, dtype=np.uint8)

            liver_center = (
                np.random.uniform(20, image_size[0] - 20),
                np.random.uniform(20, image_size[1] - 20),
                np.random.uniform(20, image_size[2] - 20),
            )
            liver_radii = (
                np.random.uniform(10, 18),
                np.random.uniform(12, 20),
                np.random.uniform(10, 18),
            )
            liver_mask = generate_3d_ellipsoid(image_size, liver_center, liver_radii)
            image[liver_mask == 1] += np.random.uniform(80, 120)
            label[liver_mask == 1] = 1

            if np.random.random() > 0.3:
                tumor_center = (
                    liver_center[0] + np.random.uniform(-5, 5),
                    liver_center[1] + np.random.uniform(-5, 5),
                    liver_center[2] + np.random.uniform(-5, 5),
                )
                tumor_radii = (
                    np.random.uniform(3, 6),
                    np.random.uniform(3, 6),
                    np.random.uniform(3, 6),
                )
                tumor_mask = generate_3d_ellipsoid(image_size, tumor_center, tumor_radii)
                tumor_mask = tumor_mask & liver_mask
                image[tumor_mask == 1] += np.random.uniform(40, 80)
                label[tumor_mask == 1] = 2

            noise = np.random.normal(0, 20, image_size)
            image += noise
            image = np.clip(image, -200, 500)

        image_sitk = sitk.GetImageFromArray(image)
        label_sitk = sitk.GetImageFromArray(label)

        spacing = (1.0, 1.0, 1.0)
        image_sitk.SetSpacing(spacing)
        label_sitk.SetSpacing(spacing)

        image_path = os.path.join(image_dir, f"sample_{i:03d}.nii.gz")
        label_path = os.path.join(label_dir, f"sample_{i:03d}.nii.gz")

        sitk.WriteImage(image_sitk, image_path)
        sitk.WriteImage(label_sitk, label_path)

        print(f"  Generated labeled sample {i + 1}/{num_samples}")

    for i in range(num_unlabeled):
        if multi_organ:
            image, _ = generate_multi_organ_sample(image_size, class_names)
        else:
            image = np.random.normal(-100, 400, image_size).astype(np.float32)
            liver_center = (
                np.random.uniform(20, image_size[0] - 20),
                np.random.uniform(20, image_size[1] - 20),
                np.random.uniform(20, image_size[2] - 20),
            )
            liver_radii = (
                np.random.uniform(10, 18),
                np.random.uniform(12, 20),
                np.random.uniform(10, 18),
            )
            liver_mask = generate_3d_ellipsoid(image_size, liver_center, liver_radii)
            image[liver_mask == 1] += np.random.uniform(80, 120)
            noise = np.random.normal(0, 20, image_size)
            image += noise
            image = np.clip(image, -200, 500)

        image_sitk = sitk.GetImageFromArray(image)
        image_sitk.SetSpacing((1.0, 1.0, 1.0))
        image_path = os.path.join(unlabeled_dir, f"unlabeled_{i:03d}.nii.gz")
        sitk.WriteImage(image_sitk, image_path)

        print(f"  Generated unlabeled sample {i + 1}/{num_unlabeled}")

    print(f"\nSample data generated successfully!")
    print(f"  Labeled images saved to: {image_dir}")
    print(f"  Labels saved to: {label_dir}")
    if num_unlabeled > 0:
        print(f"  Unlabeled images saved to: {unlabeled_dir}")
    print(f"\nClass distribution in labels:")
    for i, name in enumerate(class_names):
        print(f"  {i}: {name}")


if __name__ == "__main__":
    config = Config()
    generate_sample_data(
        output_dir=config.data_dir,
        num_samples=20,
        image_size=config.image_size,
        multi_organ=config.multi_organ,
        class_names=config.class_names,
        num_unlabeled=10,
    )
