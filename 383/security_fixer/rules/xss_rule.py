"""XSS(跨站脚本)检测规则"""

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


HTML_TAGS_PATTERN = re.compile(
    r'<\s*(script|iframe|object|embed|form|input|textarea|button|a|img|svg|body|html|head|style|link|meta|div|span|p|h[1-6]|table|tr|td|th|ul|ol|li|nav|header|footer|section|article|aside)\b',
    re.IGNORECASE,
)

EVENT_HANDLERS = re.compile(
    r'\bon\w+\s*=',
    re.IGNORECASE,
)

DANGEROUS_OUTPUT_FUNCTIONS = {
    "python": ["print", "write", "response.write", "render", "render_template", "jsonify", "Response", "HttpResponse"],
    "java": ["println", "write", "out.print", "out.println", "getWriter", "sendRedirect", "forward", "include"],
    "javascript": ["innerHTML", "outerHTML", "document.write", "document.writeln", "html", "append", "prepend", "after", "before"],
}

TEMPLATE_DIRS = {
    "python": ["render_template", "render", "TemplateResponse", "render_to_response"],
    "java": ["jsp", "thymeleaf", "freemarker", "velocity"],
    "javascript": ["ejs", "pug", "handlebars", "mustache", "nunjucks", "jade"],
}


INPUT_SANITIZATION_LIBS = {
    "python": [
        "bleach", "sanitize", "strip_tags", "html.escape", "cgi.escape",
        "markupsafe.escape", "django.utils.html.escape", "html_sanitizer",
        "lxml.html.clean", "nh3", "readability",
    ],
    "java": [
        "StringEscapeUtils.escapeHtml", "HtmlUtils.htmlEscape",
        "jsoup.clean", "antisamy", "owasp-esapi", "sanitize",
        "Jsoup.clean", "HtmlSanitizer",
    ],
    "javascript": [
        "DOMPurify", "sanitize-html", "xss", "html-purify",
        "escape-html", "he.encode", "sanitizer", "purify",
    ],
}


XSS_DANGEROUS_PATTERNS = [
    r'<\s*script[^>]*>',
    r'javascript\s*:',
    r'vbscript\s*:',
    r'on\w+\s*=',
    r'<\s*iframe[^>]*>',
    r'<\s*object[^>]*>',
    r'<\s*embed[^>]*>',
    r'<\s*form[^>]*>',
    r'\beval\s*\(',
    r'\bexpression\s*\(',
    r'<!--.*-->',
]


