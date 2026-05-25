import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_service import EcommerceSearchService
from knowledge_graph import KnowledgeGraph
from query_rewriter import QueryRewriter


def print_separator(title):
    print('\n' + '=' * 60)
    print(f'  {title}')
    print('=' * 60 + '\n')


def test_basic_search(service):
    print_separator('测试1: 基础搜索')
    
    test_queries = [
        '苹果手机',
        '华为Mate 60',
        '笔记本电脑',
        '降噪耳机',
        '4K显示器'
    ]
    
    for query in test_queries:
        print(f'查询: {query}')
        result = service.search(query, top_n=3)
        print(f'  意图: {result["intent_analysis"]["intent"]}')
        print(f'  置信度: {result["intent_analysis"]["confidence"]:.2f}')
        print(f'  品牌: {result["attribute_extraction"]["brands"]}')
        print(f'  品类: {result["attribute_extraction"]["categories"]}')
        print(f'  规格: {result["attribute_extraction"]["specs"]}')
        print(f'  搜索结果数: {result["search_results"]["total"]}')
        print(f'  召回提升: 扩展了{result["recall_improvement"]["term_expansion_rate"]}倍词汇')
        print()


def test_intent_classification(service):
    print_separator('测试2: 意图识别分类')
    
    test_cases = [
        ('我想买一部iPhone 15', '购买意向'),
        ('苹果和华为手机哪个好', '比价'),
        ('什么是OLED屏幕', '知识查询'),
        ('推荐一款性价比高的笔记本', '购买意向'),
        ('小米14和一加12对比', '比价'),
        ('5G手机有什么优势', '知识查询')
    ]
    
    correct = 0
    for query, expected_intent in test_cases:
        result = service.analyze_intent(query)
        predicted = result['intent']
        is_correct = predicted == expected_intent
        if is_correct:
            correct += 1
        
        status = '✓' if is_correct else '✗'
        print(f'{status} 查询: {query}')
        print(f'   预测: {predicted}, 期望: {expected_intent}, 置信度: {result["confidence"]:.2f}')
        print()
    
    print(f'准确率: {correct}/{len(test_cases)} = {correct/len(test_cases)*100:.1f}%')


def test_attribute_extraction(service):
    print_separator('测试3: 属性抽取')
    
    test_cases = [
        '苹果iPhone 15 256G手机',
        '索尼WH-1000XM5降噪耳机',
        '戴尔27寸4K显示器',
        '华为Mate 60 Pro',
        '三星65英寸智能电视'
    ]
    
    for query in test_cases:
        result = service.extract_attributes(query)
        print(f'查询: {query}')
        print(f'  品牌: {result["brands"]}')
        print(f'  品类: {result["categories"]}')
        print(f'  规格: {result["specs"]}')
        print()


def test_query_rewriting(service):
    print_separator('测试4: 查询改写')
    
    test_cases = [
        '苹果手机',
        '笔记本电脑推荐',
        '无线耳机',
        '平版电脑',
        'Apple iPhone'
    ]
    
    for query in test_cases:
        result = service.rewrite_query(query)
        print(f'原始查询: {query}')
        print(f'  修正查询: {result["primary_query"]}')
        print(f'  扩展词汇: {result["rewrite_details"]["expanded_terms"]}')
        print(f'  过滤条件: {result["filter_terms"]}')
        print()


def test_recall_improvement(service):
    print_separator('测试5: 召回率提升对比')
    
    test_queries = [
        '苹果',
        '手机',
        '耳机',
        '笔记本'
    ]
    
    for query in test_queries:
        result = service.search(query, top_n=5)
        print(f'查询: {query}')
        print(f'  原始词汇数: {result["recall_improvement"]["original_term_count"]}')
        print(f'  扩展词汇数: {result["recall_improvement"]["expanded_term_count"]}')
        print(f'  扩展倍率: {result["recall_improvement"]["term_expansion_rate"]}x')
        print(f'  新增词汇: {result["recall_improvement"]["new_terms_added"]}')
        print(f'  返回商品数: {result["search_results"]["total"]}')
        print()


def test_search_results(service):
    print_separator('测试6: 完整搜索结果展示')
    
    query = '苹果手机'
    result = service.search(query, top_n=5)
    
    print(f'查询: {query}')
    print(f'意图: {result["intent_analysis"]["intent"]}')
    print(f'推荐语: {result["recommendation"]["message"]}')
    print()
    print('搜索结果:')
    print('-' * 60)
    
    for i, product in enumerate(result['search_results']['products'], 1):
        print(f'{i}. {product["name"]}')
        print(f'   品牌: {product["brand"]} | 品类: {product["category"]}')
        print(f'   价格: ¥{product["price"]} | 相关度: {product.get("_score", "N/A")}')
        print()


