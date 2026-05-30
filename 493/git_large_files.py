#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from typing import List

import click
from tabulate import tabulate

from git_scanner import GitHistoryScanner, LargeFileInfo
from file_analyzer import LargeFileAnalyzer, FileTypeAnalyzer, ArchiveScanner
from bfg_advisor import BFGCleanerAdvisor, SizeEstimator, format_size
from trend_analysis import TrendAnalyzer, ChartGenerator, CleanupComparison
from pr_generator import PRGenerator


def print_header(title: str):
    click.echo()
    click.echo("=" * 80)
    click.echo(f"  {title}")
    click.echo("=" * 80)


def print_large_files_table(files: List[LargeFileInfo], title: str, limit: int = None):
    if not files:
        click.echo("  没有找到大文件")
        return

    if limit:
        files = files[:limit]

    headers = ["序号", "文件路径", "最大大小", "当前大小", "文件类型", "引入时间", "修改次数"]
    rows = []

    for idx, info in enumerate(files, 1):
        rows.append([
            idx,
            info.file_path,
            format_size(info.max_size),
            format_size(info.current_size),
            info.file_type,
            info.first_introduced.strftime("%Y-%m-%d"),
            info.commit_count
        ])

    click.echo()
    click.echo(f"  {title}")
    click.echo("  " + "-" * 78)
    click.echo(tabulate(rows, headers=headers, tablefmt="simple", maxcolwidths=[4, 40, 10, 10, 12, 12, 8]))
    click.echo()


@click.group()
@click.version_option(version="1.2.0")
def cli():
    """
    Git 仓库大文件检测工具

    扫描 Git 历史记录中的大文件，分析文件类型、引入时间和修改频率，
    并提供 BFG Repo-Cleaner 清理建议、仓库瘦身预估、趋势分析、PR 生成。
    """
    pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
@click.option('--top', '-n', type=int, default=20,
              help='显示前 N 个大文件, 默认: 20')
@click.option('--by-type', is_flag=True, help='按文件类型分组显示')
@click.option('--mime', is_flag=True, help='启用 MIME 类型检测 (需安装 python-magic)')
@click.option('--scan-archives', is_flag=True, help='扫描压缩包内部文件列表')
@click.option('--json-output', '-j', type=click.Path(dir_okay=False),
              help='将结果输出为 JSON 文件')
