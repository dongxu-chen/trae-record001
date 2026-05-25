#!/usr/bin/env python3
import sys
import yaml
sys.path.insert(0, '.')

from k8s_linter import K8sConfigDetector, AutoFixer, ClusterConfigComparer
from k8s_linter.admission_webhook import AdmissionController, AdmissionReview

print("=" * 80)
print("Kubernetes 配置检测工具高级功能测试")
print("=" * 80)

print("\n" + "=" * 80)
print("测试 1: 自动修复功能")
print("=" * 80)

detector = K8sConfigDetector()
auto_fixer = AutoFixer()

with open('examples/bad_deployment.yaml', 'r') as f:
    original_content = f.read()

print("\n原始配置:")
print("-" * 40)
print(original_content)

report = detector.scan_file('examples/bad_deployment.yaml')
print(f"\n发现 {len(report.issues)} 个问题")

fixes = auto_fixer.generate_fixes(report.issues)
print(f"可修复 {len(fixes)} 个问题")

print("\n修复列表:")
for i, fix in enumerate(fixes, 1):
    print(f"  {i}. {fix.description} ({fix.rule_id})")

success, fixed_content = auto_fixer.apply_fixes_to_file('examples/bad_deployment.yaml', issues=report.issues)
if success:
    print("\n修复后的配置:")
    print("-" * 40)
    print(fixed_content)
else:
    print("\n修复失败")

print("\n" + "=" * 80)
print("测试 2: 集群配置漂移检测 (无kubectl环境模拟)")
print("=" * 80)

comparer = ClusterConfigComparer()

if comparer.is_available():
    print("kubectl 可用，可以连接集群")
else:
    print("kubectl 不可用，跳过实际集群连接测试")
    print("提示：安装 kubectl 并配置 kubeconfig 后可使用漂移检测功能")

print("\n漂移检测功能说明:")
print("  - 连接运行中的Kubernetes集群")
print("  - 对比YAML配置与集群实际配置")
print("  - 检测资源spec、标签、注解的差异")
print("  - 忽略动态字段(status, resourceVersion等)")

print("\n" + "=" * 80)
print("测试 3: 准入控制Webhook")
print("=" * 80)

controller = AdmissionController(deny_on_severity='error')

admission_request = {
    'apiVersion': 'admission.k8s.io/v1',
    'kind': 'AdmissionReview',
    'request': {
        'uid': 'test-request-123',
        'kind': {'group': '', 'version': 'v1', 'kind': 'Deployment'},
        'name': 'test-app',
        'namespace': 'default',
        'operation': 'CREATE',
        'object': yaml.safe_load(open('examples/bad_deployment.yaml')),
        'dryRun': True
    }
}

print("\n测试准入控制验证:")
print("-" * 40)

response = controller.handle_admission_review(admission_request)
allowed = response['response']['allowed']
warnings = response['response'].get('warnings', [])
status = response['response']['status']

print(f"允许: {'是' if allowed else '否'}")
print(f"状态码: {status.get('code')}")
print(f"状态消息: {status.get('message')}")
print(f"警告数量: {len(warnings)}")

if warnings:
    print("\n警告详情:")
    for i, warning in enumerate(warnings[:5], 1):
        print(f"  {i}. {warning}")
    if len(warnings) > 5:
        print(f"  ... 还有 {len(warnings) - 5} 条警告")

print("\n" + "=" * 80)
print("高级功能测试完成!")
print("=" * 80)
print("\n新增功能总结:")
print("""
1. 自动修复 (fix 命令)
   - 支持资源配置自动添加
   - 支持安全上下文自动修复
   - 支持镜像标签自动更新
   - 支持预览和就地修改

2. 配置漂移检测 (drift 命令)
   - 连接运行中的集群
   - 对比YAML与实际配置
   - 检测spec、标签、注解差异

3. 准入控制Webhook (webhook 命令)
   - 启动验证Webhook服务器
   - 实时拦截不合规配置
   - 支持按错误等级拒绝
   - 生成部署清单和证书
""")
