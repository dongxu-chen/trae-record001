import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import load_config, get_collector, run_full_analysis
from database import DatabaseManager


def run_demo():
    print("\n" + "="*70)
    print("                    云成本优化工具 - 演示模式")
    print("="*70)
    print()
    
    config = load_config()
    collector = get_collector(config, 'mock')
    
    print("使用模拟数据进行演示分析...")
    print("(模拟15个ECS实例和8个EIP的云环境)\n")
    
    db = DatabaseManager()
    
    results = run_full_analysis(config, collector, db)
    
    print("\n" + "="*70)
    print("                          演示完成!")
    print("="*70)
    print()
    print("下一步操作:")
    print("  1. 运行 'python main.py --api' 启动API服务器")
    print("  2. 访问 http://localhost:5000/metrics 查看Prometheus指标")
    print("  3. 访问 http://localhost:5000/api/analysis 查看分析结果")
    print("  4. 导入 grafana/dashboards/cloud_cost_optimizer.json 到Grafana")
    print("  5. 运行 'python main.py --show-requests --db' 查看待审批请求")
    print()
    
    db.close()


if __name__ == '__main__':
    run_demo()
