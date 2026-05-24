"""报告生成模块"""
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

class ReportGenerator:
    """生成清理报告"""
    
    def __init__(self):
        self.console = Console()
    
    def print_summary(self, large_files: List[Dict], sensitive_findings: List[Dict], 
                      stale_branches: List[Dict]):
        """打印扫描摘要"""
        total_large_size = sum(f['size'] for f in large_files) if large_files else 0
        
        self.console.print(Panel.fit(
            Text.assemble(
                ("Git仓库扫描报告\n", "bold cyan"),
                f"大文件数量: {len(large_files)}\n",
                f"大文件总大小: {round(total_large_size / (1024*1024), 2)} MB\n",
                f"敏感信息发现: {len(sensitive_findings)} 处\n",
                f"陈旧分支: {len(stale_branches)} 个\n",
                justify="center"
            ),
            title="扫描摘要",
            border_style="cyan"
        ))
    
    def print_large_files(self, large_files: List[Dict], top_n: int = 20):
        """打印大文件列表"""
        if not large_files:
            self.console.print("[green]✓ 未发现大文件[/green]")
            return
        
        table = Table(title=f"大文件列表 (Top {min(top_n, len(large_files))})")
        table.add_column("文件路径", style="cyan")
        table.add_column("大小 (MB)", justify="right")
        table.add_column("Blob ID", style="dim")
        table.add_column("首次提交日期", style="yellow")
        
        for f in large_files[:top_n]:
            table.add_row(
                f['path'],
                f"{f['size_mb']:.2f}",
                f['blob_id'][:12],
                f['commit_date'][:10]
            )
        
        self.console.print(table)
    
    def print_sensitive_findings(self, findings: List[Dict], group_by_type: Dict[str, List[Dict]]):
        """打印敏感信息发现"""
        if not findings:
            self.console.print("[green]✓ 未发现敏感信息[/green]")
            return
        
        self.console.print(Panel(
            f"发现 [red]{len(findings)}[/red] 处敏感信息，分为 [yellow]{len(group_by_type)}[/yellow] 类",
            title="敏感信息警告",
            border_style="red"
        ))
        
        for find_type, items in group_by_type.items():
            table = Table(title=f"{find_type} ({len(items)} 处)")
            table.add_column("文件路径", style="cyan")
            table.add_column("行号", justify="right")
            table.add_column("匹配内容", style="red")
            
            for item in items[:10]:
                table.add_row(item['path'], str(item['line']), item['match'])
            
            self.console.print(table)
            if len(items) > 10:
                self.console.print(f"  [dim]... 还有 {len(items) - 10} 处未显示[/dim]")
    
    def print_stale_branches(self, stale_branches: List[Dict], summary: Dict):
        """打印陈旧分支列表"""
        if not stale_branches:
            self.console.print("[green]✓ 未发现陈旧分支[/green]")
            return
        
        self.console.print(Panel(
            f"发现 [yellow]{len(stale_branches)}[/yellow] 个陈旧分支\n"
            f"  - 本地分支: {summary['local']} 个\n"
            f"  - 远程分支: {summary['remote']} 个",
            title="陈旧分支",
            border_style="yellow"
        ))
        
        table = Table(title="陈旧分支列表")
        table.add_column("分支类型", style="dim")
        table.add_column("分支名称", style="cyan")
        table.add_column("未更新天数", justify="right")
        table.add_column("最后提交日期", style="yellow")
        table.add_column("最后提交者")
        
        for b in stale_branches:
            branch_type = "远程" if b['is_remote'] else "本地"
            table.add_row(
                branch_type,
                b['name'],
                f"{b['days_since_update']} 天",
                b['last_commit_date'].strftime('%Y-%m-%d'),
                b['last_committer']
            )
        
        self.console.print(table)
    
    def print_cleanup_suggestions(self, large_files: List[Dict], sensitive_findings: List[Dict], 
                                  stale_branches: List[Dict], dry_run: bool = False):
        """打印清理建议"""
        self.console.print("\n[bold]清理建议:[/bold]")
        
        prefix = "[DRY-RUN] " if dry_run else ""
        
        if large_files:
            total_size = sum(f['size'] for f in large_files)
            self.console.print(f"\n  1. [yellow]大文件清理:[/yellow]")
            self.console.print(f"     {prefix}可清理 {len(large_files)} 个大文件，释放 {round(total_size/(1024*1024), 2)} MB")
            self.console.print(f"     {prefix}命令: bfg --strip-blobs-bigger-than-10M .")
        
        if sensitive_findings:
            self.console.print(f"\n  2. [red]敏感信息清理:[/red]")
            self.console.print(f"     {prefix}发现 {len(sensitive_findings)} 处敏感信息需要清理")
            self.console.print(f"     {prefix}命令: bfg --replace-text sensitive.txt .")
        
        if stale_branches:
            self.console.print(f"\n  3. [yellow]陈旧分支清理:[/yellow]")
            self.console.print(f"     {prefix}可删除 {len(stale_branches)} 个陈旧分支")
            local_branches = [b for b in stale_branches if not b['is_remote']]
            remote_branches = [b for b in stale_branches if b['is_remote']]
            if local_branches:
                self.console.print(f"     {prefix}本地: git branch -D {' '.join(b['name'] for b in local_branches[:5])}")
            if remote_branches:
                self.console.print(f"     {prefix}远程: git push origin --delete {' '.join(b['name'].split('/')[-1] for b in remote_branches[:5])}")
        
        if large_files or sensitive_findings:
            self.console.print(f"\n  4. [bold]最后步骤:[/bold]")
            self.console.print(f"     {prefix}git reflog expire --expire=now --all")
            self.console.print(f"     {prefix}git gc --prune=now --aggressive")
    
    def print_exclude_patterns(self, patterns: Dict[str, List[str]]):
        """打印排除模式信息"""
        self.console.print("\n[bold]路径排除规则:[/bold]")
        
        if patterns.get('builtin'):
            self.console.print(f"  [dim]内置排除模式 ({len(patterns['builtin'])} 个):[/dim]")
            for p in patterns['builtin'][:10]:
                self.console.print(f"    - {p}")
            if len(patterns['builtin']) > 10:
                self.console.print(f"    [dim]... 还有 {len(patterns['builtin']) - 10} 个更多[/dim]")
        
        if patterns.get('gitignore'):
            self.console.print(f"\n  [dim].gitignore 排除模式 ({len(patterns['gitignore'])} 个):[/dim]")
            for p in patterns['gitignore'][:10]:
                self.console.print(f"    - {p}")
            if len(patterns['gitignore']) > 10:
                self.console.print(f"    [dim]... 还有 {len(patterns['gitignore']) - 10} 个更多[/dim]")
        
        if not patterns.get('builtin') and not patterns.get('gitignore'):
            self.console.print("  (无排除规则)")
