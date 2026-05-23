import os
from typing import List, Optional, Dict

from .config import AppConfig, LinterConfig
from .git_utils import GitRepoManager, FileChange, get_ci_environment, ChangeType
from .linters import (
    BaseLinter,
    ESLintLinter,
    PylintLinter,
    CheckstyleLinter,
    BlackLinter,
    CustomRuleLinter,
    LinterResult,
)
from .report import ReportGenerator, QualityReport
from .threshold import ThresholdChecker
from .quality_gate import QualityGateChecker, QualityGateResult
from .html_report import HTMLReportGenerator


LINTER_CLASSES: Dict[str, type] = {
    "eslint": ESLintLinter,
    "pylint": PylintLinter,
    "checkstyle": CheckstyleLinter,
    "black": BlackLinter,
}


class CodeQualityChecker:
    def __init__(
        self,
        config: AppConfig,
        repo_path: str = ".",
    ):
        self.config = config
        self.repo_path = os.path.abspath(repo_path)
        self.git_manager = GitRepoManager(repo_path)
        self.report_generator = ReportGenerator(config.report.output_dir)
        self.threshold_checker = ThresholdChecker(config.thresholds)
        self.quality_gate_checker = QualityGateChecker(config.quality_gate)
        self.linters: Dict[str, BaseLinter] = {}
        self._init_linters()

    def _init_linters(self):
        for name, linter_config in self.config.linters.items():
            if not linter_config.enabled:
                continue

            linter_class = LINTER_CLASSES.get(name)
            if linter_class is None:
                print(f"Warning: Unknown linter '{name}', skipping.")
                continue

            linter = linter_class(linter_config)
            if not linter.is_available():
                print(f"Warning: {name} is not available, skipping.")
                continue

            self.linters[name] = linter

        if self.config.custom_rules:
            custom_linter_config = LinterConfig(enabled=True)
            custom_linter = CustomRuleLinter(
                custom_linter_config,
                rules_config=self.config.custom_rules,
            )
            if custom_linter.rules:
                self.linters["custom"] = custom_linter
                print(f"Loaded {len(custom_linter.rules)} custom rules")

    def get_files_to_check(
        self,
        incremental: Optional[bool] = None,
        base_branch: Optional[str] = None,
        specific_files: Optional[List[str]] = None,
    ) -> List[FileChange]:
        if specific_files:
            file_changes = []
            for f in specific_files:
                abs_path = os.path.abspath(f)
                if os.path.isfile(abs_path):
                    rel_path = os.path.relpath(abs_path, self.repo_path)
                    rel_path = rel_path.replace("\\", "/")
                    file_changes.append(
                        FileChange(
                            path=rel_path,
                            change_type=ChangeType.SPECIFIED.value,
                            abs_path=abs_path,
                        )
                    )
            return file_changes

        use_incremental = incremental if incremental is not None else self.config.incremental.enabled
        base_branch = base_branch or self.config.incremental.base_branch

        all_extensions = []
        for linter in self.linters.values():
            all_extensions.extend(linter.extensions)
        all_extensions = list(set(all_extensions))

        if use_incremental and self.git_manager.is_git_repo():
            print(f"Running incremental check against branch: {base_branch}")
            return self.git_manager.get_changed_files(
                base_branch=base_branch,
                extensions=all_extensions,
            )
        else:
            print("Running full check on all files...")
            return self.git_manager.get_all_files(extensions=all_extensions)

    def run_checks(
        self,
        files: List[FileChange],
        auto_fix: bool = False,
    ) -> List[LinterResult]:
        results: List[LinterResult] = []

        if not files:
            print("No files to check.")
            return results

        print(f"Checking {len(files)} files...\n")

        for name, linter in self.linters.items():
            filtered_files = linter.filter_files(files)
            if not filtered_files:
                print(f"Skipping {name}: no matching files")
                results.append(LinterResult(linter_name=name, success=True))
                continue

            fix_flag = auto_fix and linter.config.auto_fix
            print(f"Running {name} on {len(filtered_files)} files" +
                  (f" (auto-fix enabled)" if fix_flag else "") + "...")

            result = linter.check_files(filtered_files, auto_fix=fix_flag)
            results.append(result)

            status = "✓" if result.success else "✗"
            status_color = "\033[92m" if result.success else "\033[91m"
            reset_color = "\033[0m"
            score_str = f", score: {result.score:.2f}" if result.score is not None else ""
            print(f"  {status_color}{status}{reset_color} {name}: "
                  f"{result.error_count} errors, {result.warning_count} warnings{score_str}")

        return results

    def run(
        self,
        incremental: Optional[bool] = None,
        base_branch: Optional[str] = None,
        auto_fix: bool = False,
        specific_files: Optional[List[str]] = None,
        format: Optional[str] = None,
        save_report: bool = True,
        generate_html: bool = False,
    ) -> tuple[QualityReport, int]:
        platform, pr_number, commit_sha = get_ci_environment()
        if platform:
            platform_name = platform.upper()
            if pr_number:
                print(f"CI Environment: {platform_name} PR/MR #{pr_number}, Commit: {commit_sha}")
            else:
                print(f"CI Environment: {platform_name}, Commit: {commit_sha}")

        files = self.get_files_to_check(incremental, base_branch, specific_files)
        results = self.run_checks(files, auto_fix)

        report_format = format or self.config.report.format
        report = self.report_generator.generate(
            results,
            format=report_format,
            show_summary=self.config.report.show_summary,
        )

        report = self.threshold_checker.check_thresholds(report)

        quality_gate_result = self.quality_gate_checker.check(report)
        if self.config.quality_gate.enabled:
            self.quality_gate_checker.print_summary(quality_gate_result)

        if save_report:
            report_path = self.report_generator.save_report(report)
            print(f"Full JSON report saved to: {report_path}")

            if generate_html or self.config.report.html.enabled:
                html_generator = HTMLReportGenerator(self.config.report.output_dir)
                html_path = html_generator.generate(report, quality_gate_result)
                print(f"HTML report saved to: {html_path}")

        threshold_exit = self.threshold_checker.get_exit_code(
            report, fail_on_threshold=self.config.ci.fail_on_threshold
        )
        qg_exit = self.quality_gate_checker.get_exit_code(quality_gate_result)

        exit_code = max(threshold_exit, qg_exit)

        return report, exit_code

    def list_available_linters(self) -> List[str]:
        return list(self.linters.keys())

    def list_enabled_linters(self) -> List[str]:
        return [name for name, cfg in self.config.linters.items() if cfg.enabled]
