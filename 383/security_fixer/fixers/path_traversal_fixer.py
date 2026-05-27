"""路径遍历修复器"""

import re
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType
from .base_fixer import BaseFixer, FixAction, FixResult


class PathTraversalFixer(BaseFixer):
    """路径遍历漏洞修复器"""

    vuln_type = VulnerabilityType.PATH_TRAVERSAL
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
            if vuln.vuln_type != VulnerabilityType.PATH_TRAVERSAL:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if "open(" in line or "send_file(" in line or "send_from_directory(" in line:
                if "os.path.realpath" not in line and "secure_filename" not in line:
                    fixed = self._fix_python_path(line)
                    if fixed != line:
                        actions.append(
                            self._create_fix_action(
                                "add_path_validation",
                                "添加路径验证和规范化",
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
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions

    def _fix_python_path(self, line: str) -> str:
        if "open(" in line:
            line = re.sub(
                r'open\(\s*([^,)]+)',
                r'open(os.path.realpath(os.path.join(BASE_DIR, \1))',
                line,
            )
        if "send_file(" in line:
            line = re.sub(
                r'send_file\(\s*([^,)]+)',
                r'send_file(os.path.realpath(os.path.join(app.config["UPLOAD_FOLDER"], \1))',
                line,
            )
        return line

    def _fix_java(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.PATH_TRAVERSAL:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if ("new File(" in line or "FileInputStream" in line or "FileReader" in line
                    or "Paths.get(" in line):
                if "normalize" not in line and "getCanonicalPath" not in line:
                    fixed = self._fix_java_path(line)
                    if fixed != line:
                        actions.append(
                            self._create_fix_action(
                                "add_path_normalization",
                                "添加路径规范化和验证",
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
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions

    def _fix_java_path(self, line: str) -> str:
        if "new File(" in line:
            line = re.sub(
                r'new File\(\s*([^)]+)\)',
                r'new File(BASE_DIR.toPath().resolve(\1).normalize().toFile())',
                line,
            )
        if "Paths.get(" in line:
            line = re.sub(
                r'Paths\.get\(\s*([^)]+)\)',
                r'BASE_DIR.toPath().resolve(\1).normalize()',
                line,
            )
        return line

    def _fix_javascript(self, source_code, vulnerabilities, result):
        actions: List[FixAction] = []
        lines = source_code.splitlines()

        for vuln in vulnerabilities:
            if vuln.vuln_type != VulnerabilityType.PATH_TRAVERSAL:
                continue
            line_no = vuln.source_span.start_line
            if line_no <= 0 or line_no > len(lines):
                result.vulnerabilities_skipped.append(vuln)
                continue

            line = lines[line_no - 1]

            if ("readFile" in line or "writeFile" in line or "createReadStream" in line
                    or "sendFile" in line):
                if "path.resolve" not in line and "path.normalize" not in line:
                    fixed = self._fix_javascript_path(line)
                    if fixed != line:
                        actions.append(
                            self._create_fix_action(
                                "add_path_validation",
                                "添加路径验证",
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
            else:
                result.vulnerabilities_skipped.append(vuln)

        if actions:
            result.fixed_source = self._apply_line_replacements(source_code, actions)
        result.actions = actions

    def _fix_javascript_path(self, line: str) -> str:
        if "fs.readFile" in line or "fs.readFileSync" in line:
            line = re.sub(
                r'fs\.read(File|FileSync)\(\s*([^,)]+)',
                r'fs.read\1(path.resolve(BASE_DIR, \2)',
                line,
            )
        if "sendFile" in line:
            line = re.sub(
                r'sendFile\(\s*([^,)]+)',
                r'sendFile(path.resolve(BASE_DIR, \1)',
                line,
            )
        return line
