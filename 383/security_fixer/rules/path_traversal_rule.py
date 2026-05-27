"""路径遍历检测规则"""

import re
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import (
    ASTNode,
    Language,
    Severity,
    SourceSpan,
    Vulnerability,
    VulnerabilityType,
)
from .rule_engine import BaseRule


PATH_TRAVERSAL_PATTERNS = [
    r'\.\.[\\/]',
    r'%2e%2e',
    r'%252e%252e',
    r'\.\.%[\\/]',
    r'\.\.%2f',
    r'\.\.%5c',
]

FILE_ACCESS_FUNCTIONS = {
    "python": [
        "open", "read", "read_file", "write", "write_file",
        "send_file", "get_file", "file_get_contents",
        "os.path.join", "pathlib.Path", "Path",
        "send_from_directory", "send_file",
        "download", "upload", "read_text", "write_text",
    ],
    "java": [
        "FileInputStream", "FileOutputStream", "FileReader", "FileWriter",
        "RandomAccessFile", "Files.read", "Files.write", "Files.newInputStream",
        "Files.newOutputStream", "Paths.get", "new File",
    ],
    "javascript": [
        "readFile", "readFileSync", "writeFile", "writeFileSync",
        "createReadStream", "createWriteStream",
        "readdir", "unlink", "rm", "stat", "exists",
        "resolve", "join",
        "sendFile", "download",
    ],
}


