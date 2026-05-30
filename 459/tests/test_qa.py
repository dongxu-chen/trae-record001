import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.qa_service import QAService
from nlp.entity_extractor import DynamicThreshold


def test_single_hop_queries():
    print("=" * 50)
    print("测试单跳查询 (Hybrid生成)")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    test_questions = [
        "感冒有什么症状？",
        "感冒吃什么药？",
        "感冒挂什么科？",
        "阿莫西林治什么病？",
        "呼吸内科看什么病？",
    ]

    for question in test_questions:
        print(f"\n问题: {question}")
        try:
            result = qa.answer(question)
            print(f"答案: {result['answer']}")
            method = result.get('query_info', {}).get('generation_method', 'unknown')
            print(f"生成方式: {method}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


def test_multi_hop_with_completion():
    print("\n" + "=" * 50)
    print("测试多跳推理(含路径补全)")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    test_questions = [
        "感冒的症状有哪些然后用什么药？",
        "肺炎应该挂什么科以及怎么治疗？",
    ]

    for question in test_questions:
        print(f"\n问题: {question}")
        try:
            result = qa.answer(question)
            print(f"答案: {result['answer']}")
            path_info = result.get('path_reasoning', {})
            print(f"路径推理状态: {path_info.get('status', 'N/A')}")
            print(f"是否使用补全: {path_info.get('completion_used', False)}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


def test_path_completion():
    print("\n" + "=" * 50)
    print("测试路径补全")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    test_cases = [
        ("感冒", "阿莫西林"),
        ("高血压", "心电图"),
        ("感冒", "消化内科"),
    ]

    for entity1, entity2 in test_cases:
        print(f"\n路径补全: {entity1} -> {entity2}")
        try:
            result = qa.path_completion_query(entity1, entity2)
            print(f"状态: {result['status']}")
            print(f"是否找到路径: {result['path_found']}")
            if result.get('bridge_nodes'):
                print(f"桥接节点: {result['bridge_nodes']}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


def test_missing_node_hop():
    print("\n" + "=" * 50)
    print("测试缺失节点跳跃查询")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    test_cases = [
        {"start_entity": "感冒", "target_entity_type": "Drug"},
        {"start_entity": "感冒", "target_relation": "HAS_SYMPTOM"},
        {"start_entity": "高血压", "target_entity_type": "Examination"},
    ]

    for case in test_cases:
        print(f"\n跳跃查询: {case}")
        try:
            result = qa.missing_node_hop(**case)
            print(f"状态: {result['status']}")
            if result.get('results'):
                print(f"找到 {len(result['results'])} 个结果")
            if result.get('hop_distribution'):
                print(f"跳数分布: {result['hop_distribution']}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


def test_dynamic_threshold():
    print("\n" + "=" * 50)
    print("测试动态阈值模糊匹配")
    print("=" * 50)

    dt = DynamicThreshold()

    test_words = ["肺", "感冒", "高血压", "阿莫西林", "呼吸内科", "上呼吸道感染"]

    print("\n实体长度 -> 自适应阈值:")
    print("-" * 40)
    for word in test_words:
        threshold = dt.compute(word)
        reason = ""
        if len(word) <= 2:
            reason = "(短实体，低阈值增加召回)"
        elif len(word) >= 5:
            reason = "(长实体，高阈值保证精确)"
        else:
            reason = "(中等实体，平衡阈值)"
        print(f"  '{word}' (len={len(word)}) -> 阈值={threshold} {reason}")

    qa = QAService(use_bert=False, use_seq2seq=False)

    print("\n模糊匹配详情测试:")
    try:
        detail = qa.fuzzy_match_detail("发烧咳嗽")
        print(f"  原文: {detail['original_text']}")
        print(f"  分词: {detail['segmented_words']}")
        for word, info in detail.get('thresholds', {}).items():
            print(f"  '{word}' -> 阈值={info['threshold']}, {info['reason']}")
        if detail['entities']:
            print(f"  匹配到的实体: {[e['canonical_name'] for e in detail['entities']]}")
    except Exception as e:
        print(f"  错误: {e}")

    qa.close()


def test_fuzzy_queries():
    print("\n" + "=" * 50)
    print("测试模糊查询(动态阈值)")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    test_questions = [
        "关于感冒的信息",
        "和肺相关的病",
    ]

    for question in test_questions:
        print(f"\n问题: {question}")
        try:
            result = qa.answer(question)
            print(f"答案: {result['answer']}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


def test_entity_details():
    print("\n" + "=" * 50)
    print("测试实体详情查询")
    print("=" * 50)

    qa = QAService(use_bert=False, use_seq2seq=False)

    entities = ["感冒", "阿莫西林", "呼吸内科"]

    for entity in entities:
        print(f"\n实体: {entity}")
        try:
            result = qa.get_entity_details(entity)
            print(f"详情: {result['answer']}")
        except Exception as e:
            print(f"错误: {e}")

    qa.close()


if __name__ == "__main__":
    test_single_hop_queries()
    test_multi_hop_with_completion()
    test_path_completion()
    test_missing_node_hop()
    test_dynamic_threshold()
    test_fuzzy_queries()
    test_entity_details()
    print("\n" + "=" * 50)
    print("v2.0 全部测试完成！")
    print("=" * 50)
