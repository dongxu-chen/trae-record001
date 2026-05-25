"""
漏洞可达性分析模块
通过静态代码分析判断漏洞代码是否被实际调用，减少误报
"""
import os
import ast
import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from ..models import (
    Vulnerability,
    Dependency,
    ReachabilityInfo,
    PackageManager,
)


class ReachabilityAnalyzer:
    """漏洞可达性分析器"""

    def __init__(self, project_path: str):
        self.project_path = project_path
        self._source_files: Dict[str, List[str]] = {}
        self._import_graph: Dict[str, Set[str]] = {}
        self._call_graph: Dict[str, Set[str]] = {}
        self._ast_cache: Dict[str, ast.AST] = {}

    def analyze(
        self,
        vulnerabilities: List[Vulnerability],
    ) -> List[Vulnerability]:
        """分析漏洞的可达性"""
        if not vulnerabilities:
            return vulnerabilities

        print("   ↳ Analyzing reachability...")
        self._build_source_index()

        for vuln in vulnerabilities:
            try:
                reachability = self._analyze_vulnerability(vuln)
                vuln.reachability = reachability
            except Exception as e:
                vuln.reachability = ReachabilityInfo(
                    is_reachable=True,
                    confidence=0.5,
                    evidence=[f"Analysis error: {str(e)}"],
                    analysis_method="static_fallback",
                )

        reachable_count = sum(1 for v in vulnerabilities if v.reachability and v.reachability.is_reachable)
        print(f"   ↳ Reachable: {reachable_count}/{len(vulnerabilities)} vulnerabilities")

        return vulnerabilities

    def _build_source_index(self) -> None:
        """构建源代码索引"""
        self._find_source_files()
        self._build_import_graph()
        self._build_call_graph()

    def _find_source_files(self) -> None:
        """查找项目中的所有源代码文件"""
        file_patterns = {
            PackageManager.PIP: [".py"],
            PackageManager.NPM: [".js", ".jsx", ".ts", ".tsx"],
            PackageManager.MAVEN: [".java", ".kt", ".scala"],
            PackageManager.GO: [".go"],
        }

        pm = self._detect_package_manager()
        extensions = file_patterns.get(pm, [".py", ".js", ".ts", ".java", ".kt", ".go"])

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in ["node_modules", "target", "dist", "build", ".git", "venv", "__pycache__"]]

            for filename in files:
                if any(filename.endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                        self._source_files[filepath] = lines

                        if filepath.endswith(".py"):
                            try:
                                tree = ast.parse("".join(lines), filename=filepath)
                                self._ast_cache[filepath] = tree
                            except (SyntaxError, IndentationError):
                                pass
                    except Exception:
                        pass

    def _detect_package_manager(self) -> PackageManager:
        """检测项目包管理器"""
        if os.path.exists(os.path.join(self.project_path, "requirements.txt")):
            return PackageManager.PIP
        elif os.path.exists(os.path.join(self.project_path, "package.json")):
            return PackageManager.NPM
        elif os.path.exists(os.path.join(self.project_path, "pom.xml")):
            return PackageManager.MAVEN
        elif os.path.exists(os.path.join(self.project_path, "go.mod")):
            return PackageManager.GO
        return PackageManager.UNKNOWN

    def _build_import_graph(self) -> None:
        """构建导入图"""
        for filepath, lines in self._source_files.items():
            imports = set()

            if filepath.endswith(".py"):
                imports.update(self._extract_python_imports(filepath, lines))
            elif filepath.endswith((".js", ".jsx", ".ts", ".tsx")):
                imports.update(self._extract_js_imports(lines))
            elif filepath.endswith((".java", ".kt")):
                imports.update(self._extract_java_imports(lines))
            elif filepath.endswith(".go"):
                imports.update(self._extract_go_imports(lines))

            if imports:
                self._import_graph[filepath] = imports

    def _extract_python_imports(self, filepath: str, lines: List[str]) -> Set[str]:
        """提取 Python 导入"""
        imports = set()

        if filepath in self._ast_cache:
            tree = self._ast_cache[filepath]
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        else:
            for line in lines:
                s = line.strip()
                if s.startswith("import "):
                    match = re.match(r"^import\s+([a-zA-Z0-9_\.]+)", s)
                    if match:
                        imports.add(match.group(1).split(".")[0])
                elif s.startswith("from "):
                    match = re.match(r"^from\s+([a-zA-Z0-9_\.]+)", s)
                    if match:
                        imports.add(match.group(1).split(".")[0])

        return imports

    def _extract_js_imports(self, lines: List[str]) -> Set[str]:
        """提取 JavaScript/TypeScript 导入"""
        imports = set()

        for line in lines:
            s = line.strip()
            patterns = [
                r"^import\s+(?:.+?\s+from\s+)?['\"]([^'\"]+)['\"]",
                r"^const\s+.+\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]",
                r"^import\s*\(\s*['\"]([^'\"]+)['\"]",
            ]

            for pattern in patterns:
                match = re.match(pattern, s)
                if match:
                    module = match.group(1)
                    if not module.startswith(".") and not module.startswith("/"):
                        pkg = module.split("/")[0]
                        if pkg.startswith("@"):
                            parts = module.split("/")
                            if len(parts) >= 2:
                                pkg = f"{parts[0]}/{parts[1]}"
                        imports.add(pkg)
                    break

        return imports

    def _extract_java_imports(self, lines: List[str]) -> Set[str]:
        """提取 Java/Kotlin 导入"""
        imports = set()

        for line in lines:
            s = line.strip()
            if s.startswith("import "):
                match = re.match(r"^import\s+static\s+([a-zA-Z0-9_\.]+)", s)
                if not match:
                    match = re.match(r"^import\s+([a-zA-Z0-9_\.]+)", s)
                if match:
                    pkg = match.group(1)
                    parts = pkg.split(".")
                    if len(parts) >= 2:
                        imports.add(f"{parts[0]}.{parts[1]}")
                        imports.add(parts[-1])

        return imports

    def _extract_go_imports(self, lines: List[str]) -> Set[str]:
        """提取 Go 导入"""
        imports = set()
        in_import_block = False

        for line in lines:
            s = line.strip()
            if s == "import (":
                in_import_block = True
                continue
            elif s == ")" and in_import_block:
                in_import_block = False
                continue

            if in_import_block or s.startswith("import "):
                match = re.search(r'["\']([^"\']+)["\']', s)
                if match:
                    path = match.group(1)
                    parts = path.split("/")
                    if len(parts) >= 3:
                        imports.add(f"{parts[0]}/{parts[1]}/{parts[2]}")
                    imports.add(parts[-1])

        return imports

    def _build_call_graph(self) -> None:
        """构建调用图"""
        for filepath, lines in self._source_files.items():
            calls = set()

            if filepath.endswith(".py") and filepath in self._ast_cache:
                calls.update(self._extract_python_calls(filepath))
            else:
                calls.update(self._extract_generic_calls(lines))

            if calls:
                self._call_graph[filepath] = calls

    def _extract_python_calls(self, filepath: str) -> Set[str]:
        """提取 Python 函数调用"""
        calls = set()

        if filepath in self._ast_cache:
            tree = self._ast_cache[filepath]
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.add(node.func.attr)
                        if isinstance(node.func.value, ast.Name):
                            calls.add(f"{node.func.value.id}.{node.func.attr}")

        return calls

    def _extract_generic_calls(self, lines: List[str]) -> Set[str]:
        """通用调用提取（基于正则）"""
        calls = set()

        for line in lines:
            patterns = [
                r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                r'\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    calls.add(match.group(1))

        return calls

    def _analyze_vulnerability(self, vuln: Vulnerability) -> ReachabilityInfo:
        """分析单个漏洞的可达性"""
        dep = vuln.dependency
        evidence: List[str] = []
        import_sites: List[str] = []
        call_sites: List[str] = []
        confidence = 0.0

        pkg_names = self._get_package_name_variants(dep)

        is_imported = False
        is_called = False

        for filepath, imports in self._import_graph.items():
            for pkg_name in pkg_names:
                if pkg_name in imports:
                    is_imported = True
                    rel_path = os.path.relpath(filepath, self.project_path)
                    import_sites.append(rel_path)
                    evidence.append(f"Imported in {rel_path}")
                    break

        if is_imported:
            confidence = 0.4

            vulnerable_symbols = self._extract_vulnerable_symbols(vuln)

            if vulnerable_symbols:
                for filepath, calls in self._call_graph.items():
                    for symbol in vulnerable_symbols:
                        if symbol in calls:
                            is_called = True
                            rel_path = os.path.relpath(filepath, self.project_path)
                            call_sites.append(f"{rel_path}: {symbol}()")
                            evidence.append(f"Vulnerable symbol '{symbol}' called in {rel_path}")
                            confidence = max(confidence, 0.9)
                            break

            if not is_called:
                confidence = 0.6
                evidence.append("Package imported but vulnerable symbols not directly detected")

            if dep.is_transitive:
                if is_imported:
                    evidence.append("Transitive dependency imported directly")
                    confidence = max(confidence, 0.7)
                else:
                    confidence = max(confidence, 0.3)
                    evidence.append("Transitive dependency - may be reachable through parent")
        else:
            if dep.is_transitive:
                parent_chain = dep.dependency_chain
                if parent_chain:
                    parent_pkg = parent_chain[-2] if len(parent_chain) >= 2 else parent_chain[-1]
                    for filepath, imports in self._import_graph.items():
                        if parent_pkg in imports:
                            confidence = max(confidence, 0.3)
                            evidence.append(f"Parent dependency '{parent_pkg}' is imported")
                            break
                if confidence == 0:
                    confidence = 0.1
                    evidence.append("Transitive dependency - no direct or indirect import detected")
            else:
                confidence = 0.05
                evidence.append("Dependency not imported in source code")

        is_reachable = confidence >= 0.3

        if is_reachable and not import_sites:
            import_sites.append("Reachable through transitive dependency chain")

        return ReachabilityInfo(
            is_reachable=is_reachable,
            confidence=round(confidence, 2),
            evidence=evidence,
            call_sites=call_sites,
            import_sites=import_sites,
            analysis_method="static" if is_imported else "heuristic",
        )

    def _get_package_name_variants(self, dep: Dependency) -> List[str]:
        """获取包名的各种变体"""
        variants = [dep.name, dep.full_name]

        if dep.package_manager == PackageManager.PIP:
            variants.append(dep.name.replace("-", "_"))
            variants.append(dep.name.replace("_", "-"))
            variants.append(dep.name.replace("-", ""))
            variants.append(dep.name.replace("_", ""))

        elif dep.package_manager == PackageManager.NPM:
            if "/" in dep.name:
                variants.append(dep.name.split("/")[-1])

        elif dep.package_manager == PackageManager.MAVEN:
            if dep.group_id:
                variants.append(dep.group_id)
                variants.append(f"{dep.group_id}.{dep.name}")
                variants.append(dep.name)

        elif dep.package_manager == PackageManager.GO:
            parts = dep.name.split("/")
            if len(parts) >= 3:
                variants.append(f"{parts[0]}/{parts[1]}/{parts[2]}")
            variants.append(parts[-1])

        return list(set(v.lower() for v in variants if v))

    def _extract_vulnerable_symbols(self, vuln: Vulnerability) -> List[str]:
        """从漏洞信息中提取可能受影响的符号/函数名"""
        symbols: List[str] = []

        title = vuln.title.lower()
        desc = vuln.description.lower()
        text = f"{title} {desc}"

        function_patterns = [
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'method\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'`([a-zA-Z_][a-zA-Z0-9_]*)`',
            r"'([a-zA-Z_][a-zA-Z0-9_]*)'",
        ]

        for pattern in function_patterns:
            for match in re.finditer(pattern, text):
                symbols.append(match.group(1))

        cwe_keywords = {
            "CWE-89": ["execute", "query", "execSQL", "prepareStatement"],
            "CWE-78": ["exec", "system", "popen", "spawn"],
            "CWE-79": ["render", "innerHTML", "template"],
            "CWE-22": ["open", "readFile", "createReadStream"],
            "CWE-200": ["info", "dump", "debug", "trace"],
            "CWE-94": ["eval", "exec", "Function", "compile"],
            "CWE-400": ["parse", "load", "decode", "decompress"],
            "CWE-20": ["parse", "validate", "sanitize"],
        }

        for cwe_id in vuln.cwe_ids:
            if cwe_id in cwe_keywords:
                symbols.extend(cwe_keywords[cwe_id])

        vuln_keywords = {
            "sql": ["execute", "query", "sql", "select", "insert"],
            "xss": ["render", "escape", "sanitize", "html"],
            "rce": ["exec", "eval", "command", "shell"],
            "traversal": ["path", "file", "read", "open"],
            "injection": ["query", "exec", "command"],
            "dos": ["parse", "process", "handle", "loop"],
            "overflow": ["buffer", "copy", "string"],
            "csrf": ["token", "verify", "origin"],
        }

        for keyword, funcs in vuln_keywords.items():
            if keyword in text:
                symbols.extend(funcs)

        return list(set(symbols))

    def get_import_summary(self) -> Dict[str, Any]:
        """获取导入摘要"""
        all_imports = set()
        for imports in self._import_graph.values():
            all_imports.update(imports)

        return {
            "source_files_analyzed": len(self._source_files),
            "unique_imports": len(all_imports),
            "import_graph_size": len(self._import_graph),
            "call_graph_size": len(self._call_graph),
            "top_imports": sorted(all_imports)[:20],
        }
