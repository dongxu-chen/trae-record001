import copy
import math
import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm

from .config import TrainConfig
from .models import build_models
from .models.wgangp import compute_gradient_penalty
from .utils.checkpoint import CheckpointManager
from .utils.visualizer import Visualizer
from .utils.evaluator import GANEvaluator
from .utils.interpolation import LatentInterpolationAnimator


class EMAModel:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.ema = copy.deepcopy(model)
        self.ema.eval()
        self.decay = decay
        for p in self.ema.parameters():
            p.requires_grad_(False)

    def update(self, model: nn.Module):
        with torch.no_grad():
            for ema_p, model_p in zip(self.ema.parameters(), model.parameters()):
                ema_p.data.mul_(self.decay).add_(model_p.data, alpha=1 - self.decay)

    def state_dict(self):
        return self.ema.state_dict()

    def load_state_dict(self, state_dict):
        self.ema.load_state_dict(state_dict)


class GANTrainer:
    def __init__(self, config: TrainConfig):
        self.config = config
        self.device = torch.device(config.device if torch.cuda.is_available() else "cpu")

        self.generator, self.discriminator = build_models(config)
        self.generator.to(self.device)
        self.discriminator.to(self.device)

        self.g_optimizer = torch.optim.Adam(
            self.generator.parameters(),
            lr=config.g_lr,
            betas=(config.beta1, config.beta2),
        )
        self.d_optimizer = torch.optim.Adam(
            self.discriminator.parameters(),
            lr=config.d_lr,
            betas=(config.beta1, config.beta2),
        )

        self.ema_g = None
        if config.use_ema:
            self.ema_g = EMAModel(self.generator, config.ema_decay)

        self.scaler = torch.amp.GradScaler("cuda") if config.use_amp and self.device.type == "cuda" else None

        self.checkpoint_mgr = CheckpointManager(
            config,
            max_keep=config.checkpoint_max_keep,
            expire_seconds=config.checkpoint_expire_seconds,
        )
        self.visualizer = Visualizer(config)

        self.evaluator = None
        if config.fid_kid_enabled and self.device.type == "cuda":
            self.evaluator = GANEvaluator(config, self.device)

        self.animator = LatentInterpolationAnimator(config, self.device,
                                                    output_dir=os.path.join(config.sample_dir, "animations"))

        self.fixed_z = torch.randn(config.num_sample_images, config.z_dim, device=self.device)
        self.interp_z1 = torch.randn(1, config.z_dim, device=self.device)
        self.interp_z2 = torch.randn(1, config.z_dim, device=self.device)
        self.global_step = 0
        self.current_epoch = 0
        self.best_g_loss = float("inf")
        self.best_fid = float("inf")

    def get_dataloader(self) -> DataLoader:
        config = self.config
        transform = transforms.Compose([
            transforms.Resize(config.img_size),
            transforms.CenterCrop(config.img_size),
            transforms.ToTensor(),
            transforms.Normalize([0.5] * config.img_channels, [0.5] * config.img_channels),
        ])

        if config.dataset == "cifar10":
            dataset = datasets.CIFAR10(root=config.data_root, train=True, download=True, transform=transform)
        elif config.dataset == "mnist":
            dataset = datasets.MNIST(root=config.data_root, train=True, download=True, transform=transform)
            config.img_channels = 1
        elif config.dataset == "stl10":
            dataset = datasets.STL10(root=config.data_root, split="train", download=True, transform=transform)
        elif config.dataset == "folder":
            dataset = datasets.ImageFolder(root=config.data_root, transform=transform)
        else:
            raise ValueError(f"Unknown dataset: {config.dataset}")

        return DataLoader(
            dataset,
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=config.num_workers,
            pin_memory=True,
            drop_last=True,
        )

    def _train_step_dcgan(self, real_images: torch.Tensor) -> dict:
        use_amp = self.scaler is not None

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z).detach()
            d_real = self.discriminator(real_images)
            d_fake = self.discriminator(fake_images)

            real_label = torch.ones_like(d_real)
            fake_label = torch.zeros_like(d_fake)

            d_loss = nn.functional.binary_cross_entropy_with_logits(d_real, real_label) + \
                     nn.functional.binary_cross_entropy_with_logits(d_fake, fake_label)

        self.d_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(d_loss).backward()
            self.scaler.step(self.d_optimizer)
            self.scaler.update()
        else:
            d_loss.backward()
            self.d_optimizer.step()

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z)
            d_fake = self.discriminator(fake_images)
            g_loss = nn.functional.binary_cross_entropy_with_logits(d_fake, real_label)

        self.g_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(g_loss).backward()
            self.scaler.step(self.g_optimizer)
            self.scaler.update()
        else:
            g_loss.backward()
            self.g_optimizer.step()

        if self.ema_g is not None:
            self.ema_g.update(self.generator)

        return {
            "g_loss": g_loss.item(),
            "d_loss": d_loss.item(),
            "d_real": d_real.mean().item(),
            "d_fake": d_fake.mean().item(),
            "gp_loss": 0.0,
        }

    def _train_step_wgangp(self, real_images: torch.Tensor) -> dict:
        use_amp = self.scaler is not None

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z).detach()
            d_real = self.discriminator(real_images)
            d_fake = self.discriminator(fake_images)

        gp = compute_gradient_penalty(
            self.discriminator, real_images, fake_images, self.device,
            edge_ratio=self.config.gp_edge_ratio,
            edge_threshold=self.config.gp_edge_threshold,
            edge_weight=self.config.gp_edge_weight,
        )
        d_loss = d_fake.mean() - d_real.mean() + self.config.lambda_gp * gp

        self.d_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(d_loss).backward()
            self.scaler.step(self.d_optimizer)
            self.scaler.update()
        else:
            d_loss.backward()
            self.d_optimizer.step()

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z)
            d_fake_g = self.discriminator(fake_images)
            g_loss = -d_fake_g.mean()

        self.g_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(g_loss).backward()
            self.scaler.step(self.g_optimizer)
            self.scaler.update()
        else:
            g_loss.backward()
            self.g_optimizer.step()

        if self.ema_g is not None:
            self.ema_g.update(self.generator)

        return {
            "g_loss": g_loss.item(),
            "d_loss": d_loss.item(),
            "d_real": d_real.mean().item(),
            "d_fake": d_fake_g.mean().item(),
            "gp_loss": gp.item(),
        }

    def _train_step_stylegan2(self, real_images: torch.Tensor) -> dict:
        use_amp = self.scaler is not None

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z).detach()
            d_real = self.discriminator(real_images)
            d_fake = self.discriminator(fake_images)

            d_loss = d_fake.mean() - d_real.mean()

        if self.global_step % self.config.lazy_reg_interval == 0:
            gp = compute_gradient_penalty(
                self.discriminator, real_images, fake_images, self.device,
                edge_ratio=self.config.gp_edge_ratio,
                edge_threshold=self.config.gp_edge_threshold,
                edge_weight=self.config.gp_edge_weight,
            )
            real_images_req = real_images.detach().requires_grad_(True)
            d_real_req = self.discriminator(real_images_req)
            r1_grads = torch.autograd.grad(
                outputs=d_real_req.sum(), inputs=real_images_req, create_graph=True
            )[0]
            r1_penalty = r1_grads.pow(2).reshape(r1_grads.shape[0], -1).sum(1).mean()
            d_loss = d_loss + self.config.lambda_gp * gp + self.config.stylegan2_r1_gamma * 0.5 * r1_penalty

        self.d_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(d_loss).backward()
            self.scaler.step(self.d_optimizer)
            self.scaler.update()
        else:
            d_loss.backward()
            self.d_optimizer.step()

        z = torch.randn(real_images.size(0), self.config.z_dim, device=self.device)
        with torch.amp.autocast("cuda", enabled=use_amp):
            fake_images = self.generator(z)
            d_fake_g = self.discriminator(fake_images)
            g_loss = -d_fake_g.mean()

        if self.global_step % self.config.lazy_reg_interval == 0:
            path_noise = torch.randn_like(fake_images) / math.sqrt(
                fake_images.shape[2] * fake_images.shape[3]
            )
            path_grads = torch.autograd.grad(
                outputs=(fake_images * path_noise).sum(), inputs=z, create_graph=True
            )[0]
            path_lengths = path_grads.pow(2).sum(1).sqrt()
            path_loss = (path_lengths - 1.0).pow(2).mean() * self.config.stylegan2_path_reg_gamma
            g_loss = g_loss + path_loss

        self.g_optimizer.zero_grad()
        if use_amp:
            self.scaler.scale(g_loss).backward()
            self.scaler.step(self.g_optimizer)
            self.scaler.update()
        else:
            g_loss.backward()
            self.g_optimizer.step()

        if self.ema_g is not None:
            self.ema_g.update(self.generator)

        return {
            "g_loss": g_loss.item(),
            "d_loss": d_loss.item(),
            "d_real": d_real.mean().item(),
            "d_fake": d_fake_g.mean().item(),
            "gp_loss": 0.0,
        }

    def _get_train_step(self):
        step_map = {
            "dcgan": self._train_step_dcgan,
            "wgan-gp": self._train_step_wgangp,
            "stylegan2": self._train_step_stylegan2,
        }
        step_fn = step_map.get(self.config.architecture)
        if step_fn is None:
            raise ValueError(f"No train step for {self.config.architecture}")
        return step_fn

    def _generate_samples(self):
        g = self.ema_g.ema if self.ema_g is not None else self.generator
        g.eval()
        with torch.no_grad():
            samples = g(self.fixed_z)
        g.train()
        return samples

    def train(self):
        dataloader = self.get_dataloader()
        train_step = self._get_train_step()

        ckpt = self.checkpoint_mgr.load()
        if ckpt is not None:
            self.generator.load_state_dict(ckpt["g_state_dict"])
            self.discriminator.load_state_dict(ckpt["d_state_dict"])
            self.g_optimizer.load_state_dict(ckpt["g_optimizer_state_dict"])
            self.d_optimizer.load_state_dict(ckpt["d_optimizer_state_dict"])
            self.global_step = ckpt["step"]
            self.current_epoch = ckpt["epoch"]
            if self.ema_g and "ema_g_state_dict" in ckpt:
                self.ema_g.load_state_dict(ckpt["ema_g_state_dict"])
            if self.scaler is not None and "scaler_state_dict" in ckpt:
                self.scaler.load_state_dict(ckpt["scaler_state_dict"])
            print(f"Resumed from step {self.global_step}, epoch {self.current_epoch}")

        self.generator.train()
        self.discriminator.train()

        print(f"Training {self.config.architecture.upper()} on {self.device}")
        print(f"AMP: {'Enabled' if self.scaler else 'Disabled'} | FID/KID: {'Enabled' if self.evaluator else 'Disabled'}")
        print(f"Dataset: {self.config.dataset}, Image size: {self.config.img_size}x{self.config.img_size}")
        print(f"G params: {sum(p.numel() for p in self.generator.parameters()):,}")
        print(f"D params: {sum(p.numel() for p in self.discriminator.parameters()):,}")

        for epoch in range(self.current_epoch, self.config.num_epochs):
            self.current_epoch = epoch
            pbar = tqdm(dataloader, desc=f"Epoch {epoch + 1}/{self.config.num_epochs}")

            epoch_g_loss, epoch_d_loss = 0.0, 0.0
            num_batches = 0

            for batch_idx, (real_images, _) in enumerate(pbar):
                real_images = real_images.to(self.device)
                metrics = train_step(real_images)
                self.global_step += 1
                num_batches += 1

                epoch_g_loss += metrics["g_loss"]
                epoch_d_loss += metrics["d_loss"]

                pbar.set_postfix(
                    g_loss=f"{metrics['g_loss']:.4f}",
                    d_loss=f"{metrics['d_loss']:.4f}",
                )

                if self.global_step % 100 == 0:
                    self.visualizer.log_scalars(
                        step=self.global_step,
                        g_loss=metrics["g_loss"],
                        d_loss=metrics["d_loss"],
                        d_real=metrics["d_real"],
                        d_fake=metrics["d_fake"],
                        gp_loss=metrics["gp_loss"],
                    )

                if self.global_step % self.config.sample_interval == 0:
                    samples = self._generate_samples()
                    self.visualizer.save_sample_grid(self.global_step, samples)
                    self.visualizer.log_images(self.global_step, samples)
                    self.visualizer.plot_training_curves(self.global_step)

                if self.global_step % self.config.checkpoint_interval == 0:
                    is_best = metrics["g_loss"] < self.best_g_loss
                    if is_best:
                        self.best_g_loss = metrics["g_loss"]

                    scaler_state = self.scaler.state_dict() if self.scaler is not None else None

                    self.checkpoint_mgr.save(
                        epoch=epoch,
                        step=self.global_step,
                        g_state=self.generator.state_dict(),
                        d_state=self.discriminator.state_dict(),
                        g_opt_state=self.g_optimizer.state_dict(),
                        d_opt_state=self.d_optimizer.state_dict(),
                        is_best=is_best,
                        ema_g_state=self.ema_g.state_dict() if self.ema_g else None,
                    )
                    self.checkpoint_mgr.cleanup_old()

            avg_g_loss = epoch_g_loss / max(1, num_batches)
            avg_d_loss = epoch_d_loss / max(1, num_batches)
            print(f"\nEpoch {epoch + 1} Summary: avg_g_loss={avg_g_loss:.4f}, avg_d_loss={avg_d_loss:.4f}")

            eval_metrics = None
            if self.evaluator is not None:
                print(f"Evaluating FID/KID...")
                eval_metrics = self.evaluator.evaluate(self.generator, ema_g=self.ema_g)
                print(f"FID: {eval_metrics['fid']:.4f} | KID: {eval_metrics['kid']:.4f}")
                self.visualizer.writer.add_scalar("Metric/FID", eval_metrics["fid"], self.global_step)
                self.visualizer.writer.add_scalar("Metric/KID", eval_metrics["kid"], self.global_step)

                if eval_metrics["fid"] < self.best_fid:
                    self.best_fid = eval_metrics["fid"]
                    scaler_state = self.scaler.state_dict() if self.scaler is not None else None
                    self.checkpoint_mgr.save(
                        epoch=epoch,
                        step=self.global_step,
                        g_state=self.generator.state_dict(),
                        d_state=self.discriminator.state_dict(),
                        g_opt_state=self.g_optimizer.state_dict(),
                        d_opt_state=self.d_optimizer.state_dict(),
                        is_best=True,
                        ema_g_state=self.ema_g.state_dict() if self.ema_g else None,
                    )

            print(f"Generating interpolation animation...")
            video_path = self.animator.generate_interpolation_video(
                self.generator,
                z1=self.interp_z1,
                z2=self.interp_z2,
                num_samples=16,
                ema_g=self.ema_g,
                output_path=os.path.join(self.animator.output_dir, f"interp_epoch_{epoch + 1}.mp4"),
            )
            print(f"Animation saved to: {video_path}")

        samples = self._generate_samples()
        self.visualizer.save_sample_grid(self.global_step, samples, nrow=8)
        self.visualizer.plot_training_curves(self.global_step)

        scaler_state = self.scaler.state_dict() if self.scaler is not None else None
        self.checkpoint_mgr.save(
            epoch=self.config.num_epochs,
            step=self.global_step,
            g_state=self.generator.state_dict(),
            d_state=self.discriminator.state_dict(),
            g_opt_state=self.g_optimizer.state_dict(),
            d_opt_state=self.d_optimizer.state_dict(),
            is_best=False,
            ema_g_state=self.ema_g.state_dict() if self.ema_g else None,
        )

        self.visualizer.close()
        print("Training complete!")
