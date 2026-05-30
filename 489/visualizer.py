import io
import base64
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from scipy.ndimage import gaussian_filter
from scipy.interpolate import griddata


def find_local_extrema(grid_z, neighbor_size=3):
    from scipy.ndimage import maximum_filter, minimum_filter
    half = neighbor_size // 2
    footprint = np.ones((neighbor_size, neighbor_size), dtype=bool)
    nan_mask = np.isnan(grid_z)
    z_filled = np.where(nan_mask, -np.inf, grid_z)
    local_max = (grid_z == maximum_filter(z_filled, footprint=footprint)) & ~nan_mask
    z_filled = np.where(nan_mask, np.inf, grid_z)
    local_min = (grid_z == minimum_filter(z_filled, footprint=footprint)) & ~nan_mask
    return local_max | local_min


def adaptive_smooth(grid_z, smooth_level=1.0, preserve_extrema=True,
                    extremum_neighbor=3, adaptive_gradient=True):
    z = np.array(grid_z, dtype=float)
    nan_mask = np.isnan(z)
    z_filled = np.where(nan_mask, np.nanmedian(z), z)

    if adaptive_gradient:
        grad_y, grad_x = np.gradient(z_filled)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        if grad_mag.max() > 0:
            grad_norm = grad_mag / (grad_mag.max() + 1e-10)
            local_sigma = smooth_level * (1.0 - 0.7 * grad_norm)
            local_sigma = np.clip(local_sigma, 0.3, smooth_level * 1.5)
            mean_sigma = np.mean(local_sigma)
        else:
            mean_sigma = smooth_level
    else:
        mean_sigma = smooth_level

    z_smooth = gaussian_filter(z_filled, sigma=mean_sigma)
    z_smooth[nan_mask] = np.nan

    if preserve_extrema:
        is_extremum = find_local_extrema(z, neighbor_size=extremum_neighbor)
        z_smooth[is_extremum & ~nan_mask] = z[is_extremum & ~nan_mask]

    return z_smooth


def plot_contour(grid_x, grid_y, grid_z, station_x=None, station_y=None,
                 station_z=None, title="Spatial Interpolation",
                 label="Value", levels=15, cmap="RdYlBu_r",
                 figsize=(10, 8), dpi=120,
                 adaptive_smooth_level=0.0,
                 preserve_extrema=True):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    z_plot = grid_z
    if adaptive_smooth_level > 0.01:
        z_plot = adaptive_smooth(grid_z,
                                  smooth_level=adaptive_smooth_level,
                                  preserve_extrema=preserve_extrema)

    z_min = np.nanmin(z_plot)
    z_max = np.nanmax(z_plot)
    if z_min == z_max:
        z_max = z_min + 1.0
    level_vals = np.linspace(z_min, z_max, levels + 1)

    cf = ax.contourf(grid_x, grid_y, z_plot, levels=level_vals, cmap=cmap, extend="both")
    cs = ax.contour(grid_x, grid_y, z_plot, levels=level_vals, colors="k", linewidths=0.4, alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%.1f")

    cbar = fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.03)
    cbar.set_label(label, fontsize=11)

    if adaptive_smooth_level > 0.01:
        is_ext = find_local_extrema(grid_z)
        ext_mask = is_ext & ~np.isnan(grid_z)
        ext_x = grid_x[ext_mask]
        ext_y = grid_y[ext_mask]
        ext_z = grid_z[ext_mask]
        if len(ext_x) > 0:
            ax.scatter(ext_x, ext_y, c="white", s=22, edgecolors="black",
                       linewidths=0.8, zorder=6, label="Preserved Extremes",
                       marker="o", facecolors="none")

    if station_x is not None and station_y is not None:
        ax.scatter(station_x, station_y, c="black", s=28, edgecolors="white",
                   linewidths=0.8, zorder=5, label="Stations")
        if station_z is not None:
            for sx, sy, sz in zip(station_x, station_y, station_z):
                ax.annotate(f"{sz:.1f}", (sx, sy), textcoords="offset points",
                            xytext=(4, 4), fontsize=7, color="black",
                            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7, ec="none"))
        ax.legend(loc="upper right", fontsize=9)

    ax.set_xlabel("Longitude", fontsize=11)
    ax.set_ylabel("Latitude", fontsize=11)
    if adaptive_smooth_level > 0.01:
        title = f"{title} (smoothing={adaptive_smooth_level:.1f}"
        title += ", extrema preserved)" if preserve_extrema else ")"
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig


