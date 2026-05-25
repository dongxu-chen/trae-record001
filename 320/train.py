import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau, CosineAnnealingLR
from torch.cuda.amp import GradScaler, autocast
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime
import json
import gc

from config import Config
from data_loader import create_data_loaders
from augmentation import (
    create_dynamic_train_transforms,
    get_val_transforms,
    AugmentationScheduler,
)
from model import create_model, save_model, load_model
from losses import create_loss_function, SegmentationMetrics


def setup_logging(log_dir: str) -> logging.Logger:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"train_{timestamp}.log")

    logger = logging.getLogger("training")
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


def print_memory_usage(device: torch.device, logger: logging.Logger = None):
    if torch.cuda.is_available() and device.type == "cuda":
        allocated = torch.cuda.memory_allocated() / 1024 ** 3
        cached = torch.cuda.memory_reserved() / 1024 ** 3
        max_allocated = torch.cuda.max_memory_allocated() / 1024 ** 3
        message = f"GPU Memory: {allocated:.2f} GB allocated, {cached:.2f} GB cached, max: {max_allocated:.2f} GB"
        if logger:
            logger.debug(message)
        else:
            print(message)


def clear_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def train_epoch(
    model: nn.Module,
    train_loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    scaler: GradScaler,
    metrics: SegmentationMetrics,
    device: torch.device,
    config: Config,
    epoch: int,
    logger: logging.Logger,
    aug_scheduler: AugmentationScheduler = None,
) -> dict:
    model.train()
    total_loss = 0.0
    metrics.reset()

    if aug_scheduler is not None:
        aug_scheduler.set_epoch(epoch)

    accumulation_steps = config.gradient_accumulation_steps
    optimizer.zero_grad(set_to_none=True)

    pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{config.num_epochs} - Train")
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

        pbar.set_postfix({
            "loss": f"{loss.item() * accumulation_steps:.4f}",
            "lr": f"{optimizer.param_groups[0]['lr']:.2e}",
        })

        if batch_idx % 10 == 0:
            print_memory_usage(device, logger)

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
    metric_results = metrics.compute()

    logger.info(f"Train - Epoch {epoch + 1}: Loss = {avg_loss:.4f}, Mean Dice = {metric_results['mean_dice']:.4f}")
    print_memory_usage(device, logger)

    return {"loss": avg_loss, **metric_results}


def validate_epoch(
    model: nn.Module,
    val_loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    metrics: SegmentationMetrics,
    device: torch.device,
    config: Config,
    epoch: int,
    logger: logging.Logger,
) -> dict:
    model.eval()
    total_loss = 0.0
    metrics.reset()

    with torch.no_grad():
        pbar = tqdm(val_loader, desc=f"Epoch {epoch + 1}/{config.num_epochs} - Val")
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

            total_loss += loss.item()
            metrics.update(outputs, labels)

            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

            clear_memory()

    avg_loss = total_loss / len(val_loader)
    metric_results = metrics.compute()

    logger.info(f"Val - Epoch {epoch + 1}: Loss = {avg_loss:.4f}, Mean Dice = {metric_results['mean_dice']:.4f}")

    return {"loss": avg_loss, **metric_results}


def train(config: Config = None):
    config = config or Config()
    logger = setup_logging(config.log_dir)
    logger.info("Starting 3D Medical Image Segmentation Training")
    logger.info(f"Config: {json.dumps(config.__dict__, indent=2)}")

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        logger.info(f"CUDA available: {torch.cuda.device_count()} devices")
        for i in range(torch.cuda.device_count()):
            logger.info(f"  Device {i}: {torch.cuda.get_device_name(i)}")

    torch.manual_seed(config.random_seed)
    np.random.seed(config.random_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.random_seed)

    train_transforms, aug_scheduler = create_dynamic_train_transforms(config)
    val_transforms = get_val_transforms(config)

    train_loader, val_loader, test_loader = create_data_loaders(
        config,
        train_transform=train_transforms,
        val_transform=val_transforms,
    )

    effective_batch_size = config.batch_size * config.gradient_accumulation_steps
    logger.info(f"Effective batch size: {effective_batch_size} (batch_size={config.batch_size} * accumulation_steps={config.gradient_accumulation_steps})")

    model = create_model(config, use_monai=False)
    model = model.to(device)

    if config.device_ids and len(config.device_ids) > 1:
        model = nn.DataParallel(model, device_ids=config.device_ids)
        logger.info(f"Using DataParallel on devices: {config.device_ids}")

    model_total_params = sum(p.numel() for p in model.parameters())
    model_trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model parameters: {model_total_params:,} total, {model_trainable_params:,} trainable")

    if config.use_checkpoint and not hasattr(model, 'module'):
        logger.info("Using gradient checkpointing to reduce memory usage")

    criterion = create_loss_function(config, loss_type="dice_ce")
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=5,
        verbose=True,
        min_lr=1e-7,
    )
    scaler = GradScaler(
        init_scale=2.0 ** 16,
        growth_factor=2.0,
        backoff_factor=0.5,
        growth_interval=2000,
        enabled=config.use_amp,
    ) if config.use_amp else None

    metrics = SegmentationMetrics(num_classes=config.num_classes, include_background=False)

    start_epoch = 0
    best_val_dice = 0.0
    early_stopping_counter = 0
    history = {"train": [], "val": []}

    resume_path = os.path.join(config.model_dir, "latest_checkpoint.pth")
    if os.path.exists(resume_path):
        logger.info(f"Resuming from checkpoint: {resume_path}")
        model, optimizer, scheduler, start_epoch = load_model(
            model, resume_path, device, optimizer, scheduler
        )

    logger.info("Starting training...")
    for epoch in range(start_epoch, config.num_epochs):
        clear_memory()

        train_metrics = train_epoch(
            model, train_loader, criterion, optimizer, scaler,
            metrics, device, config, epoch, logger, aug_scheduler
        )

        clear_memory()

        val_metrics = validate_epoch(
            model, val_loader, criterion, metrics,
            device, config, epoch, logger
        )

        history["train"].append(train_metrics)
        history["val"].append(val_metrics)

        scheduler.step(val_metrics["mean_dice"])

        if val_metrics["mean_dice"] > best_val_dice:
            best_val_dice = val_metrics["mean_dice"]
            early_stopping_counter = 0
            best_model_path = os.path.join(config.model_dir, "best_model.pth")
            save_model(model, best_model_path, epoch + 1, optimizer, scheduler)
            logger.info(f"New best model saved with Mean Dice: {best_val_dice:.4f}")
        else:
            early_stopping_counter += 1

        if (epoch + 1) % config.save_interval == 0:
            checkpoint_path = os.path.join(config.model_dir, f"checkpoint_epoch_{epoch + 1}.pth")
            save_model(model, checkpoint_path, epoch + 1, optimizer, scheduler)

        latest_path = os.path.join(config.model_dir, "latest_checkpoint.pth")
        save_model(model, latest_path, epoch + 1, optimizer, scheduler)

        if early_stopping_counter >= config.early_stopping_patience:
            logger.info(f"Early stopping triggered after {config.early_stopping_patience} epochs without improvement")
            break

    history_path = os.path.join(config.log_dir, "training_history.json")
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)
    logger.info(f"Training history saved to {history_path}")

    logger.info("Training completed!")
    logger.info(f"Best validation Mean Dice: {best_val_dice:.4f}")

    if torch.cuda.is_available():
        max_mem = torch.cuda.max_memory_allocated() / 1024 ** 3
        logger.info(f"Peak GPU memory usage: {max_mem:.2f} GB")

    return model, history


if __name__ == "__main__":
    config = Config()
    train(config)
