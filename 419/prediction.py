import pandas as pd
import numpy as np
import holidays
from datetime import datetime, timedelta
from model_training import AirlinePriceModel
from airline_events import get_event_features, AIRLINE_SPECIFIC_DATES
from oil_futures import (
    predict_oil_price_for_date, 
    calculate_fuel_surcharge, 
    get_oil_market_analysis,
    predict_fuel_surcharge_trend,
    get_current_futures_curve
)
from risk_model import generate_risk_report, generate_risk_assessment
from multi_city import (
    recommend_multi_city_itineraries, 
    find_open_jaw_trip,
    get_airline_transfer_info,
    HUB_CITIES
)

ROUTE_DISTANCE = {
    '北京-上海': 'short_haul',
    '北京-广州': 'long_haul',
    '上海-深圳': 'medium_haul',
    '北京-成都': 'long_haul',
    '上海-广州': 'medium_haul',
    '深圳-成都': 'medium_haul'
}

def is_holiday(date):
    cn_holidays = holidays.CN(years=range(2024, 2028))
    if date in cn_holidays:
        return 1
    if date.weekday() >= 5:
        return 0.5
    return 0

def get_current_oil_price():
    curve = get_current_futures_curve()
    return curve.iloc[0]['spot_price']

def prepare_prediction_data_enhanced(route, departure_date, current_date=None, airline=None):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
    
    booking_days = (departure_date - current_date).days
    
    if booking_days < 0:
        raise ValueError('出发日期不能早于当前日期')
    
    origin, dest = route.split('-')
    
    oil_price, oil_volatility = predict_oil_price_for_date(departure_date, current_date)
    
    distance = ROUTE_DISTANCE.get(route, 'medium_haul')
    fuel_surcharge_dict = calculate_fuel_surcharge(oil_price)
    fuel_surcharge = fuel_surcharge_dict[distance]
    
    holiday_factor = is_holiday(departure_date)
    
    event_features = get_event_features(current_date, airline)
    is_promotion = event_features['is_promotion']
    discount_amount = event_features['discount_amount']
    event_impact = event_features['event_impact']
    seasonal_effect = event_features['seasonal_effect']
    
    data = {
        'origin': origin,
        'destination': dest,
        'route': route,
        'airline': airline if airline else '中国国航',
        'departure_date': departure_date,
        'search_date': current_date,
        'booking_days': booking_days,
        'oil_price': oil_price,
        'oil_futures_price': oil_price,
        'oil_volatility': oil_volatility,
        'fuel_surcharge': fuel_surcharge,
        'is_holiday': holiday_factor,
        'is_promotion': is_promotion,
        'discount_amount': discount_amount,
        'event_impact': event_impact,
        'seasonal_effect': seasonal_effect,
        'month': departure_date.month,
        'day_of_week': departure_date.weekday()
    }
    
    return pd.DataFrame([data])

def predict_future_prices_enhanced(model, route, departure_date, current_date=None, days_ahead=60, airline=None):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
    
    max_days = (departure_date - current_date).days
    if max_days < 0:
        raise ValueError('出发日期不能早于当前日期')
    
    predictions = []
    
    for days_offset in range(0, min(days_ahead, max_days + 1)):
        search_date = current_date + timedelta(days=days_offset)
        booking_days = (departure_date - search_date).days
        
        if booking_days < 0:
            break
        
        try:
            feature_data = prepare_prediction_data_enhanced(route, departure_date, search_date, airline)
            predicted_price = model.predict_with_xgboost(feature_data)[0]
            
            predictions.append({
                'search_date': search_date,
                'booking_days': booking_days,
                'predicted_price': predicted_price
            })
        except Exception as e:
            continue
    
    df = pd.DataFrame(predictions)
    
    if len(df) > 0:
        df['price_lower'] = df['predicted_price'] * 0.88
        df['price_upper'] = df['predicted_price'] * 1.12
    
    return df

