import pandas as pd
import numpy as np
import os
import sys

from data_generator import generate_all_data
from recommender import CollaborativeFilteringRecommender
from boxoffice_predictor import BoxOfficePredictor
from preference_analyzer import PreferenceAnalyzer


def format_currency(value):
    return f"${value:,.0f}"


def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_data_generation():
    print_section("1. 数据生成测试")

    os.makedirs('data', exist_ok=True)
    movies_df, users_df, ratings_df, boxoffice_df = generate_all_data()

    print(f"电影数据: {len(movies_df)} 条")
    print(f"用户数据: {len(users_df)} 条")
    print(f"评分数据: {len(ratings_df)} 条")
    print(f"票房数据: {len(boxoffice_df)} 条")

    print("\n电影数据示例:")
    print(movies_df[['movie_id', 'title', 'genres', 'budget', 'runtime']].head(3).to_string(index=False))

    print("\n用户数据示例:")
    user_cols = ['user_id', 'age_group', 'gender', 'occupation', 'watch_frequency']
    print(users_df[user_cols].head(3).to_string(index=False))

    return movies_df, users_df, ratings_df, boxoffice_df


def test_recommender_basic(ratings_df, users_df, movies_df):
    print_section("2. 基础推荐 + 层次聚类 + 冷启动测试")

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    test_user = 'U001'
    is_cold = recommender._is_cold_start(test_user)
    print(f"用户 {test_user} 冷启动状态: {is_cold}")

    print(f"\n为用户 {test_user} 生成推荐 (混合方法 + 探索):")
    recommendations = recommender.recommend(test_user, top_n=8, method='hybrid')
    for i, rec in enumerate(recommendations, 1):
        source = rec.get('recommendation_source', 'N/A')
        print(f"  {i}. {rec['title']} | 类型: {rec['genres']} | 预测评分: {rec['predicted_rating']} | 来源: {source}")

    print(f"\n层次聚类信息:")
    cluster_info = recommender.get_cluster_info()
    print(f"  最优聚类数: {cluster_info['optimal_n_clusters']}")
    for c, size in cluster_info['cluster_sizes'].items():
        print(f"  聚类 {c}: {size} 个用户")

    user_cluster = recommender.get_cluster_info(test_user)
    print(f"\n用户 {test_user} 的聚类信息:")
    print(f"  所属聚类: {user_cluster.get('user_cluster', 'N/A')}")
    if 'cluster_demographics' in user_cluster:
        demo = user_cluster['cluster_demographics']
        print(f"  聚类年龄分布: {demo.get('age_distribution', {})}")
        print(f"  聚类性别分布: {demo.get('gender_distribution', {})}")

    return recommender


def test_cold_start(ratings_df, users_df, movies_df):
    print_section("3. 冷启动用户人口统计学推荐测试")

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    new_user_id = 'COLD_NEW_001'
    new_user_data = pd.DataFrame([{
        'user_id': new_user_id,
        'age_group': '18-25',
        'gender': 'M',
        'occupation': '学生',
        'city': '北京',
        'watch_frequency': '高频',
        'pref_动作': 0.9, 'pref_喜剧': 0.7, 'pref_剧情': 0.3,
        'pref_科幻': 0.8, 'pref_恐怖': 0.1, 'pref_爱情': 0.2,
        'pref_动画': 0.6, 'pref_悬疑': 0.5, 'pref_冒险': 0.7, 'pref_战争': 0.4
    }])

    temp_users = pd.concat([users_df, new_user_data], ignore_index=True)
    orig = recommender.users_df
    recommender.users_df = temp_users

    print(f"冷启动用户: {new_user_id}")
    print(f"  年龄: 18-25 | 性别: 男 | 职业: 学生 | 频率: 高频")
    print(f"  偏好: 动作(0.9), 科幻(0.8), 冒险(0.7)")

    is_cold = recommender._is_cold_start(new_user_id)
    print(f"  冷启动判断: {is_cold}")

    print(f"\n人口统计学 + 探索推荐结果:")
    recommendations = recommender._recommend_cold_start_demographic(new_user_id, top_n=8)
    for i, rec in enumerate(recommendations, 1):
        source = rec.get('recommendation_source', 'N/A')
        print(f"  {i}. {rec['title']} | 类型: {rec['genres']} | 预测评分: {rec['predicted_rating']} | 来源: {source}")

    recommender.users_df = orig
    return recommender


