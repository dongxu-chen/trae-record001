import numpy as np
import warnings
warnings.filterwarnings("ignore")

MULTIVAR_METHODS = [
    "cokriging_simple",
    "regression_kriging",
    "collocated_cokriging",
]


def interpolate_collocated_cokriging(x_prim, y_prim, z_prim,
                                     x_sec, y_sec, z_sec,
                                     grid_x, grid_y,
                                     variogram_model="linear", nlags=6):
    from pykrige.ok import OrdinaryKriging

    x1, y1, z1 = np.array(x_prim), np.array(y_prim), np.array(z_prim)
    x2, y2, z2 = np.array(x_sec), np.array(y_sec), np.array(z_sec)

    valid_mask1 = ~np.isnan(z1)
    x1v, y1v, z1v = x1[valid_mask1], y1[valid_mask1], z1[valid_mask1]

    OK_prim = OrdinaryKriging(x1v, y1v, z1v, variogram_model=variogram_model,
                              nlags=nlags, verbose=False, enable_plotting=False)
    z_prim_grid, var_prim_grid = OK_prim.execute("grid", grid_x[0, :], grid_y[:, 0])

    valid_mask2 = ~np.isnan(z2)
    x2v, y2v, z2v = x2[valid_mask2], y2[valid_mask2], z2[valid_mask2]

    if len(z2v) > 3:
        OK_sec = OrdinaryKriging(x2v, y2v, z2v, variogram_model=variogram_model,
                                 nlags=nlags, verbose=False, enable_plotting=False)
        z_sec_grid, var_sec_grid = OK_sec.execute("grid", grid_x[0, :], grid_y[:, 0])
    else:
        z_sec_grid = np.full(grid_x.shape, np.nanmean(z2v))
        var_sec_grid = np.full(grid_x.shape, np.nanvar(z2v))

    z1_mean, z2_mean = np.nanmean(z1v), np.nanmean(z2v)
    z1_std, z2_std = np.nanstd(z1v), np.nanstd(z2v)

    min_len = min(len(z1v), len(z2v))
    if z1_std > 0 and z2_std > 0 and min_len > 3:
        corr = np.corrcoef(z1v[:min_len], z2v[:min_len])[0, 1]
    else:
        corr = 0.5

    if np.isnan(corr):
        corr = 0.5

    alpha = corr * (z1_std / z2_std if z2_std > 0 else 0.5)

    z_co_grid = z_prim_grid + alpha * (z_sec_grid - z2_mean)

    var_co_grid = var_prim_grid + (alpha**2) * var_sec_grid

    return z_co_grid, var_co_grid, z_prim_grid, z_sec_grid


def interpolate_regression_kriging(x_prim, y_prim, z_prim,
                                   x_sec, y_sec, z_sec,
                                   grid_x, grid_y,
                                   variogram_model="linear", nlags=6):
    from pykrige.ok import OrdinaryKriging
    from scipy.interpolate import griddata

    x1, y1, z1 = np.array(x_prim), np.array(y_prim), np.array(z_prim)
    x2, y2, z2 = np.array(x_sec), np.array(y_sec), np.array(z_sec)

    z2_at_primary = griddata(np.column_stack([x2, y2]), z2, (x1, y1), method="linear")

    valid_mask = ~np.isnan(z1) & ~np.isnan(z2_at_primary)
    z1v = z1[valid_mask]
    z2v = z2_at_primary[valid_mask]
    x1v = x1[valid_mask]
    y1v = y1[valid_mask]

    if len(z1v) >= 2:
        X = np.column_stack([np.ones(len(z1v)), z2v])
        beta, _, _, _ = np.linalg.lstsq(X, z1v, rcond=None)
    else:
        beta = np.array([np.nanmean(z1), 0.0])

    drift_grid = griddata(np.column_stack([x2, y2]), z2, (grid_x, grid_y), method="linear")

    residuals = z1v - (beta[0] + beta[1] * z2v)

    OK_resid = OrdinaryKriging(x1v, y1v, residuals, variogram_model=variogram_model,
                               nlags=nlags, verbose=False, enable_plotting=False)
    resid_grid, var_grid = OK_resid.execute("grid", grid_x[0, :], grid_y[:, 0])

    z_rk_grid = beta[0] + beta[1] * drift_grid + resid_grid

    return z_rk_grid, var_grid


def interpolate_simple_cokriging(x_prim, y_prim, z_prim,
                                  x_sec, y_sec, z_sec,
                                  grid_x, grid_y,
                                  variogram_model="linear", nlags=6):
    z_co_grid, var_co_grid, _, _ = interpolate_collocated_cokriging(
        x_prim, y_prim, z_prim,
        x_sec, y_sec, z_sec,
        grid_x, grid_y,
        variogram_model=variogram_model, nlags=nlags
    )
    return z_co_grid, var_co_grid


def plot_cokriging_comparison(grid_x, grid_y,
                              z_primary, z_secondary, z_cokriged,
                              title="Co-Kriging Comparison",
                              label_primary="Primary",
                              label_secondary="Secondary",
                              figsize=(14, 10), dpi=120):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=figsize, dpi=dpi)

    z_min = min(np.nanmin(z_primary), np.nanmin(z_cokriged))
    z_max = max(np.nanmax(z_primary), np.nanmax(z_cokriged))

    cf1 = axes[0, 0].contourf(grid_x, grid_y, z_primary, levels=15,
                               cmap="RdYlBu_r", extend="both")
    axes[0, 0].set_title(f"{label_primary} (Ordinary Kriging)",
                         fontsize=11, fontweight="bold")
    fig.colorbar(cf1, ax=axes[0, 0])

    cf2 = axes[0, 1].contourf(grid_x, grid_y, z_secondary, levels=15,
                               cmap="RdYlBu_r", extend="both")
    axes[0, 1].set_title(f"{label_secondary}", fontsize=11, fontweight="bold")
    fig.colorbar(cf2, ax=axes[0, 1])

    cf3 = axes[1, 0].contourf(grid_x, grid_y, z_cokriged, levels=15,
                               cmap="RdYlBu_r", extend="both")
    axes[1, 0].set_title("Co-Kriging", fontsize=11, fontweight="bold")
    fig.colorbar(cf3, ax=axes[1, 0])

    diff = z_cokriged - z_primary
    vmax = np.nanmax(np.abs(diff))
    cf4 = axes[1, 1].contourf(grid_x, grid_y, diff, levels=15,
                               cmap="RdBu_r", vmin=-vmax, vmax=vmax, extend="both")
    axes[1, 1].set_title("Difference (Co-Kriging - OK)",
                         fontsize=11, fontweight="bold")
    fig.colorbar(cf4, ax=axes[1, 1])

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig
