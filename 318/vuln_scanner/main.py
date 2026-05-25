"""
依赖项安全漏洞扫描器主入口
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import (
    ScanResult,
    Dependency,
    Vulnerability,
    FixSuggestion,
    SeverityLevel,
    PackageManager,
)
from .parsers import ParserFactory
from .parsers.dependency_tree import DependencyTreeResolverFactory, DependencyTree
from .scanner import VulnerabilityScanner
from .analyzer import ImpactAnalyzer, SeverityEvaluator
from .fixer import VersionSuggester, DependencyUpdater
from .github_integration import GitHubAPIClient, PRCreator
from .github_integration.pr_tester import PRPreTester


class DependencyVulnerabilityScanner:
    """完整的依赖漏洞扫描器"""

    def __init__(
        self,
        project_path: str,
        use_safety_db: bool = True,
        use_nvd: bool = False,
        nvd_api_key: Optional[str] = None,
        min_severity: SeverityLevel = SeverityLevel.LOW,
        auto_fix: bool = False,
        github_token: Optional[str] = None,
        include_transitive: bool = True,
        nvd_sync_interval: int = 3600,
        nvd_auto_sync: bool = True,
    ):
        self.project_path = os.path.abspath(project_path)
        self.auto_fix = auto_fix
        self.min_severity = min_severity
        self.include_transitive = include_transitive

        self.parser = None
        self.dependency_tree: Optional[DependencyTree] = None

        self.scanner = VulnerabilityScanner(
            use_safety_db=use_safety_db,
            use_nvd=use_nvd,
            nvd_api_key=nvd_api_key,
            min_severity=min_severity,
            nvd_sync_interval=nvd_sync_interval,
            nvd_auto_sync=nvd_auto_sync,
        )
        self.impact_analyzer = ImpactAnalyzer()
        self.severity_evaluator = SeverityEvaluator()
        self.version_suggester = VersionSuggester(use_remote=True)

        if github_token:
            self.github_client = GitHubAPIClient(token=github_token)
            self.pr_creator = PRCreator(self.github_client)
            self.pr_tester = PRPreTester(self.project_path)
        else:
            self.github_client = None
            self.pr_creator = None
            self.pr_tester = None

    def scan(self, package_manager: Optional[PackageManager] = None) -> ScanResult:
        """执行完整扫描流程"""
        print(f"🔍 Scanning project: {self.project_path}")

        if package_manager:
            self.parser = ParserFactory.get_parser(package_manager, self.project_path)
        else:
            self.parser = ParserFactory.detect_parser(self.project_path)

        if not self.parser:
            raise ValueError(
                f"Could not detect project type or find dependency files in {self.project_path}"
            )

        print(f"📦 Detected package manager: {self.parser.package_manager.value}")

        if self.include_transitive:
            print("🌳 Resolving full dependency tree (including transitive)...")
            tree_resolver = DependencyTreeResolverFactory.get_resolver(
                self.parser.package_manager,
                self.project_path,
            )
            self.dependency_tree = tree_resolver.resolve(include_transitive=True)
            dependencies = self.dependency_tree.flatten()

            direct_count = len(self.dependency_tree.get_direct_dependencies())
            transitive_count = len(self.dependency_tree.get_transitive_dependencies())
            print(f"📋 Found {len(dependencies)} dependencies (direct: {direct_count}, transitive: {transitive_count})")
        else:
            dependencies = self.parser.parse()
            print(f"📋 Found {len(dependencies)} dependencies (direct only)")

        scan_result = self.scanner.scan(dependencies, self.project_path)

        scan_result.vulnerabilities = self.impact_analyzer.analyze_batch(
            scan_result.vulnerabilities
        )

        scan_result.vulnerabilities = self.severity_evaluator.evaluate_batch(
            scan_result.vulnerabilities, dependencies
        )

        scan_result.vulnerabilities = [
            v for v in scan_result.vulnerabilities
            if v.severity.order >= self.min_severity.order
        ]

        scan_result.vulnerabilities.sort(
            key=lambda v: (v.severity.order, v.cvss_score), reverse=True
        )

        self._print_scan_summary(scan_result)

        return scan_result

    def scan_full_tree(self) -> DependencyTree:
        """仅解析并返回完整依赖树"""
        if self.dependency_tree:
            return self.dependency_tree

        if not self.parser:
            self.parser = ParserFactory.detect_parser(self.project_path)

        if not self.parser:
            raise ValueError(f"Could not detect project type in {self.project_path}")

        print("🌳 Resolving full dependency tree...")
        tree_resolver = DependencyTreeResolverFactory.get_resolver(
            self.parser.package_manager,
            self.project_path,
        )
        self.dependency_tree = tree_resolver.resolve(include_transitive=True)

        direct_count = len(self.dependency_tree.get_direct_dependencies())
        transitive_count = len(self.dependency_tree.get_transitive_dependencies())
        print(f"📦 Total: {len(self.dependency_tree.all_dependencies)} (direct: {direct_count}, transitive: {transitive_count})")

        return self.dependency_tree

    def get_fix_suggestions(self, scan_result: ScanResult) -> List[FixSuggestion]:
        """获取修复建议"""
        if not scan_result.vulnerabilities:
            print("✅ No vulnerabilities found. No fixes needed.")
            return []

        print("\n💡 Generating fix suggestions...")
        suggestions = self.version_suggester.suggest_fixes(
            scan_result.vulnerabilities, scan_result.dependencies
        )

        self._print_fix_suggestions(suggestions)
        return suggestions

    def apply_fixes(
        self,
        suggestions: List[FixSuggestion],
        backup: bool = True,
    ) -> Dict[str, Any]:
        """应用修复到本地文件"""
        if not suggestions:
            return {"success": False, "message": "No suggestions to apply"}

        print(f"\n🔧 Applying {len(suggestions)} fixes...")

        updater = DependencyUpdater(self.project_path, backup=backup)
        results = updater.update_dependencies(suggestions)

        success_count = sum(1 for r in results if r["success"])
        print(f"✅ Successfully applied {success_count}/{len(results)} fixes")

        for result in results:
            s = result["suggestion"]
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {s.dependency.full_name}: {s.current_version} → {s.suggested_version}")

        return {
            "success": success_count > 0,
            "total": len(results),
            "success_count": success_count,
            "results": results,
            "changes_summary": updater.get_changes_summary(),
        }

    def create_pull_request(
        self,
        suggestions: List[FixSuggestion],
        owner: str,
        repo: str,
        base_branch: str = "main",
        draft: bool = False,
        pre_test: bool = True,
        test_command: Optional[str] = None,
        fail_on_test_failure: bool = True,
    ) -> Dict[str, Any]:
        """创建自动修复 PR（含预测试）"""
        if not self.pr_creator:
            raise ValueError("GitHub token not provided. Cannot create PR.")

        if not suggestions:
            raise ValueError("No fix suggestions available for PR creation")

        print(f"\n🚀 Creating PR for {len(suggestions)} fixes...")
        print(f"   Repository: {owner}/{repo}")
        print(f"   Base branch: {base_branch}")

        if pre_test and self.pr_tester:
            print("\n🧪 Running pre-test before PR creation...")
            test_result = self.pr_tester.run_pre_tests(
                suggestions=suggestions,
                test_command=test_command,
                package_manager=self.parser.package_manager if self.parser else None,
            )

            if not test_result["success"]:
                print(f"❌ Pre-tests failed: {test_result.get('error', 'Unknown error')}")
                print(f"   Test output: {test_result.get('output', '')[:500]}")

                if fail_on_test_failure:
                    print("   Aborting PR creation due to test failures.")
                    return {
                        "success": False,
                        "pr": None,
                        "test_result": test_result,
                        "error": "Pre-tests failed",
                    }
                else:
                    print("   ⚠️  Continuing with PR creation despite test failures.")
            else:
                print(f"✅ All pre-tests passed!")
                if test_result.get("duration"):
                    print(f"   Duration: {test_result['duration']:.2f}s")

        result = self.pr_creator.create_fix_pr(
            owner=owner,
            repo=repo,
            suggestions=suggestions,
            base_branch=base_branch,
            draft=draft,
        )

        pr_url = result["pr"].get("html_url", "")
        print(f"✅ PR created successfully: {pr_url}")

        if pre_test:
            result["test_result"] = test_result

        return result

    def run_pre_tests(
        self,
        suggestions: List[FixSuggestion],
        test_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        """仅运行预测试，不创建 PR"""
        if not self.pr_tester:
            raise ValueError("GitHub token not provided. Pre-tester not initialized.")

        print("🧪 Running pre-tests...")
        result = self.pr_tester.run_pre_tests(
            suggestions=suggestions,
            test_command=test_command,
            package_manager=self.parser.package_manager if self.parser else None,
        )

        if result["success"]:
            print(f"✅ All tests passed! ({result.get('duration', 0):.2f}s)")
        else:
            print(f"❌ Tests failed: {result.get('error', 'Unknown error')}")

        return result

    def create_issue(
        self,
        vulnerabilities: List[Vulnerability],
        owner: str,
        repo: str,
        suggestions: Optional[List[FixSuggestion]] = None,
    ) -> Dict[str, Any]:
        """创建漏洞 Issue"""
        if not self.pr_creator:
            raise ValueError("GitHub token not provided. Cannot create issue.")

        if not vulnerabilities:
            raise ValueError("No vulnerabilities to report")

        print(f"\n📝 Creating issue for {len(vulnerabilities)} vulnerabilities...")

        result = self.pr_creator.create_vulnerability_issue(
            owner=owner,
            repo=repo,
            vulnerabilities=vulnerabilities,
            suggestions=suggestions,
        )

        issue_url = result.get("html_url", "")
        print(f"✅ Issue created successfully: {issue_url}")

        return result

    def generate_report(
        self,
        scan_result: ScanResult,
        suggestions: Optional[List[FixSuggestion]] = None,
        output_format: str = "json",
        output_file: Optional[str] = None,
    ) -> str:
        """生成扫描报告"""
        report_data = scan_result.to_dict()

        if suggestions:
            report_data["fix_suggestions"] = [s.to_dict() for s in suggestions]

        impact_report = self.impact_analyzer.generate_impact_report(
            scan_result.vulnerabilities, scan_result.dependencies
        )
        report_data["impact_analysis"] = impact_report

        report_data["risk_score"] = self.severity_evaluator.get_risk_score(
            scan_result.vulnerabilities
        )

        output = ""
        if output_format == "json":
            output = json.dumps(report_data, indent=2, ensure_ascii=False)
        elif output_format == "markdown":
            output = self._generate_markdown_report(scan_result, suggestions, report_data)
        elif output_format == "text":
            output = self._generate_text_report(scan_result, suggestions, report_data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\n📄 Report saved to: {output_file}")

        return output

    def update_database(self) -> bool:
        """更新漏洞数据库"""
        print("🔄 Updating vulnerability database...")
        success = self.scanner.update_database()
        if success:
            print("✅ Database updated successfully")
        else:
            print("⚠️  Failed to update database, using built-in database")
        return success

    def _print_scan_summary(self, result: ScanResult) -> None:
        """打印扫描摘要"""
        print(f"\n{'='*60}")
        print("📊 SCAN SUMMARY")
        print(f"{'='*60}")
        print(f"  Project: {result.project_path}")
        print(f"  Scan time: {result.scan_time}")
        print(f"  Package manager: {result.package_manager.value}")
        print(f"  Dependencies scanned: {len(result.dependencies)}")
        print(f"  Vulnerabilities found: {len(result.vulnerabilities)}")
        print(f"    - Critical: {result.critical_count}")
        print(f"    - High: {result.high_count}")
        print(f"    - Medium: {result.medium_count}")
        print(f"    - Low: {result.low_count}")

        if result.vulnerabilities:
            print(f"\n{'='*60}")
            print("🐛 VULNERABILITIES")
            print(f"{'='*60}")

            for i, vuln in enumerate(result.vulnerabilities, 1):
                dep = vuln.dependency
                print(f"\n  [{i}] {vuln.severity.color}{vuln.severity.value}\033[0m - {vuln.cve_id}")
                print(f"      Package: {dep.full_name} {dep.version}")
                print(f"      Title: {vuln.title}")
                if vuln.cvss_score > 0:
                    print(f"      CVSS Score: {vuln.cvss_score}")
                if vuln.impact_scope and vuln.impact_scope != "unknown":
                    print(f"      Impact Scope: {vuln.impact_scope}")
                if vuln.fixed_versions:
                    print(f"      Fixed in: {', '.join(vuln.fixed_versions)}")

    def _print_fix_suggestions(self, suggestions: List[FixSuggestion]) -> None:
        """打印修复建议"""
        if not suggestions:
            print("✅ No fix suggestions available")
            return

        print(f"\n{'='*60}")
        print("💡 FIX SUGGESTIONS")
        print(f"{'='*60}")

        for i, s in enumerate(suggestions, 1):
            dep = s.dependency
            highest_sev = max(v.severity for v in s.vulnerabilities)
            breaking = " ⚠️ BREAKING CHANGES" if s.breaking_changes else ""
            print(f"\n  [{i}] {dep.full_name}: {s.current_version} → {s.suggested_version}")
            print(f"      Severity: {highest_sev.color}{highest_sev.value}\033[0m")
            print(f"      Upgrade type: {s.upgrade_type}{breaking}")
            print(f"      CVEs fixed: {', '.join(v.cve_id for v in s.vulnerabilities)}")

    def _generate_markdown_report(
        self,
        scan_result: ScanResult,
        suggestions: Optional[List[FixSuggestion]],
        report_data: Dict[str, Any],
    ) -> str:
        """生成 Markdown 格式报告"""
        lines = []

        lines.append("# 🔒 Dependency Vulnerability Scan Report")
        lines.append("")
        lines.append(f"**Scan Time**: {scan_result.scan_time}")
        lines.append(f"**Project**: {scan_result.project_path}")
        lines.append(f"**Package Manager**: {scan_result.package_manager.value}")
        lines.append(f"**Risk Score**: {report_data.get('risk_score', 0):.1f}/100")
        lines.append("")

        lines.append("## 📊 Summary")
        lines.append("")
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Dependencies Scanned | {len(scan_result.dependencies)} |")
        lines.append(f"| Total Vulnerabilities | {len(scan_result.vulnerabilities)} |")
        lines.append(f"| Critical | {scan_result.critical_count} |")
        lines.append(f"| High | {scan_result.high_count} |")
        lines.append(f"| Medium | {scan_result.medium_count} |")
        lines.append(f"| Low | {scan_result.low_count} |")
        lines.append("")

        if scan_result.vulnerabilities:
            lines.append("## 🐛 Vulnerabilities")
            lines.append("")
            lines.append("| CVE | Severity | Package | Version | CVSS | Description |")
            lines.append("|-----|----------|---------|---------|------|-------------|")

            for v in scan_result.vulnerabilities:
                lines.append(
                    f"| {v.cve_id} | {v.severity.value} | `{v.dependency.full_name}` | "
                    f"{v.dependency.version} | {v.cvss_score} | {v.title} |"
                )
            lines.append("")

        if suggestions:
            lines.append("## 💡 Fix Suggestions")
            lines.append("")
            lines.append("| Package | Current | Suggested | Upgrade Type | Breaking | CVEs Fixed |")
            lines.append("|---------|---------|-----------|--------------|----------|------------|")

            for s in suggestions:
                breaking = "⚠️ Yes" if s.breaking_changes else "✅ No"
                cves = ", ".join(v.cve_id for v in s.vulnerabilities)
                lines.append(
                    f"| `{s.dependency.full_name}` | `{s.current_version}` | "
                    f"`{s.suggested_version}` | {s.upgrade_type} | {breaking} | {cves} |"
                )
            lines.append("")

        lines.append("## 📈 Impact Analysis")
        lines.append("")
        impact = report_data.get("impact_analysis", {})

        if impact.get("by_severity"):
            lines.append("### By Severity")
            lines.append("")
            for sev, count in impact["by_severity"].items():
                lines.append(f"- **{sev}**: {count}")
            lines.append("")

        if impact.get("by_scope"):
            lines.append("### By Impact Scope")
            lines.append("")
            for scope, count in impact["by_scope"].items():
                lines.append(f"- **{scope}**: {count}")
            lines.append("")

        if impact.get("high_risk_dependencies"):
            lines.append("### High Risk Dependencies")
            lines.append("")
            for dep in impact["high_risk_dependencies"]:
                lines.append(
                    f"- **{dep['dependency']}** {dep['version']} - "
                    f"{dep['cve_id']} ({dep['severity']}, Impact Score: {dep['impact_score']})"
                )
            lines.append("")

        return "\n".join(lines)

    def _generate_text_report(
        self,
        scan_result: ScanResult,
        suggestions: Optional[List[FixSuggestion]],
        report_data: Dict[str, Any],
    ) -> str:
        """生成纯文本格式报告"""
        lines = []

        lines.append("=" * 70)
        lines.append("DEPENDENCY VULNERABILITY SCAN REPORT")
        lines.append("=" * 70)
        lines.append(f"Scan Time: {scan_result.scan_time}")
        lines.append(f"Project: {scan_result.project_path}")
        lines.append(f"Package Manager: {scan_result.package_manager.value}")
        lines.append(f"Risk Score: {report_data.get('risk_score', 0):.1f}/100")
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Dependencies Scanned: {len(scan_result.dependencies)}")
        lines.append(f"Total Vulnerabilities: {len(scan_result.vulnerabilities)}")
        lines.append(f"  Critical: {scan_result.critical_count}")
        lines.append(f"  High: {scan_result.high_count}")
        lines.append(f"  Medium: {scan_result.medium_count}")
        lines.append(f"  Low: {scan_result.low_count}")
        lines.append("")

        if scan_result.vulnerabilities:
            lines.append("VULNERABILITIES")
            lines.append("-" * 70)
            for i, v in enumerate(scan_result.vulnerabilities, 1):
                lines.append(f"\n[{i}] {v.severity.value} - {v.cve_id}")
                lines.append(f"    Package: {v.dependency.full_name} {v.dependency.version}")
                lines.append(f"    Title: {v.title}")
                lines.append(f"    CVSS: {v.cvss_score}")
                if v.fixed_versions:
                    lines.append(f"    Fixed in: {', '.join(v.fixed_versions)}")
            lines.append("")

        if suggestions:
            lines.append("FIX SUGGESTIONS")
            lines.append("-" * 70)
            for i, s in enumerate(suggestions, 1):
                breaking = " [BREAKING CHANGES]" if s.breaking_changes else ""
                lines.append(f"\n[{i}] {s.dependency.full_name}")
                lines.append(f"    {s.current_version} -> {s.suggested_version} ({s.upgrade_type}){breaking}")
                lines.append(f"    Fixes: {', '.join(v.cve_id for v in s.vulnerabilities)}")
            lines.append("")

        return "\n".join(lines)


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Dependency Vulnerability Scanner - 扫描项目依赖的安全漏洞",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描当前目录（包含传递依赖）
  python -m vuln_scanner scan .

  # 仅扫描直接依赖
  python -m vuln_scanner scan . --no-transitive

  # 使用 NVD 实时同步数据库（每小时自动更新）
  python -m vuln_scanner scan . --use-nvd --nvd-api-key YOUR_API_KEY

  # 解析并显示完整依赖树
  python -m vuln_scanner tree .

  # 扫描并自动创建 PR（预测试后提交）
  python -m vuln_scanner scan . --create-pr --github-token YOUR_TOKEN --repo owner/repo --pre-test

  # 仅运行预测试，不创建 PR
  python -m vuln_scanner pre-test . --test-command "pytest tests/"

  # 手动触发 NVD 全量同步
  python -m vuln_scanner sync-nvd --full --nvd-api-key YOUR_API_KEY

  # 查看 NVD 同步状态
  python -m vuln_scanner nvd-status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    scan_parser = subparsers.add_parser("scan", help="扫描项目依赖漏洞")
    scan_parser.add_argument("path", help="项目路径")
    scan_parser.add_argument(
        "--package-manager",
        choices=["maven", "npm", "pip", "go"],
        help="指定包管理器（默认自动检测）",
    )
    scan_parser.add_argument(
        "--min-severity",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="LOW",
        help="最低显示的漏洞严重等级（默认: LOW）",
    )
    scan_parser.add_argument("--no-safety-db", action="store_true", help="不使用 Safety DB")
    scan_parser.add_argument("--use-nvd", action="store_true", help="使用 NVD 实时同步数据库")
    scan_parser.add_argument("--nvd-api-key", help="NVD API Key")
    scan_parser.add_argument("--nvd-sync-interval", type=int, default=3600, help="NVD 同步间隔（秒，默认3600）")
    scan_parser.add_argument("--no-nvd-auto-sync", action="store_true", help="禁用 NVD 自动同步")
    scan_parser.add_argument(
        "--format",
        choices=["json", "markdown", "text"],
        default="text",
        help="输出格式（默认: text）",
    )
    scan_parser.add_argument("--output", "-o", help="输出报告文件路径")
    scan_parser.add_argument("--no-transitive", action="store_true", help="不扫描传递依赖（仅直接依赖）")
    scan_parser.add_argument("--auto-fix", action="store_true", help="自动应用修复")
    scan_parser.add_argument("--no-backup", action="store_true", help="不备份原文件")
    scan_parser.add_argument("--create-pr", action="store_true", help="创建自动修复 PR")
    scan_parser.add_argument("--github-token", help="GitHub Token")
    scan_parser.add_argument("--repo", help="GitHub 仓库（格式: owner/repo）")
    scan_parser.add_argument("--base-branch", default="main", help="基础分支（默认: main）")
    scan_parser.add_argument("--draft", action="store_true", help="创建草稿 PR")
    scan_parser.add_argument("--pre-test", action="store_true", help="创建 PR 前运行预测试")
    scan_parser.add_argument("--no-fail-on-test-failure", action="store_true", help="测试失败仍继续创建 PR")
    scan_parser.add_argument("--test-command", help="自定义测试命令")
    scan_parser.add_argument("--create-issue", action="store_true", help="创建漏洞 Issue")

    tree_parser = subparsers.add_parser("tree", help="解析并显示依赖树")
    tree_parser.add_argument("path", help="项目路径")
    tree_parser.add_argument(
        "--package-manager",
        choices=["maven", "npm", "pip", "go"],
        help="指定包管理器（默认自动检测）",
    )
    tree_parser.add_argument("--no-transitive", action="store_true", help="仅显示直接依赖")

    pretest_parser = subparsers.add_parser("pre-test", help="仅运行预测试，不创建 PR")
    pretest_parser.add_argument("path", help="项目路径")
    pretest_parser.add_argument("--github-token", help="GitHub Token（用于初始化预测试器）")
    pretest_parser.add_argument("--test-command", help="自定义测试命令")

    sync_nvd_parser = subparsers.add_parser("sync-nvd", help="同步 NVD 漏洞数据库")
    sync_nvd_parser.add_argument("--nvd-api-key", help="NVD API Key")
    sync_nvd_parser.add_argument("--full", action="store_true", help="全量同步（默认增量）")

    status_parser = subparsers.add_parser("nvd-status", help="查看 NVD 同步状态")
    status_parser.add_argument("--nvd-api-key", help="NVD API Key")

    subparsers.add_parser("update-db", help="更新所有漏洞数据库")

    args = parser.parse_args()

    if args.command == "update-db":
        scanner = DependencyVulnerabilityScanner(
            project_path=".",
            use_safety_db=True,
        )
        success = scanner.update_database()
        sys.exit(0 if success else 1)

    elif args.command == "sync-nvd":
        from .scanner import NVDSync
        nvd = NVDSync(api_key=args.nvd_api_key, auto_sync=False)
        nvd.load()
        result = nvd.sync(full_sync=args.full)
        print(f"\n🔄 NVD Sync Complete:")
        print(f"   New vulnerabilities: {result.get('new_vulnerabilities', 0)}")
        print(f"   Total vulnerabilities: {result.get('total_vulnerabilities', 0)}")
        print(f"   Packages: {result.get('packages', 0)}")
        print(f"   Last sync: {result.get('last_sync', '')}")
        sys.exit(0)

    elif args.command == "nvd-status":
        from .scanner import NVDSync
        nvd = NVDSync(api_key=args.nvd_api_key, auto_sync=False)
        nvd.load()
        status = nvd.get_sync_status()
        print(f"\n📊 NVD Sync Status:")
        print(f"   Loaded: {status.get('loaded', False)}")
        print(f"   Last sync: {status.get('last_sync', 'Never')}")
        print(f"   Packages: {status.get('packages', 0)}")
        print(f"   Total vulnerabilities: {status.get('total_vulnerabilities', 0)}")
        print(f"   Sync interval: {status.get('sync_interval', 3600)}s")
        print(f"   Auto sync: {status.get('auto_sync', False)}")
        print(f"   Background sync: {status.get('background_sync_running', False)}")
        sys.exit(0)

    elif args.command == "tree":
        pm = PackageManager(args.package_manager) if args.package_manager else None

        try:
            scanner = DependencyVulnerabilityScanner(
                project_path=args.path,
                use_safety_db=False,
                include_transitive=not args.no_transitive,
            )

            tree = scanner.scan_full_tree()

            print(f"\n🌳 Dependency Tree for: {args.path}")
            print(f"{'='*60}")
            print(f"📦 Total dependencies: {len(tree.all_dependencies)}")
            print(f"   Direct: {len(tree.get_direct_dependencies())}")
            print(f"   Transitive: {len(tree.get_transitive_dependencies())}")
            print(f"{'='*60}\n")

            tree.print_tree()

            sys.exit(0)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    elif args.command == "pre-test":
        try:
            scanner = DependencyVulnerabilityScanner(
                project_path=args.path,
                use_safety_db=True,
                github_token=args.github_token,
                include_transitive=False,
            )

            result = scanner.scan()
            suggestions = scanner.get_fix_suggestions(result)

            if suggestions:
                test_result = scanner.run_pre_tests(suggestions, test_command=args.test_command)
                sys.exit(0 if test_result["success"] else 1)
            else:
                print("✅ No fixes needed, no tests to run.")
                sys.exit(0)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    elif args.command == "scan":
        pm = PackageManager(args.package_manager) if args.package_manager else None
        min_severity = SeverityLevel(args.min_severity)

        try:
            scanner = DependencyVulnerabilityScanner(
                project_path=args.path,
                use_safety_db=not args.no_safety_db,
                use_nvd=args.use_nvd,
                nvd_api_key=args.nvd_api_key,
                min_severity=min_severity,
                auto_fix=args.auto_fix,
                github_token=args.github_token,
                include_transitive=not args.no_transitive,
                nvd_sync_interval=args.nvd_sync_interval,
                nvd_auto_sync=not args.no_nvd_auto_sync,
            )

            result = scanner.scan(package_manager=pm)
            suggestions = scanner.get_fix_suggestions(result)

            if args.output:
                scanner.generate_report(
                    result, suggestions, args.format, args.output
                )

            if args.auto_fix and suggestions:
                scanner.apply_fixes(suggestions, backup=not args.no_backup)

            if args.create_pr and suggestions:
                if not args.repo:
                    print("❌ Error: --repo is required for --create-pr")
                    sys.exit(1)
                owner, repo = args.repo.split("/", 1)
                pr_result = scanner.create_pull_request(
                    suggestions,
                    owner,
                    repo,
                    base_branch=args.base_branch,
                    draft=args.draft,
                    pre_test=args.pre_test,
                    test_command=args.test_command,
                    fail_on_test_failure=not args.no_fail_on_test_failure,
                )
                if not pr_result.get("success", True):
                    sys.exit(1)

            if args.create_issue and result.vulnerabilities:
                if not args.repo:
                    print("❌ Error: --repo is required for --create-issue")
                    sys.exit(1)
                owner, repo = args.repo.split("/", 1)
                scanner.create_issue(result.vulnerabilities, owner, repo, suggestions)

            if result.vulnerabilities:
                sys.exit(1)
            else:
                sys.exit(0)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
