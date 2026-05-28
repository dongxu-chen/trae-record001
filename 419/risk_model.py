import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta

class ValueAtRisk:
    def __init__(self, confidence_level=0.95):
        self.confidence_level = confidence_level
        self.z_score = stats.norm.ppf(confidence_level)
    
    def calculate_var_historical(self, returns, holding_period=1):
        if returns is None or len(returns) < 10:
            return None
        
        returns = np.array(returns)
        var = np.percentile(returns, (1 - self.confidence_level) * 100)
        return abs(var * np.sqrt(holding_period))
    
    def calculate_var_parametric(self, mu, sigma, holding_period=1):
        var = (mu - self.z_score * sigma) * np.sqrt(holding_period)
        return abs(var)
    
    def calculate_var_monte_carlo(self, current_price, mu, sigma, n_simulations=10000, holding_period=1):
        simulations = np.random.normal(mu, sigma, n_simulations)
        var = np.percentile(simulations, (1 - self.confidence_level) * 100)
        return abs(var * current_price)

def simulate_price_paths(current_price, mu, sigma, n_days, n_simulations=1000):
    paths = np.zeros((n_simulations, n_days))
    paths[:, 0] = current_price
    
    for t in range(1, n_days):
        shocks = np.random.normal(mu, sigma, n_simulations)
        paths[:, t] = paths[:, t-1] * (1 + shocks)
    
    return paths

def calculate_waiting_risk(price_predictions, volatility=0.03):
    if price_predictions is None or len(price_predictions) < 2:
        return None
    
    prices = price_predictions['predicted_price'].values
    returns = np.diff(prices) / prices[:-1]
    
    if returns is None or len(returns) < 5:
        returns = np.array([0.02, -0.01, 0.03, -0.02, 0.01])
    
    mu = np.mean(returns)
    sigma = np.std(returns) if np.std(returns) > 0 else volatility
    
    var_95 = np.percentile(returns, 5) * 100
    var_99 = np.percentile(returns, 1) * 100
    
    expected_shortfall_95 = np.mean(returns[returns <= np.percentile(returns, 5)]) * 100
    
    current_price = prices[0]
    best_price = np.min(prices)
    worst_price = np.max(prices)
    
    potential_gain = ((current_price - best_price) / current_price) * 100
    potential_loss = ((worst_price - current_price) / current_price) * 100
    
    sharpe = (mu / sigma) * np.sqrt(252) if sigma > 0 else 0
    
    return {
        'daily_volatility': sigma * 100,
        'var_95': abs(var_95),
        'var_99': abs(var_99),
        'expected_shortfall_95': abs(expected_shortfall_95),
        'potential_gain_percent': potential_gain,
        'potential_loss_percent': potential_loss,
        'sharpe_ratio': sharpe,
        'risk_reward_ratio': potential_gain / abs(var_95) if var_95 != 0 else 0
    }

def generate_risk_assessment(price_predictions, oil_volatility=0.025):
    risk_metrics = calculate_waiting_risk(price_predictions, oil_volatility)
    
    if risk_metrics is None:
        return None
    
    var_95 = risk_metrics['var_95']
    potential_gain = risk_metrics['potential_gain_percent']
    risk_reward = risk_metrics['risk_reward_ratio']
    
    if risk_reward > 2 and var_95 < 3:
        risk_level = '低风险'
        recommendation = '强烈建议等待'
    elif risk_reward > 1.5 and var_95 < 5:
        risk_level = '中低风险'
        recommendation = '可以等待'
    elif risk_reward > 1 and var_95 < 7:
        risk_level = '中等风险'
        recommendation = '谨慎等待'
    elif risk_reward > 0.5:
        risk_level = '中高风险'
        recommendation = '考虑立即购买'
    else:
        risk_level = '高风险'
        recommendation = '建议立即购买'
    
    best_wait_days = find_best_wait_period(price_predictions)
    
    return {
        **risk_metrics,
        'risk_level': risk_level,
        'recommendation': recommendation,
        'best_wait_days': best_wait_days
    }

def find_best_wait_period(price_predictions):
    if price_predictions is None or len(price_predictions) < 5:
        return {'start': 0, 'end': 0, 'reason': '数据不足'}
    
    prices = price_predictions['predicted_price'].values
    min_idx = np.argmin(prices)
    
    if min_idx == 0:
        return {'start': 0, 'end': 0, 'reason': '当前已是最佳'}
    elif min_idx == len(prices) - 1:
        return {'start': len(prices) - 1, 'end': len(prices) - 1, 'reason': '最后一天最佳'}
    
    window_start = max(0, min_idx - 3)
    window_end = min(len(prices) - 1, min_idx + 2)
    
    return {
        'start': window_start,
        'end': window_end,
        'best_day': min_idx,
        'reason': f'最佳购买窗口为第{window_start}到{window_end}天'
    }

