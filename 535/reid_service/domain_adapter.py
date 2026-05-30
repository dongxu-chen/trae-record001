from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from config import ReidConfig

logger = logging.getLogger(__name__)


@dataclass
class AdaptationResult:
    success: bool
    epochs_trained: int
    final_loss: float
    message: str


class DomainAdaptationDataset(Dataset):
    def __init__(
        self,
        features: np.ndarray,
        domain_labels: np.ndarray,
        transform: Callable | None = None,
    ):
        self.features = torch.from_numpy(features.astype(np.float32))
        self.domain_labels = torch.from_numpy(domain_labels.astype(np.int64))
        self.transform = transform

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        feat = self.features[idx]
        label = self.domain_labels[idx]
        if self.transform:
            feat = self.transform(feat)
        return feat, label


class DomainDiscriminator(nn.Module):
    def __init__(self, feature_dim: int, hidden_dim: int = 256, num_domains: int = 2):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, num_domains),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(x)


class GradientReversalLayer(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x: torch.Tensor, alpha: float = 1.0) -> torch.Tensor:
        ctx.alpha = alpha
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor) -> tuple[torch.Tensor, None]:
        output = grad_output.neg() * ctx.alpha
        return output, None


class DomainAdversarialHead(nn.Module):
    def __init__(self, feature_dim: int, num_domains: int = 2):
        super().__init__()
        self.discriminator = DomainDiscriminator(feature_dim, num_domains=num_domains)

    def forward(self, features: torch.Tensor, alpha: float = 1.0) -> torch.Tensor:
        reversed_features = GradientReversalLayer.apply(features, alpha)
        return self.discriminator(reversed_features)


