import numpy as np
from scipy.optimize import minimize
from .gp import GaussianProcess, SparseFITCGaussianProcess


def _safe_negative_log_marginal_likelihood(params, gp, X, y, optimize_sigma_n=True):
    kernel_params = params[:-1] if optimize_sigma_n else params
    sigma_n = params[-1] if optimize_sigma_n else gp.sigma_n

    try:
        gp.kernel.set_params(kernel_params)
        gp.sigma_n = sigma_n
        gp.fit(X, y)
        return -gp.log_marginal_likelihood()
    except (np.linalg.LinAlgError, RuntimeError, ValueError):
        return 1e12


def _generate_initial_points(bounds, n_points, seed=None):
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState()

    bounds = np.array(bounds)
    log_lower = np.log(bounds[:, 0] + 1e-15)
    log_upper = np.log(bounds[:, 1] + 1e-15)

    log_samples = rng.uniform(log_lower, log_upper, (n_points, len(bounds)))
    samples = np.exp(log_samples)

    return samples


def optimize_marginal_likelihood(
    gp: GaussianProcess,
    X,
    y,
    optimize_sigma_n=True,
    bounds=None,
    method='L-BFGS-B',
    n_restarts=5,
    random_state=None,
    **kwargs
):
    initial_kernel_params = gp.kernel.get_params()
    n_kernel_params = len(initial_kernel_params)

    if optimize_sigma_n:
        initial_params = np.concatenate([initial_kernel_params, [gp.sigma_n]])
        n_total_params = n_kernel_params + 1
    else:
        initial_params = initial_kernel_params
        n_total_params = n_kernel_params

    if bounds is None:
        bounds = [(1e-4, 1e4)] * n_kernel_params
        if optimize_sigma_n:
            bounds.append((1e-4, 1e0))
        bounds = np.array(bounds)

    if len(bounds) != n_total_params:
        raise ValueError(f"Expected {n_total_params} bounds, got {len(bounds)}")

    best_result = None
    best_neg_lml = np.inf

    starting_points = [initial_params]

    if n_restarts > 0:
        random_starts = _generate_initial_points(bounds, n_restarts, seed=random_state)
        starting_points.extend(list(random_starts))

    for i, start in enumerate(starting_points):
        start = np.clip(start, bounds[:, 0], bounds[:, 1])

        try:
            result = minimize(
                _safe_negative_log_marginal_likelihood,
                start,
                args=(gp, X, y, optimize_sigma_n),
                method=method,
                bounds=bounds,
                **kwargs
            )

            if result.fun < best_neg_lml:
                best_neg_lml = result.fun
                best_result = result

        except Exception:
            continue

    if best_result is None:
        raise RuntimeError("All optimization attempts failed")

    optimal_params = best_result.x

    if optimize_sigma_n:
        gp.kernel.set_params(optimal_params[:-1])
        gp.sigma_n = optimal_params[-1]
    else:
        gp.kernel.set_params(optimal_params)

    gp.fit(X, y)

    best_result.n_restarts = n_restarts
    best_result.total_evaluations = len(starting_points)

    return best_result


def _safe_fitc_neg_lml(params, gp, X, y, optimize_sigma_n=True, optimize_inducing=False):
    n_kernel_params = len(gp.kernel.get_params())

    if optimize_inducing:
        n_inducing = gp.n_inducing
        n_features = X.shape[1] if X.ndim > 1 else 1
        inducing_params_end = n_kernel_params + n_inducing * n_features
        inducing_params = params[n_kernel_params:inducing_params_end].reshape(n_inducing, n_features)
        gp.X_inducing = inducing_params
    else:
        inducing_params_end = n_kernel_params

    kernel_params = params[:n_kernel_params]

    if optimize_sigma_n:
        sigma_n = params[inducing_params_end]
    else:
        sigma_n = gp.sigma_n

    try:
        gp.kernel.set_params(kernel_params)
        gp.sigma_n = sigma_n
        gp.fit(X, y)
        return -gp.log_marginal_likelihood()
    except (np.linalg.LinAlgError, RuntimeError, ValueError):
        return 1e12


