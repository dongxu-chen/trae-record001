#!/usr/bin/env python3
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.impact_analyzer import ImpactAnalyzer
from src.ai_reviewer import AIReviewer
from src.effort_estimator import EffortEstimator
from src.code_review_tool import CodeReviewTool


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def create_test_code() -> str:
    return '''
# 测试代码 - 包含各种模式的示例
import os
import sys
import random

API_KEY = "sk-1234567890abcdef"

def process_data(data, items=[]):
    """处理数据"""
    if data is None:
        return []
    
    password = "mypassword123"
    
    result = []
    for item in items:
        if item > 10:
            if item < 100:
                if item % 2 == 0:
                    if item % 3 == 0:
                        if item % 5 == 0:
                            result.append(item * 2)
    
    try:
        risky_operation()
    except:
        pass
    
    return result


def risky_operation():
    # TODO: 实现错误处理
    print("执行危险操作")
    
    f = open("data.txt")
    content = f.read()
    
    for i in range(len(content)):
        char = content[i]
        if char == "a":
            pass
    
    token = random.randint(1000, 9999)
    
    user_id = 123
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    return content


def calculate_complex(a, b, c, d, e, f, g):
    """参数过多的函数"""
    if a > b:
        if c > d:
            if e > f:
                if g > 0:
                    return a + b + c + d + e + f + g
    return 0


class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_item(self, item):
        self.data.append(item)
    
    def process_all(self):
        # FIXME: 优化性能
        result = []
        for item in self.data:
            processed = process_data(item, self.data)
            result.extend(processed)
        return result
'''


def demo_1_impact_analysis():
    print_separator("演示1: 变更影响分析")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "core.py")
        file2 = os.path.join(tmpdir, "utils.py")
        file3 = os.path.join(tmpdir, "main.py")
        
        with open(file1, 'w') as f:
            f.write('''
def core_function():
    return "core"

def helper_function():
    return core_function()
''')
        
        with open(file2, 'w') as f:
            f.write('''
from core import helper_function

def utility_function():
    return helper_function() + " utility"

def another_function():
    return utility_function()
''')
        
        with open(file3, 'w') as f:
            f.write('''
from utils import another_function

def main():
    result = another_function()
    print(result)
    return result

def secondary():
    return "secondary"
''')
        
        print("测试代码结构:")
        print("  core.py -> core_function, helper_function")
        print("  utils.py -> utility_function (调用 helper_function), another_function")
        print("  main.py -> main (调用 another_function), secondary")
        print()
        
        changed_files = ["core.py"]
        print(f"变更文件: {changed_files}")
        print()
        
        analyzer = ImpactAnalyzer()
        result = analyzer.analyze_directory(tmpdir, changed_files)
        
        print("变更函数:")
        for func in result.get('changed_functions', []):
            print(f"  ✅ {func}")
        print()
        
        impact_summary = result.get('impact_summary', {})
        print("影响分析摘要:")
        print(f"  受影响函数数: {impact_summary.get('total_impacted_functions', 0)}")
        print(f"  最大影响深度: {impact_summary.get('max_impact_depth', 0)}")
        print(f"  受影响文件数: {len(impact_summary.get('impacted_files', []))}")
        print(f"  影响链数量: {impact_summary.get('chain_count', 0)}")
        print()
        
        risk = result.get('risk_assessment', {})
        print(f"影响风险等级: {risk.get('level', 'unknown').upper()} (分数: {risk.get('score', 0)})")
        print()
        
        print("影响链 (调用关系):")
        for chain in result.get('impact_chains', [])[:5]:
            path = " → ".join([p.split('::')[-1] for p in chain.get('path', [])])
            print(f"  {path} (深度: {chain.get('depth', 0)})")
        
        print()
        print("✅ 变更影响分析可帮助识别:")
        print("   - 哪些函数会受到变更的影响")
        print("   - 变更的传递深度")
        print("   - 变更的整体风险等级")


