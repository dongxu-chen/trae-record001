from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

from .config import QualityGateConfig, QualityGateRule
from .report import QualityReport
from .linters.base import LinterResult


@dataclass
class QualityGateViolation:
    linter: str
    rule_type: str
    actual: float
    threshold: float
    message: str


@dataclass
class QualityGateResult:
    passed: bool
    violations: List[QualityGateViolation] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)


class QualityGateChecker:
    def __init__(self, config: QualityGateConfig):
        self.config = config

    def check(self, report: QualityReport) -> QualityGateResult:
        if not self.config.enabled:
            return QualityGateResult(passed=True)

        violations: List[QualityGateViolation] = []
        passed_rules: List[str] = []

        results_by_linter: Dict[str, LinterResult] = {
            r.linter_name: r for r in report.results
        }

        for rule in self.config.rules:
            if not rule.enabled:
                continue

            linter_result = results_by_linter.get(rule.linter)
            if linter_result is None:
                passed_rules.append(f"{rule.linter}_not_found")
                continue

            rule_violations = self._check_rule(rule, linter_result)
            if rule_violations:
                violations.extend(rule_violations)
            else:
                passed_rules.append(f"{rule.linter}_passed")

        passed = len(violations) == 0

        return QualityGateResult(
            passed=passed,
            violations=violations,
            passed_rules=passed_rules,
        )

    def _check_rule(
        self, rule: QualityGateRule, result: LinterResult
    ) -> List[QualityGateViolation]:
        violations: List[QualityGateViolation] = []

        if rule.max_errors is not None and result.error_count > rule.max_errors:
            violations.append(
                QualityGateViolation(
                    linter=rule.linter,
                    rule_type="max_errors",
                    actual=result.error_count,
                    threshold=rule.max_errors,
                    message=f"{rule.linter} errors ({result.error_count}) exceeds threshold ({rule.max_errors})",
                )
            )

        if rule.max_warnings is not None and result.warning_count > rule.max_warnings:
            violations.append(
                QualityGateViolation(
                    linter=rule.linter,
                    rule_type="max_warnings",
                    actual=result.warning_count,
                    threshold=rule.max_warnings,
                    message=f"{rule.linter} warnings ({result.warning_count}) exceeds threshold ({rule.max_warnings})",
                )
            )

        if rule.min_score is not None and result.score is not None:
            if result.score < rule.min_score:
                violations.append(
                    QualityGateViolation(
                        linter=rule.linter,
                        rule_type="min_score",
                        actual=result.score,
                        threshold=rule.min_score,
                        message=f"{rule.linter} score ({result.score:.2f}) is below threshold ({rule.min_score})",
                    )
                )

        return violations

    def get_exit_code(self, result: QualityGateResult) -> int:
        if not self.config.enabled or result.passed:
            return 0
        return 1 if self.config.block_merge else 0

    def print_summary(self, result: QualityGateResult):
        from colorama import Fore, Style, init

        init(autoreset=True)

        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}  QUALITY GATE CHECK")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        if not self.config.enabled:
            print(f"{Fore.YELLOW}  Quality Gate is disabled{Style.RESET_ALL}")
            return

        if result.passed:
            print(f"{Fore.GREEN}  ✓ Quality Gate PASSED{Style.RESET_ALL}\n")
            if result.passed_rules:
                print(f"  Passed checks: {', '.join(result.passed_rules)}")
        else:
            print(f"{Fore.RED}  ✗ Quality Gate FAILED{Style.RESET_ALL}\n")
            print(f"  Violations ({result.violation_count}):\n")
            for v in result.violations:
                print(f"    {Fore.RED}✗{Style.RESET_ALL} {v.message}")

            if self.config.block_merge:
                print(f"\n  {Fore.RED}Merge is BLOCKED due to quality gate violations{Style.RESET_ALL}")

        print()
