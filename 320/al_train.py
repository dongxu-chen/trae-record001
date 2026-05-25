import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.cuda.amp import GradScaler, autocast
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime
import json
import gc

from config import Config
from data_loader import (
    get_file_paths,
    split_dataset,
    create_data_loaders_from_paths,
    get_inference_transforms,
)
from augmentation import get_val_transforms, create_dynamic_train_transforms
from model import create_model, save_model, load_model
from losses import create_loss_function, SegmentationMetrics, MultiOrganEvaluator
from active_learning import ActiveLearningLoop
from visualize import plot_active_learning_curve


def setup_logging(log_dir: str) -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"al_train_{timestamp}.log")

    logger = logging.getLogger("active_learning")
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


def clear_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def train_one_round(
    model: nn.Module,
    train_loader,
    val_loader,
    criterion,
    optimizer,
    scheduler,
    scaler,
    metrics,
    device,
    config,
    logger,
    aug_scheduler,
    num_epochs: int = None,
) -> Tuple[nn.Module, Dict[str, float]]:
    if num_epochs is None:
        num_epochs = config.num_epochs

    best_val_dice = 0.0
    early_stopping_counter = 0

    for epoch in range(num_epochs):
        clear_memory()
        model.train()
        total_loss = 0.0
        metrics.reset()

        if aug_scheduler is not None:
            aug_scheduler.set_epoch(epoch)

        accumulation_steps = config.gradient_accumulation_steps
        optimizer.zero_grad(set_to_none=True)

        pbar = tqdm(train_loader, desc=f"Round Train Epoch {epoch + 1}/{num_epochs}")
        for batch_idx, batch_data in enumerate(pbar):
            images = batch_data["image"].to(device, non_blocking=True)
            labels = batch_data["label"].to(device, non_blocking=True)

            if config.use_amp:
                with autocast(dtype=torch.float16):
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    loss = loss / accumulation_steps

                scaler.scale(loss).backward()

                if (batch_idx + 1) % accumulation_steps == 0:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_val)
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad(set_to_none=True)
                    clear_memory()
            else:
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss = loss / accumulation_steps
                loss.backward()

                if (batch_idx + 1) % accumulation_steps == 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_val)
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    clear_memory()

            total_loss += loss.item() * accumulation_steps
            metrics.update(outputs.detach(), labels.detach())
            pbar.set_postfix({"loss": f"{loss.item() * accumulation_steps:.4f}"})

        if (batch_idx + 1) % accumulation_steps != 0:
            if config.use_amp:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_val)
                scaler.step(optimizer)
                scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip_val)
                optimizer.step()
            optimizer.zero_grad(set_to_none=True)

        avg_loss = total_loss / len(train_loader)
        train_metrics = metrics.compute()

        clear_memory()
        model.eval()
        val_loss = 0.0
        metrics.reset()

        with torch.no_grad():
            pbar = tqdm(val_loader, desc=f"Round Val Epoch {epoch + 1}/{num_epochs}")
            for batch_data in pbar:
                images = batch_data["image"].to(device, non_blocking=True)
                labels = batch_data["label"].to(device, non_blocking=True)

                if config.use_amp:
                    with autocast(dtype=torch.float16):
                        outputs = model(images)
                        loss = criterion(outputs, labels)
                else:
                    outputs = model(images)
                    loss = criterion(outputs, labels)

                val_loss += loss.item()
                metrics.update(outputs, labels)
                pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        val_avg_loss = val_loss / len(val_loader)
        val_metrics = metrics.compute()

        scheduler.step(val_metrics["mean_dice"])

        logger.info(
            f"Epoch {epoch + 1}: Train Loss={avg_loss:.4f}, Train Dice={train_metrics['mean_dice']:.4f}, "
            f"Val Loss={val_avg_loss:.4f}, Val Dice={val_metrics['mean_dice']:.4f}"
        )

        if val_metrics["mean_dice"] > best_val_dice:
            best_val_dice = val_metrics["mean_dice"]
            early_stopping_counter = 0
        else:
            early_stopping_counter += 1

        if early_stopping_counter >= config.early_stopping_patience:
            logger.info(f"Early stopping at epoch {epoch + 1}")
            break

    return model, val_metrics


def evaluate_model(
    model: nn.Module,
    test_loader,
    device: torch.device,
    config: Config,
    logger: logging.Logger,
) -> Dict[str, float]:
    evaluator = MultiOrganEvaluator(config.class_names, include_background=False)

    model.eval()
    with torch.no_grad():
        for batch_data in tqdm(test_loader, desc="Evaluating"):
            images = batch_data["image"].to(device)
            labels = batch_data["label"].to(device)
            outputs = model(images)
            evaluator.update(outputs, labels)

    results = evaluator.compute()
    evaluator.print_summary()

    mean_dice = np.mean([m["mean_dice"] for m in results.values()])
    logger.info(f"Overall Mean Dice: {mean_dice:.4f}")

    return {"mean_dice": mean_dice, **{k: v["mean_dice"] for k, v in results.items()}}


