#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from k8s_linter import K8sConfigDetector, ReportFormatter

print("=" * 80)
print("测试 Kubernetes 配置检测工具")
print("=" * 80)

detector = K8sConfigDetector()

print("\n1. 扫描 bad_deployment.yaml (有很多问题的配置)")
print("-" * 80)
report = detector.scan_file('examples/bad_deployment.yaml')
print(ReportFormatter.format_console(report, verbose=True))

print("\n" + "=" * 80)
print("\n2. 扫描 good_deployment.yaml (良好的配置)")
print("-" * 80)
report2 = detector.scan_file('examples/good_deployment.yaml')
print(ReportFormatter.format_console(report2, verbose=True))

print("\n" + "=" * 80)
print("\n3. 扫描 medium_deployment.yaml (中等配置)")
print("-" * 80)
report3 = detector.scan_file('examples/medium_deployment.yaml')
print(ReportFormatter.format_console(report3, verbose=True))

print("\n" + "=" * 80)
print("\n4. 扫描整个 examples 目录")
print("-" * 80)
report4 = detector.scan_directory('examples')
print(f"总计发现 {len(report4.issues)} 个问题")
print(f"  严重: {report4.critical_count}")
print(f"  错误: {report4.error_count}")
print(f"  警告: {report4.warning_count}")
print(f"  信息: {report4.info_count}")

print("\n" + "=" * 80)
print("测试完成!")
print("=" * 80)
