"""Security Fixer 单元测试"""

import json
import os
import tempfile
from pathlib import Path

from security_fixer.parsers import get_parser
from security_fixer.parsers.base_parser import Language, VulnerabilityType
from security_fixer.rules.rule_engine import RuleEngine
from security_fixer.rules.sql_injection_rule import SQLInjectionRule, DEFAULT_TABLE_WHITELIST
from security_fixer.rules.xss_rule import XSSRule
from security_fixer.fixers.fixer_engine import FixerEngine
from security_fixer.github.github_client import GitHubClient, PRCreateResult
from security_fixer.dependencies import DependencyChecker, DependencyFixer, VulnerableDependency
from security_fixer.validation import FixValidator, TestResult
from security_fixer.dashboard import TrendTracker, DashboardGenerator


SAMPLE_DIR = Path(__file__).parent / "samples"


def test_python_parser():
    parser = get_parser(Language.PYTHON)
    sample_file = SAMPLE_DIR / "vulnerable_python.py"
    source = parser.read_file(str(sample_file))
    ast_root = parser.parse(source, str(sample_file))
    assert ast_root is not None
    assert ast_root.node_type == "Module"
    imports = parser.extract_imports(ast_root)
    assert len(imports) > 0
    return "Python解析器测试通过"


def test_java_parser():
    parser = get_parser(Language.JAVA)
    sample_file = SAMPLE_DIR / "VulnerableJava.java"
    source = parser.read_file(str(sample_file))
    ast_root = parser.parse(source, str(sample_file))
    assert ast_root is not None
    imports = parser.extract_imports(ast_root)
    return "Java解析器测试通过"


def test_javascript_parser():
    parser = get_parser(Language.JAVASCRIPT)
    sample_file = SAMPLE_DIR / "vulnerable_javascript.js"
    source = parser.read_file(str(sample_file))
    ast_root = parser.parse(source, str(sample_file))
    assert ast_root is not None
    imports = parser.extract_imports(ast_root)
    assert len(imports) > 0
    return "JavaScript解析器测试通过"


def test_sql_injection_dynamic_table_whitelist():
    """测试动态表名白名单检测"""
    rule = SQLInjectionRule()

    test_code = '''
def get_data(request):
    table_name = request.args.get("table")
    query = f"SELECT * FROM {table_name} WHERE id = 1"
    cursor.execute(query)
'''

    from security_fixer.parsers.python_parser import PythonParser
    parser = PythonParser()
    ast_root = parser.parse(test_code, "test.py")

    vulns = rule.detect(ast_root, test_code, "test.py")

    print(f"  检测到的漏洞数: {len(vulns)}")
    for v in vulns:
        print(f"    - [{v.severity.value}] {v.message[:80]}")
        print(f"      auto_fixable: {v.auto_fixable}")

    assert len(vulns) > 0, "应检测到动态表名漏洞"

    has_non_auto_fixable = any(not v.auto_fixable for v in vulns)
    assert has_non_auto_fixable, "应标记为不可自动修复"

    has_table_alert = any("动态表名" in v.message for v in vulns)
    assert has_table_alert, "应包含动态表名告警"

    return "动态表名白名单检测测试通过"


def test_sql_injection_dynamic_table_in_whitelist():
    """测试动态表名在白名单内的情况"""
    rule = SQLInjectionRule()
    rule.update_table_whitelist(["mytable"])

    test_code = '''
def get_data(request):
    table_name = "mytable"
    query = f"SELECT * FROM {table_name} WHERE id = 1"
    cursor.execute(query)
'''

    from security_fixer.parsers.python_parser import PythonParser
    parser = PythonParser()
    ast_root = parser.parse(test_code, "test.py")

    vulns = rule.detect(ast_root, test_code, "test.py")

    print(f"  检测到的漏洞数: {len(vulns)}")
    for v in vulns:
        print(f"    - [{v.severity.value}] {v.message[:80]} (auto_fixable={v.auto_fixable})")

    return "白名单内动态表名检测测试通过"