def active_learning_pipeline(config: Config = None):
    config = config or Config()
    logger = setup_logging(config.log_dir)
    logger.info("=" * 80)
    logger.info("ACTIVE LEARNING PIPELINE FOR 3D MEDICAL IMAGE SEGMENTATION")
    logger.info("=" * 80)

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        logger.info(f"CUDA devices: {torch.cuda.device_count()}")

    torch.manual_seed(config.random_seed)
    np.random.seed(config.random_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.random_seed)

    image_paths = get_file_paths(config.image_dir)
    label_paths = get_file_paths(config.label_dir)
    logger.info(f"Found {len(image_paths)} images and {len(label_paths)} labels")

    (train_images, train_labels), (val_images, val_labels), (test_images, test_labels) = split_dataset(
        image_paths,
        label_paths,
        val_split=config.val_split,
        test_split=config.test_split,
        random_seed=config.random_seed,
    )

    all_train_images = train_images
    all_train_labels = train_labels

    al_loop = ActiveLearningLoop(config, all_train_images, all_train_labels)
    initial_labeled_images, initial_labeled_labels = al_loop.initialize_labeled_set()

    logger.info(f"Initial labeled set: {len(initial_labeled_images)} samples")
    logger.info(f"Unlabeled pool: {len(al_loop.unlabeled_indices)} samples")

    al_history = []
    train_transforms, aug_scheduler = create_dynamic_train_transforms(config)
    val_transforms = get_val_transforms(config)

    val_loader, _, test_loader = create_data_loaders_from_paths(
        config,
        [], [],
        val_images, val_labels,
        test_images, test_labels,
        train_transforms, val_transforms,
    )
    _, _, test_loader = create_data_loaders_from_paths(
        config,
        [], [],
        [], [],
        test_images, test_labels,
        train_transforms, val_transforms,
    )

    for al_iteration in range(config.al_num_iterations):
        logger.info("\n" + "=" * 80)
        logger.info(f"ACTIVE LEARNING ITERATION {al_iteration + 1}/{config.al_num_iterations}")
        logger.info("=" * 80)

        labeled_images, labeled_labels = al_loop.get_labeled_data()
        logger.info(f"Labeled samples: {len(labeled_images)}")

        if len(labeled_labels) == 0:
            logger.error("No labeled samples available. Skipping training.")
            break

        train_loader, _, _ = create_data_loaders_from_paths(
            config,
            labeled_images, labeled_labels,
            val_images, val_labels,
            test_images, test_labels,
            train_transforms, val_transforms,
        )

        model = create_model(config, use_monai=False)
        model = model.to(device)

        criterion = create_loss_function(config, loss_type="dice_ce")
        optimizer = optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        scheduler = ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=3,
            verbose=True,
            min_lr=1e-7,
        )
        scaler = GradScaler(enabled=config.use_amp) if config.use_amp else None
        metrics = SegmentationMetrics(num_classes=config.num_classes, include_background=False)

        epochs_per_round = max(20, config.num_epochs // config.al_num_iterations)
        logger.info(f"Training for {epochs_per_round} epochs...")

        model, val_metrics = train_one_round(
            model, train_loader, val_loader,
            criterion, optimizer, scheduler, scaler,
            metrics, device, config, logger,
            aug_scheduler, num_epochs=epochs_per_round,
        )

        model_save_path = os.path.join(config.model_dir, f"al_model_iter_{al_iteration}.pth")
        save_model(model, model_save_path, epoch=epochs_per_round, optimizer=optimizer, scheduler=scheduler)

        logger.info("Evaluating on test set...")
        test_metrics = evaluate_model(model, test_loader, device, config, logger)

        al_loop.record_iteration(test_metrics, num_newly_labeled=0)
        al_history.append(al_loop.history[-1])

        if al_iteration < config.al_num_iterations - 1:
            logger.info(f"\nSelecting {config.al_num_queries_per_iter} samples for annotation...")
            selected_paths = al_loop.select_samples_for_labeling(
                model, device, num_samples=config.al_num_queries_per_iter
            )

            logger.info("Selected samples:")
            for path in selected_paths:
                logger.info(f"  - {os.path.basename(path)}")

            newly_labeled = al_loop.add_labeled_samples(selected_paths)
            al_history[-1]["num_newly_labeled"] = len(newly_labeled)
            logger.info(f"Newly labeled: {len(newly_labeled)} samples")

            if len(al_loop.unlabeled_indices) == 0:
                logger.info("All samples have been labeled. Stopping active learning.")
                break

        al_loop.save_state(config.al_dir)

        al_history_path = os.path.join(config.al_dir, "al_history.json")
        with open(al_history_path, "w") as f:
            json.dump(al_history, f, indent=2)
        logger.info(f"Active learning history saved to {al_history_path}")

    plot_active_learning_curve(
        al_history,
        save_path=os.path.join(config.result_dir, "active_learning_curve.png"),
    )

    best_iteration = np.argmax([h["metrics"]["mean_dice"] for h in al_history])
    best_dice = al_history[best_iteration]["metrics"]["mean_dice"]
    logger.info("\n" + "=" * 80)
    logger.info("ACTIVE LEARNING PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Best iteration: {best_iteration + 1}")
    logger.info(f"Best Mean Dice: {best_dice:.4f}")
    logger.info(f"Total labeled samples used: {al_loop.get_statistics()['labeled_samples']}")
    logger.info("=" * 80)

    return al_history


if __name__ == "__main__":
    config = Config()
    active_learning_pipeline(config)
