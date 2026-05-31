#!/usr/bin/env python
from config import Config
from core import SearchCorrector

corrector = SearchCorrector(Config)

print("=" * 60)
print("电商搜索纠错系统 - 新功能测试")
print("=" * 60)
print()

test_cases = [
    ('ipone', '种子匹配测试'),
    ('牛nai', '拼音混合测试'),
    ('连衣群', '短词测试(3字)'),
    ('蓝芽耳机', '长词测试(4字)'),
    ('充点器', '种子匹配测试2'),
    ('华伟手机', '种子匹配测试3'),
]

for query, desc in test_cases:
    print(f"【{desc}】")
    print(f"输入: {query}")
    
    result = corrector.correct(query)
    
    print(f"纠正为: {result['corrected']}")
    print(f"是否需要纠正: {result['needs_correction']}")
    print(f"词长度: {result['query_length']}")
    print(f"动态阈值: {result['dynamic_threshold']:.3f}")
    print(f"基础阈值: {result['base_threshold']:.3f}")
    print(f"拼音混合检测: {result['pinyin_mixed_detected']}")
    
    seed_matched = any(c.get('is_seed_match', False) for c in result['candidates'])
    print(f"种子匹配: {seed_matched}")
    
    if result['candidates']:
        top = result['candidates'][0]
        print(f"拼音相似度: {top.get('pinyin_similarity', 0):.2%}")
        print(f"最终置信度: {top['final_score']:.2%}")
    
    print("-" * 60)
    print()

print("=" * 60)
print("动态阈值规则测试:")
print("=" * 60)
for length in [1, 2, 3, 4, 5, 6, 10]:
    query = '字' * length
    threshold = corrector.get_dynamic_threshold_for_query(query)
    strictness = "严格" if threshold > 0.75 else ("中等" if threshold > 0.65 else "宽松")
    print(f"词长度 {length}: 阈值 {threshold:.3f} ({strictness})")

print()
print("所有测试完成！")
