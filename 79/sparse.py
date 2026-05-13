import numpy as np


def random_inducing_points(X, n_inducing, random_state=None):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n = len(X)
    if n_inducing >= n:
        return X.copy()

    if random_state is not None:
        rng = np.random.RandomState(random_state)
    else:
        rng = np.random.RandomState()

    indices = rng.choice(n, size=n_inducing, replace=False)
    return X[indices]


def uniform_grid_inducing_points(X, n_inducing):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n_features = X.shape[1]
    n_per_dim = int(np.power(n_inducing, 1.0 / n_features))
    if n_per_dim < 2:
        n_per_dim = 2

    grids = []
    for d in range(n_features):
        min_val = X[:, d].min()
        max_val = X[:, d].max()
        if max_val == min_val:
            grids.append(np.array([min_val]))
        else:
            padding = 0.05 * (max_val - min_val)
            grids.append(np.linspace(min_val - padding, max_val + padding, n_per_dim))

    mesh = np.meshgrid(*grids)
    inducing_points = np.column_stack([m.ravel() for m in mesh])

    if len(inducing_points) > n_inducing:
        rng = np.random.RandomState(42)
        indices = rng.choice(len(inducing_points), n_inducing, replace=False)
        inducing_points = inducing_points[indices]

    return inducing_points


def kmeans_inducing_points(X, n_inducing, max_iter=100, tol=1e-4, random_state=None):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n = len(X)
    if n_inducing >= n:
        return X.copy()

    if random_state is not None:
        rng = np.random.RandomState(random_state)
    else:
        rng = np.random.RandomState()

    indices = rng.choice(n, size=n_inducing, replace=False)
    centroids = X[indices].copy()

    for _ in range(max_iter):
        old_centroids = centroids.copy()

        distances = np.sum(X ** 2, axis=1, keepdims=True) + \
                    np.sum(centroids ** 2, axis=1) - \
                    2 * np.dot(X, centroids.T)
        labels = np.argmin(distances, axis=1)

        for k in range(n_inducing):
            cluster_points = X[labels == k]
            if len(cluster_points) > 0:
                centroids[k] = cluster_points.mean(axis=0)
            else:
                centroids[k] = X[rng.choice(n)]

        if np.sum((centroids - old_centroids) ** 2) < tol:
            break

    return centroids


def greedy_variance_inducing_points(X, n_inducing, kernel, sigma_n=1e-5, random_state=None):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n = len(X)
    if n_inducing >= n:
        return X.copy()

    if random_state is not None:
        rng = np.random.RandomState(random_state)
    else:
        rng = np.random.RandomState()

    K = kernel(X, X) + sigma_n ** 2 * np.eye(n)
    L = np.linalg.cholesky(K)

    selected = []
    candidate_indices = list(range(n))

    for _ in range(n_inducing):
        best_idx = None
        best_score = -np.inf

        for idx in candidate_indices:
            if idx in selected:
                continue

            temp_selected = selected + [idx]
            X_sel = X[temp_selected]

            K_ss = kernel(X_sel, X_sel) + 1e-6 * np.eye(len(X_sel))
            K_sx = kernel(X_sel, X)

            try:
                L_ss = np.linalg.cholesky(K_ss)
                V = solve_triangular(L_ss, K_sx, lower=True)
                approx_variance = np.sum(K.diagonal() - np.sum(V ** 2, axis=0))
            except np.linalg.LinAlgError:
                approx_variance = -np.inf

            if approx_variance > best_score:
                best_score = approx_variance
                best_idx = idx

        if best_idx is None:
            remaining = [i for i in candidate_indices if i not in selected]
            best_idx = remaining[rng.choice(len(remaining))]

        selected.append(best_idx)

    return X[selected]


from scipy.linalg import solve_triangular


def select_inducing_points(X, n_inducing, method='random', **kwargs):
    X = np.asarray(X)
    if X.ndim == 1:
        X = X.reshape(-1, 1)

    n = len(X)
    if n_inducing >= n:
        return X.copy()

    if method == 'random':
        return random_inducing_points(X, n_inducing, kwargs.get('random_state', None))
    elif method == 'grid':
        return uniform_grid_inducing_points(X, n_inducing)
    elif method == 'kmeans':
        return kmeans_inducing_points(X, n_inducing,
                                      max_iter=kwargs.get('max_iter', 100),
                                      tol=kwargs.get('tol', 1e-4),
                                      random_state=kwargs.get('random_state', None))
    elif method == 'greedy_variance':
        return greedy_variance_inducing_points(X, n_inducing,
                                               kernel=kwargs.get('kernel'),
                                               sigma_n=kwargs.get('sigma_n', 1e-5),
                                               random_state=kwargs.get('random_state', None))
    else:
        raise ValueError(f"Unknown inducing point selection method: {method}")


def initialize_inducing_points(X, n_inducing, kernel=None, strategy='kmeans', **kwargs):
    if strategy == 'kmeans':
        return kmeans_inducing_points(X, n_inducing, random_state=kwargs.get('random_state'))
    elif strategy == 'random':
        return random_inducing_points(X, n_inducing, random_state=kwargs.get('random_state'))
    elif strategy == 'grid':
        return uniform_grid_inducing_points(X, n_inducing)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
