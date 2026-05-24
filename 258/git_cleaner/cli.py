"""主程序入口"""
import os
import sys
import click
from git import Repo, InvalidGitRepositoryError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

from .config import Config
from .large_file_detector import LargeFileDetector
from .sensitive_detector import SensitiveInfoDetector
from .stale_branch_detector import StaleBranchDetector
from .bfg_cleaner import BFGCleaner
from .report import ReportGenerator
from .branch_analyzer import BranchDependencyAnalyzer
from .storage_predictor import StoragePredictor
from .report_exporter import ReportExporter
from .hook_manager import GitHookManager

console = Console()

@click.group()
@click.option('--repo-path', default='.', help='Git仓库路径 (默认: 当前目录)')
@click.option('--bfg-jar', default='bfg.jar', help='BFG Repo-Cleaner JAR文件路径')
@click.pass_context
def cli(ctx, repo_path, bfg_jar):
    """Git仓库归档清理工具 - 扫描并清理Git仓库历史中的问题"""
    ctx.ensure_object(dict)
    
    try:
        repo = Repo(repo_path, search_parent_directories=True)
        ctx.obj['repo'] = repo
        ctx.obj['repo_path'] = repo.working_dir
        ctx.obj['bfg_jar'] = bfg_jar
        ctx.obj['config'] = Config(bfg_jar_path=bfg_jar)
        console.print(f"[green]✓ 已加载仓库:[/green] {repo.working_dir}")
    except InvalidGitRepositoryError:
        console.print(f"[red]✗ 错误: {repo_path} 不是有效的Git仓库[/red]")
        sys.exit(1)

@cli.command()
@click.option('--large-only', is_flag=True, help='只扫描大文件')
@click.option('--sensitive-only', is_flag=True, help='只扫描敏感信息')
@click.option('--branches-only', is_flag=True, help='只扫描陈旧分支')
@click.option('--storage-only', is_flag=True, help='只分析存储空间')
@click.option('--large-threshold', default=10, type=int, help='大文件阈值 (MB, 默认: 10)')
@click.option('--stale-days', default=365, type=int, help='陈旧分支天数 (默认: 365)')
@click.option('--max-commits', default=1000, type=int, help='存储分析最大提交数')
@click.pass_context
def scan(ctx, large_only, sensitive_only, branches_only, storage_only, large_threshold, stale_days, max_commits):
    """扫描Git仓库，检测大文件、敏感信息、陈旧分支和存储增长趋势"""
    repo = ctx.obj['repo']
    config = ctx.obj['config']
    config.large_file_threshold = large_threshold * 1024 * 1024
    config.stale_branch_days = stale_days
    
    report = ReportGenerator()
    large_files = []
    sensitive_findings = []
    stale_branches = []
    storage_analysis = None
    
    scan_all = not (large_only or sensitive_only or branches_only or storage_only)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        if scan_all or large_only:
            task = progress.add_task("[cyan]扫描大文件...", total=None)
            detector = LargeFileDetector(repo, config)
            large_files = detector.scan()
            progress.update(task, completed=True)
            console.print(f"  发现 {len(large_files)} 个大文件")
        
        if scan_all or sensitive_only:
            task = progress.add_task("[cyan]扫描敏感信息...", total=None)
            detector = SensitiveInfoDetector(repo, config)
            sensitive_findings = detector.scan()
            progress.update(task, completed=True)
            console.print(f"  发现 {len(sensitive_findings)} 处敏感信息")
        
        if scan_all or branches_only:
            task = progress.add_task("[cyan]扫描陈旧分支...", total=None)
            detector = StaleBranchDetector(repo, config)
            stale_branches = detector.scan()
            progress.update(task, completed=True)
            console.print(f"  发现 {len(stale_branches)} 个陈旧分支")
        
        if scan_all or storage_only:
            task = progress.add_task("[cyan]分析存储增长趋势...", total=None)
            predictor = StoragePredictor(repo)
            storage_analysis = predictor.get_full_analysis(max_commits)
            progress.update(task, completed=True)
            
            pred = storage_analysis.get('prediction', {})
            if 'error' not in pred:
                console.print(f"  当前仓库大小: {round(pred.get('current_size_mb', 0), 2)} MB")
                console.print(f"  月均增长: {round(storage_analysis.get('trend', {}).get('avg_monthly_growth_mb', 0), 2)} MB")
    
    console.print("\n[bold]=== 扫描结果 ===[/bold]")
    report.print_summary(large_files, sensitive_findings, stale_branches)
    
    if storage_analysis and (scan_all or storage_only):
        _print_storage_analysis(storage_analysis)
    
    if scan_all or large_only:
        report.print_large_files(large_files)
        lf_detector = LargeFileDetector(repo, config)
        patterns = lf_detector.get_excluded_patterns()
        report.print_exclude_patterns(patterns)
    
    if scan_all or sensitive_only:
        detector = SensitiveInfoDetector(repo, config)
        grouped = detector.group_by_type(sensitive_findings)
        report.print_sensitive_findings(sensitive_findings, grouped)
    
    if scan_all or branches_only:
        detector = StaleBranchDetector(repo, config)
        summary = detector.get_stale_branches_summary(stale_branches)
        report.print_stale_branches(stale_branches, summary)
    
    report.print_cleanup_suggestions(large_files, sensitive_findings, stale_branches)
    
    ctx.obj['large_files'] = large_files
    ctx.obj['sensitive_findings'] = sensitive_findings
    ctx.obj['stale_branches'] = stale_branches
    ctx.obj['storage_analysis'] = storage_analysis


