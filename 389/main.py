import numpy as np
import pandas as pd
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_generator import AdDataGenerator, prepare_model_data
from causal_model import IncrementalValueModel
from optimizer import BudgetOptimizer
from position_analyzer import PositionValueAnalyzer
from bid_simulator import DynamicBidSimulator
from auction_simulator import AuctionSimulator


def main():
    print("=" * 60)
    print("广告曝光价值评估模型 - 增量价值分析系统")
    print("=" * 60)

    print("\n[1/6] 生成模拟数据...")
    generator = AdDataGenerator(n_users=5000, n_ads=50, n_impressions=30000, n_positions=5)
    df_users, df_ads, df_positions, df_impressions, df_auctions = generator.generate_all_data(n_competitors=5)

    print(f"  - 用户数量: {len(df_users)}")
    print(f"  - 广告数量: {len(df_ads)}")
    print(f"  - 广告位数量: {len(df_positions)}")
    print(f"  - 曝光日志数: {len(df_impressions)}")
    print(f"  - 拍卖日志数: {len(df_auctions)}")
    print(f"  - 点击率: {df_impressions['click'].mean():.4f}")
    print(f"  - 转化率: {df_impressions['conversion'].mean():.4f}" if 'conversion' in df_impressions.columns else "  - 转化率: N/A")

    print("\n  广告位信息:")
    print(f"  {'位置ID':<10} {'位置名称':<16} {'位置价值':<12} {'基础曝光容量':<14}")
    print("  " + "-" * 55)
    for _, row in df_positions.iterrows():
        print(f"  {row['position_id']:<10} {row['position_name']:<16} {row['position_value']:<12.2f} {row['base_impression_capacity']:<14}")

    print("\n[2/6] 准备模型数据...")
    X, T, Y, ad_ids, user_ids, impression_ids, df_merged = prepare_model_data(
        df_impressions, df_users, df_ads, df_positions
    )
    print(f"  - 特征维度: {X.shape}")
    print(f"  - 处理变量(点击)均值: {T.mean():.4f}")
    print(f"  - 结果变量(转化价值)均值: {Y.mean():.2f}")

    print("\n[3/6] 运行增量价值模型...")
    model = IncrementalValueModel(n_trees=300, max_depth=8, n_splits=5, use_ps_weighting=True)

    print("  [3.1] 使用 CausalForest + 倾向性评分加权 训练...")
    value_results_cf = model.compute_counterfactual_values(
        X, T, Y, ad_ids, impression_ids, method='causal_forest'
    )

    if 'propensity_score' in value_results_cf.columns:
        print(f"  - 倾向性评分均值: {value_results_cf['propensity_score'].mean():.4f}")
        print(f"  - 倾向性评分标准差: {value_results_cf['propensity_score'].std():.4f}")
    if 'sample_weight' in value_results_cf.columns:
        print(f"  - 样本权重均值: {value_results_cf['sample_weight'].mean():.4f}")

    print("  [3.2] 使用 DoubleML 训练...")
    model_dml = IncrementalValueModel(n_trees=300, max_depth=8, n_splits=5)
    value_results_dml = model_dml.compute_counterfactual_values(
        X, T, Y, ad_ids, impression_ids, method='double_ml'
    )

    print(f"\n  CausalForest + PS 加权结果:")
    print(f"  - ITE 均值: {value_results_cf['incremental_value'].mean():.4f}")
    print(f"  - ITE 标准差: {value_results_cf['incremental_value'].std():.4f}")
    print(f"  - 边际价值总和: {value_results_cf['marginal_value'].sum():.2f}")

    print(f"\n  DoubleML 结果:")
    print(f"  - ITE 均值: {value_results_dml['incremental_value'].mean():.4f}")
    print(f"  - ITE 标准差: {value_results_dml['incremental_value'].std():.4f}")
    print(f"  - 边际价值总和: {value_results_dml['marginal_value'].sum():.2f}")

    value_results = value_results_cf.copy()

    print("\n[4/6] 广告位价值分析...")
    position_analyzer = PositionValueAnalyzer()
    position_metrics = position_analyzer.analyze_position_values(value_results, df_positions)

    print(f"\n  各广告位表现汇总:")
    print(f"  {'位置ID':<8} {'位置名称':<16} {'曝光数':<8} {'点击率':<10} {'平均增量价值':<14} {'每曝光价值':<12}")
    print("  " + "-" * 70)
    for _, row in position_metrics.iterrows():
        print(f"  {row['position_id']:<8} {row['position_name']:<16} {row['total_impressions']:<8} {row['ctr']:<10.4f} {row['mean_incremental_value']:<14.4f} {row['value_per_impression']:<12.4f}")

    print(f"\n  广告位价值对比:")
    position_comparison = position_analyzer.compare_positions(position_metrics)
    best = position_comparison['best_position']
    worst = position_comparison['worst_position']
    gaps = position_comparison['gaps']
    print(f"  - 最佳位置: {best['position_name']} (价值: {best['mean_incremental_value']:.4f}, CTR: {best['ctr']:.4f})")
    print(f"  - 最差位置: {worst['position_name']} (价值: {worst['mean_incremental_value']:.4f}, CTR: {worst['ctr']:.4f})")
    print(f"  - 价值差距: {gaps['value_gap_absolute']:.4f} ({gaps['value_gap_percentage']:.2f}%)")
    print(f"  - CTR差距: {gaps['ctr_gap']:.4f}")

    print("\n[5/6] 出价模拟分析...")
    ad_summary = value_results.merge(df_ads[['ad_id', 'category', 'base_bid', 'ad_quality_score']], on='ad_id', how='left')
    ad_summary_grouped = ad_summary.groupby('ad_id').agg(
        total_impressions=('impression_id', 'count'),
        total_clicks=('click', 'sum'),
        mean_incremental_value=('incremental_value', 'mean'),
        total_conversion_value=('conversion_value', 'sum')
    ).reset_index()
    ad_summary_grouped = ad_summary_grouped.merge(df_ads[['ad_id', 'base_bid', 'ad_quality_score', 'category']], on='ad_id', how='left')
    ad_summary_grouped['ctr'] = ad_summary_grouped['total_clicks'] / ad_summary_grouped['total_impressions']
    ad_summary_grouped['value_roi'] = ad_summary_grouped['total_conversion_value'] / ad_summary_grouped['base_bid']

    bid_simulator = DynamicBidSimulator(total_budget=300000.0, time_horizon=30, roi_threshold=1.2)
    allocation_df, simulation_df = bid_simulator.simulate_bidding_with_budget(
        ad_summary_grouped, position_metrics, total_budget=300000.0
    )

    print(f"\n  广告位出价分配 (Top 10 按预期ROI排序):")
    top_allocations = allocation_df.sort_values('expected_roi', ascending=False).head(10)
    print(f"  {'广告ID':<8} {'位置ID':<8} {'位置名称':<16} {'基础出价':<10} {'预期价值':<12} {'预期ROI':<10} {'分配预算':<12}")
    print("  " + "-" * 85)
    for _, row in top_allocations.iterrows():
        print(f"  {int(row['ad_id']):<8} {int(row['position_id']):<8} {row['position_name']:<16} {row['base_position_bid']:<10.4f} {row['expected_value']:<12.4f} {row['expected_roi']:<10.4f} {row['allocated_budget']:<12.2f}")

    print(f"\n  出价建议 (Top 10 优先级):")
    bid_recs = bid_simulator.generate_bid_recommendations(ad_summary_grouped, position_metrics)
    top_recs = bid_recs.head(10)
    print(f"  {'广告ID':<8} {'位置':<8} {'当前出价':<10} {'建议出价':<10} {'变化%':<10} {'预期ROI':<10} {'操作':<20}")
    print("  " + "-" * 85)
    for _, row in top_recs.iterrows():
        print(f"  {int(row['ad_id']):<8} {int(row['position_id']):<8} {row['base_bid']:<10.4f} {row['recommended_bid']:<10.4f} {row['bid_change_pct']:<10.2f} {row['expected_roi']:<10.4f} {row['action']:<20}")

    print("\n[6/6] 拍卖模拟分析...")
    auction_simulator = AuctionSimulator()
    auction_simulator.load_auction_logs(df_auctions)

    sample_ad_id = ad_summary_grouped.iloc[0]['ad_id']
    print(f"\n  对广告 {int(sample_ad_id)} 进行拍卖策略模拟:")

    def original_bid_strategy(auctions, original_bids, ad_id):
        return original_bids

    def aggressive_bid_strategy(auctions, original_bids, ad_id):
        return original_bids * 1.3

    def conservative_bid_strategy(auctions, original_bids, ad_id):
        return original_bids * 0.8

    strategies = {
        '原始出价': original_bid_strategy,
        '激进出价(+30%)': aggressive_bid_strategy,
        '保守出价(-20%)': conservative_bid_strategy
    }

    comparison = auction_simulator.compare_strategies(int(sample_ad_id), strategies)

    print(f"\n  策略对比:")
    print(f"  {'指标':<25} {'原始出价':<15} {'激进出价':<15} {'保守出价':<15}")
    print("  " + "-" * 75)
    metric_names = {
        'win_rate': '胜率',
        'eCPI': '每曝光成本',
        'eCPC': '每点击成本',
        'eCPA': '每转化成本',
        'total_spend': '总支出',
        'total_impressions': '总曝光',
        'total_clicks': '总点击',
        'total_conversions': '总转化',
        'total_conversion_value': '总转化价值',
        'ROI': 'ROI'
    }
    for _, row in comparison.iterrows():
        metric = row['metric']
        name = metric_names.get(metric, metric)
        orig = row['原始出价']
        agg = row['激进出价(+30%)']
        cons = row['保守出价(-20%)']

        if metric in ['win_rate', 'ROI']:
            print(f"  {name:<25} {orig:<15.4f} {agg:<15.4f} {cons:<15.4f}")
        elif metric in ['total_spend', 'total_conversion_value']:
            print(f"  {name:<25} {orig:<15.2f} {agg:<15.2f} {cons:<15.2f}")
        else:
            print(f"  {name:<25} {orig:<15.2f} {agg:<15.2f} {cons:<15.2f}")

    print(f"\n  拍卖数据统计:")
    print(f"  - 总拍卖次数: {len(df_auctions)}")
    print(f"  - 平均实际支付价格: {df_auctions['actual_paid_price'].mean():.4f}")
    print(f"  - 最高实际支付价格: {df_auctions['actual_paid_price'].max():.4f}")
    print(f"  - 最低实际支付价格: {df_auctions['actual_paid_price'].min():.4f}")

    print("\n" + "=" * 60)
    print("分析完成!")
    print("=" * 60)

    return {
        'value_results': value_results,
        'ad_summary': ad_summary_grouped,
        'position_metrics': position_metrics,
        'allocation': allocation_df,
        'bid_recommendations': bid_recs,
        'auction_comparison': comparison
    }


if __name__ == '__main__':
    main()
