import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from logit_elasticity_model import PriceElasticityModel


class PromotionSimulator:
    def __init__(
        self,
        model: PriceElasticityModel,
        df: pd.DataFrame,
        base_price: Optional[float] = None,
        variable_cost: float = 0.0,
        include_post_promo_effect: bool = True,
        post_promo_halflife_days: float = 5.0,
        max_post_promo_days: int = 21,
        stockpiling_factor: float = 0.3,
        use_bootstrap_ci: bool = True
    ):
        self.model = model
        self.df = df
        self.base_price = base_price if base_price else df['effective_price'].mean()
        self.variable_cost = variable_cost
        self.include_post_promo_effect = include_post_promo_effect
        self.post_promo_halflife = post_promo_halflife_days
        self.max_post_promo_days = max_post_promo_days
        self.stockpiling_factor = stockpiling_factor
        self.use_bootstrap_ci = use_bootstrap_ci and model.bootstrap_results is not None
        
        df_features = model._prepare_features(df, feature_set='full')
        self.mean_features = df_features.mean()
        self.base_demand = df['sales_quantity'].mean()
        
        self._calculate_baseline_probability()
        self._extract_post_promo_coefficients()
    
    def _calculate_baseline_probability(self) -> None:
        X_eval = self.mean_features.copy()
        
        if self.model.decouple_promotion:
            X_eval['log_price_non_promo'] = np.log(self.base_price)
            X_eval['log_price_promo'] = 0
            X_eval['in_promotion'] = 0
            for lag in range(1, self.model.promo_lag_days + 1):
                X_eval[f'post_promo_{lag}'] = 0
        else:
            X_eval['log_price'] = np.log(self.base_price)
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
    
    def _extract_post_promo_coefficients(self) -> None:
        self.post_promo_coeffs = {}
        if self.model.decouple_promotion and self.model.model_results is not None:
            param_names = self.model.model_results.params.index.tolist()
            for lag in range(1, self.model.promo_lag_days + 1):
                feature_name = f'post_promo_{lag}'
                if feature_name in self.model.feature_names:
                    idx = self.model.feature_names.index(feature_name) + 1
                    param_name = param_names[idx] if idx < len(param_names) else feature_name
                    if param_name in param_names:
                        self.post_promo_coeffs[lag] = {
                            'coefficient': self.model.model_results.params[param_name],
                            'p_value': self.model.model_results.pvalues[param_name],
                            'significant': self.model.model_results.pvalues[param_name] < 0.05
                        }
                    else:
                        self.post_promo_coeffs[lag] = {
                            'coefficient': 0,
                            'p_value': 1.0,
                            'significant': False
                        }
    
    def _get_post_promo_decay_factor(self, days_after_promo: int) -> float:
        if days_after_promo <= 0:
            return 1.0
        
        decay = np.exp(-days_after_promo * np.log(2) / self.post_promo_halflife)
        
        if self.post_promo_coeffs:
            coeff_sum = 0
            max_lag = min(days_after_promo, self.model.promo_lag_days)
            for lag in range(1, max_lag + 1):
                if lag in self.post_promo_coeffs and self.post_promo_coeffs[lag]['significant']:
                    coeff = self.post_promo_coeffs[lag]['coefficient']
                    if coeff < 0:
                        coeff_sum += abs(coeff) * np.exp(-(days_after_promo - lag) / 3)
            
            if coeff_sum > 0:
                decay = min(decay, 1 - coeff_sum / 5)
        
        return max(0.3, decay)
    
    def _get_stockpiling_adjustment(
        self,
        day_in_promo: int,
        total_promo_days: int,
        discount_pct: float
    ) -> float:
        if day_in_promo < 0:
            return 1.0
        
        stockpiling_curve = np.minimum(
            1.0 + self.stockpiling_factor * (discount_pct / 0.2),
            1.0 + self.stockpiling_factor * np.sin(np.pi * (day_in_promo + 1) / (total_promo_days + 2))
        )
        
        return stockpiling_curve
    
    def _predict_demand(
        self,
        price: float,
        is_promotion: bool = False,
        advertising_spend: Optional[float] = None,
        post_promo_lags: Optional[Dict[int, int]] = None,
        include_ci: bool = False
    ):
        X_eval = self.mean_features.copy()
        
        if self.model.decouple_promotion:
            X_eval['log_price_non_promo'] = np.log(price) * (0 if is_promotion else 1)
            X_eval['log_price_promo'] = np.log(price) * (1 if is_promotion else 0)
            X_eval['in_promotion'] = 1 if is_promotion else 0
            
            for lag in range(1, self.model.promo_lag_days + 1):
                X_eval[f'post_promo_{lag}'] = 0
            
            if post_promo_lags:
                for lag, value in post_promo_lags.items():
                    if lag in range(1, self.model.promo_lag_days + 1):
                        X_eval[f'post_promo_{lag}'] = value
        else:
            X_eval['log_price'] = np.log(price)
            X_eval['is_promotion'] = 1 if is_promotion else 0
        
        if advertising_spend is not None:
            X_eval['advertising_spend'] = advertising_spend
        
        X_scaled = self.model.scaler.transform(X_eval.values.reshape(1, -1))
        
        if self.use_bootstrap_ci and include_ci:
            prob, prob_lower, prob_upper = self.model._predict_with_bootstrap_ci(X_scaled)
            prob_val = prob[0]
            prob_lower_val = prob_lower[0]
            prob_upper_val = prob_upper[0]
        else:
            import statsmodels.api as sm
            X_sm = sm.add_constant(X_scaled, has_constant='add')
            prob_val = self.model.model_results.predict(X_sm)[0]
            prob_lower_val = prob_val
            prob_upper_val = prob_val
        
        scaling_factor = prob_val / self.base_probability if self.base_probability > 0 else 0
        scaling_factor_lower = prob_lower_val / self.base_probability_ci[1] if self.base_probability_ci[1] > 0 else 0
        scaling_factor_upper = prob_upper_val / self.base_probability_ci[0] if self.base_probability_ci[0] > 0 else 0
        
        demand = self.base_demand * scaling_factor
        demand_lower = self.base_demand * scaling_factor_lower
        demand_upper = self.base_demand * scaling_factor_upper
        
        if include_ci:
            return demand, demand_lower, demand_upper
        else:
            return demand
    
    def simulate_promotion(
        self,
        discount_pct: float,
        duration_days: int,
        advertising_spend: float = 50.0,
        strategy: str = 'direct_discount',
        include_post_promo: bool = True
    ) -> Dict:
        promotion_price = self.base_price * (1 - discount_pct)
        
        daily_demand_promo, daily_demand_promo_lower, daily_demand_promo_upper = self._predict_demand(
            price=promotion_price,
            is_promotion=True,
            advertising_spend=advertising_spend,
            include_ci=True
        )
        
        daily_demand_normal, daily_demand_normal_lower, daily_demand_normal_upper = self._predict_demand(
            price=self.base_price,
            is_promotion=False,
            include_ci=True
        )
        
        if strategy == 'direct_discount':
            effective_price = promotion_price
            demand_multiplier = 1.0
        elif strategy == 'buy_one_get_one':
            effective_price = promotion_price * 0.5
            demand_multiplier = 1.5
        elif strategy == 'bundle':
            effective_price = promotion_price * 0.8
            demand_multiplier = 1.2
        elif strategy == 'coupon':
            effective_price = promotion_price
            demand_multiplier = 0.9
        else:
            effective_price = promotion_price
            demand_multiplier = 1.0
        
        daily_demand_promo *= demand_multiplier
        daily_demand_promo_lower *= demand_multiplier
        daily_demand_promo_upper *= demand_multiplier
        
        total_demand_promo = daily_demand_promo * duration_days
        total_demand_normal = daily_demand_normal * duration_days
        total_demand_promo_lower = daily_demand_promo_lower * duration_days
        total_demand_promo_upper = daily_demand_promo_upper * duration_days
        total_demand_normal_lower = daily_demand_normal_lower * duration_days
        total_demand_normal_upper = daily_demand_normal_upper * duration_days
        
        sales_lift = total_demand_promo - total_demand_normal
        sales_lift_pct = sales_lift / total_demand_normal if total_demand_normal > 0 else 0
        sales_lift_lower = total_demand_promo_lower - total_demand_normal_upper
        sales_lift_upper = total_demand_promo_upper - total_demand_normal_lower
        sales_lift_pct_lower = sales_lift_lower / total_demand_normal_upper if total_demand_normal_upper > 0 else 0
        sales_lift_pct_upper = sales_lift_upper / total_demand_normal_lower if total_demand_normal_lower > 0 else 0
        
        promo_revenue = total_demand_promo * effective_price
        normal_revenue = total_demand_normal * self.base_price
        promo_revenue_lower = total_demand_promo_lower * effective_price
        promo_revenue_upper = total_demand_promo_upper * effective_price
        normal_revenue_lower = total_demand_normal_lower * self.base_price
        normal_revenue_upper = total_demand_normal_upper * self.base_price
        
        promo_cost = total_demand_promo * self.variable_cost + advertising_spend * duration_days
        normal_cost = total_demand_normal * self.variable_cost
        promo_cost_lower = total_demand_promo_lower * self.variable_cost + advertising_spend * duration_days
        promo_cost_upper = total_demand_promo_upper * self.variable_cost + advertising_spend * duration_days
        
        promo_profit = promo_revenue - promo_cost
        normal_profit = normal_revenue - normal_cost
        promo_profit_lower = promo_revenue_lower - promo_cost_upper
        promo_profit_upper = promo_revenue_upper - promo_cost_lower
        normal_profit_lower = normal_revenue_lower - normal_cost
        normal_profit_upper = normal_revenue_upper - normal_cost
        
        revenue_change = promo_revenue - normal_revenue
        profit_change = promo_profit - normal_profit
        revenue_change_lower = promo_revenue_lower - normal_revenue_upper
        revenue_change_upper = promo_revenue_upper - normal_revenue_lower
        profit_change_lower = promo_profit_lower - normal_profit_upper
        profit_change_upper = promo_profit_upper - normal_profit_lower
        
        revenue_change_pct = revenue_change / normal_revenue if normal_revenue > 0 else 0
        profit_change_pct = profit_change / abs(normal_profit) if normal_profit != 0 else 0
        revenue_change_pct_lower = revenue_change_lower / normal_revenue_upper if normal_revenue_upper > 0 else 0
        revenue_change_pct_upper = revenue_change_upper / normal_revenue_lower if normal_revenue_lower > 0 else 0
        profit_change_pct_lower = profit_change_lower / abs(normal_profit_upper) if normal_profit_upper != 0 else 0
        profit_change_pct_upper = profit_change_upper / abs(normal_profit_lower) if normal_profit_lower != 0 else 0
        
        roi = profit_change / (advertising_spend * duration_days) if advertising_spend * duration_days > 0 else np.inf
        roi_lower = profit_change_lower / (advertising_spend * duration_days) if advertising_spend * duration_days > 0 else np.inf
        roi_upper = profit_change_upper / (advertising_spend * duration_days) if advertising_spend * duration_days > 0 else np.inf
        
        post_promo_loss = 0.0
        post_promo_loss_ci = (0.0, 0.0)
        net_profit_change = profit_change
        net_profit_change_ci = (profit_change_lower, profit_change_upper)
        
        if include_post_promo and self.include_post_promo_effect:
            post_promo_results = self._calculate_post_promotion_effect(
                daily_demand_promo=daily_demand_promo,
                promo_discount=discount_pct,
                promo_duration=duration_days,
                ad_spend=advertising_spend
            )
            post_promo_loss = post_promo_results['total_loss']
            post_promo_loss_ci = post_promo_results['total_loss_ci']
            net_profit_change = profit_change - post_promo_loss
            net_profit_change_ci = (
                profit_change_lower - post_promo_loss_ci[1],
                profit_change_upper - post_promo_loss_ci[0]
            )
        
        price_elasticity = sales_lift_pct / (-discount_pct) if discount_pct > 0 else np.nan
        
        return {
            'strategy': strategy,
            'discount_pct': discount_pct,
            'duration_days': duration_days,
            'base_price': self.base_price,
            'promotion_price': promotion_price,
            'effective_price': effective_price,
            'advertising_spend': advertising_spend,
            'daily_demand_normal': daily_demand_normal,
            'daily_demand_normal_ci': (daily_demand_normal_lower, daily_demand_normal_upper),
            'daily_demand_promo': daily_demand_promo,
            'daily_demand_promo_ci': (daily_demand_promo_lower, daily_demand_promo_upper),
            'total_demand_normal': total_demand_normal,
            'total_demand_normal_ci': (total_demand_normal_lower, total_demand_normal_upper),
            'total_demand_promo': total_demand_promo,
            'total_demand_promo_ci': (total_demand_promo_lower, total_demand_promo_upper),
            'cumulative_sales': total_demand_promo,
            'sales_lift': sales_lift,
            'sales_lift_ci': (sales_lift_lower, sales_lift_upper),
            'sales_lift_pct': sales_lift_pct,
            'sales_lift_pct_ci': (sales_lift_pct_lower, sales_lift_pct_upper),
            'normal_revenue': normal_revenue,
            'normal_revenue_ci': (normal_revenue_lower, normal_revenue_upper),
            'promo_revenue': promo_revenue,
            'promo_revenue_ci': (promo_revenue_lower, promo_revenue_upper),
            'revenue_change': revenue_change,
            'revenue_change_ci': (revenue_change_lower, revenue_change_upper),
            'revenue_change_pct': revenue_change_pct,
            'revenue_change_pct_ci': (revenue_change_pct_lower, revenue_change_pct_upper),
            'normal_profit': normal_profit,
            'normal_profit_ci': (normal_profit_lower, normal_profit_upper),
            'promo_profit': promo_profit,
            'promo_profit_ci': (promo_profit_lower, promo_profit_upper),
            'profit_change': profit_change,
            'profit_change_ci': (profit_change_lower, profit_change_upper),
            'profit_change_pct': profit_change_pct,
            'profit_change_pct_ci': (profit_change_pct_lower, profit_change_pct_upper),
            'roi': roi,
            'roi_ci': (roi_lower, roi_upper),
            'post_promo_loss': post_promo_loss,
            'post_promo_loss_ci': post_promo_loss_ci,
            'net_profit_change': net_profit_change,
            'net_profit_change_ci': net_profit_change_ci,
            'price_elasticity': price_elasticity,
            'break_even_lift_pct': (advertising_spend * duration_days) / (normal_revenue - normal_cost)
        }
    
    def _calculate_post_promotion_effect(
        self,
        daily_demand_promo: float,
        promo_discount: float,
        promo_duration: int,
        ad_spend: float
    ) -> Dict:
        days_to_analyze = self.max_post_promo_days
        
        normal_daily_demand = self._predict_demand(
            price=self.base_price,
            is_promotion=False
        )
        
        total_loss_demand = 0.0
        total_loss_revenue = 0.0
        total_loss_profit = 0.0
        
        daily_losses = []
        
        for day in range(1, days_to_analyze + 1):
            decay_factor = self._get_post_promo_decay_factor(day)
            
            post_promo_lags = {}
            for lag in range(1, self.model.promo_lag_days + 1):
                if day >= lag:
                    post_promo_lags[lag] = 1
            
            adjusted_demand = self._predict_demand(
                price=self.base_price,
                is_promotion=False,
                advertising_spend=ad_spend * 0.1,
                post_promo_lags=post_promo_lags
            )
            
            if day <= 3:
                adjusted_demand *= (0.8 + 0.2 * (day / 3))
            
            effective_demand = min(normal_daily_demand * decay_factor, adjusted_demand)
            effective_demand *= (1 - self.stockpiling_factor * (promo_discount / 0.2) * np.exp(-day / 7))
            
            demand_lost = normal_daily_demand - effective_demand
            revenue_lost = demand_lost * self.base_price
            profit_lost = revenue_lost - demand_lost * self.variable_cost
            
            total_loss_demand += max(0, demand_lost)
            total_loss_revenue += max(0, revenue_lost)
            total_loss_profit += max(0, profit_lost)
            
            daily_losses.append({
                'day': day,
                'decay_factor': decay_factor,
                'normal_demand': normal_daily_demand,
                'adjusted_demand': effective_demand,
                'demand_lost': max(0, demand_lost),
                'revenue_lost': max(0, revenue_lost),
                'profit_lost': max(0, profit_lost)
            })
        
        loss_multiplier = 1.0 + promo_discount * 0.5
        total_loss_demand *= loss_multiplier
        total_loss_revenue *= loss_multiplier
        total_loss_profit *= loss_multiplier
        
        if self.use_bootstrap_ci:
            ci_factor = 0.2
            total_loss_ci = (
                total_loss_profit * (1 - ci_factor),
                total_loss_profit * (1 + ci_factor)
            )
        else:
            total_loss_ci = (total_loss_profit, total_loss_profit)
        
        return {
            'daily_losses': pd.DataFrame(daily_losses),
            'total_demand_loss': total_loss_demand,
            'total_revenue_loss': total_loss_revenue,
            'total_loss': total_loss_profit,
            'total_loss_ci': total_loss_ci,
            'recovery_days': self._estimate_recovery_days(daily_losses)
        }
    
    def _estimate_recovery_days(self, daily_losses: List[Dict]) -> int:
        df = pd.DataFrame(daily_losses)
        if len(df) == 0:
            return 0
        
        normal_demand = df['normal_demand'].iloc[0]
        for i, row in df.iterrows():
            if row['demand_lost'] < normal_demand * 0.05:
                return row['day']
        
        return len(df)
    
    def run_multiple_simulations(
        self,
        discount_range: Tuple[float, float] = (0.05, 0.40),
        duration_range: Tuple[int, int] = (3, 30),
        n_discounts: int = 8,
        n_durations: int = 5,
        include_post_promo: bool = True
    ) -> pd.DataFrame:
        discounts = np.linspace(discount_range[0], discount_range[1], n_discounts)
        durations = np.linspace(duration_range[0], duration_range[1], n_durations, dtype=int)
        
        strategies = ['direct_discount', 'buy_one_get_one', 'bundle', 'coupon']
        
        results = []
        
        for discount in discounts:
            for duration in durations:
                for strategy in strategies:
                    result = self.simulate_promotion(
                        discount_pct=discount,
                        duration_days=duration,
                        strategy=strategy,
                        include_post_promo=include_post_promo
                    )
                    results.append(result)
        
        return pd.DataFrame(results)
    
    def find_optimal_promotion(
        self,
        simulation_results: Optional[pd.DataFrame] = None,
        objective: str = 'profit',
        include_post_promo: bool = True
    ) -> Dict:
        if simulation_results is None:
            simulation_results = self.run_multiple_simulations(include_post_promo=include_post_promo)
        
        if objective == 'profit':
            if 'net_profit_change' in simulation_results.columns and include_post_promo:
                best_idx = simulation_results['net_profit_change'].idxmax()
            else:
                best_idx = simulation_results['profit_change'].idxmax()
        elif objective == 'revenue':
            best_idx = simulation_results['revenue_change'].idxmax()
        elif objective == 'roi':
            best_idx = simulation_results['roi'].idxmax()
        else:
            raise ValueError(f"Unknown objective: {objective}")
        
        best_promotion = simulation_results.iloc[best_idx]
        
        profit_col = 'net_profit_change' if include_post_promo and 'net_profit_change' in simulation_results.columns else 'profit_change'
        top_promotions = simulation_results.nlargest(5, profit_col)
        
        return {
            'best_promotion': best_promotion.to_dict(),
            'objective': objective,
            'top_5_promotions': top_promotions[
                ['strategy', 'discount_pct', 'duration_days', profit_col, 'roi', 'sales_lift_pct']
            ].to_dict('records'),
            'all_results': simulation_results
        }
    
    def analyze_promotion_strategies(
        self,
        simulation_results: Optional[pd.DataFrame] = None,
        include_post_promo: bool = True
    ) -> Dict:
        if simulation_results is None:
            simulation_results = self.run_multiple_simulations(include_post_promo=include_post_promo)
        
        profit_col = 'net_profit_change' if include_post_promo and 'net_profit_change' in simulation_results.columns else 'profit_change'
        
        strategy_analysis = simulation_results.groupby('strategy').agg({
            profit_col: ['mean', 'max', 'min'],
            'revenue_change': ['mean', 'max'],
            'sales_lift_pct': ['mean', 'max'],
            'roi': ['mean', 'max'],
            'post_promo_loss': ['mean', 'max']
        }).round(2)
        
        strategy_analysis.columns = ['_'.join(col).strip() for col in strategy_analysis.columns.values]
        strategy_analysis = strategy_analysis.reset_index()
        
        discount_analysis = simulation_results.groupby('discount_pct').agg({
            profit_col: 'mean',
            'revenue_change': 'mean',
            'sales_lift_pct': 'mean',
            'roi': 'mean',
            'post_promo_loss': 'mean'
        }).reset_index()
        
        duration_analysis = simulation_results.groupby('duration_days').agg({
            profit_col: 'mean',
            'revenue_change': 'mean',
            'sales_lift_pct': 'mean',
            'post_promo_loss': 'mean'
        }).reset_index()
        
        optimal_profit = self.find_optimal_promotion(simulation_results, 'profit', include_post_promo)
        optimal_roi = self.find_optimal_promotion(simulation_results, 'roi', include_post_promo)
        
        return {
            'strategy_comparison': strategy_analysis,
            'discount_analysis': discount_analysis,
            'duration_analysis': duration_analysis,
            'best_by_profit': optimal_profit['best_promotion'],
            'best_by_roi': optimal_roi['best_promotion'],
            'recommendations': self._generate_promotion_recommendations(strategy_analysis, profit_col)
        }
    
    def _generate_promotion_recommendations(
        self,
        strategy_analysis: pd.DataFrame,
        profit_col: str
    ) -> List[Dict]:
        recommendations = []
        
        profit_mean_col = f'{profit_col}_mean'
        
        best_strategy_profit = strategy_analysis.loc[
            strategy_analysis[profit_mean_col].idxmax(),
            'strategy'
        ]
        best_strategy_roi = strategy_analysis.loc[
            strategy_analysis['roi_mean'].idxmax(),
            'strategy'
        ]
        
        strategy_names = {
            'direct_discount': '直接折扣',
            'buy_one_get_one': '买一送一',
            'bundle': '捆绑销售',
            'coupon': '优惠券'
        }
        
        recommendations.append({
            'priority': '高',
            'type': '净利润最大化策略',
            'recommendation': f"推荐使用【{strategy_names.get(best_strategy_profit, best_strategy_profit)}】策略，考虑延后效应后可获得最高净利润增长。",
            'expected_impact': f"平均净利润增长: ¥{strategy_analysis[profit_mean_col].max():,.0f}"
        })
        
        recommendations.append({
            'priority': '高',
            'type': 'ROI最优策略',
            'recommendation': f"从投资回报角度，推荐【{strategy_names.get(best_strategy_roi, best_strategy_roi)}】策略。",
            'expected_impact': f"平均ROI: {strategy_analysis['roi_mean'].max():.2f}"
        })
        
        post_promo_mean = strategy_analysis['post_promo_loss_mean'].max()
        if post_promo_mean > 100:
            recommendations.append({
                'priority': '中',
                'type': '延后效应提示',
                'recommendation': f"促销延后效应显著（平均损失 ¥{post_promo_mean:,.0f}），建议适当缩短促销周期或采用阶梯折扣策略。",
                'expected_impact': "可减少20%-30%的延后需求损失"
            })
        
        for _, row in strategy_analysis.iterrows():
            strategy = row['strategy']
            if row[profit_mean_col] < 0:
                recommendations.append({
                    'priority': '低',
                    'type': '谨慎策略',
                    'recommendation': f"【{strategy_names.get(strategy, strategy)}】策略平均净利润为负，建议谨慎使用或调整参数。",
                    'expected_impact': f"平均净利润变化: ¥{row[profit_mean_col]:,.0f}"
                })
        
        return recommendations
    
    def simulate_promotion_timeline(
        self,
        discount_pct: float,
        duration_days: int,
        pre_promo_days: int = 7,
        post_promo_days: int = 21,
        advertising_spend: float = 50.0,
        strategy: str = 'direct_discount'
    ) -> pd.DataFrame:
        total_days = pre_promo_days + duration_days + post_promo_days
        timeline = []
        
        for day in range(total_days):
            if day < pre_promo_days:
                period = '促销前'
                is_promo = False
                price = self.base_price
                ad_spend = advertising_spend * 0.3
                demand_factor = 1.0
                stockpiling_factor = 1.0
                post_promo_lags = {}
            elif day < pre_promo_days + duration_days:
                period = '促销中'
                is_promo = True
                price = self.base_price * (1 - discount_pct)
                ad_spend = advertising_spend
                day_in_promo = day - pre_promo_days
                demand_factor = 1.0 + 0.3 * np.sin(np.pi * (day_in_promo) / max(1, duration_days - 1))
                stockpiling_factor = self._get_stockpiling_adjustment(
                    day_in_promo, duration_days, discount_pct
                )
                post_promo_lags = {}
            else:
                period = '促销后'
                is_promo = False
                price = self.base_price
                ad_spend = advertising_spend * 0.1
                days_after = day - pre_promo_days - duration_days
                demand_factor = self._get_post_promo_decay_factor(days_after)
                
                post_promo_lags = {}
                for lag in range(1, self.model.promo_lag_days + 1):
                    if days_after >= lag:
                        post_promo_lags[lag] = 1
                
                stockpiling_correction = 1 - self.stockpiling_factor * (discount_pct / 0.2) * np.exp(-days_after / 7)
                demand_factor = min(demand_factor, stockpiling_correction)
                stockpiling_factor = 1.0
            
            daily_demand = self._predict_demand(
                price=price,
                is_promotion=is_promo,
                advertising_spend=ad_spend,
                post_promo_lags=post_promo_lags
            ) * demand_factor * stockpiling_factor
            
            if strategy == 'buy_one_get_one' and period == '促销中':
                daily_demand *= 1.5
            elif strategy == 'bundle' and period == '促销中':
                daily_demand *= 1.2
            elif strategy == 'coupon' and period == '促销中':
                daily_demand *= 0.9
            
            effective_price = price
            if strategy == 'buy_one_get_one' and period == '促销中':
                effective_price = price * 0.5
            elif strategy == 'bundle' and period == '促销中':
                effective_price = price * 0.8
            
            daily_revenue = daily_demand * effective_price
            daily_cost = daily_demand * self.variable_cost + ad_spend
            daily_profit = daily_revenue - daily_cost
            
            normal_daily_demand = self._predict_demand(
                price=self.base_price,
                is_promotion=False
            )
            normal_daily_revenue = normal_daily_demand * self.base_price
            normal_daily_profit = normal_daily_revenue - normal_daily_demand * self.variable_cost
            
            timeline.append({
                'day': day + 1,
                'period': period,
                'price': price,
                'effective_price': effective_price,
                'advertising_spend': ad_spend,
                'demand': daily_demand,
                'demand_vs_normal': daily_demand / normal_daily_demand if normal_daily_demand > 0 else 0,
                'revenue': daily_revenue,
                'cost': daily_cost,
                'profit': daily_profit,
                'normal_demand': normal_daily_demand,
                'normal_revenue': normal_daily_revenue,
                'normal_profit': normal_daily_profit,
                'demand_lift_vs_normal': daily_demand - normal_daily_demand,
                'revenue_lift_vs_normal': daily_revenue - normal_daily_revenue,
                'profit_lift_vs_normal': daily_profit - normal_daily_profit
            })
        
        return pd.DataFrame(timeline).round(2)
    
    def calculate_promotion_thresholds(
        self,
        include_post_promo: bool = True
    ) -> Dict:
        discounts = np.linspace(0.01, 0.50, 100)
        
        breakeven_discount = None
        optimal_discount = None
        max_profit = -np.inf
        
        profit_col = 'net_profit_change' if include_post_promo else 'profit_change'
        
        for d in discounts:
            result = self.simulate_promotion(
                discount_pct=d,
                duration_days=7,
                advertising_spend=50.0,
                include_post_promo=include_post_promo
            )
            profit = result[profit_col]
            if breakeven_discount is None and profit > 0:
                breakeven_discount = d
            if profit > max_profit:
                max_profit = profit
                optimal_discount = d
        
        post_promo_analysis = None
        if include_post_promo:
            post_promo_analysis = self._analyze_post_promo_sensitivity()
        
        return {
            'min_effective_discount_pct': breakeven_discount * 100 if breakeven_discount else None,
            'optimal_discount_pct': optimal_discount * 100 if optimal_discount else None,
            'max_expected_profit': max_profit,
            'recommended_discount_range_pct': (
                breakeven_discount * 100 if breakeven_discount else 5,
                min(optimal_discount * 1.5 * 100 if optimal_discount else 40, 50)
            ),
            'post_promo_analysis': post_promo_analysis
        }
    
    def _analyze_post_promo_sensitivity(self) -> Dict:
        durations = [3, 7, 14, 21, 30]
        discounts = [0.10, 0.20, 0.30]
        
        results = []
        
        for duration in durations:
            for discount in discounts:
                result = self.simulate_promotion(
                    discount_pct=discount,
                    duration_days=duration,
                    include_post_promo=True
                )
                results.append({
                    'duration': duration,
                    'discount': discount,
                    'gross_profit': result['profit_change'],
                    'post_promo_loss': result['post_promo_loss'],
                    'net_profit': result['net_profit_change'],
                    'loss_ratio': result['post_promo_loss'] / abs(result['profit_change']) if result['profit_change'] != 0 else 0
                })
        
        df = pd.DataFrame(results)
        
        optimal_duration = df.loc[df['net_profit'].idxmax(), 'duration']
        optimal_discount = df.loc[df['net_profit'].idxmax(), 'discount']
        
        return {
            'sensitivity_data': df,
            'optimal_duration': optimal_duration,
            'optimal_discount': optimal_discount,
            'recommendation': f"考虑延后效应，推荐促销周期 {optimal_duration} 天，折扣 {optimal_discount*100:.0f}%"
        }
