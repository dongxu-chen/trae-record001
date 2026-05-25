import torch
import torch.nn as nn
import torch.nn.functional as F
from monai.losses import DiceLoss, FocalLoss, GeneralizedDiceLoss
from monai.metrics import DiceMetric, HausdorffDistanceMetric, MeanIoU
from typing import Dict, List, Tuple
import numpy as np
from config import Config


class DiceCoefficient(nn.Module):
    def __init__(self, smooth: float = 1e-7, ignore_background: bool = True):
        super().__init__()
        self.smooth = smooth
        self.ignore_background = ignore_background

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        inputs = F.softmax(inputs, dim=1)
        inputs = torch.argmax(inputs, dim=1)

        if self.ignore_background:
            inputs = inputs[:, 1:, ...] if inputs.dim() == 4 else inputs
            targets = targets[:, 1:, ...] if targets.dim() == 4 else targets

        inputs = inputs.contiguous().view(-1)
        targets = targets.contiguous().view(-1)

        intersection = (inputs * targets).sum()
        dice = (2.0 * intersection + self.smooth) / (inputs.sum() + targets.sum() + self.smooth)

        return dice


class DiceCELoss(nn.Module):
    def __init__(self, lambda_dice: float = 1.0, lambda_ce: float = 1.0, smooth: float = 1e-7):
        super().__init__()
        self.lambda_dice = lambda_dice
        self.lambda_ce = lambda_ce
        self.ce_loss = nn.CrossEntropyLoss()
        self.dice_loss = DiceLoss(to_onehot_y=True, softmax=True, smooth_nr=smooth, smooth_dr=smooth)

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        targets = targets.long()
        ce = self.ce_loss(inputs, targets.squeeze(1))
        dice = self.dice_loss(inputs, targets)
        loss = self.lambda_dice * dice + self.lambda_ce * ce
        return loss


class TverskyLoss(nn.Module):
    def __init__(self, alpha: float = 0.3, beta: float = 0.7, smooth: float = 1e-7):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.smooth = smooth

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        inputs = F.softmax(inputs, dim=1)
        targets = F.one_hot(targets.squeeze(1).long(), num_classes=inputs.shape[1])
        targets = targets.permute(0, 4, 1, 2, 3).contiguous().float()

        inputs = inputs.view(-1)
        targets = targets.view(-1)

        true_pos = (inputs * targets).sum()
        false_neg = (targets * (1 - inputs)).sum()
        false_pos = ((1 - targets) * inputs).sum()

        tversky = (true_pos + self.smooth) / (
            true_pos + self.alpha * false_pos + self.beta * false_neg + self.smooth
        )

        return 1 - tversky


class WeightedDiceCELoss(nn.Module):
    def __init__(
        self,
        class_weights: Optional[List[float]] = None,
        lambda_dice: float = 1.0,
        lambda_ce: float = 1.0,
        smooth: float = 1e-7,
        num_classes: int = 7,
    ):
        super().__init__()
        self.lambda_dice = lambda_dice
        self.lambda_ce = lambda_ce
        self.num_classes = num_classes

        if class_weights is not None:
            self.class_weights = torch.tensor(class_weights, dtype=torch.float32)
        else:
            self.class_weights = None

        self.ce_loss = nn.CrossEntropyLoss(weight=self.class_weights)
        self.dice_loss = DiceLoss(
            to_onehot_y=True,
            softmax=True,
            smooth_nr=smooth,
            smooth_dr=smooth,
            weight=self.class_weights,
        )

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        targets = targets.long()
        ce = self.ce_loss(inputs, targets.squeeze(1))
        dice = self.dice_loss(inputs, targets)
        loss = self.lambda_dice * dice + self.lambda_ce * ce
        return loss