def test_xss_dual_protection_detection():
    """测试XSS双重防护检测"""
    rule = XSSRule()

    test_code_without_protection = '''
def show_page(request):
    user_input = request.args.get("content")
    return HttpResponse(user_input)
'''

    from security_fixer.parsers.python_parser import PythonParser
    parser = PythonParser()
    ast_root = parser.parse(test_code_without_protection, "test.py")

    vulns = rule.detect(ast_root, test_code_without_protection, "test.py")

    print(f"  无防护代码检测到的漏洞数: {len(vulns)}")
    for v in vulns:
        print(f"    - [{v.severity.value}] {v.message[:80]}")
        if "has_output_escape" in v.context or "has_input_sanitization" in v.context:
            print(f"      has_escape: {v.context.get('has_output_escape', 'N/A')}")
            print(f"      has_sanitization: {v.context.get('has_input_sanitization', 'N/A')}")

    assert len(vulns) > 0, "应检测到XSS漏洞"

    has_severity_high = any(v.severity.value in ("high", "critical") for v in vulns)
    assert has_severity_high, "无防护时应为高严重程度"

    test_code_with_both = '''
import bleach
def show_page(request):
    user_input = bleach.clean(request.args.get("content"))
    return HttpResponse(escape(user_input))
'''

    ast_root2 = parser.parse(test_code_with_both, "test2.py")
    vulns2 = rule.detect(ast_root2, test_code_with_both, "test2.py")

    print(f"  有防护代码检测到的漏洞数: {len(vulns2)}")

    return "XSS双重防护检测测试通过"


def test_xss_protection_suggestions():
    """测试XSS防护建议"""
    rule = XSSRule()

    suggestion = rule._suggest_xss_fix(False, False, "python")
    print(f"  无防护建议: {suggestion[:100]}...")
    assert "输入过滤" in suggestion
    assert "输出转义" in suggestion

    suggestion2 = rule._suggest_xss_fix(True, False, "python")
    print(f"  仅转义建议: {suggestion2[:100]}...")
    assert "输入过滤" in suggestion2

    suggestion3 = rule._suggest_xss_fix(False, True, "python")
    print(f"  仅过滤建议: {suggestion3[:100]}...")
    assert "输出转义" in suggestion3

    suggestion4 = rule._suggest_xss_fix(True, True, "python")
    assert "双重防护" in suggestion4

    return "XSS防护建议测试通过"


def test_vulnerability_auto_fixable_flag():
    """测试auto_fixable标志在修复引擎中的行为"""
    engine = RuleEngine()
    fixer_engine = FixerEngine()
    sample_file = SAMPLE_DIR / "vulnerable_python.py"
    result = engine.scan_file(str(sample_file), Language.PYTHON)

    print(f"  检测到的漏洞:")
    for v in result.vulnerabilities:
        print(f"    - {v.vuln_type.value}: auto_fixable={v.auto_fixable}")

    auto_fixable_count = sum(1 for v in result.vulnerabilities if v.auto_fixable)
    non_auto_fixable_count = sum(1 for v in result.vulnerabilities if not v.auto_fixable)

    print(f"  可自动修复: {auto_fixable_count}, 不可自动修复: {non_auto_fixable_count}")

    fix_result = fixer_engine.fix_file(
        str(sample_file),
        result.vulnerabilities,
        Language.PYTHON,
    )

    print(f"  实际修复: {fix_result.success_count}, 跳过: {fix_result.skipped_count}")

    assert fix_result.success_count <= auto_fixable_count, "只修复可自动修复的漏洞"
    assert fix_result.skipped_count >= non_auto_fixable_count, "跳过不可自动修复的漏洞"

    return "auto_fixable标志测试通过"


def test_rule_engine_scan_python():
    engine = RuleEngine()
    sample_file = SAMPLE_DIR / "vulnerable_python.py"
    result = engine.scan_file(str(sample_file), Language.PYTHON)

    assert result.parse_error is None, f"解析错误: {result.parse_error}"
    assert len(result.vulnerabilities) > 0, "应检测到至少一个漏洞"

    vuln_types = set(v.vuln_type for v in result.vulnerabilities)
    print(f"  检测到的漏洞类型: {vuln_types}")
    print(f"  漏洞数量: {len(result.vulnerabilities)}")

    for v in result.vulnerabilities:
        print(f"    - [{v.severity.value}] {v.vuln_type.value}: {v.message[:80]} (auto_fixable={v.auto_fixable})")

    return f"Python扫描测试通过，发现 {len(result.vulnerabilities)} 个漏洞"


