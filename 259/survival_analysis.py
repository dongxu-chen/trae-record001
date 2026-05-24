import pandas as pd
import numpy as np
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.utils import concordance_index
from lifelines.statistics import proportional_hazard_test
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class ChurnSurvivalAnalyzer:
    def __init__(self):
        self.cph = None
        self.scaler = None
        self.feature_cols = None
        self.duration_col = None
        self.event_col = None
        self.training_data = None
        self.strata_cols = []
        self.ph_test_results = None
        self.violated_features = []
        
    def fit_cox_model(self, df, duration_col, event_col, feature_cols, standardize=True, strata_cols=None):
        self.duration_col = duration_col
        self.event_col = event_col
        self.feature_cols = feature_cols
        self.training_data = df.copy()
        self.strata_cols = strata_cols if strata_cols else []
        
        all_cols = feature_cols + [duration_col, event_col]
        if self.strata_cols:
            all_cols += self.strata_cols
        
        df_model = df[all_cols].copy()
        
        if standardize:
            self.scaler = StandardScaler()
            df_model[feature_cols] = self.scaler.fit_transform(df_model[feature_cols])
        
        if self.strata_cols:
            self.cph = CoxPHFitter(penalizer=0.01)
            self.cph.fit(
                df_model, 
                duration_col=duration_col, 
                event_col=event_col,
                strata=self.strata_cols
            )
        else:
            self.cph = CoxPHFitter(penalizer=0.01)
            self.cph.fit(df_model, duration_col=duration_col, event_col=event_col)
        
        return self.cph
    
    def check_proportional_hazards(self, p_threshold=0.05):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        self.ph_test_results = proportional_hazard_test(
            self.cph, 
            self.training_data[self.feature_cols + [self.duration_col, self.event_col]],
            time_transform='rank'
        )
        
        test_df = self.ph_test_results.summary
        test_df['feature'] = test_df.index
        test_df = test_df.reset_index(drop=True)
        test_df['satisfies_ph'] = test_df['p'] >= p_threshold
        
        self.violated_features = test_df[~test_df['satisfies_ph']]['feature'].tolist()
        
        return test_df
    
    def fit_stratified_cox_model(self, df, duration_col, event_col, feature_cols, strata_cols, standardize=True):
        if not strata_cols:
            return self.fit_cox_model(df, duration_col, event_col, feature_cols, standardize)
        
        for col in strata_cols:
            if df[col].nunique() > 10:
                df[f'{col}_strata'] = pd.qcut(df[col], q=min(5, df[col].nunique()), labels=False, duplicates='drop')
            else:
                df[f'{col}_strata'] = df[col].astype('category').cat.codes
        
        strata_processed = [f'{col}_strata' for col in strata_cols]
        
        return self.fit_cox_model(df, duration_col, event_col, feature_cols, standardize, strata_processed)
    
    def get_coefficients(self):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        coef_df = pd.DataFrame({
            'feature': self.feature_cols,
            'coef': self.cph.params_.values,
            'hazard_ratio': np.exp(self.cph.params_.values),
            'p_value': self.cph.p_values.values,
            'ci_lower': np.exp(self.cph.confidence_intervals_['95% lower-bound'].values),
            'ci_upper': np.exp(self.cph.confidence_intervals_['95% upper-bound'].values),
            'se': self.cph.standard_errors_.values
        })
        
        coef_df = coef_df.sort_values('coef', key=lambda x: abs(x), ascending=False)
        coef_df['significance'] = coef_df['p_value'].apply(
            lambda p: '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        )
        
        return coef_df
    
    def get_model_summary(self):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        df_model = self.training_data[self.feature_cols + [self.duration_col, self.event_col]].copy()
        if self.scaler:
            df_model[self.feature_cols] = self.scaler.transform(df_model[self.feature_cols])
        
        c_index = concordance_index(
            df_model[self.duration_col],
            -self.cph.predict_partial_hazard(df_model),
            df_model[self.event_col]
        )
        
        summary = {
            'n_observations': len(df_model),
            'n_events': df_model[self.event_col].sum(),
            'n_censored': (1 - df_model[self.event_col]).sum(),
            'censoring_rate': (1 - df_model[self.event_col]).mean(),
            'concordance_index': c_index,
            'log_likelihood': self.cph.log_likelihood_,
            'aic': self.cph.AIC_,
            'n_features': len(self.feature_cols)
        }
        
        return summary
    
    def predict_risk_scores(self, df):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        df_predict = df[self.feature_cols].copy()
        
        if self.scaler:
            df_predict[self.feature_cols] = self.scaler.transform(df_predict[self.feature_cols])
        
        risk_scores = self.cph.predict_partial_hazard(df_predict)
        return risk_scores
    
    def predict_survival_function(self, df, times=None):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        df_predict = df[self.feature_cols].copy()
        
        if self.scaler:
            df_predict[self.feature_cols] = self.scaler.transform(df_predict[self.feature_cols])
        
        if times is None:
            max_time = self.training_data[self.duration_col].max()
            times = np.linspace(0, max_time, 100)
        
        surv_funcs = self.cph.predict_survival_function(df_predict, times=times)
        return surv_funcs
    
    def feature_importance(self):
        coef_df = self.get_coefficients()
        importance = pd.DataFrame({
            'feature': coef_df['feature'],
            'importance': abs(coef_df['coef']),
            'direction': coef_df['coef'].apply(lambda x: 'Risk Factor' if x > 0 else 'Protective Factor')
        })
        importance = importance.sort_values('importance', ascending=False)
        return importance
    
    def calculate_probability_at_time(self, df, target_time):
        surv_funcs = self.predict_survival_function(df, times=[target_time])
        survival_prob = surv_funcs.iloc[0].values
        churn_prob = 1 - survival_prob
        return churn_prob
    
    def get_kaplan_meier_curve(self, df=None, group_col=None):
        kmf = KaplanMeierFitter()
        
        if df is None:
            df = self.training_data
        
        if group_col is None:
            kmf.fit(df[self.duration_col], df[self.event_col])
            return kmf
        else:
            groups = df[group_col].unique()
            kmf_results = {}
            for group in groups:
                mask = df[group_col] == group
                kmf_group = KaplanMeierFitter()
                kmf_group.fit(df.loc[mask, self.duration_col], df.loc[mask, self.event_col], label=str(group))
                kmf_results[group] = kmf_group
            return kmf_results
    
    def bootstrap_survival_curves(self, df=None, n_bootstrap=100, times=None, random_state=42):
        if df is None:
            df = self.training_data
        
        np.random.seed(random_state)
        
        if times is None:
            max_time = df[self.duration_col].max()
            times = np.linspace(0, max_time, 100)
        
        bootstrap_results = []
        
        for i in range(n_bootstrap):
            sample_idx = np.random.choice(len(df), size=len(df), replace=True)
            sample_df = df.iloc[sample_idx]
            
            kmf = KaplanMeierFitter()
            kmf.fit(sample_df[self.duration_col], sample_df[self.event_col])
            
            surv_probs = kmf.survival_function_at_times(times).values.flatten()
            bootstrap_results.append(surv_probs)
        
        bootstrap_matrix = np.array(bootstrap_results)
        
        mean_surv = np.mean(bootstrap_matrix, axis=0)
        median_surv = np.median(bootstrap_matrix, axis=0)
        ci_lower = np.percentile(bootstrap_matrix, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_matrix, 97.5, axis=0)
        std_surv = np.std(bootstrap_matrix, axis=0)
        
        result_df = pd.DataFrame({
            'time': times,
            'mean_survival': mean_surv,
            'median_survival': median_surv,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'std': std_surv
        })
        
        return result_df, bootstrap_matrix
    
    def predict_survival_with_bootstrap(self, df, n_bootstrap=100, times=None, random_state=42):
        if self.cph is None:
            raise ValueError("Model not fitted yet")
        
        np.random.seed(random_state)
        
        df_predict = df[self.feature_cols].copy()
        
        if self.scaler:
            df_predict[self.feature_cols] = self.scaler.transform(df_predict[self.feature_cols])
        
        if times is None:
            max_time = self.training_data[self.duration_col].max()
            times = np.linspace(0, max_time, 100)
        
        n_samples = len(df)
        n_times = len(times)
        
        bootstrap_surv = np.zeros((n_bootstrap, n_samples, n_times))
        
        coef_samples = np.random.multivariate_normal(
            mean=self.cph.params_.values,
            cov=self.cph.variance_matrix_,
            size=n_bootstrap
        )
        
        baseline_hazard = self.cph.baseline_hazard_
        baseline_cumulative_hazard = baseline_hazard.cumsum()
        
        for b in range(n_bootstrap):
            log_hazards = df_predict.values @ coef_samples[b]
            individual_cumulative_hazards = np.outer(np.exp(log_hazards), baseline_cumulative_hazard.values.flatten())
            surv_probs = np.exp(-individual_cumulative_hazards)
            
            for i in range(n_samples):
                interp_surv = np.interp(times, baseline_cumulative_hazard.index, surv_probs[i])
                bootstrap_surv[b, i, :] = interp_surv
        
        mean_surv = np.mean(bootstrap_surv, axis=0)
        ci_lower = np.percentile(bootstrap_surv, 2.5, axis=0)
        ci_upper = np.percentile(bootstrap_surv, 97.5, axis=0)
        
        return {
            'times': times,
            'mean_survival': pd.DataFrame(mean_surv.T, index=times, columns=df.index if hasattr(df, 'index') else range(n_samples)),
            'ci_lower': pd.DataFrame(ci_lower.T, index=times, columns=df.index if hasattr(df, 'index') else range(n_samples)),
            'ci_upper': pd.DataFrame(ci_upper.T, index=times, columns=df.index if hasattr(df, 'index') else range(n_samples)),
            'bootstrap_samples': bootstrap_surv
        }
