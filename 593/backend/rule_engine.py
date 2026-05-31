import re
import fnmatch
import json
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class Severity(Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class CheckStatus(Enum):
    PASS = 'pass'
    FAIL = 'fail'
    SKIP = 'skip'
    WARNING = 'warning'


@dataclass
class ValidationResult:
    rule_name: str
    passed: bool
    severity: Severity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckItem:
    id: str
    name: str
    description: str
    category: str
    status: CheckStatus
    severity: Severity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    check_time: str = field(default_factory=lambda: datetime.now().isoformat())
    suggestion: Optional[str] = None
    documentation_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'status': self.status.value,
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'check_time': self.check_time,
            'suggestion': self.suggestion,
            'documentation_url': self.documentation_url
        }


@dataclass
class CheckResult:
    category: str
    display_name: str
    status: CheckStatus
    items: List[CheckItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'display_name': self.display_name,
            'status': self.status.value,
            'items': [item.to_dict() for item in self.items],
            'metadata': self.metadata,
            'summary': {
                'total': len(self.items),
                'passed': len([i for i in self.items if i.status == CheckStatus.PASS]),
                'failed': len([i for i in self.items if i.status == CheckStatus.FAIL]),
                'warnings': len([i for i in self.items if i.status == CheckStatus.WARNING]),
                'skipped': len([i for i in self.items if i.status == CheckStatus.SKIP])
            }
        }

    def get_errors(self) -> List[CheckItem]:
        return [i for i in self.items if i.status == CheckStatus.FAIL and i.severity == Severity.ERROR]

    def get_warnings(self) -> List[CheckItem]:
        return [i for i in self.items if i.status == CheckStatus.WARNING or (i.status == CheckStatus.FAIL and i.severity == Severity.WARNING)]


@dataclass
class Report:
    report_id: str = field(default_factory=lambda: f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    repo_path: Optional[str] = None
    check_results: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        check_results_dict = [cr.to_dict() for cr in self.check_results]
        
        all_items = [item for cr in self.check_results for item in cr.items]
        errors = [i for i in all_items if i.status == CheckStatus.FAIL and i.severity == Severity.ERROR]
        warnings = [i for i in all_items if i.status == CheckStatus.WARNING or (i.status == CheckStatus.FAIL and i.severity == Severity.WARNING)]
        passed = [i for i in all_items if i.status == CheckStatus.PASS]
        skipped = [i for i in all_items if i.status == CheckStatus.SKIP]

        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at,
            'source_branch': self.source_branch,
            'target_branch': self.target_branch,
            'repo_path': self.repo_path,
            'check_results': check_results_dict,
            'summary': {
                'total_checks': len(all_items),
                'errors': len(errors),
                'warnings': len(warnings),
                'passed': len(passed),
                'skipped': len(skipped),
                'status': 'failed' if len(errors) > 0 else 'passed',
                'error_items': [i.to_dict() for i in errors],
                'warning_items': [i.to_dict() for i in warnings]
            }
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_checklist(self) -> str:
        lines = []
        lines.append(f'# Git Branch Policy Check Report - {self.report_id}')
        lines.append('')
        lines.append(f'- **Repository**: `{self.repo_path}`')
        lines.append(f'- **Source Branch**: `{self.source_branch}`')
        lines.append(f'- **Target Branch**: `{self.target_branch}`')
        lines.append(f'- **Generated At**: {self.generated_at}')
        lines.append('')

        summary = self.to_dict()['summary']
        lines.append('## Summary')
        lines.append('')
        lines.append(f'- [{"x" if summary["status"] == "failed" else " "}] Overall Status: **{summary["status"].upper()}**')
        lines.append(f'- Total Checks: **{summary["total_checks"]}**')
        lines.append(f'- {chr(10003) if summary["passed"] > 0 else chr(10007)} Passed: **{summary["passed"]}**')
        lines.append(f'- {chr(10003) if summary["errors"] == 0 else chr(10007)} Errors: **{summary["errors"]}**')
        lines.append(f'- {chr(10003) if summary["warnings"] == 0 else chr(10007)} Warnings: **{summary["warnings"]}**')
        lines.append('')

        for cr in self.check_results:
            cr_dict = cr.to_dict()
            lines.append(f'## {cr.display_name}')
            lines.append('')
            
            for item in cr.items:
                check = chr(10003) if item.status == CheckStatus.PASS else chr(10007)
                if item.status == CheckStatus.WARNING:
                    check = chr(9888)
                elif item.status == CheckStatus.SKIP:
                    check = chr(9717)
                
                status_str = item.status.value.upper()
                severity_str = item.severity.value.upper()
                
                lines.append(f'- {check} **[{status_str}]** {item.name}')
                lines.append(f'  - Category: `{item.category}` | Severity: `{severity_str}`')
                lines.append(f'  - {item.message}')
                if item.suggestion:
                    lines.append(f'  - 💡 Suggestion: {item.suggestion}')
                if item.details:
                    lines.append(f'  - Details:')
                    for key, value in item.details.items():
                        lines.append(f'    - {key}: `{value}`')
                lines.append('')

        return '\n'.join(lines)


class Rule:
    def __init__(self, name: str, check_func: Callable, severity: Severity = Severity.ERROR):
        self.name = name
        self.check_func = check_func
        self.severity = severity

    def check(self, *args, **kwargs) -> ValidationResult:
        try:
            result = self.check_func(*args, **kwargs)
            if isinstance(result, tuple):
                passed, message, details = result[0], result[1], result[2] if len(result) > 2 else {}
            else:
                passed, message, details = result, '', {}
            
            return ValidationResult(
                rule_name=self.name,
                passed=passed,
                severity=self.severity,
                message=message,
                details=details
            )
        except Exception as e:
            return ValidationResult(
                rule_name=self.name,
                passed=False,
                severity=Severity.ERROR,
                message=f'Rule execution failed: {str(e)}',
                details={'error': str(e)}
            )


class RuleEngine:
    def __init__(self):
        self.rules: Dict[str, List[Rule]] = {}

    def add_rule(self, category: str, rule: Rule):
        if category not in self.rules:
            self.rules[category] = []
        self.rules[category].append(rule)

    def run_category(self, category: str, *args, **kwargs) -> List[ValidationResult]:
        results = []
        if category in self.rules:
            for rule in self.rules[category]:
                results.append(rule.check(*args, **kwargs))
        return results

    def run_all(self, *args, **kwargs) -> Dict[str, List[ValidationResult]]:
        all_results = {}
        for category in self.rules:
            all_results[category] = self.run_category(category, *args, **kwargs)
        return all_results

    @staticmethod
    def match_pattern(text: str, pattern: str, use_regex: bool = True) -> bool:
        if use_regex:
            return bool(re.match(pattern, text))
        return fnmatch.fnmatch(text, pattern)

    @staticmethod
    def match_glob_pattern(text: str, pattern: str) -> bool:
        return fnmatch.fnmatch(text, pattern)


class Checker:
    def __init__(self, git_utils, config):
        self.git_utils = git_utils
        self.config = config
        self.rule_engine = RuleEngine()
        self._build_rules()

    def _build_rules(self):
        pass

    def check(self) -> List[ValidationResult]:
        pass
