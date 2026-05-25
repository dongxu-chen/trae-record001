import sys
import os
import time
import json
import random
from unittest.mock import patch, MagicMock

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config

def setup_mock_redis(mock_redis_instance):
    mock_redis_instance.get_budget.return_value = None
    mock_redis_instance.set_budget.return_value = True
    mock_redis_instance.get_remaining_budget.return_value = 10000.0
    mock_redis_instance.get_hourly_remaining.return_value = 1000.0
    mock_redis_instance.get_pace.return_value = 1.0
    mock_redis_instance.get_cached_prediction.return_value = None
    mock_redis_instance.cache_prediction.return_value = True
    mock_redis_instance.check_all_frequency_limits.return_value = (True, [])
    mock_redis_instance.check_sliding_window_limits.return_value = (True, [], {"1h": 0, "6h": 0, "24h": 0, "7d": 0})
    mock_redis_instance.get_frequency.return_value = 0
    mock_redis_instance.get_sliding_window_count.return_value = 0
    mock_redis_instance.get_sliding_window_timestamps.return_value = []
    mock_redis_instance.add_impression_sliding_window.return_value = (1, True, 0)
    mock_redis_instance.record_impression_sliding_window.return_value = ({"1h": 1, "6h": 1, "24h": 1, "7d": 1}, {"1h": True, "6h": True, "24h": True, "7d": True})
    mock_redis_instance.increment_frequency.return_value = True
    mock_redis_instance._get_sliding_window_key.return_value = "freq:sw:user1:ad1:1h"
    mock_redis_instance.record_bid.return_value = True
    mock_redis_instance.get_bid_history.return_value = None
    mock_redis_instance.consume_budget.return_value = True
    mock_redis_instance.consume_hourly_budget.return_value = True
    mock_redis_instance.get_user_profile.return_value = None
    mock_redis_instance.save_user_profile.return_value = True
    mock_redis_instance.clear_all.return_value = True
    mock_redis_instance.delete_key.return_value = True
    mock_redis_instance.get_all_keys.return_value = []
    mock_redis_instance.set_hourly_budget.return_value = True
    mock_redis_instance.update_pace.return_value = True
    
    def mock_get_client():
        class MockRedis:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def get(self, key):
                return b'1000.0' if 'hourly' in key else None
            def setex(self, key, ttl, value):
                return True
            def incr(self, key):
                return 1
            def expire(self, key, ttl):
                return True
            def pipeline(self):
                class MockPipeline:
                    def incr(self, key):
                        pass
                    def expire(self, key, ttl):
                        pass
                    def execute(self):
                        return [1, True]
                    def hset(self, key, field, value):
                        pass
                    def hsetnx(self, key, field, value):
                        pass
                    def hincrbyfloat(self, key, field, value):
                        pass
                    def hget(self, key, field):
                        return b'10000.0'
                    def hgetall(self, key):
                        return {b'total': b'10000.0', b'spent': b'0.0'}
                    def decrbyfloat(self, key, value):
                        pass
                    def zremrangebyscore(self, key, min_val, max_val):
                        pass
                    def zadd(self, key, mapping):
                        pass
                    def zcard(self, key):
                        return 0
                    def zcount(self, key, min_val, max_val):
                        return 0
                    def zrangebyscore(self, key, min_val, max_val):
                        return []
                    def eval(self, script, num_keys, *args):
                        return [1, 0]
                return MockPipeline()
            def hset(self, key, field, value):
                return 1
            def hgetall(self, key):
                return {b'total': b'10000.0', b'spent': b'0.0'}
            def hget(self, key, field):
                return b'10000.0' if field == b'total' else b'0.0'
            def hincrbyfloat(self, key, field, value):
                return 0.0 + value
            def decrbyfloat(self, key, value):
                return 100.0 - value
            def zremrangebyscore(self, key, min_val, max_val):
                return 0
            def zadd(self, key, mapping):
                return 1
            def zcard(self, key):
                return 0
            def zcount(self, key, min_val, max_val):
                return 0
            def zrangebyscore(self, key, min_val, max_val):
                return []
            def eval(self, script, num_keys, *args):
                return [0, 0]
            def keys(self, pattern):
                return []
            def delete(self, key):
                return 1
            def flushdb(self):
                pass
        return MockRedis()
    
    mock_redis_instance.get_client.side_effect = mock_get_client
    
    def mock_get_layer_budget(layer_name, campaign_id):
        return {
            'allocated': 1000.0,
            'spent': random.uniform(0, 500),
            'impressions': random.randint(0, 100),
            'clicks': random.randint(0, 10),
        }
    mock_redis_instance.get_layer_budget.side_effect = mock_get_layer_budget
    
    def mock_get_traffic_layer_stats(layer_name, campaign_id):
        return {
            "allocated": 1000.0,
            "spent": random.uniform(0, 100),
            "value": random.uniform(800, 950),
            "impressions": random.randint(0, 100),
            "clicks": random.randint(0, 10),
        }
    mock_redis_instance.get_traffic_layer_stats.side_effect = mock_get_traffic_layer_stats
    
    def mock_set_traffic_layer_counter(layer_name, campaign_id, amount):
        return True
    mock_redis_instance.set_traffic_layer_counter.side_effect = mock_set_traffic_layer_counter
    
    def mock_consume_layer_budget(layer_name, campaign_id, amount):
        return True
    mock_redis_instance.consume_layer_budget.side_effect = mock_consume_layer_budget
    
    mock_redis_instance.record_layer_impression.return_value = True
    mock_redis_instance.record_layer_click.return_value = True
    mock_redis_instance.record_layer_cost.return_value = True