def test_sequence_recommendation(ratings_df, users_df, movies_df):
    print_section("4. 序列推荐测试（捕捉偏好演变）")

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    test_user = 'U001'

    print(f"用户 {test_user} 的观影序列分析:")
    seq_analysis = recommender.get_user_sequence_analysis(test_user)
    print(f"  总观看数: {seq_analysis.get('total_watched', 0)}")
    print(f"  最近类型趋势:")
    for trend in seq_analysis.get('recent_trend', []):
        print(f"    - {trend['genre']}: 趋势分 {trend['trend_score']}")

    print(f"  热门类型转换:")
    for transition, score in list(seq_analysis.get('top_genre_transitions', {}).items())[:5]:
        print(f"    {transition}: {score}")

    print(f"\n序列感知推荐 (序列权重=0.3):")
    seq_recs = recommender.recommend_sequence(test_user, top_n=8, sequence_weight=0.3)
    for i, rec in enumerate(seq_recs, 1):
        seq_score = rec.get('sequence_score', 0)
        final_score = rec.get('final_score', 0)
        print(f"  {i}. {rec['title']} | 类型: {rec['genres']} | 序列分: {seq_score} | 综合分: {final_score}")

    return recommender


def test_diversity_control(ratings_df, users_df, movies_df):
    print_section("5. 推荐多样性控制测试")

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    test_user = 'U001'

    print(f"用户 {test_user} 的普通推荐 (无多样性控制):")
    normal_recs = recommender.recommend(test_user, top_n=8)
    normal_genres = set()
    for rec in normal_recs:
        for g in rec['genres'].split('|'):
            normal_genres.add(g)
    print(f"  覆盖类型数: {len(normal_genres)}")
    print(f"  类型列表: {normal_genres}")

    print(f"\nGreedy 多样性控制推荐 (多样性权重=0.25):")
    greedy_recs = recommender.recommend_with_diversity(test_user, top_n=8, diversity_weight=0.25, diversity_method='greedy')
    greedy_genres = set()
    for i, rec in enumerate(greedy_recs, 1):
        for g in rec['genres'].split('|'):
            greedy_genres.add(g)
        div_score = rec.get('diversity_adjusted_score', 0)
        print(f"  {i}. {rec['title']} | 类型: {rec['genres']} | 调整分: {div_score}")
    print(f"  覆盖类型数: {len(greedy_genres)} (+{len(greedy_genres)-len(normal_genres)})")
    print(f"  类型列表: {greedy_genres}")

    print(f"\nMMR 多样性控制推荐 (多样性权重=0.3):")
    mmr_recs = recommender.recommend_with_diversity(test_user, top_n=8, diversity_weight=0.3, diversity_method='mmr')
    mmr_genres = set()
    for i, rec in enumerate(mmr_recs, 1):
        for g in rec['genres'].split('|'):
            mmr_genres.add(g)
        mmr_score = rec.get('mmr_score', 0)
        print(f"  {i}. {rec['title']} | 类型: {rec['genres']} | MMR分: {mmr_score}")
    print(f"  覆盖类型数: {len(mmr_genres)} (+{len(mmr_genres)-len(normal_genres)})")
    print(f"  类型列表: {mmr_genres}")

    return recommender


