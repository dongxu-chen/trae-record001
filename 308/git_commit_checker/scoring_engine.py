from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QualityGrade(Enum):
    EXCELLENT = "A"
    GOOD = "B"
    FAIR = "C"
    POOR = "D"
    FAIL = "F"


@dataclass
class CommitQualityReport:
    commit_hash: str
    commit_message: str
    author: str
    date: str
    total_score: float
    max_score: float
    percentage: float
    grade: QualityGrade
    passed: bool
    format_result: Any = None
    scope_result: Any = None
    size_result: Any = None
    consistency_result: Any = None
    history_result: Any = None
    template_result: Any = None
    custom_results: List[Any] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "commit_hash": self.commit_hash,
            "commit_message": self.commit_message,
            "author": self.author,
            "date": self.date,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "grade": self.grade.value,
            "passed": self.passed,
            "format": self._result_to_dict(self.format_result),
            "scope": self._result_to_dict(self.scope_result),
            "size": self._result_to_dict(self.size_result),
            "custom_rules": [self._result_to_dict(r) for r in self.custom_results],
            "suggestions": self.suggestions,
        }

        if self.consistency_result:
            result["consistency"] = self._result_to_dict(self.consistency_result)
        if self.history_result:
            result["history"] = self._result_to_dict(self.history_result)
        if self.template_result:
            result["template"] = self._result_to_dict(self.template_result)
            result["recommendations"] = [
                rec.__dict__ for rec in getattr(self.template_result, "recommendations", [])
            ]

        return result

    def _result_to_dict(self, result: Any) -> Dict[str, Any]:
        if result is None:
            return {}
        if hasattr(result, "__dict__"):
            return {
                "valid": getattr(result, "valid", True),
                "score": getattr(result, "score", 0),
                "max_score": getattr(result, "max_score", 0),
                "issues": getattr(result, "issues", []),
                "details": getattr(result, "details", {}),
            }
        return {}