def test_rule_engine_scan_java():
    engine = RuleEngine()
    sample_file = SAMPLE_DIR / "VulnerableJava.java"
    result = engine.scan_file(str(sample_file), Language.JAVA)

    assert result.parse_error is None, f"解析错误: {result.parse_error}"
    print(f"  漏洞数量: {len(result.vulnerabilities)}")

    for v in result.vulnerabilities:
        print(f"    - [{v.severity.value}] {v.vuln_type.value}: {v.message[:80]}")

    return f"Java扫描测试通过"


def test_rule_engine_scan_javascript():
    engine = RuleEngine()
    sample_file = SAMPLE_DIR / "vulnerable_javascript.js"
    result = engine.scan_file(str(sample_file), Language.JAVASCRIPT)

    assert result.parse_error is None, f"解析错误: {result.parse_error}"
    print(f"  漏洞数量: {len(result.vulnerabilities)}")

    for v in result.vulnerabilities:
        print(f"    - [{v.severity.value}] {v.vuln_type.value}: {v.message[:80]}")

    return f"JavaScript扫描测试通过"


def test_fix_engine_python():
    engine = RuleEngine()
    fixer_engine = FixerEngine()
    sample_file = SAMPLE_DIR / "vulnerable_python.py"
    result = engine.scan_file(str(sample_file), Language.PYTHON)

    if not result.has_vulnerabilities:
        return "无漏洞可修复"

    fix_result = fixer_engine.fix_file(
        str(sample_file),
        result.vulnerabilities,
        Language.PYTHON,
    )

    print(f"  修复前漏洞数: {len(result.vulnerabilities)}")
    print(f"  已修复: {fix_result.success_count}")
    print(f"  跳过: {fix_result.skipped_count}")
    print(f"  文件已更改: {fix_result.is_changed}")

    return f"Python修复测试通过: 修复{fix_result.success_count}个漏洞"


def test_fix_engine_java():
    engine = RuleEngine()
    fixer_engine = FixerEngine()
    sample_file = SAMPLE_DIR / "VulnerableJava.java"
    result = engine.scan_file(str(sample_file), Language.JAVA)

    if not result.has_vulnerabilities:
        return "无漏洞可修复"

    fix_result = fixer_engine.fix_file(
        str(sample_file),
        result.vulnerabilities,
        Language.JAVA,
    )

    print(f"  已修复: {fix_result.success_count}")
    print(f"  跳过: {fix_result.skipped_count}")

    return f"Java修复测试通过"


def test_fix_engine_javascript():
    engine = RuleEngine()
    fixer_engine = FixerEngine()
    sample_file = SAMPLE_DIR / "vulnerable_javascript.js"
    result = engine.scan_file(str(sample_file), Language.JAVASCRIPT)

    if not result.has_vulnerabilities:
        return "无漏洞可修复"

    fix_result = fixer_engine.fix_file(
        str(sample_file),
        result.vulnerabilities,
        Language.JAVASCRIPT,
    )

    print(f"  已修复: {fix_result.success_count}")
    print(f"  跳过: {fix_result.skipped_count}")

    return f"JavaScript修复测试通过"


def test_summary_report():
    engine = RuleEngine()
    sample_dir = SAMPLE_DIR
    results = engine.scan_directory(str(sample_dir))

    summary = engine.get_vulnerability_summary(results)

    print(f"  扫描文件数: {summary['summary']['total_files_scanned']}")
    print(f"  含漏洞文件: {summary['summary']['files_with_vulnerabilities']}")
    print(f"  漏洞总数: {summary['summary']['total_vulnerabilities']}")
    print(f"  按类型: {summary['summary']['by_type']}")
    print(f"  按严重程度: {summary['summary']['by_severity']}")

    assert summary["summary"]["total_vulnerabilities"] > 0
    return "汇总报告测试通过"


def test_github_client_rollback_feature():
    """测试GitHub客户端的回退功能"""
    github = GitHubClient()

    assert hasattr(github, 'close_pull_request'), "应有close_pull_request方法"
    assert hasattr(github, 'add_pr_comment'), "应有add_pr_comment方法"
    assert hasattr(github, 'delete_local_branch'), "应有delete_local_branch方法"
    assert hasattr(github, 'delete_remote_branch'), "应有delete_remote_branch方法"
    assert hasattr(github, 'rollback_pr_creation'), "应有rollback_pr_creation方法"

    result = PRCreateResult(success=False, branch_name="test-branch")
    assert hasattr(result, 'rolled_back'), "PRCreateResult应有rolled_back字段"
    assert hasattr(result, 'rollback_details'), "PRCreateResult应有rollback_details字段"

    return "GitHub回退功能接口测试通过"