def _print_storage_analysis(analysis: Dict):
    """打印存储分析结果"""
    pred = analysis.get('prediction', {})
    trend = analysis.get('trend', {})
    
    if 'error' in pred:
        console.print(f"\n[yellow]⚠️  存储分析: {pred['error']}[/yellow]")
        return
    
    console.print("\n[bold]📊 存储空间分析[/bold]")
    
    table = Table(show_header=False, box=None)
    table.add_column("指标", style="cyan")
    table.add_column("值", justify="right")
    
    table.add_row("当前仓库大小", f"{round(pred.get('current_size_mb', 0), 2)} MB")
    table.add_row("当前仓库大小 (GB)", f"{round(pred.get('current_size_gb', 0), 2)} GB")
    table.add_row("分析提交数", f"{trend.get('total_commits', 0)}")
    table.add_row("分析时间跨度", f"{trend.get('days_span', 0)} 天")
    table.add_row("月均增长", f"{round(trend.get('avg_monthly_growth_mb', 0), 2)} MB")
    
    console.print(table)
    
    thresholds = pred.get('time_to_thresholds', [])
    if thresholds:
        console.print("\n[bold]📈 仓库膨胀预测:[/bold]")
        for t in thresholds:
            console.print(f"  - 达到 [yellow]{t['threshold']}[/yellow]: 预计 [cyan]{t['months_needed']}[/cyan] 个月后 ({t['estimated_date']})")
    
    predictions = pred.get('predictions', [])
    if predictions:
        console.print("\n[bold]🔮 未来12个月预测:[/bold]")
        pred_table = Table()
        pred_table.add_column("月份", style="cyan")
        pred_table.add_column("预测大小 (MB)", justify="right")
        for p in predictions[:12]:
            pred_table.add_row(p['date'], f"{round(p['predicted_size_mb'], 2)}")
        console.print(pred_table)


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['json', 'html', 'both']), default='both', help='导出格式')
@click.option('--output-dir', default='cleanup_reports', help='输出目录')
@click.option('--include-storage', is_flag=True, help='包含存储分析')
@click.pass_context
def export(ctx, output_format, output_dir, include_storage):
    """导出清理报告为JSON或HTML格式"""
    repo = ctx.obj['repo']
    
    large_files = ctx.obj.get('large_files', [])
    sensitive_findings = ctx.obj.get('sensitive_findings', [])
    stale_branches = ctx.obj.get('stale_branches', [])
    storage_analysis = ctx.obj.get('storage_analysis')
    
    if not any([large_files, sensitive_findings, stale_branches]):
        console.print("[yellow]⚠️  未找到扫描数据，请先执行 scan 命令[/yellow]")
        
        with console.status("[cyan]正在扫描...[/cyan]"):
            config = ctx.obj['config']
            large_files = LargeFileDetector(repo, config).scan()
            sensitive_findings = SensitiveInfoDetector(repo, config).scan()
            stale_branches = StaleBranchDetector(repo, config).scan()
            
            if include_storage:
                storage_analysis = StoragePredictor(repo).get_full_analysis()
    
    exporter = ReportExporter(output_dir)
    report_data = exporter.generate_cleanup_report_data(
        repo_path=repo.working_dir,
        large_files=large_files,
        sensitive_findings=sensitive_findings,
        stale_branches=stale_branches,
        storage_analysis=storage_analysis if include_storage else None
    )
    
    exported_files = []
    
    if output_format in ['json', 'both']:
        path = exporter.export_json(report_data)
        exported_files.append(path)
        console.print(f"[green]✓ JSON报告已导出:[/green] {path}")
    
    if output_format in ['html', 'both']:
        path = exporter.export_html(report_data)
        exported_files.append(path)
        console.print(f"[green]✓ HTML报告已导出:[/green] {path}")
    
    total_saved = report_data['summary']['total_large_size_mb']
    console.print(f"\n[bold]报告摘要:[/bold]")
    console.print(f"  - 大文件: {report_data['summary']['large_file_count']} 个")
    console.print(f"  - 敏感信息: {report_data['summary']['sensitive_findings_count']} 处")
    console.print(f"  - 陈旧分支: {report_data['summary']['stale_branches_count']} 个")
    console.print(f"  - 预计节省: {total_saved} MB")