def reset_redis_singleton():
    try:
        from src.redis_client import RedisClient
        RedisClient._instance = None
        RedisClient._pool = None
    except ImportError:
        pass


def demo_exploration_mechanism():
    print("\n" + "="*70)
    print("【功能1】探索机制演示 - ε-greedy + UCB 多臂老虎机")
    print("="*70)
    
    from src.exploration import ExplorationEngine, ExplorationStrategy, BiddingStrategy
    
    print("\n▶ 初始化探索引擎 (UCB策略)...")
    engine = ExplorationEngine(
        strategy=ExplorationStrategy.UCB,
        epsilon=0.2,
        ucb_c=2.0,
        min_trials_for_exploitation=5,
    )
    
    print(f"  可用策略: {engine.get_available_strategies()}")
    print(f"  初始探索率: {engine.get_exploration_rate():.2%}")
    
    print("\n▶ 模拟100轮竞价，收集各策略表现...")
    random.seed(42)
    
    strategy_performance = {name: [] for name in engine.get_available_strategies()}
    
    for i in range(100):
        strategy_name, strategy, details = engine.select_strategy()
        is_exploration = details["is_exploration"]
        
        reward = random.uniform(0, 2.0) if strategy_name == "balanced" else random.uniform(0, 1.5)
        if strategy_name == "aggressive" and i > 30:
            reward = random.uniform(1.0, 3.0)
        
        success = reward > 0.5
        engine.record_result(strategy_name, reward, success)
        strategy_performance[strategy_name].append(reward)
        
        if (i + 1) % 20 == 0:
            print(f"\n  第 {i+1} 轮后统计:")
            summary = engine.get_strategy_summary()
            print(f"    总试验次数: {summary['total_trials']}")
            print(f"    探索次数: {summary['exploration_trials']}")
            print(f"    利用次数: {summary['exploitation_trials']}")
            print(f"    当前最佳策略: {summary['best_strategy']}")
            print(f"    当前探索率: {summary['exploration_rate']:.2%}")
            
            top = engine.get_top_strategies(top_n=3)
            print(f"    Top 3策略:")
            for name, value in top:
                trials = summary['strategies'][name]['trials']
                print(f"      - {name}: {value:.4f} (试验{trials}次)")
    
    print("\n▶ 探索热度分布:")
    heatmap = engine.get_exploration_heatmap()
    for strategy, count in sorted(heatmap.items(), key=lambda x: -x[1]):
        bar = "█" * int(count / 3)
        print(f"  {strategy:20s} {count:3d}次 {bar}")
    
    print("\n▶ 保存探索状态...")
    state = engine.save_state()
    print(f"  状态已保存，包含 {len(state['strategies'])} 个策略的统计数据")
    
    print("\n✅ 探索机制演示完成！")
    return engine