def plot_error_heatmap(grid_x, grid_y, error_grid, station_x=None, station_y=None,
                       station_error=None, title="Spatial Error Distribution",
                       label="Absolute Error", cmap="YlOrRd",
                       figsize=(10, 8), dpi=120):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    err_min = np.nanmin(error_grid)
    err_max = np.nanmax(error_grid)
    if err_min == err_max:
        err_max = err_min + 1.0

    cf = ax.contourf(grid_x, grid_y, error_grid, levels=15, cmap=cmap, extend="max")
    cs = ax.contour(grid_x, grid_y, error_grid, levels=15, colors="k",
                    linewidths=0.3, alpha=0.5)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.2f")
    cbar = fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.03)
    cbar.set_label(label, fontsize=11)

    if station_x is not None and station_y is not None:
        if station_error is not None:
            err_arr = np.array(station_error)
            norm = Normalize(vmin=err_min, vmax=err_max)
            cmap_obj = plt.get_cmap(cmap)
            colors = cmap_obj(norm(err_arr))
            sizes = 30 + 50 * norm(err_arr)
            ax.scatter(station_x, station_y, c=colors, s=sizes,
                       edgecolors="black", linewidths=0.8, zorder=5,
                       label="Station Error")
            for sx, sy, se in zip(station_x, station_y, station_error):
                ax.annotate(f"{se:.1f}", (sx, sy), textcoords="offset points",
                            xytext=(4, 4), fontsize=7, color="black",
                            bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                      alpha=0.7, ec="none"))
        else:
            ax.scatter(station_x, station_y, c="black", s=28,
                       edgecolors="white", linewidths=0.8, zorder=5,
                       label="Stations")
        ax.legend(loc="upper right", fontsize=9)

    ax.set_xlabel("Longitude", fontsize=11)
    ax.set_ylabel("Latitude", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig


def interpolate_error_to_grid(grid_x, grid_y, station_x, station_y, station_error,
                              method="idw", power=2.0):
    sx = np.asarray(station_x)
    sy = np.asarray(station_y)
    se = np.asarray(station_error)

    ny, nx = grid_x.shape
    ns = len(sx)

    gx_flat = grid_x.reshape(-1, 1)
    gy_flat = grid_y.reshape(-1, 1)
    sx_br = sx.reshape(1, -1)
    sy_br = sy.reshape(1, -1)
    se_br = se.reshape(1, -1)

    dx = sx_br - gx_flat
    dy = sy_br - gy_flat
    dist = np.sqrt(dx**2 + dy**2)

    zero_mask = dist == 0
    has_zero = np.any(zero_mask, axis=1)

    result = np.zeros(gx_flat.shape[0])

    if np.any(has_zero):
        result[has_zero] = se_br[zero_mask]

    non_zero = ~has_zero
    if np.any(non_zero):
        w = 1.0 / (dist[non_zero]**power)
        w_sum = np.sum(w, axis=1, keepdims=True)
        result[non_zero] = np.sum(w * se_br, axis=1) / w_sum.flatten()

    return result.reshape(ny, nx)


def plot_cv_scatter(observed, predicted, title="Cross-Validation: Observed vs Predicted",
                    figsize=(7, 7), dpi=120):
    obs = np.asarray(observed)
    pred = np.asarray(predicted)
    mask = ~(np.isnan(obs) | np.isnan(pred))
    obs, pred = obs[mask], pred[mask]

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.scatter(obs, pred, c="steelblue", s=36, edgecolors="white", linewidths=0.6, alpha=0.8)

    lo = min(obs.min(), pred.min())
    hi = max(obs.max(), pred.max())
    margin = (hi - lo) * 0.05
    ax.plot([lo - margin, hi + margin], [lo - margin, hi + margin], "k--", lw=1, label="1:1 line")

    ax.set_xlabel("Observed", fontsize=11)
    ax.set_ylabel("Predicted", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig


def plot_variogram(grid_x, grid_y, grid_var, station_x=None, station_y=None,
                   title="Interpolation Variance", cmap="YlOrRd",
                   figsize=(10, 8), dpi=120):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    if np.all(np.isnan(grid_var)):
        ax.text(0.5, 0.5, "Variance not available for this method",
                transform=ax.transAxes, ha="center", va="center", fontsize=14)
        ax.set_title(title, fontsize=13, fontweight="bold")
        fig.tight_layout()
        return fig

    cf = ax.contourf(grid_x, grid_y, grid_var, levels=15, cmap=cmap)
    fig.colorbar(cf, ax=ax, shrink=0.85, pad=0.03, label="Variance")

    if station_x is not None and station_y is not None:
        ax.scatter(station_x, station_y, c="black", s=28, edgecolors="white",
                   linewidths=0.8, zorder=5)

    ax.set_xlabel("Longitude", fontsize=11)
    ax.set_ylabel("Latitude", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_base64
