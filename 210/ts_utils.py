import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import STL
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf


def remove_seasonality_stl(series, period=5, seasonal=7, robust=True):
    series_clean = series.dropna()
    series_freq = series_clean.asfreq('B')
    series_interp = series_freq.interpolate(method='time')
    
    try:
        stl = STL(series_interp, period=period, seasonal=seasonal, robust=robust)
        result = stl.fit()
        trend_resid = result.trend + result.resid
        return trend_resid
    except Exception as e:
        print(f"STL分解失败: {e}，使用原始序列")
        return series_clean


def adf_test(series, significance_level=0.05, remove_seasonality=True, stl_period=5):
    series_clean = series.dropna()
    
    if remove_seasonality and len(series_clean) >= 2 * stl_period:
        series_for_test = remove_seasonality_stl(series_clean, period=stl_period)
    else:
        series_for_test = series_clean
    
    result = adfuller(series_for_test, autolag='AIC')
    adf_statistic = result[0]
    p_value = result[1]
    critical_values = result[4]
    
    is_stationary = p_value < significance_level
    
    return {
        'adf_statistic': adf_statistic,
        'p_value': p_value,
        'critical_values': critical_values,
        'is_stationary': is_stationary,
        'seasonality_removed': remove_seasonality
    }


def find_optimal_d(series, max_d=3, significance_level=0.05, remove_seasonality=True, stl_period=5):
    d = 0
    current_series = series.copy()
    
    while d <= max_d:
        test_result = adf_test(
            current_series, 
            significance_level,
            remove_seasonality=remove_seasonality,
            stl_period=stl_period
        )
        if test_result['is_stationary']:
            return d, test_result
        
        d += 1
        current_series = current_series.diff().dropna()
    
    return max_d, adf_test(
        current_series, 
        significance_level,
        remove_seasonality=remove_seasonality,
        stl_period=stl_period
    )


def find_optimal_pq(series, d, max_p=5, max_q=5):
    best_aic = float('inf')
    best_bic = float('inf')
    best_order = None
    
    series_diff = series.copy()
    for _ in range(d):
        series_diff = series_diff.diff().dropna()
    
    for p in range(max_p + 1):
        for q in range(max_q + 1):
            try:
                model = ARIMA(series, order=(p, d, q))
                results = model.fit()
                
                if results.aic < best_aic:
                    best_aic = results.aic
                    best_bic = results.bic
                    best_order = (p, d, q)
            except:
                continue
    
    return best_order, best_aic, best_bic


def auto_arima_order_selection(series, max_p=5, max_d=3, max_q=5, 
                                remove_seasonality=True, stl_period=5):
    d, _ = find_optimal_d(
        series, 
        max_d=max_d,
        remove_seasonality=remove_seasonality,
        stl_period=stl_period
    )
    order, aic, bic = find_optimal_pq(series, d, max_p=max_p, max_q=max_q)
    
    return {
        'order': order,
        'd': d,
        'aic': aic,
        'bic': bic
    }