class ScoringEngine:
    def __init__(self, config: Any):
        self.config = config
        self.pass_threshold = config.get("scoring.pass_threshold", 70)
        self.warning_threshold = config.get("scoring.warning_threshold", 50)

    def calculate_grade(self, percentage: float) -> QualityGrade:
        if percentage >= 90:
            return QualityGrade.EXCELLENT
        elif percentage >= 75:
            return QualityGrade.GOOD
        elif percentage >= 60:
            return QualityGrade.FAIR
        elif percentage >= 40:
            return QualityGrade.POOR
        else:
            return QualityGrade.FAIL

    def generate_report(
        self,
        commit_hash: str,
        commit_message: str,
        author: str,
        date: str,
        format_result: Any,
        scope_result: Any,
        size_result: Any,
        consistency_result: Any = None,
        history_result: Any = None,
        template_result: Any = None,
        custom_results: List[Any] = None,
    ) -> CommitQualityReport:
        custom_results = custom_results or []

        total_score = sum([
            getattr(format_result, "score", 0) if format_result else 0,
            getattr(scope_result, "score", 0) if scope_result else 0,
            getattr(size_result, "score", 0) if size_result else 0,
            getattr(consistency_result, "score", 0) if consistency_result else 0,
            getattr(history_result, "score", 0) if history_result else 0,
            getattr(template_result, "score", 0) if template_result else 0,
        ] + [
            getattr(r, "score", 0) for r in custom_results
        ])

        max_score = sum([
            getattr(format_result, "max_score", 0) if format_result else 0,
            getattr(scope_result, "max_score", 0) if scope_result else 0,
            getattr(size_result, "max_score", 0) if size_result else 0,
            getattr(consistency_result, "max_score", 0) if consistency_result else 0,
            getattr(history_result, "max_score", 0) if history_result else 0,
            getattr(template_result, "max_score", 0) if template_result else 0,
        ] + [
            getattr(r, "max_score", 0) for r in custom_results
        ])

        percentage = round((total_score / max_score * 100), 2) if max_score > 0 else 0
        grade = self.calculate_grade(percentage)
        passed = percentage >= self.pass_threshold

        suggestions = self._generate_suggestions(
            format_result, scope_result, size_result,
            consistency_result, history_result, template_result,
            custom_results, percentage
        )

        return CommitQualityReport(
            commit_hash=commit_hash,
            commit_message=commit_message,
            author=author,
            date=date,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            grade=grade,
            passed=passed,
            format_result=format_result,
            scope_result=scope_result,
            size_result=size_result,
            consistency_result=consistency_result,
            history_result=history_result,
            template_result=template_result,
            custom_results=custom_results,
            suggestions=suggestions,
        )

    def _generate_suggestions(
        self,
        format_result: Any,
        scope_result: Any,
        size_result: Any,
        consistency_result: Any,
        history_result: Any,
        template_result: Any,
        custom_results: List[Any],
        percentage: float,
    ) -> List[str]:
        suggestions: List[str] = []

        if format_result and getattr(format_result, "issues", None):
            suggestions.extend(self._format_suggestions(format_result))

        if scope_result and getattr(scope_result, "issues", None):
            suggestions.extend(self._scope_suggestions(scope_result))

        if size_result and getattr(size_result, "issues", None):
            suggestions.extend(self._size_suggestions(size_result))

        if consistency_result and getattr(consistency_result, "issues", None):
            suggestions.extend(getattr(consistency_result, "issues", []))

        if history_result and getattr(history_result, "issues", None):
            suggestions.extend(getattr(history_result, "issues", []))

        if template_result and getattr(template_result, "issues", None):
            suggestions.extend(getattr(template_result, "issues", []))

        for result in custom_results:
            if getattr(result, "issues", None):
                suggestions.extend(getattr(result, "issues", []))

        if not suggestions:
            if percentage >= 90:
                suggestions.append("提交质量优秀！继续保持良好的提交习惯。")
            elif percentage >= 75:
                suggestions.append("提交质量良好，还有提升空间。")
            else:
                suggestions.append("建议遵循Conventional Commits规范，保持提交精简。")

        return list(dict.fromkeys(suggestions))

    def _format_suggestions(self, result: Any) -> List[str]:
        suggestions = []
        details = getattr(result, "details", {})

        if not details.get("format_valid", False):
            suggestions.append(
                "使用 Conventional Commits 格式: <type>[optional scope]: <description>"
            )
            suggestions.append(
                "常用 type: feat(新功能), fix(修复), docs(文档), refactor(重构), test(测试), chore(构建)"
            )

        if details.get("type") and details["type"] not in ["feat", "fix", "docs", "refactor", "test"]:
            suggestions.append(
                "为提交类型添加更明确的语义：feat(新功能)、fix(修复)、refactor(重构)等"
            )

        if not details.get("scope"):
            suggestions.append(
                "考虑添加 scope 来说明影响范围，如: feat(auth): 添加登录功能"
            )

        if not details.get("has_body", False) and details.get("subject_length", 0) > 50:
            suggestions.append(
                "较长的说明建议放在 body 部分，保持 subject 简洁"
            )

        return suggestions

    def _scope_suggestions(self, result: Any) -> List[str]:
        suggestions = []
        details = getattr(result, "details", {})
        modules = details.get("modules", [])
        module_count = len(modules)

        if module_count > 2:
            suggestions.append(
                f"本次提交涉及 {module_count} 个模块，建议拆分为多个独立提交"
            )
            suggestions.append(
                "拆分原则：每个提交只完成一个逻辑上独立的变更"
            )

        if module_count > 1:
            suggestions.append(
                "跨模块提交前请确认这些改动是相关的，否则请拆分提交"
            )

        return suggestions

    def _size_suggestions(self, result: Any) -> List[str]:
        suggestions = []
        details = getattr(result, "details", {})

        total_lines = details.get("total_lines_changed", 0)
        total_files = details.get("total_files_changed", 0)

        if total_lines > 200:
            suggestions.append(
                "大的提交建议拆分为多个小提交，便于代码审查和回滚"
            )
            suggestions.append(
                "拆分技巧：按功能点、按修复问题、按重构步骤逐步提交"
            )

        if total_files > 10:
            suggestions.append(
                "单次提交文件过多，建议按关注点分离提交"
            )

        if total_lines > 400:
            suggestions.append(
                "非常大的提交会降低代码审查质量，建议与团队沟通拆分方案"
            )

        return suggestions