def create_loss_function(
    config: Config,
    loss_type: str = "dice_ce",
    use_class_weights: bool = True,
) -> nn.Module:
    if use_class_weights and config.multi_organ:
        class_weights = [0.1] + [1.0] * (config.num_classes - 1)
        class_weights = torch.tensor(class_weights, dtype=torch.float32)
    else:
        class_weights = None

    if loss_type == "dice":
        return DiceLoss(
            to_onehot_y=True,
            softmax=True,
            weight=class_weights,
        )
    elif loss_type == "ce":
        return nn.CrossEntropyLoss(weight=class_weights)
    elif loss_type == "dice_ce":
        if class_weights is not None:
            return WeightedDiceCELoss(
                class_weights=class_weights.tolist(),
                num_classes=config.num_classes,
            )
        else:
            return DiceCELoss()
    elif loss_type == "focal":
        return FocalLoss(to_onehot_y=True, gamma=2.0, weight=class_weights)
    elif loss_type == "generalized_dice":
        return GeneralizedDiceLoss(to_onehot_y=True, softmax=True)
    elif loss_type == "tversky":
        return TverskyLoss()
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")


class SegmentationMetrics:
    def __init__(self, num_classes: int = 3, include_background: bool = False):
        self.num_classes = num_classes
        self.include_background = include_background
        self.dice_metric = DiceMetric(
            include_background=include_background,
            reduction="mean_batch",
            get_not_nans=False,
        )
        self.hd95_metric = HausdorffDistanceMetric(
            include_background=include_background,
            percentile=95,
            reduction="mean_batch",
            get_not_nans=False,
        )
        self.iou_metric = MeanIoU(
            include_background=include_background,
            reduction="mean_batch",
            get_not_nans=False,
        )
        self.reset()

    def reset(self):
        self.dice_metric.reset()
        self.hd95_metric.reset()
        self.iou_metric.reset()

    def update(self, y_pred: torch.Tensor, y: torch.Tensor):
        y_pred = F.softmax(y_pred, dim=1)
        y = y.long()
        self.dice_metric(y_pred=y_pred, y=y)
        self.hd95_metric(y_pred=y_pred, y=y)
        self.iou_metric(y_pred=y_pred, y=y)

    def compute(self) -> Dict[str, float]:
        dice = self.dice_metric.aggregate().cpu().numpy()
        hd95 = self.hd95_metric.aggregate().cpu().numpy()
        iou = self.iou_metric.aggregate().cpu().numpy()

        start_idx = 0 if self.include_background else 1
        metrics = {}

        for i in range(start_idx, self.num_classes):
            class_idx = i - start_idx
            metrics[f"dice_class_{i}"] = float(dice[class_idx]) if class_idx < len(dice) else 0.0
            metrics[f"hd95_class_{i}"] = float(hd95[class_idx]) if class_idx < len(hd95) else 0.0
            metrics[f"iou_class_{i}"] = float(iou[class_idx]) if class_idx < len(iou) else 0.0

        metrics["mean_dice"] = float(np.mean(dice)) if len(dice) > 0 else 0.0
        metrics["mean_hd95"] = float(np.mean(hd95)) if len(hd95) > 0 else 0.0
        metrics["mean_iou"] = float(np.mean(iou)) if len(iou) > 0 else 0.0

        return metrics

    def compute_per_class(self, class_names: List[str]) -> Dict[str, Dict[str, float]]:
        dice = self.dice_metric.aggregate().cpu().numpy()
        hd95 = self.hd95_metric.aggregate().cpu().numpy()
        iou = self.iou_metric.aggregate().cpu().numpy()

        start_idx = 0 if self.include_background else 1
        results = {}

        for i in range(start_idx, self.num_classes):
            class_idx = i - start_idx
            class_name = class_names[i] if i < len(class_names) else f"class_{i}"
            results[class_name] = {
                "dice": float(dice[class_idx]) if class_idx < len(dice) else 0.0,
                "hd95": float(hd95[class_idx]) if class_idx < len(hd95) else 0.0,
                "iou": float(iou[class_idx]) if class_idx < len(iou) else 0.0,
            }

        return results


def calculate_batch_dice(outputs: torch.Tensor, labels: torch.Tensor, num_classes: int) -> np.ndarray:
    outputs = F.softmax(outputs, dim=1)
    outputs = torch.argmax(outputs, dim=1).cpu().numpy()
    labels = labels.squeeze(1).cpu().numpy().astype(int)

    dice_scores = np.zeros(num_classes)
    smooth = 1e-7

    for cls in range(num_classes):
        pred_mask = (outputs == cls)
        true_mask = (labels == cls)

        intersection = np.sum(pred_mask & true_mask)
        union = np.sum(pred_mask) + np.sum(true_mask)

        dice_scores[cls] = (2.0 * intersection + smooth) / (union + smooth)

    return dice_scores


