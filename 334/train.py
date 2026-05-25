import os
import sys
import numpy as np
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.preprocessing import DataPreprocessor
from src.models import XGBoostModel, LSTMModel, HybridModel
from src.utils import ShapAnalyzer
from src.utils.data_generator import MovieDataGenerator


def train_pipeline(n_samples=800, model_dir='models'):
    os.makedirs(model_dir, exist_ok=True)
    
    print("="*70)
    print("电影票房预测模型训练管道")
    print("="*70)
    
    print("\n[1/6] 生成模拟训练数据...")
    generator = MovieDataGenerator(random_seed=42)
    X_raw, y = generator.generate_dataset(n_samples=n_samples)
    generator.save_dataset(X_raw, y, output_dir='data')
    
    print("\n[2/6] 数据预处理与特征工程...")
    preprocessor = DataPreprocessor(model_dir=model_dir)
    X_struct, X_ts = preprocessor.fit_transform(X_raw)
    
    print(f"结构化特征维度: {X_struct.shape}")
    print(f"时序特征维度: {X_ts.shape}")
    print(f"特征数量: {len(preprocessor.feature_names_)}")
    
    preprocessor.save('preprocessor.joblib')
    
    print("\n[3/6] 训练XGBoost模型（结构化特征）...")
    xgb_model = XGBoostModel(model_dir=model_dir, task='hybrid')
    xgb_model.fit(X_struct, y, feature_names=preprocessor.feature_names_)
    xgb_model.save('xgb_model.joblib')
    
    print("\n[4/6] 训练LSTM模型（时序预售数据）...")
    lstm_model = LSTMModel(model_dir=model_dir)
    lstm_model.fit(X_ts, y, epochs=80, batch_size=32, learning_rate=0.001)
    lstm_model.save('lstm_model.pt')
    
    print("\n[5/6] 训练混合模型融合层...")
    hybrid_model = HybridModel(xgb_model, lstm_model, model_dir=model_dir)
    hybrid_model.fit(X_struct, X_ts, y)
    hybrid_model.save('hybrid_model.joblib')
    
    print("\n[6/6] 初始化SHAP分析器...")
    shap_analyzer = ShapAnalyzer(xgb_model, feature_names=preprocessor.feature_names_)
    
    X_background = X_struct[np.random.choice(X_struct.shape[0], min(200, X_struct.shape[0]), replace=False)]
    np.save(f'{model_dir}/X_background.npy', X_background)
    
    shap_analyzer.initialize(X_background)
    
    print("\n" + "="*70)
    print("模型训练完成！")
    print("="*70)
    
    print("\n模型文件已保存:")
    print(f"  - {model_dir}/preprocessor.joblib")
    print(f"  - {model_dir}/xgb_model.joblib")
    print(f"  - {model_dir}/lstm_model.pt")
    print(f"  - {model_dir}/hybrid_model.joblib")
    print(f"  - {model_dir}/X_background.npy")
    
    print("\n特征重要性 Top 10:")
    importance = shap_analyzer.get_feature_importance(top_n=10)
    for i, item in enumerate(importance, 1):
        print(f"  {i:2d}. {item['feature']:<30} {item['importance_percent']:6.2f}%")
    
    print("\n特征分组重要性:")
    group_importance = shap_analyzer.get_feature_groups_importance()
    for item in group_importance:
        print(f"  {item['rank']}. {item['group_name']:<15} {item['importance_percent']:6.2f}%")
    
    return {
        'preprocessor': preprocessor,
        'xgb_model': xgb_model,
        'lstm_model': lstm_model,
        'hybrid_model': hybrid_model,
        'shap_analyzer': shap_analyzer
    }


def quick_predict_demo(models):
    print("\n" + "="*70)
    print("快速预测演示")
    print("="*70)
    
    daily_promotion = [200, 300, 450, 600, 800, 1000, 1200, 1400, 1050, 1000]
    
    sample_movie = {
        'title': '流浪地球3',
        'genres': ['科幻', '冒险', '动作'],
        'director': '张艺谋',
        'main_actor': '吴京',
        'release_date': '2025-02-12',
        'promotion_budget': 8000,
        'promotion_timeseries': {
            'daily_spend': daily_promotion,
            'spend_pattern': 'back_loaded',
            'total_spend': sum(daily_promotion)
        },
        'runtime': 135,
        'production_budget': 40000,
        'competition_environment': {
            'same_period_movies': 5,
            'average_competitor_budget': 3000,
            'genre_overlap_ratio': 0.3,
            'competitor_ratings': [7.5, 6.8, 8.0, 7.2, 6.5]
        },
        'pre_sales_data': {
            'total_amount': 5000,
            'daily_sales': [50, 80, 120, 180, 250, 350, 500, 700, 900, 870],
            'presale_days': 10,
            'wish_count': 500000
        }
    }
    
    preprocessor = models['preprocessor']
    hybrid_model = models['hybrid_model']
    shap_analyzer = models['shap_analyzer']
    
    X_struct, X_ts = preprocessor.transform([sample_movie])
    
    prediction = hybrid_model.predict_with_interval(X_struct, X_ts, confidence=0.9)
    
    print(f"\n电影: {sample_movie['title']}")
    print(f"类型: {', '.join(sample_movie['genres'])}")
    print(f"导演: {sample_movie['director']}")
    print(f"主演: {sample_movie['main_actor']}")
    print(f"上映日期: {sample_movie['release_date']}")
    print(f"宣发费用: {sample_movie['promotion_budget']:.0f} 万元")
    
    print(f"\n=== 预测结果 ===")
    print(f"首周票房: {prediction['point'][0, 0]:,.0f} 万元")
    print(f"  90%置信区间: [{max(0, prediction['lower'][0, 0]):,.0f}, {prediction['upper'][0, 0]:,.0f}] 万元")
    print(f"总票房: {prediction['point'][0, 1]:,.0f} 万元")
    print(f"  90%置信区间: [{max(0, prediction['lower'][0, 1]):,.0f}, {prediction['upper'][0, 1]:,.0f}] 万元")
    
    print(f"\n=== 模型贡献 ===")
    contributions = hybrid_model.get_model_contributions(X_struct, X_ts)
    for c in contributions:
        print(f"{c['target']}: XGBoost权重={c['xgb_weight']:.3f}, LSTM权重={c['lstm_weight']:.3f}")
    
    print(f"\n=== 影响因子重要性 (Top 5) ===")
    analysis = shap_analyzer.analyze_prediction(X_struct[0])
    for i, item in enumerate(analysis['global_feature_importance'][:5], 1):
        print(f"  {i}. {item['feature']:<25} {item['importance_percent']:5.2f}%")
    
    print(f"\n=== 特征分组重要性 ===")
    for item in analysis['feature_group_importance']:
        print(f"  {item['rank']}. {item['group_name']:<15} {item['importance_percent']:5.2f}%")


if __name__ == '__main__':
    models = train_pipeline(n_samples=800, model_dir='models')
    quick_predict_demo(models)
