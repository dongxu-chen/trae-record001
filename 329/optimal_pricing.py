import numpy as np
import pandas as pd
from scipy.optimize import minimize, brentq
from typing import Dict, Tuple, Optional, List
from logit_elasticity_model import PriceElasticityModel


class OptimalPricing:
    def __init__(
        self,
        model: PriceElasticityModel,
        df: pd.DataFrame,
        variable_cost: float = 0.0,
        fixed_cost: float = 0.0,
        use_bootstrap_ci: bool = True
    ):
        self.model = model
        self.df = df
        self.variable_cost = variable_cost
        self.fixed_cost = fixed_cost
        self.use_bootstrap_ci = use_bootstrap_ci and model.bootstrap_results is not None
        
        df_features = model._prepare_features(df, feature_set='full')
        self.mean_features = df_features.mean()
        self.base_sales = df['sales_quantity'].mean()
        
        self._calculate_baseline_probability()
    
    def _calculate_baseline_probability(self) -> None:
        X_eval = self.mean_features.copy()
        
        if self.model.decouple_promotion:
            base_price = self.df['effective_price'].mean()
            X_eval['log_price_non_promo'] = np.log(base_price)
            X_eval['log_price_promo'] = 0
            X_eval['in_promotion'] = 0
            for lag in range(1, self.model.promo_lag_days + 1):
                X_eval[f'post_promo_{lag}'] = 0
        else:
            X_eval['log_price'] = np.log(self.df['effective_price'].mean())
            if 'is_promotion' in X_eval.index:
                X_eval['is_promotion'] = 0
        
        X_scaled = self.model.scaler.transform(X_eval.values.reshape(1, -1))
        
        if self.use_bootstrap_ci:
            prob, prob_lower, prob_upper = self.model._predict_with_bootstrap_ci(X_scaled)
            self.base_probability = prob[0]
            self.base_probability_ci = (prob_lower[0], prob_upper[0])
        else:
            import statsmodels.api as sm
            X_sm = sm.add_constant(X_scaled, has_constant='add')
            self.base_probability = self.model.model_results.predict(X_sm)[0]
            self.base_probability_ci = (self.base_probability, self.base_probability)
    
    def _predict_probability(
        self,
        price: float,
        is_promotion: bool = False,
        include_ci: bool = False
    ):
        X_eval = self.mean_features.copy()
        
        if self.model.decouple_promotion:
            X_eval['log_price_non_promo'] = np.log(price) * (0 if is_promotion else 1)
            X_eval['log_price_promo'] = np.log(price) * (1 if is_promotion else 0)
            X_eval['in_promotion'] = 1 if is_promotion else 0
            for lag in range(1, self.model.promo_lag_days + 1):
                X_eval[f'post_promo_{lag}'] = 0
        else:
            X_eval['log_price'] = np.log(price)
            if 'is_promotion' in X_eval.index:
                X_eval['is_promotion'] = 1 if is_promotion else 0
        
        X_scaled = self.model.scaler.transform(X_eval.values.reshape(1, -1))
        
        if self.use_bootstrap_ci and include_ci:
            prob, prob_lower, prob_upper = self.model._predict_with_bootstrap_ci(X_scaled)
            return prob[0], prob_lower[0], prob_upper[0]
        else:
            import statsmodels.api as sm
            X_sm = sm.add_constant(X_scaled, has_constant='add')
            prob = self.model.model_results.predict(X_sm)[0]
            return prob, prob, prob
    
    def _predict_quantity(
        self,
        price: float,
        is_promotion: bool = False,
        base_sales: Optional[float] = None,
        include_ci: bool = False
    ):
        if base_sales is None:
            base_sales = self.base_sales
            
        prob_base = self.base_probability
        prob_base_upper = self.base_probability_ci[1]
        prob_base_lower = self.base_probability_ci[0]
        
        prob_new, prob_new_lower, prob_new_upper = self._predict_probability(
            price, is_promotion, include_ci=True
        )
        
        scaling_factor = prob_new / prob_base if prob_base > 0 else 0
        scaling_factor_lower = prob_new_lower / prob_base_upper if prob_base_upper > 0 else 0
        scaling_factor_upper = prob_new_upper / prob_base_lower if prob_base_lower > 0 else 0
        
        quantity = base_sales * scaling_factor
        quantity_lower = base_sales * scaling_factor_lower
        quantity_upper = base_sales * scaling_factor_upper
        
        if include_ci:
            return quantity, quantity_lower, quantity_upper
        else:
            return quantity
    
    def calculate_revenue(
        self,
        price: float,
        is_promotion: bool = False,
        include_ci: bool = False
    ):
        if include_ci:
            q, q_lower, q_upper = self._predict_quantity(price, is_promotion, include_ci=True)
            return price * q, price * q_lower, price * q_upper
        else:
            q = self._predict_quantity(price, is_promotion)
            return price * q
    
    def calculate_cost(
        self,
        price: float,
        is_promotion: bool = False,
        include_ci: bool = False
    ):
        if include_ci:
            q, q_lower, q_upper = self._predict_quantity(price, is_promotion, include_ci=True)
            cost = self.fixed_cost + self.variable_cost * q
            cost_lower = self.fixed_cost + self.variable_cost * q_lower
            cost_upper = self.fixed_cost + self.variable_cost * q_upper
            return cost, cost_lower, cost_upper
        else:
            q = self._predict_quantity(price, is_promotion)
            return self.fixed_cost + self.variable_cost * q
    
    def calculate_profit(
        self,
        price: float,
        is_promotion: bool = False,
        include_ci: bool = False
    ):
        if include_ci:
            rev, rev_lower, rev_upper = self.calculate_revenue(price, is_promotion, include_ci=True)
            cost, cost_lower, cost_upper = self.calculate_cost(price, is_promotion, include_ci=True)
            profit = rev - cost
            profit_lower = rev_lower - cost_upper
            profit_upper = rev_upper - cost_lower
            return profit, profit_lower, profit_upper
        else:
            rev = self.calculate_revenue(price, is_promotion)
            cost = self.calculate_cost(price, is_promotion)
            return rev - cost
    
    def calculate_profit_margin(
        self,
        price: float,
        is_promotion: bool = False
    ) -> float:
        profit = self.calculate_profit(price, is_promotion)
        revenue = self.calculate_revenue(price, is_promotion)
        return profit / revenue if revenue > 0 else 0
    
    def _neg_profit(self, price_arr, is_promotion=False):
        return -self.calculate_profit(price_arr[0], is_promotion)
    
    def _neg_revenue(self, price_arr, is_promotion=False):
        return -self.calculate_revenue(price_arr[0], is_promotion)
    
    def find_optimal_price(
        self,
        objective: str = 'profit',
        price_range: Optional[Tuple[float, float]] = None,
        is_promotion: bool = False
    ) -> Dict:
        if price_range is None:
            price_min = self.df['effective_price'].min() * 0.8
            price_max = self.df['effective_price'].max() * 1.2
        else:
            price_min, price_max = price_range
            
        if objective == 'profit':
            neg_obj = lambda p: self._neg_profit(p, is_promotion)
        elif objective == 'revenue':
            neg_obj = lambda p: self._neg_revenue(p, is_promotion)
        else:
            raise ValueError(f"Unknown objective: {objective}")
        
        result = minimize(
            neg_obj,
            x0=[(price_min + price_max) / 2],
            bounds=[(price_min, price_max)],
            method='L-BFGS-B'
        )
        
        optimal_price = result.x[0]
        
        optimal_quantity, optimal_quantity_lower, optimal_quantity_upper = self._predict_quantity(
            optimal_price, is_promotion, include_ci=True
        )
        optimal_revenue, optimal_revenue_lower, optimal_revenue_upper = self.calculate_revenue(
            optimal_price, is_promotion, include_ci=True
        )
        optimal_cost, optimal_cost_lower, optimal_cost_upper = self.calculate_cost(
            optimal_price, is_promotion, include_ci=True
        )
        optimal_profit, optimal_profit_lower, optimal_profit_upper = self.calculate_profit(
            optimal_price, is_promotion, include_ci=True
        )
        
        prices = np.linspace(price_min, price_max, 200)
        
        if self.use_bootstrap_ci:
            profits = []
            profits_lower = []
            profits_upper = []
            revenues = []
            revenues_lower = []
            revenues_upper = []
            
            for p in prices:
                prof, prof_lower, prof_upper = self.calculate_profit(p, is_promotion, include_ci=True)
                rev, rev_lower, rev_upper = self.calculate_revenue(p, is_promotion, include_ci=True)
                profits.append(prof)
                profits_lower.append(prof_lower)
                profits_upper.append(prof_upper)
                revenues.append(rev)
                revenues_lower.append(rev_lower)
                revenues_upper.append(rev_upper)
            
            prices_analysis = pd.DataFrame({
                'price': prices,
                'profit': profits,
                'profit_lower': profits_lower,
                'profit_upper': profits_upper,
                'revenue': revenues,
                'revenue_lower': revenues_lower,
                'revenue_upper': revenues_upper
            })
        else:
            profits = [self.calculate_profit(p, is_promotion) for p in prices]
            revenues = [self.calculate_revenue(p, is_promotion) for p in prices]
            
            prices_analysis = pd.DataFrame({
                'price': prices,
                'profit': profits,
                'revenue': revenues
            })
        
        current_price = self.df['effective_price'].mean()
        
        current_profit, current_profit_lower, current_profit_upper = self.calculate_profit(
            current_price, is_promotion=False, include_ci=True
        )
        current_revenue, current_revenue_lower, current_revenue_upper = self.calculate_revenue(
            current_price, is_promotion=False, include_ci=True
        )
        
        price_scenarios = self._generate_price_scenarios(optimal_price, is_promotion)
        
        result = {
            'objective': objective,
            'is_promotion': is_promotion,
            'optimal_price': optimal_price,
            'optimal_price_ci': (
                max(price_min, optimal_price * 0.95),
                min(price_max, optimal_price * 1.05)
            ),
            'optimal_quantity': optimal_quantity,
            'optimal_quantity_ci': (optimal_quantity_lower, optimal_quantity_upper),
            'optimal_revenue': optimal_revenue,
            'optimal_revenue_ci': (optimal_revenue_lower, optimal_revenue_upper),
            'optimal_cost': optimal_cost,
            'optimal_cost_ci': (optimal_cost_lower, optimal_cost_upper),
            'optimal_profit': optimal_profit,
            'optimal_profit_ci': (optimal_profit_lower, optimal_profit_upper),
            'optimal_profit_margin': self.calculate_profit_margin(optimal_price, is_promotion),
            'current_price': current_price,
            'current_profit': current_profit,
            'current_profit_ci': (current_profit_lower, current_profit_upper),
            'current_revenue': current_revenue,
            'current_revenue_ci': (current_revenue_lower, current_revenue_upper),
            'profit_improvement_pct': (optimal_profit - current_profit) / abs(current_profit) * 100 if current_profit != 0 else np.inf,
            'profit_improvement_pct_ci': (
                (optimal_profit_lower - current_profit_upper) / abs(current_profit_upper) * 100 if current_profit_upper != 0 else np.inf,
                (optimal_profit_upper - current_profit_lower) / abs(current_profit_lower) * 100 if current_profit_lower != 0 else np.inf
            ),
            'revenue_improvement_pct': (optimal_revenue - current_revenue) / current_revenue * 100,
            'revenue_improvement_pct_ci': (
                (optimal_revenue_lower - current_revenue_upper) / current_revenue_upper * 100,
                (optimal_revenue_upper - current_revenue_lower) / current_revenue_lower * 100
            ),
            'price_range': (price_min, price_max),
            'price_scenarios': price_scenarios,
            'prices_analysis': prices_analysis
        }
        
        if self.use_bootstrap_ci and self.model.bootstrap_results is not None:
            if is_promotion:
                elast_ci = self.model.bootstrap_results['elasticity_promo_ci']
            else:
                elast_ci = self.model.bootstrap_results['elasticity_non_promo_ci']
            result['elasticity_ci'] = (elast_ci['ci_lower'], elast_ci['ci_upper'])
        
        return result
    
    def _generate_price_scenarios(
        self,
        optimal_price: float,
        is_promotion: bool = False
    ) -> pd.DataFrame:
        scenarios = []
        
        price_changes = [-0.3, -0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2, 0.3]
        
        for pct_change in price_changes:
            price = optimal_price * (1 + pct_change)
            
            quantity, q_lower, q_upper = self._predict_quantity(
                price, is_promotion, include_ci=True
            )
            revenue, rev_lower, rev_upper = self.calculate_revenue(
                price, is_promotion, include_ci=True
            )
            cost, cost_lower, cost_upper = self.calculate_cost(
                price, is_promotion, include_ci=True
            )
            profit, prof_lower, prof_upper = self.calculate_profit(
                price, is_promotion, include_ci=True
            )
            margin = self.calculate_profit_margin(price, is_promotion)
            
            opt_profit = self.calculate_profit(optimal_price, is_promotion)
            
            scenarios.append({
                'price_change_pct': pct_change * 100,
                'price': price,
                'quantity': quantity,
                'quantity_ci': (q_lower, q_upper),
                'revenue': revenue,
                'revenue_ci': (rev_lower, rev_upper),
                'cost': cost,
                'cost_ci': (cost_lower, cost_upper),
                'profit': profit,
                'profit_ci': (prof_lower, prof_upper),
                'profit_margin': margin * 100,
                'vs_optimal_profit_pct': (profit - opt_profit) / abs(opt_profit) * 100 if opt_profit != 0 else np.inf
            })
        
        return pd.DataFrame(scenarios).round(2)
    
    def find_breakeven_price(
        self,
        price_range: Optional[Tuple[float, float]] = None,
        is_promotion: bool = False
    ) -> Optional[float]:
        if price_range is None:
            price_min = self.df['effective_price'].min() * 0.5
            price_max = self.df['effective_price'].max() * 2
        else:
            price_min, price_max = price_range
        
        try:
            breakeven_price = brentq(
                lambda p: self.calculate_profit(p, is_promotion),
                price_min,
                price_max
            )
            return breakeven_price
        except ValueError:
            return None
    
    def calculate_price_sensitivity_matrix(
        self,
        base_price: Optional[float] = None,
        price_changes: Optional[List[float]] = None,
        is_promotion: bool = False
    ) -> pd.DataFrame:
        if base_price is None:
            base_price = self.df['effective_price'].mean()
            
        if price_changes is None:
            price_changes = [-0.3, -0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2, 0.3]
        
        base_quantity, base_q_lower, base_q_upper = self._predict_quantity(
            base_price, is_promotion, include_ci=True
        )
        base_revenue, base_rev_lower, base_rev_upper = self.calculate_revenue(
            base_price, is_promotion, include_ci=True
        )
        base_profit, base_prof_lower, base_prof_upper = self.calculate_profit(
            base_price, is_promotion, include_ci=True
        )
        
        sensitivity_data = []
        
        for pct_change in price_changes:
            new_price = base_price * (1 + pct_change)
            
            new_quantity, new_q_lower, new_q_upper = self._predict_quantity(
                new_price, is_promotion, include_ci=True
            )
            new_revenue, new_rev_lower, new_rev_upper = self.calculate_revenue(
                new_price, is_promotion, include_ci=True
            )
            new_profit, new_prof_lower, new_prof_upper = self.calculate_profit(
                new_price, is_promotion, include_ci=True
            )
            
            elasticity = ((new_quantity - base_quantity) / base_quantity) / pct_change if pct_change != 0 else np.nan
            
            sensitivity_data.append({
                'price_change_pct': pct_change * 100,
                'price': new_price,
                'quantity': new_quantity,
                'quantity_ci': (new_q_lower, new_q_upper),
                'quantity_change_pct': (new_quantity - base_quantity) / base_quantity * 100,
                'quantity_change_pct_ci': (
                    (new_q_lower - base_q_upper) / base_q_upper * 100,
                    (new_q_upper - base_q_lower) / base_q_lower * 100
                ),
                'revenue': new_revenue,
                'revenue_ci': (new_rev_lower, new_rev_upper),
                'revenue_change_pct': (new_revenue - base_revenue) / base_revenue * 100,
                'revenue_change_pct_ci': (
                    (new_rev_lower - base_rev_upper) / base_rev_upper * 100,
                    (new_rev_upper - base_rev_lower) / base_rev_lower * 100
                ),
                'profit': new_profit,
                'profit_ci': (new_prof_lower, new_prof_upper),
                'profit_change_pct': (new_profit - base_profit) / abs(base_profit) * 100 if base_profit != 0 else np.nan,
                'profit_change_pct_ci': (
                    (new_prof_lower - base_prof_upper) / abs(base_prof_upper) * 100 if base_prof_upper != 0 else np.nan,
                    (new_prof_upper - base_prof_lower) / abs(base_prof_lower) * 100 if base_prof_lower != 0 else np.nan
                ),
                'implied_elasticity': elasticity
            })
        
        return pd.DataFrame(sensitivity_data).round(2)
    
    def analyze_price_segmentation(
        self,
        n_segments: int = 5,
        is_promotion: bool = False
    ) -> pd.DataFrame:
        elasticity_df = self.model.calculate_price_elasticity(self.df, include_bootstrap_ci=self.use_bootstrap_ci)
        
        if 'is_promotion' in elasticity_df.columns:
            elasticity_df = elasticity_df[elasticity_df['is_promotion'] == (1 if is_promotion else 0)]
        
        elasticity_df['segment'] = pd.qcut(
            elasticity_df['price'],
            q=n_segments,
            labels=[f'区间{i+1}' for i in range(n_segments)]
        )
        
        agg_dict = {
            'price': ['min', 'max', 'mean'],
            'purchase_probability': ['min', 'max', 'mean'],
            'point_elasticity': ['min', 'max', 'mean']
        }
        
        if self.use_bootstrap_ci:
            agg_dict['prob_ci_lower'] = ['mean']
            agg_dict['prob_ci_upper'] = ['mean']
            agg_dict['elasticity_ci_lower'] = ['mean']
            agg_dict['elasticity_ci_upper'] = ['mean']
        
        segment_analysis = elasticity_df.groupby('segment').agg(agg_dict).round(3)
        
        segment_analysis.columns = ['_'.join(col).strip() for col in segment_analysis.columns.values]
        segment_analysis = segment_analysis.reset_index()
        
        segment_analysis['revenue_potential'] = (
            segment_analysis['price_mean'] * segment_analysis['purchase_probability_mean']
        )
        
        segment_analysis['recommendation'] = segment_analysis['point_elasticity_mean'].apply(
            lambda e: '建议降价' if e < -1.5 else ('建议维持' if e < -0.5 else '建议涨价')
        )
        
        return segment_analysis
    
    def generate_pricing_recommendations(self) -> Dict:
        profit_opt_non_promo = self.find_optimal_price(objective='profit', is_promotion=False)
        revenue_opt_non_promo = self.find_optimal_price(objective='revenue', is_promotion=False)
        
        profit_opt_promo = self.find_optimal_price(objective='profit', is_promotion=True)
        revenue_opt_promo = self.find_optimal_price(objective='revenue', is_promotion=True)
        
        current_price = self.df['effective_price'].mean()
        
        elasticity_df = self.model.calculate_price_elasticity(
            self.df,
            price_range=(current_price * 0.99, current_price * 1.01),
            n_points=2,
            include_bootstrap_ci=False
        )
        
        if 'is_promotion' in elasticity_df.columns:
            non_promo_elasticity = elasticity_df[elasticity_df['is_promotion'] == 0]['point_elasticity'].mean()
            promo_elasticity = elasticity_df[elasticity_df['is_promotion'] == 1]['point_elasticity'].mean()
        else:
            non_promo_elasticity = elasticity_df['point_elasticity'].mean()
            promo_elasticity = non_promo_elasticity
        
        full_elasticity_df = self.model.calculate_price_elasticity(
            self.df, include_bootstrap_ci=self.use_bootstrap_ci
        )
        elasticity_summary = self.model.get_elasticity_summary(full_elasticity_df)
        
        recommendations = []
        
        def get_recommendation_for_elasticity(elasticity, opt_price, context=""):
            if elasticity < -1.5:
                return {
                    'priority': '高',
                    'type': f'降价策略{context}',
                    'description': f'当前价格弹性为 {elasticity:.2f}，属于极富弹性区间，降价可显著提升销量和收入。',
                    'suggested_price': opt_price,
                    'expected_impact': f'预计利润提升 {opt_price.get("profit_improvement_pct", 0):.1f}%'
                }
            elif elasticity < -1:
                return {
                    'priority': '中',
                    'type': f'适度降价{context}',
                    'description': f'当前价格弹性为 {elasticity:.2f}，需求富有弹性，适度降价可提升整体收入。',
                    'suggested_price': opt_price,
                    'expected_impact': f'预计利润提升 {opt_price.get("profit_improvement_pct", 0):.1f}%'
                }
            elif elasticity < -0.5:
                return {
                    'priority': '低',
                    'type': f'维持价格{context}',
                    'description': f'当前价格弹性为 {elasticity:.2f}，处于单位弹性区间，价格调整对收入影响较小。',
                    'suggested_price': current_price,
                    'expected_impact': '建议观察市场变化后再做决策'
                }
            else:
                return {
                    'priority': '高',
                    'type': f'涨价策略{context}',
                    'description': f'当前价格弹性为 {elasticity:.2f}，需求缺乏弹性，涨价可在销量小幅下降的情况下提升收入。',
                    'suggested_price': opt_price,
                    'expected_impact': f'预计利润提升 {opt_price.get("profit_improvement_pct", 0):.1f}%'
                }
        
        non_promo_rec = get_recommendation_for_elasticity(
            non_promo_elasticity, profit_opt_non_promo, context="（非促销期）"
        )
        promo_rec = get_recommendation_for_elasticity(
            promo_elasticity, profit_opt_promo, context="（促销期）"
        )
        
        recommendations.append(non_promo_rec)
        recommendations.append(promo_rec)
        
        if abs(promo_elasticity - non_promo_elasticity) > 0.5:
            recommendations.append({
                'priority': '中',
                'type': '差异化定价',
                'description': f'促销期与非促销期弹性差异显著（{promo_elasticity:.2f} vs {non_promo_elasticity:.2f}），建议实施差异化定价策略。',
                'suggested_price': f"非促销期 ¥{profit_opt_non_promo['optimal_price']:.2f}，促销期 ¥{profit_opt_promo['optimal_price']:.2f}",
                'expected_impact': '最大化不同时期的收益'
            })
        
        result = {
            'current_price': current_price,
            'current_elasticity_non_promo': non_promo_elasticity,
            'current_elasticity_promo': promo_elasticity,
            'profit_optimal_price_non_promo': profit_opt_non_promo['optimal_price'],
            'profit_optimal_price_promo': profit_opt_promo['optimal_price'],
            'revenue_optimal_price_non_promo': revenue_opt_non_promo['optimal_price'],
            'revenue_optimal_price_promo': revenue_opt_promo['optimal_price'],
            'elasticity_summary': elasticity_summary,
            'recommendations': recommendations,
            'profit_analysis_non_promo': profit_opt_non_promo,
            'revenue_analysis_non_promo': revenue_opt_non_promo,
            'profit_analysis_promo': profit_opt_promo,
            'revenue_analysis_promo': revenue_opt_promo
        }
        
        if self.use_bootstrap_ci and self.model.bootstrap_results is not None:
            result['bootstrap_results'] = {
                'n_bootstrap': self.model.bootstrap_results['n_bootstrap'],
                'confidence_level': self.model.bootstrap_results['confidence_level'],
                'elasticity_non_promo_ci': self.model.bootstrap_results['elasticity_non_promo_ci'],
                'elasticity_promo_ci': self.model.bootstrap_results['elasticity_promo_ci']
            }
        
        return result
