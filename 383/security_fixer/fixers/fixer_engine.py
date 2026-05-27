"""修复引擎 - 管理所有修复器并协调修复流程"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType
from ..rules.rule_engine import ScanResult
from .base_fixer import BaseFixer, FixResult
from .sql_injection_fixer import SQLInjectionFixer
from .xss_fixer import XSSFixer
from .path_traversal_fixer import PathTraversalFixer
from .command_injection_fixer import CommandInjectionFixer


class FixerEngine:
    """修复引擎，根据扫描结果执行修复"""

    def __init__(self):
        self._fixers: Dict[VulnerabilityType, BaseFixer] = {}
        self._register_default_fixers()

    def _register_default_fixers(self):
        self._fixers[VulnerabilityType.SQL_INJECTION] = SQLInjectionFixer()
        self._fixers[VulnerabilityType.XSS] = XSSFixer()
        self._fixers[VulnerabilityType.PATH_TRAVERSAL] = PathTraversalFixer()
        self._fixers[VulnerabilityType.COMMAND_INJECTION] = CommandInjectionFixer()

    def register_fixer(self, fixer: BaseFixer):
        self._fixers[fixer.vuln_type] = fixer

    def get_fixer(self, vuln_type: VulnerabilityType) -> Optional[BaseFixer]:
        return self._fixers.get(vuln_type)

    def fix_file(self, file_path: str, vulnerabilities: List[Vulnerability], language: Language) -> FixResult:
        """修复单个文件"""
        file_path = str(Path(file_path).resolve())

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source_code = f.read()
        except Exception as e:
            return FixResult(
                file_path=file_path,
                language=language,
                original_source="",
                fixed_source="",
                error=f"读取文件失败: {e}",
            )

        if not vulnerabilities:
            return FixResult(
                file_path=file_path,
                language=language,
                original_source=source_code,
                fixed_source=source_code,
            )

        non_auto_fixable = [v for v in vulnerabilities if not v.auto_fixable]
        auto_fixable = [v for v in vulnerabilities if v.auto_fixable]

        by_type: Dict[VulnerabilityType, List[Vulnerability]] = {}
        for vuln in auto_fixable:
            by_type.setdefault(vuln.vuln_type, []).append(vuln)

        current_source = source_code
        all_results: List[FixResult] = []

        for v in non_auto_fixable:
            all_results.append(
                FixResult(
                    file_path=file_path,
                    language=language,
                    original_source=source_code,
                    fixed_source=source_code,
                    vulnerabilities_skipped=[v],
                    error=f"漏洞类型 {v.vuln_type.value} 标记为不可自动修复，需人工处理",
                )
            )

        for vuln_type, vulns in by_type.items():
            fixer = self._fixers.get(vuln_type)
            if fixer is None or not fixer.supports_language(language):
                for v in vulns:
                    all_results.append(
                        FixResult(
                            file_path=file_path,
                            language=language,
                            original_source=current_source,
                            fixed_source=current_source,
                            vulnerabilities_skipped=[v],
                            error=f"不支持的语言或类型: {vuln_type}/{language}",
                        )
                    )
                continue

            fix_result = fixer.fix(current_source, vulns, language)
            fix_result.file_path = file_path
            all_results.append(fix_result)
            current_source = fix_result.fixed_source

        merged = FixResult(
            file_path=file_path,
            language=language,
            original_source=source_code,
            fixed_source=current_source,
        )

        for r in all_results:
            merged.actions.extend(r.actions)
            merged.vulnerabilities_fixed.extend(r.vulnerabilities_fixed)
            merged.vulnerabilities_skipped.extend(r.vulnerabilities_skipped)

        return merged

    def fix_scan_results(self, scan_results: List[ScanResult]) -> List[FixResult]:
        """根据扫描结果批量修复"""
        fix_results: List[FixResult] = []

        for scan_result in scan_results:
            if scan_result.parse_error:
                continue
            if not scan_result.has_vulnerabilities:
                continue

            fix_result = self.fix_file(
                scan_result.file_path,
                scan_result.vulnerabilities,
                scan_result.language,
            )
            fix_results.append(fix_result)

        return fix_results

    def apply_fix(self, fix_result: FixResult, backup: bool = True) -> bool:
        """将修复结果应用到文件"""
        if not fix_result.is_changed:
            return False

        file_path = fix_result.file_path
        if not os.path.exists(file_path):
            return False

        if backup:
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fix_result.fixed_source)
            return True
        except Exception:
            return False

    def apply_fixes(self, fix_results: List[FixResult], backup: bool = True) -> Dict[str, Any]:
        """批量应用修复"""
        applied = 0
        failed = 0
        skipped = 0

        for result in fix_results:
            if not result.is_changed:
                skipped += 1
                continue

            if self.apply_fix(result, backup):
                applied += 1
            else:
                failed += 1

        return {
            "applied": applied,
            "failed": failed,
            "skipped": skipped,
            "total": len(fix_results),
        }

    def get_fix_summary(self, fix_results: List[FixResult]) -> Dict[str, Any]:
        """生成修复汇总报告"""
        total_files = len(fix_results)
        changed_files = sum(1 for r in fix_results if r.is_changed)
        total_fixed = sum(r.success_count for r in fix_results)
        total_skipped = sum(r.skipped_count for r in fix_results)

        by_type: Dict[str, int] = {}
        for r in fix_results:
            for v in r.vulnerabilities_fixed:
                t = v.vuln_type.value
                by_type[t] = by_type.get(t, 0) + 1

        details = []
        for r in fix_results:
            if r.is_changed:
                details.append({
                    "file": r.file_path,
                    "fixed": r.success_count,
                    "skipped": r.skipped_count,
                    "actions": [a.to_dict() for a in r.actions],
                })

        return {
            "summary": {
                "total_files": total_files,
                "changed_files": changed_files,
                "total_fixed": total_fixed,
                "total_skipped": total_skipped,
                "by_type": by_type,
            },
            "details": details,
        }