@cli.group()
def hooks():
    """管理Git钩子（提交/推送前自动检测大文件）"""
    pass


@hooks.command('install')
@click.option('--type', 'hook_type', type=click.Choice(['pre-push', 'pre-commit', 'all']), default='all', help='钩子类型')
@click.option('--max-size', default=10, type=int, help='最大文件大小 (MB)')
@click.option('--auto-block/--warn-only', default=True, help='自动阻止或仅警告')
@click.pass_context
def install_hooks(ctx, hook_type, max_size, auto_block):
    """安装Git钩子，自动检测并阻止大文件提交"""
    repo = ctx.obj['repo']
    manager = GitHookManager(repo)
    
    installed = []
    
    if hook_type in ['pre-push', 'all']:
        path = manager.install_pre_push_hook(max_size, auto_block)
        installed.append(('pre-push', path))
        console.print(f"[green]✓ 已安装 pre-push 钩子[/green]")
    
    if hook_type in ['pre-commit', 'all']:
        path = manager.install_pre_commit_hook(max_size)
        installed.append(('pre-commit', path))
        console.print(f"[green]✓ 已安装 pre-commit 钩子[/green]")
    
    console.print(f"\n[bold]钩子配置:[/bold]")
    console.print(f"  最大文件大小: {max_size} MB")
    console.print(f"  超出限制时: {'阻止提交' if auto_block else '仅显示警告'}")
    console.print("\n  如需绕过钩子检查，使用:")
    console.print(f"    git commit --no-verify  (跳过pre-commit)")
    console.print(f"    git push --no-verify    (跳过pre-push)")


@hooks.command('uninstall')
@click.option('--type', 'hook_type', type=click.Choice(['pre-push', 'pre-commit', 'all']), default='all', help='钩子类型')
@click.pass_context
def uninstall_hooks(ctx, hook_type):
    """卸载Git钩子"""
    repo = ctx.obj['repo']
    manager = GitHookManager(repo)
    
    if hook_type == 'all':
        results = manager.uninstall_all_hooks()
        for name, success in results.items():
            if success:
                console.print(f"[green]✓ 已卸载 {name} 钩子[/green]")
            else:
                console.print(f"[dim]  {name} 钩子不存在或非本工具创建[/dim]")
    else:
        success = manager.uninstall_hook(hook_type)
        if success:
            console.print(f"[green]✓ 已卸载 {hook_type} 钩子[/green]")
        else:
            console.print(f"[yellow]⚠️  {hook_type} 钩子不存在或非本工具创建[/yellow]")


