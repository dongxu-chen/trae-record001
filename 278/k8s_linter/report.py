from colorama import init, Fore, Style
from typing import List
from .detector import Issue, Report, Severity

init(autoreset=True)

class ReportFormatter:
    SEVERITY_COLORS = {
        Severity.CRITICAL: Fore.RED + Style.BRIGHT,
        Severity.ERROR: Fore.RED,
        Severity.WARNING: Fore.YELLOW,
        Severity.INFO: Fore.CYAN
    }

    SEVERITY_SYMBOLS = {
        Severity.CRITICAL: '✗',
        Severity.ERROR: '✗',
        Severity.WARNING: '⚠',
        Severity.INFO: 'ℹ'
    }

    @classmethod
    def format_console(cls, report: Report, verbose: bool = False) -> str:
        lines = []

        lines.append(cls._format_summary(report))
        lines.append("")

        for severity in [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]:
            issues = report.get_issues_by_severity(severity)
            if issues:
                lines.append(cls._format_severity_section(severity, issues, verbose))

        return '\n'.join(lines)

    @classmethod
    def _format_summary(cls, report: Report) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("Kubernetes 配置检测结果")
        lines.append("=" * 80)
        lines.append(f"总计发现 {} 个问题:")
        lines.append(f"  {Fore.RED + Style.BRIGHT}严重(Critical): {report.critical_count}")
        lines.append(f"  {Fore.RED}错误(Error):    {report.error_count}")
        lines.append(f"  {Fore.YELLOW}警告(Warning):  {report.warning_count}")
        lines.append(f"  {Fore.CYAN}信息(Info):     {report.info_count}")
        return '\n'.join(lines)

    @classmethod
    def _format_severity_section(cls, severity: Severity, issues: List[Issue], verbose: bool) -> str:
        lines = []
        color = cls.SEVERITY_COLORS[severity]
        symbol = cls.SEVERITY_SYMBOLS[severity]

        lines.append(f"\n{color}{'─' * 80}")
        lines.append(f"{color}{symbol} {severity.value.upper()} ({len(issues)} 项)")
        lines.append(f"{color}{'─' * 80}")

        for issue in issues:
            lines.append(cls._format_issue(issue, verbose))

        return '\n'.join(lines)

    @classmethod
    def _format_issue(cls, issue: Issue, verbose: bool) -> str:
        color = cls.SEVERITY_COLORS[issue.severity]
        lines = []

        location = f"[{issue.file_path}"
        if issue.resource_type:
            location += f" | {issue.resource_type}/{issue.resource_name}"
        if issue.container_name:
            location += f" | 容器: {issue.container_name}"
        if issue.container_type:
            type_label = {
                'regular': '业务容器',
                'init': 'Init容器',
                'ephemeral': '临时容器'
            }.get(issue.container_type, issue.container_type)
            location += f" ({type_label})"

        lines.append(f"{color}  {issue.message}")
        lines.append(f"     位置: {location}")
        lines.append(f"     规则: {issue.rule_id}")

        if verbose and issue.suggestion:
            lines.append(f"     建议: {Fore.GREEN}{issue.suggestion}")

        return '\n'.join(lines)

    @classmethod
    def format_json(cls, report: Report) -> str:
        import json
        result = {
            "summary": {
                "total": len(report.issues),
                "critical": report.critical_count,
                "error": report.error_count,
                "warning": report.warning_count,
                "info": report.info_count
            },
            "issues": [
                {
                    "rule_id": issue.rule_id,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "file_path": issue.file_path,
                    "resource_type": issue.resource_type,
                    "resource_name": issue.resource_name,
                    "container_name": issue.container_name,
                    "container_type": issue.container_type
                }
                for issue in report.issues
            ]
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    @classmethod
    def format_junit(cls, report: Report) -> str:
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom

        testsuites = Element('testsuites')
        testsuite = SubElement(testsuites, 'testsuite', {
            'name': 'k8s-config-lint',
            'tests': str(len(report.issues)),
            'failures': str(report.critical_count + report.error_count),
            'errors': '0'
        })

        for issue in report.issues:
            testcase = SubElement(testsuite, 'testcase', {
                'name': issue.rule_id,
                'classname': issue.file_path
            })
            failure = SubElement(testcase, 'failure', {
                'type': issue.severity.value,
                'message': issue.message
            })
            failure.text = issue.suggestion

        rough_string = tostring(testsuites, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
