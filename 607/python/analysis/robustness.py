import pandas as pd
import numpy as np
from scipy import stats


class RobustnessTests:
    def __init__(self, df, treatment_col, outcome_col, covariates, analysis_method='psm', **kwargs):
        self.df = df.copy()
        self.treatment_col = treatment_col
        self.outcome_col = outcome_col
        self.covariates = covariates
        self.analysis_method = analysis_method
        self.kwargs = kwargs

    def placebo_test(self, n_iterations=100):
        np.random.seed(42)
        true_effects = []
        for _ in range(n_iterations):
            placebo_treatment = np.random.permutation(self.df[self.treatment_col].values)
            placebo_df = self.df.copy()
            placebo_df['placebo_treatment'] = placebo_treatment
            if self.analysis_method == 'psm':
                from .psm import PropensityScoreMatching
                psm = PropensityScoreMatching(
                    placebo_df, 'placebo_treatment', self.outcome_col, self.covariates
                )
                result = psm.run_analysis()
                true_effects.append(result['ate']['estimate'])
            else:
                from .did import DifferenceInDifferences
                did = DifferenceInDifferences(
                    placebo_df, 'placebo_treatment', self.outcome_col, self.covariates,
                    time_col=self.kwargs.get('time_col'),
                    post_col=self.kwargs.get('post_col')
                )
                result = did.run_analysis()
                true_effects.append(result['ate']['estimate'])
        mean_effect = np.mean(true_effects)
        p_value = np.mean(np.abs(true_effects) >= np.abs(mean_effect))
        return {
            'estimate': float(mean_effect),
            'pValue': float(p_value)
        }

    def different_methods_comparison(self):
        results = []
        if self.analysis_method == 'psm':
            from .psm import PropensityScoreMatching
            for method_name, n_neighbors in [('1:1 Matching', 1), ('1:2 Matching', 2), ('1:3 Matching', 3)]:
                try:
                    psm = PropensityScoreMatching(
                        self.df, self.treatment_col, self.outcome_col, self.covariates
                    )
                    psm.estimate_propensity_scores()
                    psm.nearest_neighbor_matching(n_neighbors=n_neighbors)
                    ate = psm.calculate_ate()
                    results.append({
                        'method': method_name,
                        'estimate': ate['estimate'],
                        'stdError': ate['stdError']
                    })
                except:
                    pass
        else:
            from .did import DifferenceInDifferences
            did = DifferenceInDifferences(
                self.df, self.treatment_col, self.outcome_col, self.covariates,
                time_col=self.kwargs.get('time_col'),
                post_col=self.kwargs.get('post_col')
            )
            base_result = did.run_analysis()
            results.append({
                'method': 'Baseline DID',
                'estimate': base_result['ate']['estimate'],
                'stdError': base_result['ate']['stdError']
            })
            if len(self.covariates) > 1:
                for i in range(min(len(self.covariates), 3)):
                    reduced_covariates = [c for j, c in enumerate(self.covariates) if j != i]
                    try:
                        did_reduced = DifferenceInDifferences(
                            self.df, self.treatment_col, self.outcome_col, reduced_covariates,
                            time_col=self.kwargs.get('time_col'),
                            post_col=self.kwargs.get('post_col')
                        )
                        reduced_result = did_reduced.run_analysis()
                        results.append({
                            'method': f'DID w/o {self.covariates[i]}',
                            'estimate': reduced_result['ate']['estimate'],
                            'stdError': reduced_result['ate']['stdError']
                        })
                    except:
                        pass
        return results

    def sensitivity_analysis(self, rho_values=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5]):
        if self.analysis_method == 'psm':
            from .psm import PropensityScoreMatching
            psm = PropensityScoreMatching(
                self.df, self.treatment_col, self.outcome_col, self.covariates
            )
            base_result = psm.run_analysis()
            base_effect = base_result['ate']['estimate']
        else:
            from .did import DifferenceInDifferences
            did = DifferenceInDifferences(
                self.df, self.treatment_col, self.outcome_col, self.covariates,
                time_col=self.kwargs.get('time_col'),
                post_col=self.kwargs.get('post_col')
            )
            base_result = did.run_analysis()
            base_effect = base_result['ate']['estimate']
        bounds = []
        for rho in rho_values:
            gamma = np.exp(rho)
            lower_bound = base_effect * (1 / gamma)
            upper_bound = base_effect * gamma
            bounds.append([float(lower_bound), float(upper_bound)])
        return {
            'rhoValues': rho_values,
            'estimateBounds': bounds
        }

    def run_all_tests(self):
        tests = {}
        try:
            tests['placeboTest'] = self.placebo_test(n_iterations=50)
        except:
            pass
        try:
            tests['differentMethods'] = self.different_methods_comparison()
        except:
            pass
        try:
            tests['sensitivityAnalysis'] = self.sensitivity_analysis()
        except:
            pass
        return tests
