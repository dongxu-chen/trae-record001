import numpy as np
from scipy.linalg import cholesky, solve_triangular, cho_factor, cho_solve


class GaussianProcess:
    def __init__(self, kernel, sigma_n=1e-5):
        self.kernel = kernel
        self.sigma_n = sigma_n
        self.X_train = None
        self.y_train = None
        self.L = None
        self.alpha = None
        self._cholesky_info = None

    def fit(self, X, y):
        self.X_train = np.asarray(X)
        self.y_train = np.asarray(y)

        if self.X_train.ndim == 1:
            self.X_train = self.X_train.reshape(-1, 1)

        K = self.kernel(self.X_train, self.X_train)

        self.L, self.sigma_n, self._cholesky_info = self._stable_cholesky(K, self.sigma_n)
        self.alpha = solve_triangular(self.L.T, solve_triangular(self.L, self.y_train, lower=True))

    @staticmethod
    def _stable_cholesky(K, initial_sigma_n, max_jitter=1e3, jitter_factor=10):
        n = K.shape[0]
        jitter = initial_sigma_n ** 2

        K_attempt = K + jitter * np.eye(n)
        try:
            L = cholesky(K_attempt, lower=True)
            return L, np.sqrt(jitter), 'original'
        except np.linalg.LinAlgError:
            pass

        sigma_n_sq = max(initial_sigma_n ** 2, 1e-10)
        jitter = sigma_n_sq

        for _ in range(20):
            jitter *= jitter_factor
            if jitter > max_jitter:
                jitter = max_jitter

            K_attempt = K + jitter * np.eye(n)
            try:
                L = cholesky(K_attempt, lower=True)
                return L, np.sqrt(jitter), f'jittered_{jitter}'
            except np.linalg.LinAlgError:
                continue

        eigvals = np.linalg.eigvalsh(K)
        min_eig = np.min(eigvals)
        if min_eig < 0:
            jitter = max(-min_eig + 1e-9, jitter)
            K_attempt = K + jitter * np.eye(n)
        else:
            jitter = max(jitter, 1e-9 * np.max(eigvals))
            K_attempt = K + jitter * np.eye(n)

        try:
            L = cholesky(K_attempt, lower=True)
            return L, np.sqrt(jitter), 'eigen_adjusted'
        except np.linalg.LinAlgError:
            L, lower = cho_factor(K_attempt, lower=True)
            return L, np.sqrt(jitter), 'cho_factor'

    def solve(self, v):
        if self._cholesky_info == 'cho_factor':
            return cho_solve((self.L, True), v)
        return solve_triangular(self.L.T, solve_triangular(self.L, v, lower=True))

    def covariance_matrix(self, X1, X2=None, add_noise=False):
        X1 = np.asarray(X1)
        if X2 is None:
            X2 = X1
        else:
            X2 = np.asarray(X2)

        if X1.ndim == 1:
            X1 = X1.reshape(-1, 1)
        if X2.ndim == 1:
            X2 = X2.reshape(-1, 1)

        K = self.kernel(X1, X2)

        if add_noise and X1 is X2:
            K = K + self.sigma_n ** 2 * np.eye(len(X1))

        return K

    def log_marginal_likelihood(self):
        if self.alpha is None:
            return -np.inf

        log_likelihood = -0.5 * np.dot(self.y_train.T, self.alpha)
        log_likelihood -= np.sum(np.log(np.diag(self.L)))
        log_likelihood -= len(self.y_train) / 2 * np.log(2 * np.pi)

        return log_likelihood

    def get_diag_noise(self):
        return np.full(len(self.X_train), self.sigma_n ** 2)

    def is_sparse(self):
        return False


class SparseFITCGaussianProcess(GaussianProcess):
    def __init__(self, kernel, X_inducing, sigma_n=1e-5):
        super().__init__(kernel, sigma_n)
        self.X_inducing = np.asarray(X_inducing)
        if self.X_inducing.ndim == 1:
            self.X_inducing = self.X_inducing.reshape(-1, 1)
        self.n_inducing = len(self.X_inducing)
        self.Lm = None
        self.L = None
        self.Kmm_inv = None

    def fit(self, X, y):
        self.X_train = np.asarray(X)
        self.y_train = np.asarray(y)

        if self.X_train.ndim == 1:
            self.X_train = self.X_train.reshape(-1, 1)

        n = len(self.X_train)
        m = self.n_inducing

        Kmm = self.kernel(self.X_inducing, self.X_inducing)
        self.Lm, _, _ = self._stable_cholesky(Kmm, 1e-6)

        Kmn = self.kernel(self.X_inducing, self.X_train)
        Knn_diag = np.diag(self.kernel(self.X_train, self.X_train))

        V = solve_triangular(self.Lm, Kmn, lower=True)

        Q_diag = np.sum(V ** 2, axis=0)
        Lambda = self.sigma_n ** 2 + (Knn_diag - Q_diag)
        Lambda_inv = 1.0 / Lambda

        V_Lambda_inv = V * Lambda_inv.reshape(1, -1)
        A = np.eye(m) + np.dot(V_Lambda_inv, V.T)

        self.L, _, _ = self._stable_cholesky(A, 1e-6)

        y_weighted = self.y_train * Lambda_inv
        V_y_weighted = np.dot(V, y_weighted)
        self.alpha = solve_triangular(
            self.L.T,
            solve_triangular(self.L, V_y_weighted, lower=True)
        )

        self._Lambda = Lambda
        self._Lambda_inv = Lambda_inv
        self._V = V

    def log_marginal_likelihood(self):
        if self.alpha is None:
            return -np.inf

        n = len(self.y_train)
        m = self.n_inducing

        Lm_logdet = 2 * np.sum(np.log(np.diag(self.Lm)))
        L_logdet = 2 * np.sum(np.log(np.diag(self.L)))

        logdet = Lm_logdet + L_logdet + np.sum(np.log(self._Lambda))

        y_weighted = self.y_train * self._Lambda_inv
        quadratic = np.sum(self.y_train * y_weighted) - np.dot(self.alpha, np.dot(self._V, y_weighted))

        log_likelihood = -0.5 * quadratic
        log_likelihood -= 0.5 * logdet
        log_likelihood -= 0.5 * n * np.log(2 * np.pi)

        return log_likelihood

    def get_diag_noise(self):
        return self._Lambda

    def is_sparse(self):
        return True

    def get_fitc_matrices(self):
        return {
            'Lm': self.Lm,
            'L': self.L,
            'V': self._V,
            'Lambda': self._Lambda,
            'Lambda_inv': self._Lambda_inv,
            'alpha': self.alpha,
            'X_inducing': self.X_inducing
        }
