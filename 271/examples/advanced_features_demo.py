#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rules_dsl import DSLEngine, RuleChecker
from src.complexity_analyzer import ComplexityAnalyzer
from src.duplication_detector import DuplicationDetector
from src.code_review_tool import CodeReviewTool


def demo_dsl_rules():
    print("=" * 70)
    print("演示 1: DSL 自然语言规则系统")
    print("=" * 70)
    
    dsl_content = '''
# 示例规则集 - 中文自然语言

规则 "函数参数限制", 严重程度: 中等
    针对: 函数
    参数不能超过 5 个
    提示: "函数参数过多，建议重构"

---

规则 "函数行数限制", severity: high
    检查: 函数
    行数不能超过 30 行
    消息: "函数太长了，考虑拆分"

---

规则 "硬编码检测", 级别: 致命
    应用于: 文件
    检测硬编码密码
    提示: "发现硬编码敏感信息！"
'''
    
    engine = DSLEngine()
    rules = engine.parse_dsl_content(dsl_content)
    
    print(f"\n解析到 {len(rules)} 条规则:")
    for rule in rules:
        print(f"\n  规则: {rule.name}")
        print(f"    严重程度: {rule.severity}")
        print(f"    提示信息: {rule.message}")
        print(f"    目标: {rule.targets}")
        print(f"    条件数: {len(rule.conditions)}")


def create_test_file_with_nested_functions():
    test_code = '''
def outer_function(a, b, c, d, e, f):
    """外部函数 - 参数过多"""
    
    def inner_function1():
        """内部函数1"""
        x = 1
        if x > 0:
            if x < 10:
                if x % 2 == 0:
                    return "even"
                else:
                    return "odd"
            else:
                return "big"
        else:
            return "small"
    
    def inner_function2():
        """内部函数2 - 嵌套过深"""
        result = 0
        for i in range(10):
            if i % 2 == 0:
                for j in range(5):
                    if j > 2:
                        if i + j > 5:
                            result += 1
        return result
    
    return inner_function1() + inner_function2()


class badClassName:
    """类名不符合规范"""
    
    def MethodName(self):
        password = "hardcoded_password_123"
        return password


def duplicate_func1(x, y):
    sum_val = 0
    sum_val += x
    sum_val += y
    sum_val *= 2
    return sum_val


def duplicate_func2(a, b):
    total = 0
    total += a
    total += b
    total *= 2
    return total
'''
    
    test_file = os.path.join(os.path.dirname(__file__), "test_code", "nested_example.py")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    return test_file


def demo_nested_complexity():
    print("\n" + "=" * 70)
    print("演示 2: 嵌套作用域复杂度分析")
    print("=" * 70)
    
    test_file = create_test_file_with_nested_functions()
    
    analyzer = ComplexityAnalyzer()
    result = analyzer.analyze_file(test_file)
    
    print(f"\n文件: {test_file}")
    print(f"函数总数: {result['function_count']}")
    print(f"平均圈复杂度: {result['average_ccn']:.2f}")
    print(f"平均入口复杂度: {result.get('average_entry_complexity', 0):.2f}")
    
    print("\n函数详情（含内部函数）:")
    for func in result['functions']:
        indent = "  " * func['scope_depth']
        status = "⚠️  内部函数" if func['is_inner_function'] else ""
        print(f"{indent}- {func['long_name']} (第{func['start_line']}行)")
        print(f"{indent}  CCN: {func['ccn']}, 入口复杂度: {func['entry_complexity']}")
        print(f"{indent}  嵌套深度: {func['scope_depth']}, 行数: {func['nloc']} {status}")
    
    print("\n高风险函数:")
    for func in result['high_risk_functions']:
        print(f"  - {func['long_name']}: {func['risk_level'].upper()}")
        for issue in func['issues']:
            print(f"    • {issue}")


def demo_duplication_levels():
    print("\n" + "=" * 70)
    print("演示 3: 函数级和语句级重复代码检测")
    print("=" * 70)
    
    test_file = create_test_file_with_nested_functions()
    
    detector = DuplicationDetector()
    result = detector.detect_file_duplication(test_file)
    
    print(f"\n检测结果:")
    summary = result['summary']
    print(f"  总重复数: {summary['total_duplicates']}")
    print(f"  函数级重复: {summary['by_level']['function']}")
    print(f"  语句级重复: {summary['by_level']['statement']}")
    
    if result['duplicates']:
        print("\n重复详情:")
        for dup in result['duplicates']:
            print(f"  [{dup['level'].upper()}] 相似度: {dup['similarity']}%")
            print(f"    原始: 第{dup['original']['start_line']}-{dup['original']['end_line']}行")
            print(f"    重复: 第{dup['duplicate']['start_line']}-{dup['duplicate']['end_line']}行")


def demo_full_analysis():
    print("\n" + "=" * 70)
    print("演示 4: 完整代码审查（含所有新功能）")
    print("=" * 70)
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_code")
    
    tool = CodeReviewTool()
    
    print(f"\n分析目录: {test_dir}")
    results = tool.analyze_directory(test_dir)
    
    print("\n" + "-" * 50)
    print("复杂度分析摘要:")
    comp_summary = results['complexity']['summary']
    print(f"  总函数数: {comp_summary['total_functions']}")
    print(f"  平均CCN: {comp_summary['average_ccn']}")
    print(f"  平均入口复杂度: {comp_summary['average_entry_complexity']}")
    print(f"  高风险函数: {comp_summary['high_risk_count']}")
    print(f"  启用入口复杂度分离: {comp_summary.get('separate_entry_complexity', False)}")
    
    print("\n" + "-" * 50)
    print("重复代码检测摘要:")
    dup_summary = results['duplication']['summary']
    print(f"  总重复: {dup_summary['total_duplicates']}")
    print(f"  函数级: {dup_summary['by_level']['function']}")
    print(f"  语句级: {dup_summary['by_level']['statement']}")
    print(f"  风险等级: {dup_summary['risk_level']}")
    
    print("\n" + "-" * 50)
    print("DSL规则检查摘要:")
    dsl_summary = results.get('dsl_rules', {}).get('summary', {})
    print(f"  总违规: {dsl_summary.get('total', 0)}")
    for level in ['critical', 'high', 'medium', 'low']:
        if dsl_summary.get(level, 0) > 0:
            print(f"    {level.upper()}: {dsl_summary[level]}")
    
    print("\n" + "-" * 50)
    print("生成报告...")
    reports = tool.generate_reports({'pr_info': {}, **results}, 'all')
    for fmt, path in reports.items():
        print(f"  {fmt.upper()}: {path}")
    
    tool.report_generator.print_summary({'pr_info': {}, **results})


if __name__ == "__main__":
    demo_dsl_rules()
    demo_nested_complexity()
    demo_duplication_levels()
    demo_full_analysis()
    
    print("\n" + "=" * 70)
    print("所有演示完成！")
    print("=" * 70)
