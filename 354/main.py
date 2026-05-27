import sys
import time
import random
import json
from datetime import datetime
from typing import List, Dict

from src import (
    ClickLog,
    FeatureExtractor,
    FraudScorer,
    ActionExecutor,
    RedisStore,
    KafkaClient,
    ClickMessage,
    FlinkFraudDetector
)


def generate_mock_click_log(fraud_type: str = None) -> ClickLog:
    base_time = time.time()
    
    if fraud_type == 'high_frequency':
        ip = "192.168.1.100"
        device_id = "device_fraud_001"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    elif fraud_type == 'fixed_interval':
        ip = "10.0.0.50"
        device_id = "device_fraud_002"
        user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
    elif fraud_type == 'bot':
        ip = "172.16.0.20"
        device_id = "device_fraud_003"
        user_agent = "curl/7.68.0"
    else:
        ip = f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}"
        device_id = f"device_normal_{random.randint(1, 1000)}"
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/119.0 Firefox/119.0"
        ])

    return ClickLog(
        click_id=f"click_{int(base_time * 1000)}_{random.randint(1000, 9999)}",
        timestamp=datetime.fromtimestamp(base_time),
        ip=ip,
        device_id=device_id,
        user_agent=user_agent,
        publisher_id=f"pub_{random.randint(1, 10)}",
        campaign_id=f"camp_{random.randint(1, 5)}",
        ad_id=f"ad_{random.randint(1, 20)}",
        referrer=f"https://example{random.randint(1, 10)}.com",
        session_id=f"session_{random.randint(1, 10000)}" if random.random() > 0.1 else None,
        country=random.choice(["CN", "US", "JP", "GB", "DE"]),
        city=random.choice(["Beijing", "Shanghai", "New York", "Tokyo", "London"]),
        is_mobile=random.random() > 0.6
    )


def demo_basic_detection():
    print("=" * 60)
    print("基础欺诈检测演示")
    print("=" * 60)

    feature_extractor = FeatureExtractor()
    fraud_scorer = FraudScorer()
    action_executor = ActionExecutor()

    normal_clicks = [generate_mock_click_log() for _ in range(5)]
    high_freq_clicks = [generate_mock_click_log('high_frequency') for _ in range(5)]
    bot_clicks = [generate_mock_click_log('bot') for _ in range(2)]

    all_clicks = normal_clicks + high_freq_clicks + bot_clicks
    random.shuffle(all_clicks)

    for click in all_clicks:
        features = feature_extractor.extract_features(click)
        assessment = fraud_scorer.assess(click, features)
        action_result = action_executor.execute(assessment, click.ip, click.device_id)

        print(f"\n点击ID: {click.click_id}")
        print(f"IP: {click.ip}")
        print(f"欺诈分数: {assessment.final_fraud_score:.2f} (规则: {assessment.rule_based_score:.2f}, 异常: {assessment.anomaly_score:.2f})")
        print(f"触发规则: {assessment.triggered_rules if assessment.triggered_rules else '无'}")
        print(f"建议动作: {assessment.recommended_action.value} - {assessment.action_reason}")
        print(f"置信度: {assessment.confidence:.2f}")


def demo_redis_integration():
    print("\n" + "=" * 60)
    print("Redis 实时状态存储演示")
    print("=" * 60)

    try:
        redis_store = RedisStore()
        if not redis_store.is_connected():
            print("Redis 未连接，跳过演示")
            return

        print("Redis 连接成功！")

        for i in range(10):
            click = generate_mock_click_log()
            redis_store.record_click(
                click.click_id,
                click.ip,
                click.device_id,
                click.timestamp.timestamp()
            )

        stats = redis_store.get_stats()
        print(f"统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")

        redis_store.close()
    except Exception as e:
        print(f"Redis 演示失败: {e}")


def demo_kafka_producer():
    print("\n" + "=" * 60)
    print("Kafka 消息生产演示")
    print("=" * 60)

    try:
        kafka_client = KafkaClient()
        
        messages = []
        for i in range(10):
            click = generate_mock_click_log()
            msg = ClickMessage(
                click_id=click.click_id,
                timestamp=click.timestamp.timestamp(),
                ip=click.ip,
                device_id=click.device_id,
                user_agent=click.user_agent,
                publisher_id=click.publisher_id,
                campaign_id=click.campaign_id,
                ad_id=click.ad_id,
                referrer=click.referrer,
                session_id=click.session_id,
                user_id=click.user_id,
                country=click.country,
                city=click.city,
                is_mobile=click.is_mobile
            )
            messages.append(msg)

        success = kafka_client.send_click_log_batch(messages)
        print(f"成功发送 {success}/{len(messages)} 条消息")

        kafka_client.close()
    except Exception as e:
        print(f"Kafka 演示失败: {e}")


