"""XSS修复器"""

import re
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType
from .base_fixer import BaseFixer, FixAction, FixResult


class XSSFixer(BaseFixer):
    """XSS漏洞修复器"""

    vuln_type = VulnerabilityType.XSS
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
            if vuln.vuln_type != VulnerabilityType.XSS:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "mark_safe" in line or "Markup(" in line:
                fixed = line.replace("mark_safe(", "escape(")
                fixed = fixed.replace("Markup(", "escape(")
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "replace_mark_safe",
                            "将mark_safe/Markup替换为escape",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.7,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)

            elif "HttpResponse(" in line or "Response(" in line:
                fixed = self._fix_python_response(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "escape_response",
                            "对响应内容添加HTML转义",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.7,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)

            elif "render_template(" in line:
                fixed = self._fix_python_template(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "template_safe",
                            "确保模板变量使用安全上下文",
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

    def _fix_python_response(self, line: str) -> str:
        has_escape = "escape" in line or "bleach" in line or "sanitize" in line
        if not has_escape:
            if "HttpResponse(" in line:
                line = line.replace("HttpResponse(", "HttpResponse(escape(")
                line = re.sub(r'\)$', '))', line)
            elif "Response(" in line:
                line = line.replace("Response(", "Response(escape(")
                line = re.sub(r'\)$', '))', line)
        return line

    def _fix_python_template(self, line: str) -> str:
        return line

    def _fix_java(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.XSS:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "getWriter().write(" in line or "getWriter().print(" in line:
                fixed = self._fix_java_writer(line)
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "escape_java_output",
                            "对输出内容添加HTML转义",
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

    def _fix_java_writer(self, line: str) -> str:
        if "escapeHtml" not in line and "StringEscapeUtils" not in line:
            match = re.search(r'(getWriter\(\)\.(?:write|print))\((.*?)\)', line)
            if match:
                method = match.group(1)
                arg = match.group(2)
                line = line.replace(
                    f"{method}({arg})",
                    f"{method}(StringEscapeUtils.escapeHtml4({arg}))",
                )
        return line

    def _fix_javascript(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.XSS:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "innerHTML" in line or "outerHTML" in line:
                fixed = line.replace("innerHTML", "textContent")
                fixed = fixed.replace("outerHTML", "textContent")
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "use_textcontent",
                            "将innerHTML替换为textContent",
                            line.strip(),
                            fixed.strip(),
                            line_no,
                            confidence=0.8,
                        )
                    )
                    result.vulnerabilities_fixed.append(vuln)
                else:
                    result.vulnerabilities_skipped.append(vuln)

            elif "document.write" in line:
                fixed = line.replace("document.write(", "document.getElementById('content').textContent = ")
                if fixed != line:
                    actions.append(
                        self._create_fix_action(
                            "replace_doc_write",
                            "将document.write替换为安全DOM操作",
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
