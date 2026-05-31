import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


class RegistrationVisualizer:
    def __init__(self, figsize=(15, 5), dpi=100):
        self.figsize = figsize
        self.dpi = dpi

    def plot_overlay(self, fixed, moving, title="Overlay", alpha=0.5, save_path=None):
        fig, axes = plt.subplots(1, 3, figsize=(self.figsize[0], self.figsize[1]))

        axes[0].imshow(fixed, cmap="gray")
        axes[0].set_title("Fixed Image")
        axes[0].axis("off")

        axes[1].imshow(moving, cmap="gray")
        axes[1].set_title("Moving Image")
        axes[1].axis("off")

        overlay = np.zeros((*fixed.shape, 3))
        fixed_norm = self._normalize(fixed)
        moving_norm = self._normalize(moving)
        overlay[:, :, 0] = fixed_norm
        overlay[:, :, 1] = moving_norm
        overlay[:, :, 2] = (fixed_norm + moving_norm) / 2
        axes[2].imshow(overlay)
        axes[2].set_title(title)
        axes[2].axis("off")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_checkerboard(self, fixed, moving, grid_size=8, title="Checkerboard", save_path=None):
        checkerboard = self._create_checkerboard(fixed, moving, grid_size)

        fig, axes = plt.subplots(1, 3, figsize=self.figsize)
        axes[0].imshow(fixed, cmap="gray")
        axes[0].set_title("Fixed Image")
        axes[0].axis("off")

        axes[1].imshow(moving, cmap="gray")
        axes[1].set_title("Moving Image")
        axes[1].axis("off")

        axes[2].imshow(checkerboard, cmap="gray")
        axes[2].set_title(title)
        axes[2].axis("off")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_difference(self, fixed, moving_warped, title="Difference", save_path=None):
        diff = fixed.astype(np.float64) - moving_warped.astype(np.float64)

        fig, axes = plt.subplots(1, 3, figsize=self.figsize)
        axes[0].imshow(fixed, cmap="gray")
        axes[0].set_title("Fixed Image")
        axes[0].axis("off")

        axes[1].imshow(moving_warped, cmap="gray")
        axes[1].set_title("Warped Moving")
        axes[1].axis("off")

        vmax = max(abs(diff.min()), abs(diff.max()))
        if vmax < 1e-10:
            vmax = 1.0
        im = axes[2].imshow(diff, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        axes[2].set_title(title)
        axes[2].axis("off")
        plt.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_contour_overlay(self, fixed, moving, title="Contour Overlay", save_path=None):
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.imshow(fixed, cmap="gray")
        ax.contour(moving, levels=8, colors="cyan", linewidths=0.8, alpha=0.7)
        ax.set_title(title)
        ax.axis("off")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_registration_result(
        self, fixed, moving, moving_warped, title="Registration Result", save_path=None
    ):
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))

        axes[0, 0].imshow(fixed, cmap="gray")
        axes[0, 0].set_title("Fixed (Reference)")
        axes[0, 0].axis("off")

        axes[0, 1].imshow(moving, cmap="gray")
        axes[0, 1].set_title("Moving (Before)")
        axes[0, 1].axis("off")

        axes[0, 2].imshow(moving_warped, cmap="gray")
        axes[0, 2].set_title("Warped (After)")
        axes[0, 2].axis("off")

        diff_before = fixed.astype(np.float64) - moving.astype(np.float64)
        diff_after = fixed.astype(np.float64) - moving_warped.astype(np.float64)

        vmax = max(abs(diff_before.min()), abs(diff_before.max()), 1e-10)
        axes[1, 0].imshow(diff_before, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        axes[1, 0].set_title("Difference (Before)")
        axes[1, 0].axis("off")

        vmax2 = max(abs(diff_after.min()), abs(diff_after.max()), 1e-10)
        axes[1, 1].imshow(diff_after, cmap="RdBu_r", vmin=-vmax2, vmax=vmax2)
        axes[1, 1].set_title("Difference (After)")
        axes[1, 1].axis("off")

        checkerboard = self._create_checkerboard(fixed, moving_warped, grid_size=8)
        axes[1, 2].imshow(checkerboard, cmap="gray")
        axes[1, 2].set_title("Checkerboard (After)")
        axes[1, 2].axis("off")

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_convergence(self, metric_history, title="Convergence", save_path=None):
        fig, ax = plt.subplots(1, 1, figsize=(8, 4))
        ax.plot(metric_history, "b-", linewidth=1.5)
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Mutual Information")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        if len(metric_history) > 0:
            ax.axhline(y=max(metric_history), color="r", linestyle="--", alpha=0.5, label=f"Best: {max(metric_history):.4f}")
            ax.legend()

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_joint_histogram(self, fixed, moving, num_bins=64, title="Joint Histogram", save_path=None):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        mask = np.isfinite(fixed) & np.isfinite(moving)
        hist, x_edges, y_edges = np.histogram2d(
            fixed[mask].ravel(), moving[mask].ravel(), bins=num_bins
        )

        axes[0].imshow(np.log1p(hist.T), origin="lower", cmap="hot", aspect="auto")
        axes[0].set_xlabel("Fixed Image Intensity")
        axes[0].set_ylabel("Moving Image Intensity")
        axes[0].set_title(f"{title} (Before Registration)")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    @staticmethod
    def _normalize(image):
        arr = image.astype(np.float64)
        min_val, max_val = arr.min(), arr.max()
        if max_val - min_val > 1e-10:
            return (arr - min_val) / (max_val - min_val)
        return np.zeros_like(arr)

    @staticmethod
    def _create_checkerboard(image1, image2, grid_size=8):
        rows, cols = image1.shape[:2]
        result = np.zeros_like(image1, dtype=np.float64)
        for i in range(rows):
            for j in range(cols):
                if ((i // grid_size) + (j // grid_size)) % 2 == 0:
                    result[i, j] = image1[i, j]
                else:
                    result[i, j] = image2[i, j]
        return result

    def plot_fusion_overlay(self, fixed, warped, title="Fusion Overlay",
                            alpha=0.5, save_path=None):
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        fixed_norm = self._normalize(fixed)
        warped_norm = self._normalize(warped)

        axes[0].imshow(fixed, cmap="gray")
        axes[0].set_title("Fixed Image (CT)")
        axes[0].axis("off")

        axes[1].imshow(warped, cmap="gray")
        axes[1].set_title("Warped Moving Image (MRI)")
        axes[1].axis("off")

        fusion = np.zeros((*fixed.shape, 3))
        fusion[:, :, 0] = fixed_norm
        fusion[:, :, 1] = warped_norm * alpha + fixed_norm * (1 - alpha)
        fusion[:, :, 2] = warped_norm

        axes[2].imshow(fusion)
        axes[2].set_title(title)
        axes[2].axis("off")

        cbar_ax = fig.add_axes([0.92, 0.3, 0.02, 0.4])
        cbar = plt.colorbar(plt.cm.ScalarMappable(cmap="gray"), cax=cbar_ax)
        cbar.set_label("Intensity")
        fig.text(0.87, 0.72, "Red = Fixed", color="red", fontsize=9)
        fig.text(0.87, 0.66, "Blue = Warped", color="blue", fontsize=9)
        fig.text(0.87, 0.60, "Yellow = Overlap", color="yellow", fontsize=9)

        plt.tight_layout(rect=[0, 0, 0.9, 1])
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_displacement_field(self, displacement_field, title="Displacement Field",
                                grid_step=8, save_path=None):
        dim = displacement_field.shape[0]
        if dim != 2:
            return None

        rows, cols = displacement_field.shape[1:]
        dy = displacement_field[0]
        dx = displacement_field[1]

        magnitude = np.sqrt(dx ** 2 + dy ** 2)

        fig, axes = plt.subplots(2, 2, figsize=(14, 12))

        vmax = np.percentile(magnitude, 98) if magnitude.max() > 0 else 1.0
        im0 = axes[0, 0].imshow(dy, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        axes[0, 0].set_title("Vertical Displacement (Y)")
        axes[0, 0].axis("off")
        plt.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)

        im1 = axes[0, 1].imshow(dx, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        axes[0, 1].set_title("Horizontal Displacement (X)")
        axes[0, 1].axis("off")
        plt.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

        im2 = axes[1, 0].imshow(magnitude, cmap="hot", vmin=0, vmax=vmax)
        axes[1, 0].set_title("Displacement Magnitude")
        axes[1, 0].axis("off")
        plt.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)

        y, x = np.mgrid[0:rows:grid_step, 0:cols:grid_step]
        ax = axes[1, 1]
        ax.imshow(magnitude, cmap="hot", vmin=0, vmax=vmax, alpha=0.6)
        ax.quiver(x, y, dx[::grid_step, ::grid_step], dy[::grid_step, ::grid_step],
                  color="cyan", scale=50, headwidth=3, headlength=4, linewidth=0.5, alpha=0.8)
        ax.set_title("Vector Field (Quiver)")
        ax.axis("off")

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_jacobian_determinant(self, jac_det, title="Jacobian Determinant",
                                  save_path=None):
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        jd = np.asarray(jac_det, dtype=np.float64)
        invalid_mask = jd <= 0

        valid_jd = jd[jd > 0]
        if len(valid_jd) > 0:
            vmin, vmax = np.percentile(valid_jd, (0.5, 99.5))
        else:
            vmin, vmax = 0.5, 1.5

        im0 = axes[0].imshow(jd, cmap="RdYlBu_r", vmin=vmin, vmax=vmax)
        axes[0].set_title("Jacobian Determinant")
        axes[0].axis("off")
        plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

        jd_log = np.log(np.abs(jd) + 1e-10)
        log_max = np.percentile(np.abs(jd_log), 98)
        im1 = axes[1].imshow(jd_log, cmap="RdBu_r", vmin=-log_max, vmax=log_max)
        axes[1].set_title("Log |Jacobian Determinant|")
        axes[1].axis("off")
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

        folding_mask = jd < 0
        axes[2].imshow(jd, cmap="gray", alpha=0.3)
        if np.any(folding_mask):
            axes[2].imshow(folding_mask, cmap="Reds", alpha=0.7, vmin=0, vmax=1)
            axes[2].set_title(f"Folding Areas (det(J) < 0)\nCount: {np.sum(folding_mask)} pixels")
        else:
            axes[2].set_title("No Folding Detected (det(J) > 0 everywhere)")
        axes[2].axis("off")

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_landmark_points(self, fixed, ground_truth_points=None,
                             transformed_points=None, initial_points=None,
                             title="Landmark Points", save_path=None):
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))

        ax.imshow(fixed, cmap="gray")

        if initial_points is not None:
            initial_points = np.asarray(initial_points)
            ax.scatter(initial_points[:, 1], initial_points[:, 0],
                       s=40, facecolors="none", edgecolors="yellow",
                       linewidths=1.5, alpha=0.7, label="Initial")

        if ground_truth_points is not None:
            gt_points = np.asarray(ground_truth_points)
            ax.scatter(gt_points[:, 1], gt_points[:, 0],
                       s=60, c="lime", marker="x", linewidths=2,
                       alpha=0.8, label="Ground Truth")

        if transformed_points is not None and ground_truth_points is not None:
            tp = np.asarray(transformed_points)
            gt = np.asarray(ground_truth_points)
            for i in range(len(tp)):
                ax.plot([gt[i, 1], tp[i, 1]], [gt[i, 0], tp[i, 0]],
                        "w--", linewidth=0.8, alpha=0.5)

        if transformed_points is not None:
            tp = np.asarray(transformed_points)
            ax.scatter(tp[:, 1], tp[:, 0],
                       s=50, c="red", marker="o", edgecolors="white",
                       linewidths=1, alpha=0.7, label="Registered")

        ax.set_title(title)
        ax.legend(loc="upper right", fontsize=9)
        ax.axis("off")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig

    def plot_tre_histogram(self, tre_result, title="TRE Distribution", save_path=None):
        if tre_result is None or "all_errors" not in tre_result:
            return None

        errors = tre_result["all_errors"]

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        axes[0].hist(errors, bins=20, edgecolor="black", alpha=0.7, color="steelblue")
        axes[0].axvline(tre_result["mean"], color="red", linestyle="--", linewidth=2,
                        label=f"Mean: {tre_result['mean']:.2f}")
        axes[0].axvline(tre_result["median"], color="orange", linestyle="--", linewidth=2,
                        label=f"Median: {tre_result['median']:.2f}")
        axes[0].axvline(tre_result["p95"], color="purple", linestyle="--", linewidth=2,
                        label=f"P95: {tre_result['p95']:.2f}")
        axes[0].set_xlabel("TRE (pixels)")
        axes[0].set_ylabel("Frequency")
        axes[0].set_title("Histogram of Target Registration Errors")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        sorted_errors = tre_result["sorted_errors"]
        pct = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors) * 100
        axes[1].plot(sorted_errors, pct, "b-", linewidth=2)
        axes[1].fill_between(sorted_errors, 0, pct, alpha=0.3, color="steelblue")
        axes[1].set_xlabel("TRE (pixels)")
        axes[1].set_ylabel("Cumulative Percentage (%)")
        axes[1].set_title("Cumulative Distribution of TRE")
        axes[1].grid(True, alpha=0.3)
        for p_val in [25, 50, 75, 95]:
            err_pct = np.percentile(errors, p_val)
            axes[1].axhline(p_val, color="gray", linestyle=":", alpha=0.5)
            axes[1].axvline(err_pct, color="gray", linestyle=":", alpha=0.5)
            axes[1].text(sorted_errors[-1] * 0.6, p_val + 1, f"P{p_val}: {err_pct:.2f}", fontsize=8)

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return fig