def demo_auction_simulator():
    print("\n" + "="*70)
    print("【功能2】广告竞拍模拟器演示 - 离线回放与策略优化")
    print("="*70)
    
    from src.auction_simulator import AuctionSimulator, AuctionResult
    from src.bid_engine import BidEngine
    
    print("\n▶ 初始化竞拍模拟器...")
    bid_engine = BidEngine("demo_campaign", enable_exploration=True)
    simulator = AuctionSimulator(
        bid_engine=bid_engine,
        num_competitors=5,
        random_seed=42,
    )
    
    print(f"  竞争对手数量: {simulator.num_competitors}")
    print(f"  竞争对手: {[c.name for c in simulator.competitors]}")
    for i, comp in enumerate(simulator.competitors):
        print(f"    - {comp.name}: strategy={comp.strategy}, multiplier={comp.bid_multiplier:.2f}")
    
    print("\n▶ 运行500次竞拍模拟...")
    start_time = time.time()
    
    def progress_callback(count, record, stats):
        elapsed = time.time() - start_time
        rate = count / elapsed if elapsed > 0 else 0
        print(f"\r  进度: {count}/500 | 胜率: {stats.win_rate:.2%} | 利润: ${stats.total_profit:.2f} | 速度: {rate:.0f}/s", end="")
    
    stats = simulator.run_simulation(
        num_auctions=500,
        callback=progress_callback,
        batch_size=50,
    )
    
    print("\n\n▶ 模拟结果统计:")
    print(f"  总竞拍次数: {stats.total_auctions}")
    print(f"  获胜次数: {stats.auctions_won} ({stats.win_rate:.2%})")
    print(f"  失败次数: {stats.auctions_lost}")
    print(f"  跳过次数: {stats.auctions_skipped}")
    print(f"  总花费: ${stats.total_cost:.2f}")
    print(f"  总收入: ${stats.total_revenue:.2f}")
    print(f"  总利润: ${stats.total_profit:.2f}")
    print(f"  点击数: {stats.total_clicks} (CTR: {stats.ctr:.2%})")
    print(f"  转化数: {stats.total_conversions} (CVR: {stats.cvr:.2%})")
    print(f"  平均出价: ${stats.avg_bid:.4f}")
    print(f"  ROAS: {stats.roas:.2f}x")
    
    print("\n▶ 各出价策略表现对比:")
    comparison = simulator.get_strategy_comparison()
    print(f"  {'策略':20s} {'试验':>5} {'胜率':>8} {'CTR':>8} {'CVR':>8} {'利润':>10} {'ROAS':>8}")
    print("  " + "-"*70)
    for strategy, metrics in sorted(comparison.items(), key=lambda x: -x[1]["total_profit"]):
        print(f"  {strategy:20s} {metrics['trials']:5d} {metrics['win_rate']:7.2%} {metrics['ctr']:7.2%} {metrics['cvr']:7.2%} ${metrics['total_profit']:9.2f} {metrics['roas']:7.2f}x")
    
    print("\n▶ 各流量层表现:")
    print(f"  {'层级':>4} {'试验':>5} {'获胜':>5} {'花费':>10} {'收入':>10} {'利润':>10}")
    print("  " + "-"*55)
    for layer, metrics in sorted(stats.layer_stats.items()):
        if metrics["trials"] > 0:
            print(f"  {layer:>4} {metrics['trials']:5d} {metrics['wins']:5d} ${metrics['cost']:9.2f} ${metrics['revenue']:9.2f} ${metrics['profit']:9.2f}")
    
    print("\n▶ 导出竞拍历史 (JSON)...")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        filepath = f.name
    exported = simulator.export_history(filepath=filepath, limit=100)
    print(f"  已导出 {len(exported)} 条记录到: {filepath}")
    
    print("\n▶ 离线回放验证 (回放前50条)...")
    replay_stats = simulator.run_replay(exported[:50])
    print(f"  回放下果: {replay_stats.total_auctions} 次竞拍, 利润 ${replay_stats.total_profit:.2f}")
    
    os.unlink(filepath)
    
    print("\n✅ 竞拍模拟器演示完成！")
    return simulator


