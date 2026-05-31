#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏关卡难度预测系统 - 分群建模版
"""

import os
import sys
import argparse
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.features.data_generator import (
    generate_full_dataset, save_datasets, load_datasets,
    SKILL_GROUPS, SKILL_GROUP_ORDER
)
from src.features.preprocessing import FEATURE_COLUMNS, FeatureEngineer, prepare_single_prediction
from src.models.xgboost_model import (
    GroupedDifficultyModel, train_grouped_pipeline
)
from src.analysis.difficulty_scorer import DifficultyScorer
from src.analysis.dynamic_difficulty import DynamicDifficultyAdjuster, PlayerPerformance
from src.analysis.level_generator import LevelGenerator, GenerationConstraints
from src.analysis.churn_prediction import ChurnPredictor, PlayerBehaviorData


def parse_args():
    parser = argparse.ArgumentParser(description='游戏关卡难度预测系统 - 增强版')
    parser.add_argument(
        '--mode', 
        type=str, 
        default='web',
        choices=['web', 'train', 'analyze', 'full', 'test_grouping', 
                 'test_dynamic', 'test_generation', 'test_churn', 'test_all_new'],
        help='运行模式'
    )
    parser.add_argument(
        '--n_levels', 
        type=int, 
        default=200,
        help='生成关卡数量'
    )
    parser.add_argument(
        '--n_players', 
        type=int, 
        default=1000,
        help='生成玩家数量'
    )
    parser.add_argument(
        '--retrain', 
        action='store_true',
        help='是否重新训练模型'
    )
    return parser.parse_args()


def run_full_pipeline(n_levels: int = 200, n_players: int = 1000, 
                      retrain: bool = True):
    print("=" * 70)
    print("🎮 游戏关卡难度预测系统 - 分群建模版 - 完整流程")
    print("=" * 70)
    
    print("\n📊 步骤1: 生成游戏数据（含玩家分群和行为特征）...")
    df_levels, df_players = generate_full_dataset(
        n_levels=n_levels, 
        n_players=n_players,
        random_state=42
    )
    save_datasets(df_levels, df_players)
    print(f"✅ 生成 {len(df_levels)} 个关卡数据和 {len(df_players)} 条玩家记录")
    print(f"  特征列数: {len(df_levels.columns)}")
    print(f"  玩家分群: {df_players['skill_group'].value_counts().to_dict()}")
    
    print("\n🤖 步骤2: 训练分群模型...")
    model, data_by_group = train_grouped_pipeline(
        df_levels, FEATURE_COLUMNS, use_actual=True, model_dir="models"
    )
    print("✅ 分群模型训练完成并保存")
    
    print("\n📈 步骤3: 分群难度评分测试...")
    scorer = DifficultyScorer(target_completion_rate=0.6, target_avg_attempts=4.0)
    
    sample_idx = 0
    sample_row = df_levels.iloc[sample_idx]
    sample_params = sample_row[FEATURE_COLUMNS].to_dict()
    
    engineer = data_by_group[SKILL_GROUP_ORDER[0]]['engineer']
    X = prepare_single_prediction(sample_params, engineer)
    
    predictions_by_group = model.predict_single_all_groups(X)
    
    print(f"\n测试关卡参数: {sample_params}")
    print(f"\n各分群预测结果:")
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        pred = predictions_by_group[group]
        
        completion_rate = pred.get(
            f'actual_{group}_completion_rate',
            pred.get(f'{group}_completion_rate', 0)
        )
        avg_attempts = pred.get(
            f'actual_{group}_avg_attempts',
            pred.get(f'{group}_avg_attempts', 0)
        )
        
        score = scorer.calculate_score(
            completion_rate, avg_attempts,
            sample_params, sample_row, group
        )
        
        print(f"\n  {group_name}:")
        print(f"    通关率: {completion_rate:.1%}, 平均尝试: {avg_attempts:.1f}")
        print(f"    难度评分: {score.score:.1f}/100 ({score.rating})")
        
        if score.behavioral_score:
            print(f"    挫败指数: {score.behavioral_score.frustration_index:.2f}")
            print(f"    愤怒流失率: {score.behavioral_score.rage_quit_rate:.1%}")
        
        print(f"    调整建议: {len(score.recommendations)} 条")
        for rec in score.recommendations[:1]:
            print(f"      - {rec['title']}")
            if 'quantified_adjustments' in rec:
                for adj in rec['quantified_adjustments'][:1]:
                    print(f"        * {adj['feature_name']}: {adj['current_value_str']} "
                          f"→ {adj['suggested_value_str']} "
                          f"({adj['action']}{adj['adjustment_percent']:.0f}%)")
    
    print("\n" + "=" * 70)
    print("🎉 完整流程执行完成!")
    print("=" * 70)
    print("\n📋 输出文件:")
    print("  - data/level_data.csv - 关卡数据（含分群指标和行为特征）")
    print("  - data/player_data.csv - 玩家数据（含技能分群）")
    print("  - models/model_novice.pkl - 新手玩家模型")
    print("  - models/model_intermediate.pkl - 普通玩家模型")
    print("  - models/model_expert.pkl - 高手玩家模型")
    print("  - models/feature_engineer.pkl - 特征工程器")
    print("\n🚀 运行 'streamlit run app.py' 启动网页界面")
    
    return model, data_by_group


def test_grouping_feature(n_levels: int = 50, n_players: int = 200):
    print("=" * 70)
    print("🧪 分群建模功能测试")
    print("=" * 70)
    
    print("\n📊 生成数据...")
    df_levels, df_players = generate_full_dataset(
        n_levels=n_levels, n_players=n_players, random_state=42
    )
    
    print("\n📈 行为特征检查:")
    behavioral_cols = [c for c in df_levels.columns if any(
        x in c for x in ['frustration', 'rage_quit', 'death_zone', 'death_concentration']
    )]
    print(f"  行为特征列数: {len(behavioral_cols)}")
    print(f"  前10个: {behavioral_cols[:10]}")
    
    print("\n👥 玩家分群分布:")
    group_dist = df_players['skill_group'].value_counts()
    for group, count in group_dist.items():
        print(f"  {SKILL_GROUPS[group]['name']}: {count} 人")
    
    print("\n🎯 各分群难度差异:")
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        comp_col = f'{group}_completion_rate'
        att_col = f'{group}_avg_attempts'
        if comp_col in df_levels.columns:
            print(f"  {group_name}:")
            print(f"    平均通关率: {df_levels[comp_col].mean():.1%}")
            print(f"    平均尝试次数: {df_levels[att_col].mean():.1f}")
    
    print("\n🤖 训练分群模型...")
    model, data_by_group = train_grouped_pipeline(
        df_levels, FEATURE_COLUMNS, use_actual=True, model_dir="models"
    )
    
    print("\n📊 各模型性能:")
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        data = data_by_group[group]
        metrics = model.models[group].evaluate(data['X_test'], data['y_test'])
        
        print(f"\n  {group_name}:")
        for target, m in metrics.items():
            print(f"    {target}: R²={m['r2']:.4f}, MAE={m['mae']:.4f}")
    
    print("\n💡 测试量化建议:")
    scorer = DifficultyScorer()
    
    sample_idx = 5
    sample_row = df_levels.iloc[sample_idx]
    sample_params = sample_row[FEATURE_COLUMNS].to_dict()
    
    engineer = data_by_group[SKILL_GROUP_ORDER[0]]['engineer']
    X = prepare_single_prediction(sample_params, engineer)
    
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        pred = model.predict_single_group(X, group)
        
        completion_rate = pred.get(
            f'actual_{group}_completion_rate',
            pred.get(f'{group}_completion_rate', 0)
        )
        avg_attempts = pred.get(
            f'actual_{group}_avg_attempts',
            pred.get(f'{group}_avg_attempts', 0)
        )
        
        score = scorer.calculate_score(
            completion_rate, avg_attempts,
            sample_params, sample_row, group
        )
        
        if score.recommendations and 'quantified_adjustments' in score.recommendations[0]:
            adj = score.recommendations[0]['quantified_adjustments']
            if adj:
                print(f"\n  {group_name} 量化调整建议:")
                adj_df = scorer.format_quantified_table(adj)
                print(adj_df.to_string(index=False))
                break
    
    print("\n✅ 分群功能测试完成!")


def train_only(n_levels: int = 200, n_players: int = 1000):
    print("=" * 70)
    print("🤖 分群模型训练模式")
    print("=" * 70)
    
    print("\n📊 生成数据...")
    df_levels, df_players = generate_full_dataset(
        n_levels=n_levels, n_players=n_players, random_state=42
    )
    save_datasets(df_levels, df_players)
    
    print("\n🤖 训练分群模型...")
    model, data_by_group = train_grouped_pipeline(
        df_levels, FEATURE_COLUMNS, use_actual=True, model_dir="models"
    )
    
    print("\n✅ 训练完成!")
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        data = data_by_group[group]
        metrics = model.models[group].evaluate(data['X_test'], data['y_test'])
        print(f"\n  {group_name}:")
        for target, m in metrics.items():
            print(f"    {target}: R²={m['r2']:.4f}")
    
    return model, data_by_group


def test_dynamic_difficulty():
    print("=" * 70)
    print("⚙️  动态难度调整功能测试")
    print("=" * 70)
    
    adjuster = DynamicDifficultyAdjuster(
        target_completion_rate=0.6,
        target_avg_attempts=4.0
    )
    
    print("\n1️⃣  模拟玩家表现数据...")
    performance = PlayerPerformance(
        player_id="Player_001",
        skill_group="novice",
        completion_rate=0.35,
        avg_attempts=8.5,
        recent_attempts=[5, 8, 3, 10, 12, 2, 7, 9, 11, 13],
        recent_completions=[False, False, True, False, False, True, False, False, False, False],
        death_zones={
            'obstacle_zone': 12,
            'enemy_zone': 8,
            'platform_zone': 5,
            'time_zone': 3,
            'moving_zone': 10,
        },
        play_duration=15.5,
        timestamp=pd.Timestamp.now().timestamp()
    )
    
    print(f"  玩家: {performance.player_id} ({SKILL_GROUPS[performance.skill_group]['name']})")
    print(f"  当前通关率: {performance.completion_rate:.1%}, 平均尝试: {performance.avg_attempts:.1f}")
    
    current_params = {
        'obstacle_density': 0.35,
        'time_limit': 90,
        'enemy_count': 12,
        'platform_gap': 2.0,
        'moving_obstacle_ratio': 0.4,
        'powerup_count': 1,
        'checkpoint_count': 1,
        'level_length': 180,
    }
    
    print("\n2️⃣  生成动态调整建议...")
    result = adjuster.adjust_difficulty(performance, current_params)
    
    print(f"  风险等级: {result.risk_level}, 调整强度: {result.adjustment_strength:.0%}")
    print(f"  预期通关率: {result.expected_outcome['new_completion_rate']:.1%} "
          f"(变化: {result.expected_outcome['total_completion_change']:+.1f}%)")
    print(f"  预期尝试次数: {result.expected_outcome['new_avg_attempts']:.1f} "
          f"(变化: {result.expected_outcome['total_attempts_change']:+.1f})")
    
    if result.adjustments:
        print(f"\n  量化调整建议 ({len(result.adjustments)} 条):")
        for adj in result.adjustments[:3]:
            print(f"    - {adj.feature_name}: {adj.action} {adj.adjustment_percent:.0f}% "
                  f"({adj.current_value:.3f} → {adj.suggested_value:.3f})")
            print(f"      原因: {adj.reason}")
            print(f"      预期: 通关率{adj.expected_impact['completion_rate_change']:+.1f}%, "
                  f"尝试{adj.expected_impact['avg_attempts_change']:+.1f}次")
    else:
        print("\n  ✅ 当前难度设置合理，无需调整")
    
    print("\n3️⃣  蒙特卡洛模拟调整效果...")
    simulation = adjuster.simulate_adjustment_impact(performance, current_params)
    print(f"  模拟预期通关率: {simulation['mean_completion']:.1%} "
          f"(90% CI: {simulation['lower_completion']:.1%} ~ {simulation['upper_completion']:.1%})")
    print(f"  调整成功概率: {simulation['success_probability']:.0%}")
    
    print("\n✅ 动态难度调整功能测试完成!")


def test_level_generation():
    print("=" * 70)
    print("🎲 关卡自动生成功能测试")
    print("=" * 70)
    
    generator = LevelGenerator()
    
    print("\n1️⃣  测试单关卡生成...")
    constraints = GenerationConstraints(
        min_obstacle_density=0.1,
        max_obstacle_density=0.4,
        require_powerups=True,
        require_checkpoints=True
    )
    
    level = generator.generate_level(
        target_difficulty=0.5,
        skill_group="intermediate",
        level_type="balanced",
        constraints=constraints,
        level_id="Test_001",
        max_attempts=50
    )
    
    if level:
        print(f"  ✅ 生成关卡: {level.level_id}")
        print(f"  类型: {level.level_type} ({level.target_skill_group})")
        print(f"  预期通关率: {level.predicted_metrics['completion_rate']:.1%}")
        print(f"  预期尝试次数: {level.predicted_metrics['avg_attempts']:.1f}")
        print(f"  难度评分: {level.difficulty_score:.1f}/100 ({level.difficulty_rating})")
        print(f"  生成质量: {level.generation_score:.0%}")
        
        print(f"\n  关卡参数:")
        for feat, val in level.params.items():
            print(f"    {feat}: {val}")
        
        print(f"\n  行为风险:")
        print(f"    挫败指数: {level.behavioral_risk['frustration_index']:.2f}")
        print(f"    愤怒流失率: {level.behavioral_risk['rage_quit_rate']:.1%}")
    else:
        print("  ❌ 未能生成满足条件的关卡")
    
    print("\n2️⃣  测试批量多样化生成...")
    levels = generator.generate_multiple_levels(
        n_levels=5,
        target_difficulty=0.5,
        skill_group="intermediate",
        constraints=constraints,
        diverse=True
    )
    
    print(f"  ✅ 成功生成 {len(levels)} 个多样化关卡")
    for lvl in levels:
        print(f"    - {lvl.level_id}: {lvl.level_type} | "
              f"通关率 {lvl.predicted_metrics['completion_rate']:.0%} | "
              f"质量 {lvl.generation_score:.0%}")
    
    print("\n3️⃣  测试难度曲线生成...")
    curve_levels = generator.generate_level_curve(
        n_levels=5,
        start_difficulty=0.2,
        end_difficulty=0.8,
        skill_group="intermediate",
        curve_type="linear"
    )
    
    print(f"  ✅ 成功生成 {len(curve_levels)} 个关卡的难度曲线")
    for i, lvl in enumerate(curve_levels):
        print(f"    {i+1}. 难度 {lvl.target_difficulty:.2f} | "
              f"评分 {lvl.difficulty_score:.1f} | "
              f"通关率 {lvl.predicted_metrics['completion_rate']:.0%}")
    
    print("\n✅ 关卡自动生成功能测试完成!")


def test_churn_prediction():
    print("=" * 70)
    print("⚠️  流失预警功能测试")
    print("=" * 70)
    
    predictor = ChurnPredictor()
    
    print("\n1️⃣  模拟高风险玩家数据...")
    player_data = PlayerBehaviorData(
        player_id="Risk_Player_001",
        skill_group="novice",
        level_id="Level_042",
        completion_rate=0.25,
        avg_attempts=10.5,
        play_duration=8.0,
        recent_completions=[False, False, False, False, True, False, False, False, False, False],
        recent_attempts=[8, 12, 10, 15, 3, 15, 12, 10, 8, 14],
        death_zones={
            'obstacle_zone': 15,
            'enemy_zone': 12,
            'platform_zone': 8,
            'time_zone': 5,
            'moving_zone': 18,
        },
        frustration_events=10,
        consecutive_failures=6,
        rage_quits=3,
        session_count=8,
        days_since_last_play=3,
        total_play_time=12.5,
        level_difficulty=0.75,
        timestamp=pd.Timestamp.now().timestamp()
    )
    
    print(f"  玩家: {player_data.player_id}")
    print(f"  通关率: {player_data.completion_rate:.1%}, 尝试: {player_data.avg_attempts:.1f}")
    print(f"  连续失败: {player_data.consecutive_failures}次, 愤怒退出: {player_data.rage_quits}次")
    print(f"  挫败事件: {player_data.frustration_events}次")
    
    print("\n2️⃣  分析流失风险...")
    result = predictor.predict_churn(player_data)
    
    print(f"\n  流失概率: {result.churn_probability:.1%}")
    print(f"  风险等级: {result.risk_level} (高/中/低)")
    print(f"  干预优先级: {result.intervention_priority}")
    print(f"  预期留存改善: {result.expected_retention_impact:.0%}")
    
    print(f"\n  风险因素贡献:")
    for name, val in result.feature_contributions.items():
        bar = "█" * int(val * 20)
        print(f"    {name}: {bar} {val:.0%}")
    
    if result.warnings:
        print(f"\n  风险警告 ({len(result.warnings)} 条):")
        for w in result.warnings[:3]:
            urgency = {'immediate': '🚨 立即', 'high': '⚡ 高', 'medium': '⚠️  中', 'low': 'ℹ️  低'}[w.urgency]
            print(f"    {urgency}: {w.message}")
            print(f"      建议: {w.suggested_action}")
    
    print(f"\n3️⃣  留存策略建议:")
    strategy = result.retention_strategy
    if strategy['immediate_actions']:
        print(f"  🔴 立即执行:")
        for action in strategy['immediate_actions'][:2]:
            print(f"    - {action['action']}: {action['target']}")
            print(f"      预期: {action['expected_impact']}")
    if strategy['short_term_actions']:
        print(f"  🟡 短期执行:")
        for action in strategy['short_term_actions'][:1]:
            print(f"    - {action['action']}: {action['target']}")
    
    print("\n4️⃣  测试批量风险检测...")
    players_list = []
    np.random.seed(42)
    
    for i in range(20):
        group = np.random.choice(SKILL_GROUP_ORDER, p=[0.3, 0.5, 0.2])
        diff = np.random.uniform(0.2, 0.9)
        comp = np.random.uniform(0.1, 0.9)
        
        player = PlayerBehaviorData(
            player_id=f"Batch_{i+1:03d}",
            skill_group=group,
            level_id=f"Level_{np.random.randint(1, 50):03d}",
            completion_rate=comp,
            avg_attempts=np.random.uniform(1, 12),
            play_duration=np.random.uniform(5, 60),
            recent_completions=[bool(np.random.random() < comp) for _ in range(8)],
            recent_attempts=[np.random.randint(1, 15) for _ in range(8)],
            death_zones={k: np.random.randint(0, 15) for k in 
                        ['obstacle_zone', 'enemy_zone', 'platform_zone', 'time_zone', 'moving_zone']},
            frustration_events=np.random.randint(0, 12) if diff > 0.7 else np.random.randint(0, 3),
            consecutive_failures=np.random.randint(0, 8) if diff > 0.7 and comp < 0.3 else np.random.randint(0, 3),
            rage_quits=np.random.randint(0, 4) if diff > 0.7 and comp < 0.3 else np.random.randint(0, 1),
            session_count=np.random.randint(1, 30),
            days_since_last_play=np.random.randint(0, 15),
            total_play_time=np.random.uniform(1, 50),
            level_difficulty=diff,
            timestamp=pd.Timestamp.now().timestamp()
        )
        players_list.append(player)
    
    at_risk = predictor.identify_at_risk_players(players_list, min_risk_level='medium')
    
    print(f"  分析了 {len(players_list)} 名玩家")
    print(f"  发现 {len(at_risk)} 名中高风险玩家")
    
    dist = predictor.get_risk_distribution(predictor.batch_predict(players_list))
    print(f"    高风险: {dist['high_risk_count']}人 ({dist['high_risk_percent']:.1f}%)")
    print(f"    中风险: {dist['medium_risk_count']}人 ({dist['medium_risk_percent']:.1f}%)")
    print(f"    低风险: {dist['low_risk_count']}人 ({dist['low_risk_percent']:.1f}%)")
    
    if at_risk:
        print(f"\n  Top 5 高风险玩家:")
        for r in at_risk[:5]:
            dominant = r.risk_factors.get_dominant_factors(0.6)
            top_factor = dominant[0][0] if dominant else "综合"
            print(f"    - {r.player_id}: {r.churn_probability:.0%} 流失风险, 主要: {top_factor}")
    
    print("\n✅ 流失预警功能测试完成!")


def test_all_new_features():
    print("=" * 70)
    print("🧪 所有新功能完整测试")
    print("=" * 70)
    
    try:
        test_dynamic_difficulty()
        test_level_generation()
        test_churn_prediction()
        
        print("\n" + "=" * 70)
        print("🎉 所有新功能测试通过!")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    args = parse_args()
    
    if args.mode == 'web':
        print("🚀 启动Streamlit网页界面...")
        print("📝 运行命令: streamlit run app.py")
        os.system("streamlit run app.py")
    
    elif args.mode == 'train':
        train_only(
            n_levels=args.n_levels,
            n_players=args.n_players
        )
    
    elif args.mode == 'test_grouping':
        test_grouping_feature(
            n_levels=args.n_levels,
            n_players=args.n_players
        )
    
    elif args.mode == 'full':
        run_full_pipeline(
            n_levels=args.n_levels,
            n_players=args.n_players,
            retrain=args.retrain
        )
    
    elif args.mode == 'analyze':
        print("分析模式: 请使用网页界面或 test_grouping 模式")
    
    elif args.mode == 'test_dynamic':
        test_dynamic_difficulty()
    
    elif args.mode == 'test_generation':
        test_level_generation()
    
    elif args.mode == 'test_churn':
        test_churn_prediction()
    
    elif args.mode == 'test_all_new':
        test_all_new_features()


if __name__ == "__main__":
    main()