def get_best_time_to_buy_enhanced(price_predictions_df, risk_assessment=None):
    if price_predictions_df is None or len(price_predictions_df) == 0:
        return None
    
    min_price_idx = price_predictions_df['predicted_price'].idxmin()
    best_row = price_predictions_df.loc[min_price_idx]
    
    current_price_row = price_predictions_df.iloc[0]
    current_price = current_price_row['predicted_price']
    best_price = best_row['predicted_price']
    
    price_drop_percent = ((current_price - best_price) / current_price) * 100
    
    risk_based_recommendation = None
    if risk_assessment:
        risk_based_recommendation = risk_assessment['recommendation']
    
    if risk_based_recommendation:
        recommendation = risk_based_recommendation
        if '强烈建议等待' in recommendation:
            urgency = '低'
        elif '可以等待' in recommendation or '谨慎等待' in recommendation:
            urgency = '中'
        else:
            urgency = '高'
    else:
        if price_drop_percent > 5 and best_row['booking_days'] >= 7:
            recommendation = '等待'
            urgency = '低'
        elif price_drop_percent > 2 and best_row['booking_days'] >= 3:
            recommendation = '可以等待'
            urgency = '中'
        elif best_row['booking_days'] <= 7:
            recommendation = '立即购买'
            urgency = '高'
        else:
            recommendation = '立即购买'
            urgency = '中'
    
    reason_parts = []
    if risk_assessment:
        reason_parts.append(f"风险等级: {risk_assessment['risk_level']}")
        reason_parts.append(f"风险收益比: {risk_assessment['risk_reward_ratio']:.2f}")
    
    if price_drop_percent > 0:
        reason_parts.append(f"最佳购买日: {best_row['search_date'].strftime('%Y-%m-%d')}")
        reason_parts.append(f"预计节省: {price_drop_percent:.1f}%")
    else:
        reason_parts.append("当前价格已处于低位")
    
    reason = ' | '.join(reason_parts)
    
    return {
        'best_date': best_row['search_date'],
        'best_price': best_price,
        'best_price_lower': best_row['price_lower'],
        'best_price_upper': best_row['price_upper'],
        'current_price': current_price,
        'current_price_lower': current_price_row['price_lower'],
        'current_price_upper': current_price_row['price_upper'],
        'recommendation': recommendation,
        'urgency': urgency,
        'reason': reason,
        'potential_savings': current_price - best_price,
        'potential_savings_percent': price_drop_percent
    }

def analyze_price_trend(price_predictions_df):
    if price_predictions_df is None or len(price_predictions_df) < 2:
        return {'trend': '无法判断', 'slope': 0}
    
    x = np.arange(len(price_predictions_df))
    y = price_predictions_df['predicted_price'].values
    
    slope, _ = np.polyfit(x, y, 1)
    
    if slope > 5:
        trend = '上涨趋势'
    elif slope < -5:
        trend = '下降趋势'
    else:
        trend = '平稳趋势'
    
    return {
        'trend': trend,
        'slope': slope,
        'daily_change': slope
    }

