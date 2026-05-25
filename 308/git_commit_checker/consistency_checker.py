import os
import re
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field


@dataclass
class TestConsistencyResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ConsistencyChecker:
    TEST_FILE_PATTERNS = [
        re.compile(r"^(?P<base>.+)\.test\.(?P<ext>[a-zA-Z0-9]+)$"),
        re.compile(r"^(?P<base>.+)_test\.(?P<ext>[a-zA-Z0-9]+)$"),
        re.compile(r"^(?P<base>.+)\.spec\.(?P<ext>[a-zA-Z0-9]+)$"),
        re.compile(r"^(?P<base>.+)_spec\.(?P<ext>[a-zA-Z0-9]+)$"),
        re.compile(r"^test[s]?/(?P<base>.+)$"),
        re.compile(r"^__tests__/(?P<base>.+)$"),
        re.compile(r"^spec[s]?/(?P<base>.+)$"),
    ]

    SRC_DIRS = {"src", "lib", "main", "app", "source", "sources"}
    TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}

    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("test_consistency.enabled", True)
        self.weight = config.get("test_consistency.weight", 20)
        self.require_test_for_types = set(config.get(
            "test_consistency.require_test_for_types",
            ["feat", "fix", "perf"]
        ))
        self.exclude_patterns = [
            re.compile(p) for p in config.get(
                "test_consistency.exclude_patterns",
                [r"^docs?/", r"^README", r"^LICENSE", r"\.md$"]
            )
        ]
        self.test_file_extensions = set(config.get(
            "test_consistency.test_file_extensions",
            ["py", "js", "ts", "jsx", "tsx", "java", "go", "cpp", "c", "h", "hpp", "rb", "rs"]
        ))

    def check(
        self,
        changed_files: List[str],
        commit_types: List[str],
        file_stats: Optional[List[Any]] = None
    ) -> TestConsistencyResult:
        if not self.enabled:
            return TestConsistencyResult(
                valid=True,
                score=self.weight,
                max_score=self.weight,
                issues=[],
                details={"skipped": True}
            )

        issues: List[str] = []
        score = self.weight
        max_score = self.weight
        details: Dict[str, Any] = {}

        src_files, test_files = self._classify_files(changed_files)
        details["source_files"] = src_files
        details["test_files"] = test_files
        details["source_count"] = len(src_files)
        details["test_count"] = len(test_files)

        if not src_files:
            details["has_source_changes"] = False
            return TestConsistencyResult(
                valid=True,
                score=self.weight,
                max_score=max_score,
                issues=[],
                details=details
            )

        details["has_source_changes"] = True

        missing_tests = self._find_missing_tests(src_files, test_files)
        details["missing_tests"] = missing_tests

        needs_test = self._needs_test_update(commit_types)
        details["needs_test"] = needs_test

        if needs_test and missing_tests:
            missing_count = len(missing_tests)
            issues.append(
                f"检测到 {missing_count} 个源文件变更但缺少对应测试更新。"
                f"涉及文件: {', '.join(self._get_display_names(missing_tests[:3]))}"
                f"{' 等' if missing_count > 3 else ''}"
            )
            issues.append(
                "建议：修改业务代码时一并更新相关测试，确保功能覆盖。"
            )

            penalty = min(0.3 + missing_count * 0.1, 0.7)
            score = score * (1 - penalty)

        test_coverage_ratio = self._calculate_test_coverage_ratio(src_files, test_files)
        details["test_coverage_ratio"] = test_coverage_ratio

        if test_coverage_ratio > 0:
            if test_coverage_ratio >= 0.5:
                score = min(score * 1.1, self.weight)
                details["test_ratio_bonus"] = True
            elif test_coverage_ratio >= 0.3:
                score = min(score * 1.05, self.weight)
                details["test_ratio_bonus"] = True
        else:
            details["test_ratio_bonus"] = False

        if file_stats:
            test_change_stats = self._analyze_test_changes(file_stats, test_files)
            details["test_line_changes"] = test_change_stats

            if test_change_stats["test_insertions"] > 0:
                issues.append(
                    f"本次提交包含 {test_change_stats['test_insertions']} 行新增测试代码，"
                    f"代码质量保障良好！"
                )
                score = min(score * 1.05, self.weight)

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        return TestConsistencyResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details
        )

    def _classify_files(self, files: List[str]) -> Tuple[List[str], List[str]]:
        src_files: List[str] = []
        test_files: List[str] = []

        for file in files:
            if self._is_excluded(file):
                continue

            if self._is_test_file(file):
                test_files.append(file)
            else:
                ext = self._get_extension(file)
                if ext in self.test_file_extensions:
                    src_files.append(file)

        return src_files, test_files

    def _is_test_file(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        basename = os.path.basename(normalized)
        dirname = os.path.dirname(normalized)

        for pattern in self.TEST_FILE_PATTERNS:
            if pattern.match(basename):
                return True

        path_parts = normalized.split("/")
        for part in path_parts:
            if part.lower() in self.TEST_DIRS:
                return True

        return False

    def _is_excluded(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        return any(p.search(normalized) for p in self.exclude_patterns)

    def _get_extension(self, file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        return ext.lstrip(".").lower()

    def _find_missing_tests(
        self, src_files: List[str], test_files: List[str]
    ) -> List[str]:
        missing: List[str] = []
        test_basenames = self._get_test_basenames(test_files)

        for src_file in src_files:
            src_base = self._get_src_base(src_file)
            if src_base and src_base not in test_basenames:
                missing.append(src_file)

        return missing

    def _get_src_base(self, src_file: str) -> Optional[str]:
        normalized = src_file.replace("\\", "/")
        path_parts = normalized.split("/")

        for i, part in enumerate(path_parts):
            if part.lower() in self.SRC_DIRS and i < len(path_parts) - 1:
                path_parts = path_parts[i + 1:]
                break

        if len(path_parts) == 0:
            return None

        base = "/".join(path_parts)
        base, _ = os.path.splitext(base)
        return base.lower()

    def _get_test_basenames(self, test_files: List[str]) -> Set[str]:
        basenames: Set[str] = set()

        for test_file in test_files:
            normalized = test_file.replace("\\", "/")
            path_parts = normalized.split("/")

            test_dir_idx = -1
            for i, part in enumerate(path_parts):
                if part.lower() in self.TEST_DIRS:
                    test_dir_idx = i
                    break

            if test_dir_idx == -1:
                filename = os.path.basename(normalized)
                name, _ = os.path.splitext(filename)
                for suffix in [".test", "_test", ".spec", "_spec"]:
                    if name.endswith(suffix):
                        name = name[:-len(suffix)]
                        break
                for prefix in ["test_", "spec_"]:
                    if name.startswith(prefix):
                        name = name[len(prefix):]
                        break
                basenames.add(name.lower())
                continue

            src_parts = path_parts[:test_dir_idx]
            test_parts = path_parts[test_dir_idx + 1:]

            if src_parts:
                for i, part in enumerate(src_parts):
                    if part.lower() in self.SRC_DIRS and i < len(src_parts) - 1:
                        src_parts = src_parts[i + 1:]
                        break

            if test_parts:
                test_file_path = "/".join(test_parts)
                name, _ = os.path.splitext(test_file_path)
                filename = os.path.basename(name)
                dirname = os.path.dirname(name)

                for suffix in [".test", "_test", ".spec", "_spec"]:
                    if filename.endswith(suffix):
                        filename = filename[:-len(suffix)]
                        break

                for prefix in ["test_", "spec_"]:
                    if filename.startswith(prefix):
                        filename = filename[len(prefix):]
                        break

                if dirname:
                    full_name = f"{dirname}/{filename}"
                else:
                    full_name = filename

                if src_parts:
                    src_path = "/".join(src_parts)
                    full_name = f"{src_path}/{full_name}"

                basenames.add(full_name.lower())

        return basenames

    def _needs_test_update(self, commit_types: List[str]) -> bool:
        if not commit_types:
            return False
        return any(t in self.require_test_for_types for t in commit_types)

    def _get_display_names(self, files: List[str]) -> List[str]:
        names = []
        for f in files:
            parts = f.replace("\\", "/").split("/")
            if len(parts) > 3:
                names.append(".../" + "/".join(parts[-3:]))
            else:
                names.append(f)
        return names

    def _calculate_test_coverage_ratio(
        self, src_files: List[str], test_files: List[str]
    ) -> float:
        if not src_files:
            return 0.0

        src_modules = set(self._get_src_base(f) for f in src_files)
        test_modules = self._get_test_basenames(test_files)

        matched = sum(1 for m in src_modules if m and m in test_modules)
        total = len([m for m in src_modules if m])

        return matched / total if total > 0 else 0.0

    def _analyze_test_changes(
        self, file_stats: List[Any], test_files: List[str]
    ) -> Dict[str, int]:
        test_paths = set(test_files)
        insertions = 0
        deletions = 0

        for stat in file_stats:
            if stat.path in test_paths:
                insertions += stat.insertions
                deletions += stat.deletions

        return {
            "test_insertions": insertions,
            "test_deletions": deletions,
            "test_total": insertions + deletions
        }