@hooks.command('list')
@click.pass_context
def list_hooks(ctx):
    """列出当前Git钩子状态"""
    repo = ctx.obj['repo']
    manager = GitHookManager(repo)
    hooks = manager.list_hooks()
    
    table = Table(title="Git钩子状态")
    table.add_column("钩子名称", style="cyan")
    table.add_column("是否存在", justify="center")
    table.add_column("是否本工具创建", justify="center")
    table.add_column("路径", style="dim")
    
    for name, info in hooks.items():
        exists = "[green]✓[/green]" if info['exists'] else "[red]✗[/red]"
        ours = "[green]是[/green]" if info['is_ours'] else "[dim]否[/dim]"
        table.add_row(name, exists, ours, info['path'])
    
    console.print(table)

@cli.command()
@click.option('--strip-blobs-larger-than', default=10, type=int, help='删除大于指定大小的文件 (MB)')
@click.option('--delete-files', multiple=True, help='按文件名模式删除 (可多次指定)')
@click.option('--replace-text-file', type=click.Path(exists=True), help='包含需要替换文本的文件')
@click.option('--replace-passwords', is_flag=True, help='替换密码')
@click.option('--dry-run', is_flag=True, help='试运行模式，不实际修改')
@click.option('--force', is_flag=True, help='跳过确认，直接执行')
@click.pass_context
def clean(ctx, strip_blobs_larger_than, delete_files, replace_text_file, replace_passwords, dry_run, force):
    """使用BFG Repo-Cleaner清理Git历史"""
    repo = ctx.obj['repo']
    bfg_jar = ctx.obj['bfg_jar']
    
    if not any([strip_blobs_larger_than, delete_files, replace_text_file, replace_passwords]):
        console.print("[yellow]⚠ 未指定任何清理操作[/yellow]")
        console.print("使用 --help 查看可用选项")
        return
    
    if dry_run:
        console.print("[yellow]=== 试运行模式 ===[/yellow]")
    else:
        analyzer = BranchDependencyAnalyzer(repo)
        warning = analyzer.generate_cleanup_warning()
        console.print(warning)
        
        if not force:
            confirmed = Confirm.ask(
                "\n[bold red]重写历史是破坏性操作，确认继续？[/bold red]",
                default=False
            )
            if not confirmed:
                console.print("[yellow]操作已取消[/yellow]")
                return
    
    try:
        cleaner = BFGCleaner(repo, bfg_jar)
    except FileNotFoundError as e:
        console.print(f"[red]✗ {e}[/red]")
        console.print("请从 https://rtyley.github.io/bfg-repo-cleaner/ 下载BFG")
        sys.exit(1)
    
    results = []
    
    if strip_blobs_larger_than:
        console.print(f"\n[cyan]清理大于 {strip_blobs_larger_than}MB 的文件...[/cyan]")
        result = cleaner.clean_large_files(strip_blobs_larger_than, dry_run)
        console.print(result)
        results.append(result)
    
    if delete_files:
        console.print(f"\n[cyan]清理指定文件: {delete_files}[/cyan]")
        result = cleaner.clean_files_by_name(list(delete_files), dry_run)
        console.print(result)
        results.append(result)
    
    if replace_text_file:
        with open(replace_text_file, 'r') as f:
            patterns = [line.strip() for line in f if line.strip()]
        console.print(f"\n[cyan]替换敏感文本 (从 {replace_text_file} 加载 {len(patterns)} 个模式)...[/cyan]")
        result = cleaner.clean_sensitive_text(patterns, dry_run)
        console.print(result)
        results.append(result)
    
    if replace_passwords:
        console.print("\n[cyan]替换密码...[/cyan]")
        result = cleaner.clean_passwords(dry_run)
        console.print(result)
        results.append(result)
    
    if not dry_run:
        console.print("\n[green]✓ BFG清理完成[/green]")
        console.print("接下来需要执行:")
        console.print("  git reflog expire --expire=now --all")
        console.print("  git gc --prune=now --aggressive")
        console.print("  git push --force (如果需要推送到远程)")
    else:
        console.print("\n[yellow]试运行完成，未做任何修改[/yellow]")