def test_runtime_recommendation(ratings_df, users_df, movies_df):
    print_section("6. 观影时间预测与时长匹配推荐")

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    test_user = 'U001'

    print(f"用户 {test_user} 的观影时间模式分析:")
    time_analysis = recommender.get_user_watch_time_analysis(test_user)
    print(f"  总观看数: {time_analysis.get('total_watches', 0)}")
    print(f"  平均观看时长: {time_analysis.get('avg_runtime_watched', 0)} 分钟")
    print(f"  偏好时长范围: {time_analysis.get('preferred_runtime_range', (0,0))} 分钟")
    print(f"  周末观看比例: {time_analysis.get('weekend_ratio', 0):.1%}")
    print(f"  是否周末观影者: {'是' if time_analysis.get('is_weekend_watcher', False) else '否'}")
    print(f"  偏好星期: {time_analysis.get('preferred_days', [])}")
    suggestion = time_analysis.get('best_time_suggestion', {})
    print(f"  最佳建议: {suggestion.get('suggestion', 'N/A')}")

    available_times = [60, 120, 180]
    for avail in available_times:
        print(f"\n可用时间 {avail} 分钟的推荐 (容差15分钟):")
        runtime_result = recommender.recommend_by_runtime(test_user, available_minutes=avail, top_n=5, tolerance=15)
        pref_range = runtime_result.get('preferred_runtime_range', (0,0))
        print(f"  用户偏好时长范围: {pref_range[0]}-{pref_range[1]} 分钟")
        for i, rec in enumerate(runtime_result.get('recommendations', []), 1):
            fit = rec.get('runtime_fit_score', 0)
            is_pref = rec.get('is_preferred_range', False)
            print(f"    {i}. {rec['title']} | 时长: {rec['runtime']}分钟 | 匹配度: {fit:.2%} | 偏好范围: {'是' if is_pref else '否'}")

    return recommender


def test_boxoffice_prediction(movies_df, boxoffice_df):
    print_section("7. LightGBM 票房预测 + 宣发费用智能填充测试")

    predictor = BoxOfficePredictor()
    metrics = predictor.train(movies_df, boxoffice_df)

    print(f"\n模型性能指标:")
    print(f"  RMSE: {format_currency(metrics['rmse'])}")
    print(f"  MAE: {format_currency(metrics['mae'])}")
    print(f"  R2: {metrics['r2']:.4f}")

    test_movie = movies_df.iloc[0].to_dict()
    prediction = predictor.predict_with_interval(test_movie, confidence=0.9)

    print(f"\n电影 '{test_movie['title']}' 的票房预测:")
    print(f"  预测首周票房: {format_currency(prediction['predicted_opening'])}")
    print(f"  预测区间 ({int(prediction['confidence']*100)}%置信度):")
    print(f"    下限: {format_currency(prediction['lower_bound'])}")
    print(f"    上限: {format_currency(prediction['upper_bound'])}")
    print(f"  预测总票房: {format_currency(prediction['predicted_total'])}")
    print(f"  宣发费用来源: {prediction['marketing_spend_source']}")

    actual_opening = boxoffice_df[boxoffice_df['movie_id'] == test_movie['movie_id']]['opening_weekend_revenue'].values[0]
    print(f"  实际首周票房: {format_currency(actual_opening)}")
    error = abs(prediction['predicted_opening'] - actual_opening) / actual_opening * 100
    print(f"  预测误差: {error:.2f}%")

    print(f"\n宣发费用智能预估测试:")
    estimate = predictor.get_marketing_estimate(test_movie)
    print(f"  预估宣发费用: {format_currency(estimate['estimated_marketing_spend'])}")
    print(f"  预算占比: {estimate['budget_ratio']:.2%}")
    print(f"  电影热度评分: {estimate['heat_score']}")
    print(f"  历史均值占比: {estimate['historical_avg_ratio']:.2%}")
    print(f"  填充方法: {estimate['method']}")

    print("\n特征重要性 Top 10:")
    importance = predictor.get_feature_importance(top_n=10)
    for feat in importance:
        print(f"  - {feat['feature']}: {feat['importance']:.1f}")

    return predictor


