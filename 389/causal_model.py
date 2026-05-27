import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from econml.dml import CausalForestDML
import warnings

warnings.filterwarnings('ignore')


class IncrementalValueModel:
    def __init__(self, n_trees=500, max_depth=8, min_samples_leaf=10,
                 n_splits=5, random_seed=42, use_ps_weighting=False,
                 ps_clip_min=0.05, ps_clip_max=0.95):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.n_splits = n_splits
        self.random_seed = random_seed
        self.use_ps_weighting = use_ps_weighting
        self.ps_clip_min = ps_clip_min
        self.ps_clip_max = ps_clip_max
        self.model = None
        self.scaler = StandardScaler()
        self.feature_cols = None
        self.ite_pred = None
        self.propensity_scores = None
        self.sample_weights = None

    def fit_causal_forest(self, X, T, Y):
        self.feature_cols = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)

        self.model = CausalForestDML(
            model_t=RandomForestClassifier(
                n_estimators=self.n_trees,
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                random_state=self.random_seed,
                n_jobs=-1
            ),
            model_y=RandomForestRegressor(
                n_estimators=self.n_trees,
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                random_state=self.random_seed,
                n_jobs=-1
            ),
            n_estimators=self.n_trees,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            cv=self.n_splits,
            random_state=self.random_seed
        )

        self.model.fit(Y, T, X=X_scaled)
        self.ite_pred = self.model.effect(X_scaled)
        return self

    def fit_double_ml(self, X, T, Y):
        self.feature_cols = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)

        kf = KFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_seed)

        T_pred = np.zeros(len(T))
        Y_pred = np.zeros(len(Y))
        T_resid = np.zeros(len(T))
        Y_resid = np.zeros(len(Y))

        for train_idx, test_idx in kf.split(X_scaled):
            X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
            T_train, T_test = T[train_idx], T[test_idx]
            Y_train, Y_test = Y[train_idx], Y[test_idx]

            model_t = GradientBoostingRegressor(
                n_estimators=300,
                max_depth=5,
                random_state=self.random_seed
            )
            model_t.fit(X_train, T_train)
            T_pred_test = model_t.predict(X_test)
            T_pred[test_idx] = T_pred_test
            T_resid[test_idx] = T_test - T_pred_test

            model_y = GradientBoostingRegressor(
                n_estimators=300,
                max_depth=5,
                random_state=self.random_seed
            )
            model_y.fit(X_train, Y_train)
            Y_pred_test = model_y.predict(X_test)
            Y_pred[test_idx] = Y_pred_test
            Y_resid[test_idx] = Y_test - Y_pred_test

        self.ite_pred = np.where(T_resid != 0, Y_resid / T_resid, 0)

        self.model = {
            'T_pred': T_pred,
            'Y_pred': Y_pred,
            'T_resid': T_resid,
            'Y_resid': Y_resid,
            'method': 'double_ml'
        }

        return self

    def compute_incremental_value(self, X, T, Y, method='causal_forest'):
        if method == 'causal_forest':
            self.fit_causal_forest(X, T, Y)
        elif method == 'double_ml':
            self.fit_double_ml(X, T, Y)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'causal_forest' or 'double_ml'.")

        return self.ite_pred

    def compute_counterfactual_values(self, X, T, Y, ad_ids, impression_ids, method='causal_forest'):
        ite = self.compute_incremental_value(X, T, Y, method=method)

        results = pd.DataFrame({
            'impression_id': impression_ids,
            'ad_id': ad_ids,
            'click': T,
            'conversion_value': Y,
            'incremental_value': ite,
            'counterfactual_value': Y - ite * T,
            'marginal_value': ite * T
        })

        if self.propensity_scores is not None:
            results['propensity_score'] = self.propensity_scores
        if self.sample_weights is not None:
            results['sample_weight'] = self.sample_weights

        results['value_without_impression'] = results['counterfactual_value']
        results['value_with_impression'] = results['conversion_value']
        results['value_difference'] = results['value_with_impression'] - results['value_without_impression']

        return results

    def get_feature_importance(self, X, T, Y, method='causal_forest'):
        if method == 'causal_forest' and self.model is not None:
            try:
                importance = self.model.feature_importances_
                return pd.DataFrame({
                    'feature': self.feature_cols,
                    'importance': importance
                }).sort_values('importance', ascending=False)
            except Exception:
                pass

        rf = RandomForestRegressor(
            n_estimators=self.n_trees,
            max_depth=self.max_depth,
            random_state=self.random_seed,
            n_jobs=-1
        )
        X_scaled = self.scaler.fit_transform(X)
        rf.fit(X_scaled, Y)
        return pd.DataFrame({
            'feature': list(X.columns),
            'importance': rf.feature_importances_
        }).sort_values('importance', ascending=False)

    def predict_ite(self, X_new):
        if self.model is None:
            raise RuntimeError("Model not fitted. Call compute_incremental_value first.")

        X_scaled = self.scaler.transform(X_new)
        return self.model.effect(X_scaled) if hasattr(self.model, 'effect') else np.zeros(len(X_new))

    def estimate_propensity_scores(self, X, T):
        self.feature_cols = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)

        ps_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_seed,
            n_jobs=-1
        )
        ps_model.fit(X_scaled, T)
        self.propensity_scores = ps_model.predict_proba(X_scaled)[:, 1]
        self.propensity_scores = np.clip(
            self.propensity_scores,
            self.ps_clip_min,
            self.ps_clip_max
        )
        return self.propensity_scores

    def compute_ipw_weights(self, T):
        if self.propensity_scores is None:
            raise RuntimeError("Propensity scores not estimated. Call estimate_propensity_scores first.")

        e = self.propensity_scores
        weights = np.where(T == 1, 1.0 / e, 1.0 / (1.0 - e))
        self.sample_weights = weights
        return weights

    def compute_weighted_ate(self, T, Y):
        if self.sample_weights is None:
            if self.propensity_scores is None:
                raise RuntimeError("Propensity scores not estimated.")
            self.compute_ipw_weights(T)

        w = self.sample_weights
        treated = T == 1
        control = T == 0

        treated_mean = np.sum(Y[treated] * w[treated]) / np.sum(w[treated])
        control_mean = np.sum(Y[control] * w[control]) / np.sum(w[control])

        return treated_mean - control_mean

    def fit_propensity_weighted_causal_forest(self, X, T, Y):
        self.feature_cols = list(X.columns)
        self.estimate_propensity_scores(X, T)
        self.compute_ipw_weights(T)
        X_scaled = self.scaler.transform(X)

        self.model = CausalForestDML(
            model_t=RandomForestClassifier(
                n_estimators=self.n_trees,
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                random_state=self.random_seed,
                n_jobs=-1
            ),
            model_y=RandomForestRegressor(
                n_estimators=self.n_trees,
                max_depth=self.max_depth,
                min_samples_leaf=self.min_samples_leaf,
                random_state=self.random_seed,
                n_jobs=-1
            ),
            n_estimators=self.n_trees,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            cv=self.n_splits,
            random_state=self.random_seed
        )

        self.model.fit(Y, T, X=X_scaled, sample_weight=self.sample_weights)
        self.ite_pred = self.model.effect(X_scaled)
        return self

    def compute_incremental_value(self, X, T, Y, method='causal_forest'):
        if method == 'causal_forest':
            if self.use_ps_weighting:
                self.fit_propensity_weighted_causal_forest(X, T, Y)
            else:
                self.fit_causal_forest(X, T, Y)
        elif method == 'double_ml':
            self.fit_double_ml(X, T, Y)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'causal_forest' or 'double_ml'.")

        return self.ite_pred