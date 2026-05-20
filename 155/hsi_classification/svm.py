import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV


class SVMClassifier:
    def __init__(self, kernel='rbf', C=1.0, gamma='scale', standardize=True, random_state=42):
        self.kernel = kernel
        self.C = C
        self.gamma = gamma
        self.standardize = standardize
        self.random_state = random_state
        self.scaler = StandardScaler() if standardize else None
        self.model = None
        self.classes_ = None

    def _prepare_data(self, X, y=None, fit=False):
        if X.ndim == 3:
            X = X.reshape(-1, X.shape[-1])
        
        if y is not None:
            if y.ndim == 2:
                y = y.flatten()
            
            if fit:
                valid_mask = y > 0
                X = X[valid_mask]
                y = y[valid_mask]
        
        if self.standardize:
            if fit:
                X = self.scaler.fit_transform(X)
            else:
                X = self.scaler.transform(X)
        
        if y is not None:
            return X, y
        return X

    def fit(self, X, y):
        X, y = self._prepare_data(X, y, fit=True)
        
        self.model = SVC(
            kernel=self.kernel,
            C=self.C,
            gamma=self.gamma,
            random_state=self.random_state,
            probability=True
        )
        self.model.fit(X, y)
        self.classes_ = self.model.classes_
        
        return self

    def predict(self, X):
        original_shape = X.shape
        X = self._prepare_data(X)
        
        predictions = self.model.predict(X)
        
        if len(original_shape) == 3:
            predictions = predictions.reshape(original_shape[0], original_shape[1])
        
        return predictions

    def predict_proba(self, X):
        original_shape = X.shape
        X = self._prepare_data(X)
        
        probas = self.model.predict_proba(X)
        
        if len(original_shape) == 3:
            probas = probas.reshape(original_shape[0], original_shape[1], -1)
        
        return probas

    def score(self, X, y):
        X, y = self._prepare_data(X, y, fit=False)
        return self.model.score(X, y)

    def grid_search(self, X, y, param_grid, cv=5, n_jobs=-1):
        X, y = self._prepare_data(X, y, fit=True)
        
        grid_search = GridSearchCV(
            SVC(random_state=self.random_state, probability=True),
            param_grid,
            cv=cv,
            n_jobs=n_jobs,
            verbose=1
        )
        grid_search.fit(X, y)
        
        self.model = grid_search.best_estimator_
        self.classes_ = self.model.classes_
        self.C = grid_search.best_params_['C']
        self.gamma = grid_search.best_params_.get('gamma', 'scale')
        self.kernel = grid_search.best_params_.get('kernel', 'rbf')
        
        return grid_search.best_params_, grid_search.best_score_
