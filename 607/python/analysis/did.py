import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats


class DifferenceInDifferences:
    def __init__(self, df, treatment_col, outcome_col, covariates, time_col=None, post_col=None):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates
        self.time_col = time_col
        self.post_col = post_col
        self.results = None

    def _prepare_data(self):
        df_clean = self.df.dropna(subset=[self.treatment_col, self.outcome_col] + self.covariates).copy()
        if self.post_col is None and self.time_col is not None:
            time_values = sorted(df_clean[self.time_col].unique())
            if len(time_values) >= 2:
                mid_point = time_values[len(time_values) // 2]
                df_clean['post_treatment'] = (df_clean[self.time_col] >= mid_point).astype(int)
                self.post_col = 'post_treatment'
            else:
                raise ValueError("时间变量至少需要2个不同的值")
        elif self.post_col is None:
            raise ValueError("必须提供post_col或time_col")
        df_clean['did_interaction'] = df_clean[self.treatment_col] * df_clean[self.post_col]
        return df_clean

    def fit_model(self):
        df_clean = self._prepare_data()
        X_cols = [self.treatment_col, self.post_col, 'did_interaction'] + self.covariates
        X = df_clean[X_cols].astype(float)
        X = sm.add_constant(X)
        y = df_clean[self.outcome_col].astype(float)
        model = sm.OLS(y, X)
        self.results = model.fit(cov_type='HC3')
        return self.results

    def calculate_ate(self):
        if self.results is None:
            self.fit_model()
        did_coef = self.results.params['did_interaction']
        did_se = self.results.bse['did_interaction']
        did_pvalue = self.results.pvalues['did_interaction']
        ci_lower, ci_upper = self.results.conf_int().loc['did_interaction']
        return {
            'estimate': float(did_coef),
            'stdError': float(did_se),
            'pValue': float(did_pvalue),
            'confidenceInterval': [float(ci_lower), float(ci_upper)]
        }

    def calculate_att(self):
        return self.calculate_ate()

    def parallel_trend_test(self):
        if self.time_col is None:
            return None
        df_clean = self._prepare_data()
        time_periods = sorted(df_clean[self.time_col].unique())
        treated_means = []
        control_means = []
        for period in time_periods:
            period_data = df_clean[df_clean[self.time_col] == period]
            treated_mean = period_data[period_data[self.treatment_col] == 1][self.outcome_col].mean()
            control_mean = period_data[period_data[self.treatment_col] == 0][self.outcome_col].mean()
            treated_means.append(float(treated_mean) if not pd.isna(treated_mean) else 0)
            control_means.append(float(control_mean) if not pd.isna(control_mean) else 0)
        return {
            'timePoints': [str(t) for t in time_periods],
            'treatedMeans': treated_means,
            'controlMeans': control_means
        }

    def run_analysis(self):
        self.fit_model()
        ate = self.calculate_ate()
        att = self.calculate_att()
        parallel_trend = self.parallel_trend_test()
        sample_size = {
            'total': len(self.df),
            'treated': len(self.df[self.df[self.treatment_col] == 1]),
            'control': len(self.df[self.df[self.treatment_col] == 0])
        }
        result = {
            'method': 'did',
            'ate': ate,
            'att': att,
            'sampleSize': sample_size,
            'robustnessTests': {}
        }
        if parallel_trend:
            result['parallelTrend'] = parallel_trend
        return result
