"""命令注入检测规则"""

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


COMMAND_EXECUTION_FUNCTIONS = {
    "python": [
        "os.system", "os.popen", "subprocess.call", "subprocess.run",
        "subprocess.Popen", "subprocess.check_output", "subprocess.check_call",
        "subprocess.getoutput", "subprocess.getstatusoutput",
        "commands.getoutput", "commands.getstatusoutput",
        "os.exec", "os.execl", "os.execle", "os.execlp", "os.execlpe",
        "os.execv", "os.execve", "os.execvp", "os.execvpe",
        "eval", "exec",
        "popen2", "popen3", "popen4",
    ],
    "java": [
        "Runtime.getRuntime().exec", "Runtime.exec",
        "ProcessBuilder", "ProcessBuilder.start",
        "ScriptEngineManager", "ScriptEngine.eval",
        "GroovyShell", "GroovyShell.evaluate",
        "javax.script",
    ],
    "javascript": [
        "exec", "execSync", "execFile", "execFileSync",
        "spawn", "spawnSync", "fork",
        "eval", "Function(",
        "child_process",
    ],
}

SHELL_METACHARACTERS = re.compile(
    r'[;&|`$><\n\r\t]|\$\(|\$\{|`.*?`'
)


class CommandInjectionRule(BaseRule):
    """检测命令注入漏洞"""

    rule_name = "command_injection"
    description = "检测用户输入直接用于系统命令执行的情况"
    vuln_type = VulnerabilityType.COMMAND_INJECTION
    severity = Severity.CRITICAL
    supported_languages = [Language.PYTHON, Language.JAVA, Language.JAVASCRIPT]

    def detect(self, ast_root: ASTNode, source_code: str, file_path: str) -> List[Vulnerability]:
        vulnerabilities: List[Vulnerability] = []
        language = self._infer_language_from_path(file_path)

        self._detect_by_source_analysis(source_code, file_path, language, vulnerabilities)
        self._detect_ast_nodes(ast_root, source_code, file_path, language, vulnerabilities)

        return vulnerabilities

    def _detect_by_source_analysis(self, source_code, file_path, language, vulns):
        lines = source_code.splitlines()
        dangerous_funcs = COMMAND_EXECUTION_FUNCTIONS.get(language, [])

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            for func in dangerous_funcs:
                if func in stripped:
                    if self._has_user_input(stripped):
                        has_shell_safe = self._has_shell_safety(stripped, language)

                        if not has_shell_safe:
                            span = SourceSpan(file_path, i, i)
                            fix = self._suggest_command_fix(stripped, language)
                            vulns.append(
                                self._create_vulnerability(
                                    f"命令注入风险: {func} 调用中使用了用户输入且未进行安全处理",
                                    span,
                                    {"line": stripped[:200], "function": func},
                                    fix,
                                    confidence=0.9,
                                )
                            )
                    break

    def _detect_ast_nodes(self, ast_root, source_code, file_path, language, vulns):
        call_nodes = self._find_all_call_nodes(ast_root)
        dangerous_funcs = COMMAND_EXECUTION_FUNCTIONS.get(language, [])

        for call_node in call_nodes:
            func_name = call_node.attributes.get("function_name", "")
            module_name = call_node.attributes.get("module_name", "")

            full_name = f"{module_name}.{func_name}" if module_name else func_name

            matched = False
            for func in dangerous_funcs:
                if func.lower() in full_name.lower() or func.lower() == func_name.lower():
                    matched = True
                    break

            if not matched:
                continue

            raw_text = call_node.raw_text
            if self._has_user_input(raw_text):
                if not self._has_shell_safety(raw_text, language):
                    span = call_node.source_span
                    fix = self._suggest_command_fix(raw_text, language)
                    vulns.append(
                        self._create_vulnerability(
                            f"命令注入风险: {full_name} 调用中使用了未净化的用户输入",
                            span,
                            {"function": full_name},
                            fix,
                            confidence=0.9,
                        )
                    )

    def _has_user_input(self, line: str) -> bool:
        patterns = [
            r'request\.(args|form|values|get_full_path)',
            r'GET\[|POST\[',
            r'params\.',
            r'query\.',
            r'getParameter\b',
            r'getAttribute\b',
            r'req\.(query|params|body)',
            r'\$\{',
            r'user_input',
            r'input',
            r'data\.',
            r'argv',
            r'sys\.argv',
            r'process\.env',
            r'ctx\.request',
        ]
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _has_shell_safety(self, line: str, language: str) -> bool:
        patterns = {
            "python": [
                r'shell\s*=\s*False',
                r'shlex\.quote',
                r'shlex\.split',
                r'subprocess\.(run|call|Popen)\([^)]*shell\s*=\s*False',
                r'input\s*=.*validate',
                r'ALLOWED_COMMANDS',
                r'whitelist',
                r'allowed\s*=',
            ],
            "java": [
                r'ProcessBuilder\s*\([^)]*String\.class',
                r'ProcessBuilder\s*\(\s*new\s+String',
                r'String\[\]|List<',
                r'SecurityManager',
                r'ALLOWED_COMMANDS',
                r'allowed\s*=',
                r'whitelist',
            ],
            "javascript": [
                r'execFile\(',
                r'execFileSync\(',
                r'shell\s*:\s*false',
                r'validate|sanitize',
                r'ALLOWED_COMMANDS',
                r'allowed\s*=',
            ],
        }
        lang_patterns = patterns.get(language, [])
        for pattern in lang_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _suggest_command_fix(self, line: str, language: str) -> str:
        if language == "python":
            return (
                "使用安全的方式执行命令:\n"
                "  1. 避免使用shell=True\n"
                "  2. 使用参数列表而非字符串: subprocess.run(['ls', '-la'])\n"
                "  3. 对用户输入使用白名单验证:\n"
                "     ALLOWED_COMMANDS = {'ls', 'cat', 'grep'}\n"
                "     if user_input not in ALLOWED_COMMANDS:\n"
                "         raise ValueError('Invalid command')\n"
                "  4. 使用shlex.quote()转义: import shlex; cmd = shlex.quote(user_input)"
            )
        elif language == "java":
            return (
                "使用ProcessBuilder并传递参数数组而非字符串:\n"
                "  ProcessBuilder pb = new ProcessBuilder('ls', '-la');\n"
                "  pb.redirectErrorStream(true);\n"
                "  Process process = pb.start();\n"
                "  不要使用Runtime.exec(String)形式，始终使用数组形式\n"
                "  对白名单进行验证后再执行命令"
            )
        else:
            return (
                "使用execFile或spawn替代exec:\n"
                "  const { execFile } = require('child_process');\n"
                "  execFile('ls', ['-la'], (err, stdout, stderr) => {});\n"
                "  对用户输入使用白名单验证:\n"
                "  const ALLOWED_COMMANDS = new Set(['ls', 'cat', 'grep']);\n"
                "  if (!ALLOWED_COMMANDS.has(userInput)) throw new Error('Invalid command');"
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
