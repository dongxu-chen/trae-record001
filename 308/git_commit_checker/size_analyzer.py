import re
import fnmatch
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SizeAnalysisResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileChangeStats:
    path: str
    insertions: int
    deletions: int
    total: int


@dataclass
class TypeThreshold:
    max_lines: int
    max_files: int
    warn_lines: int
    warn_files: int
    description: str = ""


DEFAULT_TYPE_THRESHOLDS: Dict[str, TypeThreshold] = {
    "feat": TypeThreshold(500, 25, 250, 12, "新功能开发，允许较大变更"),
    "fix": TypeThreshold(300, 15, 150, 8, "Bug修复，变更应相对集中"),
    "refactor": TypeThreshold(1000, 50, 500, 25, "重构操作，允许大幅变更"),
    "style": TypeThreshold(200, 30, 100, 15, "代码风格调整，可能涉及多文件"),
    "docs": TypeThreshold(1000, 50, 500, 25, "文档更新，允许大篇幅修改"),
    "perf": TypeThreshold(400, 20, 200, 10, "性能优化，变更应适度"),
    "test": TypeThreshold(600, 30, 300, 15, "测试代码，允许较多文件"),
    "build": TypeThreshold(300, 20, 150, 10, "构建系统，变更应适度"),
    "ci": TypeThreshold(200, 15, 100, 8, "CI配置，变更应集中"),
    "chore": TypeThreshold(200, 15, 100, 8, "杂项，变更应小"),
    "revert": TypeThreshold(10000, 1000, 5000, 500, "回滚操作，无限制"),
}


