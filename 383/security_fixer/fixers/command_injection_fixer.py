"""命令注入修复器"""

import re
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType
from .base_fixer import BaseFixer, FixAction, FixResult


class CommandInjectionFixer(BaseFixer):
    """命令注入漏洞修复器"""

    vuln_type = VulnerabilityType.COMMAND_INJECTION
    supported_languages = [Language.PYTHON, Language.JAVA, Language.JAVASCRIPT]

    def fix(
        self,
        source_code: str,
        vulnerabilities: List[Vulnerability],
        language: Language,
    ) -> FixResult:
        result = FixResult(
            file_path="",
            language=language,
            original_source=source_code,
            fixed_source=source_code,
        )

        if language == Language.PYTHON:
            self._fix_python(source_code, vulnerabilities, result)
        elif language == Language.JAVA:
            self._fix_java(source_code, vulnerabilities, result)
        elif language == Language.JAVASCRIPT:
            self._fix_javascript(source_code, vulnerabilities, result)

        return result

    def _fix_python(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.COMMAND_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "shell=True" in line or "os.system(" in line:
                fixed = self._fix_python_command(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "use_subprocess_array",
                            "使用参数列表形式执行命令",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.6,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)
            elif "subprocess.call" in line or "subprocess.run" in line or "subprocess.Popen" in line:
                if 'shell=True' not in line and 'shell = True' not in line:
                    result.vulnerabilities_skipped.append(vuln)
                else:
                    fixed = self._fix_python_subprocess(line)
                    if fixed != line:
                        actions.append(
                            self._create_fix_action(
                                "remove_shell_true",
                                "移除shell=True并使用参数列表",
                                line.strip(),
                                fixed.strip(),
                                line_no,
                                confidence=0.7,
                            )
                        )
                        result.vulnerabilities_fixed.append(vuln)
                    else:
                        result.vulnerabilities_skipped.append(vuln)
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions

    def _fix_python_command(self, line: str) -> str:
        if "os.system(" in line:
            line = re.sub(
                r'os\.system\(\s*(f?["\'])',
                r'subprocess.run([\1',
                line,
            )
            line = re.sub(
                r'["\']\s*\)$',
                r'"], shell=False)',
                line,
            )
        if "shell=True" in line:
            line = line.replace("shell=True", "shell=False")
        if "shell = True" in line:
            line = line.replace("shell = True", "shell = False")
        return line

    def _fix_python_subprocess(self, line: str) -> str:
        if "shell=True" in line:
            line = line.replace("shell=True", "shell=False")
        if "shell = True" in line:
            line = line.replace("shell = True", "shell = False")
        return line

    def _fix_java(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.COMMAND_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "Runtime.getRuntime().exec" in line and "String[]" not in line:
                fixed = line.replace(
                    "Runtime.getRuntime().exec(",
                    "new ProcessBuilder(new String[]{",
                )
                fixed = fixed.replace(
                    ")",
                    "}).start()",
                )
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "use_process_builder",
                            "使用ProcessBuilder替代Runtime.exec",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.6,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions

    def _fix_javascript(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.COMMAND_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "exec(" in line or "execSync(" in line:
                fixed = line.replace("exec(", "execFile(")
                fixed = fixed.replace("execSync(", "execFileSync(")
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "use_execfile",
                            "使用execFile替代exec",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.7,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions
