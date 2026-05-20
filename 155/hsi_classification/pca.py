import numpy as np
from sklearn.decomposition import PCA as SKPCA
from sklearn.preprocessing import StandardScaler


class PCA:
    def __init__(self, n_components=None, whiten=False, standardize=True):
        self.n_components = n_components
        self.whiten = whiten
        self.standardize = standardize
        self.scaler = StandardScaler() if standardize else None
        self.pca = None
        self.explained_variance_ratio_ = None
        self.components_ = None
        self.mean_ = None

    def fit(self, X):
        if X.ndim == 3:
            X = X.reshape(-1, X.shape[-1])
        
        if self.standardize:
            X = self.scaler.fit_transform(X)
        
        self.pca = SKPCA(n_components=self.n_components, whiten=self.whiten)
        self.pca.fit(X)
        
        self.explained_variance_ratio_ = self.pca.explained_variance_ratio_
        self.components_ = self.pca.components_
        self.mean_ = self.pca.mean_
        
        return self

    def transform(self, X):
        original_shape = X.shape
        
        if X.ndim == 3:
            X = X.reshape(-1, X.shape[-1])
        
        if self.standardize:
            X = self.scaler.transform(X)
        
        X_transformed = self.pca.transform(X)
        
        if len(original_shape) == 3:
            X_transformed = X_transformed.reshape(original_shape[0], original_shape[1], -1)
        
        return X_transformed

    def fit_transform(self, X, verbose=False):
        self.fit(X)
        if verbose:
            cum_var = self.get_cumulative_variance_ratio()
            print(f"PCA降维完成：{X.shape[-1]} -> {self.n_components if self.n_components else len(cum_var)}")
            print(f"累积解释方差比：{cum_var[-1]:.4f}")
        return self.transform(X)

    def inverse_transform(self, X):
        original_shape = X.shape
        
        if X.ndim == 3:
            X = X.reshape(-1, X.shape[-1])
        
        X_reconstructed = self.pca.inverse_transform(X)
        
        if self.standardize:
            X_reconstructed = self.scaler.inverse_transform(X_reconstructed)
        
        if len(original_shape) == 3:
            X_reconstructed = X_reconstructed.reshape(original_shape[0], original_shape[1], -1)
        
        return X_reconstructed

    def get_explained_variance_ratio(self):
        return self.explained_variance_ratio_

    def get_cumulative_variance_ratio(self):
        return np.cumsum(self.explained_variance_ratio_)
