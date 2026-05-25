import os
import torch
import torch.nn as nn
import numpy as np
import json
import logging
from tqdm import tqdm
from datetime import datetime
from typing import Dict, List

from config import Config
from data_loader import create_data_loaders
from augmentation import get_val_transforms
from model import create_model, load_model
from losses import SegmentationMetrics, calculate_batch_dice


def setup_logging(log_dir: str) -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"evaluate_{timestamp}.log")

    logger = logging.getLogger("evaluation")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def evaluate(
    model: nn.Module,
    test_loader: torch.utils.data.DataLoader,
    metrics: SegmentationMetrics,
    device: torch.device,
    config: Config,
    logger: logging.Logger,
) -> Dict[str, float]:
    model.eval()
    metrics.reset()
    all_dice_scores = []

    logger.info("Starting evaluation...")

    with torch.no_grad():
        pbar = tqdm(test_loader, desc="Evaluating")
        for batch_idx, batch_data in enumerate(pbar):
            images = batch_data["image"].to(device)
            labels = batch_data["label"].to(device)

            outputs = model(images)
            metrics.update(outputs, labels)

            batch_dice = calculate_batch_dice(outputs, labels, config.num_classes)
            all_dice_scores.append(batch_dice)

            mean_batch_dice = np.mean(batch_dice[1:]) if config.num_classes > 1 else np.mean(batch_dice)
            pbar.set_postfix({"mean_dice": f"{mean_batch_dice:.4f}"})

    metric_results = metrics.compute()
    per_class_results = metrics.compute_per_class(config.class_names)

    all_dice_scores = np.array(all_dice_scores)
    mean_dice_per_class = np.mean(all_dice_scores, axis=0)
    std_dice_per_class = np.std(all_dice_scores, axis=0)

    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)

    for i in range(config.num_classes):
        class_name = config.class_names[i] if i < len(config.class_names) else f"class_{i}"
        logger.info(
            f"{class_name:15s} - Dice: {mean_dice_per_class[i]:.4f} ± {std_dice_per_class[i]:.4f}"
        )

    logger.info("-" * 60)
    logger.info(f"Overall Mean Dice: {metric_results['mean_dice']:.4f}")
    logger.info(f"Overall Mean HD95: {metric_results['mean_hd95']:.4f}")
    logger.info(f"Overall Mean IoU: {metric_results['mean_iou']:.4f}")
    logger.info("=" * 60)

    logger.info("\nDetailed Metrics:")
    for class_name, metrics_dict in per_class_results.items():
        logger.info(
            f"{class_name:15s} - Dice: {metrics_dict['dice']:.4f}, "
            f"HD95: {metrics_dict['hd95']:.4f}, IoU: {metrics_dict['iou']:.4f}"
        )

    return metric_results


def main(config: Config = None, model_path: str = None):
    config = config or Config()
    logger = setup_logging(config.log_dir)

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    val_transforms = get_val_transforms(config)
    _, _, test_loader = create_data_loaders(config, val_transform=val_transforms)

    model = create_model(config, use_monai=True)
    model = model.to(device)

    if model_path is None:
        model_path = os.path.join(config.model_dir, "best_model.pth")

    if not os.path.exists(model_path):
        logger.error(f"Model not found at {model_path}")
        return None

    logger.info(f"Loading model from {model_path}")
    model, _, _, _ = load_model(model, model_path, device)

    metrics = SegmentationMetrics(num_classes=config.num_classes, include_background=False)

    results = evaluate(model, test_loader, metrics, device, config, logger)

    results_path = os.path.join(config.result_dir, "evaluation_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)
    logger.info(f"Results saved to {results_path}")

    return results


if __name__ == "__main__":
    config = Config()
    main(config)