def monte_carlo_simulation(current_price, days_to_departure, n_simulations=5000):
    mu = 0.0002
    sigma = 0.015
    
    daily_prices = np.zeros((days_to_departure, n_simulations))
    daily_prices[0] = current_price
    
    for day in range(1, days_to_departure):
        returns = np.random.normal(mu, sigma, n_simulations)
        daily_prices[day] = daily_prices[day - 1] * (1 + returns)
    
    final_prices = daily_prices[-1]
    
    var_95 = np.percentile(final_prices, 5)
    var_99 = np.percentile(final_prices, 1)
    expected_shortfall = np.mean(final_prices[final_prices <= var_95])
    
    prob_lower = current_price * 0.9
    prob_higher = current_price * 1.1
    
    prob_price_lower = np.mean(final_prices < prob_lower)
    prob_price_higher = np.mean(final_prices > prob_higher)
    
    return {
        'simulation_results': daily_prices,
        'var_95': var_95,
        'var_99': var_99,
        'expected_shortfall': expected_shortfall,
        'prob_price_lower_10': prob_price_lower,
        'prob_price_higher_10': prob_price_higher,
        'mean_final_price': np.mean(final_prices),
        'median_final_price': np.median(final_prices)
    }

def calculate_optimal_hedging_ratio(price_volatility, oil_volatility, correlation=0.7):
    if oil_volatility == 0:
        return 0
    
    hedge_ratio = correlation * (price_volatility / oil_volatility)
    return min(max(hedge_ratio, 0), 1)

def generate_risk_report(price_predictions, departure_date, current_price=None):
    if price_predictions is None or len(price_predictions) < 3:
        return None
    
    if current_price is None:
        current_price = price_predictions['predicted_price'].iloc[0]
    
    risk_assessment = generate_risk_assessment(price_predictions)
    
    days_to_departure = len(price_predictions)
    
    mc_results = monte_carlo_simulation(current_price, days_to_departure)
    
    report = {
        'current_price': current_price,
        'risk_assessment': risk_assessment,
        'monte_carlo': mc_results,
        'summary': generate_risk_summary(risk_assessment, mc_results, current_price)
    }
    
    return report

def generate_risk_summary(risk_assessment, mc_results, current_price):
    var_95_price = current_price * (1 - risk_assessment['var_95'] / 100)
    var_99_price = current_price * (1 - risk_assessment['var_99'] / 100)
    
    gain_amount = current_price * risk_assessment['potential_gain_percent'] / 100
    loss_amount = current_price * risk_assessment['potential_loss_percent'] / 100
    
    summary = f"""
📊 **风险价值分析报告**

**风险指标:**
• 95% VaR: {risk_assessment['var_95']:.2f}% (¥{current_price - var_95_price:.0f})
• 99% VaR: {risk_assessment['var_99']:.2f}% (¥{current_price - var_99_price:.0f})
• 日波动率: {risk_assessment['daily_volatility']:.2f}%
• 夏普比率: {risk_assessment['sharpe_ratio']:.2f}

**潜在收益/损失:**
• 预期最大收益: ¥{gain_amount:.0f} ({risk_assessment['potential_gain_percent']:.1f}%)
• 预期最大损失: ¥{loss_amount:.0f} ({risk_assessment['potential_loss_percent']:.1f}%)
• 风险收益比: {risk_assessment['risk_reward_ratio']:.2f}

**风险等级: {risk_assessment['risk_level']}
**建议: {risk_assessment['recommendation']}
"""
    
    return summary

if __name__ == '__main__':
    print('风险价值模型测试...')
    
    dates = pd.date_range('2025-06-01', periods=60, freq='D')
    base_price = 700
    prices = base_price * (1 + np.cumsum(np.random.normal(0.001, 0.02, 60)))
    
    test_df = pd.DataFrame({
        'search_date': dates,
        'predicted_price': prices,
        'price_lower': prices * 0.9,
        'price_upper': prices * 1.1
    })
    
    risk_report = generate_risk_report(test_df, '2025-08-01')
    
    print(f"风险等级: {risk_report['risk_assessment']['risk_level']}")
    print(f"建议: {risk_report['risk_assessment']['recommendation']}")
    print(f"95% VaR: {risk_report['risk_assessment']['var_95']:.2f}%")
    print(f"99% VaR: {risk_report['risk_assessment']['var_99']:.2f}%")
    print(f"风险收益比: {risk_report['risk_assessment']['risk_reward_ratio']:.2f}")
    print(f"夏普比率: {risk_report['risk_assessment']['sharpe_ratio']:.2f}")
