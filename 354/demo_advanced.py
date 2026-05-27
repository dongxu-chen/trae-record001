#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import random
from src import (
    PublisherNetworkAnalyzer,
    HumanReviewSystem,
    AttributionAnalyzer
)

def print_separator(title=""):
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)

def demo_publisher_network():
    print_separator("演示一：发布商网络分析 - 关联作弊群组识别")
    
    analyzer = PublisherNetworkAnalyzer()
    
    publishers = [f"pub_{i:02d}" for i in range(1, 16)]
    normal_ips = [f"10.0.0.{i}" for i in range(1, 50)]
    normal_devices = [f"normal_dev_{i:03d}" for i in range(1, 40)]
    
    fraud_ips = [f"192.168.1.{i}" for i in range(1, 8)]
    fraud_devices = [f"fraud_dev_{i:02d}" for i in range(1, 6)]
    
    fraud_group_a = ["pub_01", "pub_02", "pub_03", "pub_04"]
    fraud_group_b = ["pub_08", "pub_09", "pub_10"]
    
    print("\n📊 模拟点击数据（包含2个共谋作弊群组）...")
    
    for i in range(300):
        publisher = random.choice(publishers)
        if publisher in fraud_group_a:
            ip = random.choice(fraud_ips[:5])
            device = random.choice(fraud_devices[:3])
            is_fraud = random.random() < 0.85
        elif publisher in fraud_group_b:
            ip = random.choice(fraud_ips[5:])
            device = random.choice(fraud_devices[3:])
            is_fraud = random.random() < 0.7
        else:
            ip = random.choice(normal_ips)
            device = random.choice(normal_devices)
            is_fraud = random.random() < 0.05
        
        analyzer.record_click(
            publisher_id=publisher,
            ip=ip,
            device_id=device,
            session_id=f"sess_{i % 30}",
            is_fraud=is_fraud
        )
    
    print("\n🔍 检测发布商社群...")
    communities = analyzer.detect_communities()
    
    print(f"\n✅ 共检测到 {len(communities)} 个社群:")
    for comm in communities:
        status = "⚠️ 高风险共谋群组" if comm.is_collusive else "✅ 正常社群"
        print(f"\n  社群 #{comm.community_id} [{status}]")
        print(f"    - 成员: {', '.join(comm.members)}")
        print(f"    - 平均欺诈率: {comm.avg_fraud_rate:.1%}")
        print(f"    - 总点击量: {comm.total_clicks}")
        print(f"    - 风险等级: {comm.risk_level}")
    
    suspicious = analyzer.get_suspicious_communities()
    print(f"\n🚨 发现 {len(suspicious)} 个可疑共谋群组！")
    
    print("\n🔗 发布商关联详情 (pub_01):")
    conn = analyzer.get_publisher_connections("pub_01")
    if conn:
        print(f"    欺诈率: {conn['fraud_rate']:.1%}, 风险分数: {conn['risk_score']:.1%}")
        print(f"    关联发布商数量: {conn['connection_count']}")
        if conn['connections']:
            print(f"    最强关联: {conn['connections'][0]['publisher_id']} "
                  f"(关联强度: {conn['connections'][0]['connection_strength']:.1%})")
    
    stats = analyzer.get_network_statistics()
    print(f"\n📈 网络统计:")
    print(f"    总发布商数: {stats['total_publishers']}")
    print(f"    可疑发布商: {stats['suspicious_publishers']} ({stats['suspicious_ratio']:.1%})")
    print(f"    社群总数: {stats['total_communities']}")
    print(f"    共谋群组: {stats['collusive_communities']}")
    
    return analyzer