class ChangeSizeAnalyzer:
    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("change_size.enabled", True)
        self.weight = config.get("change_size.weight", 35)

        self.base_max_lines = config.get("change_size.max_lines_changed", 400)
        self.base_max_files = config.get("change_size.max_files_changed", 20)
        self.base_warn_lines = config.get("change_size.warn_lines_changed", 200)
        self.base_warn_files = config.get("change_size.warn_files_changed", 10)

        self.use_dynamic_thresholds = config.get(
            "change_size.use_dynamic_thresholds", True
        )

        self.type_thresholds = self._load_type_thresholds(config)

        self.exclude_patterns = config.get("change_size.exclude_patterns", [
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "*.min.js", "*.min.css", "dist/", "build/", "node_modules/"
        ])
        self.exclude_regex = self._compile_exclude_patterns()

        self.refactor_keywords = config.get(
            "change_size.refactor_keywords",
            ["refactor", "重构", "rename", "重命名", "format", "格式化",
             "reorganize", "重组", "restructure", "调整结构"]
        )

    def _load_type_thresholds(self, config: Any) -> Dict[str, TypeThreshold]:
        thresholds = DEFAULT_TYPE_THRESHOLDS.copy()

        custom_thresholds = config.get("change_size.type_thresholds", {})
        for type_name, type_config in custom_thresholds.items():
            thresholds[type_name] = TypeThreshold(
                max_lines=type_config.get("max_lines", self.base_max_lines),
                max_files=type_config.get("max_files", self.base_max_files),
                warn_lines=type_config.get("warn_lines", self.base_warn_lines),
                warn_files=type_config.get("warn_files", self.base_warn_files),
                description=type_config.get("description", ""),
            )

        return thresholds

    def _compile_exclude_patterns(self) -> List[re.Pattern]:
        patterns = []
        for pattern in self.exclude_patterns:
            regex = fnmatch.translate(pattern)
            if pattern.endswith("/"):
                regex = regex.rstrip("\\Z") + ".*"
            patterns.append(re.compile(regex))
        return patterns

    def _should_exclude(self, file_path: str) -> bool:
        normalized_path = file_path.replace("\\", "/")
        for pattern in self.exclude_regex:
            if pattern.match(normalized_path):
                return True
        return False

    def _get_effective_threshold(
        self, commit_types: List[str], commit_message: str, file_stats: List[FileChangeStats], total_lines: int
    ) -> Tuple[TypeThreshold, Dict[str, Any]]:
        details: Dict[str, Any] = {
            "base_max_lines": self.base_max_lines,
            "base_max_files": self.base_max_files,
            "base_warn_lines": self.base_warn_lines,
            "base_warn_files": self.base_warn_files,
        }

        if not self.use_dynamic_thresholds:
            details["used_dynamic"] = False
            details["applied_threshold"] = "base"
            return TypeThreshold(
                max_lines=self.base_max_lines,
                max_files=self.base_max_files,
                warn_lines=self.base_warn_lines,
                warn_files=self.base_warn_files,
            ), details

        details["used_dynamic"] = True
        details["commit_types"] = commit_types

        is_refactoring = self._is_likely_refactoring(commit_message, file_stats, total_lines)
        details["is_refactoring"] = is_refactoring

        if is_refactoring and "refactor" not in commit_types:
            commit_types = ["refactor"] + commit_types
            details["auto_detected_refactor"] = True

        if not commit_types:
            details["applied_threshold"] = "base"
            return TypeThreshold(
                max_lines=self.base_max_lines,
                max_files=self.base_max_files,
                warn_lines=self.base_warn_lines,
                warn_files=self.base_warn_files,
            ), details

        max_lines = self.base_max_lines
        max_files = self.base_max_files
        warn_lines = self.base_warn_lines
        warn_files = self.base_warn_files

        applied_types = []
        for commit_type in commit_types:
            if commit_type in self.type_thresholds:
                threshold = self.type_thresholds[commit_type]
                max_lines = max(max_lines, threshold.max_lines)
                max_files = max(max_files, threshold.max_files)
                warn_lines = max(warn_lines, threshold.warn_lines)
                warn_files = max(warn_files, threshold.warn_files)
                applied_types.append(commit_type)

        details["applied_types"] = applied_types
        details["applied_threshold"] = ", ".join(applied_types) if applied_types else "base"
        details["effective_max_lines"] = max_lines
        details["effective_max_files"] = max_files
        details["effective_warn_lines"] = warn_lines
        details["effective_warn_files"] = warn_files

        return TypeThreshold(
            max_lines=max_lines,
            max_files=max_files,
            warn_lines=warn_lines,
            warn_files=warn_files,
        ), details

    def analyze(
        self,
        file_stats: List[FileChangeStats],
        commit_message: str = "",
        commit_types: Optional[List[str]] = None,
    ) -> SizeAnalysisResult:
        if not self.enabled:
            return SizeAnalysisResult(
                valid=True,
                score=self.weight,
                max_score=self.weight,
                issues=[],
                details={"skipped": True}
            )

        commit_types = commit_types or []

        issues: List[str] = []
        score = self.weight
        max_score = self.weight
        details: Dict[str, Any] = {}

        filtered_stats = [s for s in file_stats if not self._should_exclude(s.path)]
        excluded_files = [s.path for s in file_stats if self._should_exclude(s.path)]

        total_insertions = sum(s.insertions for s in filtered_stats)
        total_deletions = sum(s.deletions for s in filtered_stats)
        total_lines = total_insertions + total_deletions
        total_files = len(filtered_stats)

        threshold, threshold_details = self._get_effective_threshold(
            commit_types, commit_message, filtered_stats, total_lines
        )
        details.update(threshold_details)

        details["total_insertions"] = total_insertions
        details["total_deletions"] = total_deletions
        details["total_lines_changed"] = total_lines
        details["total_files_changed"] = total_files
        details["excluded_files"] = excluded_files
        details["file_stats"] = [
            {"path": s.path, "insertions": s.insertions, "deletions": s.deletions}
            for s in filtered_stats
        ]

        if threshold_details.get("is_refactoring"):
            issues.append(
                f"检测到重构操作，应用宽松阈值（最大 {threshold.max_lines} 行 / {threshold.max_files} 个文件）"
            )
        elif threshold_details.get("applied_types"):
            type_desc = ", ".join(threshold_details["applied_types"])
            issues.append(
                f"根据提交类型 '{type_desc}' 应用动态阈值："
                f"最大 {threshold.max_lines} 行 / {threshold.max_files} 个文件"
            )

        lines_score, lines_issues = self._check_lines(total_lines, threshold)
        score = score * lines_score
        issues.extend(lines_issues)

        files_score, files_issues = self._check_files(total_files, threshold)
        score = score * files_score
        issues.extend(files_issues)

        large_files_score, large_files_issues = self._check_large_files(filtered_stats)
        score = score * large_files_score
        issues.extend(large_files_issues)

        distribution_score, distribution_issues = self._check_distribution(
            filtered_stats, total_lines
        )
        score = score * distribution_score
        issues.extend(distribution_issues)

        if threshold_details.get("is_refactoring"):
            score = min(score * 1.15, self.weight)

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        return SizeAnalysisResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details
        )

    def _check_lines(self, total_lines: int, threshold: TypeThreshold) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if total_lines > threshold.max_lines:
            ratio = total_lines / threshold.max_lines
            issues.append(
                f"代码变更量过大：{total_lines} 行，超过最大值 {threshold.max_lines} 行。"
                f"建议拆分为多个提交（基准: {self.base_max_lines} 行，应用阈值: {threshold.max_lines} 行）"
            )
            if ratio <= 2:
                score = 0.6
            elif ratio <= 3:
                score = 0.4
            else:
                score = 0.2
        elif total_lines > threshold.warn_lines:
            issues.append(
                f"代码变更量较大：{total_lines} 行，超过警告阈值 {threshold.warn_lines} 行"
            )
            score = 0.85
        elif total_lines == 0:
            issues.append("本次提交没有代码变更")
            score = 0.5

        return score, issues

    def _check_files(self, total_files: int, threshold: TypeThreshold) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if total_files > threshold.max_files:
            ratio = total_files / threshold.max_files
            issues.append(
                f"变更文件过多：{total_files} 个文件，超过最大值 {threshold.max_files} 个。"
                f"建议拆分为多个提交（基准: {self.base_max_files} 个，应用阈值: {threshold.max_files} 个）"
            )
            if ratio <= 2:
                score = 0.7
            elif ratio <= 3:
                score = 0.5
            else:
                score = 0.3
        elif total_files > threshold.warn_files:
            issues.append(
                f"变更文件较多：{total_files} 个文件，超过警告阈值 {threshold.warn_files} 个"
            )
            score = 0.9

        return score, issues

    def _check_large_files(self, stats: List[FileChangeStats]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        large_files = [s for s in stats if s.total > 100]
        if large_files:
            large_file_info = ", ".join(
                f"{s.path} ({s.total}行)" for s in sorted(large_files, key=lambda x: -x.total)[:3]
            )
            if len(large_files) > 3:
                large_file_info += f" 等 {len(large_files)} 个文件"
            issues.append(f"存在变更量较大的文件: {large_file_info}")
            score *= 0.9

        return score, issues

    def _check_distribution(
        self,
        stats: List[FileChangeStats],
        total_lines: int
    ) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if not stats or total_lines == 0:
            return score, issues

        largest_file = max(stats, key=lambda s: s.total)
        largest_ratio = largest_file.total / total_lines

        if largest_ratio > 0.8 and len(stats) > 1:
            issues.append(
                f"变更分布不均：{largest_file.path} 占总变更的 {largest_ratio:.0%}，"
                f"其余 {len(stats) - 1} 个文件改动较小"
            )
            score *= 0.95

        return score, issues

    def _is_likely_refactoring(
        self,
        commit_message: str,
        stats: List[FileChangeStats],
        total_lines: int
    ) -> bool:
        message_lower = commit_message.lower()

        if any(keyword in message_lower for keyword in self.refactor_keywords):
            return True

        if stats:
            deletions = sum(s.deletions for s in stats)
            insertions = sum(s.insertions for s in stats)
            if total_lines > 100 and abs(deletions - insertions) < total_lines * 0.2:
                return True

        return False
