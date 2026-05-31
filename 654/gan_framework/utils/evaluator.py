import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
from torchvision.models import inception_v3, Inception_V3_Weights
from scipy import linalg


class InceptionFeatureExtractor(nn.Module):
    def __init__(self):
        super().__init__()
        weights = Inception_V3_Weights.DEFAULT
        inception = inception_v3(weights=weights)
        self.transform_input = False
        self.inception = nn.Sequential(*list(inception.children())[:-1])
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.feature_dim = 2048
        for p in self.parameters():
            p.requires_grad_(False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.size(1) == 1:
            x = x.repeat(1, 3, 1, 1)
        if x.shape[2] != 299 or x.shape[3] != 299:
            x = nn.functional.interpolate(x, size=(299, 299), mode="bilinear", align_corners=False)
        x = (x + 1) / 2.0
        x = x.clamp(0, 1)
        x = x * 2 - 1
        h = self.inception(x)
        if h.ndim == 4:
            h = self.pool(h)
        return h.view(h.size(0), -1)


def calculate_frechet_distance(mu1: np.ndarray, sigma1: np.ndarray,
                               mu2: np.ndarray, sigma2: np.ndarray) -> float:
    mu1 = np.atleast_1d(mu1)
    mu2 = np.atleast_1d(mu2)
    sigma1 = np.atleast_2d(sigma1)
    sigma2 = np.atleast_2d(sigma2)
    diff = mu1 - mu2
    covmean, _ = linalg.sqrtm(sigma1.dot(sigma2), disp=False)
    if not np.isfinite(covmean).all():
        offset = np.eye(sigma1.shape[0]) * 1e-6
        covmean = linalg.sqrtm((sigma1 + offset).dot(sigma2 + offset))
    if np.iscomplexobj(covmean):
        covmean = covmean.real
    tr_covmean = np.trace(covmean)
    return float(diff.dot(diff) + np.trace(sigma1) + np.trace(sigma2) - 2 * tr_covmean)


def calculate_kid(features_real: np.ndarray, features_fake: np.ndarray,
                  subset_size: int = 1000, num_subsets: int = 100) -> float:
    n = min(features_real.shape[0], features_fake.shape[0], subset_size)
    m = subset_size
    scores = []
    for _ in range(num_subsets):
        idx1 = np.random.choice(features_real.shape[0], n, replace=False)
        idx2 = np.random.choice(features_fake.shape[0], n, replace=False)
        f1 = features_real[idx1]
        f2 = features_fake[idx2]

        m = f1.shape[0]
        n = f2.shape[0]
        s1 = (f1 @ f1.T).sum() / (m * (m - 1))
        s2 = (f2 @ f2.T).sum() / (n * (n - 1))
        s3 = (f1 @ f2.T).sum() / (m * n)
        scores.append(s1 + s2 - 2 * s3)
    return float(np.mean(scores) * 1000.0)


class GANEvaluator:
    def __init__(self, config, device: torch.device):
        self.config = config
        self.device = device
        self.inception = InceptionFeatureExtractor().eval().to(device)
        self.transform = transforms.Compose([
            transforms.Resize(config.img_size),
            transforms.CenterCrop(config.img_size),
            transforms.ToTensor(),
            transforms.Normalize([0.5] * config.img_channels, [0.5] * config.img_channels),
        ])
        self._real_stats_cached = None
        self._real_features_cached = None

    def _get_real_dataloader(self) -> DataLoader:
        config = self.config
        if config.dataset == "cifar10":
            dataset = datasets.CIFAR10(root=config.data_root, train=True, download=True, transform=self.transform)
        elif config.dataset == "mnist":
            dataset = datasets.MNIST(root=config.data_root, train=True, download=True, transform=self.transform)
        elif config.dataset == "stl10":
            dataset = datasets.STL10(root=config.data_root, split="train", download=True, transform=self.transform)
        elif config.dataset == "folder":
            dataset = datasets.ImageFolder(root=config.data_root, transform=self.transform)
        else:
            raise ValueError(f"Unknown dataset: {config.dataset}")
        return DataLoader(dataset, batch_size=self.config.fid_batch_size,
                          shuffle=False, num_workers=self.config.num_workers,
                          pin_memory=True, drop_last=False)

    def compute_real_features(self, num_samples: int = None):
        if num_samples is None:
            num_samples = self.config.fid_num_samples
        if self._real_stats_cached is not None:
            return self._real_stats_cached, self._real_features_cached
        dataloader = self._get_real_dataloader()
        features = []
        count = 0
        with torch.no_grad():
            for real_images, _ in dataloader:
                real_images = real_images.to(self.device)
                feat = self.inception(real_images)
                features.append(feat.cpu().numpy())
                count += real_images.size(0)
                if count >= num_samples:
                    break
        features = np.concatenate(features, axis=0)[:num_samples]
        mu = np.mean(features, axis=0)
        sigma = np.cov(features, rowvar=False)
        self._real_stats_cached = (mu, sigma)
        self._real_features_cached = features
        return (mu, sigma), features

    def compute_fake_features(self, generator, num_samples: int = None, use_ema: bool = False, ema_g=None):
        if num_samples is None:
            num_samples = self.config.fid_num_samples
        g = ema_g.ema if (use_ema and ema_g is not None) else generator
        g.eval()
        features = []
        batch_size = self.config.fid_batch_size
        count = 0
        with torch.no_grad():
            while count < num_samples:
                z = torch.randn(min(batch_size, num_samples - count), self.config.z_dim, device=self.device)
                fake = g(z)
                feat = self.inception(fake)
                features.append(feat.cpu().numpy())
                count += z.size(0)
        g.train()
        features = np.concatenate(features, axis=0)
        mu = np.mean(features, axis=0)
        sigma = np.cov(features, rowvar=False)
        return (mu, sigma), features

    def evaluate(self, generator, ema_g=None) -> dict:
        (mu_real, sigma_real), feat_real = self.compute_real_features()
        (mu_fake, sigma_fake), feat_fake = self.compute_fake_features(
            generator, use_ema=self.config.use_ema, ema_g=ema_g
        )
        fid = calculate_frechet_distance(mu_real, sigma_real, mu_fake, sigma_fake)
        kid = calculate_kid(feat_real, feat_fake,
                            subset_size=min(self.config.kid_subset_size, feat_real.shape[0], feat_fake.shape[0]),
                            num_subsets=self.config.kid_subsets)
        return {"fid": fid, "kid": kid}