def demo_review_system():
    print_separator("演示二：人工审核系统 - 样本复核与模型反馈")
    
    review_sys = HumanReviewSystem()
    
    publishers = [f"pub_{i:02d}" for i in range(1, 11)]
    print("\n📝 自动采样待审核样本...")
    
    for i in range(100):
        fraud_score = random.random()
        
        sample_id = review_sys.add_sample(
            click_id=f"click_{i:05d}",
            ip=f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
            device_id=f"dev_{random.randint(1,50):03d}",
            publisher_id=random.choice(publishers),
            fraud_score=fraud_score,
            predicted_action="block" if fraud_score > 0.9 else "discount" if fraud_score > 0.7 else "observe",
            rule_hits=["high_frequency", "time_pattern"][:random.randint(0,2)],
            model_features={
                'click_count': random.randint(1, 100),
                'avg_interval': random.uniform(0.1, 10),
                'entropy': random.uniform(0, 1)
            }
        )
    
    stats = review_sys.calculate_statistics()
    print(f"\n✅ 已采集待审核样本: {stats.pending_samples} 个")
    print(f"   采样率: 高风险自动采样 + 低风险随机采样")
    
    pending = review_sys.get_pending_samples(limit=5)
    print(f"\n📋 前5个待审核样本:")
    for s in pending:
        status = "🔴" if s.fraud_score > 0.8 else "🟡" if s.fraud_score > 0.5 else "🟢"
        print(f"    {status} {s.sample_id}: {s.fraud_score:.1%} - {s.publisher_id}")
    
    print(f"\n✍️  人工复核...")
    
    batch_fraud = [s.sample_id for s in pending[:3]]
    count = review_sys.batch_review(batch_fraud, "fraud", reviewer="admin")
    print(f"    批量标记欺诈: {count} 个样本")
    
    review_sys.review_sample(pending[3].sample_id, "legitimate", reviewer="admin")
    print(f"    单样本标记正常: {pending[3].sample_id}")
    
    review_sys.review_sample(pending[4].sample_id, "uncertain", reviewer="admin", notes="需要进一步核实")
    print(f"    单样本标记存疑: {pending[4].sample_id}")
    
    stats = review_sys.calculate_statistics()
    print(f"\n📊 审核统计:")
    print(f"    已审核: {stats.reviewed_samples}")
    print(f"    精确率: {stats.precision:.1%}")
    print(f"    召回率: {stats.recall:.1%}")
    print(f"    F1分数: {stats.f1_score:.1%}")
    
    print(f"\n🔄 可用于模型反馈的样本:")
    feedback = review_sys.get_feedback_data()
    print(f"    新审核样本数: {len(feedback)} 个可用于增量训练")
    
    dashboard = review_sys.get_dashboard_data()
    print(f"\n📈 分数分布:")
    for range_str, count in dashboard['score_distribution'].items():
        print(f"    {range_str}: {count} 个样本")
    
    return review_sys

