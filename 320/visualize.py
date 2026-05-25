import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from typing import List, Optional, Tuple, Dict
import SimpleITK as sitk
import json
from datetime import datetime

from config import Config


ORGAN_COLORS = {
    "background": "#000000",
    "liver": "#FF0000",
    "kidney_right": "#0000FF",
    "kidney_left": "#00AAFF",
    "spleen": "#00FF00",
    "pancreas": "#FFFF00",
    "tumor": "#FF00FF",
    "heart": "#FF5555",
    "lung": "#55FF55",
}


def load_sitk_as_array(file_path: str) -> np.ndarray:
    image = sitk.ReadImage(file_path)
    return sitk.GetArrayFromImage(image)


def get_colormap_for_classes(class_names: List[str]) -> colors.ListedColormap:
    color_list = []
    for name in class_names:
        if name in ORGAN_COLORS:
            color_list.append(ORGAN_COLORS[name])
        else:
            r = np.random.rand()
            g = np.random.rand()
            b = np.random.rand()
            color_list.append((r, g, b))
    return colors.ListedColormap(color_list)


def plot_slice(
    image: np.ndarray,
    label: Optional[np.ndarray] = None,
    prediction: Optional[np.ndarray] = None,
    slice_idx: Optional[int] = None,
    axis: int = 2,
    class_names: List[str] = ["background", "liver", "kidney_right", "kidney_left", "spleen", "pancreas", "tumor"],
    save_path: Optional[str] = None,
    show: bool = False,
):
    if slice_idx is None:
        slice_idx = image.shape[axis] // 2

    if axis == 0:
        img_slice = image[slice_idx, :, :]
        if label is not None:
            lbl_slice = label[slice_idx, :, :]
        if prediction is not None:
            pred_slice = prediction[slice_idx, :, :]
    elif axis == 1:
        img_slice = image[:, slice_idx, :]
        if label is not None:
            lbl_slice = label[:, slice_idx, :]
        if prediction is not None:
            pred_slice = prediction[:, slice_idx, :]
    else:
        img_slice = image[:, :, slice_idx]
        if label is not None:
            lbl_slice = label[:, :, slice_idx]
        if prediction is not None:
            pred_slice = prediction[:, :, slice_idx]

    num_plots = 1
    if label is not None:
        num_plots += 1
    if prediction is not None:
        num_plots += 1

    fig, axes = plt.subplots(1, num_plots, figsize=(6 * num_plots, 6))
    if num_plots == 1:
        axes = [axes]

    cmap_image = plt.cm.gray
    cmap_label = get_colormap_for_classes(class_names)
    bounds = list(range(len(class_names) + 1))
    norm = colors.BoundaryNorm(bounds, cmap_label.N)

    idx = 0
    axes[idx].imshow(img_slice, cmap=cmap_image)
    axes[idx].set_title("Image")
    axes[idx].axis("off")
    idx += 1

    im = None
    if label is not None:
        im = axes[idx].imshow(lbl_slice, cmap=cmap_label, norm=norm)
        axes[idx].set_title("Ground Truth")
        axes[idx].axis("off")
        idx += 1

    if prediction is not None:
        im = axes[idx].imshow(pred_slice, cmap=cmap_label, norm=norm)
        axes[idx].set_title("Prediction")
        axes[idx].axis("off")

    if (label is not None or prediction is not None) and im is not None:
        cbar = fig.colorbar(im, ax=axes[-1], ticks=bounds[:-1], orientation="vertical")
        cbar.ax.set_yticklabels(class_names)

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {save_path}")

    if show:
        plt.show()

    plt.close()


