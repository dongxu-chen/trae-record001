from price_alert import PriceAlertManager
from refund_cost import calculate_refund_cost, calculate_breakeven_point
from datetime import datetime, timedelta

print('=== 测试价格警报 ===')
manager = PriceAlertManager()
manager.clear_all_alerts()

alert = manager.create_alert(
    route='北京-上海',
    target_price=500,
    departure_date='2025-08-15',
    email='test@example.com',
    note='测试警报'
)

print(f'创建警报: {alert["id"]}')
print(f'活动警报数: {len(manager.get_active_alerts())}')

stats = manager.get_alert_statistics()
print(f'警报统计: {stats}')

print('\n=== 测试退改签成本 ===')
dep_date = datetime.now() + timedelta(days=14)

result = calculate_refund_cost(1000, 'economy_discount', dep_date)
print(f'退票测试: 退款¥{result["refund_amount"]:.0f}, 手续费¥{result["fee_amount"]:.0f}')

be = calculate_breakeven_point(800, 1200, 'economy_discount', 'economy_flexible', dep_date)
print(f'盈亏平衡: {be["breakeven_probability"]}%')

print('\n=== 测试多城市联运预测 ===')
import sys
sys.path.insert(0, '.')
from model_training import AirlinePriceModel
from prediction import predict_multi_city_itinerary

try:
    model = AirlinePriceModel()
    model.load_models()
    
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    itineraries = predict_multi_city_itinerary('北京', '深圳', future_date, model, max_connections=1, top_n=3)
    
    print(f'找到 {len(itineraries)} 条航线推荐:')
    for i, itin in enumerate(itineraries, 1):
        print(f'\n{i}. {itin["type"]} - ¥{itin["total_price"]:.0f}')
        print(f'   航段: {" → ".join([s[0]+"-"+s[1] for s in itin["segments"]])}')
        print(f'   时长: {itin["estimated_duration"]:.1f}h | 中转: {itin["transfer_count"]}次')
except Exception as e:
    print(f'模型加载失败: {e}')
    import traceback
    traceback.print_exc()

print('\n✅ 所有测试通过!')