def test_preference_analysis(ratings_df, movies_df, users_df):
    print_section("8. 用户观影偏好分析")

    analyzer = PreferenceAnalyzer()

    test_user = 'U001'
    analysis = analyzer.analyze_user_preferences(test_user, ratings_df, movies_df, users_df)

    print(f"用户 {test_user} 信息:")
    user_info = analysis['user_info']
    print(f"  年龄段: {user_info['age_group']} | 性别: {user_info['gender']} | 职业: {user_info['occupation']}")
    print(f"  城市: {user_info['city']} | 观影频率: {user_info['watch_frequency']}")

    stats = analysis['basic_stats']
    print(f"\n基本统计:")
    print(f"  评分总数: {stats['total_ratings']} | 平均评分: {stats['average_rating']}")
    print(f"  高分率(>=4.0): {stats['high_rated_ratio']*100:.0f}% | 低分率(<=2.0): {stats['low_rated_ratio']*100:.0f}%")

    print(f"\n偏好类型 Top 5:")
    for i, genre in enumerate(analysis['genre_preferences']['top_preferred'], 1):
        print(f"  {i}. {genre['genre']} | 观看{genre['count']}部 | 均分{genre['avg_rating']}")

    print(f"\n偏好总结: {analysis['preference_summary']}")

    print(f"\n用户对比测试 (U001 vs U002):")
    comparison = analyzer.compare_users('U001', 'U002', ratings_df, movies_df)
    print(f"  共同偏好类型: {', '.join(comparison['common_preferred_genres'])}")
    print(f"  共同观看电影数: {comparison['common_movies_count']}")
    if 'common_movies_agreement' in comparison:
        print(f"  评分相似度: {comparison['common_movies_agreement']*100:.0f}%")

    return analyzer


def main():
    print("\n" + "#" * 80)
    print("#" + " " * 78 + "#")
    print("#" + " " * 18 + "电影推荐与票房预测系统 v2.1 测试" + " " * 28 + "#")
    print("#" + " " * 78 + "#")
    print("#" * 80)
    print("\n功能特性:")
    print("  1. 序列推荐 - 捕捉用户观影时序偏好演变")
    print("  2. 多样性控制 - Greedy/MMR 算法避免同类型堆砌")
    print("  3. 观影时间预测 - 匹配用户空闲时段的电影时长")
    print("  4. 冷启动人口统计学推荐 + 快速探索")
    print("  5. 宣发费用历史均值+电影热度预估填充")
    print("  6. 层次聚类 + 动态决定聚类数")

    try:
        movies_df, users_df, ratings_df, boxoffice_df = test_data_generation()

        recommender = test_recommender_basic(ratings_df, users_df, movies_df)

        cold_recommender = test_cold_start(ratings_df, users_df, movies_df)

        seq_recommender = test_sequence_recommendation(ratings_df, users_df, movies_df)

        div_recommender = test_diversity_control(ratings_df, users_df, movies_df)

        runtime_recommender = test_runtime_recommendation(ratings_df, users_df, movies_df)

        predictor = test_boxoffice_prediction(movies_df, boxoffice_df)

        analyzer = test_preference_analysis(ratings_df, movies_df, users_df)

        print_section("系统测试完成")
        print("\n所有模块测试通过！")
        print("\n启动 FastAPI 服务命令: python main.py")
        print("API 文档地址: http://localhost:8000/docs")
        print("\n新增 API 接口:")
        print("  GET /api/recommend/{user_id}/sequence - 序列感知推荐")
        print("  GET /api/recommend/{user_id}/diverse - 多样性控制推荐")
        print("  GET /api/recommend/{user_id}/runtime - 按时长推荐")
        print("  GET /api/user/{user_id}/sequence-analysis - 观影序列分析")
        print("  GET /api/user/{user_id}/watch-time - 观影时间模式分析")
        print("  GET /api/features - 系统功能列表")

    except Exception as e:
        print(f"\n测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
