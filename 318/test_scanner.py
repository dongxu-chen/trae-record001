"""
测试脚本 - 验证扫描器功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vuln_scanner.models import (
    Dependency,
    PackageManager,
    SeverityLevel,
)
from vuln_scanner.parsers import ParserFactory, PipParser, NpmParser, MavenParser, GoParser
from vuln_scanner.scanner import VulnerabilityScanner, SafetyDB
from vuln_scanner.scanner.version_utils import (
    parse_version,
    compare_versions,
    is_version_in_range,
    get_version_type,
)

print("=" * 60)
print("📋 测试版本工具")
print("=" * 60)

v1, v2 = "1.2.3", "1.2.4"
print(f"  parse_version('{v1}'): {parse_version(v1)}")
print(f"  compare_versions('{v1}', '{v2}'): {compare_versions(v1, v2)}")
print(f"  is_version_in_range('1.2.3', '<1.2.4'): {is_version_in_range('1.2.3', '<1.2.4')}")
print(f"  get_version_type('1.2.3', '1.3.0'): {get_version_type('1.2.3', '1.3.0')}")

print("\n" + "=" * 60)
print("📦 测试依赖解析器")
print("=" * 60)

test_projects = {
    "pip": "test_projects/pip_project",
    "npm": "test_projects/npm_project",
    "maven": "test_projects/maven_project",
    "go": "test_projects/go_project",
}

for pm_name, path in test_projects.items():
    parser = ParserFactory.detect_parser(path)
    if parser:
        deps = parser.parse()
        print(f"\n  [{pm_name}] {len(deps)} dependencies found:")
        for dep in deps:
            print(f"    - {dep.full_name} {dep.version}")

print("\n" + "=" * 60)
print("🔒 测试 Safety DB 漏洞匹配")
print("=" * 60)

safety_db = SafetyDB()
safety_db.load()

test_deps = [
    Dependency(name="django", version="3.2.15", package_manager=PackageManager.PIP),
    Dependency(name="requests", version="2.28.0", package_manager=PackageManager.PIP),
    Dependency(name="lodash", version="4.17.20", package_manager=PackageManager.NPM),
    Dependency(name="log4j-core", version="2.14.0", package_manager=PackageManager.MAVEN, group_id="org.apache.logging.log4j"),
    Dependency(name="golang.org/x/net", version="v0.10.0", package_manager=PackageManager.GO),
]

for dep in test_deps:
    vulns = safety_db.check_dependency(dep)
    print(f"\n  {dep.full_name} {dep.version}:")
    if vulns:
        for v in vulns:
            severity = SeverityLevel.from_cvss(v.get('cvss', 0))
            print(f"    - {v.get('cve', 'N/A')} [{severity.value} CVSS: {v.get('cvss', 0)}]")
            print(f"      {v.get('description', '')[:80]}...")
    else:
        print(f"    ✅ No vulnerabilities found")

print("\n" + "=" * 60)
print("🔍 测试完整扫描流程")
print("=" * 60)

scanner = VulnerabilityScanner(use_safety_db=True, use_nvd=False)

for pm_name, path in test_projects.items():
    parser = ParserFactory.detect_parser(path)
    if parser:
        deps = parser.parse()
        result = scanner.scan(deps, path)
        print(f"\n  [{pm_name}] {result.project_path}")
        print(f"    Dependencies: {len(result.dependencies)}")
        print(f"    Vulnerabilities: {len(result.vulnerabilities)}")
        if result.vulnerabilities:
            for v in result.vulnerabilities:
                print(f"    - {v.cve_id} [{v.severity.value}] {v.dependency.full_name} {v.dependency.version}")

print("\n" + "=" * 60)
print("✅ 所有测试完成！")
print("=" * 60)
