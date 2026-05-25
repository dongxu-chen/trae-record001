import os
import sys

from config import Config
from index_recommender import DatabaseIndexAdvisor, create_mock_data
from visualization import (
    plot_training_curves,
    plot_index_recommendations,
    plot_column_importance
)


def example_mock_mode():
    print("=" * 70)
    print("Example 1: Running in Mock Mode (No Database Required)")
    print("=" * 70)
    
    config = Config()
    config.rl.num_episodes = 50
    config.rl.max_steps_per_episode = 15
    
    advisor = DatabaseIndexAdvisor(config, use_mock_env=True)
    
    schemas, queries = create_mock_data()
    
    report = advisor.run_full_analysis(
        custom_schemas=schemas,
        custom_queries=queries,
        num_episodes=50
    )
    
    advisor.print_report(report)
    
    report_path = os.path.join(config.output_dir, 'mock_analysis_report.json')
    report.save(report_path)
    
    advisor.close()
    
    print(f"\nReport saved to: {report_path}")
    return report


def example_with_visualization():
    print("\n" + "=" * 70)
    print("Example 2: With Training Visualization")
    print("=" * 70)
    
    config = Config()
    config.rl.num_episodes = 100
    config.rl.max_steps_per_episode = 20
    
    advisor = DatabaseIndexAdvisor(config, use_mock_env=True)
    
    schemas, queries = create_mock_data()
    
    advisor.schemas = schemas
    advisor.queries = queries
    
    advisor.analyze_existing_indexes()
    advisor.generate_candidate_indexes()
    advisor.setup_environment()
    advisor.setup_agent()
    
    training_metrics = advisor.train(num_episodes=100)
    
    report = advisor.run_full_analysis(
        custom_schemas=schemas,
        custom_queries=queries,
        num_episodes=0
    )
    
    if training_metrics.get('rewards'):
        plot_training_curves(
            training_metrics['rewards'],
            training_metrics['losses'],
            os.path.join(config.output_dir, 'training_curves.png')
        )
        print("Training curves saved to output/training_curves.png")
    
    plot_index_recommendations(
        report.rl_recommendations,
        os.path.join(config.output_dir, 'recommendations.png')
    )
    print("Recommendations plot saved to output/recommendations.png")
    
    column_scores = {}
    for table in schemas.keys():
        column_scores[table] = {}
        for query in queries:
            if table in query.tables:
                for col in query.where_columns:
                    column_scores[table][col] = column_scores[table].get(col, 0) + query.execution_time
    
    plot_column_importance(
        column_scores,
        os.path.join(config.output_dir, 'column_importance.png')
    )
    print("Column importance plot saved to output/column_importance.png")
    
    advisor.print_report(report)
    advisor.close()
    
    return report


def example_real_database():
    print("\n" + "=" * 70)
    print("Example 3: Real Database Mode (Configuration Template)")
    print("=" * 70)
    
    print("""
To use with a real database, you need to:

1. Configure database connection in config.py:
   - db_type: 'mysql' or 'postgresql'
   - host, port, user, password, database

2. Prepare slow query log file

3. Run analysis:

   config = Config()
   config.db.host = 'your-host'
   config.db.user = 'your-user'
   config.db.password = 'your-password'
   config.db.database = 'your-database'
   
   advisor = DatabaseIndexAdvisor(config, use_mock_env=False)
   
   report = advisor.run_full_analysis(
       slow_log_path='path/to/slow_query.log',
       log_type='mysql'  # or 'postgresql'
   )
   
   advisor.print_report(report)
   advisor.close()
""")


def main():
    os.makedirs('output', exist_ok=True)
    
    try:
        example_mock_mode()
    except Exception as e:
        print(f"Example 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        example_with_visualization()
    except Exception as e:
        print(f"Example 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    example_real_database()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