def test_dependency_checker_python():
    """测试Python依赖漏洞检测"""
    checker = DependencyChecker()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(Path(temp_dir) / "requirements.txt")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write("requests==2.28.0\n")
            f.write("django==3.2.0\n")
            f.write("flask==2.2.0\n")
            f.write("safe-package==1.0.0\n")

        vulns = checker._scan_python_deps(temp_path)

        print(f"  检测到的漏洞依赖: {len(vulns)}")
        for v in vulns:
            print(f"    - {v.name}: {v.current_version} -> {v.fixed_version}")

        vuln_names = [v.name for v in vulns]
        assert "requests" in vuln_names, "应检测到requests漏洞"
        assert "django" in vuln_names, "应检测到django漏洞"
        assert "flask" in vuln_names, "应检测到flask漏洞"
        assert "safe-package" not in vuln_names, "安全包不应被检测"

        return "Python依赖漏洞检测测试通过"


def test_dependency_checker_javascript():
    """测试JavaScript依赖漏洞检测"""
    checker = DependencyChecker()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(Path(temp_dir) / "package.json")
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump({
                "dependencies": {
                    "lodash": "^4.17.20",
                    "express": "^4.17.2",
                    "axios": "^0.21.1",
                    "safe-package": "^1.0.0"
                }
            }, f)

        vulns = checker._scan_javascript_deps(temp_path)

        print(f"  检测到的漏洞依赖: {len(vulns)}")
        for v in vulns:
            print(f"    - {v.name}: {v.current_version} -> {v.fixed_version}")

        vuln_names = [v.name for v in vulns]
        assert "lodash" in vuln_names, "应检测到lodash漏洞"
        assert "express" in vuln_names, "应检测到express漏洞"
        assert "safe-package" not in vuln_names, "安全包不应被检测"

        return "JavaScript依赖漏洞检测测试通过"


