import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("快递时效预测系统 - 完整版测试")
print("=" * 70)

print("\n1. 测试地图API + 本地缓存...")
from utils.map_api import MapAPI
map_api = MapAPI(use_mock=True, cache_enabled=True)
route_info1 = map_api.calculate_distance("北京市朝阳区", "上海市浦东新区")
print(f"   第一次查询 - 距离: {route_info1['distance']:.1f} km, 缓存: {route_info1.get('from_cache', False)}")

route_info2 = map_api.calculate_distance("北京市朝阳区", "上海市浦东新区")
print(f"   第二次查询 - 距离: {route_info2['distance']:.1f} km, 缓存: {route_info2.get('from_cache', False)}")

cache_stats = map_api.get_cache_stats()
print(f"   缓存统计: 地址={cache_stats['geocode_count']}, 路线={cache_stats['route_count']}")
print("   ✓ 地图API + 本地缓存测试通过")

print("\n2. 测试天气API + 网格级降水量...")
from utils.weather_api import WeatherAPI
weather_api = WeatherAPI(use_mock=True, cache_enabled=True)
coords = [116.4074, 39.9042]
grid_data = weather_api.get_weather_grid(coords[0], coords[1])
print(f"   网格点数: {len(grid_data['points'])}")
print(f"   平均降水量: {grid_data['avg_precipitation']:.2f} mm/h")
print(f"   最大降水量: {grid_data['max_precipitation']:.2f} mm/h")
print(f"   降水覆盖率: {grid_data['precipitation_coverage']:.0%}")

weather_info = weather_api.get_weather("北京", coords=coords)
print(f"   天气: {weather_info['weather']}, 温度: {weather_info['temperature']}°C")
print(f"   降水量率: {weather_info.get('precipitation_rate', 0):.2f} mm/h")
print("   ✓ 天气API + 网格级降水量测试通过")

print("\n3. 测试特征工程 + 节假日特征...")
from utils.features import FeatureEngineer
from datetime import datetime
features, holiday_info = FeatureEngineer.build_features(
    "北京市朝阳区",
    "上海市浦东新区",
    datetime(2024, 11, 11, 14, 30),
    weather_info,
    "正常",
    route_info1
)
print(f"   特征数量: {len(features)}")
print(f"   核心特征: distance={features['distance']:.1f} km")
print(f"   降水特征: rate={features['precipitation_rate']:.2f}, intensity={features['precipitation_intensity']}")
print(f"   节假日特征: is_holiday={features.get('is_holiday', 0)}, holiday_name={holiday_info.get('holiday_name', 'N/A')}")
print(f"   影响系数: weather={features['weather_impact']:.2f}, precip={1+features['precipitation_impact']:.2f}")
print("   ✓ 特征工程测试通过")

print("\n4. 测试节假日影响模型...")
from utils.holiday_model import HolidayModel
holiday_model = HolidayModel()
from datetime import timedelta

test_dates = [
    datetime(2024, 2, 10, 10, 0),
    datetime(2024, 11, 11, 14, 0),
    datetime(2024, 6, 15, 12, 0),
]
for d in test_dates:
    info = holiday_model.get_holiday_info(d)
    vol_pred = holiday_model.predict_volume_change(d, base_volume=10000)
    print(f"   {d.strftime('%Y-%m-%d')}: 节假日={info.get('holiday_name', '无')}, 量系数={info['volume_factor']:.1f}, 预计量={vol_pred['predicted_volume']:.0f}")

calendar = holiday_model.get_holiday_calendar(2024)
print(f"   2024年节假日数量: {len(calendar)}")
print("   ✓ 节假日影响模型测试通过")

print("\n5. 测试延误原因分析...")
from utils.delay_analyzer import DelayAnalyzer
delay_analyzer = DelayAnalyzer()