class MultiOrganEvaluator:
    def __init__(self, class_names: List[str], include_background: bool = False):
        self.class_names = class_names
        self.num_classes = len(class_names)
        self.include_background = include_background
        self.reset()

    def reset(self):
        self.metrics = {name: {"dice": [], "iou": [], "hd95": [], "precision": [], "recall": []}
                        for name in self.class_names}
        if not self.include_background:
            self.metrics.pop(self.class_names[0], None)

    def _calculate_metrics(self, pred: np.ndarray, target: np.ndarray, cls: int) -> Dict[str, float]:
        pred_mask = (pred == cls)
        target_mask = (target == cls)

        smooth = 1e-7

        intersection = np.sum(pred_mask & target_mask)
        union = np.sum(pred_mask | target_mask)
        dice = (2.0 * intersection + smooth) / (np.sum(pred_mask) + np.sum(target_mask) + smooth)
        iou = (intersection + smooth) / (union + smooth)

        precision = (intersection + smooth) / (np.sum(pred_mask) + smooth)
        recall = (intersection + smooth) / (np.sum(target_mask) + smooth)

        from scipy.spatial.distance import directed_hausdorff
        pred_coords = np.array(np.where(pred_mask)).T
        target_coords = np.array(np.where(target_mask)).T

        if len(pred_coords) > 0 and len(target_coords) > 0:
            d1 = directed_hausdorff(pred_coords, target_coords)[0]
            d2 = directed_hausdorff(target_coords, pred_coords)[0]
            hd95 = max(d1, d2)
        else:
            hd95 = np.nan

        return {
            "dice": float(dice),
            "iou": float(iou),
            "hd95": float(hd95),
            "precision": float(precision),
            "recall": float(recall),
        }

    def update(self, outputs: torch.Tensor, targets: torch.Tensor):
        outputs = F.softmax(outputs, dim=1)
        preds = torch.argmax(outputs, dim=1).cpu().numpy()
        targets = targets.squeeze(1).cpu().numpy().astype(int)

        start_idx = 0 if self.include_background else 1

        for i in range(start_idx, self.num_classes):
            class_name = self.class_names[i]
            batch_metrics = self._calculate_metrics(preds, targets, i)
            for metric_name, value in batch_metrics.items():
                if not np.isnan(value):
                    self.metrics[class_name][metric_name].append(value)

    def compute(self) -> Dict[str, Dict[str, float]]:
        results = {}
        for class_name, class_metrics in self.metrics.items():
            results[class_name] = {}
            for metric_name, values in class_metrics.items():
                if len(values) > 0:
                    results[class_name][f"mean_{metric_name}"] = float(np.mean(values))
                    results[class_name][f"std_{metric_name}"] = float(np.std(values))
                else:
                    results[class_name][f"mean_{metric_name}"] = 0.0
                    results[class_name][f"std_{metric_name}"] = 0.0
        return results

    def print_summary(self):
        results = self.compute()
        print("\n" + "=" * 80)
        print("MULTI-ORGAN SEGMENTATION RESULTS")
        print("=" * 80)
        print(f"{'Organ':15s} {'Dice':>10s} {'IoU':>10s} {'HD95':>10s} {'Prec.':>10s} {'Recall':>10s}")
        print("-" * 80)

        for class_name, metrics in results.items():
            print(
                f"{class_name:15s} "
                f"{metrics['mean_dice']:10.4f} "
                f"{metrics['mean_iou']:10.4f} "
                f"{metrics['mean_hd95']:10.2f} "
                f"{metrics['mean_precision']:10.4f} "
                f"{metrics['mean_recall']:10.4f}"
            )

        print("-" * 80)
        mean_dice = np.mean([m["mean_dice"] for m in results.values()])
        mean_iou = np.mean([m["mean_iou"] for m in results.values()])
        print(
            f"{'AVERAGE':15s} "
            f"{mean_dice:10.4f} "
            f"{mean_iou:10.4f} "
            f"{'':10s} {'':10s} {'':10s}"
        )
        print("=" * 80 + "\n")