def demo_2_ai_review():
    print_separator("演示2: AI智能审查建议")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "problematic_code.py")
        with open(test_file, 'w') as f:
            f.write(create_test_code())
        
        print("分析包含以下问题的代码:")
        print("  - 硬编码敏感信息 (API_KEY, password)")
        print("  - 可变默认参数 (items=[])")
        print("  - 静默忽略异常 (except: pass)")
        print("  - 不安全的随机数 (random)")
        print("  - 资源泄漏风险 (open without with)")
        print("  - 调试打印语句 (print)")
        print("  - 待办事项 (TODO, FIXME)")
        print("  - 函数嵌套过深")
        print("  - 参数过多")
        print()
        
        reviewer = AIReviewer()
        result = reviewer.review_directory(tmpdir)
        
        summary = result.get('summary', {})
        print("AI审查结果摘要:")
        print(f"  总建议数: {summary.get('total_comments', 0)}")
        print(f"  整体评级: {summary.get('overall_grade', 'N/A')}")
        print(f"  风险分数: {summary.get('risk_score', 0)}")
        print()
        
        print("按严重程度分类:")
        for severity, count in summary.get('by_severity', {}).items():
            if count > 0:
                icon = "🔴" if severity == 'critical' else "🟠" if severity == 'high' else "🟡" if severity == 'medium' else "🟢"
                print(f"  {icon} {severity.upper()}: {count}")
        print()
        
        print("按类别分类:")
        for category, count in summary.get('by_category', {}).items():
            print(f"  📁 {category}: {count}")
        print()
        
        print("详细审查建议 (前10条):")
        for comment in result.get('all_comments', [])[:10]:
            severity = comment.get('severity', 'low')
            icon = "🔴" if severity == 'critical' else "🟠" if severity == 'high' else "🟡" if severity == 'medium' else "🟢"
            print(f"\n  {icon} [{severity.upper()}] {comment.get('title', '')}")
            print(f"     📄 {comment.get('file', '')}:{comment.get('line', 0)}")
            print(f"     💬 {comment.get('message', '')}")
            print(f"     💡 建议: {comment.get('suggestion', '')}")
            print(f"     🎯 置信度: {comment.get('confidence', 0):.0%}")
        
        print()
        print("✅ AI审查系统内置18种常见问题模式:")
        print("   - 安全类: 硬编码密钥、SQL注入、不安全随机数")
        print("   - 质量类: 函数过长、嵌套过深、参数过多")
        print("   - 最佳实践: 可变默认参数、空值检查、资源管理")
        print("   - 错误处理: 静默异常、捕获过宽")
        print("   - 代码风格: 未使用导入、调试语句、待办事项")


def demo_3_effort_estimation():
    print_separator("演示3: 审查工作量预估")
    
    estimator = EffortEstimator()
    
    print("快速预估示例 (基于代码行数):")
    scenarios = [
        (50, 1, 'simple', "小型修复"),
        (200, 3, 'moderate', "功能增强"),
        (500, 5, 'complex', "新功能开发"),
        (1000, 10, 'very_complex', "重大重构"),
    ]
    
    for lines, files, complexity, desc in scenarios:
        estimate = estimator.get_quick_estimate(lines, files, complexity)
        print(f"  📋 {desc}: {lines}行 / {files}文件 / {complexity}")
        print(f"     ⏱️  预估时间: {estimate.get('human_readable', 'N/A')}")
        print()
    
    print("-" * 60)
    print()
    print("实际代码文件预估:")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "simple_module.py")
        file2 = os.path.join(tmpdir, "complex_module.py")
        
        with open(file1, 'w') as f:
            f.write('''
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
''')
        
        with open(file2, 'w') as f:
            f.write(create_test_code())
        
        result = estimator.estimate_from_changes([file1, file2])
        
        print(f"总预估时间: {result.get('human_readable', 'N/A')}")
        print(f"复杂度等级: {result.get('complexity_level', 'unknown').upper()}")
        print()
        
        print("各文件预估 (按审查时间排序):")
        for file_est in result.get('file_estimates', []):
            filename = os.path.basename(file_est.get('file', ''))
            print(f"  📄 {filename}")
            print(f"     代码行数: {file_est.get('lines_changed', 0)}")
            print(f"     复杂度分数: {file_est.get('complexity_score', 0):.1f}x")
            print(f"     预估时间: {file_est.get('estimated_minutes', 0):.1f} 分钟")
            print()
        
        risk_factors = result.get('risk_factors', [])
        if risk_factors:
            print("⚠️  风险因素:")
            for factor in risk_factors:
                print(f"  - {factor}")
            print()
        
        recommendations = result.get('recommendations', [])
        if recommendations:
            print("💡 建议:")
            for rec in recommendations:
                print(f"  - {rec}")
        
        print()
        print("✅ 工作量预估考虑因素:")
        print("   - 代码行数")
        print("   - 决策点数量 (if/for/while等)")
        print("   - 函数数量")
        print("   - 嵌套深度")
        print("   - 语言类型系数")
        print("   - 关键路径乘数")
        print("   - 上下文切换开销")
        print("   - 初始化时间")