def plot_single_organ_slice(
    image: np.ndarray,
    mask: np.ndarray,
    organ_name: str,
    slice_idx: Optional[int] = None,
    axis: int = 2,
    save_path: Optional[str] = None,
    show: bool = False,
):
    if slice_idx is None:
        slice_idx = image.shape[axis] // 2

    if axis == 0:
        img_slice = image[slice_idx, :, :]
        mask_slice = mask[slice_idx, :, :]
    elif axis == 1:
        img_slice = image[:, slice_idx, :]
        mask_slice = mask[:, slice_idx, :]
    else:
        img_slice = image[:, :, slice_idx]
        mask_slice = mask[:, :, slice_idx]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    axes[0].imshow(img_slice, cmap=plt.cm.gray)
    axes[0].set_title("Image")
    axes[0].axis("off")

    axes[1].imshow(mask_slice, cmap=plt.cm.jet, vmin=0, vmax=1)
    axes[1].set_title(f"{organ_name} Mask")
    axes[1].axis("off")

    overlay = img_slice.copy()
    color = ORGAN_COLORS.get(organ_name, "#FF0000")
    r = int(color[1:3], 16) / 255
    g = int(color[3:5], 16) / 255
    b = int(color[5:7], 16) / 255

    overlay_rgb = np.stack([overlay, overlay, overlay], axis=-1)
    overlay_rgb[mask_slice > 0] = [r, g, b]
    axes[2].imshow(overlay_rgb)
    axes[2].set_title(f"Overlay - {organ_name}")
    axes[2].axis("off")

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {save_path}")

    if show:
        plt.show()

    plt.close()


def plot_comparison(
    image: np.ndarray,
    label: np.ndarray,
    prediction: np.ndarray,
    output_dir: str,
    base_name: str,
    class_names: List[str] = ["background", "liver", "kidney_right", "kidney_left", "spleen", "pancreas", "tumor"],
    num_slices: int = 5,
):
    os.makedirs(output_dir, exist_ok=True)

    z_slices = np.linspace(0, image.shape[2] - 1, num_slices, dtype=int)

    for i, z in enumerate(z_slices):
        save_path = os.path.join(output_dir, f"{base_name}_z_{z:03d}.png")
        plot_slice(
            image, label, prediction,
            slice_idx=z, axis=2,
            class_names=class_names,
            save_path=save_path,
            show=False,
        )

    x_slices = np.linspace(0, image.shape[0] - 1, num_slices, dtype=int)
    for i, x in enumerate(x_slices):
        save_path = os.path.join(output_dir, f"{base_name}_x_{x:03d}.png")
        plot_slice(
            image, label, prediction,
            slice_idx=x, axis=0,
            class_names=class_names,
            save_path=save_path,
            show=False,
        )

    y_slices = np.linspace(0, image.shape[1] - 1, num_slices, dtype=int)
    for i, y in enumerate(y_slices):
        save_path = os.path.join(output_dir, f"{base_name}_y_{y:03d}.png")
        plot_slice(
            image, label, prediction,
            slice_idx=y, axis=1,
            class_names=class_names,
            save_path=save_path,
            show=False,
        )


def plot_separate_organs(
    image: np.ndarray,
    prediction: np.ndarray,
    class_names: List[str],
    output_dir: str,
    base_name: str,
    num_slices: int = 3,
):
    os.makedirs(output_dir, exist_ok=True)

    z_slices = np.linspace(0, image.shape[2] - 1, num_slices, dtype=int)

    for class_idx, class_name in enumerate(class_names):
        if class_idx == 0:
            continue

        organ_mask = (prediction == class_idx).astype(np.uint8)

        if np.sum(organ_mask) == 0:
            continue

        for z in z_slices:
            save_path = os.path.join(output_dir, f"{base_name}_{class_name}_z_{z:03d}.png")
            plot_single_organ_slice(
                image, organ_mask, class_name,
                slice_idx=z, axis=2,
                save_path=save_path,
                show=False,
            )