def generate_enhanced_booking_advice(route, departure_date, model, current_date=None, airline=None):
    if current_date is None:
        current_date = datetime.now()
    
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
    
    days_to_departure = (departure_date - current_date).days
    
    price_predictions = predict_future_prices_enhanced(model, route, departure_date, current_date, airline=airline)
    
    risk_report = None
    risk_assessment = None
    if len(price_predictions) >= 3:
        risk_report = generate_risk_report(price_predictions, departure_date)
        if risk_report:
            risk_assessment = risk_report['risk_assessment']
    
    best_time = get_best_time_to_buy_enhanced(price_predictions, risk_assessment)
    trend = analyze_price_trend(price_predictions)
    
    prophet_forecast = model.predict_with_prophet(periods=120)
    prophet_forecast = prophet_forecast[prophet_forecast['ds'] >= current_date]
    prophet_forecast = prophet_forecast[prophet_forecast['ds'] <= departure_date + timedelta(days=30)]
    
    oil_analysis = get_oil_market_analysis(current_date)
    fuel_trend = predict_fuel_surcharge_trend(departure_date, current_date)
    
    upcoming_events = []
    for airline_name, dates in AIRLINE_SPECIFIC_DATES.items():
        member_day = dates.get('member_day')
        if member_day:
            for days_ahead in range(0, min(60, days_to_departure)):
                check_date = current_date + timedelta(days=days_ahead)
                if check_date.day == member_day:
                    upcoming_events.append({
                        'airline': airline_name,
                        'event': '会员日',
                        'date': check_date,
                        'days_to_event': days_ahead
                    })
                    break
    
    return {
        'route': route,
        'departure_date': departure_date,
        'current_date': current_date,
        'days_to_departure': days_to_departure,
        'airline': airline,
        'price_predictions': price_predictions,
        'best_time': best_time,
        'trend': trend,
        'prophet_forecast': prophet_forecast,
        'risk_report': risk_report,
        'risk_assessment': risk_assessment,
        'oil_analysis': oil_analysis,
        'fuel_trend': fuel_trend,
        'upcoming_events': upcoming_events
    }

def predict_multi_city_itinerary(origin, destination, departure_date, model, 
                                 max_connections=2, top_n=5, airline=None):
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    
    itineraries = recommend_multi_city_itineraries(
        origin, destination, departure_date, model, max_connections, top_n, airline
    )
    
    for itinerary in itineraries:
        if 'transfer_city' in itinerary:
            transfer_info = get_airline_transfer_info(
                airline if airline else '中国国航', 
                itinerary['transfer_city']
            )
            itinerary['transfer_info'] = transfer_info
        
        if itinerary['transfer_count'] == 0:
            itinerary['savings_vs_direct'] = 0
        else:
            direct = next((i for i in itineraries if i['transfer_count'] == 0), None)
            if direct:
                itinerary['savings_vs_direct'] = round(
                    (direct['total_price'] - itinerary['total_price']) / direct['total_price'] * 100, 1
                )
    
    return itineraries

def predict_open_jaw(city1, city2, city3, date1, date2, model, airline=None):
    if isinstance(date1, str):
        date1 = pd.to_datetime(date1)
    if isinstance(date2, str):
        date2 = pd.to_datetime(date2)
    
    result = find_open_jaw_trip(city1, city2, city3, date1, date2, model, airline)
    
    seg1_price = None
    seg2_price = None
    try:
        seg1_feature = prepare_prediction_data_enhanced(f'{city1}-{city2}', date1, airline=airline)
        seg1_price = model.predict_with_xgboost(seg1_feature)[0]
    except:
        pass
    
    try:
        seg2_feature = prepare_prediction_data_enhanced(f'{city2}-{city3}', date2, airline=airline)
        seg2_price = model.predict_with_xgboost(seg2_feature)[0]
    except:
        pass
    
    if seg1_price and seg2_price:
        separate_price = seg1_price + seg2_price
        result['separate_booking_price'] = separate_price
        result['actual_savings'] = round(separate_price - result['total_price'], 0)
        result['savings_percent'] = round(result['actual_savings'] / separate_price * 100, 1)
    
    return result

def compare_direct_vs_connecting(origin, destination, departure_date, model, airline=None):
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    
    itineraries = recommend_multi_city_itineraries(
        origin, destination, departure_date, model, 
        max_connections=1, top_n=10, airline=airline
    )
    
    direct_flight = next((i for i in itineraries if i['transfer_count'] == 0), None)
    connecting_flights = [i for i in itineraries if i['transfer_count'] > 0]
    
    comparison = {
        'direct_flight': direct_flight,
        'connecting_flights': connecting_flights,
        'best_connecting': min(connecting_flights, key=lambda x: x['total_price']) if connecting_flights else None
    }
    
    if direct_flight and comparison['best_connecting']:
        price_diff = direct_flight['total_price'] - comparison['best_connecting']['total_price']
        time_diff = comparison['best_connecting']['estimated_duration'] - direct_flight['estimated_duration']
        
        comparison['trade_off'] = {
            'price_savings': price_diff,
            'price_savings_percent': round(price_diff / direct_flight['total_price'] * 100, 1),
            'additional_time': time_diff,
            'price_per_hour_saved': round(price_diff / time_diff, 0) if time_diff > 0 else 0
        }
    
    return comparison

