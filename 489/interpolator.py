import numpy as np
from scipy.interpolate import Rbf
from pykrige.ok import OrdinaryKriging
from pykrige.uk import UniversalKriging
from pykrige.rk import Krige


ALGORITHMS = ["idw", "ordinary_kriging", "universal_kriging", "rbf"]

KRIGE_VARIogram_MODELS = ["linear", "power", "gaussian", "exponential", "spherical"]

RBF_FUNCTIONS = ["multiquadric", "inverse", "gaussian", "linear", "cubic", "quintic", "thin_plate_spline"]


def interpolate_idw(x, y, z, grid_x, grid_y, power=2.0, max_neighbors=12):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    grid_z = np.full(grid_x.shape, np.nan)
    grid_var = np.full(grid_x.shape, np.nan)

    for i in range(grid_x.shape[0]):
        for j in range(grid_x.shape[1]):
            dx = x - grid_x[i, j]
            dy = y - grid_y[i, j]
            dist = np.sqrt(dx**2 + dy**2)

            if max_neighbors is not None and max_neighbors < len(dist):
                idx = np.argsort(dist)[:max_neighbors]
                dist_sel = dist[idx]
                z_sel = z[idx]
            else:
                dist_sel = dist
                z_sel = z

            zero_mask = dist_sel == 0.0
            if np.any(zero_mask):
                grid_z[i, j] = z_sel[zero_mask][0]
                grid_var[i, j] = 0.0
            else:
                w = 1.0 / (dist_sel**power)
                grid_z[i, j] = np.sum(w * z_sel) / np.sum(w)
                wt = w / np.sum(w)
                grid_var[i, j] = np.sum(wt * (z_sel - grid_z[i, j])**2)

    return grid_z, grid_var


def interpolate_ordinary_kriging(x, y, z, grid_x, grid_y,
                                  variogram_model="linear",
                                  nlags=6, weight=True,
                                  coordinates_type="euclidean",
                                  anisotropy_angle=0.0,
                                  anisotropy_scaling=1.0,
                                  **kwargs):
    ok = OrdinaryKriging(
        x, y, z,
        variogram_model=variogram_model,
        nlags=nlags,
        weight=weight,
        coordinates_type=coordinates_type,
        anisotropy_angle=anisotropy_angle,
        anisotropy_scaling=anisotropy_scaling,
        verbose=False,
        enable_plotting=False,
    )
    x_grid_1d = grid_x[0, :]
    y_grid_1d = grid_y[:, 0]
    z_grid, ss_grid = ok.execute("grid", x_grid_1d, y_grid_1d)
    return z_grid, ss_grid


def interpolate_universal_kriging(x, y, z, grid_x, grid_y,
                                   variogram_model="linear",
                                   drift_terms=None,
                                   nlags=6, weight=True,
                                   **kwargs):
    if drift_terms is None:
        drift_terms = ["regional_linear"]
    uk = UniversalKriging(
        x, y, z,
        variogram_model=variogram_model,
        drift_terms=drift_terms,
        nlags=nlags,
        weight=weight,
        verbose=False,
        enable_plotting=False,
    )
    x_grid_1d = grid_x[0, :]
    y_grid_1d = grid_y[:, 0]
    z_grid, ss_grid = uk.execute("grid", x_grid_1d, y_grid_1d)
    return z_grid, ss_grid


def interpolate_rbf(x, y, z, grid_x, grid_y,
                    function="multiquadric",
                    epsilon=None,
                    smooth=0.0,
                    **kwargs):
    rbf = Rbf(x, y, z, function=function, epsilon=epsilon, smooth=smooth)
    z_grid = rbf(grid_x, grid_y)
    var_grid = np.full(z_grid.shape, np.nan)
    return z_grid, var_grid


INTERPOLATORS = {
    "idw": interpolate_idw,
    "ordinary_kriging": interpolate_ordinary_kriging,
    "universal_kriging": interpolate_universal_kriging,
    "rbf": interpolate_rbf,
}


def run_interpolation(algorithm, x, y, z, grid_x, grid_y, **params):
    if algorithm not in INTERPOLATORS:
        raise ValueError(f"Unknown algorithm: {algorithm}. Available: {list(INTERPOLATORS.keys())}")
    interp_func = INTERPOLATORS[algorithm]
    return interp_func(x, y, z, grid_x, grid_y, **params)


def make_grid(x_min, x_max, y_min, y_max, nx=100, ny=100):
    x_1d = np.linspace(x_min, x_max, nx)
    y_1d = np.linspace(y_min, y_max, ny)
    grid_x, grid_y = np.meshgrid(x_1d, y_1d)
    return grid_x, grid_y
