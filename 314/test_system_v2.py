#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统功能测试脚本 v2.0
验证新增的三个核心功能：
1. 短评数据增强
2. 事件驱动信誉更新
3. 决策树路径解释
"""

import sys
import json
from datetime import datetime, timedelta

from scoring_engine import CommentQualityScoringEngine
from user_reputation import UserHistory
from data_augmentation import TextDataAugmentor
from event_driven_reputation import EventType, EventSeverity
from decision_tree_explainer import DecisionTreeExplainer


def test_data_augmentation():
    print("=" * 70)
    print("测试 1: 短评数据增强模块")
    print("=" * 70)
    
    augmentor = TextDataAugmentor(random_seed=42)
    
    test_cases = [
        "很好，推荐购买",
        "质量不错，物流很快",
        "性价比很高，很满意",
        "太差了，不推荐",
        "一般般吧，还行"
    ]
    
    passed = 0
    for idx, text in enumerate(test_cases, 1):
        try:
            result = augmentor.augment(text=text, num_augments=5)
            
            print(f"\n✓ 测试 {idx}: {text}")
            print(f"  原始长度: {result.augmentation_stats['original_length']}")
            print(f"  生成样本: {result.augmentation_stats['num_augments_generated']}/{result.augmentation_stats['num_augments_requested']}")
            print(f"  成功率: {result.augmentation_stats['augmentation_ratio']:.1%}")
            
            if result.augmented_texts:
                print(f"  增强样本示例: {result.augmented_texts[:3]}")
            
            assert result.augmentation_stats['num_augments_generated'] >= 2
            assert len(result.methods_used) >= 1
            
            passed += 1
        except Exception as e:
            print(f"✗ 测试 {idx} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n数据增强模块测试完成: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_event_driven_reputation():
    print("\n" + "=" * 70)
    print("测试 2: 事件驱动信誉更新系统")
    print("=" * 70)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False, enable_event_driven=True)
    
    test_user = UserHistory(
        user_id='TEST_EVENT',
        total_comments=50,
        total_likes=200,
        total_reports=1,
        average_likes_per_comment=4.0,
        report_rate=0.02,
        account_age_days=180,
        is_verified=False,
        level=3
    )
    
    test_events = [
        (EventType.COMMENT_POSTED, EventSeverity.LOW, "发布评论", {'text_quality': 0.8}),
        (EventType.COMMENT_LIKED, EventSeverity.LOW, "评论获赞", {'like_count': 30, 'is_high_quality_content': True}),
        (EventType.COMMENT_REPORTED, EventSeverity.MEDIUM, "评论被举报", {'report_count': 3, 'report_reason': 'fake'}),
        (EventType.REPORT_VERIFIED, EventSeverity.HIGH, "举报核实", {'violation_type': 'fake_review', 'is_first_offense': False, 'has_prior_records': False}),
        (EventType.USER_VERIFIED, EventSeverity.MEDIUM, "用户实名认证", {'verification_type': 'identity'}),
        (EventType.APPEAL_GRANTED, EventSeverity.LOW, "申诉成功", {'original_impact': 0.10, 'restore_percentage': 0.5}),
    ]
    
    passed = 0
    current_rep = 0.75
    
    for idx, (etype, severity, desc, metadata) in enumerate(test_events, 1):
        try:
            result = engine.handle_event(
                event_type=etype,
                user_id=test_user.user_id,
                current_reputation=current_rep,
                severity=severity,
                metadata=metadata
            )
            
            print(f"\n✓ 事件 {idx}: {desc}")
            print(f"  状态: {'成功' if result.success else '失败'}")
            print(f"  原信誉: {result.old_reputation:.4f}")
            print(f"  变化量: {result.change_amount:+.4f}")
            print(f"  新信誉: {result.new_reputation:.4f}")
            print(f"  原因: {result.reason}")
            
            assert result.success == True
            assert 0 <= result.new_reputation <= 1.0
            
            current_rep = result.new_reputation
            passed += 1
            
        except Exception as e:
            print(f"✗ 事件 {idx} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n事件驱动系统测试完成: {passed}/{len(test_events)} 通过")
    return passed == len(test_events)


def test_decision_tree_explainer():
    print("\n" + "=" * 70)
    print("测试 3: 决策树路径解释模块")
    print("=" * 70)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False, enable_event_driven=True)
    explainer = DecisionTreeExplainer()
    
    test_user = UserHistory(
        user_id='TEST_TREE',
        total_comments=100,
        total_likes=2500,
        total_reports=0,
        average_likes_per_comment=25.0,
        report_rate=0.0,
        account_age_days=500,
        is_verified=True,
        level=8
    )
    
    test_comment = "这款华为Mate 60 Pro我入手一周了，体验非常好。首先是外观设计，曲面屏手感很好，素皮背面不容易沾指纹。系统是鸿蒙4.0，流畅度没得说，各种APP秒开。拍照方面，可变光圈确实很实用，白天拍照色彩鲜艳，夜景模式噪点控制得很好。续航也不错，5000mAh电池用一天完全没问题。66W快充半小时能充到70%。对比我之前用的iPhone 14，信号强太多了。"
    
    try:
        result = engine.score_comment(
            comment_id='TREE001',
            comment_text=test_comment,
            user_history=test_user,
            generate_decision_tree=True
        )
        
        print("\n✓ 评论评分完成")
        print(f"  最终得分: {result.final_score:.4f}")
        print(f"  等级: {result.score_grade}")
        
        if result.decision_tree_explanation:
            tree_result = result.decision_tree_explanation
            
            print("\n✓ 决策树生成成功")
            print(f"  根节点: {tree_result.root_node.name}")
            print(f"  子节点数: {len(tree_result.root_node.children)}")
            print(f"  决策路径数: {len(tree_result.all_paths)}")
            print(f"  特征贡献数: {len(tree_result.feature_contributions)}")
            print(f"  决策规则数: {len(tree_result.decision_rules)}")
            
            assert len(tree_result.root_node.children) == 3
            assert len(tree_result.feature_contributions) > 0
            assert len(tree_result.decision_rules) > 0
            
            print("\n✓ 特征贡献度排行 (Top 10):")
            for idx, (name, value) in enumerate(tree_result.feature_contributions.items(), 1):
                if idx <= 10:
                    print(f"    {idx:2d}. {name:<20s} {value:.4f}")
            
            print("\n✓ 决策规则示例 (前5条):")
            for idx, rule in enumerate(tree_result.decision_rules[:5], 1):
                print(f"    {idx:2d}. {rule}")
            
            passed = True
        else:
            print("✗ 决策树未生成")
            passed = False
            
    except Exception as e:
        print(f"✗ 决策树测试失败: {e}")
        import traceback
        traceback.print_exc()
        passed = False
    
    print(f"\n决策树解释模块测试完成: {'通过' if passed else '失败'}")
    return passed


def test_audit_trail():
    print("\n" + "=" * 70)
    print("测试 4: 审计追踪系统")
    print("=" * 70)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False, enable_event_driven=True)
    
    test_user = UserHistory(
        user_id='TEST_AUDIT',
        total_comments=30,
        total_likes=150,
        total_reports=2,
        average_likes_per_comment=5.0,
        report_rate=0.067,
        account_age_days=120,
        is_verified=False,
        level=2
    )
    
    current_rep = 0.65
    
    events_to_log = [
        (EventType.COMMENT_POSTED, EventSeverity.LOW, {'text_quality': 0.7}),
        (EventType.COMMENT_LIKED, EventSeverity.LOW, {'like_count': 15}),
        (EventType.COMMENT_REPORTED, EventSeverity.MEDIUM, {'report_reason': 'spam'}),
        (EventType.REPORT_VERIFIED, EventSeverity.HIGH, {'violation_type': 'spam', 'is_first_offense': True}),
    ]
    
    for etype, severity, metadata in events_to_log:
        engine.handle_event(
            event_type=etype,
            user_id=test_user.user_id,
            current_reputation=current_rep,
            severity=severity,
            metadata=metadata
        )
    
    try:
        summary = engine.get_user_event_summary(test_user.user_id)
        
        print("\n✓ 用户事件摘要:")
        print(f"  总事件数: {summary.get('total_events', 0)}")
        print(f"  当前信誉分: {summary.get('current_reputation', 0):.4f}")
        
        audit_trail = engine.get_user_audit_trail(test_user.user_id)
        
        print(f"\n✓ 审计追踪记录数: {len(audit_trail)}")
        
        if audit_trail:
            print(f"\n  最近记录示例:")
            for idx, record in enumerate(audit_trail[:3], 1):
                print(f"    {idx}. [{record['timestamp']}] {record['event_type']}: "
                      f"{record['old_reputation']:.4f} {record['change']:+.4f} → {record['new_reputation']:.4f}")
        
        assert len(audit_trail) >= len(events_to_log)
        
        passed = True
        
    except Exception as e:
        print(f"✗ 审计追踪测试失败: {e}")
        import traceback
        traceback.print_exc()
        passed = False
    
    print(f"\n审计追踪系统测试完成: {'通过' if passed else '失败'}")
    return passed


def test_full_integration():
    print("\n" + "=" * 70)
    print("测试 5: 完整集成测试")
    print("=" * 70)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False, enable_event_driven=True)
    augmentor = TextDataAugmentor(random_seed=42)
    
    test_user = UserHistory(
        user_id='TEST_INTEG',
        total_comments=75,
        total_likes=1200,
        total_reports=1,
        average_likes_per_comment=16.0,
        report_rate=0.013,
        account_age_days=300,
        is_verified=True,
        level=5
    )
    
    test_comment = "这款手机非常好用，6.7英寸屏幕显示效果细腻，骁龙8 Gen3处理器性能强劲，4800mAh电池续航很给力，拍照也很清晰，5000万像素主摄像头拍照效果很好。唯一缺点是有点重，210克长时间握持有点累。总体来说性价比很高，推荐购买！"
    
    try:
        print("\n步骤1: 数据增强测试")
        aug_result = augmentor.augment(text=test_comment[:30], num_augments=3)
        print(f"  ✓ 生成 {len(aug_result.augmented_texts)} 个增强样本")
        
        print("\n步骤2: 评论质量评分 + 决策树解释")
        result = engine.score_comment(
            comment_id='INTEG001',
            comment_text=test_comment,
            user_history=test_user,
            generate_decision_tree=True
        )
        
        print(f"  ✓ 最终得分: {result.final_score:.4f} ({result.score_grade})")
        
        print("\n步骤3: 触发点赞事件")
        current_rep = result.user_reputation.overall_reputation_score
        event_result = engine.handle_event(
            event_type=EventType.COMMENT_LIKED,
            user_id=test_user.user_id,
            current_reputation=current_rep,
            severity=EventSeverity.LOW,
            metadata={'like_count': 100, 'is_high_quality_content': True}
        )
        print(f"  ✓ 点赞后信誉分: {event_result.old_reputation:.4f} → {event_result.new_reputation:.4f}")
        
        print("\n步骤4: 触发举报核实事件")
        event_result = engine.handle_event(
            event_type=EventType.REPORT_VERIFIED,
            user_id=test_user.user_id,
            current_reputation=event_result.new_reputation,
            severity=EventSeverity.HIGH,
            metadata={'violation_type': 'advertisement', 'is_first_offense': True}
        )
        print(f"  ✓ 举报核实后信誉分: {event_result.old_reputation:.4f} → {event_result.new_reputation:.4f}")
        
        print("\n步骤5: 查看审计追踪")
        audit_trail = engine.get_user_audit_trail(test_user.user_id)
        print(f"  ✓ 审计追踪记录数: {len(audit_trail)}")
        
        print("\n步骤6: 导出完整结果")
        export_file = 'test_integration_result.json'
        engine.export_result_to_json(result, export_file)
        print(f"  ✓ 结果已导出至: {export_file}")
        
        import os
        with open(export_file, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert 'final_score' in exported_data
        assert 'decision_tree_explanation' in exported_data
        assert 'feature_contributions' in exported_data['decision_tree_explanation']
        
        os.remove(export_file)
        print(f"  ✓ 导出文件验证通过，已清理")
        
        passed = True
        
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        passed = False
    
    print(f"\n完整集成测试完成: {'通过' if passed else '失败'}")
    return passed


def main():
    print("=" * 70)
    print("评论质量评分系统 v2.0 - 新增功能测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    results.append(("数据增强模块", test_data_augmentation()))
    results.append(("事件驱动信誉系统", test_event_driven_reputation()))
    results.append(("决策树解释模块", test_decision_tree_explainer()))
    results.append(("审计追踪系统", test_audit_trail()))
    results.append(("完整集成测试", test_full_integration()))
    
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed_count = 0
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if passed:
            passed_count += 1
    
    print()
    print(f"总计: {passed_count}/{len(results)} 项测试通过")
    
    if passed_count == len(results):
        print("\n🎉 所有新增功能测试通过！系统v2.0功能正常。")
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
