import os
import torch
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from torchvision.utils import make_grid, save_image
from torch.utils.tensorboard import SummaryWriter
from .config import TrainConfig


class Visualizer:
    def __init__(self, config: TrainConfig):
        self.config = config
        self.sample_dir = config.sample_dir
        os.makedirs(self.sample_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir=config.log_dir)
        self.g_losses = []
        self.d_losses = []
        self.d_real_scores = []
        self.d_fake_scores = []
        self.gp_losses = []
        self.steps = []

    def log_scalars(
        self,
        step: int,
        g_loss: float,
        d_loss: float,
        d_real: float,
        d_fake: float,
        gp_loss: float = 0.0,
    ):
        self.steps.append(step)
        self.g_losses.append(g_loss)
        self.d_losses.append(d_loss)
        self.d_real_scores.append(d_real)
        self.d_fake_scores.append(d_fake)
        self.gp_losses.append(gp_loss)

        self.writer.add_scalar("Loss/Generator", g_loss, step)
        self.writer.add_scalar("Loss/Discriminator", d_loss, step)
        self.writer.add_scalar("Score/D_real", d_real, step)
        self.writer.add_scalar("Score/D_fake", d_fake, step)
        if gp_loss > 0:
            self.writer.add_scalar("Loss/GradientPenalty", gp_loss, step)

    def log_images(self, step: int, images: torch.Tensor, tag: str = "generated"):
        grid = make_grid(images, nrow=8, normalize=True, value_range=(-1, 1))
        self.writer.add_images(tag, grid.unsqueeze(0), step)

    def save_sample_grid(
        self, step: int, images: torch.Tensor, nrow: int = 8
    ):
        grid = make_grid(images, nrow=nrow, normalize=True, value_range=(-1, 1))
        save_path = os.path.join(self.sample_dir, f"sample_step_{step}.png")
        save_image(grid, save_path)

    def plot_training_curves(self, step: int):
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        axes[0, 0].plot(self.steps, self.g_losses, label="G Loss", color="blue")
        axes[0, 0].plot(self.steps, self.d_losses, label="D Loss", color="red")
        axes[0, 0].set_xlabel("Step")
        axes[0, 0].set_ylabel("Loss")
        axes[0, 0].set_title("Generator & Discriminator Loss")
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(self.steps, self.d_real_scores, label="D(real)", color="green")
        axes[0, 1].plot(self.steps, self.d_fake_scores, label="D(fake)", color="orange")
        axes[0, 1].set_xlabel("Step")
        axes[0, 1].set_ylabel("Score")
        axes[0, 1].set_title("Discriminator Scores")
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        if any(gp > 0 for gp in self.gp_losses):
            axes[1, 0].plot(self.steps, self.gp_losses, label="GP Loss", color="purple")
            axes[1, 0].set_xlabel("Step")
            axes[1, 0].set_ylabel("Loss")
            axes[1, 0].set_title("Gradient Penalty")
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        else:
            axes[1, 0].text(0.5, 0.5, "No GP", ha="center", va="center")
            axes[1, 0].set_title("Gradient Penalty (N/A)")

        if len(self.g_losses) > 50:
            window = min(100, len(self.g_losses) // 5)
            g_ma = np.convolve(
                self.g_losses, np.ones(window) / window, mode="valid"
            )
            d_ma = np.convolve(
                self.d_losses, np.ones(window) / window, mode="valid"
            )
            ma_steps = self.steps[window - 1 :]
            axes[1, 1].plot(ma_steps, g_ma, label="G Loss (MA)", color="blue")
            axes[1, 1].plot(ma_steps, d_ma, label="D Loss (MA)", color="red")
            axes[1, 1].set_xlabel("Step")
            axes[1, 1].set_ylabel("Loss")
            axes[1, 1].set_title("Smoothed Losses (Moving Avg)")
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].text(
                0.5, 0.5, "Not enough data", ha="center", va="center"
            )
            axes[1, 1].set_title("Smoothed Losses")

        plt.tight_layout()
        curve_path = os.path.join(self.sample_dir, f"curves_step_{step}.png")
        plt.savefig(curve_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        self.writer.add_figure("Training/Curves", fig if False else plt.figure(), step)
        return curve_path

    def log_model_graph(self, generator, discriminator, z: torch.Tensor):
        try:
            self.writer.add_graph(generator, z)
            self.writer.add_graph(discriminator, torch.randn(1, self.config.img_channels, self.config.img_size, self.config.img_size))
        except Exception:
            pass

    def close(self):
        self.writer.close()
