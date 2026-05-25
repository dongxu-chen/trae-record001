import sys
import os
sys.path.insert(0, '.')

print("=" * 60)
print("测试模块导入...")
print("=" * 60)

try:
    from src.impact_analyzer import ImpactAnalyzer
    print("✅ ImpactAnalyzer 导入成功")
except Exception as e:
    print(f"❌ ImpactAnalyzer 导入失败: {e}")

try:
    from src.ai_reviewer import AIReviewer
    print("✅ AIReviewer 导入成功")
except Exception as e:
    print(f"❌ AIReviewer 导入失败: {e}")

try:
    from src.effort_estimator import EffortEstimator
    print("✅ EffortEstimator 导入成功")
except Exception as e:
    print(f"❌ EffortEstimator 导入失败: {e}")

try:
    from src.code_review_tool import CodeReviewTool
    print("✅ CodeReviewTool 导入成功")
except Exception as e:
    print(f"❌ CodeReviewTool 导入失败: {e}")

print()
print("=" * 60)
print("测试模块功能...")
print("=" * 60)

print()
print("1. 测试 ImpactAnalyzer")
print("-" * 40)
try:
    analyzer = ImpactAnalyzer()
    print(f"   初始化成功: max_depth={analyzer.max_impact_depth}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print()
print("2. 测试 AIReviewer")
print("-" * 40)
try:
    reviewer = AIReviewer()
    print(f"   初始化成功: {len(reviewer.patterns)} 个审查模式")
    print(f"   模式示例: {[p.name for p in reviewer.patterns[:5]]}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print()
print("3. 测试 EffortEstimator")
print("-" * 40)
try:
    estimator = EffortEstimator()
    estimate = estimator.get_quick_estimate(100, 2, 'moderate')
    print(f"   初始化成功")
    print(f"   快速预估 (100行, 2文件, 中等复杂度): {estimate.get('human_readable')}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print()
print("=" * 60)
print("所有测试完成！")
print("=" * 60)