def optimize_fitc_marginal_likelihood(
    gp: SparseFITCGaussianProcess,
    X,
    y,
    optimize_sigma_n=True,
    optimize_inducing=False,
    bounds=None,
    method='L-BFGS-B',
    n_restarts=5,
    random_state=None,
    **kwargs
):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n_features = X.shape[1]
    initial_kernel_params = gp.kernel.get_params()
    n_kernel_params = len(initial_kernel_params)
    n_inducing = gp.n_inducing

    initial_params = [initial_kernel_params]
    param_names = ['kernel']

    if optimize_inducing:
        initial_params.append(gp.X_inducing.ravel())
        param_names.append('inducing')

    if optimize_sigma_n:
        initial_params.append([gp.sigma_n])
        param_names.append('sigma_n')

    initial_params = np.concatenate(initial_params)

    if bounds is None:
        bounds = []
        bounds.extend([(1e-4, 1e4)] * n_kernel_params)

        if optimize_inducing:
            x_min, x_max = X.min(axis=0), X.max(axis=0)
            for _ in range(n_inducing):
                for d in range(n_features):
                    padding = 0.1 * (x_max[d] - x_min[d]) if x_max[d] > x_min[d] else 0.1
                    bounds.append((x_min[d] - padding, x_max[d] + padding))

        if optimize_sigma_n:
            bounds.append((1e-5, 1e0))

        bounds = np.array(bounds)

    best_result = None
    best_neg_lml = np.inf

    starting_points = [initial_params]

    if n_restarts > 0:
        rng = np.random.RandomState(random_state)
        random_starts = []

        for _ in range(n_restarts):
            start = []

            for i, (low, high) in enumerate(bounds[:n_kernel_params]):
                log_low = np.log(low + 1e-15)
                log_high = np.log(high + 1e-15)
                start.append(np.exp(rng.uniform(log_low, log_high)))

            if optimize_inducing:
                inducing_start = []
                x_min, x_max = X.min(axis=0), X.max(axis=0)
                for _ in range(n_inducing):
                    for d in range(n_features):
                        padding = 0.1 * (x_max[d] - x_min[d]) if x_max[d] > x_min[d] else 0.1
                        inducing_start.append(rng.uniform(x_min[d] - padding, x_max[d] + padding))
                start.extend(inducing_start)

            if optimize_sigma_n:
                sigma_bounds = bounds[-1]
                start.append(rng.uniform(sigma_bounds[0], sigma_bounds[1]))

            random_starts.append(np.array(start))

        starting_points.extend(random_starts)

    for i, start in enumerate(starting_points):
        start = np.clip(start, bounds[:, 0], bounds[:, 1])

        try:
            result = minimize(
                _safe_fitc_neg_lml,
                start,
                args=(gp, X, y, optimize_sigma_n, optimize_inducing),
                method=method,
                bounds=bounds,
                **kwargs
            )

            if result.fun < best_neg_lml:
                best_neg_lml = result.fun
                best_result = result

        except Exception:
            continue

    if best_result is None:
        raise RuntimeError("All optimization attempts failed")

    optimal_params = best_result.x

    if optimize_inducing:
        inducing_params_end = n_kernel_params + n_inducing * n_features
        gp.X_inducing = optimal_params[n_kernel_params:inducing_params_end].reshape(n_inducing, n_features)
    else:
        inducing_params_end = n_kernel_params

    gp.kernel.set_params(optimal_params[:n_kernel_params])

    if optimize_sigma_n:
        gp.sigma_n = optimal_params[inducing_params_end]

    gp.fit(X, y)

    best_result.n_restarts = n_restarts
    best_result.total_evaluations = len(starting_points)
    best_result.optimize_inducing = optimize_inducing

    return best_result