def predict_price_range(feature_data, model, confidence=0.95):
    base_prediction = model.predict_with_xgboost(feature_data)[0]
    
    volatility = 0.15
    z_score = 1.96 if confidence == 0.95 else 2.58
    
    lower_bound = base_prediction * (1 - volatility * z_score / 2)
    upper_bound = base_prediction * (1 + volatility * z_score / 2)
    
    return lower_bound, upper_bound

def generate_price_path(mean_price, days, n_paths=1000, volatility=0.15):
    dt = 1 / 365
    sigma = volatility * np.sqrt(days / 365)
    
    paths = []
    for _ in range(n_paths):
        path = [mean_price]
        for _ in range(days):
            shock = np.random.normal(0, sigma / np.sqrt(days))
            next_price = path[-1] * (1 + shock)
            path.append(max(next_price, mean_price * 0.5))
        paths.append(path)
    
    return np.array(paths)

if __name__ == '__main__':
    model = AirlinePriceModel()
    try:
        model.load_models()
        route = '北京-上海'
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        result = generate_enhanced_booking_advice(route, future_date, model, airline='中国国航')
        print(f"航线: {result['route']}")
        print(f"出发日期: {result['departure_date'].strftime('%Y-%m-%d')}")
        print(f"距离出发: {result['days_to_departure']} 天")
        print(f"\n购票建议: {result['best_time']['recommendation']}")
        print(f"紧急程度: {result['best_time']['urgency']}")
        print(f"建议原因: {result['best_time']['reason']}")
        print(f"\n当前预测价格: ¥{result['best_time']['current_price']:.0f}")
        print(f"最佳预测价格: ¥{result['best_time']['best_price']:.0f}")
        print(f"价格趋势: {result['trend']['trend']}")
        
        if result['risk_assessment']:
            print(f"\n风险分析:")
            print(f"  风险等级: {result['risk_assessment']['risk_level']}")
            print(f"  95% VaR: {result['risk_assessment']['var_95']:.2f}%")
            print(f"  风险收益比: {result['risk_assessment']['risk_reward_ratio']:.2f}")
        
        if result['oil_analysis']:
            print(f"\n油价分析:")
            print(f"  当前油价: ${result['oil_analysis']['current_spot']:.2f}")
            print(f"  市场状态: {result['oil_analysis']['market_state']}")
            print(f"  价格趋势: {result['oil_analysis']['price_trend']}")
        
        if result['upcoming_events']:
            print(f"\n即将到来的航司活动:")
            for event in result['upcoming_events'][:3]:
                print(f"  {event['airline']} {event['event']}: {event['date'].strftime('%Y-%m-%d')}")
        
        print('\n增强版预测成功!')
        
        print('\n\n=== 联程测试 ===')
        origin, dest = '北京', '深圳'
        itineraries = predict_multi_city_itinerary(origin, dest, future_date, model, max_connections=1, top_n=3)
        print(f"\n{origin} → {dest} 航线推荐:")
        for i, itin in enumerate(itineraries, 1):
            print(f"\n{i}. {itin['type']} - ¥{itin['total_price']:.0f}")
            print(f"   航段: {' → '.join([s[0]+'-'+s[1] for s in itin['segments']])}")
            print(f"   时长: {itin['estimated_duration']:.1f}h | 中转: {itin['transfer_count']}次")
            if 'savings_vs_direct' in itin and itin['savings_vs_direct'] != 0:
                print(f"   比直飞节省: {itin['savings_vs_direct']}%")
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