def test_dependency_fixer():
    """测试依赖漏洞修复"""
    fixer = DependencyFixer(backup=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = str(Path(temp_dir) / "requirements.txt")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write("requests==2.28.0\n")
            f.write("django==3.2.0\n")

        vulns = [
            VulnerableDependency(
                name="requests",
                current_version="2.28.0",
                fixed_version="2.31.0",
                severity="high",
                vulnerability_id="CVE-2023-32681",
                description="requests漏洞",
                language="python",
                dependency_file=temp_path
            )
        ]

        result = fixer._fix_dependency_file(temp_path, vulns, "python")

        print(f"  修复结果: {result.fixed_count} 个已修复, {result.skipped_count} 个跳过")
        print(f"  备份已创建: {result.backup_created}")

        content = Path(temp_path).read_text(encoding='utf-8')
        assert "requests>=2.31.0" in content, "应更新requests版本"

        backup_exists = Path(temp_path + ".bak").exists()
        print(f"  备份文件存在: {backup_exists}")

        return "依赖漏洞修复测试通过"


def test_fix_validator():
    """测试修复验证器"""
    with tempfile.TemporaryDirectory() as temp_dir:
        validator = FixValidator(project_root=temp_dir)

        framework = validator.detect_test_framework()
        print(f"  检测到的测试框架: {framework}")

        test_result = validator.run_tests("python")
        print(f"  测试结果: passed={test_result.passed}, exit_code={test_result.exit_code}")
        print(f"  耗时: {test_result.duration:.2f}秒")

        assert isinstance(test_result.passed, bool)
        assert isinstance(test_result.exit_code, int)
        assert test_result.duration >= 0

        return "修复验证器测试通过"


def test_trend_tracker():
    """测试趋势跟踪器"""
    with tempfile.TemporaryDirectory() as temp_dir:
        tracker = TrendTracker(data_dir=temp_dir)

        class MockScanResult:
            def __init__(self, file_path, vulnerabilities):
                self.file_path = file_path
                self.vulnerabilities = vulnerabilities

        class MockVulnerability:
            def __init__(self, vuln_type, severity, auto_fixable):
                self.vuln_type = vuln_type
                self.severity = severity
                self.auto_fixable = auto_fixable

        from security_fixer.parsers.base_parser import VulnerabilityType, Severity

        scan_results = [
            MockScanResult("test.py", [
                MockVulnerability(VulnerabilityType.SQL_INJECTION, Severity.HIGH, True),
                MockVulnerability(VulnerabilityType.XSS, Severity.MEDIUM, False),
            ]),
            MockScanResult("VulnerableJava.java", [
                MockVulnerability(VulnerabilityType.PATH_TRAVERSAL, Severity.HIGH, True),
            ])
        ]

        data_point = tracker.record_scan(scan_results)

        print(f"  漏洞总数: {data_point.total_vulnerabilities}")
        print(f"  按语言: {data_point.by_language}")
        print(f"  按类型: {data_point.by_type}")
        print(f"  按严重程度: {data_point.by_severity}")
        print(f"  可自动修复: {data_point.auto_fixable}")
        print(f"  需人工修复: {data_point.non_auto_fixable}")

        assert data_point.total_vulnerabilities == 3
        assert "python" in data_point.by_language
        assert "java" in data_point.by_language
        assert data_point.auto_fixable == 2
        assert data_point.non_auto_fixable == 1

        trend = tracker.get_trend(days=30)
        print(f"  趋势数据点: {len(trend)}")

        return "趋势跟踪器测试通过"


def test_dashboard_generator():
    """测试仪表盘生成器"""
    with tempfile.TemporaryDirectory() as temp_dir:
        generator = DashboardGenerator(data_dir=temp_dir)

        class MockScanResult:
            def __init__(self, file_path, vulnerabilities):
                self.file_path = file_path
                self.vulnerabilities = vulnerabilities

        class MockVulnerability:
            def __init__(self, vuln_type, severity, auto_fixable):
                self.vuln_type = vuln_type
                self.severity = severity
                self.auto_fixable = auto_fixable

        from security_fixer.parsers.base_parser import VulnerabilityType, Severity

        scan_results = [
            MockScanResult("test.py", [
                MockVulnerability(VulnerabilityType.SQL_INJECTION, Severity.CRITICAL, True),
                MockVulnerability(VulnerabilityType.XSS, Severity.HIGH, False),
            ])
        ]

        text_report = generator.generate_text_report(scan_results)
        print(f"  文本报告长度: {len(text_report)}")
        assert "安全漏洞趋势仪表盘" in text_report
        assert "SQL_INJECTION" in text_report or "sql_injection" in text_report

        html_path = str(Path(temp_dir) / "test_dashboard.html")
        generator.generate_html_report(scan_results, html_path)
        assert Path(html_path).exists()

        json_path = str(Path(temp_dir) / "test_dashboard.json")
        generator.generate_json_report(scan_results, json_path)
        assert Path(json_path).exists()

        return "仪表盘生成器测试通过"


def run_all_tests():
    tests = [
        ("Python解析器", test_python_parser),
        ("Java解析器", test_java_parser),
        ("JavaScript解析器", test_javascript_parser),
        ("SQL注入动态表名白名单", test_sql_injection_dynamic_table_whitelist),
        ("SQL注入白名单内表名", test_sql_injection_dynamic_table_in_whitelist),
        ("XSS双重防护检测", test_xss_dual_protection_detection),
        ("XSS防护建议", test_xss_protection_suggestions),
        ("auto_fixable标志", test_vulnerability_auto_fixable_flag),
        ("Python扫描", test_rule_engine_scan_python),
        ("Java扫描", test_rule_engine_scan_java),
        ("JavaScript扫描", test_rule_engine_scan_javascript),
        ("Python修复", test_fix_engine_python),
        ("Java修复", test_fix_engine_java),
        ("JavaScript修复", test_fix_engine_javascript),
        ("汇总报告", test_summary_report),
        ("GitHub回退功能", test_github_client_rollback_feature),
        ("Python依赖检测", test_dependency_checker_python),
        ("JavaScript依赖检测", test_dependency_checker_javascript),
        ("依赖漏洞修复", test_dependency_fixer),
        ("修复验证器", test_fix_validator),
        ("趋势跟踪器", test_trend_tracker),
        ("仪表盘生成器", test_dashboard_generator),
    ]

    print("=" * 70)
    print("Security Fixer 测试套件 (增强版)")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n📋 测试: {name}")
        try:
            result = test_func()
            print(f"   ✅ {result}")
            passed += 1
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"测试结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 个测试")
    print(f"{'=' * 70}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
