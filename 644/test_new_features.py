#!/usr/bin/env python
from config import Config
from core import SearchCorrector

corrector = SearchCorrector(Config)

print("=" * 70)
print("电商搜索纠错系统 - 新功能测试")
print("=" * 70)
print()

print("【1. 多语言混合纠错测试】")
print("-" * 70)
multilingual_cases = [
    ('apple手机', '中英文混合'),
    ('iphone壳', '英文品牌+中文'),
    ('bluetooth耳机', '英文词+中文'),
    ('huawei手机', '拼音品牌+中文'),
    ('nike鞋', '英文品牌+中文'),
    ('coca cola', '纯英文品牌'),
]

for query, desc in multilingual_cases:
    result = corrector.correct(query)
    print(f"输入: {query:20s} ({desc})")
    print(f"输出: {result['corrected']:20s}")
    print(f"置信度: {result['candidates'][0]['final_score']:.2%}" if result['candidates'] else "无候选")
    if result['multilingual_details']:
        print(f"多语言处理: {[(d['original'], d['corrected']) for d in result['multilingual_details']]}")
    print()

print("【2. 个性化纠错测试】")
print("-" * 70)
user_id = 'test_user_001'

print(f"用户 {user_id} 初始状态:")
profile = corrector.get_user_profile(user_id)
print(f"  交互次数: {profile['total_interactions']}")
print(f"  接受率: {profile['acceptance_rate']:.2%}")
print(f"  阈值调整: {profile['threshold_adjustment']:+.2f}")
print()

print("模拟用户反馈（连续点击iPhone相关纠错）:")
for i in range(5):
    corrector.record_click('ipone', 'iPhone', 'iPhone', user_id)

profile = corrector.get_user_profile(user_id)
print(f"  交互次数: {profile['total_interactions']}")
print(f"  接受率: {profile['acceptance_rate']:.2%}")
print(f"  阈值调整: {profile['threshold_adjustment']:+.2f}")
print(f"  常用词: {[w[0] for w in profile['top_words'][:5]]}")
print()

print("使用用户偏好搜索 'ipone':")
result = corrector.correct('ipone', user_id=user_id)
print(f"  个性化得分: {result['candidates'][0]['personalization_score']:.2%}")
print(f"  动态阈值: {result['dynamic_threshold']:.3f}")
print()

print("【3. 纠错效果评估测试】")
print("-" * 70)
evaluation_cases = [
    'ipone',
    '牛nai',
    '连衣群',
    '蓝芽耳机',
    'apple手机',
]

for query in evaluation_cases:
    result = corrector.correct(query)
    if result['improvement']:
        imp = result['improvement']
        print(f"输入: {query:15s} → {result['corrected']:15s}")
        print(f"  纠错前效果: {imp['search_effect_before']:6.2f}")
        print(f"  纠错后效果: {imp['search_effect_after']:6.2f}")
        print(f"  提升幅度: {imp['improvement_percentage']:+8.1f}%")
        print(f"  权重提升: {imp['weight_improvement']:+d}")
        print()

print("【4. 整体效果评估指标】")
print("-" * 70)
metrics = corrector.get_evaluation_metrics()
overall = metrics['overall']
print(f"总查询数: {overall['total_queries']}")
print(f"纠错数: {overall['corrected_queries']}")
print(f"纠错率: {overall['correction_rate']:.2f}%")
print(f"接受率: {overall['acceptance_rate']:.2f}%")
print(f"平均置信度: {overall['avg_confidence']:.3f}")
print(f"用户满意度得分: {overall['user_satisfaction_score']:.2f}")
print()

print("【5. 动态阈值测试】")
print("-" * 70)
threshold_test_cases = [
    ('i', 1),
    ('ip', 2),
    ('ipo', 3),
    ('ipon', 4),
    ('ipone', 5),
    ('iphone手', 6),
    ('iphone手机', 8),
]

for query, expected_len in threshold_test_cases:
    dynamic_th = corrector.get_dynamic_threshold_for_query(query, user_id)
    print(f"词长 {len(query):2d} ({query:12s}): 阈值 {dynamic_th:.3f}")

print()
print("=" * 70)
print("所有测试完成！")
print("=" * 70)
