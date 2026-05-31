import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import statsmodels.api as sm
from scipy import stats


class PropensityScoreMatching:
    def __init__(self, df, treatment_col, outcome_col, covariates):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates
        self.scaler = StandardScaler()
        self.propensity_scores = None
        self.matched_indices = None
        self.df_matched = None

    def _prepare_data(self):
        df_clean = self.df.dropna(subset=[self.treatment_col, self.outcome_col] + self.covariates).copy()
        X = df_clean[self.covariates]
        X_scaled = self.scaler.fit_transform(X)
        return df_clean, X_scaled

    def estimate_propensity_scores(self):
        df_clean, X_scaled = self._prepare_data()
        y = df_clean[self.treatment_col].values
        logreg = LogisticRegression(random_state=42, max_iter=1000, C=1.0)
        logreg.fit(X_scaled, y)
        self.propensity_scores = logreg.predict_proba(X_scaled)[:, 1]
        df_clean['propensity_score'] = self.propensity_scores
        self.df = df_clean
        return self.propensity_scores

    def nearest_neighbor_matching(self, n_neighbors=1, caliper=None):
        if self.propensity_scores is None:
            self.estimate_propensity_scores()
        treated = self.df[self.df[self.treatment_col] == 1].reset_index(drop=True)
        control = self.df[self.df[self.treatment_col] == 0].reset_index(drop=True)
        if len(treated) == 0 or len(control) == 0:
            raise ValueError("处理组或对照组为空")
        treated_scores = treated['propensity_score'].values.reshape(-1, 1)
        control_scores = control['propensity_score'].values.reshape(-1, 1)
        nn = NearestNeighbors(n_neighbors=n_neighbors, metric='euclidean')
        nn.fit(control_scores)
        distances, indices = nn.kneighbors(treated_scores)
        matched_control_indices = []
        matched_treated_indices = []
        for i, (dist, idx) in enumerate(zip(distances, indices)):
            if caliper is not None and dist[0] > caliper:
                continue
            matched_control_indices.append(idx[0])
            matched_treated_indices.append(i)
        matched_control = control.iloc[matched_control_indices].copy()
        matched_treated = treated.iloc[matched_treated_indices].copy()
        matched_control['match_id'] = range(len(matched_control))
        matched_treated['match_id'] = range(len(matched_treated))
        self.df_matched = pd.concat([matched_treated, matched_control], ignore_index=True)
        return self.df_matched

    def calculate_ate(self):
        if self.df_matched is None:
            self.nearest_neighbor_matching()
        treated_outcomes = self.df_matched[self.df_matched[self.treatment_col] == 1][self.outcome_col].values
        control_outcomes = self.df_matched[self.df_matched[self.treatment_col] == 0][self.outcome_col].values
        ate = np.mean(treated_outcomes - control_outcomes)
        se = np.sqrt(np.var(treated_outcomes - control_outcomes) / len(treated_outcomes))
        z_score = ate / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        ci_lower = ate - 1.96 * se
        ci_upper = ate + 1.96 * se
        return {
            'estimate': float(ate),
            'stdError': float(se),
            'pValue': float(p_value),
            'confidenceInterval': [float(ci_lower), float(ci_upper)]
        }

    def calculate_att(self):
        if self.df_matched is None:
            self.nearest_neighbor_matching()
        treated_outcomes = self.df_matched[self.df_matched[self.treatment_col] == 1][self.outcome_col].values
        control_outcomes = self.df_matched[self.df_matched[self.treatment_col] == 0][self.outcome_col].values
        att = np.mean(treated_outcomes - control_outcomes)
        se = np.sqrt(np.var(treated_outcomes - control_outcomes) / len(treated_outcomes))
        z_score = att / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        ci_lower = att - 1.96 * se
        ci_upper = att + 1.96 * se
        return {
            'estimate': float(att),
            'stdError': float(se),
            'pValue': float(p_value),
            'confidenceInterval': [float(ci_lower), float(ci_upper)]
        }

    def balance_check(self):
        if self.propensity_scores is None:
            self.estimate_propensity_scores()
        before_balance = {}
        for cov in self.covariates:
            treated_mean = self.df[self.df[self.treatment_col] == 1][cov].mean()
            control_mean = self.df[self.df[self.treatment_col] == 0][cov].mean()
            treated_std = self.df[self.df[self.treatment_col] == 1][cov].std()
            control_std = self.df[self.df[self.treatment_col] == 0][cov].std()
            pooled_std = np.sqrt((treated_std ** 2 + control_std ** 2) / 2)
            std_diff = (treated_mean - control_mean) / pooled_std if pooled_std > 0 else 0
            before_balance[cov] = {'stdDiff': float(std_diff)}
        after_balance = {}
        if self.df_matched is not None:
            for cov in self.covariates:
                treated_mean = self.df_matched[self.df_matched[self.treatment_col] == 1][cov].mean()
                control_mean = self.df_matched[self.df_matched[self.treatment_col] == 0][cov].mean()
                treated_std = self.df_matched[self.df_matched[self.treatment_col] == 1][cov].std()
                control_std = self.df_matched[self.df_matched[self.treatment_col] == 0][cov].std()
                pooled_std = np.sqrt((treated_std ** 2 + control_std ** 2) / 2)
                std_diff = (treated_mean - control_mean) / pooled_std if pooled_std > 0 else 0
                after_balance[cov] = {'stdDiff': float(std_diff)}
        return {'before': before_balance, 'after': after_balance}

    def get_propensity_scores_distribution(self):
        if self.propensity_scores is None:
            self.estimate_propensity_scores()
        treated_scores = self.df[self.df[self.treatment_col] == 1]['propensity_score'].tolist()
        control_scores = self.df[self.df[self.treatment_col] == 0]['propensity_score'].tolist()
        return {'treated': treated_scores, 'control': control_scores}

    def run_analysis(self):
        self.estimate_propensity_scores()
        self.nearest_neighbor_matching()
        ate = self.calculate_ate()
        att = self.calculate_att()
        balance = self.balance_check()
        propensity_dist = self.get_propensity_scores_distribution()
        sample_size = {
            'total': len(self.df),
            'treated': len(self.df[self.df[self.treatment_col] == 1]),
            'control': len(self.df[self.df[self.treatment_col] == 0])
        }
        matched_sample_size = {
            'total': len(self.df_matched),
            'treated': len(self.df_matched[self.df_matched[self.treatment_col] == 1]),
            'control': len(self.df_matched[self.df_matched[self.treatment_col] == 0])
        }
        return {
            'method': 'psm',
            'ate': ate,
            'att': att,
            'balanceCheck': balance,
            'propensityScores': propensity_dist,
            'sampleSize': sample_size,
            'matchedSampleSize': matched_sample_size
        }
