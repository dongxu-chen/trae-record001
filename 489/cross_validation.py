import numpy as np
from interpolator import run_interpolation, make_grid, KRIGE_VARIogram_MODELS, ALGORITHMS


def auto_select_variogram(x, y, z, algorithm="ordinary_kriging",
                          cv_method="loocv", k=5, models=None,
                          extra_params=None):
    if models is None:
        models = KRIGE_VARIogram_MODELS
    if extra_params is None:
        extra_params = {}

    param_grid = {"variogram_model": models}
    for kk, vv in extra_params.items():
        if kk not in param_grid:
            param_grid[kk] = [vv]

    result = grid_search_cv(x, y, z, algorithm, param_grid,
                            cv_method=cv_method, k=k)

    valid = [r for r in result.get("all_results", []) if "rmse" in r and not np.isnan(r["rmse"])]
    if not valid:
        return {"best_model": "linear", "best_rmse": None, "all_results": []}

    best = min(valid, key=lambda r: r["rmse"])
    for r in result.get("all_results", []):
        r.pop("predicted", None)
        r.pop("observed", None)

    return {
        "best_model": best["params"]["variogram_model"],
        "best_rmse": best["rmse"],
        "best_params": best["params"],
        "all_results": result.get("all_results", []),
    }


def compute_station_errors(x, y, z, algorithm, cv_method="loocv", k=5, **params):
    if cv_method == "loocv":
        cv_result = loocv(x, y, z, algorithm, **params)
    else:
        cv_result = kfold_cv(x, y, z, algorithm, k=k, **params)

    obs = np.asarray(cv_result.get("observed", []))
    pred = np.asarray(cv_result.get("predicted", []))
    abs_err = np.abs(obs - pred)
    return {
        "x": x.tolist(),
        "y": y.tolist(),
        "absolute_error": abs_err.tolist(),
        "signed_error": (obs - pred).tolist(),
        "observed": obs.tolist(),
        "predicted": pred.tolist(),
    }


def loocv(x, y, z, algorithm, **params):
    n = len(x)
    predicted = np.full(n, np.nan)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        x_train = x[mask]
        y_train = y[mask]
        z_train = z[mask]

        margin = 0.001
        x_min, x_max = x[i] - margin, x[i] + margin
        y_min, y_max = y[i] - margin, y[i] + margin
        gx, gy = make_grid(x_min, x_max, y_min, y_max, nx=3, ny=3)

        try:
            z_grid, _ = run_interpolation(algorithm, x_train, y_train, z_train, gx, gy, **params)
            predicted[i] = z_grid[1, 1]
        except Exception:
            continue

    residuals = z - predicted
    rmse = np.sqrt(np.nanmean(residuals**2))
    mae = np.nanmean(np.abs(residuals))
    bias = np.nanmean(residuals)
    valid = ~np.isnan(predicted)
    r2 = 1.0 - np.nansum(residuals**2) / np.nansum((z[valid] - np.nanmean(z[valid]))**2) if np.nansum((z[valid] - np.nanmean(z[valid]))**2) != 0 else np.nan

    return {
        "rmse": round(float(rmse), 4),
        "mae": round(float(mae), 4),
        "bias": round(float(bias), 4),
        "r2": round(float(r2), 4),
        "n_valid": int(np.sum(valid)),
        "predicted": predicted.tolist(),
        "observed": z.tolist(),
    }


def kfold_cv(x, y, z, algorithm, k=5, seed=42, **params):
    n = len(x)
    rng = np.random.RandomState(seed)
    indices = np.arange(n)
    rng.shuffle(indices)
    folds = np.array_split(indices, k)

    all_observed = []
    all_predicted = []

    for fold_idx in range(k):
        test_idx = folds[fold_idx]
        train_idx = np.concatenate([folds[j] for j in range(k) if j != fold_idx])

        x_train, y_train, z_train = x[train_idx], y[train_idx], z[train_idx]
        x_test, y_test, z_test = x[test_idx], y[test_idx], z[test_idx]

        margin = 0.001
        x_min = min(x_test.min(), x_train.min()) - margin
        x_max = max(x_test.max(), x_train.max()) + margin
        y_min = min(y_test.min(), y_train.min()) - margin
        y_max = max(y_test.max(), y_train.max()) + margin

        gx, gy = make_grid(x_min, x_max, y_min, y_max, nx=50, ny=50)

        try:
            z_grid, _ = run_interpolation(algorithm, x_train, y_train, z_train, gx, gy, **params)
            from scipy.interpolate import RegularGridInterpolator
            x_1d = gx[0, :]
            y_1d = gy[:, 0]
            rgi = RegularGridInterpolator((y_1d, x_1d), z_grid,
                                          method="linear",
                                          bounds_error=False,
                                          fill_value=None)
            pts = np.column_stack([y_test, x_test])
            pred = rgi(pts)
            all_observed.extend(z_test.tolist())
            all_predicted.extend(pred.tolist())
        except Exception:
            continue

    observed = np.array(all_observed)
    predicted = np.array(all_predicted)
    residuals = observed - predicted
    rmse = np.sqrt(np.nanmean(residuals**2))
    mae = np.nanmean(np.abs(residuals))
    bias = np.nanmean(residuals)
    valid = ~np.isnan(predicted)
    r2 = 1.0 - np.nansum(residuals[valid]**2) / np.nansum((observed[valid] - np.nanmean(observed[valid]))**2) if np.nansum((observed[valid] - np.nanmean(observed[valid]))**2) != 0 else np.nan

    return {
        "rmse": round(float(rmse), 4),
        "mae": round(float(mae), 4),
        "bias": round(float(bias), 4),
        "r2": round(float(r2), 4),
        "n_valid": int(np.sum(valid)),
        "predicted": all_predicted,
        "observed": all_observed,
    }


def grid_search_cv(x, y, z, algorithm, param_grid, cv_method="loocv", k=5):
    import itertools

    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combos = list(itertools.product(*values))

    results = []
    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            if cv_method == "loocv":
                cv_result = loocv(x, y, z, algorithm, **params)
            else:
                cv_result = kfold_cv(x, y, z, algorithm, k=k, **params)
            cv_result["params"] = params
            results.append(cv_result)
        except Exception as e:
            results.append({"params": params, "error": str(e)})

    best = min(results, key=lambda r: r.get("rmse", float("inf")))
    return {
        "best_params": best.get("params", {}),
        "best_rmse": best.get("rmse"),
        "all_results": results,
    }
