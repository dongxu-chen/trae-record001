import sys
import time
import random
import json
from datetime import datetime
from typing import List, Dict

from src import (
    ClickLog,
    FeatureExtractor,
    PublisherThresholdManager,
    PublisherLimitManager,
    FraudScorerV2,
    ActionExecutorV2,
    GradedPenaltyManager
)


def generate_mock_click(publisher_id: str = None, fraud_type: str = None) -> ClickLog:
    base_time = time.time()
    
    if publisher_id is None:
        publisher_id = random.choice(['pub_1', 'pub_2', 'pub_3', 'pub_default'])
    
    if fraud_type == 'high_frequency':
        ip = "192.168.255.100"
        device_id = "device_fraud_001"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    elif fraud_type == 'bot':
        ip = "10.0.0.50"
        device_id = "device_fraud_002"
        user_agent = "curl/7.68.0"
    else:
        ip = f"192.168.{random.randint(0, 200)}.{random.randint(0, 255)}"
        device_id = f"device_normal_{random.randint(1, 1000)}"
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        ])

    return ClickLog(
        click_id=f"click_{int(base_time * 1000)}_{random.randint(1000, 9999)}",
        timestamp=datetime.fromtimestamp(base_time),
        ip=ip,
        device_id=device_id,
        user_agent=user_agent,
        publisher_id=publisher_id,
        campaign_id=f"camp_{random.randint(1, 5)}",
        ad_id=f"ad_{random.randint(1, 20)}",
        referrer=f"https://example{random.randint(1, 10)}.com",
        session_id=f"session_{random.randint(1, 10000)}" if random.random() > 0.1 else None,
    )


def demo_publisher_thresholds():
    print("=" * 70)
    print("演示1: 发布商独立阈值配置")
    print("=" * 70)

    threshold_mgr = PublisherThresholdManager()
    
    print("\n当前发布商阈值配置:")
    print(f"  {'发布商ID':<15} {'欺诈阈值':<12} {'IP频控上限':<12} {'设备频控上限':<12}")
    print("  " + "-" * 55)
    
    limit_mgr = PublisherLimitManager()
    
    for pub_id in ['pub_1', 'pub_2', 'pub_3', 'pub_default', 'unknown_pub']:
        threshold = threshold_mgr.get_threshold(pub_id)
        ip_limit = limit_mgr.get_high_freq_ip_limit(pub_id)
        device_limit = limit_mgr.get_high_freq_device_limit(pub_id)
        print(f"  {pub_id:<15} {threshold:<12.2f} {ip_limit:<12d} {device_limit:<12d}")

    print("\n✓ 发布商独立阈值配置加载成功")


def simulate_fraud_attacks(attack_type: str, publisher_id: str, num_clicks: int = 50) -> List[Dict]:
    print(f"\n模拟 {attack_type} 攻击 (发布商: {publisher_id}, {num_clicks} 次点击)...")
    
    feature_extractor = FeatureExtractor()
    fraud_scorer = FraudScorerV2(use_redis=False)
    
    results = []
    base_time = time.time()
    
    for i in range(num_clicks):
        if attack_type == '高频点击':
            click = ClickLog(
                click_id=f"attack_{i}",
                timestamp=datetime.fromtimestamp(base_time + i * 0.05),
                ip="192.168.99.99",
                device_id="attack_device_001",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                publisher_id=publisher_id,
                campaign_id="camp_1",
                ad_id="ad_1",
                referrer="https://example.com",
                session_id="attack_session_001"
            )
        else:
            click = generate_mock_click(publisher_id=publisher_id, fraud_type='bot')
        
        features = feature_extractor.extract_features(click)
        assessment = fraud_scorer.assess(click, features)
        results.append({
            'click_id': click.click_id,
            'score': assessment.final_fraud_score,
            'threshold': assessment.publisher_threshold,
            'is_fraud': assessment.is_fraud,
            'action': assessment.penalty_level.name,
            'action_type': assessment.penalty_level.action.value,
            'penalty_rate': assessment.penalty_level.penalty_rate,
            'triggered_rules': assessment.triggered_rules,
            'repeat_count': assessment.repeat_offense_count,
            'is_escalated': assessment.is_escalated
        })
    
    return results