def demo_auto_tuner():
    print("\n" + "="*70)
    print("【功能3】Optuna自动调参演示 - 搜索最优出价参数")
    print("="*70)
    
    try:
        from src.auto_tuner import AutoTuner, TuningResult, OptimizationMetric
    except ImportError as e:
        print(f"\n❌ Optuna未安装，跳过自动调参演示: {e}")
        print("  安装命令: pip install optuna")
        return None
    
    print("\n▶ 初始化自动调参器...")
    tuner = AutoTuner(
        metric="total_profit",
        direction="maximize",
        n_trials=5,
        random_seed=42,
        sampler_type="random",
        pruner_type="none",
    )
    
    print(f"  优化目标: 最大化 {tuner.metric}")
    print(f"  试验次数: {tuner.n_trials}")
    print(f"  采样算法: Random (快速演示模式)")
    print(f"  剪枝算法: None")
    
    print("\n▶ 待优化参数范围:")
    for param in tuner.parameter_ranges:
        if param.param_type == "categorical":
            print(f"  - {param.name}: {param.choices}")
        else:
            step_info = f", step={param.step}" if param.step else ""
            log_info = f", log scale" if param.log else ""
            print(f"  - {param.name}: [{param.low}, {param.high}]{step_info}{log_info}")
    
    print("\n▶ 开始参数搜索 (每次试验运行100次竞拍模拟)...")
    start_time = time.time()
    
    def tuning_callback(trial_num, params, value):
        elapsed = time.time() - start_time
        print(f"\r  试验 {trial_num+1}/{tuner.n_trials}: 利润=${value:.2f}", end="")
    
    result = tuner.optimize(callback=tuning_callback)
    
    print(f"\n\n▶ 调参完成！耗时: {result.duration:.1f}秒")
    print(f"\n  最佳参数组合:")
    for param, value in sorted(result.best_params.items()):
        print(f"    {param}: {value}")
    print(f"\n  最佳{result.metric}: ${result.best_value:.2f}")
    
    print("\n▶ 生成最优出价策略:")
    optimal_strategy = tuner.generate_optimal_strategy(result, name="demo_optimal")
    for key, value in optimal_strategy.items():
        print(f"    {key}: {value}")
    
    print("\n▶ 各试验结果 (Top 5):")
    top_trials = sorted(result.trial_results, key=lambda x: -x["value"])[:5]
    print(f"  {'试验':>4} {'利润':>10} {'bid_mult':>8} {'ctr_w':>6} {'cvr_w':>6} {'策略':>12}")
    print("  " + "-"*60)
    for trial in top_trials:
        p = trial["params"]
        print(f"  {trial['trial_number']:4d} ${trial['value']:9.2f} {p.get('bid_base_multiplier','-'):>8} {p.get('ctr_weight','-'):>6.2f} {p.get('cvr_weight','-'):>6.2f} {p.get('exploration_strategy','-'):>12}")
    
    print("\n▶ 保存最优参数...")
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        filepath = f.name
    result.save(filepath)
    print(f"  已保存到: {filepath}")
    
    print("\n▶ 应用最优参数到系统配置...")
    tuner.apply_best_params(result)
    print("  配置已更新！")
    
    os.unlink(filepath)
    
    print("\n✅ 自动调参演示完成！")
    return tuner, result


def main():
    reset_redis_singleton()
    
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*20 + "RTB高级功能综合演示" + " "*24 + "║")
    print("║" + " "*15 + "探索机制 | 竞拍模拟 | 自动调参" + " "*20 + "║")
    print("╚" + "═"*68 + "╝")
    
    print("\n" + "▌" + " "*3 + "系统信息:")
    print(f"  • Python版本: {sys.version.split()[0]}")
    print(f"  • 配置文件: config.py")
    
    config.exploration.enabled = True
    config.simulator.num_competitors = 5
    config.auto_tuner.n_trials = 10
    config.auto_tuner.timeout = 120
    
    try:
        demo_exploration_mechanism()
        demo_auction_simulator()
        demo_auto_tuner()
        
        print("\n" + "="*70)
        print("🎉 所有高级功能演示完成！")
        print("="*70)
        print("\n📊 核心功能总结:")
        print("  1. ✅ 探索机制 - 多臂老虎机算法(UCB/ε-greedy/Thompson/Boltzmann)")
        print("     - 7种预置出价策略，支持自定义添加")
        print("     - 自动探索-利用平衡，避免局部最优")
        print("     - 支持状态持久化与恢复")
        print("\n  2. ✅ 竞拍模拟器 - 离线A/B测试平台")
        print("     - 多竞争对手模拟，4种竞争策略")
        print("     - 点击/转化概率建模，真实竞拍流程")
        print("     - 历史数据回放，策略离线验证")
        print("\n  3. ✅ 自动调参 - Optuna贝叶斯优化")
        print("     - 11维参数空间搜索")
        print("     - TPE采样 + Median剪枝，高效搜索")
        print("     - 最优参数一键应用到生产配置")
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    reset_redis_singleton()
    
    _redis_patch = patch('src.redis_client.RedisClient')
    _mock_redis = _redis_patch.start()
    _mock_redis_instance = MagicMock()
    _mock_redis.return_value = _mock_redis_instance
    
    try:
        setup_mock_redis(_mock_redis_instance)
        main()
    finally:
        _redis_patch.stop()
