import re
import os
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import ast


@dataclass
class ModuleDependencyGraph:
    modules: Set[str] = field(default_factory=set)
    dependencies: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    dependents: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    module_files: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def add_module(self, module: str):
        self.modules.add(module)

    def add_dependency(self, from_module: str, to_module: str):
        if from_module == to_module:
            return
        self.add_module(from_module)
        self.add_module(to_module)
        self.dependencies[from_module].add(to_module)
        self.dependents[to_module].add(from_module)

    def add_module_file(self, module: str, filepath: str):
        self.add_module(module)
        self.module_files[module].add(filepath)

    def get_dependencies(self, module: str) -> Set[str]:
        return self.dependencies.get(module, set())

    def get_dependents(self, module: str) -> Set[str]:
        return self.dependents.get(module, set())

    def get_related_modules(self, module: str, max_depth: int = 2) -> Set[str]:
        related = set()
        visited = set()
        queue = [(module, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            if current != module:
                related.add(current)

            for dep in self.get_dependencies(current):
                if dep not in visited:
                    queue.append((dep, depth + 1))

            for dep in self.get_dependents(current):
                if dep not in visited:
                    queue.append((dep, depth + 1))

        return related

    def are_modules_related(self, module1: str, module2: str) -> bool:
        if module1 == module2:
            return True
        return module2 in self.get_related_modules(module1)

    def get_module_clusters(self) -> List[Set[str]]:
        visited = set()
        clusters = []

        for module in self.modules:
            if module in visited:
                continue

            cluster = set()
            queue = [module]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.add(current)

                for dep in self.get_dependencies(current):
                    if dep not in visited:
                        queue.append(dep)
                for dep in self.get_dependents(current):
                    if dep not in visited:
                        queue.append(dep)

            if cluster:
                clusters.append(cluster)

        return clusters

    def find_shortest_path(self, from_module: str, to_module: str) -> Optional[List[str]]:
        if from_module == to_module:
            return [from_module]

        visited = set()
        queue = [(from_module, [from_module])]

        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            for neighbor in self.get_dependencies(current) | self.get_dependents(current):
                if neighbor == to_module:
                    return path + [neighbor]
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def calculate_cohesion_score(self, modules: Set[str]) -> float:
        if len(modules) <= 1:
            return 1.0

        total_pairs = len(modules) * (len(modules) - 1) / 2
        if total_pairs == 0:
            return 1.0

        related_pairs = 0
        module_list = list(modules)

        for i in range(len(module_list)):
            for j in range(i + 1, len(module_list)):
                if self.are_modules_related(module_list[i], module_list[j]):
                    related_pairs += 1

        return related_pairs / total_pairs


class DependencyExtractor:
    PYTHON_IMPORT_PATTERN = re.compile(
        r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))",
        re.MULTILINE
    )

    JS_IMPORT_PATTERN = re.compile(
        r"(?:import\s+(?:.+\s+from\s+)?['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
        re.MULTILINE
    )

    JAVA_IMPORT_PATTERN = re.compile(
        r"^\s*import\s+([\w.]+);",
        re.MULTILINE
    )

    C_INCLUDE_PATTERN = re.compile(
        r'^\s*#\s*include\s*[<"]([^">]+)[">]',
        re.MULTILINE
    )

    GO_IMPORT_PATTERN = re.compile(
        r'"([^"]+)"',
        re.MULTILINE
    )

    def __init__(self, repo_path: str, module_patterns: List[re.Pattern]):
        self.repo_path = repo_path
        self.module_patterns = module_patterns

    def extract_graph(self) -> ModuleDependencyGraph:
        graph = ModuleDependencyGraph()

        for root, dirs, files in os.walk(self.repo_path):
            if self._should_skip_directory(root):
                dirs[:] = []
                continue

            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    rel_path = os.path.relpath(filepath, self.repo_path)
                    normalized_path = rel_path.replace("\\", "/")

                    module = self._extract_module(normalized_path)
                    if module:
                        graph.add_module_file(module, normalized_path)
                        graph.add_module(module)

                        dependencies = self._extract_dependencies(filepath)
                        for dep in dependencies:
                            dep_module = self._extract_module(dep) or self._extract_module_from_import(dep)
                            if dep_module and dep_module != module:
                                graph.add_dependency(module, dep_module)
                except Exception:
                    continue

        return graph

    def _should_skip_directory(self, path: str) -> bool:
        skip_patterns = [
            "__pycache__",
            "node_modules",
            ".git",
            "dist",
            "build",
            "target",
            ".idea",
            ".vscode",
            "venv",
            ".venv",
            "env",
        ]
        return any(p in path for p in skip_patterns)

    def _extract_module(self, filepath: str) -> Optional[str]:
        normalized_path = filepath.replace("\\", "/")
        for pattern in self.module_patterns:
            match = pattern.match(normalized_path)
            if match:
                module_name = match.group(1)
                if module_name and not module_name.startswith("."):
                    return module_name
        return None

    def _extract_module_from_import(self, import_path: str) -> Optional[str]:
        normalized = import_path.replace(".", "/").replace("\\", "/")
        for pattern in self.module_patterns:
            match = pattern.match(normalized)
            if match:
                module_name = match.group(1)
                if module_name and not module_name.startswith("."):
                    return module_name
        return None

    def _extract_dependencies(self, filepath: str) -> List[str]:
        ext = os.path.splitext(filepath)[1].lower()

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        dependencies = []

        if ext == ".py":
            dependencies.extend(self._extract_python_imports(content))
        elif ext in [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]:
            dependencies.extend(self._extract_js_imports(content))
        elif ext in [".java", ".kt", ".scala"]:
            dependencies.extend(self._extract_java_imports(content))
        elif ext in [".c", ".cpp", ".h", ".hpp", ".cc"]:
            dependencies.extend(self._extract_c_includes(content))
        elif ext == ".go":
            dependencies.extend(self._extract_go_imports(content))

        return dependencies

    def _extract_python_imports(self, content: str) -> List[str]:
        imports = []
        for match in self.PYTHON_IMPORT_PATTERN.finditer(content):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.append(imp)
        return imports

    def _extract_js_imports(self, content: str) -> List[str]:
        imports = []
        for match in self.JS_IMPORT_PATTERN.finditer(content):
            imp = match.group(1) or match.group(2)
            if imp and not imp.startswith("."):
                imports.append(imp)
        return imports

    def _extract_java_imports(self, content: str) -> List[str]:
        imports = []
        for match in self.JAVA_IMPORT_PATTERN.finditer(content):
            imp = match.group(1)
            if imp:
                imports.append(imp)
        return imports

    def _extract_c_includes(self, content: str) -> List[str]:
        imports = []
        for match in self.C_INCLUDE_PATTERN.finditer(content):
            imp = match.group(1)
            if imp:
                imports.append(imp)
        return imports

    def _extract_go_imports(self, content: str) -> List[str]:
        imports = []
        import_block_match = re.search(
            r"import\s*\((.*?)\)", content, re.DOTALL
        )
        if import_block_match:
            import_block = import_block_match.group(1)
            for match in self.GO_IMPORT_PATTERN.finditer(import_block):
                imp = match.group(1)
                if imp:
                    imports.append(imp)
        return imports