def demo_graded_penalty():
    print("\n" + "=" * 70)
    print("演示2: 分级处罚与阶梯处理")
    print("=" * 70)

    penalty_mgr = GradedPenaltyManager()
    
    print("\n分级处罚配置:")
    print(f"  {'级别':<6} {'名称':<10} {'动作':<18} {'分数范围':<15} {'扣量比例':<10}")
    print("  " + "-" * 60)
    
    for level in penalty_mgr.penalty_levels:
        print(f"  {level.level:<6} {level.name:<10} {level.action.value:<18} "
              f"{level.score_min:.2f}-{level.score_max:<11.2f} {level.penalty_rate:<10.0%}")

    print("\n处罚升级规则:")
    print(f"  - 违规次数 >= {penalty_mgr.max_offenses} 次自动升级处罚级别")
    print(f"  - 违规统计窗口: {penalty_mgr.repeat_offense_window / 3600:.1f} 小时")
    print(f"  - 升级级别数: {penalty_mgr.escalation_levels} 级")

    print("\n✓ 分级处罚配置加载成功")


def demo_attack_simulation():
    print("\n" + "=" * 70)
    print("演示3: 高频点击攻击模拟与分级处置")
    print("=" * 70)

    results = simulate_fraud_attacks('高频点击', 'pub_1', num_clicks=50)
    
    print("\n检测结果统计:")
    
    action_stats = {}
    for r in results:
        action = r['action_type']
        action_stats[action] = action_stats.get(action, 0) + 1
    
    print(f"  {'动作类型':<18} {'次数':<8} {'占比':<10}")
    print("  " + "-" * 40)
    for action, count in sorted(action_stats.items()):
        print(f"  {action:<18} {count:<8} {count/len(results)*100:>7.1f}%")

    print("\n点击明细 (前15次):")
    print(f"  {'序号':<6} {'欺诈分数':<12} {'阈值':<8} {'处罚级别':<12} {'扣量比例':<10} {'屡犯次数':<8}")
    print("  " + "-" * 60)
    
    for i, r in enumerate(results[:15]):
        escalated_mark = "*" if r['is_escalated'] else ""
        print(f"  {i+1:<6} {r['score']:<12.2f} {r['threshold']:<8.2f} "
              f"{r['action']:<12} {r['penalty_rate']:<10.0%} {r['repeat_count']:<8}{escalated_mark}")
    
    if any(r['is_escalated'] for r in results):
        print("\n* 标记表示因屡犯被加重处罚")

    print("\n✓ 高频攻击模拟完成")


def demo_different_publishers():
    print("\n" + "=" * 70)
    print("演示4: 不同发布商的差异化检测")
    print("=" * 70)

    feature_extractor = FeatureExtractor()
    fraud_scorer = FraudScorerV2(use_redis=False)

    publishers = ['pub_1', 'pub_2', 'pub_3']
    
    print("\n不同发布商检测对比 (相同欺诈流量):")
    print(f"  {'发布商':<12} {'欺诈阈值':<10} {'IP频控上限':<12} {'检测为欺诈':<12} {'平均处罚级别':<15}")
    print("  " + "-" * 60)
    
    for pub_id in publishers:
        attack_ip = f"192.168.100.{publishers.index(pub_id)}"
        fraud_count = 0
        total_penalty_level = 0
        
        for i in range(30):
            click = ClickLog(
                click_id=f"test_{pub_id}_{i}",
                timestamp=datetime.fromtimestamp(time.time() + i * 0.1),
                ip=attack_ip,
                device_id=f"device_{pub_id}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                publisher_id=pub_id,
                campaign_id="camp_1",
                ad_id="ad_1",
                referrer="https://example.com",
                session_id=f"session_{pub_id}"
            )
            features = feature_extractor.extract_features(click)
            assessment = fraud_scorer.assess(click, features)
            
            if assessment.is_fraud:
                fraud_count += 1
            total_penalty_level += assessment.penalty_level.level
        
        threshold = fraud_scorer.threshold_manager.get_threshold(pub_id)
        ip_limit = fraud_scorer.rule_engine.publisher_limit_manager.get_high_freq_ip_limit(pub_id)
        avg_penalty = total_penalty_level / 30
        
        penalty_name = fraud_scorer.penalty_manager.penalty_levels[
            min(int(avg_penalty), len(fraud_scorer.penalty_manager.penalty_levels)-1)
        ].name
        
        print(f"  {pub_id:<12} {threshold:<10.2f} {ip_limit:<12} {fraud_count:<12} {penalty_name:<15}")

    print("\n✓ 不同发布商差异化检测验证完成")


