import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*60)
print("汽车油耗预测系统 V3.0 - 功能集成测试")
print("="*60)

print("\n1. 测试行程记录管理模块...")
try:
    from trip_manager import TripRecordManager
    tm = TripRecordManager()
    print("   ✓ TripRecordManager 初始化成功")
    
    stats = tm.get_statistics()
    print(f"   ✓ 获取统计数据成功: {stats['total_trips']} 条行程")
    
    vehicle = tm.get_vehicle_profile()
    print(f"   ✓ 车辆档案加载成功: {vehicle['make']} {vehicle['model']}")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n2. 测试异常检测模块...")
try:
    from anomaly_detector import FuelAnomalyDetector
    ad = FuelAnomalyDetector()
    print("   ✓ FuelAnomalyDetector 初始化成功")
    
    trend = ad.get_trend_analysis()
    print(f"   ✓ 趋势分析: {trend if trend else '数据不足'}")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n3. 测试车辆健康分析模块...")
try:
    from vehicle_health import VehicleHealthAnalyzer, DTC_DATABASE
    vh = VehicleHealthAnalyzer()
    print("   ✓ VehicleHealthAnalyzer 初始化成功")
    
    print(f"   ✓ 故障码数据库: {len(DTC_DATABASE)} 个故障码")
    
    report = vh.generate_health_report()
    print(f"   ✓ 健康报告生成: 评分 {report['health_score']}/100")
    
    test_dtc = 'P0300'
    info = vh.lookup_dtc(test_dtc)
    if info:
        print(f"   ✓ 故障码查询: {test_dtc} - {info['description']}")
        print(f"     油耗影响: +{info['fuel_impact_pct']}%")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n4. 测试核心模块兼容性...")
try:
    from feature_engineering import FeatureEngineer
    from quantile_trainer import QuantileFuelModel
    from shap_explainer import FuelConsumptionExplainer
    print("   ✓ 所有核心模块导入成功")
except Exception as e:
    print(f"   ✗ 错误: {e}")

print("\n" + "="*60)
print("集成测试完成!")
print("="*60)
print("\n8个功能标签页:")
print("  📊 油耗预测")
print("  📡 传感器数据")
print("  💡 个性化建议")
print("  🚙 车型对比")
print("  🔬 模型解释")
print("  📝 行程记录 (新增)")
print("  ⚠️ 异常检测 (新增)")
print("  🔧 车辆健康 (新增)")
print("\n启动命令: streamlit run app.py")
