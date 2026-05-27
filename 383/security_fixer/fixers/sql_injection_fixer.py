"""SQL注入修复器"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType
from .base_fixer import BaseFixer, FixAction, FixResult


class SQLInjectionFixer(BaseFixer):
    """SQL注入漏洞修复器"""

    vuln_type = VulnerabilityType.SQL_INJECTION
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
            if vuln.vuln_type != VulnerabilityType.SQL_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]
            indent = self._indent_of(line)

            if "execute(" in line or "executemany(" in line:
                fixed_line = self._fix_python_execute_call(line, indent)
                if fixed_line != line:
                    actions.append(
                        self._create_fix_action(
                            "parameterize",
                            "将字符串拼接SQL改为参数化查询",
                            line.strip(),
                            fixed_line.strip(),
                            line_no,
                            confidence=0.7,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)
            elif re.search(r'"(?:SELECT|INSERT|UPDATE|DELETE).*"', line, re.IGNORECASE):
                fixed_line = self._fix_python_string_concat(line, indent)
                if fixed_line != line:
                    actions.append(
                        self._create_fix_action(
                            "parameterize",
                            "将字符串拼接改为参数化查询",
                            line.strip(),
                            fixed_line.strip(),
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

    def _fix_python_execute_call(self, line: str, indent: str) -> str:
        pattern = re.compile(
            r'(\w+)\.(execute|executemany)\s*\(\s*(f?["\'])((?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)[^"\']*)\{(\w+)\}([^"\']*)(["\'])',
            re.IGNORECASE,
        )
        match = pattern.search(line)
        if match:
            var_name = match.group(5)
            return line.replace(
                f'{{{var_name}}}',
                f'%({var_name})s',
            )

        pattern2 = re.compile(
            r'(\w+)\.(execute|executemany)\s*\(\s*["\']((?:SELECT|INSERT|UPDATE|DELETE)[^"\']*)\s*["\']\s*\+\s*(\w+)',
            re.IGNORECASE,
        )
        match2 = pattern2.search(line)
        if match2:
            var_name = match2.group(3)
            old = f"' + {var_name}"
            new = f"', ({var_name},)"
            line = line.replace(old, new)
            line = line.replace(
                f'" + {var_name}',
                f'", ({var_name},)',
            )
            return line

        return line

    def _fix_python_string_concat(self, line: str, indent: str) -> str:
        if '+' in line and ('"' in line or "'" in line):
            parts = line.split('+')
            if len(parts) >= 2:
                fixed = re.sub(
                    r'(["\'])(.*?)\1\s*\+\s*(\w+)',
                    r'\1\2%s\1, (\3,)',
                    line,
                )
                return fixed
        return line

    def _fix_java(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.SQL_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "createStatement" in line:
                fixed = line.replace(
                    "createStatement()",
                    "prepareStatement(sql)",
                )
                actions.append(
                    self._create_fix_action(
                        "use_prepared_statement",
                        "将createStatement替换为prepareStatement",
                        line.strip(),
                        fixed.strip(),
                        line_no,
                        confidence=0.6,
                    )
                )
                result.vulnerabilities_fixed.append(vuln)
            elif "executeQuery" in line or "executeUpdate" in line and "+" in line:
                fixed = self._fix_java_execute_call(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "parameterize",
                            "将字符串拼接改为参数化查询",
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

    def _fix_java_execute_call(self, line: str) -> str:
        if "+" in line and ('"' in line or "'" in line):
            fixed = re.sub(
                r'(\w+\s*\.\s*execute\w*)\s*\(\s*"([^"]*)"\s*\+\s*(\w+)',
                r'PreparedStatement ps = conn.prepareStatement("\2?");\n    ps.setString(1, \3);\n    ps.execute()',
                line,
            )
            return fixed
        return line

    def _fix_javascript(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.SQL_INJECTION:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "query" in line and ("+" in line or "${" in line):
                fixed = self._fix_javascript_query(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "parameterize",
                            "将字符串拼接改为参数化查询",
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

    def _fix_javascript_query(self, line: str) -> str:
        line = line.replace("${", "?")
        line = line.replace("}", "")
        line = re.sub(
            r'(db\s*\.\s*query\s*\(\s*`)',
            r'db.query("',
            line,
        )
        line = line.replace("`", '"')
        return line
