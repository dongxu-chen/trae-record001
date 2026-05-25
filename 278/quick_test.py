import sys
sys.path.insert(0, '.')

from k8s_linter import K8sConfigDetector, ContainerType

detector = K8sConfigDetector()
report = detector.scan_file('examples/deployment_with_init.yaml')

print('=' * 60)
print('Test Result')
print('=' * 60)
print(f'Total issues: {len(report.issues)}')
print(f'Critical: {report.critical_count}')
print(f'Error: {report.error_count}')
print(f'Warning: {report.warning_count}')
print(f'Info: {report.info_count}')

print()
print('By container type:')
print(f'  Regular: {len(report.get_issues_by_container_type(ContainerType.REGULAR))}')
print(f'  Init: {len(report.get_issues_by_container_type(ContainerType.INIT))}')

print()
print('Issues:')
for issue in report.issues:
    ct = issue.container_type or 'Pod-level'
    print(f'  [{issue.severity.value.upper()}] {issue.rule_id} ({ct})')
    print(f'      {issue.message}')