@cli.command('finalize')
@click.option('--dry-run', is_flag=True, help='试运行模式')
@click.option('--force', is_flag=True, help='跳过确认，直接执行')
@click.pass_context
def finalize(ctx, dry_run, force):
    """完成清理：执行reflog过期和垃圾回收"""
    repo = ctx.obj['repo']
    bfg_jar = ctx.obj['bfg_jar']
    
    if dry_run:
        console.print("[yellow]=== 试运行模式 ===[/yellow]")
    else:
        console.print("\n[bold yellow]⚠️  此操作将永久删除过期的ref日志和松散对象[/bold yellow]")
        console.print("  建议在执行前确保:")
        console.print("  1. 已经备份了仓库")
        console.print("  2. BFG清理已经成功完成")
        console.print("  3. 所有必要的分支和标签都已保留")
        console.print("")
        
        if not force:
            confirmed = Confirm.ask(
                "[bold red]确认执行reflog过期和垃圾回收？[/bold red]",
                default=False
            )
            if not confirmed:
                console.print("[yellow]操作已取消[/yellow]")
                return
    
    try:
        cleaner = BFGCleaner(repo, bfg_jar)
        result = cleaner.finalize_cleanup(dry_run)
        console.print(result)
        
        if not dry_run:
            console.print("[green]✓ 清理完成！[/green]")
            console.print("注意: 如果需要推送到远程，请使用: git push --force --all")
    except FileNotFoundError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)
    except RuntimeError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

@cli.command('delete-branches')
@click.option('--days', default=365, type=int, help='删除多少天未更新的分支')
@click.option('--include-remote', is_flag=True, help='同时删除远程分支')
@click.option('--dry-run', is_flag=True, help='试运行模式')
@click.pass_context
def delete_branches(ctx, days, include_remote, dry_run):
    """删除陈旧分支"""
    repo = ctx.obj['repo']
    config = ctx.obj['config']
    config.stale_branch_days = days
    
    detector = StaleBranchDetector(repo, config)
    stale_branches = detector.scan()
    
    if not stale_branches:
        console.print("[green]✓ 没有需要删除的陈旧分支[/green]")
        return
    
    if dry_run:
        console.print("[yellow]=== 试运行模式 ===[/yellow]")
    
    local_branches = [b for b in stale_branches if not b['is_remote']]
    remote_branches = [b for b in stale_branches if b['is_remote']]
    
    if local_branches:
        console.print(f"\n[cyan]将删除 {len(local_branches)} 个本地分支:[/cyan]")
        for b in local_branches:
            console.print(f"  - {b['name']} ({b['days_since_update']} 天未更新)")
        
        if not dry_run:
            for b in local_branches:
                try:
                    repo.delete_head(b['name'], force=True)
                    console.print(f"  [green]✓ 已删除 {b['name']}[/green]")
                except Exception as e:
                    console.print(f"  [red]✗ 删除 {b['name']} 失败: {e}[/red]")
    
    if include_remote and remote_branches:
        console.print(f"\n[cyan]将删除 {len(remote_branches)} 个远程分支:[/cyan]")
        for b in remote_branches:
            console.print(f"  - {b['name']} ({b['days_since_update']} 天未更新)")
        
        if not dry_run:
            for b in remote_branches:
                try:
                    parts = b['name'].split('/', 1)
                    if len(parts) == 2:
                        remote_name, branch_name = parts
                        repo.git.push(remote_name, '--delete', branch_name)
                        console.print(f"  [green]✓ 已删除远程分支 {b['name']}[/green]")
                except Exception as e:
                    console.print(f"  [red]✗ 删除远程分支 {b['name']} 失败: {e}[/red]")
    
    if dry_run:
        console.print("\n[yellow]试运行完成，未做任何修改[/yellow]")
    else:
        console.print(f"\n[green]✓ 共删除 {len([b for b in stale_branches if not b['is_remote'] or (include_remote and b['is_remote'])])} 个分支[/green]")

def main():
    cli(obj={})

if __name__ == '__main__':
    main()
