import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta
import holidays

from airline_events import get_event_features, AIRLINE_SPECIFIC_DATES, SEASONAL_EVENTS
from oil_futures import generate_historical_oil_futures, predict_oil_price_for_date

def create_enhanced_data():
    print('正在创建增强版测试数据（含航司活动和油价期货特征）...')
    
    routes = [
        ('北京', '上海'), ('北京', '广州'), ('上海', '深圳'), 
        ('北京', '成都'), ('上海', '广州'), ('深圳', '成都')
    ]
    
    airlines = list(AIRLINE_SPECIFIC_DATES.keys())
    
    data = []
    start_date = pd.to_datetime('2024-01-01')
    end_date = pd.to_datetime('2025-06-30')
    
    cn_holidays = holidays.CN(years=range(2024, 2026))
    
    route_base = {
        ('北京', '上海'): 600,
        ('北京', '广州'): 900,
        ('上海', '深圳'): 700,
        ('北京', '成都'): 1000,
        ('上海', '广州'): 800,
        ('深圳', '成都'): 950
    }
    
    route_distance = {
        ('北京', '上海'): 'short_haul',
        ('北京', '广州'): 'long_haul',
        ('上海', '深圳'): 'medium_haul',
        ('北京', '成都'): 'long_haul',
        ('上海', '广州'): 'medium_haul',
        ('深圳', '成都'): 'medium_haul'
    }
    
    print('生成油价历史数据...')
    oil_futures_data = generate_historical_oil_futures(start_date, end_date)
    daily_oil = oil_futures_data.groupby('trade_date').first()['spot_price'].to_dict()
    
    print('生成票价数据...')
    for _ in range(25000):
        route = random.choice(routes)
        origin, dest = route
        airline = random.choice(airlines)
        
        days_offset = random.randint(0, (end_date - start_date).days)
        departure_date = start_date + pd.DateOffset(days=days_offset)
        
        booking_days = random.randint(1, 90)
        search_date = departure_date - pd.DateOffset(days=booking_days)
        
        if search_date < start_date:
            continue
        
        base_price = route_base[route]
        distance = route_distance[route]
        
        search_date_str = search_date.strftime('%Y-%m-%d')
        oil_price = daily_oil.get(pd.Timestamp(search_date_str), 80)
        
        oil_futures_price, oil_volatility = predict_oil_price_for_date(departure_date, search_date)
        
        fuel_surcharge = 0
        if distance == 'short_haul':
            fuel_surcharge = 50 + max(0, (oil_price - 80) / 80) * 80
        elif distance == 'medium_haul':
            fuel_surcharge = 80 + max(0, (oil_price - 80) / 80) * 120
        else:
            fuel_surcharge = 150 + max(0, (oil_price - 80) / 80) * 200
        
        event_features = get_event_features(search_date, airline)
        event_impact = event_features['event_impact']
        is_promotion = event_features['is_promotion']
        discount_amount = event_features['discount_amount']
        
        seasonal_effect = event_features['seasonal_effect']
        
        holiday_factor = 1.0
        if departure_date in cn_holidays:
            holiday_factor = 1.4
        elif departure_date.weekday() >= 5:
            holiday_factor = 1.15
        
        month = departure_date.month
        season_factor = 1.0
        if month in [1, 2, 7, 8]:
            season_factor = 1.25
        elif month in [4, 5, 9, 10]:
            season_factor = 1.1
        
        booking_factor = 1.0
        if booking_days <= 7:
            booking_factor = 1.45
        elif booking_days <= 14:
            booking_factor = 1.2
        elif booking_days <= 30:
            booking_factor = 1.0
        elif booking_days <= 60:
            booking_factor = 0.88
        else:
            booking_factor = 0.82
        
        price = (base_price + fuel_surcharge) * booking_factor * season_factor * holiday_factor * event_impact
        price = price * np.random.normal(1, 0.12)
        price = max(150, round(price, 0))
        
        is_holiday_val = 1 if departure_date in cn_holidays else (0.5 if departure_date.weekday() >= 5 else 0)
        
        data.append({
            'origin': origin,
            'destination': dest,
            'route': f'{origin}-{dest}',
            'airline': airline,
            'departure_date': departure_date,
            'search_date': search_date,
            'booking_days': booking_days,
            'oil_price': oil_price,
            'oil_futures_price': oil_futures_price,
            'oil_volatility': oil_volatility,
            'fuel_surcharge': round(fuel_surcharge, 2),
            'is_holiday': is_holiday_val,
            'is_promotion': is_promotion,
            'discount_amount': discount_amount,
            'event_impact': event_impact,
            'seasonal_effect': seasonal_effect,
            'month': month,
            'day_of_week': departure_date.weekday(),
            'price': price
        })
    
    df = pd.DataFrame(data)
    df.to_csv('historical_data.csv', index=False, encoding='utf-8-sig')
    print(f'成功创建 {len(df)} 条增强数据')
    print(f'新增特征: 航司、油价期货、燃油附加费、促销活动、事件影响')
    return df

def train_enhanced_models(df):
    print('\n正在训练增强版模型...')
    
    from model_training import AirlinePriceModel
    
    model = AirlinePriceModel()
    
    print('训练XGBoost模型（含新特征）...')
    model.train_xgboost(df)
    
    print('训练Prophet时间序列模型...')
    model.train_prophet(df)
    
    model.save_models()
    print('增强版模型训练完成并保存!')
    return model

def test_enhanced_prediction(model):
    print('\n正在测试增强版预测功能...')
    
    from prediction import generate_booking_advice
    from risk_model import generate_risk_report
    
    try:
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        result = generate_booking_advice('北京-上海', future_date, model)
        print(f"航线: {result['route']}")
        print(f"出发日期: {result['departure_date'].strftime('%Y-%m-%d')}")
        print(f"购票建议: {result['best_time']['recommendation']}")
        print(f"当前预测价格: ¥{result['best_time']['current_price']:.0f}")
        print(f"最佳预测价格: ¥{result['best_time']['best_price']:.0f}")
        
        if len(result['price_predictions']) > 3:
            risk_report = generate_risk_report(result['price_predictions'], result['departure_date'])
            if risk_report:
                print(f"\n风险分析:")
                print(f"  风险等级: {risk_report['risk_assessment']['risk_level']}")
                print(f"  95% VaR: {risk_report['risk_assessment']['var_95']:.2f}%")
                print(f"  风险收益比: {risk_report['risk_assessment']['risk_reward_ratio']:.2f}")
        
        print('增强版预测测试成功!')
        return True
    except Exception as e:
        print(f'预测测试失败: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('=' * 60)
    print('航空票价预测系统 v2.0 - 增强版初始化脚本')
    print('=' * 60)
    print('新增功能:')
    print('  • 航司特有活动日历特征')
    print('  • 风险价值(VaR)模型')
    print('  • 油价期货曲线预测')
    print('=' * 60)
    
    try:
        df = create_enhanced_data()
        model = train_enhanced_models(df)
        success = test_enhanced_prediction(model)
        
        if success:
            print('\n' + '=' * 60)
            print('✅ 增强版系统初始化成功!')
            print('现在可以运行: streamlit run app.py')
            print('=' * 60)
        else:
            print('\n❌ 系统初始化部分失败，请检查错误信息')
    except Exception as e:
        print(f'\n❌ 初始化失败: {e}')
        import traceback
        traceback.print_exc()