class XSSRule(BaseRule):
    """检测跨站脚本(XSS)漏洞 - 支持输出转义+输入过滤双重防护检测"""

    rule_name = "xss"
    description = "检测未经验证的用户输入直接输出到HTML响应的情况"
    vuln_type = VulnerabilityType.XSS
    severity = Severity.HIGH
    supported_languages = [Language.PYTHON, Language.JAVA, Language.JAVASCRIPT]

    def detect(self, ast_root: ASTNode, source_code: str, file_path: str) -> List[Vulnerability]:
        vulnerabilities: List[Vulnerability] = []
        language = self._infer_language_from_path(file_path)

        self._detect_input_sanitization_usage(source_code, file_path, language, vulnerabilities)

        if language == "javascript":
            self._detect_javascript_xss(ast_root, source_code, file_path, vulnerabilities)
        elif language == "python":
            self._detect_python_xss(ast_root, source_code, file_path, vulnerabilities)
        elif language == "java":
            self._detect_java_xss(ast_root, source_code, file_path, vulnerabilities)

        return vulnerabilities

    def _detect_input_sanitization_usage(self, source_code, file_path, language, vulns):
        """检测是否使用了输入过滤库"""
        import_lines = []
        usage_lines = []

        sanitization_libs = INPUT_SANITIZATION_LIBS.get(language, [])

        for i, line in enumerate(source_code.splitlines(), 1):
            for lib in sanitization_libs:
                if lib in line:
                    if any(kw in line.lower() for kw in ["import", "from", "require", "include"]):
                        import_lines.append((i, line.strip(), lib))
                    else:
                        usage_lines.append((i, line.strip(), lib))

        if not import_lines and not usage_lines:
            span = SourceSpan(file_path, 1, 1)
            vulns.append(
                self._create_vulnerability(
                    "XSS防护建议: 建议使用输入过滤库作为第一道防线",
                    span,
                    {
                        "language": language,
                        "recommended_libs": sanitization_libs[:5],
                    },
                    self._suggest_input_sanitization(language),
                    confidence=0.5,
                    auto_fixable=False,
                )
            )

    def _detect_javascript_xss(self, ast_root, source_code, file_path, vulns):
        lines = source_code.splitlines()
        dangerous_funcs = DANGEROUS_OUTPUT_FUNCTIONS["javascript"]

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            for func in dangerous_funcs:
                if func in stripped.lower():
                    if self._contains_user_input(stripped):
                        has_escape = self._has_output_escape(stripped, "javascript")
                        has_sanitization = self._has_input_sanitization(stripped, "javascript")

                        if "innerHTML" in stripped or "outerHTML" in stripped or "document.write" in stripped:
                            span = SourceSpan(file_path, i, i)
                            fix = self._suggest_xss_fix(has_escape, has_sanitization, "javascript")

                            if not has_escape and not has_sanitization:
                                severity = Severity.CRITICAL
                                msg = f"XSS严重风险: 使用{func}直接输出用户输入，无转义也无输入过滤"
                            elif not has_escape:
                                severity = Severity.HIGH
                                msg = f"XSS高风险: 使用{func}直接输出用户输入，缺少输出转义"
                            elif not has_sanitization:
                                severity = Severity.MEDIUM
                                msg = f"XSS警告: 使用{func}输出，有转义但建议增加输入过滤"
                            else:
                                continue

                            vulns.append(
                                self._create_vulnerability(
                                    msg,
                                    span,
                                    {
                                        "line": stripped[:200],
                                        "has_output_escape": has_escape,
                                        "has_input_sanitization": has_sanitization,
                                    },
                                    fix,
                                    confidence=0.9,
                                )
                            )

    def _detect_python_xss(self, ast_root, source_code, file_path, vulns):
        lines = source_code.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if re.search(r'render_template|render\(', stripped, re.IGNORECASE):
                if not re.search(r'escape|markupsafe|safe', stripped, re.IGNORECASE):
                    if re.search(r'request\.args|request\.form|request\.json|request\.values', stripped):
                        has_sanitization = self._has_input_sanitization(stripped, "python")
                        span = SourceSpan(file_path, i, i)
                        fix = self._suggest_xss_fix(False, has_sanitization, "python")

                        if not has_sanitization:
                            msg = "XSS风险: 未转义的用户输入渲染到模板，建议同时增加输入过滤"
                        else:
                            msg = "XSS警告: 未转义的用户输入渲染到模板"

                        vulns.append(
                            self._create_vulnerability(
                                msg,
                                span,
                                {"line": stripped[:200], "has_input_sanitization": has_sanitization},
                                fix,
                                confidence=0.8,
                            )
                        )

            if re.search(r'HttpResponse|Response\s*\(', stripped):
                if re.search(r'request\.|GET\[|POST\[|params\[|input', stripped, re.IGNORECASE):
                    has_escape = self._has_output_escape(stripped, "python")
                    has_sanitization = self._has_input_sanitization(stripped, "python")

                    if not has_escape:
                        span = SourceSpan(file_path, i, i)
                        fix = self._suggest_xss_fix(has_escape, has_sanitization, "python")

                        if not has_sanitization:
                            severity = Severity.HIGH
                            msg = "XSS高风险: 直接将用户输入放入响应内容，无转义也无输入过滤"
                        else:
                            severity = Severity.MEDIUM
                            msg = "XSS风险: 直接将用户输入放入响应内容，缺少输出转义"

                        vulns.append(
                            self._create_vulnerability(
                                msg,
                                span,
                                {
                                    "line": stripped[:200],
                                    "has_output_escape": has_escape,
                                    "has_input_sanitization": has_sanitization,
                                },
                                fix,
                                confidence=0.85,
                            )
                        )

            if re.search(r'mark_safe|Markup\(', stripped, re.IGNORECASE):
                if re.search(r'request\.|GET\[|POST\[|input', stripped, re.IGNORECASE):
                    has_sanitization = self._has_input_sanitization(stripped, "python")
                    span = SourceSpan(file_path, i, i)
                    fix = self._suggest_xss_fix(False, has_sanitization, "python")

                    if not has_sanitization:
                        severity = Severity.CRITICAL
                        msg = "XSS严重风险: 对用户输入使用mark_safe且无输入过滤"
                    else:
                        severity = Severity.HIGH
                        msg = "XSS高风险: 对用户输入使用mark_safe，即使有输入过滤也需谨慎"

                    vulns.append(
                        self._create_vulnerability(
                            msg,
                            span,
                            {
                                "line": stripped[:200],
                                "has_input_sanitization": has_sanitization,
                            },
                            fix,
                            confidence=0.95,
                        )
                    )

    def _detect_java_xss(self, ast_root, source_code, file_path, vulns):
        lines = source_code.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if re.search(r'getWriter\(\)\.write|getWriter\(\)\.print|out\.print|out\.write', stripped):
                if re.search(r'getParameter|getAttribute|request\.get', stripped):
                    has_escape = self._has_output_escape(stripped, "java")
                    has_sanitization = self._has_input_sanitization(stripped, "java")
                    span = SourceSpan(file_path, i, i)
                    fix = self._suggest_xss_fix(has_escape, has_sanitization, "java")

                    if not has_escape and not has_sanitization:
                        severity = Severity.CRITICAL
                        msg = "XSS严重风险: 未转义的用户输入直接输出，也无输入过滤"
                    elif not has_escape:
                        severity = Severity.HIGH
                        msg = "XSS高风险: 未转义的用户输入直接输出到HTTP响应"
                    elif not has_sanitization:
                        severity = Severity.MEDIUM
                        msg = "XSS警告: 有转义但建议增加输入过滤作为双重防护"
                    else:
                        continue

                    vulns.append(
                        self._create_vulnerability(
                            msg,
                            span,
                            {
                                "line": stripped[:200],
                                "has_output_escape": has_escape,
                                "has_input_sanitization": has_sanitization,
                            },
                            fix,
                            confidence=0.9,
                        )
                    )

            if re.search(r'JspWriter|PageContext|getOut\(\)', stripped):
                if re.search(r'getParameter|getAttribute', stripped):
                    has_escape = self._has_output_escape(stripped, "java")
                    has_sanitization = self._has_input_sanitization(stripped, "java")
                    span = SourceSpan(file_path, i, i)
                    fix = self._suggest_xss_fix(has_escape, has_sanitization, "java")

                    if not has_escape and not has_sanitization:
                        severity = Severity.HIGH
                        msg = "XSS高风险: JSP中直接输出用户输入，无转义无过滤"
                    else:
                        severity = Severity.MEDIUM
                        msg = "XSS警告: JSP中输出用户输入，建议使用JSTL自动转义"

                    vulns.append(
                        self._create_vulnerability(
                            msg,
                            span,
                            {
                                "line": stripped[:200],
                                "has_output_escape": has_escape,
                                "has_input_sanitization": has_sanitization,
                            },
                            fix,
                            confidence=0.85,
                        )
                    )

    def _has_output_escape(self, line: str, language: str) -> bool:
        """检查是否有输出转义"""
        escape_patterns = {
            "python": [
                r'escape\s*\(', r'|e\s*\}\}', r'markupsafe', r'bleach\.clean',
                r'html\.escape', r'cgi\.escape', r'strip_tags',
            ],
            "java": [
                r'escapeHtml', r'htmlEscape', r'Jsoup\.clean',
                r'StringEscapeUtils', r'<c:out', r'fn:escapeXml',
            ],
            "javascript": [
                r'textContent', r'DOMPurify', r'sanitize',
                r'escape.*html', r'he\.encode',
            ],
        }

        patterns = escape_patterns.get(language, [])
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _has_input_sanitization(self, line: str, language: str) -> bool:
        """检查是否有输入过滤/清理"""
        sanitization_libs = INPUT_SANITIZATION_LIBS.get(language, [])
        for lib in sanitization_libs:
            if re.search(r'\b' + re.escape(lib) + r'\b', line, re.IGNORECASE):
                return True
        return False

    def _contains_user_input(self, line: str) -> bool:
        patterns = [
            r'request\.\w+',
            r'getParameter',
            r'getAttribute',
            r'GET\[', r'POST\[',
            r'params\.',
            r'query\.',
            r'body\.',
            r'\$\{.*\}',
            r'userInput',
            r'user_input',
            r'input',
            r'data\.',
            r'value\.',
        ]
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def _infer_language_from_path(self, file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        ext_map = {"py": "python", "java": "java", "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript"}
        return ext_map.get(ext.lower(), "python")

    def _suggest_xss_fix(self, has_escape: bool, has_sanitization: bool, language: str) -> str:
        """根据防护情况建议修复方案"""
        suggestions = []

        if not has_sanitization:
            suggestions.append(self._suggest_input_sanitization(language))
        if not has_escape:
            suggestions.append(self._suggest_output_escape(language))

        if has_escape and has_sanitization:
            return "✅ 已实现双重防护（输入过滤+输出转义），安全措施到位。"

        return "\n\n".join(suggestions)

    def _suggest_input_sanitization(self, language: str) -> str:
        """建议输入过滤方案"""
        if language == "python":
            return (
                "🛡️  输入过滤（第一道防线）:\n"
                "  使用 bleach 或 nh3 清理HTML输入:\n"
                "    import bleach\n"
                "    clean_html = bleach.clean(user_input, tags=['p', 'b', 'i'], attributes={})\n"
                "  或使用 html.parser 完全移除HTML:\n"
                "    from html.parser import HTMLParser\n"
                "    class TextExtractor(HTMLParser): ..."
            )
        elif language == "java":
            return (
                "🛡️  输入过滤（第一道防线）:\n"
                "  使用 Jsoup 清理HTML:\n"
                "    import org.jsoup.Jsoup;\n"
                "    import org.jsoup.safety.Safelist;\n"
                "    String safeHtml = Jsoup.clean(userInput, Safelist.none());\n"
                "  或使用 OWASP ESAPI:\n"
                "    String safe = ESAPI.encoder().encodeForHTML(userInput);"
            )
        else:
            return (
                "🛡️  输入过滤（第一道防线）:\n"
                "  使用 DOMPurify 清理HTML:\n"
                "    import DOMPurify from 'dompurify';\n"
                "    const cleanHtml = DOMPurify.sanitize(userInput);\n"
                "  或使用 sanitize-html:\n"
                "    const sanitizeHtml = require('sanitize-html');\n"
                "    const clean = sanitizeHtml(dirty, { allowedTags: [] });"
            )

    def _suggest_output_escape(self, language: str) -> str:
        """建议输出转义方案"""
        if language == "python":
            return (
                "🔒 输出转义（第二道防线）:\n"
                "  对输出内容进行HTML转义:\n"
                "    from django.utils.html import escape\n"
                "    return HttpResponse(escape(user_input))\n"
                "  或在模板中使用自动转义:\n"
                "    {{ user_input|e }}  {# Jinja2自动转义 #}"
            )
        elif language == "java":
            return (
                "🔒 输出转义（第二道防线）:\n"
                "  使用 StringEscapeUtils:\n"
                "    import org.apache.commons.text.StringEscapeUtils;\n"
                "    out.print(StringEscapeUtils.escapeHtml4(userInput));\n"
                "  或在JSP中使用JSTL:\n"
                "    <c:out value='${userInput}' />"
            )
        else:
            return (
                "🔒 输出转义（第二道防线）:\n"
                "  使用 textContent 替代 innerHTML:\n"
                "    element.textContent = userInput;  // 自动转义\n"
                "  或使用 createTextNode:\n"
                "    element.appendChild(document.createTextNode(userInput));"
            )
