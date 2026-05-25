import os
import torch
import torch.nn as nn
import numpy as np
import SimpleITK as sitk
from tqdm import tqdm
from typing import Tuple, Optional, Dict

from config import Config
from augmentation import get_inference_transforms
from model import create_model, load_model
from post_processing import (
    post_process_segmentation,
    extract_separate_masks,
    save_separate_masks,
)


def preprocess_single_image(image_path: str, config: Config) -> Tuple[torch.Tensor, sitk.Image]:
    transform = get_inference_transforms(config)
    data = {"image": image_path}
    transformed = transform(data)
    image_tensor = transformed["image"].unsqueeze(0)

    original_image = sitk.ReadImage(image_path) if os.path.isfile(image_path) else None

    return image_tensor, original_image


def postprocess_prediction(
    prediction: torch.Tensor,
    original_image: Optional[sitk.Image],
    config: Config,
) -> np.ndarray:
    pred_softmax = torch.softmax(prediction, dim=1)
    pred_mask = torch.argmax(pred_softmax, dim=1)
    pred_mask = pred_mask.squeeze(0).squeeze(0).cpu().numpy().astype(np.uint8)

    if config.use_post_processing:
        pred_mask = post_process_segmentation(pred_mask, config)

    return pred_mask


def predict_single(
    model: nn.Module,
    image_path: str,
    config: Config,
    device: torch.device,
    return_probabilities: bool = False,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    model.eval()

    with torch.no_grad():
        image_tensor, original_image = preprocess_single_image(image_path, config)
        image_tensor = image_tensor.to(device)

        prediction = model(image_tensor)
        pred_mask = postprocess_prediction(prediction, original_image, config)

        prob_map = None
        if return_probabilities:
            prob_map = torch.softmax(prediction, dim=1).squeeze(0).cpu().numpy()

    return pred_mask, prob_map


def save_prediction(
    pred_mask: np.ndarray,
    output_path: str,
    reference_image: Optional[sitk.Image] = None,
):
    pred_image = sitk.GetImageFromArray(pred_mask)

    if reference_image is not None:
        pred_image.CopyInformation(reference_image)

    sitk.WriteImage(pred_image, output_path)
    print(f"Prediction saved to {output_path}")


def run_inference(
    image_paths: list,
    model_path: str,
    output_dir: str,
    config: Config = None,
    save_separate: bool = None,
):
    config = config or Config()
    os.makedirs(output_dir, exist_ok=True)

    if save_separate is None:
        save_separate = config.save_separate_masks

    if save_separate:
        separate_masks_dir = os.path.join(output_dir, "separate_masks")
        os.makedirs(separate_masks_dir, exist_ok=True)

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = create_model(config, use_monai=False)
    model = model.to(device)

    print(f"Loading model from {model_path}")
    model, _, _, _ = load_model(model, model_path, device)

    if config.multi_organ:
        print(f"Multi-organ segmentation enabled. Classes: {config.class_names}")

    if config.use_post_processing:
        print(f"Post-processing enabled: hole filling (<{config.min_hole_size} voxels), "
              f"small object removal (<{config.min_object_size} voxels)")

    print(f"Running inference on {len(image_paths)} images...")

    for image_path in tqdm(image_paths, desc="Inference"):
        image_name = os.path.basename(image_path)
        if image_name.endswith(".nii.gz"):
            base_name = image_name[:-7]
        elif image_name.endswith(".nii"):
            base_name = image_name[:-4]
        else:
            base_name = os.path.splitext(image_name)[0]

        pred_mask, prob_map = predict_single(model, image_path, config, device, return_probabilities=True)

        output_path = os.path.join(output_dir, f"{base_name}_prediction.nii.gz")
        reference_image = sitk.ReadImage(image_path) if os.path.isfile(image_path) else None
        save_prediction(pred_mask, output_path, reference_image)

        if save_separate and config.multi_organ:
            separate_masks = extract_separate_masks(pred_mask, config.class_names)
            save_separate_masks(
                separate_masks,
                separate_masks_dir,
                base_name,
                reference_image,
            )
            print(f"  Separate masks saved for {len(separate_masks)} organs")

        if prob_map is not None:
            prob_output_path = os.path.join(output_dir, f"{base_name}_probabilities.npz")
            np.savez_compressed(prob_output_path, probabilities=prob_map)

    print("Inference completed!")


def generate_pseudo_labels(
    model: nn.Module,
    image_paths: list,
    output_dir: str,
    config: Config,
    device: torch.device,
    threshold: float = 0.7,
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    pseudo_label_paths = []

    model.eval()

    for image_path in tqdm(image_paths, desc="Generating pseudo-labels"):
        try:
            pred_mask, prob_map = predict_single(model, image_path, config, device, return_probabilities=True)

            if prob_map is not None:
                max_prob = np.max(prob_map, axis=0)
                high_confidence = np.mean(max_prob > threshold)

                if high_confidence < 0.5:
                    print(f"  Skipping {os.path.basename(image_path)}: low confidence ({high_confidence:.3f})")
                    continue

            image_name = os.path.basename(image_path)
            if image_name.endswith(".nii.gz"):
                base_name = image_name[:-7]
            else:
                base_name = os.path.splitext(image_name)[0]

            output_path = os.path.join(output_dir, f"{base_name}_pseudo.nii.gz")
            reference_image = sitk.ReadImage(image_path) if os.path.isfile(image_path) else None
            save_prediction(pred_mask, output_path, reference_image)
            pseudo_label_paths.append(output_path)

        except Exception as e:
            print(f"  Error processing {image_path}: {e}")

    print(f"Generated {len(pseudo_label_paths)} pseudo-labels")
    return pseudo_label_paths


def main():
    config = Config()

    image_dir = config.image_dir
    image_paths = []
    for f in os.listdir(image_dir):
        if f.endswith((".nii", ".nii.gz", ".mhd")):
            image_paths.append(os.path.join(image_dir, f))

    model_path = os.path.join(config.model_dir, "best_model.pth")
    output_dir = config.result_dir

    run_inference(image_paths, model_path, output_dir, config)


if __name__ == "__main__":
    main()