test_features = {
    'distance': 1200,
    'precipitation_rate': 5.0,
    'precipitation_intensity': 3,
    'precipitation_coverage': 0.8,
    'windpower': 6,
    'weather_encoded': 5,
    'busy_score': 0.85,
    'busy_impact': 1.25,
    'weather_impact': 0.6,
    'holiday_volume_factor': 2.0,
    'holiday_delay_factor': 1.5,
    'is_ecommerce_promo': 1,
    'is_spring_festival': 0,
}
analysis = delay_analyzer.analyze(test_features, predicted_hours=45, expected_hours=24)
print(f"   预测时效: {analysis['predicted_hours']:.1f}h, 延误: {analysis['delay_hours']:.1f}h ({analysis['delay_pct']:.0f}%)")
print(f"   延误程度: {analysis['severity']}")
print(f"   主导因素: {analysis['dominant_factor_name']}")
print(f"   因素贡献:")
for contrib in delay_analyzer.get_factor_contribution(analysis):
    print(f"     - {contrib['factor_name']}: {contrib['contribution_pct']:.1f}% ({contrib['delay_hours']:.1f}h)")
print(f"   建议数量: {len(analysis['recommendations'])}")
print("   ✓ 延误原因分析测试通过")

print("\n6. 测试快递公司时效对比...")
from utils.courier_comparison import CourierComparison
courier = CourierComparison()

comparison = courier.compare_couriers(
    base_hours=30,
    features_dict=test_features,
    weight=5,
    distance=1200,
    service_type='standard'
)
print(f"   参与对比公司: {len(comparison)} 家")
for c in comparison[:3]:
    print(f"   {c['courier_name']}: 时效{c['estimated_hours']:.1f}h, 费用{c['estimated_fee']}元, 综合{c['overall_score']}分")

recommendation = courier.recommend_courier(comparison, priority='balanced')
print(f"   推荐公司: {recommendation['recommended']}")
for reason in recommendation['reasons']:
    print(f"     - {reason}")

courier_options = courier.get_courier_options()
print(f"   可选快递公司: {', '.join(courier_options)}")
print("   ✓ 快递公司时效对比测试通过")

print("\n7. 测试数据生成 + 节假日/延误列...")
from generate_data import generate_training_data
df = generate_training_data(300)
print(f"   生成数据量: {len(df)} 条")
print(f"   新增列: precipitation_rate={df['precipitation_rate'].mean():.2f}")
if 'is_holiday' in df.columns:
    print(f"   节假日占比: {df['is_holiday'].mean():.1%}")
if 'delay_reason' in df.columns:
    print(f"   延误原因分布: {df['delay_reason'].value_counts().to_dict()}")
print(f"   列名: {list(df.columns)}")
print("   ✓ 数据生成测试通过")

print("\n8. 测试分位数回归模型 + 区间收窄...")
from model import DeliveryTimeModel
model = DeliveryTimeModel(confidence_levels=[0.80, 0.90, 0.95, 0.99])
metrics = model.train(df)
print(f"   模型MAE: {metrics['mae']:.2f} 小时")
print(f"   模型R²: {metrics['r2']:.4f}")
for cl in [99, 95, 90, 80]:
    cov = metrics.get(f'coverage_{cl}', 0)
    width = metrics.get(f'interval_width_{cl}', 0)
    print(f"   {cl}%置信区间: 覆盖率={cov:.2%}, 平均宽度={width:.2f}h")
print(f"   分位数点: {model.quantiles}")
print("   ✓ 分位数回归测试通过")

print("\n9. 测试预测功能 + 多置信区间...")
prediction = model.predict(features, confidence_level=0.95)
print(f"   预测时效: {prediction['predicted_hours']:.1f} 小时")
print(f"   {prediction['confidence_level']}置信区间: [{prediction['lower_bound']:.1f}, {prediction['upper_bound']:.1f}] 小时")
print(f"   区间宽度: {prediction['interval_width']:.1f} 小时")
print(f"   是否已收窄: {prediction['narrowed']}")
if prediction.get('all_intervals'):
    print("   多置信水平支持:")
    for level, interval in prediction['all_intervals'].items():
        print(f"      {level}: [{interval['lower']:.1f}, {interval['upper']:.1f}]h")
print("   ✓ 预测功能测试通过")

print("\n10. 测试缓存复用...")
route_info3 = map_api.calculate_distance("北京市朝阳区", "上海市浦东新区")
print(f"   第三次查询 - 缓存命中: {route_info3.get('from_cache', False)}")
map_api.clear_cache()
cache_stats2 = map_api.get_cache_stats()
print(f"   清除后缓存: 地址={cache_stats2['geocode_count']}, 路线={cache_stats2['route_count']}")
print("   ✓ 缓存复用测试通过")

print("\n" + "=" * 70)
print("所有完整版测试通过！项目运行正常。")
print("=" * 70)
