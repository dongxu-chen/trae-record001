import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, IndexConfig
from database import TableSchema, ColumnInfo, IndexInfo, QueryInfo
from index_analyzer import IndexAnalyzer
from index_env import MockIndexRecommendationEnv


def test_column_order_duplicate_detection():
    print("=" * 60)
    print("Test 1: 列顺序兼容的重复索引检测")
    print("=" * 60)
    
    config = IndexConfig(use_column_order_compatibility=True)
    analyzer = IndexAnalyzer(config)
    
    idx1 = IndexInfo(name='idx_a', columns=['status', 'country', 'created_at'])
    idx2 = IndexInfo(name='idx_b', columns=['country', 'status', 'created_at'])
    idx3 = IndexInfo(name='idx_c', columns=['status', 'created_at'])
    idx4 = IndexInfo(name='idx_d', columns=['status', 'country', 'created_at'])
    
    similarity, reason = analyzer._calculate_index_similarity(idx1, idx2)
    print(f"  idx1 {idx1.columns} vs idx2 {idx2.columns}")
    print(f"    Similarity: {similarity:.2f}")
    print(f"    Reason: {reason}")
    assert similarity >= 0.9, "列集合相同应该被检测为高相似度"
    
    similarity, reason = analyzer._calculate_index_similarity(idx1, idx3)
    print(f"\n  idx1 {idx1.columns} vs idx3 {idx3.columns}")
    print(f"    Similarity: {similarity:.2f}")
    print(f"    Reason: {reason}")
    
    similarity, reason = analyzer._calculate_index_similarity(idx1, idx4)
    print(f"\n  idx1 {idx1.columns} vs idx4 {idx4.columns}")
    print(f"    Similarity: {similarity:.2f}")
    print(f"    Reason: {reason}")
    assert similarity == 1.0, "完全相同应该相似度为1"
    
    print("\n  ✓ 重复索引检测测试通过！")


def test_merge_with_column_order():
    print("\n" + "=" * 60)
    print("Test 2: 支持列顺序兼容的索引合并")
    print("=" * 60)
    
    config = IndexConfig(use_column_order_compatibility=True)
    analyzer = IndexAnalyzer(config)
    
    idx1 = IndexInfo(name='idx_a', columns=['status', 'country', 'created_at'])
    idx2 = IndexInfo(name='idx_b', columns=['country', 'status', 'created_at'])
    
    merged, benefit, reason = analyzer._try_merge_indexes([idx1, idx2])
    print(f"  合并索引:")
    print(f"    idx1: {idx1.columns}")
    print(f"    idx2: {idx2.columns}")
    print(f"  建议合并为: {merged}")
    print(f"  收益分数: {benefit:.2f}")
    print(f"  原因: {reason}")
    
    assert merged is not None, "应该能够合并列集合相同的索引"
    assert len(merged) == 3, "应该包含所有3列"
    
    print("\n  ✓ 索引合并测试通过！")


def test_state_compression():
    print("\n" + "=" * 60)
    print("Test 3: 状态压缩 - 列排序特征")
    print("=" * 60)
    
    config = Config()
    config.rl.num_episodes = 10
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=10000),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True, cardinality=5),
                ColumnInfo(name='country', data_type='varchar(50)', is_nullable=True, cardinality=50),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=9500),
            ],
            indexes=[IndexInfo(name='PRIMARY', columns=['id'], is_primary=True)],
            row_count=10000
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1 AND country = 'CN' ORDER BY created_at DESC",
            execution_time=2.5,
            rows_examined=8000,
            tables=['users'],
            where_columns=['status', 'country'],
            orderby_columns=['created_at']
        )
    ]
    
    candidate_indexes = {
        'users': [
            ['status', 'country'],
            ['status', 'created_at'],
            ['country', 'created_at'],
            ['status', 'country', 'created_at'],
        ]
    }
    
    env = MockIndexRecommendationEnv(config, schemas, queries, candidate_indexes)
    
    obs, _ = env.reset()
    
    print(f"  原始状态空间设计 (按候选索引):")
    print(f"    候选索引数量: {env.total_candidates}")
    print(f"    旧方案维度: {env.total_candidates * 10} (每个索引10维)")
    
    print(f"\n  新状态空间 (按列排序特征):")
    print(f"    列重要性排名: {env.column_rank}")
    print(f"    状态维度: {env.observation_space.shape[0]}")
    print(f"    维度组成:")
    print(f"      - 查询代价: {len(queries)} 维")
    print(f"      - 列覆盖特征: {len(env.column_rank['users']) * 2} 维 (覆盖+位置)")
    print(f"      - 索引计数: 1 维")
    print(f"      - 其他: 3 维 (步数、存储、维护代价)")
    
    print(f"\n  状态观测值形状: {obs.shape}")
    print(f"  状态观测值 (前10个): {obs[:10]}")
    
    assert obs.shape[0] == env.observation_space.shape[0]
    
    env.close()
    print("\n  ✓ 状态压缩测试通过！")


