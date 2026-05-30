import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from typing import Optional, Tuple, List, Dict, Any
from .distortion_models import (
    FisheyeDistortionModel,
    FisheyeProjectionType,
    EquidistantProjection,
    EquisolidProjection,
    OrthographicProjection,
    StereographicProjection,
)
from .fisheye_corrector import (
    FisheyeCorrector,
    CorrectionMethod,
    generate_correction_grid,
    correct_fisheye_image,
)
from .calibration import estimate_fisheye_params_auto


class FisheyeVisualizer:
    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        self.figsize = figsize
        self.dpi = dpi
        self.fig = None
        self.axes = None

    def _create_figure(self, nrows: int = 1, ncols: int = 1):
        self.fig, self.axes = plt.subplots(
            nrows, ncols, figsize=self.figsize, dpi=self.dpi
        )
        if nrows == 1 and ncols == 1:
            self.axes = np.array([self.axes])
        self.axes = self.axes.reshape(nrows, ncols)

    def _imshow(self, ax, image: np.ndarray, title: str = "", cmap: Optional[str] = None):
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            ax.imshow(image)
        else:
            ax.imshow(image, cmap=cmap or "gray")
        ax.set_title(title, fontsize=12)
        ax.axis("off")

    def show_image_pair(
        self,
        original: np.ndarray,
        corrected: np.ndarray,
        original_title: str = "Original Fisheye",
        corrected_title: str = "Corrected Image",
        save_path: Optional[str] = None,
    ):
        self._create_figure(1, 2)

        self._imshow(self.axes[0, 0], original, original_title)
        self._imshow(self.axes[0, 1], corrected, corrected_title)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_all_methods(
        self,
        image: np.ndarray,
        distortion_model: Optional[FisheyeDistortionModel] = None,
        save_path: Optional[str] = None,
    ):
        if distortion_model is None:
            params = estimate_fisheye_params_auto(image)
            distortion_model = params["model"]

        methods = [
            (CorrectionMethod.SPHERICAL_PROJECTION, "Spherical Projection"),
            (CorrectionMethod.EQURECTANGULAR_PROJECTION, "Equirectangular (Panorama)"),
            (CorrectionMethod.PERSPECTIVE_PROJECTION, "Perspective Projection"),
        ]

        n_cols = len(methods) + 1
        self._create_figure(1, n_cols)

        self._imshow(self.axes[0, 0], image, "Original Fisheye")

        for i, (method, title) in enumerate(methods, start=1):
            corrector = FisheyeCorrector(
                distortion_model=distortion_model, method=method
            )
            corrected = corrector.correct(image)
            self._imshow(self.axes[0, i], corrected, title)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_projection_models(
        self,
        image: np.ndarray,
        center: Optional[Tuple[float, float]] = None,
        focal_length: Optional[float] = None,
        save_path: Optional[str] = None,
    ):
        h, w = image.shape[:2]

        if center is None or focal_length is None:
            params = estimate_fisheye_params_auto(image)
            center = params["center"]
            focal_length = params["focal_length"]

        models = [
            (EquidistantProjection(focal_length, center), "Equidistant"),
            (EquisolidProjection(focal_length, center), "Equisolid"),
            (OrthographicProjection(focal_length, center), "Orthographic"),
            (StereographicProjection(focal_length, center), "Stereographic"),
        ]

        self._create_figure(2, 2)

        for i, (model, title) in enumerate(models):
            row = i // 2
            col = i % 2
            corrector = FisheyeCorrector(distortion_model=model)
            corrected = corrector.correct(image)
            self._imshow(self.axes[row, col], corrected, title)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_distortion_grid(
        self,
        image: np.ndarray,
        distortion_model: Optional[FisheyeDistortionModel] = None,
        grid_spacing: int = 50,
        save_path: Optional[str] = None,
    ):
        if distortion_model is None:
            params = estimate_fisheye_params_auto(image)
            distortion_model = params["model"]

        h, w = image.shape[:2]
        h_lines_x, h_lines_y, v_lines_x, v_lines_y = generate_correction_grid(
            (h, w), distortion_model, grid_spacing
        )

        self._create_figure(1, 2)

        self._imshow(self.axes[0, 0], image, "Original with Grid")
        for x, y in zip(h_lines_x, h_lines_y):
            self.axes[0, 0].plot(x, y, "r-", alpha=0.5, linewidth=1)
        for x, y in zip(v_lines_x, v_lines_y):
            self.axes[0, 0].plot(x, y, "r-", alpha=0.5, linewidth=1)

        corrector = FisheyeCorrector(distortion_model=distortion_model)
        corrected = corrector.correct(image)
        self._imshow(self.axes[0, 1], corrected, "Corrected with Grid")

        for y in range(0, corrected.shape[0], grid_spacing):
            self.axes[0, 1].axhline(y, color="r", alpha=0.5, linewidth=1)
        for x in range(0, corrected.shape[1], grid_spacing):
            self.axes[0, 1].axvline(x, color="r", alpha=0.5, linewidth=1)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_fov_estimate(
        self,
        image: np.ndarray,
        fov_degrees: Optional[float] = None,
        center: Optional[Tuple[float, float]] = None,
        save_path: Optional[str] = None,
    ):
        from .calibration import estimate_fov_from_image, estimate_center_auto

        if fov_degrees is None:
            fov_degrees = estimate_fov_from_image(image)
        if center is None:
            center = estimate_center_auto(image)

        h, w = image.shape[:2]

        self._create_figure(1, 1)
        ax = self.axes[0, 0]

        self._imshow(ax, image, f"FOV Estimate: {fov_degrees:.1f}°")

        ax.plot(center[0], center[1], "r+", markersize=15, markeredgewidth=2)

        max_dim = max(w, h)
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]])
        r_max = np.max(np.sqrt(np.sum((corners - center) ** 2, axis=1)))
        theta_max = np.radians(fov_degrees / 2)

        fov_circle = Circle(
            center,
            r_max * np.sin(theta_max),
            fill=False,
            color="red",
            linestyle="--",
            linewidth=2,
            alpha=0.7,
            label=f"FOV: {fov_degrees:.1f}°",
        )
        ax.add_patch(fov_circle)

        ax.legend(loc="upper right")

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_projection_curves(
        self,
        fov_degrees: float = 180.0,
        save_path: Optional[str] = None,
    ):
        theta_max = np.radians(fov_degrees / 2)
        theta = np.linspace(0, theta_max, 100)

        models = [
            (EquidistantProjection(1.0, (0, 0)), "Equidistant: r = fθ"),
            (EquisolidProjection(1.0, (0, 0)), "Equisolid: r = 2f sin(θ/2)"),
            (OrthographicProjection(1.0, (0, 0)), "Orthographic: r = f sin(θ)"),
            (StereographicProjection(1.0, (0, 0)), "Stereographic: r = 2f tan(θ/2)"),
        ]

        self._create_figure(1, 2)

        ax1 = self.axes[0, 0]
        for model, label in models:
            r = model.project(theta)
            ax1.plot(np.degrees(theta), r, label=label, linewidth=2)

        ax1.set_xlabel("Incident Angle θ (degrees)", fontsize=11)
        ax1.set_ylabel("Normalized Radius r/f", fontsize=11)
        ax1.set_title("Forward Projection: r(θ)", fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=9)

        ax2 = self.axes[0, 1]
        r_max = models[0][0].project(theta_max)
        r = np.linspace(0, r_max, 100)
        for model, label in models:
            theta_unproj = model.unproject(r)
            ax2.plot(r, np.degrees(theta_unproj), label=label, linewidth=2)

        ax2.set_xlabel("Normalized Radius r/f", fontsize=11)
        ax2.set_ylabel("Incident Angle θ (degrees)", fontsize=11)
        ax2.set_title("Inverse Projection: θ(r)", fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=9)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_rotation_effect(
        self,
        image: np.ndarray,
        distortion_model: Optional[FisheyeDistortionModel] = None,
        yaw_angles: List[float] = [-45, 0, 45],
        pitch: float = 0.0,
        save_path: Optional[str] = None,
    ):
        if distortion_model is None:
            params = estimate_fisheye_params_auto(image)
            distortion_model = params["model"]

        n_cols = len(yaw_angles)
        self._create_figure(1, n_cols)

        corrector = FisheyeCorrector(distortion_model=distortion_model)

        for i, yaw in enumerate(yaw_angles):
            corrected = corrector.correct_with_custom_rotation(
                image, yaw=yaw, pitch=pitch
            )
            self._imshow(
                self.axes[0, i], corrected, f"Yaw: {yaw}°, Pitch: {pitch}°"
            )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_calibration_result(
        self,
        original: np.ndarray,
        params: Dict[str, Any],
        save_path: Optional[str] = None,
    ):
        corrector = FisheyeCorrector(distortion_model=params["model"])
        corrected = corrector.correct(original)

        self._create_figure(1, 2)

        self._imshow(self.axes[0, 0], original, "Original Fisheye")

        info_text = (
            f"FOV: {params['fov_degrees']:.1f}°\n"
            f"Center: ({params['center'][0]:.1f}, {params['center'][1]:.1f})\n"
            f"Focal Length: {params['focal_length']:.1f}\n"
            f"Projection: {params['projection_type'].value}"
        )

        self._imshow(self.axes[0, 1], corrected, "Corrected Image")
        self.axes[0, 1].text(
            0.02,
            0.98,
            info_text,
            transform=self.axes[0, 1].transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def show_intensity_profile(
        self,
        original: np.ndarray,
        corrected: np.ndarray,
        center: Optional[Tuple[float, float]] = None,
        save_path: Optional[str] = None,
    ):
        h, w = original.shape[:2]
        if center is None:
            center = (w / 2, h / 2)

        if len(original.shape) == 3:
            orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            corr_gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
        else:
            orig_gray = original
            corr_gray = corrected

        y_orig, x_orig = np.mgrid[0:h, 0:w]
        r_orig = np.sqrt((x_orig - center[0]) ** 2 + (y_orig - center[1]) ** 2)

        h_c, w_c = corrected.shape[:2]
        y_corr, x_corr = np.mgrid[0:h_c, 0:w_c]
        r_corr = np.sqrt((x_corr - w_c / 2) ** 2 + (y_corr - h_c / 2) ** 2)

        r_bins = np.linspace(0, min(r_orig.max(), r_corr.max()), 50)
        orig_profile = []
        corr_profile = []

        for i in range(len(r_bins) - 1):
            mask_orig = (r_orig >= r_bins[i]) & (r_orig < r_bins[i + 1])
            mask_corr = (r_corr >= r_bins[i]) & (r_corr < r_bins[i + 1])

            if mask_orig.any():
                orig_profile.append(orig_gray[mask_orig].mean())
            else:
                orig_profile.append(0)

            if mask_corr.any():
                corr_profile.append(corr_gray[mask_corr].mean())
            else:
                corr_profile.append(0)

        self._create_figure(2, 2)

        self._imshow(self.axes[0, 0], original, "Original")
        self._imshow(self.axes[0, 1], corrected, "Corrected")

        ax = self.axes[1, 0]
        ax.plot(r_bins[:-1], orig_profile, "b-", label="Original", linewidth=2)
        ax.plot(r_bins[:-1], corr_profile, "r-", label="Corrected", linewidth=2)
        ax.set_xlabel("Radius from Center (pixels)", fontsize=11)
        ax.set_ylabel("Mean Intensity", fontsize=11)
        ax.set_title("Radial Intensity Profile", fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        ax = self.axes[1, 1]
        ax.hist(
            orig_gray.ravel(),
            bins=50,
            alpha=0.5,
            label="Original",
            color="blue",
            density=True,
        )
        ax.hist(
            corr_gray.ravel(),
            bins=50,
            alpha=0.5,
            label="Corrected",
            color="red",
            density=True,
        )
        ax.set_xlabel("Intensity", fontsize=11)
        ax.set_ylabel("Density", fontsize=11)
        ax.set_title("Intensity Histogram", fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=self.dpi)

        plt.show()

    def close(self):
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
            self.axes = None


def visualize_correction_result(
    image_path: str,
    method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
    auto_params: bool = True,
) -> None:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    corrected = correct_fisheye_image(image, method=method, auto_params=auto_params)

    visualizer = FisheyeVisualizer()
    visualizer.show_image_pair(image, corrected)
    visualizer.close()


def compare_all_methods(image_path: str) -> None:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    visualizer = FisheyeVisualizer(figsize=(18, 6))
    visualizer.show_all_methods(image)
    visualizer.close()
