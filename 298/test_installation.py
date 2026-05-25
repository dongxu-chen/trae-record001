import sys

def test_imports():
    print("Testing imports...")
    
    try:
        import numpy as np
        print(f"  ✓ numpy {np.__version__}")
    except ImportError as e:
        print(f"  ✗ numpy: {e}")
        return False
    
    try:
        import tensorflow as tf
        print(f"  ✓ tensorflow {tf.__version__}")
    except ImportError as e:
        print(f"  ✗ tensorflow: {e}")
        return False
    
    try:
        import gymnasium as gym
        print(f"  ✓ gymnasium {gym.__version__}")
    except ImportError as e:
        print(f"  ✗ gymnasium: {e}")
        return False
    
    try:
        import sqlparse
        print(f"  ✓ sqlparse {sqlparse.__version__}")
    except ImportError as e:
        print(f"  ✗ sqlparse: {e}")
        return False
    
    try:
        import matplotlib
        print(f"  ✓ matplotlib {matplotlib.__version__}")
    except ImportError as e:
        print(f"  ✗ matplotlib: {e}")
        return False
    
    return True


def test_local_modules():
    print("\nTesting local modules...")
    
    try:
        from config import Config
        print("  ✓ config")
    except Exception as e:
        print(f"  ✗ config: {e}")
        return False
    
    try:
        from database import TableSchema, ColumnInfo, IndexInfo, QueryInfo
        print("  ✓ database (dataclasses)")
    except Exception as e:
        print(f"  ✗ database: {e}")
        return False
    
    try:
        from query_parser import SlowQueryLogParser
        print("  ✓ query_parser")
    except Exception as e:
        print(f"  ✗ query_parser: {e}")
        return False
    
    try:
        from index_analyzer import IndexAnalyzer
        print("  ✓ index_analyzer")
    except Exception as e:
        print(f"  ✗ index_analyzer: {e}")
        return False
    
    try:
        from index_env import MockIndexRecommendationEnv
        print("  ✓ index_env")
    except Exception as e:
        print(f"  ✗ index_env: {e}")
        return False
    
    try:
        from dqn_agent import DQNAgent
        print("  ✓ dqn_agent")
    except Exception as e:
        print(f"  ✗ dqn_agent: {e}")
        return False
    
    try:
        from index_recommender import DatabaseIndexAdvisor
        print("  ✓ index_recommender")
    except Exception as e:
        print(f"  ✗ index_recommender: {e}")
        return False
    
    return True


def test_mock_run():
    print("\nTesting mock run (quick)...")
    
    try:
        from config import Config
        from index_recommender import DatabaseIndexAdvisor, create_mock_data
        
        config = Config()
        config.rl.num_episodes = 5
        config.rl.max_steps_per_episode = 5
        
        advisor = DatabaseIndexAdvisor(config, use_mock_env=True)
        schemas, queries = create_mock_data()
        
        report = advisor.run_full_analysis(
            custom_schemas=schemas,
            custom_queries=queries,
            num_episodes=5
        )
        
        print(f"  ✓ Mock run completed")
        print(f"    - Recommendations: {len(report.rl_recommendations)}")
        print(f"    - Best reward: {report.training_metrics.get('best_reward', 0):.2f}")
        
        advisor.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Mock run failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Database Index Advisor - Installation Test")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_local_modules()
    all_passed &= test_mock_run()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("  You can now run: python example_usage.py")
    else:
        print("✗ Some tests failed.")
        print("  Please install missing dependencies: pip install -r requirements.txt")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
