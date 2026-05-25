import os
import sys
import requests
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_separator():
    print("=" * 70)


def run_api_example():
    print_separator()
    print("电影票房预测平台 - API 使用示例")
    print_separator()

    base_url = "http://localhost:8000"

    print("\n1. 检查服务健康状态...")
    try:
        response = requests.get(f"{base_url}/health")
        health_data = response.json()
        print(f"   状态: {health_data['status']}")
        print(f"   模型就绪: {health_data['model_ready']}")
        print(f"   版本: {health_data['version']}")
        if not health_data['model_ready']:
            print("   警告: 模型尚未训练，请先运行 python train.py")
            return
    except requests.exceptions.ConnectionError:
        print("   错误: 无法连接到服务，请先运行 python main.py 启动服务")
        return

    print("\n2. 单电影票房预测...")
    
    daily_promo = [200, 300, 450, 600, 800, 1000, 1200, 1400, 1050, 1000]
    
    movie_data = {
        "title": "流浪地球3",
        "genres": ["科幻", "冒险", "动作"],
        "director": "张艺谋",
        "main_actor": "吴京",
        "release_date": "2025-02-12",
        "promotion_budget": 8000,
        "promotion_timeseries": {
            "daily_spend": daily_promo,
            "spend_pattern": "back_loaded",
            "total_spend": sum(daily_promo)
        },
        "runtime": 135,
        "production_budget": 40000,
        "competition_environment": {
            "same_period_movies": 5,
            "average_competitor_budget": 3000,
            "genre_overlap_ratio": 0.3,
            "competitor_ratings": [7.5, 6.8, 8.0, 7.2, 6.5]
        },
        "pre_sales_data": {
            "total_amount": 5000,
            "daily_sales": [50, 80, 120, 180, 250, 350, 500, 700, 900, 870],
            "presale_days": 10,
            "wish_count": 500000
        },
        "point_screen_data": {
            "screen_count": 150,
            "total_viewers": 18000,
            "average_occupancy": 0.85,
            "point_screen_days": 3,
            "average_score": 9.2,
            "positive_review_ratio": 0.95,
            "social_media_mentions": 12000,
            "want_to_watch_increase": 80000
        },
        "wom_scoring": {
            "douban_score": 8.8,
            "maoyan_score": 9.5,
            "taopiaopiao_score": 9.4,
            "imdb_score": 8.2,
            "rotten_tomatoes": 92,
            "metacritic": 85
        }
    }

    print(f"   电影: {movie_data['title']}")
    print(f"   类型: {', '.join(movie_data['genres'])}")
    print(f"   导演: {movie_data['director']}")
    print(f"   主演: {movie_data['main_actor']}")

    try:
        response = requests.post(
            f"{base_url}/predict",
            params={"confidence": 0.9},
            json=movie_data
        )
        result = response.json()
        
        if response.status_code == 200:
            print("\n" + "-" * 50)
            print("预测结果:")
            print("-" * 50)
            
            fw = result['first_week_box_office']
            tb = result['total_box_office']
            
            print(f"\n首周票房:")
            print(f"  预测值: {fw['point']:,.0f} 万元")
            print(f"  {int(fw['confidence']*100)}%置信区间: [{fw['lower']:,.0f}, {fw['upper']:,.0f}] 万元")
            print(f"  分位数:")
            for q, v in fw['quantiles'].items():
                print(f"    {q}: {v:,.0f} 万元")
            
            print(f"\n总票房:")
            print(f"  预测值: {tb['point']:,.0f} 万元")
            print(f"  {int(tb['confidence']*100)}%置信区间: [{tb['lower']:,.0f}, {tb['upper']:,.0f}] 万元")
            print(f"  分位数:")
            for q, v in tb['quantiles'].items():
                print(f"    {q}: {v:,.0f} 万元")
            
            print(f"\n预测置信度: {result['prediction_confidence']:.2%}")
            
            print("\n" + "-" * 50)
            print("模型贡献:")
            print("-" * 50)
            for mc in result['model_contributions']:
                print(f"  {mc['target']}:")
                print(f"    XGBoost权重: {mc['xgb_weight']:.3f}")
                print(f"    LSTM权重: {mc['lstm_weight']:.3f}")
            
            print("\n" + "-" * 50)
            print("影响因子重要性 (Top 10):")
            print("-" * 50)
            for i, fi in enumerate(result['feature_importance'][:10], 1):
                bar = "█" * int(fi['importance_percent'] / 2)
                print(f"  {i:2d}. {fi['feature']:<25} {fi['importance_percent']:5.2f}%  {bar}")
            
            print("\n" + "-" * 50)
            print("特征分组重要性:")
            print("-" * 50)
            for fgi in result['feature_group_importance']:
                bar = "█" * int(fgi['importance_percent'] / 2)
                print(f"  {fgi['rank']}. {fgi['group_name']:<15} {fgi['importance_percent']:5.2f}%  {bar}")
            
            print("\n" + "-" * 50)
            print("局部特征贡献 (首周票房 Top 5):")
            print("-" * 50)
            local = result['local_explanation']['first_week']
            print(f"  基准值: {local['base_value']:,.0f} 万元")
            for i, item in enumerate(local['explanation'][:5], 1):
                sign = "+" if item['impact'] == 'positive' else ""
                print(f"  {i}. {item['feature']:<25} {sign}{item['shap_value']:,.0f} 万元 ({item['impact']})")
            
            if result.get('point_screen_applied', False):
                print("\n" + "-" * 50)
                print("点映数据修正:")
                print("-" * 50)
                print(f"  点映修正因子: {result['point_screen_correction_factor']:.3f}x")
                if result['point_screen_correction_factor'] > 1:
                    print(f"  修正效果: 正向修正 +{((result['point_screen_correction_factor']-1)*100):.1f}%")
                else:
                    print(f"  修正效果: 负向修正 -{((1-result['point_screen_correction_factor'])*100):.1f}%")
            
            if result.get('wom_analysis'):
                wom = result['wom_analysis']
                print("\n" + "-" * 50)
                print("口碑传播仿真分析:")
                print("-" * 50)
                print(f"  综合口碑得分: {wom['word_of_mouth_score']:.2f}/10")
                print(f"  口碑影响力: {wom['word_of_mouth_impact']:.1f}%")
                print(f"  长尾效应 (Legs Ratio): {wom['legs_ratio']:.2f}x")
                print(f"  预测票房峰值: 第{wom['peak_week']}周")
                print(f"  预测总放映周: {wom['forecast_weeks']}周")
                print(f"  修正后首周: {wom['adjusted_first_week']:,.0f} 万元")
                print(f"  修正后总票房: {wom['adjusted_total']:,.0f} 万元")
                
                print("\n  逐周票房预测:")
                print(f"  {'周次':<6}{'单周票房':<15}{'累计票房':<15}{'口碑乘数':<10}{'占比':<8}")
                print("  " + "-" * 54)
                for wf in wom['weekly_forecast']:
                    print(f"  {wf['week']:<6}{wf['week_box_office']:>10,.0f}万   {wf['cumulative_box_office']:>10,.0f}万   {wf['wom_multiplier']:.3f}   {wf['share_of_total']*100:>5.1f}%")
                
                print(f"\n  口碑策略建议: {wom['wom_recommendation']}")
            
            if result.get('pricing_strategy'):
                ps = result['pricing_strategy']
                print("\n" + "-" * 50)
                print("定价策略建议:")
                print("-" * 50)
                print(f"  建议平均票价: {ps['average_ticket_price']:.1f} 元")
                print(f"  建议价格区间: [{ps['min_suggested_price']:.1f}, {ps['max_suggested_price']:.1f}] 元")
                print(f"  价格敏感指数: {ps['price_sensitivity_index']:.2f}")
                print(f"  口碑调整系数: {ps['wom_adjustment']:.3f}x")
                
                print("\n  分时段最优定价:")
                print(f"  {'时段':<8}{'类型':<8}{'票价':<8}{'收入':<12}{'上座率':<8}{'弹性':<8}")
                print("  " + "-" * 52)
                for segment_name, segment_data in ps['segment_pricing'].items():
                    for day_type in ['weekday', 'weekend']:
                        day_label = '工作日' if day_type == 'weekday' else '周末'
                        sp = segment_data[day_type]
                        print(f"  {segment_name:<8}{day_label:<8}{sp['optimal_price']:>6.1f}元  {sp['expected_revenue']:>8,.0f}万  {sp['expected_occupancy']:>6.1%}  {sp['demand_elasticity']:>6.2f}")
                
                print(f"\n  定价策略建议: {ps['recommendation']}")
        else:
            print(f"错误: {result.get('detail', 'Unknown error')}")
            
    except Exception as e:
        print(f"请求失败: {e}")

    print("\n3. 获取全局特征重要性...")
    try:
        response = requests.get(f"{base_url}/feature-importance", params={"top_n": 10})
        data = response.json()
        
        if response.status_code == 200:
            print("\n全局特征重要性 Top 10:")
            for i, fi in enumerate(data['feature_importance'], 1):
                bar = "█" * int(fi['importance_percent'] / 2)
                print(f"  {i:2d}. {fi['feature']:<25} {fi['importance_percent']:5.2f}%  {bar}")
            
            print("\n全局特征分组重要性:")
            for fgi in data['feature_group_importance']:
                bar = "█" * int(fgi['importance_percent'] / 2)
                print(f"  {fgi['rank']}. {fgi['group_name']:<15} {fgi['importance_percent']:5.2f}%  {bar}")
        else:
            print(f"错误: {data.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"请求失败: {e}")

    print("\n4. 批量预测示例...")
    
    daily_promo1 = [300, 500, 700, 1000, 1300, 1500, 1700, 1800, 1400, 1100, 700]
    daily_promo2 = [250, 350, 500, 700, 850, 900, 950, 800, 700]
    
    batch_data = {
        "movies": [
            {
                "title": "春节档喜剧片",
                "genres": ["喜剧", "剧情"],
                "director": "陈思诚",
                "main_actor": "沈腾",
                "release_date": "2025-02-10",
                "promotion_budget": 12000,
                "promotion_timeseries": {
                    "daily_spend": daily_promo1,
                    "spend_pattern": "front_loaded",
                    "total_spend": sum(daily_promo1)
                },
                "runtime": 128,
                "production_budget": 30000,
                "competition_environment": {
                    "same_period_movies": 8,
                    "average_competitor_budget": 8000,
                    "genre_overlap_ratio": 0.6
                },
                "pre_sales_data": {
                    "total_amount": 15000,
                    "daily_sales": [200, 350, 500, 700, 950, 1200, 1500, 1800, 2200, 2600, 3000],
                    "presale_days": 11,
                    "wish_count": 1200000
                }
            },
            {
                "title": "暑期档动画",
                "genres": ["动画", "家庭", "冒险"],
                "director": "Disney Animation",
                "main_actor": "Tom Hanks",
                "release_date": "2025-07-15",
                "promotion_budget": 6000,
                "promotion_timeseries": {
                    "daily_spend": daily_promo2,
                    "spend_pattern": "uniform",
                    "total_spend": sum(daily_promo2)
                },
                "runtime": 105,
                "production_budget": 50000,
                "competition_environment": {
                    "same_period_movies": 3,
                    "average_competitor_budget": 2000,
                    "genre_overlap_ratio": 0.1
                },
                "pre_sales_data": {
                    "total_amount": 3000,
                    "daily_sales": [80, 120, 180, 250, 320, 400, 480, 550, 620],
                    "presale_days": 9,
                    "wish_count": 300000
                }
            }
        ],
        "confidence": 0.9
    }

    try:
        response = requests.post(f"{base_url}/batch-predict", json=batch_data)
        results = response.json()
        
        if response.status_code == 200:
            for i, result in enumerate(results, 1):
                print(f"\n  电影 {i}: {result['movie_title']}")
                print(f"    首周票房: {result['first_week_box_office']['point']:,.0f} 万元")
                print(f"    总票房: {result['total_box_office']['point']:,.0f} 万元")
                print(f"    置信度: {result['prediction_confidence']:.2%}")
        else:
            print(f"错误: {results.get('detail', 'Unknown error')}")
            
    except Exception as e:
        print(f"请求失败: {e}")

    print("\n" + "=" * 70)
    print("API 示例运行完成")
    print("=" * 70)


if __name__ == '__main__':
    run_api_example()
