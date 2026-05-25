import json
import sys
from typing import List, Dict, Any
from dataclasses import asdict

from .scoring_engine import CommitQualityReport, QualityGrade


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

    @classmethod
    def get_grade_color(cls, grade: QualityGrade) -> str:
        color_map = {
            QualityGrade.EXCELLENT: cls.GREEN,
            QualityGrade.GOOD: cls.CYAN,
            QualityGrade.FAIR: cls.YELLOW,
            QualityGrade.POOR: cls.MAGENTA,
            QualityGrade.FAIL: cls.RED,
        }
        return color_map.get(grade, cls.RESET)

    @classmethod
    def get_score_color(cls, percentage: float) -> str:
        if percentage >= 90:
            return cls.GREEN
        elif percentage >= 75:
            return cls.CYAN
        elif percentage >= 60:
            return cls.YELLOW
        elif percentage >= 40:
            return cls.MAGENTA
        else:
            return cls.RED


class OutputFormatter:
    def __init__(self, config: Any, use_color: bool = True):
        self.config = config
        self.use_color = use_color and config.get("output.color", True)
        self.show_details = config.get("output.show_details", True)
        self.show_suggestions = config.get("output.show_suggestions", True)

    def _color(self, text: str, color: str) -> str:
        if self.use_color:
            return f"{color}{text}{Colors.RESET}"
        return text

    def format(self, reports: List[CommitQualityReport], output_format: str = "human") -> str:
        if output_format == "json":
            return self._format_json(reports)
        elif output_format == "markdown":
            return self._format_markdown(reports)
        else:
            return self._format_human(reports)

    def _format_human(self, reports: List[CommitQualityReport]) -> str:
        lines = []

        for i, report in enumerate(reports):
            if i > 0:
                lines.append("")
                lines.append(self._color("─" * 80, Colors.GRAY))
                lines.append("")

            lines.extend(self._format_single_report_human(report))

        if len(reports) > 1:
            lines.append("")
            lines.append(self._color("═" * 80, Colors.GRAY))
            lines.extend(self._format_summary(reports))

        return "\n".join(lines)

    def _format_single_report_human(self, report: CommitQualityReport) -> List[str]:
        lines = []

        header = self._format_header(report)
        lines.extend(header)
        lines.append("")

        if self.show_details:
            lines.extend(self._format_section_scores(report))
            lines.append("")

        lines.extend(self._format_issues(report))

        if self.show_suggestions and report.suggestions:
            lines.append("")
            lines.extend(self._format_suggestions(report))

        if self.show_details:
            lines.append("")
            lines.extend(self._format_details(report))

        return lines

    def _format_header(self, report: CommitQualityReport) -> List[str]:
        lines = []

        status_icon = "✓" if report.passed else "✗"
        status_color = Colors.GREEN if report.passed else Colors.RED
        status_text = "PASSED" if report.passed else "FAILED"

        grade_color = Colors.get_grade_color(report.grade)
        score_color = Colors.get_score_color(report.percentage)

        lines.append(
            f"{self._color(status_icon, status_color)} "
            f"{self._color(report.commit_hash[:8], Colors.BOLD + Colors.BLUE)} "
            f"- {self._color(report.commit_message.split(chr(10))[0][:60], Colors.BOLD)}"
        )

        score_bar = self._format_score_bar(report.percentage)
        lines.append(
            f"  {self._color(status_text, status_color)} | "
            f"Grade: {self._color(report.grade.value, grade_color + Colors.BOLD)} | "
            f"Score: {self._color(f'{report.percentage:.1f}%', score_color + Colors.BOLD)} | "
            f"{score_bar}"
        )

        lines.append(
            f"  {self._color('Author:', Colors.DIM)} {report.author} | "
            f"{self._color('Date:', Colors.DIM)} {report.date}"
        )

        return lines

    def _format_score_bar(self, percentage: float, width: int = 20) -> str:
        filled = int(percentage / 100 * width)
        empty = width - filled

        color = Colors.get_score_color(percentage)
        bar = f"{'█' * filled}{'░' * empty}"

        return self._color(bar, color)

    def _format_section_scores(self, report: CommitQualityReport) -> List[str]:
        lines = [self._color("  ┌─ Section Scores", Colors.DIM)]

        sections = [
            ("Commit Format", report.format_result),
            ("Change Scope", report.scope_result),
            ("Change Size", report.size_result),
        ]

        for result in report.custom_results:
            sections.append((f"Custom: {getattr(result, 'rule_name', 'Unknown')}", result))

        for name, result in sections:
            if result is None:
                continue

            score = getattr(result, "score", 0)
            max_score = getattr(result, "max_score", 0)
            valid = getattr(result, "valid", True)
            issues = getattr(result, "issues", [])

            if max_score > 0:
                pct = score / max_score * 100
            else:
                pct = 100

            status = "✓" if valid else "✗"
            color = Colors.GREEN if valid else Colors.RED
            score_color = Colors.get_score_color(pct)

            issue_count = len(issues)
            issue_text = f" [{issue_count} issues]" if issue_count > 0 else ""

            lines.append(
                f"  │ {self._color(status, color)} {name:<20} "
                f"{self._color(f'{score:5.1f}/{max_score:<5.0f}', score_color)}"
                f"{self._color(issue_text, Colors.GRAY)}"
            )

        lines.append(self._color("  └────────────────────────────────", Colors.DIM))
        return lines

    def _format_issues(self, report: CommitQualityReport) -> List[str]:
        lines = []
        all_issues = []

        for result in [report.format_result, report.scope_result, report.size_result]:
            if result and hasattr(result, "issues"):
                all_issues.extend(result.issues)

        for result in report.custom_results:
            if hasattr(result, "issues"):
                all_issues.extend(result.issues)

        if all_issues:
            lines.append(self._color("  Issues:", Colors.BOLD + Colors.YELLOW))
            for i, issue in enumerate(all_issues, 1):
                lines.append(f"    {self._color(f'{i}.', Colors.GRAY)} {issue}")

        return lines

    def _format_suggestions(self, report: CommitQualityReport) -> List[str]:
        lines = []
        lines.append(self._color("  💡 Suggestions:", Colors.BOLD + Colors.CYAN))
        for i, suggestion in enumerate(report.suggestions, 1):
            lines.append(f"    {self._color(f'{i}.', Colors.GRAY)} {suggestion}")
        return lines

    def _format_details(self, report: CommitQualityReport) -> List[str]:
        lines = []
        lines.append(self._color("  📊 Details:", Colors.DIM))

        size_details = getattr(report.size_result, "details", {}) if report.size_result else {}
        scope_details = getattr(report.scope_result, "details", {}) if report.scope_result else {}
        format_details = getattr(report.format_result, "details", {}) if report.format_result else {}

        if "total_lines_changed" in size_details:
            lines.append(
                f"    {self._color('Lines changed:', Colors.DIM)} "
                f"{size_details['total_lines_changed']} "
                f"(+{size_details.get('total_insertions', 0)}/-{size_details.get('total_deletions', 0)})"
            )

        if "total_files_changed" in size_details:
            lines.append(
                f"    {self._color('Files changed:', Colors.DIM)} "
                f"{size_details['total_files_changed']}"
            )

        if "modules" in scope_details:
            modules = scope_details["modules"]
            if modules:
                lines.append(
                    f"    {self._color('Modules affected:', Colors.DIM)} "
                    f"{', '.join(modules)}"
                )

        if "type" in format_details:
            lines.append(
                f"    {self._color('Commit type:', Colors.DIM)} "
                f"{format_details['type']}"
            )
            if format_details.get("scope"):
                lines.append(
                    f"    {self._color('Scope:', Colors.DIM)} "
                    f"{format_details['scope']}"
                )

        if "excluded_files" in size_details and size_details["excluded_files"]:
            excluded = size_details["excluded_files"]
            if len(excluded) > 0:
                lines.append(
                    f"    {self._color('Excluded files:', Colors.DIM)} "
                    f"{len(excluded)} file(s) skipped"
                )

        return lines

    def _format_summary(self, reports: List[CommitQualityReport]) -> List[str]:
        lines = []

        passed = sum(1 for r in reports if r.passed)
        total = len(reports)
        avg_score = sum(r.percentage for r in reports) / total
        min_score = min(r.percentage for r in reports)
        max_score = max(r.percentage for r in reports)

        grade_counts = {}
        for r in reports:
            grade_counts[r.grade] = grade_counts.get(r.grade, 0) + 1

        all_passed = passed == total
        status_color = Colors.GREEN if all_passed else Colors.RED
        status_icon = "✓" if all_passed else "✗"

        lines.append("")
        lines.append(
            f"{self._color(status_icon, status_color)} "
            f"{self._color('SUMMARY', Colors.BOLD)} "
            f"({passed}/{total} passed)"
        )
        lines.append(
            f"  Average Score: {self._color(f'{avg_score:.1f}%', Colors.get_score_color(avg_score) + Colors.BOLD)} | "
            f"Min: {self._color(f'{min_score:.1f}%', Colors.get_score_color(min_score))} | "
            f"Max: {self._color(f'{max_score:.1f}%', Colors.get_score_color(max_score))}"
        )

        grade_text = []
        for grade in [QualityGrade.EXCELLENT, QualityGrade.GOOD, QualityGrade.FAIR,
                      QualityGrade.POOR, QualityGrade.FAIL]:
            count = grade_counts.get(grade, 0)
            if count > 0:
                grade_text.append(
                    self._color(f"{grade.value}: {count}", Colors.get_grade_color(grade))
                )
        if grade_text:
            lines.append(f"  Grades: {', '.join(grade_text)}")

        return lines

    def _format_json(self, reports: List[CommitQualityReport]) -> str:
        data = {
            "version": "1.0.0",
            "total_commits": len(reports),
            "passed": sum(1 for r in reports if r.passed),
            "failed": sum(1 for r in reports if not r.passed),
            "average_score": round(sum(r.percentage for r in reports) / len(reports), 2),
            "reports": [r.to_dict() for r in reports],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_markdown(self, reports: List[CommitQualityReport]) -> str:
        lines = []

        lines.append("# Git Commit Quality Report")
        lines.append("")

        if len(reports) > 1:
            passed = sum(1 for r in reports if r.passed)
            total = len(reports)
            avg_score = sum(r.percentage for r in reports) / total
            lines.append(f"**Summary:** {passed}/{total} commits passed")
            lines.append(f"**Average Score:** {avg_score:.1f}%")
            lines.append("")

        for i, report in enumerate(reports):
            if i > 0:
                lines.append("---")
                lines.append("")

            status = "✅ PASSED" if report.passed else "❌ FAILED"
            lines.append(f"## {report.commit_hash[:8]} - {status}")
            lines.append("")
            lines.append(f"- **Grade:** {report.grade.value}")
            lines.append(f"- **Score:** {report.percentage:.1f}% ({report.total_score:.1f}/{report.max_score:.0f})")
            lines.append(f"- **Author:** {report.author}")
            lines.append(f"- **Date:** {report.date}")
            lines.append(f"- **Message:** {report.commit_message.split(chr(10))[0]}")
            lines.append("")

            issues = []
            for result in [report.format_result, report.scope_result, report.size_result]:
                if result and hasattr(result, "issues"):
                    issues.extend(result.issues)
            for result in report.custom_results:
                if hasattr(result, "issues"):
                    issues.extend(result.issues)

            if issues:
                lines.append("### Issues")
                lines.append("")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")

            if report.suggestions:
                lines.append("### Suggestions")
                lines.append("")
                for suggestion in report.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")

        return "\n".join(lines)
