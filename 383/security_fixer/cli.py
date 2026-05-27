"""Security Fixer CLI - 命令行入口"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from .rules.rule_engine import RuleEngine, ScanResult
from .fixers.fixer_engine import FixerEngine
from .fixers.base_fixer import FixResult
from .github.github_client import GitHubClient, PRCreateResult
from .dependencies import DependencyChecker, DependencyFixer
from .validation import FixValidator
from .dashboard import DashboardGenerator


def print_banner():
    banner = r"""
  ███████╗███████╗ ██████╗██╗   ██╗██████╗ ██╗████████╗██╗   ██╗
  ██╔════╝██╔════╝██╔════╝██║   ██║██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
  ███████╗█████╗  ██║     ██║   ██║██████╔╝██║   ██║    ╚████╔╝
  ╚════██║██╔══╝  ██║     ██║   ██║██╔══██╗██║   ██║     ╚██╔╝
  ███████║███████╗╚██████╗╚██████╔╝██║  ██║██║   ██║      ██║
  ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝
  ================================================================
  🔒 安全漏洞自动扫描与修复工具
  支持语言: Python | Java | JavaScript
  检测类型: SQL注入 | XSS | 路径遍历 | 命令注入
    """
    click.echo(banner)


def print_scan_result(result: ScanResult):
    click.echo(f"\n📄 文件: {result.file_path}")
    click.echo(f"   语言: {result.language.value}")

    if result.parse_error:
        click.echo(f"   ⚠️  解析错误: {result.parse_error}")
        return

    if not result.vulnerabilities:
        click.echo(f"   ✅ 未发现安全漏洞")
        return

    for v in result.vulnerabilities:
        icon = "🔴" if v.severity.value in ("critical", "high") else "🟡"
        click.echo(f"   {icon} [{v.severity.value.upper()}] {v.vuln_type.value}")
        click.echo(f"      行 {v.source_span.start_line}: {v.message}")
        if v.suggested_fix:
            click.echo(f"      💡 修复建议: {v.suggested_fix[:100]}...")


def print_fix_result(result: FixResult):
    click.echo(f"\n🔧 修复: {result.file_path}")
    if result.error:
        click.echo(f"   ⚠️  错误: {result.error}")
    elif result.is_changed:
        click.echo(f"   ✅ 已修复 {result.success_count} 个漏洞")
        if result.skipped_count:
            click.echo(f"   ⚠️  跳过 {result.skipped_count} 个漏洞（需人工处理）")
        for action in result.actions[:3]:
            click.echo(f"   - {action.description}")
    else:
        click.echo(f"   ℹ️  无需更改")


@click.group()
@click.version_option(version="1.0.0", prog_name="security-fixer")
def cli():
    """Security Fixer - 安全漏洞自动扫描与修复工具"""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--language", "-l", type=click.Choice(["python", "java", "javascript", "all"]),
              default="all", help="指定扫描语言")
@click.option("--output", "-o", type=click.Path(), help="输出JSON报告文件路径")
@click.option("--verbose", "-v", is_flag=True, help="显示详细信息")
def scan(path, language, output, verbose):
    """扫描代码仓库中的安全漏洞"""
    print_banner()

    engine = RuleEngine()
    scan_path = Path(path)

    click.echo(f"🔍 开始扫描: {scan_path}")

    if scan_path.is_file():
        from .parsers.base_parser import Language
        lang_map = {"python": Language.PYTHON, "java": Language.JAVA, "javascript": Language.JAVASCRIPT}
        lang = lang_map.get(language) if language != "all" else None
        results = [engine.scan_file(str(scan_path), lang)]
    else:
        results = engine.scan_directory_filtered(str(scan_path))

    click.echo(f"\n📊 扫描完成: {len(results)} 个文件")

    files_with_vulns = 0
    total_vulns = 0

    for result in results:
        print_scan_result(result)
        if result.has_vulnerabilities:
            files_with_vulns += 1
            total_vulns += len(result.vulnerabilities)

    click.echo(f"\n📈 汇总:")
    click.echo(f"   扫描文件: {len(results)}")
    click.echo(f"   含漏洞文件: {files_with_vulns}")
    click.echo(f"   漏洞总数: {total_vulns}")

    summary = engine.get_vulnerability_summary(results)

    click.echo(f"\n📋 漏洞类型分布:")
    for vtype, count in summary["summary"]["by_type"].items():
        click.echo(f"   - {vtype}: {count}")

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        click.echo(f"\n💾 报告已保存到: {output}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--apply", "-a", is_flag=True, help="直接应用修复到文件")
@click.option("--backup/--no-backup", default=True, help="应用修复时是否备份原文件")
@click.option("--output-dir", "-o", type=click.Path(), help="修复后文件输出目录")
def fix(path, apply, backup, output_dir):
    """扫描并自动修复安全漏洞"""
    print_banner()

    engine = RuleEngine()
    fixer_engine = FixerEngine()

    scan_path = Path(path)

    click.echo(f"🔍 扫描漏洞: {scan_path}")

    if scan_path.is_file():
        scan_results = [engine.scan_file(str(scan_path))]
    else:
        scan_results = engine.scan_directory_filtered(str(scan_path))

    vulnerable_results = [r for r in scan_results if r.has_vulnerabilities]

    if not vulnerable_results:
        click.echo("\n✅ 未发现安全漏洞，无需修复")
        return

    click.echo(f"\n🔧 开始修复 {len(vulnerable_results)} 个文件中的漏洞...")

    fix_results = fixer_engine.fix_scan_results(vulnerable_results)

    for result in fix_results:
        print_fix_result(result)

    total_fixed = sum(r.success_count for r in fix_results)
    total_skipped = sum(r.skipped_count for r in fix_results)
    changed_files = sum(1 for r in fix_results if r.is_changed)

    click.echo(f"\n📊 修复汇总:")
    click.echo(f"   修改文件: {changed_files}")
    click.echo(f"   已修复漏洞: {total_fixed}")
    click.echo(f"   跳过漏洞: {total_skipped}")

    if apply and changed_files > 0:
        click.echo(f"\n💾 正在应用修复...")
        apply_result = fixer_engine.apply_fixes(fix_results, backup=backup)
        click.echo(f"   成功: {apply_result['applied']}")
        click.echo(f"   失败: {apply_result['failed']}")
        if backup:
            click.echo(f"   💾 原文件已备份为 .bak 文件")
    elif output_dir and changed_files > 0:
        os.makedirs(output_dir, exist_ok=True)
        for result in fix_results:
            if result.is_changed:
                relative_path = Path(result.file_path).name
                output_path = Path(output_dir) / relative_path
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.fixed_source)
                click.echo(f"   💾 修复后文件: {output_path}")

    fix_summary = fixer_engine.get_fix_summary(fix_results)

    if output_dir:
        report_path = Path(output_dir) / "fix_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(fix_summary, f, indent=2, ensure_ascii=False)
        click.echo(f"\n💾 修复报告: {report_path}")

    if not apply and not output_dir:
        click.echo("\n💡 提示: 使用 --apply 直接应用修复，或使用 --output-dir 指定输出目录")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--token", "-t", envvar="GITHUB_TOKEN", help="GitHub Token")
@click.option("--base-branch", "-b", default="main", help="PR目标分支")
@click.option("--branch-prefix", default="security-fix", help="修复分支前缀")
@click.option("--dry-run", is_flag=True, help="仅显示将要创建的PR内容，不实际创建")
@click.option("--rollback/--no-rollback", default=True, help="PR创建失败时是否自动回退")
def create_pr(path, token, base_branch, branch_prefix, dry_run, rollback):
    """扫描漏洞并创建修复PR"""
    print_banner()

    engine = RuleEngine()
    fixer_engine = FixerEngine()
    github = GitHubClient(token=token, repo_path=str(Path(path).resolve()))

    if not github.is_git_repo():
        click.echo("❌ 错误: 当前目录不是Git仓库")
        return

    click.echo(f"🔍 扫描: {path}")

    if Path(path).is_file():
        scan_results = [engine.scan_file(str(Path(path)))]
    else:
        scan_results = engine.scan_directory_filtered(str(Path(path)))

    vulnerable = [r for r in scan_results if r.has_vulnerabilities]

    if not vulnerable:
        click.echo("\n✅ 未发现漏洞，无需创建PR")
        return

    click.echo(f"\n🔧 修复 {len(vulnerable)} 个文件...")

    fix_results = fixer_engine.fix_scan_results(vulnerable)

    changed_results = [r for r in fix_results if r.is_changed]

    if not changed_results:
        click.echo("\n⚠️  没有可自动修复的内容")
        return

    if dry_run:
        click.echo("\n📋 PR预览:")
        click.echo(f"   标题: 🔒 安全修复: {sum(r.success_count for r in changed_results)}个漏洞自动修复")
        click.echo(f"   修改文件: {len(changed_results)}")
        for r in changed_results:
            click.echo(f"   - {r.file_path}: 修复{r.success_count}个漏洞")
        click.echo("\n💡 使用 --dry-run 以外的选项将实际创建PR")
        return

    apply_result = fixer_engine.apply_fixes(changed_results, backup=True)

    if apply_result["applied"] == 0:
        click.echo("❌ 修复应用失败")
        return

    click.echo(f"\n💾 已应用 {apply_result['applied']} 个文件修复")
    click.echo("📦 创建PR...")

    fixes_data = []
    for r in changed_results:
        fixes_data.append({
            "file_path": r.file_path,
            "fixed_count": r.success_count,
            "skipped_count": r.skipped_count,
            "vuln_types": list(set(v.vuln_type.value for v in r.vulnerabilities_fixed)),
            "actions": [a.to_dict() for a in r.actions],
        })

    result = github.create_pr_from_fixes(fixes_data, branch_prefix, base_branch, auto_rollback=rollback)

    if result.success:
        click.echo(f"\n✅ PR创建成功!")
        click.echo(f"   🔗 URL: {result.pr_url}")
        click.echo(f"   🌿 分支: {result.branch_name}")
    elif result.rolled_back:
        click.echo(f"\n❌ PR创建失败，已自动回退")
        click.echo(f"   错误原因: {result.error}")
        click.echo(f"   回退详情:")
        for step in result.rollback_details.get("steps", []):
            status = "✅" if step["success"] else "❌"
            click.echo(f"   {status} {step['step']}: {step['message']}")
    else:
        click.echo(f"\n❌ PR创建失败: {result.error}")
        click.echo(f"   分支已创建: {result.branch_name}")
        click.echo(f"   请手动创建PR或检查GitHub Token权限")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def report(path):
    """生成完整的安全扫描报告"""
    print_banner()

    engine = RuleEngine()
    fixer_engine = FixerEngine()

    scan_path = Path(path)

    click.echo(f"🔍 全面扫描: {scan_path}")

    if scan_path.is_file():
        scan_results = [engine.scan_file(str(scan_path))]
    else:
        scan_results = engine.scan_directory_filtered(str(scan_path))

    summary = engine.get_vulnerability_summary(scan_results)

    report = {
        "title": "Security Fixer 安全扫描报告",
        "scan_path": str(scan_path),
        "summary": summary["summary"],
        "files": [],
    }

    for r in scan_results:
        file_report = {
            "file": r.file_path,
            "language": r.language.value,
            "vulnerabilities": [v.to_dict() for v in r.vulnerabilities],
            "error": r.parse_error,
        }
        report["files"].append(file_report)

    output_path = scan_path / "security_report.json" if scan_path.is_dir() else scan_path.parent / "security_report.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    click.echo(f"\n📄 报告已生成: {output_path}")
    click.echo(f"   扫描文件: {report['summary']['total_files_scanned']}")
    click.echo(f"   漏洞文件: {report['summary']['files_with_vulnerabilities']}")
    click.echo(f"   漏洞总数: {report['summary']['total_vulnerabilities']}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="输出JSON报告文件路径")
def check_deps(path, output):
    """检查项目依赖中的安全漏洞"""
    print_banner()

    checker = DependencyChecker()
    scan_path = Path(path)

    click.echo(f"🔍 检查依赖漏洞: {scan_path}")

    if scan_path.is_file():
        file_path = str(scan_path)
        if file_path.endswith((".txt", ".json", ".xml", ".toml", ".gradle")):
            vulns = checker._scan_dependency_file(file_path, "python")
        else:
            vulns = []
    else:
        vulns = checker.scan_directory(str(scan_path))

    if not vulns:
        click.echo("\n✅ 未发现有漏洞的依赖")
        return

    click.echo(f"\n📊 发现 {len(vulns)} 个有漏洞的依赖:")
    for v in vulns:
        icon = "🔴" if v.severity == "critical" else "🟠"
        click.echo(f"   {icon} [{v.severity.upper()}] {v.name}")
        click.echo(f"      当前版本: {v.current_version}")
        click.echo(f"      修复版本: {v.fixed_version}")
        click.echo(f"      漏洞ID: {v.vulnerability_id}")
        click.echo(f"      描述: {v.description}")
        click.echo(f"      文件: {v.dependency_file}")

    if output:
        report = {
            "vulnerable_dependencies": [
                {
                    "name": v.name,
                    "current_version": v.current_version,
                    "fixed_version": v.fixed_version,
                    "severity": v.severity,
                    "vulnerability_id": v.vulnerability_id,
                    "description": v.description,
                    "language": v.language,
                    "dependency_file": v.dependency_file,
                }
                for v in vulns
            ],
            "total": len(vulns),
        }
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        click.echo(f"\n💾 报告已保存到: {output}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--backup/--no-backup", default=True, help="是否备份原文件")
def fix_deps(path, backup):
    """修复有漏洞的依赖版本"""
    print_banner()

    fixer = DependencyFixer(backup=backup)
    scan_path = Path(path)

    click.echo(f"🔧 修复依赖漏洞: {scan_path}")

    results = fixer.fix_vulnerable_dependencies(str(scan_path))

    if not results:
        click.echo("\n✅ 没有需要修复的依赖")
        return

    total_fixed = 0
    for file_path, result in results.items():
        click.echo(f"\n📄 {file_path}")
        click.echo(f"   已修复: {result.fixed_count} 个依赖")
        if result.skipped_count:
            click.echo(f"   跳过: {result.skipped_count} 个依赖")
        if result.backup_created:
            click.echo(f"   备份: {result.backup_path}")
        for dep in result.fixed_dependencies:
            click.echo(f"   ✅ {dep.name}: {dep.current_version} -> {dep.fixed_version}")
        total_fixed += result.fixed_count

    click.echo(f"\n📊 共修复 {total_fixed} 个有漏洞的依赖")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--framework", "-f", type=click.Choice(["auto", "pytest", "npm", "maven", "gradle", "python"]),
              default="auto", help="测试框架类型")
@click.option("--run-before/--no-run-before", default=False, help="是否在修复前运行测试")
def validate(path, framework, run_before):
    """修复后运行测试验证功能"""
    print_banner()

    validator = FixValidator(project_root=str(Path(path).resolve()))

    click.echo(f"🔍 验证修复结果: {path}")

    test_framework = framework if framework != "auto" else None
    if test_framework is None:
        detected = validator.detect_test_framework()
        click.echo(f"   检测到测试框架: {detected or '未知'}")

    click.echo("\n🧪 运行测试...")
    result = validator.run_tests(test_framework)

    click.echo(f"\n📊 测试结果:")
    click.echo(f"   通过: {'✅' if result.passed else '❌'}")
    click.echo(f"   退出码: {result.exit_code}")
    click.echo(f"   耗时: {result.duration:.2f}秒")
    click.echo(f"   测试数: {result.tests_run}")
    click.echo(f"   通过: {result.tests_passed}")
    click.echo(f"   失败: {result.tests_failed}")

    if result.stderr and not result.passed:
        click.echo(f"\n📋 错误输出:")
        click.echo(result.stderr[:500])

    if not result.passed:
        click.echo("\n⚠️  测试未通过，请检查修复是否引入了问题")
    else:
        click.echo("\n✅ 所有测试通过!")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "-f", type=click.Choice(["text", "html", "json"]),
              default="text", help="输出格式")
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
def dashboard(path, format, output):
    """生成漏洞趋势仪表盘"""
    print_banner()

    engine = RuleEngine()
    scan_path = Path(path)

    click.echo(f"🔍 扫描并生成仪表盘: {scan_path}")

    if scan_path.is_file():
        scan_results = [engine.scan_file(str(scan_path))]
    else:
        scan_results = engine.scan_directory_filtered(str(scan_path))

    generator = DashboardGenerator()

    if format == "text":
        report = generator.generate_text_report(scan_results)
        click.echo(report)
        if output:
            Path(output).write_text(report, encoding="utf-8")
            click.echo(f"\n💾 报告已保存到: {output}")
    elif format == "html":
        output_path = output or str(scan_path / "dashboard.html" if scan_path.is_dir() else "dashboard.html")
        generator.generate_html_report(scan_results, output_path)
        click.echo(f"\n💾 HTML仪表盘已生成: {output_path}")
    elif format == "json":
        output_path = output or str(scan_path / "dashboard.json" if scan_path.is_dir() else "dashboard.json")
        generator.generate_json_report(scan_results, output_path)
        click.echo(f"\n💾 JSON报告已生成: {output_path}")


def main():
    cli()


if __name__ == "__main__":
    main()
