import numpy as np
from scipy.linalg import solve_triangular


def predict(gp, X_test, return_std=True, return_cov=False, include_noise=True):
    X_test = np.asarray(X_test)
    if X_test.ndim == 1:
        X_test = X_test.reshape(-1, 1)

    if hasattr(gp, 'is_sparse') and gp.is_sparse():
        return _predict_fitc(gp, X_test, return_std, return_cov, include_noise)
    else:
        return _predict_exact(gp, X_test, return_std, return_cov, include_noise)


def _predict_exact(gp, X_test, return_std, return_cov, include_noise):
    K_star = gp.kernel(gp.X_train, X_test)
    v = solve_triangular(gp.L, K_star, lower=True)

    mu = np.dot(K_star.T, gp.alpha)

    if not (return_std or return_cov):
        return mu

    K_star_star = gp.kernel(X_test, X_test)

    if return_cov:
        cov = K_star_star - np.dot(v.T, v)
        if include_noise:
            cov = cov + gp.sigma_n ** 2 * np.eye(len(X_test))
        eigvals = np.linalg.eigvalsh(cov)
        min_eig = np.min(eigvals)
        if min_eig < 0:
            cov = cov + (1e-9 - min_eig) * np.eye(len(X_test))
        if return_std:
            std = np.sqrt(np.maximum(np.diag(cov), 0))
            return mu, std, cov
        return mu, cov

    var = np.diag(K_star_star) - np.sum(v ** 2, axis=0)
    var = np.maximum(var, 0)
    if include_noise:
        var = var + gp.sigma_n ** 2
    std = np.sqrt(var)

    return mu, std


def _predict_fitc(gp, X_test, return_std, return_cov, include_noise):
    Kms = gp.kernel(gp.X_inducing, X_test)

    v_ms = solve_triangular(gp.Lm, Kms, lower=True)

    mu = np.dot(Kms.T, gp.alpha)

    if not (return_std or return_cov):
        return mu

    Kss = gp.kernel(X_test, X_test)

    v_bs = solve_triangular(gp.L, v_ms, lower=True)

    if return_cov:
        cov = Kss - np.dot(v_ms.T, v_ms) + np.dot(v_bs.T, v_bs)
        if include_noise:
            cov = cov + gp.sigma_n ** 2 * np.eye(len(X_test))
        eigvals = np.linalg.eigvalsh(cov)
        min_eig = np.min(eigvals)
        if min_eig < 0:
            cov = cov + (1e-9 - min_eig) * np.eye(len(X_test))
        if return_std:
            std = np.sqrt(np.maximum(np.diag(cov), 0))
            return mu, std, cov
        return mu, cov

    var = np.diag(Kss) - np.sum(v_ms ** 2, axis=0) + np.sum(v_bs ** 2, axis=0)
    var = np.maximum(var, 0)
    if include_noise:
        var = var + gp.sigma_n ** 2
    std = np.sqrt(var)

    return mu, std


def predict_with_variance(gp, X_test):
    return predict(gp, X_test, return_std=True, return_cov=False)


def predict_with_covariance(gp, X_test):
    return predict(gp, X_test, return_std=False, return_cov=True)


def sample_y(gp, X_test, n_samples=1):
    mu, cov = predict(gp, X_test, return_std=False, return_cov=True)
    cov = cov + 1e-10 * np.eye(len(X_test))
    return np.random.multivariate_normal(mu, cov, size=n_samples).T
