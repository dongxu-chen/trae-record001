import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.interpolate import interp1d

FUTURE_MONTHS = [1, 2, 3, 6, 12, 18, 24, 36]

def generate_historical_oil_futures(start_date='2024-01-01', end_date='2026-06-30'):
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    futures_data = []
    
    spot_price = 75.0
    historical_spot = []
    
    for _ in range(len(date_range)):
        change = np.random.normal(0, 1.2)
        spot_price = max(40, min(130, spot_price + change))
        historical_spot.append(spot_price)
    
    for i, trade_date in enumerate(date_range):
        spot = historical_spot[i]
        
        volatility = 0.02 + np.random.uniform(0, 0.03)
        trend = np.random.uniform(-0.001, 0.002)
        
        for months in FUTURE_MONTHS:
            t = months / 12.0
            
            futures_price = spot * np.exp((trend + 0.5 * volatility ** 2) * t + volatility * np.random.normal(0, np.sqrt(t)) * 0.3)
            
            futures_price = futures_price * (1 + np.random.uniform(-0.02, 0.02))
            
            futures_data.append({
                'trade_date': trade_date,
                'delivery_months': months,
                'delivery_date': trade_date + pd.DateOffset(months=months),
                'futures_price': futures_price,
                'spot_price': spot,
                'basis': futures_price - spot,
                'contango': futures_price > spot
            })
    
    df = pd.DataFrame(futures_data)
    return df

def get_current_futures_curve(current_date=None):
    if current_date is None:
        current_date = datetime.now()
    
    spot = 78.5 + np.random.uniform(-3, 3)
    volatility = 0.025
    
    curve_data = []
    
    for months in FUTURE_MONTHS:
        t = months / 12.0
        
        seasonal_adjustment = 1.0
        future_month = (current_date.month + months - 1) % 12 + 1
        if future_month in [7, 8]:
            seasonal_adjustment = 1.05
        elif future_month in [1, 2]:
            seasonal_adjustment = 1.03
        elif future_month in [3, 4, 10, 11]:
            seasonal_adjustment = 0.97
        
        futures_price = spot * np.exp(0.01 * t) * seasonal_adjustment
        futures_price = futures_price * (1 + np.random.uniform(-0.015, 0.015))
        
        curve_data.append({
            'months': months,
            'delivery_date': current_date + pd.DateOffset(months=months),
            'futures_price': futures_price,
            'spot_price': spot,
            'basis': futures_price - spot,
            'contango': futures_price > spot
        })
    
    return pd.DataFrame(curve_data)

def predict_oil_price_for_date(target_date, current_date=None):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(target_date, str):
        target_date = pd.to_datetime(target_date)
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
    
    months_diff = (target_date.year - current_date.year) * 12 + (target_date.month - current_date.month)
    
    curve = get_current_futures_curve(current_date)
    
    if months_diff <= 0:
        return curve.iloc[0]['spot_price'], 0.02
    elif months_diff >= 36:
        return curve.iloc[-1]['futures_price'], 0.08
    else:
        f = interp1d(curve['months'], curve['futures_price'], kind='cubic', fill_value='extrapolate')
        predicted_price = float(f(months_diff))
        
        vol_curve = interp1d(curve['months'], [0.02, 0.025, 0.03, 0.04, 0.055, 0.065, 0.07, 0.08], 
                            kind='linear', fill_value='extrapolate')
        volatility = float(vol_curve(months_diff))
        
        return predicted_price, volatility

def calculate_fuel_surcharge(oil_price, base_oil_price=80.0):
    surcharge_factor = max(0, (oil_price - base_oil_price) / base_oil_price)
    
    surcharge = {
        'short_haul': round(50 + surcharge_factor * 80, 2),
        'medium_haul': round(80 + surcharge_factor * 120, 2),
        'long_haul': round(150 + surcharge_factor * 200, 2)
    }
    
    return surcharge

def predict_fuel_surcharge_trend(departure_date, current_date=None, route_distance='medium_haul'):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    
    dates = []
    surcharges = []
    oil_prices = []
    
    for days in range(0, min(90, (departure_date - current_date).days + 1), 7):
        target_date = current_date + timedelta(days=days)
        oil_price, volatility = predict_oil_price_for_date(target_date, current_date)
        surcharge = calculate_fuel_surcharge(oil_price)
        
        dates.append(target_date)
        oil_prices.append(oil_price)
        surcharges.append(surcharge[route_distance])
    
    df = pd.DataFrame({
        'date': dates,
        'oil_price': oil_prices,
        'fuel_surcharge': surcharges
    })
    
    return df

def get_oil_market_analysis(current_date=None):
    if current_date is None:
        current_date = datetime.now()
    
    curve = get_current_futures_curve(current_date)
    
    front_month = curve.iloc[0]
    twelve_month = curve[curve['months'] == 12].iloc[0] if len(curve[curve['months'] == 12]) > 0 else curve.iloc[-1]
    
    market_state = 'contango' if front_month['futures_price'] < twelve_month['futures_price'] else 'backwardation'
    
    trend = '上涨' if twelve_month['futures_price'] > front_month['spot_price'] * 1.03 else ('下跌' if twelve_month['futures_price'] < front_month['spot_price'] * 0.97 else '平稳')
    
    analysis = {
        'current_spot': front_month['spot_price'],
        'front_month_future': front_month['futures_price'],
        'twelve_month_future': twelve_month['futures_price'],
        'market_state': market_state,
        'price_trend': trend,
        'expected_change_percent': ((twelve_month['futures_price'] - front_month['spot_price']) / front_month['spot_price']) * 100
    }
    
    return analysis

if __name__ == '__main__':
    print('生成油价期货曲线...')
    curve = get_current_futures_curve()
    print('当前期货曲线:')
    print(curve[['months', 'delivery_date', 'futures_price', 'basis', 'contango']])
    
    print('\n预测2025-08-15的油价:')
    price, vol = predict_oil_price_for_date('2025-08-15')
    print(f'预测油价: ${price:.2f}/桶, 波动率: {vol*100:.1f}%')
    
    print('\n燃油附加费:')
    surcharge = calculate_fuel_surcharge(price)
    print(f'短途: ¥{surcharge["short_haul"]}, 中途: ¥{surcharge["medium_haul"]}, 长途: ¥{surcharge["long_haul"]}')
    
    print('\n市场分析:')
    analysis = get_oil_market_analysis()
    for k, v in analysis.items():
        print(f'  {k}: {v}')
