#!/usr/bin/env python3
import os
import sys
import json
from typing import Dict, List
from .git_utils import GitUtils
from .config import Config
from .rule_engine import Report, CheckStatus
from .checkers.branch_naming import BranchNamingChecker
from .checkers.merge_direction import MergeDirectionChecker
from .checkers.pr_size import PRSizeChecker
from .checkers.commit_frequency import CommitFrequencyChecker
from .checkers.branch_age import BranchAgeChecker
from .checkers.commit_quality import CommitQualityChecker
from .checkers.team_report import TeamReportChecker
from .auto_fix import AutoFix


class CIIntegration:
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getenv('GIT_REPO_PATH', '.')
        self.config = Config()
        self.git_utils = GitUtils(self.repo_path)
        self.auto_fix = AutoFix(self.git_utils, self.config)
        
        self.branch_naming_checker = BranchNamingChecker(self.git_utils, self.config)
        self.merge_direction_checker = MergeDirectionChecker(self.git_utils, self.config)
        self.pr_size_checker = PRSizeChecker(self.git_utils, self.config)
        self.commit_frequency_checker = CommitFrequencyChecker(self.git_utils, self.config)
        self.branch_age_checker = BranchAgeChecker(self.git_utils, self.config)
        self.commit_quality_checker = CommitQualityChecker(self.git_utils, self.config)
        self.team_report_checker = TeamReportChecker(self.git_utils, self.config)

    def run_full_check(self, source_branch: str = None, target_branch: str = 'develop') -> Report:
        if source_branch is None:
            source_branch = self.git_utils.get_current_branch()

        report = Report(
            source_branch=source_branch,
            target_branch=target_branch,
            repo_path=self.repo_path
        )

        report.check_results.append(self.branch_naming_checker.check(source_branch))
        report.check_results.append(self.merge_direction_checker.check(source_branch, target_branch))
        report.check_results.append(self.pr_size_checker.check(source_branch, target_branch))
        report.check_results.append(self.commit_frequency_checker.check(source_branch))
        report.check_results.append(self.branch_age_checker.check(source_branch, target_branch))
        report.check_results.append(self.commit_quality_checker.check(source_branch))
        report.check_results.append(self.auto_fix.detect_conflicts(source_branch, target_branch))

        return report

    def output_json(self, report: Report, indent: int = 2) -> str:
        return report.to_json(indent=indent)

    def output_checklist(self, report: Report) -> str:
        return report.to_checklist()

    def output_console(self, report: Report) -> str:
        lines = []
        report_dict = report.to_dict()
        summary = report_dict['summary']

        lines.append('')
        lines.append('=' * 70)
        lines.append('  GIT BRANCH POLICY CHECK')
        lines.append('=' * 70)
        lines.append('')
        lines.append(f'  Repository: {report.repo_path}')
        lines.append(f'  Source Branch: {report.source_branch}')
        lines.append(f'  Target Branch: {report.target_branch}')
        lines.append(f'  Report ID: {report.report_id}')
        lines.append(f'  Generated: {report.generated_at}')
        lines.append('')

        status_icon = '\u274c' if summary['status'] == 'failed' else '\u2705'
        lines.append(f'  {status_icon} OVERALL STATUS: {summary["status"].upper()}')
        lines.append('')
        lines.append(f'  \u2705 Passed:  {summary["passed"]}')
        lines.append(f'  \u274c Errors:  {summary["errors"]}')
        lines.append(f'  \u26a0\ufe0f  Warnings: {summary["warnings"]}')
        lines.append(f'  \u2139\ufe0f  Skipped: {summary["skipped"]}')
        lines.append('')

        for check_result in report.check_results:
            cr_dict = check_result.to_dict()
            lines.append('-' * 70)
            
            status_icon = '\u2705'
            if check_result.status == CheckStatus.FAIL:
                status_icon = '\u274c'
            elif check_result.status == CheckStatus.WARNING:
                status_icon = '\u26a0\ufe0f'
            elif check_result.status == CheckStatus.SKIP:
                status_icon = '\u2139\ufe0f'
            
            lines.append(f'  {status_icon} {check_result.display_name}')
            lines.append(f'     Category: {check_result.category}')
            lines.append(f'     Status: {check_result.status.value.upper()}')
            lines.append(f'     Checks: {cr_dict["summary"]["total"]} total, {cr_dict["summary"]["passed"]} passed')
            lines.append('')

            for item in check_result.items:
                item_icon = '\u2705' if item.status == CheckStatus.PASS else '\u274c'
                if item.status == CheckStatus.WARNING:
                    item_icon = '\u26a0\ufe0f'
                elif item.status == CheckStatus.SKIP:
                    item_icon = '\u2139\ufe0f'
                
                severity_tag = f'[{item.severity.value.upper()}]'
                
                lines.append(f'     {item_icon} {severity_tag} {item.name}')
                lines.append(f'        {item.message}')
                
                if item.suggestion:
                    lines.append(f'        \ud83d\udca1 Suggestion: {item.suggestion.split(chr(10))[0]}')
                
                if item.status != CheckStatus.PASS:
                    for key, value in item.details.items():
                        if isinstance(value, list) and len(value) > 3:
                            value = f'[{", ".join(value[:3])} ...]'
                        elif isinstance(value, dict):
                            value = '{...}'
                        lines.append(f'        - {key}: {value}')
                lines.append('')

        lines.append('-' * 70)

        if summary['errors'] > 0:
            lines.append('')
            lines.append('  \u274c ERRORS FOUND - Please fix the issues above before merging.')
            lines.append('')
            lines.append('  Error Items:')
            for item in summary['error_items']:
                lines.append(f'    - [{item["severity"].upper()}] {item["category"]}: {item["message"]}')

        if summary['warnings'] > 0:
            lines.append('')
            lines.append('  \u26a0\ufe0f  WARNINGS - Please review the warnings above.')

        lines.append('')
        lines.append('=' * 70)
        lines.append('')

        return '\n'.join(lines)

    def output_github_annotations(self, report: Report) -> str:
        report_dict = report.to_dict()
        annotations = []

        for cr in report.check_results:
            for item in cr.items:
                if item.status in [CheckStatus.FAIL, CheckStatus.WARNING]:
                    annotation_level = 'error' if item.status == CheckStatus.FAIL else 'warning'
                    annotations.append({
                        'path': '.git/policy-check',
                        'start_line': 1,
                        'end_line': 1,
                        'annotation_level': annotation_level,
                        'title': f'{cr.display_name}: {item.name}',
                        'message': item.message + (f'\n\nSuggestion: {item.suggestion}' if item.suggestion else '')
                    })

        return json.dumps(annotations)

    def exit_with_code(self, report: Report) -> int:
        report_dict = report.to_dict()
        if report_dict['summary']['status'] == 'failed':
            return 1
        return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Git Branch Policy Checker')
    parser.add_argument('--repo', default='.', help='Repository path')
    parser.add_argument('--source', help='Source branch')
    parser.add_argument('--target', default='develop', help='Target branch')
    parser.add_argument('--format', choices=['console', 'json', 'checklist'], 
                       default='console', help='Output format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--check-conflicts', action='store_true', 
                       help='Only run conflict detection')
    parser.add_argument('--check-branch-age', action='store_true',
                       help='Run branch age check only')
    parser.add_argument('--check-commit-quality', action='store_true',
                       help='Run commit quality check only')
    parser.add_argument('--team-report', action='store_true',
                       help='Generate team report')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to analyze (default: 30)')
    parser.add_argument('--list-branches', action='store_true',
                       help='List available branches')
    
    args = parser.parse_args()

    if args.list_branches:
        ci = CIIntegration(args.repo)
        branches = ci.git_utils.get_all_branches()
        current = ci.git_utils.get_current_branch()
        print('Available branches:')
        for b in branches:
            prefix = '* ' if b == current else '  '
            print(f'{prefix}{b}')
        return 0

    ci = CIIntegration(args.repo)

    if args.check_conflicts:
        source = args.source or ci.git_utils.get_current_branch()
        result = ci.auto_fix.detect_conflicts(source, args.target)
        print(ci.output_console(Report(check_results=[result])))
        return 1 if result.status == CheckStatus.FAIL else 0

    if args.check_branch_age:
        source = args.source or ci.git_utils.get_current_branch()
        result = ci.branch_age_checker.check(source, args.target)
        print(ci.output_console(Report(check_results=[result])))
        return 1 if result.status == CheckStatus.FAIL else 0

    if args.check_commit_quality:
        source = args.source or ci.git_utils.get_current_branch()
        result = ci.commit_quality_checker.check(source, args.days)
        print(ci.output_console(Report(check_results=[result])))
        return 1 if result.status == CheckStatus.FAIL else 0

    if args.team_report:
        result = ci.team_report_checker.check(days=args.days)
        print(ci.output_console(Report(check_results=[result])))
        return 0

    report = ci.run_full_check(args.source, args.target)
    
    output = ''
    if args.format == 'json':
        output = ci.output_json(report)
    elif args.format == 'checklist':
        output = ci.output_checklist(report)
    else:
        output = ci.output_console(report)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'Report written to: {args.output}')
    else:
        print(output)

    sys.exit(ci.exit_with_code(report))


if __name__ == '__main__':
    main()
