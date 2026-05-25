import re
import os
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field

from .module_dependency import (
    ModuleDependencyGraph,
    DependencyExtractor,
    CrossModuleAnalyzer,
)


@dataclass
class ScopeAnalysisResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ChangeScopeAnalyzer:
    def __init__(self, config: Any, repo_path: Optional[str] = None):
        self.config = config
        self.repo_path = repo_path or os.getcwd()
        self.enabled = config.get("change_scope.enabled", True)
        self.weight = config.get("change_scope.weight", 30)
        self.module_patterns = [
            re.compile(p) for p in config.get("change_scope.module_patterns", [
                r"^src/([^/]+)/",
                r"^packages/([^/]+)/",
                r"^([^/]+)/",
            ])
        ]
        self.max_modules = config.get("change_scope.max_modules_per_commit", 2)
        self.cross_module_warning = config.get("change_scope.cross_module_warning", True)
        self.use_dependency_graph = config.get(
            "change_scope.use_dependency_graph", True
        )
        self.dependency_graph_cache: Optional[ModuleDependencyGraph] = None

    def _get_dependency_graph(self) -> ModuleDependencyGraph:
        if self.dependency_graph_cache is None:
            extractor = DependencyExtractor(self.repo_path, self.module_patterns)
            self.dependency_graph_cache = extractor.extract_graph()
        return self.dependency_graph_cache

    def analyze(self, changed_files: List[str]) -> ScopeAnalysisResult:
        if not self.enabled:
            return ScopeAnalysisResult(
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

        modules = self._extract_modules(changed_files)
        file_module_map = self._map_files_to_modules(changed_files)

        details["changed_files"] = changed_files
        details["file_count"] = len(changed_files)
        details["modules"] = sorted(list(modules))
        details["module_count"] = len(modules)
        details["file_module_map"] = file_module_map

        module_score, module_issues = self._check_module_count(modules)
        score = score * module_score
        issues.extend(module_issues)

        if self.use_dependency_graph and len(modules) > 1:
            dep_score, dep_issues, dep_details = self._analyze_module_dependencies(modules)
            score = score * dep_score
            issues.extend(dep_issues)
            details.update(dep_details)
            details["used_dependency_graph"] = True
        else:
            coherence_score, coherence_issues = self._check_coherence(
                changed_files, modules, file_module_map
            )
            score = score * coherence_score
            issues.extend(coherence_issues)
            details["used_dependency_graph"] = False

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        return ScopeAnalysisResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details
        )

    def _extract_modules(self, files: List[str]) -> Set[str]:
        modules: Set[str] = set()
        for file_path in files:
            normalized_path = file_path.replace("\\", "/")
            for pattern in self.module_patterns:
                match = pattern.match(normalized_path)
                if match:
                    module_name = match.group(1)
                    if module_name and not module_name.startswith("."):
                        modules.add(module_name)
                    break
        return modules

    def _map_files_to_modules(self, files: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for file_path in files:
            normalized_path = file_path.replace("\\", "/")
            module = "unknown"
            for pattern in self.module_patterns:
                match = pattern.match(normalized_path)
                if match:
                    module_name = match.group(1)
                    if module_name and not module_name.startswith("."):
                        module = module_name
                    break
            mapping[file_path] = module
        return mapping

    def _check_module_count(self, modules: Set[str]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0
        count = len(modules)

        if count > self.max_modules:
            issues.append(
                f"本次提交涉及 {count} 个模块，超过了最大建议值 {self.max_modules} 个。"
                f"涉及模块: {', '.join(sorted(modules))}"
            )
            if count <= self.max_modules * 2:
                score = 0.7
            elif count <= self.max_modules * 3:
                score = 0.5
            else:
                score = 0.3
        elif count == 0:
            issues.append("未能识别出变更涉及的模块")
            score = 0.8
        elif count == 1:
            pass
        elif self.cross_module_warning:
            issues.append(
                f"本次提交涉及 {count} 个模块: {', '.join(sorted(modules))}。"
                "正在分析模块间依赖关系..."
            )
            score = 0.95

        return score, issues

    def _analyze_module_dependencies(
        self, modules: Set[str]
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        try:
            graph = self._get_dependency_graph()
            analyzer = CrossModuleAnalyzer(graph)

            score, issues, details = analyzer.analyze_cross_module_change(modules)

            graph_info = {
                "total_modules_in_graph": len(graph.modules),
                "total_dependencies": sum(len(deps) for deps in graph.dependencies.values()),
            }
            details["graph_info"] = graph_info

            if len(graph.modules) == 0:
                issues.append("无法构建模块依赖图，可能项目中没有可识别的源文件")
                details["graph_available"] = False
            else:
                details["graph_available"] = True

            return score, issues, details
        except Exception as e:
            issues.append(f"模块依赖分析失败: {str(e)}")
            return 0.9, issues, {"dependency_analysis_error": str(e)}

    def _check_coherence(
        self,
        files: List[str],
        modules: Set[str],
        file_module_map: Dict[str, str]
    ) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if len(modules) <= 1:
            return score, issues

        module_file_counts: Dict[str, int] = {}
        for file_path, module in file_module_map.items():
            module_file_counts[module] = module_file_counts.get(module, 0) + 1

        if len(modules) > 1:
            max_files = max(module_file_counts.values())
            min_files = min(module_file_counts.values())
            if max_files > min_files * 5 and min_files == 1:
                main_modules = [m for m, c in module_file_counts.items() if c == max_files]
                minor_modules = [m for m, c in module_file_counts.items() if c == 1]
                issues.append(
                    f"提交可能包含不相关的改动。主要修改在 {', '.join(main_modules)}，"
                    f"但同时包含对 {', '.join(minor_modules)} 的零散修改"
                )
                score *= 0.85

        file_types = set()
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext:
                file_types.add(ext)

        if len(file_types) > 5 and len(modules) > 2:
            issues.append(
                f"提交涉及多种文件类型 ({', '.join(sorted(file_types))}) 和多个模块，"
                "建议按功能或模块拆分提交"
            )
            score *= 0.9

        return score, issues
