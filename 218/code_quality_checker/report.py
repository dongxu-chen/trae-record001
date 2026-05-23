import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

from tabulate import tabulate
from colorama import Fore, Style, init

from .linters.base import LinterResult

init(autoreset=True)


@dataclass
class QualityReport:
    timestamp: str
    total_errors: int = 0
    total_warnings: int = 0
    total_files_checked: int = 0
    results: List[LinterResult] = field(default_factory=list)
    threshold_passed: bool = True
    threshold_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_files_checked": self.total_files_checked,
            "threshold_passed": self.threshold_passed,
            "threshold_violations": self.threshold_violations,
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "by_linter": {
                    r.linter_name: {
                        "errors": r.error_count,
                        "warnings": r.warning_count,
                        "score": r.score,
                        "files_checked": len(r.files_checked),
                    }
                    for r in self.results
                }
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class ReportGenerator:
    def __init__(self, output_dir: str = "quality-reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        results: List[LinterResult],
        format: str = "table",
        show_summary: bool = True,
    ) -> QualityReport:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_files = len(set(f for r in results for f in r.files_checked))

        report = QualityReport(
            timestamp=timestamp,
            total_errors=total_errors,
            total_warnings=total_warnings,
            total_files_checked=total_files,
            results=results,
        )

        if format == "json":
            self._print_json(report)
        elif format == "table":
            self._print_table(report, show_summary)
        else:
            self._print_text(report, show_summary)

        return report

    def save_report(self, report: QualityReport, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_report_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.to_json())

        return filepath

    def _print_json(self, report: QualityReport):
        print(report.to_json())

    def _print_table(self, report: QualityReport, show_summary: bool):
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}  Code Quality Report - {report.timestamp}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        if show_summary:
            self._print_summary_table(report)

        for result in report.results:
            if not result.files_checked:
                continue
            self._print_linter_result(result)

        self._print_violations(report)

    def _print_summary_table(self, report: QualityReport):
        headers = ["Linter", "Files", "Errors", "Warnings", "Score", "Status"]
        rows = []

        for result in report.results:
            status_color = Fore.GREEN if result.success else Fore.RED
            status = f"{status_color}PASS{Style.RESET_ALL}" if result.success else f"{status_color}FAIL{Style.RESET_ALL}"
            score = f"{result.score:.2f}" if result.score is not None else "N/A"

            rows.append([
                result.linter_name,
                len(result.files_checked),
                f"{Fore.RED}{result.error_count}{Style.RESET_ALL}" if result.error_count > 0 else result.error_count,
                f"{Fore.YELLOW}{result.warning_count}{Style.RESET_ALL}" if result.warning_count > 0 else result.warning_count,
                score,
                status,
            ])

        print(f"{Fore.CYAN}Summary:{Style.RESET_ALL}")
        print(tabulate(rows, headers=headers, tablefmt="github"))
        print()

        total_errors = f"{Fore.RED}{report.total_errors}{Style.RESET_ALL}" if report.total_errors > 0 else report.total_errors
        total_warnings = f"{Fore.YELLOW}{report.total_warnings}{Style.RESET_ALL}" if report.total_warnings > 0 else report.total_warnings
        print(f"Total files checked: {report.total_files_checked}")
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")
        print()

    def _print_linter_result(self, result: LinterResult):
        if not result.issues:
            return

        print(f"\n{Fore.MAGENTA}{result.linter_name.upper()} Issues:{Style.RESET_ALL}")
        print(f"{'-'*80}")

        headers = ["File", "Line", "Col", "Severity", "Rule", "Message"]
        rows = []

        for issue in result.issues:
            severity_color = Fore.RED if issue.severity.lower() == "error" else Fore.YELLOW
            rows.append([
                issue.file,
                issue.line,
                issue.column,
                f"{severity_color}{issue.severity}{Style.RESET_ALL}",
                issue.rule,
                issue.message[:60] + "..." if len(issue.message) > 60 else issue.message,
            ])

        print(tabulate(rows, headers=headers, tablefmt="simple"))
        print()

        fixable = sum(1 for i in result.issues if i.fixable)
        if fixable > 0:
            print(f"{Fore.CYAN}ℹ {fixable} issues can be auto-fixed with --fix{Style.RESET_ALL}")
            print()

    def _print_text(self, report: QualityReport, show_summary: bool):
        print(f"Code Quality Report - {report.timestamp}")
        print("=" * 80)

        if show_summary:
            print(f"\nTotal files checked: {report.total_files_checked}")
            print(f"Total errors: {report.total_errors}")
            print(f"Total warnings: {report.total_warnings}")

        for result in report.results:
            if not result.files_checked:
                continue

            print(f"\n[{result.linter_name}]")
            print(f"  Files checked: {len(result.files_checked)}")
            print(f"  Errors: {result.error_count}")
            print(f"  Warnings: {result.warning_count}")
            if result.score is not None:
                print(f"  Score: {result.score:.2f}/10")

            for issue in result.issues:
                print(f"  {issue.file}:{issue.line}:{issue.column} - "
                      f"[{issue.severity}] {issue.rule}: {issue.message}")

    def _print_violations(self, report: QualityReport):
        if report.threshold_violations:
            print(f"\n{Fore.RED}{'='*80}")
            print(f"{Fore.RED}  THRESHOLD VIOLATIONS:")
            print(f"{Fore.RED}{'='*80}{Style.RESET_ALL}")
            for violation in report.threshold_violations:
                print(f"{Fore.RED}  ✗ {violation}{Style.RESET_ALL}")
            print()
        elif report.threshold_passed:
            print(f"\n{Fore.GREEN}{'='*80}")
            print(f"{Fore.GREEN}  ✓ All thresholds passed!")
            print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
