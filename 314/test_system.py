#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统功能测试脚本
验证评论质量评分系统的各个模块功能
"""

import sys
import json
from datetime import datetime, timedelta

from bert_analyzer import BERTTextAnalyzer
from knowledge_graph import KnowledgeGraphAnalyzer
from user_reputation import UserReputationAnalyzer, UserHistory
from scoring_engine import CommentQualityScoringEngine


def test_bert_analyzer():
    print("=" * 60)
    print("测试 1: BERT文本质量分析模块")
    print("=" * 60)
    
    analyzer = BERTTextAnalyzer(use_pretrained=False)
    
    test_cases = [
        ("优质评论", "这款手机我已经用了3个月了，整体来说非常满意。屏幕是6.7英寸的OLED屏，显示效果非常细腻，看视频玩游戏都很爽。处理器是最新的骁龙8 Gen3，日常使用完全不卡顿，玩大型游戏也能保持60帧以上。续航方面，4800mAh的电池中度使用可以用一天半，充电速度也很快，30分钟就能充到80%。拍照效果也不错，5000万像素的主摄像头拍照很清晰，夜景模式也很给力。唯一的小缺点是手机稍微有点重，210克的重量长时间握持有点累。总体来说，这款手机性价比很高，非常推荐购买！"),
        ("简短评论", "很好，不错。"),
        ("可疑评论", "垃圾！！！垃圾！！！千万别买！！！"),
        ("中等评论", "性价比很高，质量不错，物流也很快。")
    ]
    
    passed = 0
    for name, text in test_cases:
        try:
            result = analyzer.analyze(text)
            print(f"\n✓ {name} - 分析成功")
            print(f"  有用性: {result.usefulness_score:.4f}")
            print(f"  真实性: {result.authenticity_score:.4f}")
            print(f"  完整性: {result.completeness_score:.4f}")
            print(f"  综合分: {result.overall_text_score:.4f}")
            print(f"  证据条数: {len(result.usefulness_evidence) + len(result.authenticity_evidence) + len(result.completeness_evidence)}")
            
            assert 0 <= result.usefulness_score <= 1
            assert 0 <= result.authenticity_score <= 1
            assert 0 <= result.completeness_score <= 1
            assert 0 <= result.overall_text_score <= 1
            
            passed += 1
        except Exception as e:
            print(f"✗ {name} - 分析失败: {e}")
    
    print(f"\nBERT模块测试完成: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_knowledge_graph():
    print("\n" + "=" * 60)
    print("测试 2: 知识图谱模块")
    print("=" * 60)
    
    analyzer = KnowledgeGraphAnalyzer()
    
    test_texts = [
        "这款华为Mate 60 Pro非常好，6.69英寸的屏幕，5000mAh电池，拍照质量很好，价格6999元。对比iPhone 15，信号强太多了。",
        "小米14的性能很强，骁龙8 Gen3处理器，性价比很高。",
        "这个耳机的降噪效果不错，音质清晰，佩戴舒适。"
    ]
    
    passed = 0
    for idx, text in enumerate(test_texts, 1):
        try:
            result = analyzer.analyze(text)
            print(f"\n✓ 测试文本 {idx} - 分析成功")
            print(f"  实体数量: {len(result.entities)}")
            print(f"  关系数量: {len(result.relations)}")
            print(f"  事实验证分: {result.fact_verification_score:.4f}")
            print(f"  实体多样性: {result.entity_diversity_score:.4f}")
            print(f"  关系质量分: {result.relation_quality_score:.4f}")
            print(f"  综合分: {result.overall_kg_score:.4f}")
            
            if result.entities:
                print(f"  提取实体: {[e.name for e in result.entities[:5]]}")
            if result.relations:
                print(f"  提取关系: {[r.predicate for r in result.relations[:3]]}")
            
            assert 0 <= result.overall_kg_score <= 1
            
            passed += 1
        except Exception as e:
            print(f"✗ 测试文本 {idx} - 分析失败: {e}")
    
    print(f"\n知识图谱模块测试完成: {passed}/{len(test_texts)} 通过")
    return passed == len(test_texts)


def test_user_reputation():
    print("\n" + "=" * 60)
    print("测试 3: 用户信誉分析模块")
    print("=" * 60)
    
    analyzer = UserReputationAnalyzer()
    
    test_users = [
        ("高信誉用户", UserHistory(
            user_id='U001',
            total_comments=156,
            total_likes=3240,
            total_reports=0,
            average_likes_per_comment=20.8,
            report_rate=0.0,
            account_age_days=730,
            is_verified=True,
            level=7
        )),
        ("高风险用户", UserHistory(
            user_id='U002',
            total_comments=28,
            total_likes=15,
            total_reports=5,
            average_likes_per_comment=0.5,
            report_rate=0.179,
            account_age_days=45,
            is_verified=False,
            level=2,
            comment_history=[
                {'text': '垃圾产品，千万别买！！！', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=5)},
                {'text': '骗人的，假货！！！', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=10)},
                {'text': '很差很差很差', 'rating': 1, 'timestamp': datetime.now() - timedelta(minutes=15)},
            ]
        )),
        ("新用户", UserHistory(
            user_id='U003',
            total_comments=3,
            total_likes=2,
            total_reports=0,
            average_likes_per_comment=0.7,
            report_rate=0.0,
            account_age_days=7,
            is_verified=False,
            level=1
        ))
    ]
    
    passed = 0
    for name, user_history in test_users:
        try:
            result = analyzer.analyze(user_history, [0.75, 0.82])
            print(f"\n✓ {name} - 分析成功")
            print(f"  总体信誉: {result.overall_reputation_score:.4f}")
            print(f"  可信度: {result.trustworthiness_score:.4f}")
            print(f"  影响力: {result.influence_score:.4f}")
            print(f"  一致性: {result.consistency_score:.4f}")
            print(f"  风险分: {result.risk_score:.4f}")
            print(f"  证据条数: {len(result.evidence)}")
            
            profile = analyzer.generate_user_profile(user_history)
            print(f"  用户画像: {profile}")
            
            assert 0 <= result.overall_reputation_score <= 1
            assert 0 <= result.trustworthiness_score <= 1
            assert 0 <= result.influence_score <= 1
            assert 0 <= result.consistency_score <= 1
            assert 0 <= result.risk_score <= 1
            
            passed += 1
        except Exception as e:
            print(f"✗ {name} - 分析失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n用户信誉模块测试完成: {passed}/{len(test_users)} 通过")
    return passed == len(test_users)


def test_scoring_engine():
    print("\n" + "=" * 60)
    print("测试 4: 综合评分引擎")
    print("=" * 60)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False)
    
    test_cases = [
        {
            'comment_id': 'TEST001',
            'comment_text': '这款华为Mate 60 Pro我入手一周了，体验非常好。首先是外观设计，曲面屏手感很好，素皮背面不容易沾指纹。系统是鸿蒙4.0，流畅度没得说，各种APP秒开。拍照方面，可变光圈确实很实用，白天拍照色彩鲜艳，夜景模式噪点控制得很好。续航也不错，5000mAh电池用一天完全没问题。66W快充半小时能充到70%。对比我之前用的iPhone 14，信号强太多了，在地下车库也能满格。缺点就是价格有点贵，而且有点重，225克。但总体来说，支持华为，值得入手！',
            'user_history': UserHistory(
                user_id='TEST_USER',
                total_comments=156,
                total_likes=3240,
                total_reports=0,
                average_likes_per_comment=20.8,
                report_rate=0.0,
                account_age_days=730,
                is_verified=True,
                level=7
            ),
            'historical_scores': [0.75, 0.82, 0.78]
        }
    ]
    
    passed = 0
    for idx, test_case in enumerate(test_cases, 1):
        try:
            result = engine.score_comment(
                comment_id=test_case['comment_id'],
                comment_text=test_case['comment_text'],
                user_history=test_case['user_history'],
                historical_text_scores=test_case['historical_scores']
            )
            
            print(f"\n✓ 测试用例 {idx} - 评分成功")
            print(f"  最终得分: {result.final_score:.4f}")
            print(f"  等级: {result.score_grade}")
            print(f"  百分位: {result.score_percentile:.2f}%")
            print(f"  评分权重: {result.scoring_weights}")
            
            print(f"\n  各模块得分:")
            for module, data in result.score_breakdown['module_scores'].items():
                print(f"    {module}: {data['raw_score']:.4f} (加权: {data['weighted_score']:.4f})")
            
            print(f"\n  解读总结:")
            for summary in result.interpretation['overall_summary'][:2]:
                print(f"    - {summary}")
            
            if result.interpretation['strengths']:
                print(f"\n  优势: {result.interpretation['strengths'][0]}")
            
            if result.recommendations:
                print(f"  建议: {result.recommendations[0]}")
            
            assert 0 <= result.final_score <= 1
            assert result.score_grade in ['S (优秀)', 'A (良好)', 'B (较好)', 'C (一般)', 'D (较差)', 'F (差)']
            
            passed += 1
        except Exception as e:
            print(f"✗ 测试用例 {idx} - 评分失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n综合评分引擎测试完成: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_json_export():
    print("\n" + "=" * 60)
    print("测试 5: JSON导出功能")
    print("=" * 60)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False)
    
    try:
        user_history = UserHistory(
            user_id='EXPORT_TEST',
            total_comments=50,
            total_likes=500,
            total_reports=1,
            average_likes_per_comment=10.0,
            report_rate=0.02,
            account_age_days=180,
            is_verified=False,
            level=3
        )
        
        result = engine.score_comment(
            comment_id='EXPORT001',
            comment_text='这款手机性价比很高，质量不错，物流也很快，推荐购买。',
            user_history=user_history
        )
        
        output_file = 'test_export.json'
        exported_path = engine.export_result_to_json(result, output_file)
        
        with open(exported_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['comment_id'] == 'EXPORT001'
        assert 'final_score' in data
        assert 'text_quality' in data
        assert 'knowledge_graph' in data
        assert 'user_reputation' in data
        
        print(f"✓ JSON导出成功")
        print(f"  导出文件: {exported_path}")
        print(f"  包含字段: {list(data.keys())}")
        print(f"  最终得分: {data['final_score']:.4f}")
        
        import os
        os.remove(exported_path)
        print(f"  测试文件已清理")
        
        return True
    except Exception as e:
        print(f"✗ JSON导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_weight_adjustment():
    print("\n" + "=" * 60)
    print("测试 6: 权重调整功能")
    print("=" * 60)
    
    engine = CommentQualityScoringEngine(use_bert_pretrained=False)
    
    try:
        original_weights = engine.weights.copy()
        print(f"原始权重: {original_weights}")
        
        custom_weights = {
            'text_quality': 0.6,
            'knowledge_graph': 0.2,
            'user_reputation': 0.2
        }
        engine.update_weights(custom_weights)
        print(f"自定义权重: {engine.weights}")
        
        assert abs(engine.weights['text_quality'] - 0.6) < 0.01
        assert abs(engine.weights['knowledge_graph'] - 0.2) < 0.01
        assert abs(engine.weights['user_reputation'] - 0.2) < 0.01
        
        unbalanced_weights = {
            'text_quality': 0.5,
            'knowledge_graph': 0.5,
            'user_reputation': 0.5
        }
        engine.update_weights(unbalanced_weights)
        total = sum(engine.weights.values())
        print(f"归一化后权重: {engine.weights}, 和为: {total:.4f}")
        assert abs(total - 1.0) < 0.01
        
        engine.update_weights(original_weights)
        print(f"✓ 权重调整测试通过")
        print(f"  支持自定义权重")
        print(f"  支持自动归一化")
        print(f"  支持重置为默认值")
        
        return True
    except Exception as e:
        print(f"✗ 权重调整测试失败: {e}")
        return False


def main():
    print("=" * 60)
    print("评论质量评分系统 - 功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    results.append(("BERT文本分析模块", test_bert_analyzer()))
    results.append(("知识图谱模块", test_knowledge_graph()))
    results.append(("用户信誉分析模块", test_user_reputation()))
    results.append(("综合评分引擎", test_scoring_engine()))
    results.append(("JSON导出功能", test_json_export()))
    results.append(("权重调整功能", test_weight_adjustment()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed_count = 0
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if passed:
            passed_count += 1
    
    print()
    print(f"总计: {passed_count}/{len(results)} 项测试通过")
    
    if passed_count == len(results):
        print("\n🎉 所有测试通过！系统功能正常。")
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
