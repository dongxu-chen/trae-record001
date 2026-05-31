#!/usr/bin/env python3
import os
import sys
import argparse
import json
from backend.ci_integration import CIIntegration


def main():
    parser = argparse.ArgumentParser(
        description='Git Branch Policy Checker - 检查分支命名、合并方向、PR大小和提交频率',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py --repo ./my-project
  python cli.py --source feature/ABC-123 --target develop
  python cli.py --format json > results.json
  python cli.py --format checklist
  python cli.py --check-conflicts
        """
    )
    
    parser.add_argument('--repo', default='.', help='Git仓库路径 (默认: 当前目录)')
    parser.add_argument('--source', help='源分支名称 (默认: 当前分支)')
    parser.add_argument('--target', default='develop', help='目标分支名称 (默认: develop)')
    parser.add_argument('--format', choices=['console', 'json', 'checklist'], 
                       default='console', help='输出格式 (默认: console)')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--check-conflicts', action='store_true', 
                       help='仅运行冲突检测')
    parser.add_argument('--check-branch-age', action='store_true',
                       help='仅运行分支年龄检查')
    parser.add_argument('--check-commit-quality', action='store_true',
                       help='仅运行提交质量检查')
    parser.add_argument('--team-report', action='store_true',
                       help='生成团队简报统计')
    parser.add_argument('--days', type=int, default=30,
                       help='分析天数 (默认: 30)')
    parser.add_argument('--list-branches', action='store_true', help='列出所有分支')
    
    args = parser.parse_args()

    try:
        if args.list_branches:
            from backend.git_utils import GitUtils
            git = GitUtils(args.repo)
            branches = git.get_all_branches()
            current = git.get_current_branch()
            print('可用分支:')
            for b in branches:
                prefix = '* ' if b == current else '  '
                print(f'{prefix}{b}')
            return 0

        ci = CIIntegration(args.repo)

        if args.check_conflicts:
            source = args.source or ci.git_utils.get_current_branch()
            result = ci.auto_fix.detect_conflicts(source, args.target)
            from backend.rule_engine import Report, CheckStatus
            report = Report(check_results=[result])
            print(ci.output_console(report))
            return 1 if result.status == CheckStatus.FAIL else 0

        if args.check_branch_age:
            source = args.source or ci.git_utils.get_current_branch()
            result = ci.branch_age_checker.check(source, args.target)
            from backend.rule_engine import Report, CheckStatus
            report = Report(check_results=[result])
            print(ci.output_console(report))
            return 1 if result.status == CheckStatus.FAIL else 0

        if args.check_commit_quality:
            source = args.source or ci.git_utils.get_current_branch()
            result = ci.commit_quality_checker.check(source, args.days)
            from backend.rule_engine import Report, CheckStatus
            report = Report(check_results=[result])
            print(ci.output_console(report))
            return 1 if result.status == CheckStatus.FAIL else 0

        if args.team_report:
            result = ci.team_report_checker.check(days=args.days)
            from backend.rule_engine import Report
            report = Report(check_results=[result])
            print(ci.output_console(report))
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

        return ci.exit_with_code(report)
        
    except Exception as e:
        print(f'错误: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
