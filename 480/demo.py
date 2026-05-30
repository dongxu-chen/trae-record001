import sys
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.widgets import Button, RectangleSelector

from color_transfer import (
    ColorSpace,
    reinhard_transfer,
    GMMColorTransfer,
    create_region_mask,
    create_color_range_mask,
    create_segmentation_mask,
    feather_mask,
    mask_weighted_blend,
    local_color_transfer,
    multi_region_transfer,
    selective_color_transfer,
)
from video_transfer import VideoColorTransfer, process_video_with_reference
from style_lut import StylePalette, LUT3D


def generate_sample_images():
    h, w = 256, 384
    rows = np.arange(h).reshape(h, 1)
    cols = np.arange(w).reshape(1, w)

    ch_b = (50 + 150 * rows / h).astype(np.uint8)
    ch_g = (100 + 100 * cols / w).astype(np.uint8)
    ch_r = (180 - 80 * (rows + cols) / (h + w)).astype(np.uint8)
    source = np.stack([ch_b, ch_g, ch_r], axis=2).astype(np.uint8)
    source = np.broadcast_to(source, (h, w, 3)).copy()

    noise = np.random.randint(0, 20, (h, w, 3), dtype=np.uint8)
    source = cv2.add(source, noise)
    source = cv2.GaussianBlur(source, (5, 5), 1)
    cv2.circle(source, (96, 128), 60, (200, 180, 50), -1)
    cv2.rectangle(source, (200, 60), (340, 200), (50, 200, 100), -1)

    ch_b2 = (200 - 100 * rows / h).astype(np.uint8)
    ch_g2 = (50 + 150 * cols / w).astype(np.uint8)
    ch_r2 = (150 + 80 * (rows + cols) / (h + w)).astype(np.uint8)
    reference = np.stack([ch_b2, ch_g2, ch_r2], axis=2).astype(np.uint8)
    reference = np.broadcast_to(reference, (h, w, 3)).copy()

    ref_noise = np.random.randint(0, 15, (h, w, 3), dtype=np.uint8)
    reference = cv2.add(reference, ref_noise)
    reference = cv2.GaussianBlur(reference, (5, 5), 1)
    cv2.circle(reference, (96, 128), 60, (30, 80, 220), -1)
    cv2.rectangle(reference, (200, 60), (340, 200), (220, 100, 50), -1)

    return source, reference


