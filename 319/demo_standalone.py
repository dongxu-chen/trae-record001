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

def reset_redis_singleton():
    try:
        from src.redis_client import RedisClient
        RedisClient._instance = None
        RedisClient._pool = None
    except ImportError:
        pass

reset_redis_singleton()

redis_patch = patch('src.redis_client.RedisClient')
mock_redis = redis_patch.start()
mock_redis_instance = MagicMock()
mock_redis.return_value = mock_redis_instance

def setup_mock_redis():
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

setup_mock_redis()

from src.bid_engine import BidEngine, BidRequest
from src.data_generator import DataGenerator
from src.prediction_model import PredictionModel

def run_demo():
    print("=" * 70)
    print("  实时竞价广告出价系统 - 功能演示")
    print("  Real-Time Bidding (RTB) System Demo")
    print("=" * 70)
    
    data_generator = DataGenerator()
    
    print("\n📊 第1步: 创建XGBoost预测模型")
    print("-" * 70)
    predictor = PredictionModel()
    print("  ✓ CTR预测模型已加载")
    print("  ✓ CVR预测模型已加载")
    
    print("\n📈 第2步: 模型特征重要性分析")
    print("-" * 70)
    ctr_importance = predictor.get_feature_importance("ctr")
    print("\n  CTR模型Top 5重要特征:")
    for i, (feat, imp) in enumerate(sorted(ctr_importance.items(), key=lambda x: -x[1])[:5], 1):
        bar = "█" * int(imp * 50)
        print(f"    {i}. {feat:20s} {imp:.4f} {bar}")
    
    cvr_importance = predictor.get_feature_importance("cvr")
    print("\n  CVR模型Top 5重要特征:")
    for i, (feat, imp) in enumerate(sorted(cvr_importance.items(), key=lambda x: -x[1])[:5], 1):
        bar = "█" * int(imp * 50)
        print(f"    {i}. {feat:20s} {imp:.4f} {bar}")
    
    print("\n🎯 第3步: 初始化出价引擎")
    print("-" * 70)
    engine = BidEngine(campaign_id="demo_campaign_001")
    print("  ✓ 出价引擎初始化完成")
    print(f"  ✓ 活动ID: demo_campaign_001")
    
    print("\n🔍 第4步: 系统配置信息")
    print("-" * 70)
    status = engine.get_engine_status()
    print(f"\n  预算配置:")
    print(f"    总预算: ${status['budget_status']['total_budget']:.2f}")
    print(f"    已消耗: ${status['budget_status']['total_spent']:.2f}")
    print(f"    剩余预算: ${status['budget_status']['remaining_total']:.2f}")
    print(f"    使用率: {status['budget_status']['utilization_rate']*100:.1f}%")
    print(f"    节奏调整: {status['budget_status']['pace_adjustment']:.2f}x")
    
    print(f"\n  流量价值分层配置:")
    for name, perf in status['traffic_layers'].items():
        multiplier = engine.traffic_layer.get_layer_multiplier(name)
        share = engine.traffic_layer.get_layer_budget_share(name) * 100
        bar = "█" * int(share / 2)
        print(f"    {name}层: 出价倍率={multiplier:.1f}x, 预算占比={share:.0f}% {bar}")
        if perf.get('ctr', 0) > 0:
            print(f"          CTR={perf.get('ctr', 0):.4f}, CVR={perf.get('cvr', 0):.4f}, 消耗=${perf.get('cost', 0):.2f}")
    
    print("\n💰 第5步: 实时竞价处理演示 (30个请求)")
    print("-" * 70)
    print(f"\n  {'#':>3} {'用户':<10} {'层级':<6} {'CTR':<8} {'CVR':<8} {'出价':<10} {'状态':<10} 详情")
    print("  " + "-" * 95)
    
    results = []
    successful_bids = 0
    total_spend = 0.0
    layer_stats = {'S': {'count': 0, 'spend': 0.0}, 'A': {'count': 0, 'spend': 0.0}, 
                   'B': {'count': 0, 'spend': 0.0}, 'C': {'count': 0, 'spend': 0.0}}
    
    for i in range(30):
        user_id = f"user_{random.randint(0, 999):03d}"
        user_profile = data_generator.generate_user_profile(user_id)
        context = data_generator.generate_context()
        ad_info = data_generator.generate_ad_info(f"ad_{random.randint(0, 50):02d}")
        
        freq_1h = random.randint(0, 3)
        freq_6h = random.randint(0, 5)
        freq_24h = random.randint(0, 8)
        freq_7d = random.randint(0, 10)
        mock_redis_instance.get_sliding_window_count.return_value = freq_24h
        mock_redis_instance.get_sliding_window_timestamps.return_value = [
            int(time.time() * 1000) - 3600000 * i for i in range(freq_24h)
        ]
        if random.random() < 0.1:
            mock_redis_instance.check_sliding_window_limits.return_value = (
                False, ["24h"], {"1h": freq_1h, "6h": freq_6h, "24h": 15, "7d": freq_7d}
            )
        else:
            mock_redis_instance.check_sliding_window_limits.return_value = (
                True, [], {"1h": freq_1h, "6h": freq_6h, "24h": freq_24h, "7d": freq_7d}
            )
        
        bid_request = BidRequest(
            request_id=f"req_{i:04d}",
            user_id=user_id,
            ad_id=ad_info["ad_id"],
            campaign_id="demo_campaign_001",
            user_profile=user_profile,
            context=context,
            ad_info=ad_info,
            floor_price=0.01,
            cpa_goal=20.0,
        )
        
        response = engine.process_bid(bid_request)
        results.append(response)
        
        status_icon = "✓" if response.success else "✗"
        layer = response.details.get('traffic_layer', 'N/A')
        ctr = response.details.get('ctr', 0)
        cvr = response.details.get('cvr', 0)
        bid_price = response.bid_price
        
        if response.success:
            successful_bids += 1
            total_spend += bid_price
            layer_stats[layer]['count'] += 1
            layer_stats[layer]['spend'] += bid_price
            status_str = "SUCCESS"
            color_start = "\033[92m"
            color_end = "\033[0m"
        else:
            status_str = response.reason[:10]
            color_start = "\033[91m"
            color_end = "\033[0m"
        
        detail = ""
        if 'LAYER' in response.reason:
            detail = "层预算不足"
        elif 'FREQUENCY' in response.reason:
            detail = "频次超限"
        elif 'BUDGET' in response.reason:
            detail = "预算不足"
        elif 'FLOOR' in response.reason:
            detail = "低于底价"
        
        print(f"  {color_start}{i+1:>3} {user_id:<10} {layer:<6} {ctr:<8.4f} {cvr:<8.4f} ${bid_price:<9.4f} {status_str:<10} {detail}{color_end}")
        time.sleep(0.05)
    
    print("\n" + "=" * 70)
    print("  📊 竞价结果统计")
    print("=" * 70)
    
    print(f"\n  整体统计:")
    print(f"    总请求数: {len(results)}")
    print(f"    成功出价: {successful_bids} ({successful_bids/len(results)*100:.1f}%)")
    print(f"    拒绝出价: {len(results) - successful_bids} ({(len(results)-successful_bids)/len(results)*100:.1f}%)")
    print(f"    总消耗: ${total_spend:.4f}")
    print(f"    平均出价: ${total_spend/successful_bids:.4f}" if successful_bids > 0 else "    平均出价: N/A")
    
    print(f"\n  流量分层统计:")
    for layer in ['S', 'A', 'B', 'C']:
        stats = layer_stats[layer]
        if successful_bids > 0:
            pct = stats['count'] / successful_bids * 100
            spend_pct = stats['spend'] / total_spend * 100 if total_spend > 0 else 0
        else:
            pct = 0
            spend_pct = 0
        bar = "█" * int(pct / 2)
        print(f"    {layer}层: {stats['count']}次 ({pct:.1f}%), 消耗${stats['spend']:.4f} ({spend_pct:.1f}%) {bar}")
    
    print(f"\n  拒绝原因统计:")
    rejection_reasons = {}
    for r in results:
        if not r.success:
            reason = r.reason.split(':')[0]
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    
    if rejection_reasons:
        total_rejected = len(results) - successful_bids
        for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
            pct = count / total_rejected * 100
            bar = "█" * int(pct / 2)
            reason_cn = {
                'FREQUENCY_LIMIT_EXCEEDED': '频次超限',
                'LAYER_BUDGET_EXHAUSTED': '层预算不足',
                'HOURLY_BUDGET_EXHAUSTED': '小时预算不足',
                'BELOW_FLOOR_PRICE': '低于底价',
                'INSUFFICIENT_BUDGET': '预算不足',
            }.get(reason, reason)
            print(f"    {reason_cn}: {count}次 ({pct:.1f}%) {bar}")
    
    print("\n" + "=" * 70)
    print("  🎉 演示完成!")
    print("=" * 70)
    
    print("\n  核心功能说明:")
    print("  1. 🎯 CTR/CVR预测 - 使用XGBoost模型预测点击和转化概率")
    print("  2. 📊 流量价值分层 - S/A/B/C四层, 不同出价倍率和预算分配")
    print("  3. ⏰ 频次控制 - 多时间窗口(1h/6h/24h/7d)防过度曝光")
    print("  4. 💰 预算平滑消耗 - 小时预算分配 + 节奏控制 + 应急阈值")
    print("  5. 📈 动态出价调整 - 综合预测值、分层、频次、预算的智能出价")
    
    print("\n  技术栈:")
    print("  • Python + FastAPI - 核心服务框架")
    print("  • XGBoost - CTR/CVR预测模型")
    print("  • Redis - 用户画像、频次、预算、缓存")
    print("  • Kafka - 消息队列, 处理竞价请求/响应")
    print("  • Flink - 实时分析、预算节奏、频次监控")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        run_demo()
    finally:
        redis_patch.stop()