def demo_attribution_analysis():
    print_separator("演示三：归因分析 - 欺诈损失评估")
    
    analyzer = AttributionAnalyzer()
    
    publishers = [f"pub_{i:02d}" for i in range(1, 11)]
    campaigns = [f"camp_{i:02d}" for i in range(1, 6)]
    
    high_fraud_pubs = ["pub_01", "pub_02", "pub_03"]
    
    print("\n💰 模拟点击与转化数据...")
    
    base_time = time.time() - 3600 * 12
    user_devices = {}
    
    for i in range(500):
        device = f"device_{random.randint(1, 100):03d}"
        ip = f"10.0.{random.randint(1,20)}.{random.randint(1,254)}"
        publisher = random.choice(publishers)
        campaign = random.choice(campaigns)
        
        if publisher in high_fraud_pubs:
            fraud_score = random.uniform(0.6, 1.0)
            is_fraud = fraud_score > 0.7
        else:
            fraud_score = random.uniform(0, 0.4)
            is_fraud = fraud_score > 0.3
        
        ts = base_time + i * 60
        
        analyzer.add_click(
            click_id=f"click_{i:05d}",
            ip=ip,
            device_id=device,
            publisher_id=publisher,
            campaign_id=campaign,
            timestamp=ts,
            fraud_score=fraud_score,
            is_fraud=is_fraud,
            action_taken="block" if is_fraud else "allow",
            cost=random.uniform(0.3, 2.0)
        )
        
        user_key = (device, campaign)
        if not is_fraud and random.random() < 0.15:
            user_devices[user_key] = ts
    
    print(f"\n🔄 运行归因匹配...")
    for (device, campaign), click_time in user_devices.items():
        ip = f"10.0.{random.randint(1,20)}.{random.randint(1,254)}"
        analyzer.add_conversion(
            conversion_id=f"conv_{len(user_devices):03d}",
            ip=ip,
            device_id=device,
            campaign_id=campaign,
            timestamp=click_time + random.uniform(60, 1800),
            revenue=random.uniform(20, 200),
            conversion_type=random.choice(["purchase", "signup", "download"])
        )
    
    analyzer.run_attribution()
    
    impact = analyzer.get_fraud_impact_summary()
    summary = impact['summary']
    
    print(f"\n📊 欺诈影响汇总:")
    print(f"    总点击数: {summary['total_clicks']}")
    print(f"    欺诈点击: {summary['fraud_clicks']} ({summary['fraud_rate']:.1%})")
    print(f"    总广告费: ¥{summary['total_cost']:.2f}")
    print(f"    欺诈浪费: ¥{summary['fraud_cost']:.2f} ({summary['fraud_cost_percentage']:.1%})")
    print(f"    归因收入: ¥{summary['total_attributed_revenue']:.2f}")
    print(f"    流失收入: ¥{summary['lost_revenue']:.2f}")
    
    print(f"\n📋 各发布商表现:")
    pub_results = analyzer.get_all_publishers_summary()
    pub_results.sort(key=lambda x: x.fraud_clicks / max(x.total_clicks, 1), reverse=True)
    
    for pub in pub_results[:5]:
        fraud_rate = pub.fraud_clicks / max(pub.total_clicks, 1)
        roi_status = "🔴" if pub.roi < 0 else "🟡" if pub.roi < 1 else "🟢"
        print(f"    {roi_status} {pub.publisher_id}: "
              f"欺诈率 {fraud_rate:.1%}, "
              f"损失 ¥{pub.fraud_cost:.2f}, "
              f"ROI {pub.roi:.2f}x")
    
    print(f"\n📈 生成建议报告...")
    report = analyzer.generate_report()
    print(f"\n💡 智能建议:")
    for rec in report['recommendations']:
        print(f"    - {rec}")
    
    print(f"\n🔍 活动归因详情 (camp_01):")
    camp_result = analyzer.calculate_campaign_attribution("camp_01")
    print(f"    总点击: {camp_result.total_clicks}")
    print(f"    欺诈: {camp_result.fraud_clicks} ({camp_result.fraud_rate:.1%})")
    print(f"    有效转化: {camp_result.legitimate_conversions}")
    print(f"    ROI: {camp_result.roi:.2f}x")
    
    return analyzer

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                     ║
║           🚀 广告欺诈检测系统 - 高级功能演示 V3.0                  ║
║                                                                     ║
║  新增功能:                                                         ║
║    1. 🕸️ 发布商网络分析 - 识别关联作弊群组                        ║
║    2. 🔍 人工审核系统 - 样本复核与反馈优化                        ║
║    3. 💰 归因分析 - 欺诈损失评估                                  ║
║    4. 🌐 Web可视化界面 - 集成所有功能                              ║
║                                                                     ║
╚═══════════════════════════════════════════════════════════════════════╝
    """)
    
    time.sleep(1)
    
    try:
        analyzer = demo_publisher_network()
        time.sleep(1)
        
        review_sys = demo_review_system()
        time.sleep(1)
        
        attr_analyzer = demo_attribution_analysis()
        
    except KeyboardInterrupt:
        print("\n\n👋 演示中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()
    
    print_separator("演示完成")
    print("""
📌 后续操作:

  1. 运行 Web 界面查看可视化效果:
     python web_app.py
     
  2. 访问 http://localhost:5000 体验:
     📊 控制台 - 系统总览
     🔍 人工审核 - 样本复核
     🕸️ 网络分析 - 社群检测
     💰 归因分析 - 损失评估
    """)

if __name__ == "__main__":
    main()
