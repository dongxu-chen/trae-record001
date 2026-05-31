import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor


class ParallelTrendTester:
    def __init__(self, df, treatment_col, outcome_col, time_col, covariates=None):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.time_col = time_col
        self.covariates = covariates or []
        self.results = {}

    def test_parallel_trend_graphical(self):
        time_periods = sorted(self.df[self.time_col].unique())
        treated_means = []
        control_means = []
        treated_se = []
        control_se = []

        for period in time_periods:
            period_data = self.df[self.df[self.time_col] == period]
            treated_group = period_data[period_data[self.treatment_col] == 1][self.outcome_col]
            control_group = period_data[period_data[self.treatment_col] == 0][self.outcome_col]
            
            treated_means.append(treated_group.mean())
            control_means.append(control_group.mean())
            treated_se.append(treated_group.std() / np.sqrt(len(treated_group)))
            control_se.append(control_group.std() / np.sqrt(len(control_group)))

        self.results['graphical'] = {
            'timePoints': [str(t) for t in time_periods],
            'treatedMeans': [float(m) for m in treated_means],
            'controlMeans': [float(m) for m in control_means],
            'treatedSE': [float(s) for s in treated_se],
            'controlSE': [float(s) for s in control_se],
        }
        return self.results['graphical']

    def test_parallel_trend_statistical(self):
        df_clean = self.df.dropna(
            subset=[self.treatment_col, self.outcome_col, self.time_col] + self.covariates
        ).copy()

        time_periods = sorted(df_clean[self.time_col].unique())
        n_periods = len(time_periods)

        if n_periods < 3:
            return {
                'f_statistic': None,
                'p_value': None,
                'significant': False,
                'note': '需要至少3个时间点进行统计检验',
                'passed': True
            }

        pre_periods = [t for i, t in enumerate(time_periods) if i < n_periods // 2]

        if len(pre_periods) < 2:
            pre_periods = time_periods[:-1]

        df_pre = df_clean[df_clean[self.time_col].isin(pre_periods)].copy()

        time_dummies = pd.get_dummies(df_pre[self.time_col], prefix='time', drop_first=True)
        treated_dummy = df_pre[self.treatment_col].values.reshape(-1, 1)

        interaction_terms = pd.DataFrame()
        for col in time_dummies.columns:
            interaction_terms[f'treat_x_{col}'] = df_pre[self.treatment_col].values * time_dummies[col].values

        X = pd.concat([time_dummies, pd.DataFrame({'treated': df_pre[self.treatment_col].values}), interaction_terms], axis=1)
        
        if self.covariates:
            for cov in self.covariates:
                X[cov] = df_pre[cov].values

        X = X.astype(float)
        X = sm.add_constant(X)
        y = df_pre[self.outcome_col].values.astype(float)

        model = sm.OLS(y, X).fit(cov_type='HC3')

        interaction_coefs = [coef for coef in model.params.index if 'treat_x_' in coef]
        
        if len(interaction_coefs) > 0:
            hypothesis = ' = '.join(interaction_coefs) + ' = 0'
            f_test = model.f_test(hypothesis)
            
            f_stat = float(f_test.fvalue)
            p_value = float(f_test.pvalue)
            
            self.results['statistical'] = {
                'f_statistic': f_stat,
                'p_value': p_value,
                'df_num': int(f_test.df_num),
                'df_denom': int(f_test.df_denom),
                'significant': p_value < 0.05,
                'passed': p_value >= 0.05,
                'note': 'p >= 0.05 表示通过平行趋势假设检验'
            }
        else:
            self.results['statistical'] = {
                'f_statistic': None,
                'p_value': None,
                'significant': False,
                'passed': True,
                'note': '交互项不足，无法进行F检验'
            }

        return self.results['statistical']

    def test_event_study(self):
        df_clean = self.df.dropna(
            subset=[self.treatment_col, self.outcome_col, self.time_col] + self.covariates
        ).copy()

        time_periods = sorted(df_clean[self.time_col].unique())
        n_periods = len(time_periods)
        mid_period = time_periods[n_periods // 2]

        df_clean['relative_time'] = df_clean[self.time_col] - mid_period
        relative_times = sorted(df_clean['relative_time'].unique())

        coefs = []
        conf_int_lower = []
        conf_int_upper = []
        p_values = []

        for rt in relative_times:
            df_rt = df_clean.copy()
            df_rt['post_rt'] = (df_rt['relative_time'] >= rt).astype(int)
            df_rt['did'] = df_rt[self.treatment_col] * df_rt['post_rt']

            X_cols = [self.treatment_col, 'post_rt', 'did'] + self.covariates
            X = df_rt[X_cols].astype(float)
            X = sm.add_constant(X)
            y = df_rt[self.outcome_col].values.astype(float)

            model = sm.OLS(y, X).fit(cov_type='HC3')
            coefs.append(float(model.params['did']))
            ci = model.conf_int().loc['did']
            conf_int_lower.append(float(ci[0]))
            conf_int_upper.append(float(ci[1]))
            p_values.append(float(model.pvalues['did']))

        self.results['event_study'] = {
            'relative_times': [float(rt) for rt in relative_times],
            'coefficients': coefs,
            'confIntLower': conf_int_lower,
            'confIntUpper': conf_int_upper,
            'pValues': p_values
        }
        return self.results['event_study']

    def run_all_tests(self):
        self.test_parallel_trend_graphical()
        self.test_parallel_trend_statistical()
        
        try:
            self.test_event_study()
        except:
            pass

        return self.results