def test_reward_function():
    print("\n" + "=" * 60)
    print("Test 4: 奖励函数 - 查询代价收益 - 索引维护代价")
    print("=" * 60)
    
    config = Config()
    config.rl.num_episodes = 10
    
    schemas = {
        'users': TableSchema(
            name='users',
            columns=[
                ColumnInfo(name='id', data_type='int', is_nullable=False, cardinality=10000),
                ColumnInfo(name='status', data_type='tinyint', is_nullable=True, cardinality=5),
                ColumnInfo(name='country', data_type='varchar(50)', is_nullable=True, cardinality=50),
                ColumnInfo(name='created_at', data_type='datetime', is_nullable=False, cardinality=9500),
            ],
            indexes=[IndexInfo(name='PRIMARY', columns=['id'], is_primary=True)],
            row_count=10000
        )
    }
    
    queries = [
        QueryInfo(
            sql="SELECT * FROM users WHERE status = 1 AND country = 'CN' ORDER BY created_at DESC",
            execution_time=2.5,
            rows_examined=8000,
            tables=['users'],
            where_columns=['status', 'country'],
            orderby_columns=['created_at']
        )
    ]
    
    candidate_indexes = {
        'users': [
            ['status', 'country'],
            ['status'],
            ['status', 'country', 'created_at'],
            ['created_at'],
        ]
    }
    
    env = MockIndexRecommendationEnv(config, schemas, queries, candidate_indexes)
    
    obs, _ = env.reset()
    
    print(f"  测试不同索引的奖励:")
    print(f"  {'索引组合':<30} {'奖励':>10} {'存储代价':>12} {'维护代价':>12}")
    print("-" * 70)
    
    for action in range(len(candidate_indexes['users'])):
        obs, reward, terminated, truncated, info = env.step(action)
        
        if action < len(candidate_indexes['users']):
            idx_cols = candidate_indexes['users'][action]
            print(f"  {str(idx_cols):<30} {reward:>10.4f} "
                  f"{info['total_storage_cost']/1e6:>10.2f}MB "
                  f"{info['total_maintenance_cost']/1e3:>10.2f}")
    
    print(f"\n  奖励组成:")
    print(f"    奖励 = 查询改进 - (存储代价 * 存储权重 + 维护代价 * 维护权重)")
    print(f"    存储权重: {config.index.index_storage_cost_weight}")
    print(f"    维护权重: {config.index.index_maintenance_cost_weight}")
    
    env.close()
    print("\n  ✓ 奖励函数测试通过！")


def test_full_pipeline():
    print("\n" + "=" * 60)
    print("Test 5: 完整优化管道测试")
    print("=" * 60)
    
    from index_recommender import DatabaseIndexAdvisor, create_mock_data
    
    config = Config()
    config.rl.num_episodes = 20
    config.rl.max_steps_per_episode = 10
    config.index.use_column_order_compatibility = True
    
    advisor = DatabaseIndexAdvisor(config, use_mock_env=True)
    
    schemas, queries = create_mock_data()
    
    advisor.schemas = schemas
    advisor.queries = queries
    
    print("  运行静态分析...")
    static_result = advisor.analyze_existing_indexes()
    print(f"    发现 {len(static_result.duplicate_indexes)} 个重复索引")
    print(f"    发现 {len(static_result.merge_suggestions)} 个合并建议")
    
    print("  生成候选索引...")
    advisor.generate_candidate_indexes()
    total_candidates = sum(len(v) for v in advisor.candidate_indexes.values())
    print(f"    生成 {total_candidates} 个候选索引")
    
    print("  设置环境...")
    advisor.setup_environment()
    print(f"    环境状态维度: {advisor.env.observation_space.shape[0]}")
    print(f"    动作空间大小: {advisor.env.action_space.n}")
    
    print("  设置Agent...")
    advisor.setup_agent()
    print(f"    DQN Agent 初始化完成")
    
    print("  训练 (20 episodes)...")
    advisor.train(num_episodes=20)
    
    print("  生成推荐...")
    recommendations = advisor.get_recommendations(top_k=5)
    print(f"    推荐了 {len(recommendations)} 个索引")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec['table']}: {rec['columns']} (Q={rec['q_value']:.3f})")
    
    advisor.close()
    print("\n  ✓ 完整管道测试通过！")


def main():
    print("\n" + "#" * 60)
    print("#  数据库索引推荐工具 - 优化改进测试")
    print("#" * 60)
    
    all_passed = True
    
    try:
        test_column_order_duplicate_detection()
    except Exception as e:
        print(f"\n  ✗ 重复索引检测测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_merge_with_column_order()
    except Exception as e:
        print(f"\n  ✗ 索引合并测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_state_compression()
    except Exception as e:
        print(f"\n  ✗ 状态压缩测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_reward_function()
    except Exception as e:
        print(f"\n  ✗ 奖励函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_full_pipeline()
    except Exception as e:
        print(f"\n  ✗ 完整管道测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "#" * 60)
    if all_passed:
        print("#  ✓ 所有优化改进测试通过！")
    else:
        print("#  ✗ 部分测试失败")
    print("#" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