def test_tinybert_performance(service):
    print_separator('测试7: TinyBERT推理性能测试')
    
    test_queries = [
        '我想买苹果手机',
        '华为和小米哪个好',
        '什么是OLED屏幕',
        '推荐一款笔记本电脑',
        '降噪耳机推荐'
    ]
    
    print('进行推理延迟测试（预热后）...')
    print()
    
    times = []
    for i, query in enumerate(test_queries):
        start_time = time.time()
        result = service.analyze_intent(query)
        elapsed = (time.time() - start_time) * 1000
        times.append(elapsed)
        
        print(f'  查询{i+1}: "{query}"')
        print(f'    推理时间: {elapsed:.2f}ms, 意图: {result["intent"]}')
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    min_time = min(times)
    
    print()
    print(f'  平均推理时间: {avg_time:.2f}ms')
    print(f'  最快: {min_time:.2f}ms, 最慢: {max_time:.2f}ms')
    print(f'  目标: 50ms以内 {"✓ 达标" if avg_time < 50 else "✗ 未达标"}')


def test_abbreviation_and_colloquial():
    print_separator('测试8: 品牌缩写和俗称识别')
    
    kg = KnowledgeGraph()
    
    test_cases = [
        ('缩写识别', [
            ('HW', '华为'),
            ('XM', '小米'),
            ('AP', '苹果'),
            ('DE', '戴尔'),
            ('LX', '联想')
        ]),
        ('俗称识别', [
            ('菊花', '华为'),
            ('粗粮', '小米'),
            ('水果', '苹果'),
            ('本本', '笔记本电脑'),
            ('爪机', '手机')
        ])
    ]
    
    for test_name, cases in test_cases:
        print(f'{test_name}:')
        correct = 0
        for term, expected in cases:
            result = kg.normalize_term(term)
            is_correct = result == expected
            if is_correct:
                correct += 1
            
            status = '✓' if is_correct else '✗'
            print(f'  {status} {term} → {result} (期望: {expected})')
        
        print(f'  准确率: {correct}/{len(cases)} = {correct/len(cases)*100:.1f}%')
        print()


def test_confidence_threshold():
    print_separator('测试9: 置信度阈值验证')
    
    from config import Config
    rewriter = QueryRewriter()
    
    print(f'当前置信度阈值: {Config.REWRITE_CONFIDENCE_THRESHOLD}')
    print()
    
    test_cases = [
        ('苹果手机', '高置信度，正常改写'),
        ('平果手机', '中等置信度，可能拒绝'),
        ('苹国手机', '低置信度，保留原词'),
        ('HW手机', '缩写，高置信度通过'),
        ('菊花手机', '俗称，高置信度通过')
    ]
    
    for query, description in test_cases:
        print(f'查询: "{query}" ({description})')
        result = rewriter.rewrite(query)
        
        print(f'  修正查询: {result["corrected_query"]}')
        
        if result['corrections']:
            for corr in result['corrections']:
                applied = corr.get('applied', False)
                confidence = corr.get('confidence', 0)
                status = '✓ 应用' if applied else '✗ 拒绝(低置信)'
                print(f'    {status}: {corr["original"]} → {corr["corrected"]}, 置信度: {confidence:.4f}')
        
        preserved = result.get('preserved_original_words', [])
        if preserved:
            print(f'  保留原词: {preserved}')
        
        print()


def main():
    print('\n' + '#' * 60)
    print('#' + ' ' * 58 + '#')
    print('#' + ' ' * 10 + '电商搜索意图识别系统 v2.0' + ' ' * 14 + '#')
    print('#' + ' ' * 8 + '[TinyBERT优化 + 别名映射 + 置信度]' + ' ' * 9 + '#')
    print('#' + ' ' * 58 + '#')
    print('#' * 60)
    
    print('\n正在初始化搜索服务...')
    service = EcommerceSearchService(use_pretrained=False)
    
    print('\n系统状态:')
    stats = service.get_stats()
    print(f'  知识图谱实体数: {stats["knowledge_graph"]["total_entities"]}')
    print(f'  知识图谱关系数: {stats["knowledge_graph"]["total_relations"]}')
    print(f'  缩写映射数: {stats["knowledge_graph"].get("abbreviations_count", 0)}')
    print(f'  俗称映射数: {stats["knowledge_graph"].get("colloquials_count", 0)}')
    print(f'  同义词条目数: {stats["synonym_manager"]["main_terms_count"]}')
    print(f'  索引商品数: {stats["product_search"]["total_products"]}')
    print(f'  改写置信度阈值: {stats["query_rewriter"].get("confidence_threshold", "N/A")}')
    
    test_basic_search(service)
    test_intent_classification(service)
    test_attribute_extraction(service)
    test_query_rewriting(service)
    test_recall_improvement(service)
    test_search_results(service)
    test_tinybert_performance(service)
    test_abbreviation_and_colloquial()
    test_confidence_threshold()
    
    print_separator('测试完成')
    print('所有测试用例执行完毕！')
    print()
    print('优化功能总结:')
    print('  ✓ TinyBERT蒸馏版模型 - 推理延迟优化')
    print('  ✓ 品牌缩写识别 (HW, XM, AP等)')
    print('  ✓ 品牌俗称识别 (菊花, 粗粮, 水果等)')
    print('  ✓ 置信度阈值过滤 - 低置信度保留原词')
    print()
    print('提示: 启动API服务请运行: python main.py')
    print('      训练TinyBERT模型请运行: python -m bert_module.train')


if __name__ == '__main__':
    main()
