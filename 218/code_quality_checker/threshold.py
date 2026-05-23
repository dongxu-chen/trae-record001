from typing import List

from .linters.base import LinterResult
from .config import ThresholdConfig
from .report import QualityReport


class ThresholdChecker:
    def __init__(self, config: ThresholdConfig):
        self.config = config

    def check_thresholds(self, report: QualityReport) -> QualityReport:
        violations: List[str] = []

        if report.total_errors > self.config.error:
            violations.append(
                f"Error count ({report.total_errors}) exceeds threshold ({self.config.error})"
            )

        if report.total_warnings > self.config.warning:
            violations.append(
                f"Warning count ({report.total_warnings}) exceeds threshold ({self.config.warning})"
            )

        for result in report.results:
            if result.linter_name == "pylint" and result.score is not None:
                if result.score < self.config.pylint_score:
                    violations.append(
                        f"Pylint score ({result.score:.2f}) is below threshold ({self.config.pylint_score})"
                    )

        report.threshold_violations = violations
        report.threshold_passed = len(violations) == 0

        return report

    def get_exit_code(self, report: QualityReport, fail_on_threshold: bool = True) -> int:
        if not fail_on_threshold:
            return 0

        if not report.threshold_passed:
            return 1

        for result in report.results:
            if not result.success:
                return 1

        return 0