def plot_training_history(history_path: str, save_path: Optional[str] = None):
    with open(history_path, "r") as f:
        history = json.load(f)

    train_history = history["train"]
    val_history = history["val"]

    epochs = list(range(1, len(train_history) + 1))

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    axes[0].plot(epochs, [h["loss"] for h in train_history], label="Train Loss")
    axes[0].plot(epochs, [h["loss"] for h in val_history], label="Val Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].set_title("Training and Validation Loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(epochs, [h["mean_dice"] for h in train_history], label="Train Mean Dice")
    axes[1].plot(epochs, [h["mean_dice"] for h in val_history], label="Val Mean Dice")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Dice Coefficient")
    axes[1].set_title("Training and Validation Mean Dice")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Training history plot saved to {save_path}")

    plt.close()


def plot_active_learning_curve(
    al_history: List[Dict],
    save_path: Optional[str] = None,
):
    iterations = [h["iteration"] for h in al_history]
    num_labeled = [h["num_labeled"] for h in al_history]
    mean_dice = [h["metrics"]["mean_dice"] for h in al_history]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(iterations, mean_dice, 'b-o', linewidth=2, markersize=8, label='Mean Dice')
    ax1.set_xlabel('Active Learning Iteration')
    ax1.set_ylabel('Mean Dice Coefficient', color='b')
    ax1.tick_params('y', colors='b')
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(iterations, num_labeled, 'r--s', linewidth=2, markersize=8, label='Labeled Samples')
    ax2.set_ylabel('Number of Labeled Samples', color='r')
    ax2.tick_params('y', colors='r')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower right')

    plt.title('Active Learning Performance Curve')
    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Active learning curve saved to {save_path}")

    plt.close()


def visualize_sample(
    image_path: str,
    label_path: Optional[str] = None,
    pred_path: Optional[str] = None,
    output_dir: str = "./output/visualizations",
    class_names: List[str] = ["background", "liver", "kidney_right", "kidney_left", "spleen", "pancreas", "tumor"],
    num_slices: int = 5,
    plot_separate: bool = True,
):
    os.makedirs(output_dir, exist_ok=True)

    image = load_sitk_as_array(image_path)
    base_name = os.path.basename(image_path).replace(".nii.gz", "").replace(".nii", "")

    label = None
    if label_path is not None and os.path.exists(label_path):
        label = load_sitk_as_array(label_path)

    prediction = None
    if pred_path is not None and os.path.exists(pred_path):
        prediction = load_sitk_as_array(pred_path)

    plot_comparison(image, label, prediction, output_dir, base_name, class_names, num_slices)

    if plot_separate and prediction is not None and len(class_names) > 3:
        separate_dir = os.path.join(output_dir, "separate_organs")
        plot_separate_organs(image, prediction, class_names, separate_dir, base_name, num_slices=3)


def visualize_results(
    image_dir: str,
    label_dir: str,
    pred_dir: str,
    output_dir: str = "./output/visualizations",
    class_names: List[str] = ["background", "liver", "kidney_right", "kidney_left", "spleen", "pancreas", "tumor"],
    num_samples: int = 5,
    num_slices: int = 5,
):
    os.makedirs(output_dir, exist_ok=True)

    image_files = sorted([f for f in os.listdir(image_dir) if f.endswith((".nii", ".nii.gz"))])

    if len(image_files) > num_samples:
        image_files = image_files[:num_samples]

    for image_file in image_files:
        base_name = image_file.replace(".nii.gz", "").replace(".nii", "")

        image_path = os.path.join(image_dir, image_file)
        label_path = os.path.join(label_dir, image_file)
        pred_path = os.path.join(pred_dir, f"{base_name}_prediction.nii.gz")

        if not os.path.exists(label_path):
            label_path = None
        if not os.path.exists(pred_path):
            pred_path = None

        sample_output_dir = os.path.join(output_dir, base_name)
        visualize_sample(image_path, label_path, pred_path, sample_output_dir, class_names, num_slices)

    print(f"Visualizations saved to {output_dir}")


if __name__ == "__main__":
    config = Config()

    history_path = os.path.join(config.log_dir, "training_history.json")
    if os.path.exists(history_path):
        plot_training_history(
            history_path,
            save_path=os.path.join(config.result_dir, "training_history.png"),
        )

    al_history_path = os.path.join(config.al_dir, "al_history.json")
    if os.path.exists(al_history_path):
        with open(al_history_path, "r") as f:
            al_history = json.load(f)
        plot_active_learning_curve(
            al_history,
            save_path=os.path.join(config.result_dir, "active_learning_curve.png"),
        )

    visualize_results(
        image_dir=config.image_dir,
        label_dir=config.label_dir,
        pred_dir=config.result_dir,
        output_dir=os.path.join(config.result_dir, "visualizations"),
        class_names=config.class_names,
        num_samples=3,
        num_slices=5,
    )