def demo_basic_transfer(source, reference):
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("Basic Color Transfer - Reinhard Method (Multiple Color Spaces)", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference Image")
    axes[0, 1].axis("off")

    color_spaces = [ColorSpace.LAB, ColorSpace.RGB, ColorSpace.HSV, ColorSpace.YCRCB]
    cs_names = ["Lab", "RGB", "HSV", "YCrCb"]

    for idx, (cs, name) in enumerate(zip(color_spaces, cs_names)):
        result = reinhard_transfer(source, reference, color_space=cs)
        axes[0 if idx < 2 else 1, 2 + idx if idx < 2 else idx - 2].imshow(
            cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        )
        axes[0 if idx < 2 else 1, 2 + idx if idx < 2 else idx - 2].set_title(f"Reinhard ({name})")
        axes[0 if idx < 2 else 1, 2 + idx if idx < 2 else idx - 2].axis("off")

    for i in range(2):
        for j in range(4):
            if not axes[i, j].images:
                axes[i, j].axis("off")

    plt.tight_layout()
    plt.savefig("demo_basic_transfer.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Basic transfer demo saved: demo_basic_transfer.png")


def demo_gmm_transfer(source, reference):
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("GMM-based Color Transfer (Lab Space)", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference Image")
    axes[0, 1].axis("off")

    n_components_list = [2, 3, 5]
    for idx, n_comp in enumerate(n_components_list):
        gmm = GMMColorTransfer(n_components=n_comp, color_space=ColorSpace.LAB)
        result = gmm.fit_transform(source, reference)
        row, col = 0 if idx < 1 else 1, 2 if idx == 0 else idx - 1
        axes[row, col].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[row, col].set_title(f"GMM (n={n_comp})")
        axes[row, col].axis("off")

    for idx, n_comp in enumerate([3, 5]):
        gmm = GMMColorTransfer(n_components=n_comp, color_space=ColorSpace.LAB)
        result = gmm.fit_transform(source, reference, blend=0.6)
        row, col = 1, idx + 1
        axes[row, col].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[row, col].set_title(f"GMM (n={n_comp}, blend=0.6)")
        axes[row, col].axis("off")

    plt.tight_layout()
    plt.savefig("demo_gmm_transfer.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] GMM transfer demo saved: demo_gmm_transfer.png")


def demo_local_transfer(source, reference):
    h, w = source.shape[:2]

    source_mask1 = np.zeros((h, w), dtype=np.uint8)
    source_mask1[30:190, 30:160] = 255

    source_mask2 = np.zeros((h, w), dtype=np.uint8)
    source_mask2[60:200, 190:360] = 255

    ref_mask = np.ones((reference.shape[0], reference.shape[1]), dtype=np.uint8) * 255

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("Local / Region-Guided Color Transfer", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    src_with_mask = source.copy()
    src_with_mask[source_mask1 > 0] = [0, 255, 0]
    src_overlay = cv2.addWeighted(source, 0.7, src_with_mask, 0.3, 0)
    axes[0, 1].imshow(cv2.cvtColor(src_overlay, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Source + Region Mask 1")
    axes[0, 1].axis("off")

    src_with_mask2 = source.copy()
    src_with_mask2[source_mask2 > 0] = [255, 0, 255]
    src_overlay2 = cv2.addWeighted(source, 0.7, src_with_mask2, 0.3, 0)
    axes[0, 2].imshow(cv2.cvtColor(src_overlay2, cv2.COLOR_BGR2RGB))
    axes[0, 2].set_title("Source + Region Mask 2")
    axes[0, 2].axis("off")

    axes[0, 3].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 3].set_title("Reference Image")
    axes[0, 3].axis("off")

    result_r1 = local_color_transfer(
        source, reference, source_mask1, ref_mask,
        color_space=ColorSpace.LAB, method="reinhard",
    )
    axes[1, 0].imshow(cv2.cvtColor(result_r1, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Local Reinhard (Region 1)")
    axes[1, 0].axis("off")

    result_gmm1 = local_color_transfer(
        source, reference, source_mask1, ref_mask,
        color_space=ColorSpace.LAB, method="gmm", n_components=3,
    )
    axes[1, 1].imshow(cv2.cvtColor(result_gmm1, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title("Local GMM (Region 1)")
    axes[1, 1].axis("off")

    result_r2 = local_color_transfer(
        source, reference, source_mask2, ref_mask,
        color_space=ColorSpace.LAB, method="reinhard",
    )
    axes[1, 2].imshow(cv2.cvtColor(result_r2, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title("Local Reinhard (Region 2)")
    axes[1, 2].axis("off")

    result_multi = multi_region_transfer(
        source, reference,
        [source_mask1, source_mask2],
        [ref_mask, ref_mask],
        color_space=ColorSpace.LAB, method="reinhard",
    )
    axes[1, 3].imshow(cv2.cvtColor(result_multi, cv2.COLOR_BGR2RGB))
    axes[1, 3].set_title("Multi-Region Transfer")
    axes[1, 3].axis("off")

    plt.tight_layout()
    plt.savefig("demo_local_transfer.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Local transfer demo saved: demo_local_transfer.png")


def demo_selective_color(source, reference):
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle("Selective Color Transfer (Hue-Range Guided)", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference Image")
    axes[0, 1].axis("off")

    result_warm = selective_color_transfer(
        source, reference,
        target_hue_range=(10, 50),
        color_space=ColorSpace.LAB, method="reinhard",
    )
    axes[1, 0].imshow(cv2.cvtColor(result_warm, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Select Warm Hues (10°-50°)")
    axes[1, 0].axis("off")

    result_cool = selective_color_transfer(
        source, reference,
        target_hue_range=(100, 140),
        color_space=ColorSpace.LAB, method="reinhard",
    )
    axes[1, 1].imshow(cv2.cvtColor(result_cool, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title("Select Cool Hues (100°-140°)")
    axes[1, 1].axis("off")

    plt.tight_layout()
    plt.savefig("demo_selective_color.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Selective color demo saved: demo_selective_color.png")


def demo_color_distribution(source, reference):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Color Distribution Analysis (Lab Space)", fontsize=16, fontweight="bold")

    src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2Lab).astype(np.float64)
    ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2Lab).astype(np.float64)

    result = reinhard_transfer(source, reference, ColorSpace.LAB)
    res_lab = cv2.cvtColor(result, cv2.COLOR_BGR2Lab).astype(np.float64)

    channel_names = ["L (Lightness)", "a (Green-Red)", "b (Blue-Yellow)"]
    colors_src = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    colors_ref = ["#d62728", "#9467bd", "#8c564b"]
    colors_res = ["#e377c2", "#7f7f7f", "#bcbd22"]

    for c in range(3):
        ax = axes[c // 2 if c < 2 else 1, c if c < 2 else 2]
        src_ch = src_lab[:, :, c].flatten()
        ref_ch = ref_lab[:, :, c].flatten()
        res_ch = res_lab[:, :, c].flatten()

        ax.hist(src_ch, bins=80, alpha=0.5, label="Source", color=colors_src[c], density=True)
        ax.hist(ref_ch, bins=80, alpha=0.5, label="Reference", color=colors_ref[c], density=True)
        ax.hist(res_ch, bins=80, alpha=0.5, label="Result", color=colors_res[c], density=True)
        ax.set_title(channel_names[c])
        ax.legend(fontsize=8)

    axes[1, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Source")
    axes[1, 0].axis("off")

    axes[1, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title("Reference")
    axes[1, 1].axis("off")

    axes[1, 2].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title("Result")
    axes[1, 2].axis("off")

    plt.tight_layout()
    plt.savefig("demo_color_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Color distribution demo saved: demo_color_distribution.png")


def demo_blend_comparison(source, reference):
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("Blend Factor Comparison (Reinhard + Lab)", fontsize=16, fontweight="bold")

    blend_values = [0.2, 0.4, 0.6, 0.8, 1.0]

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference")
    axes[0, 1].axis("off")

    positions = [(0, 2), (1, 0), (1, 1), (1, 2)]
    for idx, blend in enumerate(blend_values[:4]):
        row, col = positions[idx]
        result = reinhard_transfer(source, reference, ColorSpace.LAB, blend=blend)
        axes[row, col].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[row, col].set_title(f"Blend = {blend}")
        axes[row, col].axis("off")

    plt.tight_layout()
    plt.savefig("demo_blend_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Blend comparison demo saved: demo_blend_comparison.png")


def demo_gmm_components_analysis(source, reference):
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("GMM Component Analysis (Lab a-b plane)", fontsize=16, fontweight="bold")

    ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2Lab).astype(np.float64)
    ref_pixels = ref_lab.reshape(-1, 3)

    from sklearn.mixture import GaussianMixture

    for idx, n_comp in enumerate([2, 3, 4, 5]):
        gmm = GaussianMixture(n_components=n_comp, random_state=42)
        labels = gmm.fit_predict(ref_pixels[:, 1:3])

        row, col = idx // 4, idx
        if idx >= 4:
            break
        row, col = 0, idx

        scatter = axes[row, col].scatter(
            ref_pixels[::10, 1], ref_pixels[::10, 2],
            c=labels[::10], cmap="viridis", alpha=0.3, s=2,
        )
        axes[row, col].set_xlabel("a*")
        axes[row, col].set_ylabel("b*")
        axes[row, col].set_title(f"Ref GMM (n={n_comp})")
        for k in range(n_comp):
            mean = gmm.means_[k]
            axes[row, col].plot(mean[0], mean[1], "r+", markersize=15, markeredgewidth=2)

    axes[1, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Source")
    axes[1, 0].axis("off")

    axes[1, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title("Reference")
    axes[1, 1].axis("off")

    gmm3 = GMMColorTransfer(n_components=3, color_space=ColorSpace.LAB)
    result3 = gmm3.fit_transform(source, reference)
    axes[1, 2].imshow(cv2.cvtColor(result3, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title("GMM Transfer (n=3)")
    axes[1, 2].axis("off")

    gmm5 = GMMColorTransfer(n_components=5, color_space=ColorSpace.LAB)
    result5 = gmm5.fit_transform(source, reference)
    axes[1, 3].imshow(cv2.cvtColor(result5, cv2.COLOR_BGR2RGB))
    axes[1, 3].set_title("GMM Transfer (n=5)")
    axes[1, 3].axis("off")

    plt.tight_layout()
    plt.savefig("demo_gmm_analysis.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] GMM analysis demo saved: demo_gmm_analysis.png")


def interactive_region_selector(source, reference):
    print("\n" + "=" * 60)
    print("Interactive Region Selection Guide")
    print("=" * 60)
    print("This demo shows how region selection works for color transfer.")
    print("In a real application, users would draw rectangles on the image.")
    print()

    h, w = source.shape[:2]

    regions_source = [(30, 30, 160, 190)]
    regions_reference = [(50, 50, 200, 200)]

    source_mask = create_region_mask(source.shape, regions_source)
    reference_mask = create_region_mask(reference.shape, regions_reference)

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("User-Guided Region Selection → Color Transfer", fontsize=16, fontweight="bold")

    src_overlay = source.copy()
    src_with_mask = src_overlay.copy()
    src_with_mask[source_mask > 0] = [0, 255, 0]
    src_overlay = cv2.addWeighted(source, 0.6, src_with_mask, 0.4, 0)

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Step 1: Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(src_overlay, cv2.COLOR_BGR2RGB))
    rect1 = Rectangle((30, 30), 130, 160, linewidth=2, edgecolor="lime", facecolor="none")
    axes[0, 1].add_patch(rect1)
    axes[0, 1].set_title("Step 2: Select Source Region")
    axes[0, 1].axis("off")

    ref_overlay = reference.copy()
    ref_with_mask = ref_overlay.copy()
    ref_with_mask_resized = cv2.resize(reference_mask, (reference.shape[1], reference.shape[0]))
    ref_with_mask[ref_with_mask_resized > 0] = [0, 255, 255]
    ref_overlay = cv2.addWeighted(reference, 0.6, ref_with_mask, 0.4, 0)

    axes[0, 2].imshow(cv2.cvtColor(ref_overlay, cv2.COLOR_BGR2RGB))
    rect2 = Rectangle((50, 50), 150, 150, linewidth=2, edgecolor="cyan", facecolor="none")
    axes[0, 2].add_patch(rect2)
    axes[0, 2].set_title("Step 3: Select Ref Region")
    axes[0, 2].axis("off")

    result_reinhard = local_color_transfer(
        source, reference, source_mask, reference_mask,
        ColorSpace.LAB, "reinhard",
    )
    axes[1, 0].imshow(cv2.cvtColor(result_reinhard, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Step 4: Reinhard Local Transfer")
    axes[1, 0].axis("off")

    result_gmm = local_color_transfer(
        source, reference, source_mask, reference_mask,
        ColorSpace.LAB, "gmm", n_components=3,
    )
    axes[1, 1].imshow(cv2.cvtColor(result_gmm, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title("Step 4: GMM Local Transfer")
    axes[1, 1].axis("off")

    result_full = reinhard_transfer(source, reference, ColorSpace.LAB)
    axes[1, 2].imshow(cv2.cvtColor(result_full, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title("Full Image Transfer (Comparison)")
    axes[1, 2].axis("off")

    plt.tight_layout()
    plt.savefig("demo_interactive_region.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Interactive region demo saved: demo_interactive_region.png")


def demo_segmentation_guide(source, reference):
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("Global Transfer with Segmentation Guidance", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference Image")
    axes[0, 1].axis("off")

    seg_methods = ["kmeans", "grabcut", "saliency"]
    seg_names = ["K-Means (n=3)", "GrabCut", "Saliency"]

    for idx, (method, name) in enumerate(zip(seg_methods, seg_names)):
        try:
            mask = create_segmentation_mask(source, method=method, n_segments=3)
            row, col = 0, idx + 2

            mask_overlay = source.copy()
            mask_overlay[mask > 0] = [0, 255, 0]
            overlay = cv2.addWeighted(source, 0.6, mask_overlay, 0.4, 0)
            axes[row, col].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
            axes[row, col].set_title(f"Seg Mask: {name}")
            axes[row, col].axis("off")
        except Exception as e:
            axes[0, idx + 2].text(0.5, 0.5, f"{name}\nUnavailable", ha="center", va="center", fontsize=12)
            axes[0, idx + 2].axis("off")

    result_full = reinhard_transfer(source, reference, ColorSpace.LAB)
    axes[1, 0].imshow(cv2.cvtColor(result_full, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Full Image Transfer")
    axes[1, 0].axis("off")

    for idx, (method, name) in enumerate(zip(seg_methods, seg_names)):
        try:
            result_seg = reinhard_transfer(
                source, reference, ColorSpace.LAB,
                auto_segment=method, n_segments=3,
                feather_radius=15,
            )
            row, col = 1, idx + 1
            axes[row, col].imshow(cv2.cvtColor(result_seg, cv2.COLOR_BGR2RGB))
            axes[row, col].set_title(f"Seg-Guided: {name}")
            axes[row, col].axis("off")
        except Exception as e:
            axes[1, idx + 1].text(0.5, 0.5, f"{name}\nUnavailable", ha="center", va="center", fontsize=12)
            axes[1, idx + 1].axis("off")

    axes[1, 3].axis("off")

    plt.tight_layout()
    plt.savefig("demo_segmentation_guide.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Segmentation guide demo saved: demo_segmentation_guide.png")


def demo_feather_comparison(source, reference):
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("Edge Feathering Comparison (Smooth Transition)", fontsize=16, fontweight="bold")

    h, w = source.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[50:210, 50:190] = 255

    ref_mask = np.ones(reference.shape[:2], dtype=np.uint8) * 255

    src_overlay = source.copy()
    src_overlay[mask > 0] = [0, 255, 0]
    overlay = cv2.addWeighted(source, 0.6, src_overlay, 0.4, 0)
    axes[0, 0].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    rect = Rectangle((50, 50), 140, 160, linewidth=2, edgecolor="lime", facecolor="none")
    axes[0, 0].add_patch(rect)
    axes[0, 0].set_title("Source + Transfer Region")
    axes[0, 0].axis("off")

    feather_radii = [0, 10, 25]
    for idx, radius in enumerate(feather_radii):
        feathered = feather_mask(mask, feather_radius=radius)
        row = 0 if idx == 0 else (0 if idx == 1 else 1)
        col = 1 if idx == 0 else (2 if idx == 1 else 0)

        axes[row, col].imshow(feathered, cmap="gray", vmin=0, vmax=255)
        if radius == 0:
            axes[row, col].set_title("Hard Mask (No Feather)")
        else:
            axes[row, col].set_title(f"Feather Radius = {radius}px")
        axes[row, col].axis("off")

    for idx, radius in enumerate(feather_radii):
        result = local_color_transfer(
            source, reference, mask, ref_mask,
            ColorSpace.LAB, "reinhard",
            feather_radius=radius,
        )
        row = 1
        col = idx + 1
        if col >= 3:
            col = idx

        axes[row, col].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        if radius == 0:
            axes[row, col].set_title("Hard Edge (No Feather)")
        else:
            axes[row, col].set_title(f"Feathered Edge (r={radius})")
        axes[row, col].axis("off")

    plt.tight_layout()
    plt.savefig("demo_feather_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Feather comparison demo saved: demo_feather_comparison.png")


def demo_detail_preservation(source, reference):
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle("Detail Preservation: Clamp+Scale vs Simple Clamp", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference Image")
    axes[0, 1].axis("off")

    result_preserve = reinhard_transfer(
        source, reference, ColorSpace.LAB,
        preserve_details=True, blend=1.0,
    )
    axes[0, 2].imshow(cv2.cvtColor(result_preserve, cv2.COLOR_BGR2RGB))
    axes[0, 2].set_title("Clamp+Scale (Preserve Details)")
    axes[0, 2].axis("off")

    result_clip = reinhard_transfer(
        source, reference, ColorSpace.LAB,
        preserve_details=False, blend=1.0,
    )
    axes[0, 3].imshow(cv2.cvtColor(result_clip, cv2.COLOR_BGR2RGB))
    axes[0, 3].set_title("Simple Clamp (May Lose Details)")
    axes[0, 3].axis("off")

    def compute_laplacian_var(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2Lab).astype(np.float64)
    res_p_lab = cv2.cvtColor(result_preserve, cv2.COLOR_BGR2Lab).astype(np.float64)
    res_c_lab = cv2.cvtColor(result_clip, cv2.COLOR_BGR2Lab).astype(np.float64)

    channel_names = ["L*", "a*", "b*"]
    for c in range(3):
        ax = axes[1, c]
        ax.hist(src_lab[:, :, c].flatten(), bins=60, alpha=0.5, label="Source", color="#1f77b4", density=True)
        ax.hist(res_p_lab[:, :, c].flatten(), bins=60, alpha=0.5, label="Clamp+Scale", color="#2ca02c", density=True)
        ax.hist(res_c_lab[:, :, c].flatten(), bins=60, alpha=0.5, label="Simple Clamp", color="#d62728", density=True, linestyle="--")
        ax.set_title(f"{channel_names[c]} Channel Distribution")
        ax.legend(fontsize=8)

    variance_info = (
        f"Sharpness (Laplacian Variance):\n"
        f"Source:       {compute_laplacian_var(source):.1f}\n"
        f"Clamp+Scale:  {compute_laplacian_var(result_preserve):.1f}\n"
        f"Simple Clamp: {compute_laplacian_var(result_clip):.1f}"
    )
    axes[1, 3].text(0.05, 0.5, variance_info, fontsize=11, family="monospace",
                    verticalalignment="center", transform=axes[1, 3].transAxes)
    axes[1, 3].set_title("Detail Quality Metrics")
    axes[1, 3].axis("off")

    plt.tight_layout()
    plt.savefig("demo_detail_preservation.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Detail preservation demo saved: demo_detail_preservation.png")


def generate_sample_frames(n_frames: int = 5) -> List[np.ndarray]:
    h, w = 128, 192
    frames = []
    for i in range(n_frames):
        rows = np.arange(h).reshape(h, 1)
        cols = np.arange(w).reshape(1, w)

        shift = i * 10
        ch_b = (50 + 150 * (rows + shift) / h).astype(np.uint8)
        ch_g = (100 + 100 * (cols - shift) / w).astype(np.uint8)
        ch_r = (180 - 80 * (rows + cols) / (h + w)).astype(np.uint8)

        frame = np.stack([
            np.broadcast_to(ch_b, (h, w)),
            np.broadcast_to(ch_g, (h, w)),
            np.broadcast_to(ch_r, (h, w)),
        ], axis=2)

        noise = np.random.randint(0, 15, (h, w, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)

        if i % 2 == 0:
            cv2.circle(frame, (64 + i * 5, 64), 25, (200, 180, 50), -1)
        else:
            cv2.rectangle(frame, (100 - i * 3, 40), (160, 90), (50, 200, 100), -1)

        frames.append(frame)
    return frames


def generate_reference_images(n_refs: int = 3) -> List[np.ndarray]:
    h, w = 128, 192
    refs = []

    color_schemes = [
        [(200, 50, 50), (50, 200, 50), (50, 50, 200)],
        [(255, 200, 100), (100, 200, 255), (200, 100, 200)],
        [(80, 80, 80), (180, 180, 180), (255, 255, 255)],
    ]

    rows = np.arange(h).reshape(h, 1)
    cols = np.arange(w).reshape(1, w)

    for scheme in color_schemes[:n_refs]:
        ch_b = scheme[0][0] + (scheme[1][0] - scheme[0][0]) * rows / h + (scheme[2][0] - scheme[0][0]) * cols / w
        ch_g = scheme[0][1] + (scheme[1][1] - scheme[0][1]) * rows / h + (scheme[2][1] - scheme[0][1]) * cols / w
        ch_r = scheme[0][2] + (scheme[1][2] - scheme[0][2]) * rows / h + (scheme[2][2] - scheme[0][2]) * cols / w

        img = np.stack([
            np.broadcast_to(ch_b.astype(np.uint8), (h, w)),
            np.broadcast_to(ch_g.astype(np.uint8), (h, w)),
            np.broadcast_to(ch_r.astype(np.uint8), (h, w)),
        ], axis=2)

        noise = np.random.randint(0, 10, (h, w, 3), dtype=np.uint8)
        img = cv2.add(img, noise)
        refs.append(img)

    return refs


def demo_video_transfer(source, reference):
    fig, axes = plt.subplots(3, 5, figsize=(20, 12))
    fig.suptitle("Video Color Transfer with Temporal Consistency (EMA)", fontsize=16, fontweight="bold")

    frames = generate_sample_frames(5)
    source_ref = frames[0].copy()

    h, w = frames[0].shape[:2]
    ref_for_video = cv2.resize(reference, (w, h))

    for idx, frame in enumerate(frames):
        axes[0, idx].imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        axes[0, idx].set_title(f"Frame {idx} (Original)")
        axes[0, idx].axis("off")

    transfer_no_ema = VideoColorTransfer(
        ref_for_video, ColorSpace.LAB, "reinhard",
        ema_alpha=1.0, blend=1.0,
    )
    results_no_ema = []
    for i, frame in enumerate(frames):
        results_no_ema.append(transfer_no_ema.transfer_frame(frame, frame_index=i))

    for idx, result in enumerate(results_no_ema):
        axes[1, idx].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1, idx].set_title(f"Frame {idx} (No EMA, α=1.0)")
        axes[1, idx].axis("off")

    transfer_ema = VideoColorTransfer(
        ref_for_video, ColorSpace.LAB, "reinhard",
        ema_alpha=0.2, blend=1.0,
    )
    results_ema = []
    for i, frame in enumerate(frames):
        results_ema.append(transfer_ema.transfer_frame(frame, frame_index=i))

    for idx, result in enumerate(results_ema):
        axes[2, idx].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[2, idx].set_title(f"Frame {idx} (EMA α=0.2)")
        axes[2, idx].axis("off")

    plt.tight_layout()
    plt.savefig("demo_video_transfer.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Video transfer demo saved: demo_video_transfer.png")

    def compute_frame_diff(f1, f2):
        return np.mean(np.abs(f1.astype(np.int32) - f2.astype(np.int32)))

    diff_no_ema = compute_frame_diff(results_no_ema[0], results_no_ema[-1])
    diff_ema = compute_frame_diff(results_ema[0], results_ema[-1])
    print(f"    Temporal consistency: No EMA diff={diff_no_ema:.1f}, EMA diff={diff_ema:.1f}")


def demo_style_palette(source, reference):
    fig, axes = plt.subplots(2, 5, figsize=(20, 8))
    fig.suptitle("Style Palette: Learn from Multiple References", fontsize=16, fontweight="bold")

    refs = generate_reference_images(3)

    for idx, ref in enumerate(refs):
        axes[0, idx].imshow(cv2.cvtColor(ref, cv2.COLOR_BGR2RGB))
        axes[0, idx].set_title(f"Reference {idx + 1}")
        axes[0, idx].axis("off")

    palette = StylePalette(n_colors=8, color_space=ColorSpace.LAB)
    palette.fit(refs, weights=[0.5, 0.3, 0.2], sample_ratio=0.5)

    palette_img = palette.visualize_palette(swatch_size=40)
    axes[0, 3].imshow(palette_img)
    axes[0, 3].set_title("Learned Palette (8 colors)")
    axes[0, 3].axis("off")

    axes[0, 4].axis("off")

    axes[1, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("Source Image")
    axes[1, 0].axis("off")

    for idx, blend in enumerate([0.4, 0.7, 1.0]):
        result = palette.transfer(source, blend=blend)
        axes[1, idx + 1].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1, idx + 1].set_title(f"Style Transfer (blend={blend})")
        axes[1, idx + 1].axis("off")

    ref_resized = cv2.resize(refs[0], (source.shape[1], source.shape[0]))
    result_single = reinhard_transfer(source, ref_resized, ColorSpace.LAB)
    axes[1, 4].imshow(cv2.cvtColor(result_single, cv2.COLOR_BGR2RGB))
    axes[1, 4].set_title("Single Ref (Comparison)")
    axes[1, 4].axis("off")

    plt.tight_layout()
    plt.savefig("demo_style_palette.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] Style palette demo saved: demo_style_palette.png")


def demo_lut_export(source, reference):
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    fig.suptitle("3D LUT Export & Application", fontsize=16, fontweight="bold")

    axes[0, 0].imshow(cv2.cvtColor(source, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title("Source Image")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title("Reference (Style)")
    axes[0, 1].axis("off")

    result_direct = reinhard_transfer(source, reference, ColorSpace.LAB, blend=1.0)
    axes[0, 2].imshow(cv2.cvtColor(result_direct, cv2.COLOR_BGR2RGB))
    axes[0, 2].set_title("Direct Transfer")
    axes[0, 2].axis("off")

    def transfer_fn(img):
        return reinhard_transfer(img, reference, ColorSpace.LAB, blend=1.0)

    lut = LUT3D.from_transfer_function(transfer_fn, size=33)

    lut.save_cube("color_transfer_33.cube", name="ColorTransfer_33")
    lut.save_png("color_transfer_hald.png", hald_size=33)
    print(f"    LUT saved: color_transfer_33.cube (33^3 = {33**3} entries)")
    print(f"    Hald CLUT saved: color_transfer_hald.png")

    result_lut = lut.apply(source)
    axes[0, 3].imshow(cv2.cvtColor(result_lut, cv2.COLOR_BGR2RGB))
    diff = np.mean(np.abs(result_direct.astype(np.int32) - result_lut.astype(np.int32)))
    axes[0, 3].set_title(f"LUT Applied (diff={diff:.1f})")
    axes[0, 3].axis("off")

    lut_loaded = LUT3D.load_cube("color_transfer_33.cube")
    result_reloaded = lut_loaded.apply(source)
    axes[1, 0].imshow(cv2.cvtColor(result_reloaded, cv2.COLOR_BGR2RGB))
    axes[1, 0].set_title("LUT Loaded + Applied")
    axes[1, 0].axis("off")

    def transfer_fn2(img):
        return reinhard_transfer(img, reference, ColorSpace.LAB, blend=0.5)

    lut_17 = LUT3D.from_transfer_function(transfer_fn2, size=17)
    lut_17.save_cube("color_transfer_17.cube", name="ColorTransfer_17")
    result_17 = lut_17.apply(source)
    axes[1, 1].imshow(cv2.cvtColor(result_17, cv2.COLOR_BGR2RGB))
    axes[1, 1].set_title(f"LUT 17^3 (blend=0.5)")
    axes[1, 1].axis("off")

    hald_img = cv2.imread("color_transfer_hald.png")
    axes[1, 2].imshow(cv2.cvtColor(hald_img, cv2.COLOR_BGR2RGB))
    axes[1, 2].set_title("Hald CLUT Image")
    axes[1, 2].axis("off")

    lut_65 = LUT3D.from_transfer_function(transfer_fn, size=65)
    result_65 = lut_65.apply(source)
    axes[1, 3].imshow(cv2.cvtColor(result_65, cv2.COLOR_BGR2RGB))
    axes[1, 3].set_title(f"LUT 65^3 (Higher Precision)")
    axes[1, 3].axis("off")

    plt.tight_layout()
    plt.savefig("demo_lut_export.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[OK] LUT export demo saved: demo_lut_export.png")


def main():
    print("=" * 60)
    print("  Image Color Transfer Algorithm Demo")
    print("  NumPy + OpenCV + Lab + GMM + Matplotlib")
    print("  (Enhanced: Segmentation Guide, Feathering, Detail Preserve)")
    print("  (NEW: Video Transfer, Style Palette, 3D LUT Export)")
    print("=" * 60)
    print()

    print("Generating sample images...")
    source, reference = generate_sample_images()
    cv2.imwrite("source.png", source)
    cv2.imwrite("reference.png", reference)
    print("[OK] Sample images saved: source.png, reference.png")
    print()

    print("Running demos...\n")

    print("[1/12] Basic color transfer (Reinhard, multiple color spaces)...")
    demo_basic_transfer(source, reference)

    print("[2/12] GMM-based color transfer...")
    demo_gmm_transfer(source, reference)

    print("[3/12] Local / region-guided color transfer...")
    demo_local_transfer(source, reference)

    print("[4/12] Selective color transfer (hue range)...")
    demo_selective_color(source, reference)

    print("[5/12] Color distribution analysis...")
    demo_color_distribution(source, reference)

    print("[6/12] Blend factor & GMM component analysis...")
    demo_blend_comparison(source, reference)
    demo_gmm_components_analysis(source, reference)

    print("[7/12] Segmentation-guided global transfer...")
    demo_segmentation_guide(source, reference)

    print("[8/12] Edge feathering comparison...")
    demo_feather_comparison(source, reference)

    print("[9/12] Detail preservation (clamp+scale vs simple clamp)...")
    demo_detail_preservation(source, reference)

    print()
    print("=== NEW ENHANCEMENTS ===")
    print()

    print("[10/12] NEW: Video color transfer with EMA temporal consistency...")
    demo_video_transfer(source, reference)

    print("[11/12] NEW: Style palette from multiple references...")
    demo_style_palette(source, reference)

    print("[12/12] NEW: 3D LUT export and application...")
    demo_lut_export(source, reference)

    print()
    print("Interactive region selection demo...")
    interactive_region_selector(source, reference)

    print()
    print("=" * 60)
    print("  All demos completed!")
    print("  Generated files:")
    print("    - source.png / reference.png")
    print("    - demo_basic_transfer.png")
    print("    - demo_gmm_transfer.png")
    print("    - demo_local_transfer.png")
    print("    - demo_selective_color.png")
    print("    - demo_color_distribution.png")
    print("    - demo_blend_comparison.png")
    print("    - demo_gmm_analysis.png")
    print("    - demo_interactive_region.png")
    print("    - demo_segmentation_guide.png")
    print("    - demo_feather_comparison.png")
    print("    - demo_detail_preservation.png")
    print("  -- NEW FEATURES --")
    print("    - demo_video_transfer.png")
    print("    - demo_style_palette.png")
    print("    - demo_lut_export.png")
    print("    - color_transfer_33.cube  (3D LUT)")
    print("    - color_transfer_17.cube  (3D LUT)")
    print("    - color_transfer_hald.png (Hald CLUT)")
    print("=" * 60)


if __name__ == "__main__":
    main()
