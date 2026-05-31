import pandas as pd
import numpy as np
from scipy import stats


class EnhancedPlaceboTester:
    def __init__(self, df, treatment_col, outcome_col, covariates, analysis_method='psm', **kwargs):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates
        self.analysis_method = analysis_method
        self.kwargs = kwargs
        self.results = {}

    def random_treatment_assignment(self, n_permutations=200):
        np.random.seed(42)
        true_effects = []
        
        original_treatment = self.df[self.treatment_col].values.copy()
        n_treated = int(original_treatment.sum())
        
        for i in range(n_permutations):
            permuted = np.zeros(len(original_treatment))
            treated_indices = np.random.choice(len(original_treatment), n_treated, replace=False)
            permuted[treated_indices] = 1
            
            placebo_df = self.df.copy()
            placebo_df[self.treatment_col] = permuted
            
            try:
                if self.analysis_method == 'psm':
                    from .psm import PropensityScoreMatching
                    psm = PropensityScoreMatching(
                        placebo_df, self.treatment_col, self.outcome_col, self.covariates
                    )
                    result = psm.run_analysis()
                    true_effects.append(result['ate']['estimate'])
                else:
                    from .did import DifferenceInDifferences
                    did = DifferenceInDifferences(
                        placebo_df, self.treatment_col, self.outcome_col, self.covariates,
                        time_col=self.kwargs.get('time_col'),
                        post_col=self.kwargs.get('post_col')
                    )
                    result = did.run_analysis()
                    true_effects.append(result['ate']['estimate'])
            except:
                continue
        
        self.results['random_assignment'] = {
            'placebo_effects': [float(e) for e in true_effects],
            'mean_effect': float(np.mean(true_effects)) if true_effects else 0,
            'std_effect': float(np.std(true_effects)) if true_effects else 0,
            'n_permutations': len(true_effects)
        }
        
        return self.results['random_assignment']

    def in_time_placebo(self, n_permutations=100):
        if self.analysis_method != 'did' or 'time_col' not in self.kwargs:
            return None
            
        time_col = self.kwargs['time_col']
        true_effects = []
        
        time_periods = sorted(self.df[time_col].unique())
        
        for i in range(n_permutations):
            if len(time_periods) >= 3:
                fake_cutoff = np.random.choice(time_periods[1:-1])
                placebo_df = self.df.copy()
                placebo_df['fake_post'] = (placebo_df[time_col] >= fake_cutoff).astype(int)
                
                try:
                    from .did import DifferenceInDifferences
                    did = DifferenceInDifferences(
                        placebo_df, self.treatment_col, self.outcome_col, self.covariates,
                        time_col=time_col,
                        post_col='fake_post'
                    )
                    result = did.run_analysis()
                    true_effects.append(result['ate']['estimate'])
                except:
                    continue
        
        self.results['in_time'] = {
            'placebo_effects': [float(e) for e in true_effects],
            'mean_effect': float(np.mean(true_effects)) if true_effects else 0,
            'std_effect': float(np.std(true_effects)) if true_effects else 0,
            'n_permutations': len(true_effects)
        }
        return self.results['in_time']
                
    def subgroup_placebo(self, n_subgroups=5):
        np.random.seed(42)
        subgroup_effects = []
        
        df_clean = self.df.dropna(
            subset=[self.treatment_col, self.outcome_col] + self.covariates
        ).copy()
        
        treated_df = df_clean[df_clean[self.treatment_col] == 1].copy()
        
        for i in range(n_subgroups):
            shuffled = treated_df.sample(frac=0.5, random_state=i)
            
            if self.analysis_method == 'psm':
                from .psm import PropensityScoreMatching
                psm = PropensityScoreMatching(
                    shuffled, self.treatment_col, self.outcome_col, self.covariates
                )
                result = psm.run_analysis()
                subgroup_effects.append(result['ate']['estimate'])
        
        self.results['subgroup'] = {
            'subgroup_effects': [float(e) for e in subgroup_effects],
            'mean_effect': float(np.mean(subgroup_effects)) if subgroup_effects else 0,
            'std_effect': float(np.std(subgroup_effects)) if subgroup_effects else 0,
        }
        return self.results['subgroup']
                
    def outcome_placebo(self, n_permutations=50):
        np.random.seed(42)
        true_effects = []
        
        df_clean = self.df.dropna(
            subset=[self.treatment_col, self.outcome_col] + self.covariates
        ).copy()
        
        for i in range(n_permutations):
            placebo_outcome = np.random.permutation(df_clean[self.outcome_col].values)
            
            placebo_df = df_clean.copy()
            placebo_df[self.outcome_col] = placebo_outcome
            
            try:
                if self.analysis_method == 'psm':
                    from .psm import PropensityScoreMatching
                    psm = PropensityScoreMatching(
                        placebo_df, self.treatment_col, self.outcome_col, self.covariates
                    )
                    result = psm.run_analysis()
                    true_effects.append(result['ate']['estimate'])
            except:
                continue
        
        self.results['outcome_permutation'] = {
            'placebo_effects': [float(e) for e in true_effects],
            'mean_effect': float(np.mean(true_effects)) if true_effects else 0,
            'std_effect': float(np.std(true_effects)) if true_effects else 0,
            'n_permutations': len(true_effects)
        }
        return self.results['outcome_permutation']
                
    def calculate_p_value(self, true_estimate):
        all_placebo_effects = []
        
        if 'random_assignment' in self.results:
            all_placebo_effects.extend(self.results['random_assignment']['placebo_effects'])
        if 'in_time' in self.results and self.results['in_time']:
            all_placebo_effects.extend(self.results['in_time']['placebo_effects'])
        
        if not all_placebo_effects:
            return 1.0
            
        n_extreme = sum(1 for e in all_placebo_effects if abs(e) >= abs(true_estimate))
        p_value = (n_extreme + 1) / (len(all_placebo_effects) + 1)
        
        return float(p_value)
                
    def run_all_tests(self, true_estimate=None):
        self.random_treatment_assignment(n_permutations=100)
        
        if self.analysis_method == 'did':
            self.in_time_placebo(n_permutations=50)
        
        self.outcome_placebo(n_permutations=50)
        
        combined_effects = []
        
        if 'random_assignment' in self.results:
            combined_effects.extend(self.results['random_assignment']['placebo_effects'])
        if 'in_time' in self.results and self.results['in_time']:
            combined_effects.extend(self.results['in_time']['placebo_effects'])
        if 'outcome_permutation' in self.results:
            combined_effects.extend(self.results['outcome_permutation']['placebo_effects'])
        
        self.results['combined'] = {
            'all_effects': [float(e) for e in combined_effects],
            'mean_effect': float(np.mean(combined_effects)) if combined_effects else 0,
            'std_effect': float(np.std(combined_effects)) if combined_effects else 0,
            'n_total': len(combined_effects)
        }
        
        if true_estimate is not None:
            self.results['combined']['p_value'] = self.calculate_p_value(true_estimate)
        
        return self.results