def demo_repeat_offense_escalation():
    print("\n" + "=" * 70)
    print("演示5: 屡犯加重处罚机制")
    print("=" * 70)

    feature_extractor = FeatureExtractor()
    fraud_scorer = FraudScorerV2(use_redis=False)
    
    attack_ip = "192.168.200.200"
    publisher_id = "pub_1"
    
    print(f"\n模拟同一IP多次违规 (IP: {attack_ip}):")
    print(f"  {'轮次':<8} {'欺诈分数':<12} {'违规次数':<10} {'处罚级别':<15} {'是否升级':<10}")
    print("  " + "-" * 55)
    
    for round_num in range(5):
        for i in range(15):
            click = ClickLog(
                click_id=f"round{round_num}_{i}",
                timestamp=datetime.fromtimestamp(time.time() + round_num * 100 + i * 0.1),
                ip=attack_ip,
                device_id="escalation_device",
                user_agent="curl/7.68.0",
                publisher_id=publisher_id,
                campaign_id="camp_1",
                ad_id="ad_1",
                referrer="https://example.com",
                session_id=f"session_{round_num}"
            )
            features = feature_extractor.extract_features(click)
            assessment = fraud_scorer.assess(click, features)
            
            if assessment.is_fraud:
                escalated = "是" if assessment.is_escalated else "否"
                print(f"  {round_num+1:<8} {assessment.final_fraud_score:<12.2f} "
                      f"{assessment.repeat_offense_count:<10} {assessment.penalty_level.name:<15} {escalated:<10}")
                break

    print("\n✓ 屡犯加重处罚机制验证完成")


def main():
    print("\n" + "=" * 70)
    print("广告点击欺诈检测系统 v2.0 - 增强功能演示")
    print("=" * 70)
    print("\n新增功能:")
    print("  1. 发布商独立阈值配置 - 不同发布商差异化检测标准")
    print("  2. Redis频控聚合 - 跨节点统一计数，分布式部署")
    print("  3. 分级处罚机制 - 观察/扣量/强扣量/拦截 四级处理")
    print("  4. 屡犯加重处罚 - 多次违规自动升级处罚级别")

    demos = [
        ("发布商独立阈值配置", demo_publisher_thresholds),
        ("分级处罚与阶梯处理", demo_graded_penalty),
        ("高频点击攻击模拟与分级处置", demo_attack_simulation),
        ("不同发布商的差异化检测", demo_different_publishers),
        ("屡犯加重处罚机制", demo_repeat_offense_escalation),
    ]

    print("\n可用演示:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. 运行全部演示")

    try:
        choice = input("\n请选择演示 (0-5, 默认运行全部): ").strip()
        choice = int(choice) if choice else 0

        if choice == 0:
            for name, demo_func in demos:
                try:
                    demo_func()
                except Exception as e:
                    print(f"\n✗ {name} 出错: {e}")
                    import traceback
                    traceback.print_exc()
        elif 1 <= choice <= len(demos):
            demos[choice - 1][1]()
        else:
            print("无效选择")
    except KeyboardInterrupt:
        print("\n演示被中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("增强功能演示结束！")
    print("=" * 70)
    print("\n新增模块:")
    print("  - threshold_manager.py: 发布商阈值管理器")
    print("  - rule_engine_v2.py: Redis频控聚合规则引擎")
    print("  - fraud_scorer_v2.py: 分级处罚欺诈评分器")


if __name__ == "__main__":
    main()