def demo_flink_processing():
    print("\n" + "=" * 60)
    print("Flink 流处理演示 (模拟模式)")
    print("=" * 60)

    try:
        flink_detector = FlinkFraudDetector()
        
        click_data_list = []
        for i in range(20):
            click = generate_mock_click_log()
            click_data_list.append({
                'click_id': click.click_id,
                'timestamp': click.timestamp.timestamp(),
                'ip': click.ip,
                'device_id': click.device_id,
                'user_agent': click.user_agent,
                'publisher_id': click.publisher_id
            })

        results = flink_detector.process_from_collection(click_data_list)
        
        fraud_count = sum(1 for r in results if r['is_fraud'])
        print(f"处理完成: 共 {len(results)} 条, 欺诈 {fraud_count} 条")
        
        for r in results[:5]:
            print(f"  {r['click_id']}: 分数={r['fraud_score']:.2f}, 欺诈={r['is_fraud']}, 原因={r['reasons']}")

    except Exception as e:
        print(f"Flink 演示失败: {e}")


def demo_real_time_pipeline():
    print("\n" + "=" * 60)
    print("完整实时检测流水线演示")
    print("=" * 60)
    print("模拟高频点击攻击场景...\n")

    feature_extractor = FeatureExtractor()
    fraud_scorer = FraudScorer()
    action_executor = ActionExecutor()

    fraud_ip = "192.168.255.255"
    attack_clicks = []

    base_time = time.time()
    for i in range(50):
        click = ClickLog(
            click_id=f"attack_click_{i}",
            timestamp=datetime.fromtimestamp(base_time + i * 0.1),
            ip=fraud_ip,
            device_id="attack_device_001",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            publisher_id="pub_5",
            campaign_id="camp_3",
            ad_id="ad_10",
            referrer="https://example.com",
            session_id="attack_session_001"
        )
        attack_clicks.append(click)

    print(f"模拟来自 IP {fraud_ip} 的 50 次高频点击攻击...")
    print(f"点击间隔: 100ms\n")

    blocked_count = 0
    flagged_count = 0
    allowed_count = 0

    for i, click in enumerate(attack_clicks):
        features = feature_extractor.extract_features(click)
        assessment = fraud_scorer.assess(click, features)
        
        if assessment.recommended_action.value == 'block':
            blocked_count += 1
        elif assessment.recommended_action.value == 'flag':
            flagged_count += 1
        else:
            allowed_count += 1

        if (i + 1) % 10 == 0:
            print(f"已处理 {i+1} 次点击 - 阻止: {blocked_count}, 标记: {flagged_count}, 允许: {allowed_count}")
            if assessment.triggered_rules:
                print(f"  最新点击触发规则: {assessment.triggered_rules}")
                print(f"  最新欺诈分数: {assessment.final_fraud_score:.2f}")

    print(f"\n攻击场景检测结果:")
    print(f"  总点击数: {len(attack_clicks)}")
    print(f"  阻止: {blocked_count} ({blocked_count/len(attack_clicks)*100:.1f}%)")
    print(f"  标记: {flagged_count} ({flagged_count/len(attack_clicks)*100:.1f}%)")
    print(f"  允许: {allowed_count} ({allowed_count/len(attack_clicks)*100:.1f}%)")


def main():
    print("\n广告点击欺诈检测系统 v1.0")
    print("=" * 60)

    demos = [
        ("基础欺诈检测演示", demo_basic_detection),
        ("Redis 实时状态存储演示", demo_redis_integration),
        ("Kafka 消息生产演示", demo_kafka_producer),
        ("Flink 流处理演示", demo_flink_processing),
        ("完整实时检测流水线演示", demo_real_time_pipeline),
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
                    print(f"{name} 出错: {e}")
        elif 1 <= choice <= len(demos):
            demos[choice - 1][1]()
        else:
            print("无效选择")
    except KeyboardInterrupt:
        print("\n演示被中断")
    except Exception as e:
        print(f"错误: {e}")

    print("\n演示结束！")


if __name__ == "__main__":
    main()
