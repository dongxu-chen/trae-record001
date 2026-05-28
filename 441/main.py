import argparse
from data_generator import TimeSeriesDataGenerator
from anomaly_fusion import AnomalyFusion
from root_cause_analyzer import RootCauseAnalyzer
from es_storage import ElasticsearchStorage
from config import Config

def run_demo():
    print("=" * 60)
    print("时间序列异常检测平台 - 演示模式")
    print("=" * 60)
    
    print("\n[1/4] 生成模拟数据...")
    generator = TimeSeriesDataGenerator(days=7, freq='5min')
    df, injected_anomalies = generator.generate_metrics_data(inject_anomalies=True)
    print(f"  - 生成 {len(df)} 条数据记录")
    print(f"  - 注入 {len(injected_anomalies)} 个异常点")
    
    print("\n[2/4] 执行多算法异常检测...")
    fusion = AnomalyFusion()
    anomalies = fusion.fuse_anomalies(df, Config.METRICS)
    print(f"  - 检测到 {len(anomalies)} 个异常")
    
    summary = fusion.get_anomaly_summary(df, Config.METRICS)
    print(f"  - 联合异常: {summary['joint_anomalies']}")
    print(f"  - 严重异常: {summary['high_severity']}")
    
    print("\n[3/4] 根因分析...")
    analyzer = RootCauseAnalyzer()
    anomalies_with_root = analyzer.analyze_root_causes(df, anomalies, Config.METRICS)
    
    print(f"\n[4/4] Top 5 异常结果:")
    for i, anomaly in enumerate(anomalies_with_root[:5]):
        print(f"\n  异常 #{i+1}")
        print(f"  - 时间: {anomaly['timestamp']}")
        print(f"  - 分数: {anomaly['total_score']:.2%}")
        print(f"  - 指标: {', '.join(anomaly['metrics'].keys())}")
        print(f"  - 联合异常: {'是' if anomaly['is_joint_anomaly'] else '否'}")
        
        if anomaly['root_cause_candidates']:
            top_cause = anomaly['root_cause_candidates'][0]
            print(f"  - 根因: {top_cause['description']}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)

def store_data():
    print("生成并存储数据到Elasticsearch...")
    
    storage = ElasticsearchStorage()
    generator = TimeSeriesDataGenerator(days=14, freq='5min')
    df, _ = generator.generate_metrics_data()
    
    storage.store_metrics(df)
    print(f"已存储 {len(df)} 条记录")

def run_full_analysis():
    print("执行完整分析...")
    
    storage = ElasticsearchStorage()
    fusion = AnomalyFusion()
    analyzer = RootCauseAnalyzer()
    
    from datetime import datetime, timedelta
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        print("没有数据，请先生成数据")
        return
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = fusion.fuse_anomalies(df_pivot, Config.METRICS)
    anomalies_with_root = analyzer.analyze_root_causes(df_pivot, anomalies, Config.METRICS)
    
    storage.store_anomalies(anomalies_with_root)
    
    print(f"检测到 {len(anomalies_with_root)} 个异常并已存储")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='时间序列异常检测平台')
    parser.add_argument('--mode', choices=['demo', 'store', 'analyze', 'server'], 
                       default='demo', help='运行模式')
    args = parser.parse_args()
    
    if args.mode == 'demo':
        run_demo()
    elif args.mode == 'store':
        store_data()
    elif args.mode == 'analyze':
        run_full_analysis()
    elif args.mode == 'server':
        from app import app
        app.run(host='0.0.0.0', port=5000, debug=True)