class CrossModuleAnalyzer:
    def __init__(self, graph: ModuleDependencyGraph):
        self.graph = graph

    def analyze_cross_module_change(
        self, changed_modules: Set[str]
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        issues: List[str] = []
        details: Dict[str, Any] = {}

        if len(changed_modules) <= 1:
            return 1.0, [], {"cross_module": False}

        details["cross_module"] = True
        details["changed_modules"] = sorted(list(changed_modules))

        cohesion_score = self.graph.calculate_cohesion_score(changed_modules)
        details["cohesion_score"] = cohesion_score

        unrelated_modules = self._find_unrelated_modules(changed_modules)
        details["unrelated_modules"] = sorted(list(unrelated_modules))

        related_clusters = self._find_related_clusters(changed_modules)
        details["related_clusters"] = [sorted(list(c)) for c in related_clusters]

        score = 1.0

        if unrelated_modules:
            issues.append(
                f"检测到不相关的模块变更: {', '.join(sorted(unrelated_modules))}。"
                f"这些模块没有直接或间接的依赖关系，建议拆分提交。"
            )
            score *= 0.6

        if len(related_clusters) > 1:
            cluster_desc = "; ".join(
                f"[{', '.join(sorted(c))}]" for c in related_clusters
            )
            issues.append(
                f"提交涉及 {len(related_clusters)} 个独立的模块集群: {cluster_desc}。"
                f"建议按集群拆分提交。"
            )
            score *= 0.7 ** (len(related_clusters) - 1)

        if cohesion_score < 0.3:
            issues.append(
                f"模块间关联性很低（{cohesion_score:.1%}），"
                f"建议拆分为多个独立提交。"
            )
            score *= 0.8
        elif cohesion_score < 0.6:
            issues.append(
                f"模块间关联性一般（{cohesion_score:.1%}），"
                f"请确认这些改动是否属于同一个逻辑变更。"
            )
            score *= 0.95

        for module in sorted(changed_modules):
            related = self.graph.get_related_modules(module, max_depth=1)
            changed_related = related & changed_modules
            if changed_related:
                issues.append(
                    f"模块 '{module}' 的关联模块 {', '.join(sorted(changed_related))} 也被修改，"
                    f"这是合理的耦合变更。"
                )

        module_paths = {}
        for module in changed_modules:
            paths = self.graph.module_files.get(module, set())
            if paths:
                module_paths[module] = sorted(list(paths))[:5]
        details["module_file_examples"] = module_paths

        dependency_chains = self._find_dependency_chains(changed_modules)
        if dependency_chains:
            details["dependency_chains"] = dependency_chains
            chain_desc = " → ".join(dependency_chains[0])
            issues.append(
                f"检测到模块间依赖链: {chain_desc}。"
                f"这是正常的级联变更。"
            )
            score = min(score * 1.1, 1.0)

        return round(score, 4), issues, details

    def _find_unrelated_modules(self, modules: Set[str]) -> Set[str]:
        unrelated = set()
        module_list = list(modules)

        for i, module in enumerate(module_list):
            has_relation = False
            for j, other in enumerate(module_list):
                if i != j and self.graph.are_modules_related(module, other):
                    has_relation = True
                    break
            if not has_relation:
                unrelated.add(module)

        return unrelated

    def _find_related_clusters(self, modules: Set[str]) -> List[Set[str]]:
        visited = set()
        clusters = []

        for module in modules:
            if module in visited:
                continue

            cluster = set()
            queue = [module]

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.add(current)

                for other in modules:
                    if other not in visited and self.graph.are_modules_related(current, other):
                        queue.append(other)

            if cluster:
                clusters.append(cluster)

        return clusters

    def _find_dependency_chains(self, modules: Set[str]) -> List[List[str]]:
        chains = []
        module_list = list(modules)

        for i in range(len(module_list)):
            for j in range(len(module_list)):
                if i != j:
                    path = self.graph.find_shortest_path(module_list[i], module_list[j])
                    if path and len(path) >= 2:
                        chains.append(path)

        chains.sort(key=len, reverse=True)
        return chains[:3]
