#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统功能测试脚本 v3.0
验证新增的三个核心功能：
1. 虚假评论检测（刷单、水军、竞品恶意）
2. 评论排序优化（高质量优先展示）
3. 评论趋势监控（质量突降告警）
"""

import sys
import json
import random
from datetime import datetime, timedelta

from scoring_engine import CommentQualityScoringEngine
from user_reputation import UserHistory
from fake_review_detector import FakeReviewDetector, ReviewForDetection, FakeReviewType
from review_ranking import ReviewRanker, ReviewForRanking, SortStrategy, RankingResult
from trend_monitor import CommentTrendMonitor, AlertSeverity, AlertType


def test_fake_review_detection():
    print("=" * 80)
    print("测试 1: 虚假评论检测模块")
    print("=" * 80)
    
    detector = FakeReviewDetector(threshold=0.7)
    now = datetime.now()
    
    test_cases = [
        {
            'name': '正常评论 - 详细使用体验',
            'content': '用了两周了，整体体验不错，屏幕显示细腻，电池续航也可以，轻度使用一天没问题。拍照中规中矩，满足日常需求。',
            'rating': 4,
            'user_age': 365,
            'user_reviews': 50,
            'user_avg_rating': 4.0,
            'expected_type': FakeReviewType.LEGITIMATE,
            'should_be_fake': False
        },
        {
            'name': '刷单评论 - 关键词堆砌',
            'content': '好评好评好评！真的太赞了，超级喜欢，物美价廉，性价比很高，推荐购买，非常好，商家服务好，发货快，物流快，好评！',
            'rating': 5,
            'user_age': 7,
            'user_reviews': 3,
            'user_avg_rating': 4.9,
            'expected_type': FakeReviewType.BRUSHING,
            'should_be_fake': True
        },
        {
            'name': '刷单评论 - 超短模板',
            'content': '好评！非常好，推荐购买，物美价廉！',
            'rating': 5,
            'user_age': 2,
            'user_reviews': 1,
            'user_avg_rating': 5.0,
            'expected_type': FakeReviewType.BRUSHING,
            'should_be_fake': True
        },
        {
            'name': '竞品恶意 - 极端负面+竞品提及',
            'content': '垃圾手机，千万不要买！用了三天就坏了，质量太差了，还是买苹果吧，苹果比这个好多了，三星也不错，华为就是垃圾，骗子公司！',
            'rating': 1,
            'user_age': 15,
            'user_reviews': 8,
            'user_avg_rating': 1.5,
            'expected_type': FakeReviewType.COMPETITOR_MALICIOUS,
            'should_be_fake': True
        },
        {
            'name': '竞品恶意 - 专业差评师',
            'content': '这款手机真的太差了，完全比不上小米14。小米14的处理器更快，拍照更好，系统更流畅。而这款手机卡得要死，玩游戏掉帧严重，拍照模糊不清，系统广告一大堆。强烈建议大家去买小米，别买这个垃圾牌子。',
            'rating': 1,
            'user_age': 30,
            'user_reviews': 25,
            'user_avg_rating': 1.2,
            'expected_type': FakeReviewType.COMPETITOR_MALICIOUS,
            'should_be_fake': True
        },
        {
            'name': '正常评论 - 中等评价',
            'content': '还可以吧，性价比还行，日常使用没问题，就是偶尔会有点卡顿，拍照一般般。',
            'rating': 3,
            'user_age': 180,
            'user_reviews': 35,
            'user_avg_rating': 3.5,
            'expected_type': FakeReviewType.LEGITIMATE,
            'should_be_fake': False
        },
        {
            'name': '刷单评论 - 模板化结构',
            'content': '非常好，很满意，性价比高，值得购买',
            'rating': 5,
            'user_age': 3,
            'user_reviews': 1,
            'user_avg_rating': 5.0,
            'expected_type': FakeReviewType.BRUSHING,
            'should_be_fake': True
        }
    ]
    
    passed = 0
    for idx, case in enumerate(test_cases, 1):
        try:
            review = ReviewForDetection(
                review_id=f'TEST_{idx:03d}',
                user_id=f'USER_{idx:03d}',
                product_id='PROD_TEST',
                content=case['content'],
                rating=case['rating'],
                timestamp=now - timedelta(hours=idx),
                ip_address=f'192.168.1.{100+idx}',
                device_id=f'DEV_{idx:03d}',
                user_account_age_days=case['user_age'],
                user_total_reviews=case['user_reviews'],
                user_average_rating=case['user_avg_rating']
            )
            
            result = detector.detect(review)
            
            type_match = result.fake_type == case['expected_type']
            fake_match = result.is_fake == case['should_be_fake']
            
            status = "✓" if (type_match and fake_match) else "✗"
            print(f"\n{status} 测试 {idx}: {case['name']}")
            print(f"  内容: {case['content'][:60]}...")
            print(f"  检测类型: {result.fake_type.value} (预期: {case['expected_type'].value})")
            print(f"  是否虚假: {result.is_fake} (预期: {case['should_be_fake']})")
            print(f"  可疑分数: {result.suspicion_score:.4f}")
            print(f"  分项: 刷单={result.brushing_score:.2f} 水军={result.water_army_score:.2f} 竞品={result.competitor_score:.2f}")
            
            if result.evidence:
                print(f"  证据 ({len(result.evidence)}条):")
                for ev in result.evidence[:3]:
                    print(f"    - {ev.description}")
            
            if type_match and fake_match:
                passed += 1
            else:
                print(f"  ⚠️  检测结果与预期不符")
                
        except Exception as e:
            print(f"\n✗ 测试 {idx} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n虚假评论检测: {passed}/{len(test_cases)} 通过")
    
    print("\n" + "-" * 60)
    print("测试群组检测（水军）:")
    
    water_army_reviews = []
    for i in range(6):
        review = ReviewForDetection(
            review_id=f'WATER_{i:03d}',
            user_id=f'WATER_USER_{i:02d}',
            product_id='PROD_WATER',
            content=f"非常好，很满意，值得购买，好评{'！' * i}",
            rating=5,
            timestamp=now + timedelta(minutes=i*3),
            ip_address='10.0.0.100',
            device_id=f'WATER_DEV_{i:02d}',
            user_account_age_days=random.randint(2, 10),
            user_total_reviews=random.randint(1, 3)
        )
        water_army_reviews.append(review)
    
    group_results = detector.detect_group(water_army_reviews)
    if group_results:
        print(f"✓ 检测到 {len(group_results)} 个可疑群组")
        for g in group_results:
            print(f"  群组 {g.group_id}: 可疑度={g.suspicion_score:.2%}, 用户数={len(g.suspicious_users)}")
            for ev in g.evidence:
                print(f"    - {ev}")
        passed += 1
    else:
        print("✗ 未检测到水军群组")
    
    return passed >= len(test_cases)


def test_review_ranking():
    print("\n" + "=" * 80)
    print("测试 2: 评论排序优化模块")
    print("=" * 80)
    
    ranker = ReviewRanker()
    now = datetime.now()
    
    test_reviews = []
    review_configs = [
        ("优质长评-高信誉", 0.92, 0.90, 150, 45, 8, 12, True, 0.0, 1),
        ("优质长评-新用户", 0.88, 0.55, 140, 12, 3, 2, True, 0.0, 0),
        ("中等评论-老用户", 0.65, 0.85, 50, 78, 15, 8, False, 0.0, 7),
        ("短评-高互动", 0.55, 0.70, 25, 156, 23, 45, True, 0.0, 3),
        ("优质新评论", 0.85, 0.80, 120, 5, 1, 0, True, 0.0, 0),
        ("老评论-高有用", 0.80, 0.75, 95, 234, 45, 15, False, 0.0, 60),
        ("疑似刷单", 0.55, 0.30, 15, 0, 0, 0, False, 0.80, 1),
        ("低质量差评", 0.35, 0.40, 20, 15, 8, 4, False, 0.10, 5),
        ("中等评论", 0.62, 0.65, 45, 23, 5, 3, False, 0.0, 15),
        ("优质-已验证", 0.78, 0.88, 85, 67, 12, 6, True, 0.0, 10),
        ("极短评论", 0.45, 0.50, 8, 3, 1, 0, False, 0.0, 2),
        ("高信誉-新评论", 0.75, 0.92, 90, 3, 0, 1, True, 0.0, 0),
    ]
    
    for i, (desc, quality, rep, length, helpful, unhelpful, replies, verified, fake, days) in enumerate(review_configs):
        review = ReviewForRanking(
            review_id=f'REV_{i:03d}',
            quality_score=quality,
            user_reputation=rep,
            helpful_votes=helpful,
            unhelpful_votes=unhelpful,
            reply_count=replies,
            timestamp=now - timedelta(days=days),
            content_length=length,
            is_verified_purchase=verified,
            fake_review_score=fake
        )
        test_reviews.append(review)
    
    print(f"\n测试数据: {len(test_reviews)} 条评论")
    for i, (desc, *_) in enumerate(review_configs, 1):
        r = test_reviews[i-1]
        print(f"  {i:2d}. {desc:20s} 质量={r.quality_score:.2f} 信誉={r.user_reputation:.2f} "
              f"有用={r.helpful_votes:3d} 发布={(now - r.timestamp).days:3d}天前"
              f"{' ✓验证' if r.is_verified_purchase else ''}"
              f"{' ⚠️虚假' if r.fake_review_score > 0.5 else ''}")
    
    print("\n" + "-" * 60)
    print("测试不同排序策略:")
    
    strategies = [
        (SortStrategy.QUALITY_FIRST, "质量优先"),
        (SortStrategy.HELPFULNESS_FIRST, "有用性优先"),
        (SortStrategy.TIME_DECAY, "时间衰减"),
        (SortStrategy.BALANCED, "综合平衡"),
        (SortStrategy.NEWEST_FIRST, "最新优先"),
        (SortStrategy.MOST_HELPFUL, "最多有用"),
    ]
    
    all_passed = True
    for strategy, name in strategies:
        try:
            ranked = ranker.rank_reviews(test_reviews, strategy=strategy)
            top3_ids = [r[0].review_id for r in ranked[:3]]
            top3_scores = [f"{r[1].final_score:.3f}" for r in ranked[:3]]
            print(f"  ✓ {name}: Top3={top3_ids}, 分数={top3_scores}")
        except Exception as e:
            print(f"  ✗ {name} 失败: {e}")
            all_passed = False
    
    print("\n" + "-" * 60)
    print("测试综合平衡排序详细结果:")
    ranked = ranker.rank_reviews(test_reviews, strategy=SortStrategy.BALANCED)
    
    quality_first = ranked[0][0].quality_score
    last_quality = ranked[-1][0].quality_score
    print(f"  第一名质量分: {quality_first:.2f}, 最后一名: {last_quality:.2f}")
    
    if quality_first >= 0.85:
        print("  ✓ 高质量评论排在前面")
    else:
        print("  ⚠️  第一名质量分偏低，可能需要调整权重")
        all_passed = False
    
    fake_review_rank = None
    for i, (rev, res) in enumerate(ranked):
        if rev.fake_review_score > 0.5:
            fake_review_rank = i + 1
            break
    
    if fake_review_rank and fake_review_rank > len(test_reviews) // 2:
        print(f"  ✓ 虚假评论（#{fake_review_rank}）排在后半部分，惩罚机制生效")
    elif fake_review_rank:
        print(f"  ⚠️  虚假评论排名 #{fake_review_rank}，惩罚可能不足")
    
    print("\n" + "-" * 60)
    print("测试多样性重排:")
    ranked_with_div = ranker.rerank_with_diversity(ranked, diversity_window=5, max_same_user_in_window=1)
    
    if len(ranked_with_div) == len(test_reviews):
        print(f"  ✓ 多样性重排完成，评论数一致: {len(ranked_with_div)}")
    else:
        print("  ✗ 多样性重排后评论数不一致")
        all_passed = False
    
    print("\n" + "-" * 60)
    print("测试特征分解:")
    if ranked and ranked[0][1].features:
        top_review, top_result = ranked[0]
        print(f"  第一名评论 {top_review.review_id} 特征分解:")
        for f in sorted(top_result.features, key=lambda x: x.weight * x.normalized_value, reverse=True):
            contrib = f.weight * f.normalized_value
            bar = "█" * int(contrib * 50)
            print(f"    {f.name:<18} {bar:<50} {contrib:.4f}")
            print(f"      {f.description}")
        
        if len(top_result.features) == 6:
            print("  ✓ 特征数量正确（6个核心特征）")
        else:
            print(f"  ⚠️  特征数量异常: {len(top_result.features)}")
            all_passed = False
    else:
        print("  ✗ 特征分解失败")
        all_passed = False
    
    print(f"\n评论排序优化: {'通过' if all_passed else '失败'}")
    return all_passed


def test_trend_monitoring():
    print("\n" + "=" * 80)
    print("测试 3: 评论趋势监控模块")
    print("=" * 80)
    
    monitor = CommentTrendMonitor()
    product_id = 'TEST_PROD_001'
    now = datetime.now()
    
    print("\n阶段1: 注入正常数据（24小时，质量稳定）")
    for i in range(24):
        quality = 0.80 + random.uniform(-0.05, 0.05)
        fake_ratio = random.uniform(0.02, 0.08)
        review_count = random.randint(15, 30)
        
        monitor.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=47 - i),
            avg_rating=4.3 + random.uniform(-0.3, 0.3),
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.65 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count}
        )
    
    print("  ✓ 已注入24条正常数据点")
    
    print("\n阶段2: 注入异常数据（12小时，质量骤降）")
    for i in range(24, 36):
        hour = 47 - i
        quality = 0.80 - (i - 23) * 0.04 + random.uniform(-0.03, 0.03)
        quality = max(0.30, quality)
        fake_ratio = 0.25 + random.uniform(0, 0.15)
        review_count = random.randint(40, 60)
        avg_rating = max(2.0, 4.3 - (i - 23) * 0.15)
        
        monitor.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=hour),
            avg_rating=avg_rating,
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.40 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count, 'is_anomaly': True}
        )
        
        if i == 29:
            print(f"  小时 {hour:2d}: 质量={quality:.3f} ↓ 虚假率={fake_ratio:.1%} ↑")
    
    print("  ✓ 已注入12条异常数据点（模拟竞品攻击）")
    
    print("\n阶段3: 注入恢复数据（12小时，质量回升）")
    for i in range(36, 48):
        hour = 47 - i
        quality = 0.45 + (i - 35) * 0.03 + random.uniform(-0.03, 0.03)
        quality = min(0.85, quality)
        fake_ratio = max(0.05, 0.15 - (i - 35) * 0.01)
        review_count = random.randint(20, 35)
        avg_rating = 3.5 + (i - 35) * 0.08
        
        monitor.add_quality_data(
            product_id=product_id,
            quality_score=quality,
            timestamp=now - timedelta(hours=hour),
            avg_rating=avg_rating,
            fake_review_count=int(review_count * fake_ratio),
            fake_review_ratio=fake_ratio,
            avg_usefulness=0.55 + random.uniform(-0.1, 0.1),
            metadata={'review_count': review_count}
        )
    
    print("  ✓ 已注入12条恢复数据点")
    
    print("\n" + "-" * 60)
    print("执行趋势分析:")
    analysis = monitor.analyze_trends(product_id, time_window_hours=48)
    
    print(f"  时间范围: {analysis.time_span['start'].strftime('%H:%M')} - {analysis.time_span['end'].strftime('%H:%M')}")
    print(f"  数据点数: {analysis.statistics.get('total_data_points', 0)}")
    print(f"  平均质量: {analysis.statistics.get('avg_quality_score', 0):.4f}")
    print(f"  整体趋势: {analysis.overall_trend}")
    print(f"  趋势斜率: {analysis.trend_slope:.6f}")
    if analysis.quality_forecast:
        print(f"  下期预测: {analysis.quality_forecast:.4f}")
    
    print("\n" + "-" * 60)
    print(f"检测到 {len(analysis.alerts)} 个告警:")
    
    alert_types_found = set()
    for idx, alert in enumerate(analysis.alerts, 1):
        severity_icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡" if alert.severity == AlertSeverity.WARNING else "🔵"
        print(f"  {idx}. {severity_icon} {alert.alert_type.value}")
        print(f"     {alert.description}")
        print(f"     {alert.metric_name}: {alert.current_value:.4f} → 预期 {alert.expected_value:.4f} (阈值 {alert.threshold:.4f})")
        alert_types_found.add(alert.alert_type)
    
    expected_alerts = {
        AlertType.QUALITY_DROP,
        AlertType.FAKE_REVIEW_SURGE,
        AlertType.RATING_MANIPULATION,
        AlertType.VOLUME_ANOMALY
    }
    
    found_count = len(alert_types_found & expected_alerts)
    if found_count >= 2:
        print(f"\n  ✓ 检测到 {found_count}/{len(expected_alerts)} 种预期告警类型")
    else:
        print(f"\n  ⚠️  仅检测到 {found_count}/{len(expected_alerts)} 种预期告警类型")
    
    print("\n" + "-" * 60)
    print("测试告警管理:")
    
    active_alerts = monitor.get_active_alerts(product_id=product_id, only_unhandled=True)
    print(f"  活跃告警数: {len(active_alerts)}")
    
    if active_alerts:
        first_alert_id = active_alerts[0].alert_id
        result = monitor.mark_alert_handled(first_alert_id)
        if result:
            print(f"  ✓ 标记告警 {first_alert_id} 为已处理")
        
        remaining = monitor.get_active_alerts(product_id=product_id, only_unhandled=True)
        print(f"  剩余未处理告警: {len(remaining)}")
        
        if len(remaining) == len(active_alerts) - 1:
            print("  ✓ 告警管理功能正常")
        else:
            print("  ⚠️  告警计数异常")
    
    print("\n" + "-" * 60)
    print("测试趋势摘要:")
    summary = monitor.get_trend_summary(product_id)
    if 'current_quality' in summary:
        print(f"  ✓ 当前质量: {summary['current_quality']:.4f}")
        print(f"  ✓ 平均质量: {summary['average_quality']:.4f}")
        print(f"  ✓ 活跃告警: {summary.get('active_alerts', 0)}")
        all_passed = True
    else:
        print("  ✗ 趋势摘要获取失败")
        all_passed = False
    
    print(f"\n评论趋势监控: {'通过' if all_passed else '失败'}")
    return all_passed


def test_integration():
    print("\n" + "=" * 80)
    print("测试 4: 完整集成测试")
    print("=" * 80)
    
    engine = CommentQualityScoringEngine(
        use_bert_pretrained=False,
        enable_event_driven=True,
        enable_fake_detection=True
    )
    
    test_user = UserHistory(
        user_id='INTEG_TEST_001',
        total_comments=156,
        total_likes=3240,
        total_reports=0,
        average_likes_per_comment=20.8,
        report_rate=0.0,
        account_age_days=730,
        is_verified=True,
        level=7
    )
    
    test_comment = "这款华为Mate 60 Pro我入手一周了，体验非常好。首先是外观设计，曲面屏手感很好，素皮背面不容易沾指纹。系统是鸿蒙4.0，流畅度没得说，各种APP秒开。拍照方面，可变光圈确实很实用，白天拍照色彩鲜艳，夜景模式噪点控制得很好。续航也不错，5000mAh电池用一天完全没问题。66W快充半小时能充到70%。对比我之前用的iPhone 14，信号强太多了。"
    
    print("\n步骤1: 评论质量评分 + 虚假评论检测")
    result = engine.score_comment(
        comment_id='INTEG_001',
        comment_text=test_comment,
        user_history=test_user,
        generate_decision_tree=True
    )
    
    print(f"  ✓ 最终得分: {result.final_score:.4f} ({result.score_grade})")
    
    if result.fake_review_detection:
        print(f"  ✓ 虚假检测: {result.fake_review_detection.fake_type.value} "
              f"(分数={result.fake_review_detection.suspicion_score:.2%})")
    else:
        print("  ⚠️  未生成虚假检测结果")
    
    print("\n步骤2: 生成排序数据并排序")
    now = datetime.now()
    ranking_reviews = []
    
    for i in range(10):
        quality = random.uniform(0.4, 0.95)
        rep = random.uniform(0.3, 0.95)
        review = ReviewForRanking(
            review_id=f'RANK_INTEG_{i:03d}',
            quality_score=quality,
            user_reputation=rep,
            helpful_votes=random.randint(0, 200),
            unhelpful_votes=random.randint(0, 50),
            reply_count=random.randint(0, 20),
            timestamp=now - timedelta(days=random.randint(0, 60)),
            content_length=random.randint(10, 200),
            is_verified_purchase=random.choice([True, False]),
            fake_review_score=random.choice([0.0, 0.0, 0.0, 0.1, 0.3, 0.8])
        )
        ranking_reviews.append(review)
    
    ranked = engine.rank_reviews(ranking_reviews, strategy=SortStrategy.BALANCED)
    print(f"  ✓ 完成 {len(ranked)} 条评论排序")
    print(f"  ✓ Top1: {ranked[0][0].review_id} (质量={ranked[0][0].quality_score:.2f})")
    
    print("\n步骤3: 趋势监控数据注入与分析")
    for i in range(20):
        engine.add_quality_data(
            product_id='PROD_INTEG_001',
            quality_score=random.uniform(0.65, 0.85),
            timestamp=now - timedelta(hours=i),
            avg_rating=random.uniform(3.8, 4.5),
            fake_review_ratio=random.uniform(0.02, 0.10),
            metadata={'review_count': random.randint(10, 30)}
        )
    
    trend_summary = engine.get_trend_summary('PROD_INTEG_001', time_window_hours=24)
    print(f"  ✓ 趋势摘要: 平均质量={trend_summary.get('average_quality', 0):.4f}")
    
    print("\n步骤4: 结果导出")
    export_file = 'integration_test_result.json'
    engine.export_result_to_json(result, export_file)
    
    import os
    if os.path.exists(export_file):
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_keys = ['final_score', 'fake_review_detection', 'decision_tree_explanation']
        found_keys = [k for k in required_keys if k in data]
        
        if len(found_keys) == len(required_keys):
            print(f"  ✓ 导出JSON包含所有关键字段: {found_keys}")
        else:
            print(f"  ⚠️  缺少字段: {set(required_keys) - set(found_keys)}")
        
        os.remove(export_file)
        print(f"  ✓ 测试文件已清理")
    
    print("\n✓ 集成测试完成")
    return True


def main():
    print("=" * 80)
    print("评论质量评分系统 v3.0 - 新增功能测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    try:
        results.append(("虚假评论检测", test_fake_review_detection()))
    except Exception as e:
        print(f"\n✗ 虚假评论检测测试异常: {e}")
        import traceback
        traceback.print_exc()
        results.append(("虚假评论检测", False))
    
    try:
        results.append(("评论排序优化", test_review_ranking()))
    except Exception as e:
        print(f"\n✗ 评论排序优化测试异常: {e}")
        import traceback
        traceback.print_exc()
        results.append(("评论排序优化", False))
    
    try:
        results.append(("评论趋势监控", test_trend_monitoring()))
    except Exception as e:
        print(f"\n✗ 评论趋势监控测试异常: {e}")
        import traceback
        traceback.print_exc()
        results.append(("评论趋势监控", False))
    
    try:
        results.append(("完整集成测试", test_integration()))
    except Exception as e:
        print(f"\n✗ 集成测试异常: {e}")
        import traceback
        traceback.print_exc()
        results.append(("完整集成测试", False))
    
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    passed_count = 0
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if passed:
            passed_count += 1
    
    print()
    print(f"总计: {passed_count}/{len(results)} 项测试通过")
    
    if passed_count == len(results):
        print("\n🎉 所有v3.0新增功能测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {len(results) - passed_count} 项测试失败，请检查。")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