def scan(repo_path, threshold, top, by_type, mime, scan_archives, json_output):
    """扫描 Git 仓库中的大文件"""

    click.echo(click.style(f"\n开始扫描 Git 仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))
    click.echo(f"大文件阈值: {threshold} MB")
    if mime:
        click.echo("MIME 检测: 已启用")
    if scan_archives:
        click.echo("压缩包扫描: 已启用")
    click.echo()

    try:
        with click.progressbar(length=1, label="正在扫描 Git 历史...") as bar:
            scanner = GitHistoryScanner(repo_path)
            large_files = scanner.scan_history(size_threshold_mb=threshold)
            bar.update(1)

        if not large_files:
            click.echo(click.style("\n✓ 未发现超过阈值的大文件！", fg="green"))
            return

        click.echo(click.style(f"\n发现 {len(large_files)} 个大文件", fg="yellow", bold=True))

        use_blob_data = mime or scan_archives
        analyzer = LargeFileAnalyzer(large_files, scanner=scanner if use_blob_data else None)

        print_header("大文件清单")
        if by_type:
            for file_type, files in analyzer.file_types.items():
                click.echo(f"\n  【{file_type.upper()}】({len(files)} 个文件)")
                print_large_files_table(files, "", limit=top)
        else:
            top_files = analyzer.get_top_largest_files(limit=top)
            print_large_files_table(top_files, f"按大小排序的前 {len(top_files)} 个大文件")

        print_header("文件类型统计")
        type_summary = analyzer.get_summary_by_type()
        type_rows = []
        for file_type, stats in type_summary.items():
            type_rows.append([
                file_type.upper(),
                stats['count'],
                format_size(stats['total_size']),
                format_size(stats['avg_size']),
                stats['total_commits']
            ])
        click.echo(tabulate(
            type_rows,
            headers=["文件类型", "文件数量", "总大小", "平均大小", "总提交次数"],
            tablefmt="simple"
        ))

        print_header("最频繁修改的大文件")
        frequent_files = analyzer.get_most_frequently_modified(limit=5)
        print_large_files_table(frequent_files, "按修改次数排序 (前 5 个)", limit=5)

        print_header("最早引入的大文件")
        oldest_files = analyzer.get_oldest_files(limit=5)
        print_large_files_table(oldest_files, "按引入时间排序 (前 5 个)", limit=5)

        if scan_archives and analyzer.get_archive_reports():
            print_header("压缩包内容分析")
            archive_reports = analyzer.get_archive_reports()
            for file_path, report in archive_reports.items():
                click.echo(f"\n  📦 {file_path} ({format_size(report['total_size'])} 解压后)")
                click.echo(f"     内含文件数: {report['file_count']}")
                if report['total_compressed'] > 0:
                    click.echo(f"     压缩大小: {format_size(report['total_compressed'])}")
                    ratio = report['total_size'] / report['total_compressed'] if report['total_compressed'] > 0 else 0
                    click.echo(f"     压缩比: {ratio:.2f}x")

                if report['file_type_distribution']:
                    click.echo("     文件类型分布:")
                    for ext, count in sorted(report['file_type_distribution'].items(), key=lambda x: -x[1])[:8]:
                        click.echo(f"       {ext}: {count} 个")

                if report['top_files']:
                    click.echo("     最大的文件 (Top 5):")
                    for name, size, comp_size in report['top_files'][:5]:
                        click.echo(f"       {name}: {format_size(size)} (压缩: {format_size(comp_size)})")

        if json_output:
            import json
            output_data = {
                'repo_path': os.path.abspath(repo_path),
                'threshold_mb': threshold,
                'scan_time': datetime.now().isoformat(),
                'large_files_count': len(large_files),
                'large_files': [
                    {
                        'file_path': info.file_path,
                        'max_size': info.max_size,
                        'current_size': info.current_size,
                        'file_type': info.file_type,
                        'first_introduced': info.first_introduced.isoformat(),
                        'last_modified': info.last_modified.isoformat(),
                        'commit_count': info.commit_count,
                        'blob_count': len(info.blob_ids)
                    }
                    for info in large_files.values()
                ]
            }
            if scan_archives and analyzer.get_archive_reports():
                output_data['archive_reports'] = {
                    k: {kk: vv for kk, vv in v.items() if kk != 'top_files'}
                    for k, v in analyzer.get_archive_reports().items()
                }
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            click.echo(click.style(f"\n✓ 结果已保存到: {json_output}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
@click.option('--by-time', is_flag=True, help='按时间间隔分析（默认按提交）')
@click.option('--interval', type=int, default=7,
              help='时间间隔天数（仅按时间分析时有效）, 默认: 7 天')
@click.option('--max-points', type=int, default=20,
              help='趋势图数据点数量, 默认: 20')
def trend(repo_path, threshold, by_time, interval, max_points):
    """大文件数量/大小趋势分析"""

    click.echo(click.style(f"\n分析仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))
    click.echo(f"大文件阈值: {threshold} MB")
    click.echo(f"分析方式: {'按时间间隔 (' + str(interval) + '天)' if by_time else '按提交'}")
    click.echo()

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        if not large_files:
            click.echo(click.style("\n✓ 未发现大文件，无趋势数据！", fg="green"))
            return

        analyzer = TrendAnalyzer(scanner)

        if by_time:
            trend_data = analyzer.analyze_by_time(interval_days=interval, max_points=max_points)
            title = f"Large Files Trend (by {interval} days)"
        else:
            trend_data = analyzer.analyze_by_commit(max_points=max_points)
            title = "Large Files Trend (by commit)"

        summary = analyzer.get_summary()

        print_header("趋势分析汇总")
        if summary:
            summary_rows = [
                ["统计周期", f"{summary['start_date'].strftime('%Y-%m-%d')} ~ {summary['end_date'].strftime('%Y-%m-%d')}"],
                ["大文件数量变化", f"{summary['initial_count']} → {summary['final_count']} (增长: +{summary['count_growth']})"],
                ["大文件大小变化", f"{format_size(summary['initial_size'])} → {format_size(summary['final_size'])} (增长: +{format_size(summary['size_growth'])})"],
                ["峰值文件数量", summary['peak_count']],
                ["峰值大小", format_size(summary['peak_size'])],
                ["数据点数量", summary['data_points']],
            ]
            click.echo(tabulate(summary_rows, tablefmt="simple"))

        print_header("趋势图")
        chart_lines = ChartGenerator.generate_trend_chart(trend_data, title=title)
        for line in chart_lines:
            click.echo(line)

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
def compare(repo_path, threshold):
    """清理前后仓库大小对比图表"""

    click.echo(click.style(f"\n分析仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))
    click.echo(f"大文件阈值: {threshold} MB")
    click.echo()

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        if not large_files:
            click.echo(click.style("\n✓ 未发现大文件，仓库已很精简！", fg="green"))
            return

        comparison = CleanupComparison(scanner)

        print_header("清理前后对比")
        report_lines = comparison.generate_comparison_report()
        for line in report_lines:
            click.echo(line)

        print_header("各类文件大小分布")
        by_type = {}
        for info in large_files.values():
            ftype = info.file_type.split('/')[0] if '/' in info.file_type else info.file_type
            if ftype not in by_type:
                by_type[ftype] = 0
            by_type[ftype] += info.max_size

        type_data = sorted(by_type.items(), key=lambda x: -x[1])
        chart_lines = ChartGenerator.generate_bar_chart(
            type_data,
            title='Large Files by Type'
        )
        for line in chart_lines:
            click.echo(line)

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
@click.option('--create-branch', is_flag=True,
              help='自动创建清理分支（默认仅生成模板）')
@click.option('--update-gitignore', is_flag=True,
              help='在清理分支中自动更新 .gitignore')
@click.option('--output', '-o', type=click.Path(dir_okay=False),
              help='将 PR 模板保存到指定文件')
def pr(repo_path, threshold, create_branch, update_gitignore, output):
    """生成大文件清理 PR 供审查"""

    click.echo(click.style(f"\n分析仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))
    click.echo(f"大文件阈值: {threshold} MB")
    click.echo()

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        if not large_files:
            click.echo(click.style("\n✓ 未发现大文件，无需清理 PR！", fg="green"))
            return

        pr_gen = PRGenerator(repo_path, large_files, scanner=scanner)

        click.echo(click.style(f"将清理 {len(large_files)} 个大文件", fg="yellow", bold=True))
        click.echo()

        if create_branch:
            print_header("创建清理分支")
            result = pr_gen.create_cleanup_branch(
                update_gitignore=update_gitignore,
                add_pr_body=True
            )
            if result['success']:
                click.echo(click.style(f"  ✓ 分支创建成功: {result['branch_name']}", fg="green"))
                if result['gitignore_updated']:
                    click.echo(click.style("  ✓ .gitignore 已更新", fg="green"))
                if result['pr_body_generated']:
                    click.echo(click.style(f"  ✓ PR 模板已生成: {result['pr_body_path']}", fg="green"))
                if result['warnings']:
                    click.echo()
                    click.echo(click.style("  ⚠ 警告:", fg="yellow"))
                    for w in result['warnings']:
                        click.echo(click.style(f"    - {w}", fg="yellow"))
            else:
                click.echo(click.style(f"  ✗ 失败: {result['error']}", fg="red"))
        else:
            if output:
                pr_path = pr_gen.save_pr_template(output_path=output)
            else:
                pr_path = pr_gen.save_pr_template()
            click.echo(click.style(f"  ✓ PR 模板已保存到: {pr_path}", fg="green"))

        print_header("PR 标题")
        click.echo(f"  {pr_gen.generate_pr_title()}")
        click.echo()

        print_header(".gitignore 建议")
        entries = pr_gen.generate_gitignore_entries()
        for line in entries:
            click.echo(f"  {line}")

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
@click.option('--dry-run', is_flag=True,
              help='预演模式：BFG 命令使用 --no-commit 参数')
@click.option('--scan-archives', is_flag=True, help='扫描压缩包内部文件列表')
@click.option('--output', '-o', type=click.Path(dir_okay=False),
              help='将完整报告保存到文件')
def full(repo_path, threshold, dry_run, scan_archives, output):
    """执行完整分析（扫描 + 趋势 + 对比 + BFG建议 + 瘦身预估）"""

    click.echo(click.style(f"\n开始完整分析: {os.path.abspath(repo_path)}", fg="cyan", bold=True))
    click.echo(f"大文件阈值: {threshold} MB")

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GIT 仓库大文件检测 - 完整分析报告")
        report_lines.append("=" * 80)
        report_lines.append(f"仓库路径: {os.path.abspath(repo_path)}")
        report_lines.append(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"大文件阈值: {threshold} MB")
        if dry_run:
            report_lines.append("BFG 模式: 预演模式 (--no-commit)")
        report_lines.append("")

        if not large_files:
            report_lines.append("✓ 未发现超过阈值的大文件！")
            click.echo(click.style("\n✓ 未发现超过阈值的大文件！", fg="green"))
        else:
            analyzer = LargeFileAnalyzer(large_files, scanner=scanner)
            advisor = BFGCleanerAdvisor(large_files, repo_path)
            estimator = SizeEstimator(scanner)
            trend_analyzer = TrendAnalyzer(scanner)
            comparison = CleanupComparison(scanner)

            report_lines.append(f"发现大文件数量: {len(large_files)}")
            report_lines.append("")

            trend_analyzer.analyze_by_commit(max_points=20)
            summary = trend_analyzer.get_summary()
            if summary:
                report_lines.append("=== 趋势分析 ===")
                report_lines.append(f"周期: {summary['start_date'].strftime('%Y-%m-%d')} ~ {summary['end_date'].strftime('%Y-%m-%d')}")
                report_lines.append(f"文件数量: {summary['initial_count']} → {summary['final_count']}")
                report_lines.append(f"文件大小: {format_size(summary['initial_size'])} → {format_size(summary['final_size'])}")
                report_lines.append("")

            report_lines.extend(comparison.generate_comparison_report())
            report_lines.append("")
            report_lines.extend(estimator.generate_savings_report())
            report_lines.append("")
            report_lines.extend(advisor.generate_cleanup_steps(dry_run=dry_run))

            if scan_archives and analyzer.get_archive_reports():
                report_lines.append("")
                report_lines.append("=== 压缩包内容分析 ===")
                for file_path, report in analyzer.get_archive_reports().items():
                    report_lines.append(f"  {file_path}")
                    report_lines.append(f"    内含文件数: {report['file_count']}")
                    report_lines.append(f"    解压后大小: {format_size(report['total_size'])}")

            for line in report_lines:
                click.echo(line)

            click.echo(click.style("\n✓ 分析完成！", fg="green"))

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            click.echo(click.style(f"\n✓ 报告已保存到: {output}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
@click.option('--dry-run', is_flag=True,
              help='预演模式：生成带 --no-commit 的 BFG 命令，不实际修改仓库')
@click.option('--verify', is_flag=True,
              help='验证模式：检查 Java/BFG 是否可用，验证环境准备情况')
def bfg(repo_path, threshold, dry_run, verify):
    """生成 BFG Repo-Cleaner 清理建议"""

    click.echo(click.style(f"\n分析仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        if not large_files:
            click.echo(click.style("\n✓ 未发现大文件，无需清理！", fg="green"))
            return

        advisor = BFGCleanerAdvisor(large_files, repo_path)

        if verify:
            print_header("BFG 环境验证")
            result = advisor.verify_dry_run()

            status_items = [
                ("Java 运行环境", "✓ 已安装" if result['java_available'] else "✗ 未安装",
                 "green" if result['java_available'] else "red"),
                ("BFG Repo-Cleaner", "✓ 已找到" if result['bfg_available'] else "✗ 未找到",
                 "green" if result['bfg_available'] else "red"),
                ("Git 仓库", "✓ 有效" if result.get('repo_valid') else "✗ 无效",
                 "green" if result.get('repo_valid') else "red"),
            ]

            if result.get('java_version'):
                status_items.append(("Java 版本", result['java_version'], "cyan"))

            status_items.append(("受影响文件数", str(result.get('affected_files', 0)), "yellow"))

            for label, value, color in status_items:
                click.echo(f"  {label:20s}: {click.style(value, fg=color)}")

            if result['warnings']:
                click.echo()
                click.echo(click.style("  ⚠ 警告:", fg="yellow"))
                for warning in result['warnings']:
                    click.echo(click.style(f"    - {warning}", fg="yellow"))

            click.echo()

        print_header(f"BFG 清理建议 {'(预演模式)' if dry_run else ''}")
        for step in advisor.generate_cleanup_steps(dry_run=dry_run):
            click.echo(step)

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False), default='.')
@click.option('--threshold', '-t', type=float, default=10.0,
              help='大文件阈值 (MB), 默认: 10 MB')
def estimate(repo_path, threshold):
    """预估仓库瘦身效果"""

    click.echo(click.style(f"\n分析仓库: {os.path.abspath(repo_path)}", fg="cyan", bold=True))

    try:
        scanner = GitHistoryScanner(repo_path)
        large_files = scanner.scan_history(size_threshold_mb=threshold)

        if not large_files:
            click.echo(click.style("\n✓ 未发现大文件，仓库已很精简！", fg="green"))
            return

        estimator = SizeEstimator(scanner)

        print_header("仓库瘦身预估")
        for line in estimator.generate_savings_report():
            click.echo(line)

    except Exception as e:
        click.echo(click.style(f"\n错误: {str(e)}", fg="red", bold=True), err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
