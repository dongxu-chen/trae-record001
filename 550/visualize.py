import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from typing import Optional, Tuple, List


def colormap_disparity(disparity: np.ndarray, vmin: Optional[float] = None,
                       vmax: Optional[float] = None, cmap: str = "jet") -> np.ndarray:
    valid = disparity[disparity > 0]
    if vmin is None:
        vmin = valid.min() if valid.size > 0 else 0
    if vmax is None:
        vmax = valid.max() if valid.size > 0 else 1
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    colored = cmap_obj(norm(disparity))
    colored[disparity <= 0] = [0, 0, 0, 1]
    return (colored[:, :, :3] * 255).astype(np.uint8)


def colormap_depth(depth: np.ndarray, vmin: Optional[float] = None,
                   vmax: Optional[float] = None, cmap: str = "plasma") -> np.ndarray:
    valid = depth[depth > 0]
    if vmin is None:
        vmin = valid.min() if valid.size > 0 else 0
    if vmax is None:
        vmax = valid.max() if valid.size > 0 else 1
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    colored = cmap_obj(norm(depth))
    colored[depth <= 0] = [0, 0, 0, 1]
    return (colored[:, :, :3] * 255).astype(np.uint8)


def plot_stereo_pair(img_l: np.ndarray, img_r: np.ndarray,
                     titles: Tuple[str, str] = ("Left", "Right"),
                     figsize: Tuple[int, int] = (12, 5), save_path: Optional[str] = None) -> None:
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    if len(img_l.shape) == 2:
        axes[0].imshow(img_l, cmap="gray")
    else:
        axes[0].imshow(cv2_color_to_rgb(img_l))
    axes[0].set_title(titles[0])
    axes[0].axis("off")
    if len(img_r.shape) == 2:
        axes[1].imshow(img_r, cmap="gray")
    else:
        axes[1].imshow(cv2_color_to_rgb(img_r))
    axes[1].set_title(titles[1])
    axes[1].axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_disparity(disparity: np.ndarray, title: str = "Disparity Map",
                   vmin: Optional[float] = None, vmax: Optional[float] = None,
                   cmap: str = "jet", figsize: Tuple[int, int] = (8, 6),
                   save_path: Optional[str] = None) -> None:
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    valid = disparity[disparity > 0]
    if vmin is None:
        vmin = valid.min() if valid.size > 0 else 0
    if vmax is None:
        vmax = valid.max() if valid.size > 0 else 1
    im = ax.imshow(disparity, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.axis("off")
    plt.colorbar(im, ax=ax, label="Disparity (pixels)")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_depth(depth: np.ndarray, title: str = "Depth Map",
               vmin: Optional[float] = None, vmax: Optional[float] = None,
               cmap: str = "plasma", figsize: Tuple[int, int] = (8, 6),
               save_path: Optional[str] = None, unit: str = "m") -> None:
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    valid = depth[depth > 0]
    if vmin is None:
        vmin = valid.min() if valid.size > 0 else 0
    if vmax is None:
        vmax = valid.max() if valid.size > 0 else 1
    im = ax.imshow(depth, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.axis("off")
    plt.colorbar(im, ax=ax, label=f"Depth ({unit})")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_comparison(images: List[np.ndarray], titles: List[str],
                    cmaps: Optional[List[str]] = None,
                    figsize: Optional[Tuple[int, int]] = None,
                    save_path: Optional[str] = None) -> None:
    n = len(images)
    if figsize is None:
        figsize = (5 * n, 5)
    fig, axes = plt.subplots(1, n, figsize=figsize)
    if n == 1:
        axes = [axes]
    for i, (img, title) in enumerate(zip(images, titles)):
        cmap = cmaps[i] if cmaps and i < len(cmaps) else ("gray" if len(img.shape) == 2 else None)
        if len(img.shape) == 2:
            axes[i].imshow(img, cmap=cmap)
        else:
            axes[i].imshow(img)
        axes[i].set_title(title)
        axes[i].axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_pipeline_results(results: dict, save_path: Optional[str] = None) -> None:
    has_conf = results.get("confidence") is not None
    has_grad = results.get("gradient") is not None
    ncols = 4 if (has_conf or has_grad) else 3
    fig, axes = plt.subplots(2, ncols, figsize=(6 * ncols, 12))

    rect_l = results.get("rectified_left")
    if rect_l is not None:
        if len(rect_l.shape) == 2:
            axes[0, 0].imshow(rect_l, cmap="gray")
        else:
            axes[0, 0].imshow(cv2_color_to_rgb(rect_l))
    axes[0, 0].set_title("Rectified Left")
    axes[0, 0].axis("off")

    disp_raw = results.get("disparity_raw")
    if disp_raw is not None:
        im1 = axes[0, 1].imshow(disp_raw, cmap="jet")
        plt.colorbar(im1, ax=axes[0, 1], fraction=0.046)
    axes[0, 1].set_title("Raw Disparity (Adaptive SGM)")
    axes[0, 1].axis("off")

    disp_filt = results.get("disparity_filtered")
    if disp_filt is not None:
        im2 = axes[0, 2].imshow(disp_filt, cmap="jet")
        plt.colorbar(im2, ax=axes[0, 2], fraction=0.046)
    axes[0, 2].set_title("Filtered Disparity")
    axes[0, 2].axis("off")

    if has_conf or has_grad:
        confidence = results.get("confidence")
        gradient = results.get("gradient")
        if confidence is not None:
            im_conf = axes[0, 3].imshow(confidence, cmap="RdYlGn", vmin=0, vmax=1)
            plt.colorbar(im_conf, ax=axes[0, 3], fraction=0.046)
            axes[0, 3].set_title("Confidence Map")
        elif gradient is not None:
            im_grad = axes[0, 3].imshow(gradient, cmap="hot")
            plt.colorbar(im_grad, ax=axes[0, 3], fraction=0.046)
            axes[0, 3].set_title("Gradient Map")
        axes[0, 3].axis("off")

    depth = results.get("depth")
    depth_col = 0
    if depth is not None:
        im3 = axes[1, depth_col].imshow(depth, cmap="plasma")
        plt.colorbar(im3, ax=axes[1, depth_col], fraction=0.046)
    axes[1, depth_col].set_title("Depth Map")
    axes[1, depth_col].axis("off")

    points = results.get("points_3d")
    colors = results.get("colors")
    pt_col = 1
    if points is not None and colors is not None:
        mask = points[:, 2] > 0
        if mask.sum() > 5000:
            idx = np.random.choice(mask.sum(), 5000, replace=False)
            pts = points[mask][idx]
            clrs = colors[mask][idx]
        else:
            pts = points[mask] if mask.any() else points
            clrs = colors[mask] if mask.any() else colors
        axes[1, pt_col].scatter(pts[:, 0], pts[:, 2], c=clrs, s=0.5, marker=".")
        axes[1, pt_col].set_xlabel("X")
        axes[1, pt_col].set_ylabel("Z (Depth)")
        axes[1, pt_col].invert_yaxis()
    axes[1, pt_col].set_title("Point Cloud (XZ, original colors)")
    axes[1, pt_col].set_aspect("equal")

    info_col = 2
    if has_conf:
        conf_col = 2
        confidence = results.get("confidence")
        gradient = results.get("gradient")
        if gradient is not None:
            im_g = axes[1, conf_col].imshow(gradient, cmap="hot")
            plt.colorbar(im_g, ax=axes[1, conf_col], fraction=0.046)
            axes[1, conf_col].set_title("Gradient Map")
        axes[1, conf_col].axis("off")
        info_col = 3

    for c in range(info_col, ncols):
        axes[1, c].axis("off")

    axes[1, info_col].axis("off")
    info_text = "Adaptive SGM Pipeline\n"
    info_text += f"Disparity range: [{disp_raw.min():.1f}, {disp_raw.max():.1f}]\n" if disp_raw is not None else ""
    info_text += f"Depth range: [{depth[depth>0].min():.2f}, {depth[depth>0].max():.2f}] m\n" if depth is not None and (depth > 0).any() else ""
    info_text += f"Valid points: {points.shape[0]}\n" if points is not None else ""
    confidence = results.get("confidence")
    if confidence is not None:
        info_text += f"High-conf pixels: {(confidence > 0.3).sum()}\n"
    axes[1, info_col].text(0.1, 0.5, info_text, fontsize=11, family="monospace",
                    verticalalignment="center", transform=axes[1, info_col].transAxes)
    axes[1, info_col].set_title("Statistics")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def cv2_color_to_rgb(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3 and img.shape[2] == 3:
        return img[:, :, ::-1]
    return img


def visualize_point_cloud_open3d(points: np.ndarray, colors: np.ndarray) -> None:
    try:
        import open3d as o3d
    except ImportError:
        print("Open3D not installed. Skipping 3D visualization.")
        return
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    o3d.visualization.draw_geometries([pcd], window_name="3D Point Cloud")


def save_point_cloud_ply(points: np.ndarray, colors: np.ndarray, filepath: str) -> None:
    try:
        import open3d as o3d
    except ImportError:
        _save_ply_ascii(points, colors, filepath)
        return
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(filepath, pcd)


def _save_ply_ascii(points: np.ndarray, colors: np.ndarray, filepath: str) -> None:
    n = points.shape[0]
    with open(filepath, "w") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for i in range(n):
            c = (colors[i] * 255).astype(int)
            f.write(f"{points[i,0]:.6f} {points[i,1]:.6f} {points[i,2]:.6f} {c[0]} {c[1]} {c[2]}\n")