class PathTraversalRule(BaseRule):
    """检测路径遍历漏洞"""

    rule_name = "path_traversal"
    description = "检测用户输入直接用于文件路径访问的情况"
    vuln_type = VulnerabilityType.PATH_TRAVERSAL
    severity = Severity.HIGH
    supported_languages = [Language.PYTHON, Language.JAVA, Language.JAVASCRIPT]

    def detect(self, ast_root: ASTNode, source_code: str, file_path: str) -> List[Vulnerability]:
        vulnerabilities: List[Vulnerability] = []
        language = self._infer_language_from_path(file_path)

        self._detect_by_source_analysis(source_code, file_path, language, vulnerabilities)
        self._detect_ast_node(ast_root, source_code, file_path, language, vulnerabilities)

        return vulnerabilities

    def _detect_by_source_analysis(self, source_code, file_path, language, vulns):
        lines = source_code.splitlines()
        dangerous_funcs = FILE_ACCESS_FUNCTIONS.get(language, [])

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            line_contains_file_func = False
            for func in dangerous_funcs:
                if func in stripped:
                    line_contains_file_func = True
                    break

            if not line_contains_file_func:
                continue

            if self._has_user_input_in_path(stripped):
                has_path_validation = self._has_path_sanitization(stripped, language)

                if not has_path_validation:
                    span = SourceSpan(file_path, i, i)
                    fix = self._suggest_path_fix(stripped, language)
                    vulns.append(
                        self._create_vulnerability(
                            f"路径遍历风险: 用户输入直接用于文件访问，未进行路径验证",
                            span,
                            {"line": stripped[:200]},
                            fix,
                            confidence=0.85,
                        )
                    )

            for pattern in PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, stripped, re.IGNORECASE):
                    span = SourceSpan(file_path, i, i)
                    fix = (
                        "检测到路径遍历尝试，需要进行路径规范化:\n"
                        "  使用 os.path.realpath() 或 Path.resolve() 解析真实路径\n"
                        "  验证路径是否在允许的目录范围内"
                    )
                    vulns.append(
                        self._create_vulnerability(
                            "路径遍历风险: 检测到路径遍历字符序列",
                            span,
                            {"line": stripped[:200]},
                            fix,
                            confidence=0.9,
                        )
                    )

    def _detect_ast_node(self, ast_root, source_code, file_path, language, vulns):
        call_nodes = self._find_all_call_nodes(ast_root)
        dangerous_funcs = FILE_ACCESS_FUNCTIONS.get(language, [])

        for call_node in call_nodes:
            func_name = call_node.attributes.get("function_name", "")
            module_name = call_node.attributes.get("module_name", "")

            full_name = f"{module_name}.{func_name}" if module_name else func_name

            matched = False
            for func in dangerous_funcs:
                if func.lower() in full_name.lower():
                    matched = True
                    break

            if not matched:
                continue

            raw_text = call_node.raw_text
            if self._has_user_input_in_path(raw_text):
                if not self._has_path_sanitization(raw_text, language):
                    span = call_node.source_span
                    fix = self._suggest_path_fix(raw_text, language)
                    vulns.append(
                        self._create_vulnerability(
                            f"路径遍历风险: {full_name} 调用中使用了未验证的用户输入路径",
                            span,
                            {"function": full_name},
                            fix,
                            confidence=0.9,
                        )
                    )

    def _has_user_input_in_path(self, line: str) -> bool:
        patterns = [
            r'request\.(args|form|files|get_full_path|path)',
            r'GET\[|POST\[',
            r'params\.',
            r'query\.',
            r'getParameter\b',
            r'getAttribute\b',
            r'req\.(query|params|body)',
            r'http\.IncomingMessage',
            r'ctx\.request',
            r'\$\{.*path',
            r'\$\{.*file',
            r'\$\{.*filename',
            r'user_input',
            r'filename',
            r'filepath',
            r'file_path',
            r'\$\{',
        ]
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _has_path_sanitization(self, line: str, language: str) -> bool:
        patterns = {
            "python": [
                r'os\.path\.realpath',
                r'os\.path\.abspath',
                r'os\.path\.normpath',
                r'\.resolve\(\)',
                r'werkzeug\.utils\.secure_filename',
                r'secure_filename',
                r'safe_join',
                r'validate_file_path',
                r'allowed_paths',
                r'allowed_dir',
                r'whitelist',
                r'ALLOWED',
            ],
            "java": [
                r'normalize\(\)',
                r'resolve\(\)',
                r'getCanonicalPath',
                r'getAbsolutePath',
                r'Paths\.get\(.*\.normalize',
                r'SecurityManager',
                r'FileSystems\.getDefault\(\)\.getPathMatcher',
            ],
            "javascript": [
                r'path\.resolve\(',
                r'path\.normalize\(',
                r'path\.isAbsolute\(',
                r'validate',
                r'sanitize',
                r'safeFile',
            ],
        }
        lang_patterns = patterns.get(language, [])
        for pattern in lang_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _suggest_path_fix(self, line: str, language: str) -> str:
        if language == "python":
            return (
                "对文件路径进行严格验证:\n"
                "  from werkzeug.utils import secure_filename\n"
                "  filename = secure_filename(user_input)\n"
                "  safe_path = os.path.realpath(os.path.join(BASE_DIR, filename))\n"
                "  if not safe_path.startswith(BASE_DIR):\n"
                "      raise ValueError('Invalid path')"
            )
        elif language == "java":
            return (
                "对文件路径进行验证和规范化:\n"
                "  Path basePath = Paths.get(BASE_DIR).toAbsolutePath().normalize();\n"
                "  Path resolvedPath = basePath.resolve(userInput).normalize();\n"
                "  if (!resolvedPath.startsWith(basePath)) {\n"
                "      throw new SecurityException('Invalid path');\n"
                "  }"
            )
        else:
            return (
                "对文件路径进行验证:\n"
                "  const path = require('path');\n"
                "  const safePath = path.resolve(BASE_DIR, userInput);\n"
                "  if (!safePath.startsWith(BASE_DIR)) {\n"
                "      throw new Error('Invalid path');\n"
                "  }"
            )

    def _find_all_call_nodes(self, node: ASTNode) -> List[ASTNode]:
        results: List[ASTNode] = []
        if node.node_type in ("Call", "MethodInvocation", "CallExpression"):
            results.append(node)
        for child in node.children:
            results.extend(self._find_all_call_nodes(child))
        return results

    def _infer_language_from_path(self, file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        ext_map = {"py": "python", "java": "java", "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript"}
        return ext_map.get(ext.lower(), "python")