def demo_4_full_integration():
    print_separator("演示4: 完整集成审查")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "sample_code.py")
        with open(test_file, 'w') as f:
            f.write(create_test_code())
        
        print("运行完整代码审查...")
        print()
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "config.yaml"
        )
        
        tool = CodeReviewTool(config_path=config_path)
        results = tool.analyze_directory(tmpdir)
        
        print("📊 审查结果概览:")
        print()
        
        print("  🔍 变更影响分析:")
        impact = results.get('impact_analysis', {})
        summary = impact.get('impact_summary', {})
        print(f"     变更函数: {len(impact.get('changed_functions', []))}")
        print(f"     受影响函数: {summary.get('total_impacted_functions', 0)}")
        print(f"     风险等级: {impact.get('risk_assessment', {}).get('level', 'unknown').upper()}")
        print()
        
        print("  🤖 AI审查建议:")
        ai = results.get('ai_review', {})
        ai_summary = ai.get('summary', {})
        print(f"     建议数量: {ai_summary.get('total_comments', 0)}")
        print(f"     整体评级: {ai_summary.get('overall_grade', 'N/A')}")
        for sev in ['critical', 'high', 'medium', 'low']:
            count = ai_summary.get('by_severity', {}).get(sev, 0)
            if count > 0:
                print(f"     {sev.upper()}: {count}")
        print()
        
        print("  ⏱️  审查工作量预估:")
        effort = results.get('effort_estimate', {})
        print(f"     预估时间: {effort.get('human_readable', 'N/A')}")
        print(f"     复杂度等级: {effort.get('complexity_level', 'unknown').upper()}")
        print(f"     文件数量: {effort.get('summary', {}).get('total_files', 0)}")
        print()
        
        print("  📈 整体风险评估:")
        risk = tool.report_generator.calculate_risk_score(results)
        print(f"     风险分数: {risk.get('risk_score', 0)}")
        print(f"     风险等级: {risk.get('risk_level', 'unknown').upper()}")
        print()
        
        print("✅ 完整集成审查完成！")
        print()
        print("📋 生成的报告包含:")
        print("   - 代码规范检查 (linting)")
        print("   - 圈复杂度分析")
        print("   - 重复代码检测")
        print("   - DSL规则检查")
        print("   - 👉 变更影响分析 (新增)")
        print("   - 👉 AI智能审查建议 (新增)")
        print("   - 👉 审查工作量预估 (新增)")


if __name__ == "__main__":
    print("\n" + "#" * 80)
    print("#" + " " * 78 + "#")
    print("#" + " " * 20 + "代码审查工具 - 新功能演示" + " " * 32 + "#")
    print("#" + " " * 78 + "#")
    print("#" * 80)
    
    demo_1_impact_analysis()
    demo_2_ai_review()
    demo_3_effort_estimation()
    demo_4_full_integration()
    
    print()
    print("=" * 80)
    print("  演示完成！所有新功能已集成到主工具中。")
    print("=" * 80 + "\n")
