import sys
sys.path.insert(0, '.')

from k8s_linter import K8sConfigDetector, ReportFormatter

detector = K8sConfigDetector()
report = detector.scan_file('examples/bad_deployment.yaml')

print('=' * 60)
print('K8s Config Linter Test')
print('=' * 60)
print(f'Total issues: {len(report.issues)}')
print(f'Critical: {report.critical_count}')
print(f'Error: {report.error_count}')
print(f'Warning: {report.warning_count}')
print(f'Info: {report.info_count}')
print()

for issue in report.issues[:5]:
    print(f'[{issue.severity.value}] {issue.message}')
    print(f'  File: {issue.file_path}')
    print(f'  Rule: {issue.rule_id}')
    print()
