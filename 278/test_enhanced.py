#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from k8s_linter import K8sConfigDetector, ReportFormatter, ContainerType, Severity

print("=" * 80)
print("Kubernetes 配置检测工具增强功能测试")
print("=" * 80)

detector = K8sConfigDetector()

print("\n" + "=" * 80)
print("测试 1: 扫描带 init 容器的 Deployment")
print("=" * 80)
report = detector.scan_file('examples/deployment_with_init.yaml')

print(f"\n总计发现 {len(report.issues)} 个问题")
print(f"  严重: {report.critical_count}")
print(f"  错误: {report.error_count}")
print(f"  警告: {report.warning_count}")
print(f"  信息: {report.info_count}")

print("\n按容器类型分类:")
print(f"  业务容器问题: {len(report.get_issues_by_container_type(ContainerType.REGULAR))}")
print(f"  Init容器问题: {len(report.get_issues_by_container_type(ContainerType.INIT))}")

print("\n详细问题列表:")
for issue in report.issues:
    type_label = {
        'regular': '业务',
        'init': 'Init',
        'ephemeral': '临时',
        '': 'Pod级'
    }.get(issue.container_type, issue.container_type)
    
    print(f"\n  [{issue.severity.value.upper()}] {issue.rule_id}")
    print(f"    消息: {issue.message}")
    print(f"    位置: {issue.resource_type}/{issue.resource_name}", end="")
    if issue.container_name:
        print(f" | {issue.container_name} ({type_label})")
    else:
        print(f" (Pod级)")

print("\n" + "=" * 80)
print("测试 2: 验证规则引擎布尔表达式")
print("=" * 80)

from k8s_linter.detector import ExpressionEvaluator

evaluator = ExpressionEvaluator()

test_cases = [
    ("is_regular_container", {'is_regular_container': True}, True),
    ("is_regular_container", {'is_regular_container': False}, False),
    ("not is_init_container", {'is_init_container': True}, False),
    ("not is_init_container", {'is_init_container': False}, True),
    ("is_regular_container or is_init_container", {'is_regular_container': True, 'is_init_container': False}, True),
    ("is_regular_container and is_init_container", {'is_regular_container': True, 'is_init_container': False}, False),
    ("kind == 'Deployment'", {'kind': 'Deployment'}, True),
    ("kind == 'Deployment'", {'kind': 'Pod'}, False),
    ("container_name == 'main-app'", {'container_name': 'main-app'}, True),
    ("container_count > 0", {'container_count': 2}, True),
    ("container_count > 5", {'container_count': 2}, False),
]

print("\n布尔表达式测试结果:")
passed = 0
failed = 0
for expr, context, expected in test_cases:
    result = evaluator.evaluate(expr, context)
    status = "✓" if result == expected else "✗"
    if result == expected:
        passed += 1
    else:
        failed += 1
    print(f"  {status} {expr} -> {result} (预期: {expected})")

print(f"\n总计: {passed} 通过, {failed} 失败")

print("\n" + "=" * 80)
print("测试 3: 扫描 bad_deployment.yaml (对比测试)")
print("=" * 80)

report2 = detector.scan_file('examples/bad_deployment.yaml')
print(ReportFormatter.format_console(report2, verbose=True))

print("\n" + "=" * 80)
print("增强功能测试完成!")
print("=" * 80)