class DomainAdapter:
    def __init__(
        self,
        feature_extractor: nn.Module,
        config: ReidConfig | None = None,
    ):
        self.config = config or ReidConfig()
        self.feature_extractor = feature_extractor
        self.device = torch.device(
            self.config.device if torch.cuda.is_available() else "cpu"
        )
        self.domain_adversarial_head: DomainAdversarialHead | None = None
        self.optimizer: optim.Optimizer | None = None
        self.is_adapted: bool = False
        self.source_domain_stats: dict[str, np.ndarray] = {}
        self.target_domain_stats: dict[str, np.ndarray] = {}

        logger.info(f"DomainAdapter initialized on {self.device}")

    def compute_domain_stats(
        self,
        features: np.ndarray,
        domain_name: str = "source",
    ) -> dict[str, np.ndarray]:
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0)
        stats = {"mean": mean, "std": std}
        if domain_name == "source":
            self.source_domain_stats = stats
        else:
            self.target_domain_stats = stats
        logger.info(
            f"Computed {domain_name} domain stats: "
            f"feature_dim={len(mean)}, samples={len(features)}"
        )
        return stats

    def feature_level_adaptation(
        self,
        features: np.ndarray,
        method: str = "zscore",
    ) -> np.ndarray:
        if not self.source_domain_stats or not self.target_domain_stats:
            logger.warning("Domain stats not computed, returning original features")
            return features

        if method == "zscore":
            src_mean = self.source_domain_stats["mean"]
            src_std = self.source_domain_stats["std"]
            tgt_mean = self.target_domain_stats["mean"]
            tgt_std = self.target_domain_stats["std"]

            src_std_safe = np.where(src_std < 1e-6, 1.0, src_std)
            tgt_std_safe = np.where(tgt_std < 1e-6, 1.0, tgt_std)

            normalized = (features - tgt_mean) / tgt_std_safe
            adapted = normalized * src_std_safe + src_mean
            return adapted

        elif method == "coral":
            return self._coral_adaptation(features)

        return features

    def _coral_adaptation(self, features: np.ndarray) -> np.ndarray:
        if "cov" not in self.source_domain_stats:
            logger.warning("Source covariance not computed, skipping CORAL")
            return features

        src_cov = self.source_domain_stats["cov"]
        tgt_cov = self.target_domain_stats.get("cov")
        if tgt_cov is None:
            logger.warning("Target covariance not computed, skipping CORAL")
            return features

        src_cov_sqrt = self._matrix_sqrt(src_cov)
        tgt_cov_inv_sqrt = self._matrix_inv_sqrt(tgt_cov)
        if src_cov_sqrt is None or tgt_cov_inv_sqrt is None:
            return features

        M = src_cov_sqrt @ tgt_cov_inv_sqrt
        return features @ M

    def _matrix_sqrt(self, matrix: np.ndarray) -> np.ndarray | None:
        try:
            eigvals, eigvecs = np.linalg.eigh(matrix)
            eigvals = np.clip(eigvals, 0, None)
            return eigvecs @ np.diag(np.sqrt(eigvals)) @ eigvecs.T
        except Exception as e:
            logger.error(f"Matrix sqrt failed: {e}")
            return None

    def _matrix_inv_sqrt(self, matrix: np.ndarray) -> np.ndarray | None:
        try:
            eigvals, eigvecs = np.linalg.eigh(matrix)
            eigvals = np.clip(eigvals, 1e-6, None)
            return eigvecs @ np.diag(1.0 / np.sqrt(eigvals)) @ eigvecs.T
        except Exception as e:
            logger.error(f"Matrix inv sqrt failed: {e}")
            return None

    def setup_adversarial_training(
        self,
        num_domains: int = 2,
    ) -> None:
        feature_dim = self.config.feature_dim
        self.domain_adversarial_head = DomainAdversarialHead(
            feature_dim, num_domains
        ).to(self.device)

        params = list(self.feature_extractor.parameters()) + list(
            self.domain_adversarial_head.parameters()
        )
        self.optimizer = optim.SGD(
            params,
            lr=self.config.da_learning_rate,
            momentum=self.config.da_momentum,
        )

        logger.info(
            f"Setup adversarial training: num_domains={num_domains}, "
            f"lr={self.config.da_learning_rate}"
        )

    def adversarial_adaptation(
        self,
        source_images: list[np.ndarray],
        target_images: list[np.ndarray],
        num_epochs: int | None = None,
    ) -> AdaptationResult:
        num_epochs = num_epochs or self.config.da_epochs

        if self.domain_adversarial_head is None:
            self.setup_adversarial_training(num_domains=2)
            assert self.domain_adversarial_head is not None
            assert self.optimizer is not None

        criterion = nn.CrossEntropyLoss()

        all_images = source_images + target_images
        all_labels = [0] * len(source_images) + [1] * len(target_images)

        dataset = SimpleImageDataset(all_images, all_labels)
        dataloader = DataLoader(
            dataset,
            batch_size=self.config.da_batch_size,
            shuffle=True,
            num_workers=0,
        )

        self.feature_extractor.train()
        self.domain_adversarial_head.train()

        total_loss = 0.0
        num_batches = 0

        pbar = tqdm(range(num_epochs), desc="Domain Adaptation")
        for epoch in pbar:
            epoch_loss = 0.0

            for batch_idx, (images, labels) in enumerate(dataloader):
                images = images.to(self.device)
                labels = labels.to(self.device)

                self.optimizer.zero_grad()

                features = self.feature_extractor(images)

                progress = (epoch * len(dataloader) + batch_idx) / (
                    num_epochs * len(dataloader)
                )
                alpha = 2.0 / (1.0 + np.exp(-10.0 * progress)) - 1.0

                domain_preds = self.domain_adversarial_head(features, alpha)
                loss = criterion(domain_preds, labels)

                loss.backward()
                self.optimizer.step()

                epoch_loss += loss.item()
                num_batches += 1

            avg_epoch_loss = epoch_loss / len(dataloader)
            pbar.set_postfix({"loss": f"{avg_epoch_loss:.4f}"})
            total_loss += avg_epoch_loss

        avg_loss = total_loss / num_epochs if num_epochs > 0 else 0.0
        self.is_adapted = True
        self.feature_extractor.eval()

        logger.info(
            f"Adversarial adaptation complete: epochs={num_epochs}, "
            f"final_loss={avg_loss:.4f}"
        )

        return AdaptationResult(
            success=True,
            epochs_trained=num_epochs,
            final_loss=avg_loss,
            message="Domain adaptation completed successfully",
        )

    def incremental_adapt(
        self,
        new_target_features: np.ndarray,
        adaptation_strength: float = 0.1,
    ) -> None:
        if not self.target_domain_stats:
            self.target_domain_stats = {
                "mean": np.mean(new_target_features, axis=0),
                "std": np.std(new_target_features, axis=0),
            }
        else:
            new_mean = np.mean(new_target_features, axis=0)
            new_std = np.std(new_target_features, axis=0)
            self.target_domain_stats["mean"] = (
                1 - adaptation_strength
            ) * self.target_domain_stats["mean"] + adaptation_strength * new_mean
            self.target_domain_stats["std"] = (
                1 - adaptation_strength
            ) * self.target_domain_stats["std"] + adaptation_strength * new_std

        logger.info(
            f"Incremental adaptation updated with {len(new_target_features)} samples"
        )

    def reset_adaptation(self) -> None:
        self.is_adapted = False
        self.source_domain_stats.clear()
        self.target_domain_stats.clear()
        logger.info("Domain adaptation reset")


class SimpleImageDataset(Dataset):
    def __init__(self, images: list[np.ndarray], labels: list[int]):
        from torchvision import transforms

        self.images = images
        self.labels = labels
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 128)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        img = self.images[idx]
        if len(img.shape) == 2:
            import cv2

            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            import cv2

            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        elif img.shape[2] == 3:
            import cv2

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return self.transform(img), self.labels[idx]
