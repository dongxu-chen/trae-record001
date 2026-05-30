import numpy as np
from scipy.optimize import minimize


class PricingOptimizer:
    def __init__(self, our_cost, competitor_prices, price_elasticity=-1.5):
        self.our_cost = our_cost
        self.competitor_prices = np.array(competitor_prices)
        self.avg_competitor_price = np.mean(competitor_prices) if len(competitor_prices) > 0 else our_cost * 1.5
        self.min_competitor_price = np.min(competitor_prices) if len(competitor_prices) > 0 else our_cost
        self.max_competitor_price = np.max(competitor_prices) if len(competitor_prices) > 0 else our_cost * 2
        self.elasticity = price_elasticity

    def demand_model(self, price, base_demand=1000):
        relative_price = price / self.avg_competitor_price
        demand = base_demand * (relative_price ** self.elasticity)
        return max(demand, 0)

    def profit_function(self, price):
        demand = self.demand_model(price)
        profit = (price - self.our_cost) * demand
        return profit

    def revenue_function(self, price):
        demand = self.demand_model(price)
        return price * demand

    def market_share_model(self, price):
        all_prices = np.append(self.competitor_prices, price)
        attractiveness = 1.0 / all_prices
        our_attractiveness = 1.0 / price
        market_share = our_attractiveness / attractiveness.sum()
        return market_share

    def optimize_for_profit(self, price_range=None):
        if price_range is None:
            price_range = (self.our_cost * 1.01, self.max_competitor_price * 1.3)
        result = minimize(
            lambda p: -self.profit_function(p[0]),
            x0=[self.avg_competitor_price],
            bounds=[price_range],
            method='L-BFGS-B',
        )
        optimal_price = result.x[0]
        demand = self.demand_model(optimal_price)
        profit = self.profit_function(optimal_price)
        revenue = self.revenue_function(optimal_price)
        margin = (optimal_price - self.our_cost) / optimal_price * 100
        return {
            'objective': '利润最大化',
            'optimal_price': round(optimal_price, 2),
            'expected_demand': round(demand, 0),
            'expected_profit': round(profit, 2),
            'expected_revenue': round(revenue, 2),
            'profit_margin': round(margin, 2),
            'market_share': round(self.market_share_model(optimal_price) * 100, 2),
        }

    def optimize_for_revenue(self, price_range=None):
        if price_range is None:
            price_range = (self.our_cost * 1.01, self.max_competitor_price * 1.3)
        result = minimize(
            lambda p: -self.revenue_function(p[0]),
            x0=[self.avg_competitor_price],
            bounds=[price_range],
            method='L-BFGS-B',
        )
        optimal_price = result.x[0]
        demand = self.demand_model(optimal_price)
        profit = self.profit_function(optimal_price)
        revenue = self.revenue_function(optimal_price)
        margin = (optimal_price - self.our_cost) / optimal_price * 100
        return {
            'objective': '营收最大化',
            'optimal_price': round(optimal_price, 2),
            'expected_demand': round(demand, 0),
            'expected_profit': round(profit, 2),
            'expected_revenue': round(revenue, 2),
            'profit_margin': round(margin, 2),
            'market_share': round(self.market_share_model(optimal_price) * 100, 2),
        }

    def optimize_for_market_share(self, price_range=None):
        if price_range is None:
            price_range = (self.our_cost * 1.01, self.max_competitor_price * 1.3)
        result = minimize(
            lambda p: -self.market_share_model(p[0]),
            x0=[self.min_competitor_price],
            bounds=[price_range],
            method='L-BFGS-B',
        )
        optimal_price = result.x[0]
        demand = self.demand_model(optimal_price)
        profit = self.profit_function(optimal_price)
        revenue = self.revenue_function(optimal_price)
        margin = (optimal_price - self.our_cost) / optimal_price * 100
        return {
            'objective': '市场份额最大化',
            'optimal_price': round(optimal_price, 2),
            'expected_demand': round(demand, 0),
            'expected_profit': round(profit, 2),
            'expected_revenue': round(revenue, 2),
            'profit_margin': round(margin, 2),
            'market_share': round(self.market_share_model(optimal_price) * 100, 2),
        }

    def simulate_price_range(self, prices=None):
        if prices is None:
            low = max(self.our_cost * 1.01, self.min_competitor_price * 0.7)
            high = self.max_competitor_price * 1.3
            prices = np.linspace(low, high, 50)
        results = []
        for p in prices:
            demand = self.demand_model(p)
            profit = self.profit_function(p)
            revenue = self.revenue_function(p)
            margin = (p - self.our_cost) / p * 100 if p > 0 else 0
            ms = self.market_share_model(p) * 100
            results.append({
                'price': round(p, 2),
                'demand': round(demand, 0),
                'profit': round(profit, 2),
                'revenue': round(revenue, 2),
                'margin_pct': round(margin, 2),
                'market_share_pct': round(ms, 2),
                'price_index': round(p / self.avg_competitor_price * 100, 2),
            })
        return results

    def multi_objective_optimization(self, weights=None):
        if weights is None:
            weights = {'profit': 0.4, 'revenue': 0.3, 'market_share': 0.3}
        price_range = (self.our_cost * 1.01, self.max_competitor_price * 1.3)
        max_profit = self.profit_function(self.optimize_for_profit()['optimal_price'])
        max_revenue = self.revenue_function(self.optimize_for_revenue()['optimal_price'])
        max_ms = self.market_share_model(self.optimize_for_market_share()['optimal_price'])

        def combined_objective(p):
            norm_profit = self.profit_function(p[0]) / max_profit if max_profit > 0 else 0
            norm_revenue = self.revenue_function(p[0]) / max_revenue if max_revenue > 0 else 0
            norm_ms = self.market_share_model(p[0]) / max_ms if max_ms > 0 else 0
            score = weights['profit'] * norm_profit + weights['revenue'] * norm_revenue + weights['market_share'] * norm_ms
            return -score

        result = minimize(
            combined_objective,
            x0=[self.avg_competitor_price],
            bounds=[price_range],
            method='L-BFGS-B',
        )
        optimal_price = result.x[0]
        return {
            'objective': '多目标优化',
            'optimal_price': round(optimal_price, 2),
            'expected_demand': round(self.demand_model(optimal_price), 0),
            'expected_profit': round(self.profit_function(optimal_price), 2),
            'expected_revenue': round(self.revenue_function(optimal_price), 2),
            'profit_margin': round((optimal_price - self.our_cost) / optimal_price * 100, 2),
            'market_share': round(self.market_share_model(optimal_price) * 100, 2),
            'weights': weights,
            'combined_score': round(-result.fun, 4),
        }
