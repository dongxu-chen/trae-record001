import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
import statsmodels.api as sm


class LassoCovariateSelector:
    def __init__(self, df, treatment_col, outcome_col, candidate_covariates):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.candidate_covariates = candidate_covariates
        self.scaler = StandardScaler()
        self.selected_covariates = []
        self.coefficients = {}

    def _prepare_data(self):
        df_clean = self.df.dropna(
            subset=[self.treatment_col, self.outcome_col] + self.candidate_covariates
        ).copy()
        
        X = df_clean[self.candidate_covariates]
        X_scaled = self.scaler.fit_transform(X)
        
        return df_clean, X_scaled

    def select_by_treatment_prediction(self, alpha=None, max_features=20):
        df_clean, X_scaled = self._prepare_data()
        y = df_clean[self.treatment_col].values
        
        if alpha is None:
            logreg_cv = LogisticRegression(
                penalty='l1',
                solver='saga',
                C=1.0,
                max_iter=5000,
                random_state=42
            )
            logreg_cv.fit(X_scaled, y)
        else:
            logreg = LogisticRegression(
                penalty='l1',
                solver='saga',
                C=1/alpha,
                max_iter=5000,
                random_state=42
            )
            logreg.fit(X_scaled, y)
            logreg_cv = logreg
        
        coef = logreg_cv.coef_[0]
        coef_dict = {cov: abs(coef[i]) for i, cov in enumerate(self.candidate_covariates)}
        
        sorted_cov = sorted(coef_dict.items(), key=lambda x: x[1], reverse=True)
        selected = [cov for cov, val in sorted_cov if val > 1e-6][:max_features]
        
        self.coefficients['treatment_prediction'] = coef_dict
        return selected

    def select_by_outcome_prediction(self, alpha=None, max_features=20):
        df_clean, X_scaled = self._prepare_data()
        y = df_clean[self.outcome_col].values
        
        if alpha is None:
            lasso_cv = LassoCV(cv=5, max_iter=5000, random_state=42)
            lasso_cv.fit(X_scaled, y)
        else:
            from sklearn.linear_model import Lasso
            lasso = Lasso(alpha=alpha, max_iter=5000, random_state=42)
            lasso.fit(X_scaled, y)
            lasso_cv = lasso
        
        coef = lasso_cv.coef_
        coef_dict = {cov: abs(coef[i]) for i, cov in enumerate(self.candidate_covariates)}
        
        sorted_cov = sorted(coef_dict.items(), key=lambda x: x[1], reverse=True)
        selected = [cov for cov, val in sorted_cov if val > 1e-6][:max_features]
        
        self.coefficients['outcome_prediction'] = coef_dict
        return selected

    def select_double_lasso(self, max_features=20):
        treatment_selected = self.select_by_treatment_prediction(max_features=max_features)
        outcome_selected = self.select_by_outcome_prediction(max_features=max_features)
        
        union_selected = list(set(treatment_selected) | set(outcome_selected))
        intersection_selected = list(set(treatment_selected) & set(outcome_selected))
        
        return {
            'union': union_selected,
            'intersection': intersection_selected,
            'treatment_selected': treatment_selected,
            'outcome_selected': outcome_selected
        }

    def select_by_perturbation(self, n_bootstraps=50, threshold=0.5):
        df_clean, X_scaled = self._prepare_data()
        y_treatment = df_clean[self.treatment_col].values
        y_outcome = df_clean[self.outcome_col].values
        
        selection_counts = {cov: 0 for cov in self.candidate_covariates}
        
        kf = KFold(n_splits=n_bootstraps, shuffle=True, random_state=42)
        
        for i, (train_idx, _) in enumerate(kf.split(X_scaled)):
            X_train = X_scaled[train_idx]
            y_treat_train = y_treatment[train_idx]
            
            try:
                logreg = LogisticRegression(
                    penalty='l1',
                    solver='saga',
                    C=0.5,
                    max_iter=3000,
                    random_state=42 + i
                )
                logreg.fit(X_train, y_treat_train)
                
                for j, cov in enumerate(self.candidate_covariates):
                    if abs(logreg.coef_[0][j]) > 1e-4:
                        selection_counts[cov] += 1
            except:
                continue
        
        selected = [
            cov for cov, count in selection_counts.items()
            if count / n_bootstraps >= threshold
        ]
        
        self.coefficients['selection_frequency'] = {
            cov: count / n_bootstraps for cov, count in selection_counts.items()
        }
        
        return selected

    def get_covariate_importance(self):
        if 'treatment_prediction' not in self.coefficients:
            self.select_by_treatment_prediction()
        if 'outcome_prediction' not in self.coefficients:
            self.select_by_outcome_prediction()
        
        importance = []
        for cov in self.candidate_covariates:
            treat_imp = self.coefficients.get('treatment_prediction', {}).get(cov, 0)
            outcome_imp = self.coefficients.get('outcome_prediction', {}).get(cov, 0)
            selection_freq = self.coefficients.get('selection_frequency', {}).get(cov, 0)
            
            importance.append({
                'covariate': cov,
                'treatment_importance': treat_imp,
                'outcome_importance': outcome_imp,
                'selection_frequency': selection_freq,
                'combined_importance': (treat_imp + outcome_imp) / 2
            })
        
        return sorted(importance, key=lambda x: x['combined_importance'], reverse=True)

    def auto_select(self, method='double_lasso', **kwargs):
        if method == 'treatment':
            self.selected_covariates = self.select_by_treatment_prediction(**kwargs)
        elif method == 'outcome':
            self.selected_covariates = self.select_by_outcome_prediction(**kwargs)
        elif method == 'double_lasso':
            result = self.select_double_lasso(**kwargs)
            self.selected_covariates = result['union']
        elif method == 'perturbation':
            self.selected_covariates = self.select_by_perturbation(**kwargs)
        else:
            raise ValueError(f"Unknown selection method: {method}")
        
        return self.selected_covariates
