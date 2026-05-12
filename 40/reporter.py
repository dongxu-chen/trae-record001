#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class GitCleanupReporter:
    def __init__(self, report_dir: str = "reports"):
        self.report_dir = report_dir
        self.reports: Dict[str, List[Dict[str, Any]]] = {}
        self.start_time = datetime.now()

        os.makedirs(report_dir, exist_ok=True)

    def add_repo_report(self, repo_name: str, task_type: str, data: Dict[str, Any]):
        key = f"{repo_name}_{task_type}"
        if key not in self.reports:
            self.reports[key] = []

        report_entry = {
            "timestamp": datetime.now().isoformat(),
            "repo_name": repo_name,
            "task_type": task_type,
            "data": data
        }
        self.reports[key].append(report_entry)

    def add_branch_cleanup_report(self, repo_name: str, local_deleted: int, remote_deleted: int,
                                   skipped_protected: int, skipped_merged: int, dry_run: bool = False):
        data = {
            "local_branches_deleted": local_deleted,
            "remote_branches_deleted": remote_deleted,
            "skipped_protected": skipped_protected,
            "skipped_not_merged": skipped_merged,
            "dry_run": dry_run
        }
        self.add_repo_report(repo_name, "branch_cleanup", data)

    def add_large_files_report(self, repo_name: str, files_found: int, files_deleted: int,
                                total_size_mb: float, dry_run: bool = False):
        data = {
            "large_files_found": files_found,
            "large_files_deleted": files_deleted,
            "total_size_mb": round(total_size_mb, 2),
            "dry_run": dry_run
        }
        self.add_repo_report(repo_name, "large_files", data)

    def add_history_rewrite_report(self, repo_name: str, files_deleted: int, folders_deleted: int,
                                    blobs_stripped: int, text_replaced: int, secrets_redacted: int,
                                    cleanup_executed: bool, push_executed: bool, dry_run: bool = False):
        data = {
            "files_deleted": files_deleted,
            "folders_deleted": folders_deleted,
            "blobs_stripped": blobs_stripped,
            "text_replaced": text_replaced,
            "secrets_redacted": secrets_redacted,
            "cleanup_executed": cleanup_executed,
            "push_executed": push_executed,
            "dry_run": dry_run
        }
        self.add_repo_report(repo_name, "history_rewrite", data)

    def generate_text_report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("Git 仓库清理报告")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        total_stats = {
            "repos_processed": set(),
            "branches_deleted": 0,
            "large_files_deleted": 0,
            "total_size_saved_mb": 0,
            "history_cleanups": 0
        }

        for key, entries in self.reports.items():
            for entry in entries:
                repo_name = entry["repo_name"]
                task_type = entry["task_type"]
                data = entry["data"]

                total_stats["repos_processed"].add(repo_name)

                lines.append(f"仓库: {repo_name}")
                lines.append(f"任务类型: {task_type}")
                lines.append(f"时间: {entry['timestamp']}")
                lines.append("-" * 40)

                if task_type == "branch_cleanup":
                    lines.append(f"  本地分支删除: {data['local_branches_deleted']}")
                    lines.append(f"  远程分支删除: {data['remote_branches_deleted']}")
                    lines.append(f"  跳过受保护分支: {data['skipped_protected']}")
                    lines.append(f"  跳过未合并分支: {data['skipped_not_merged']}")
                    total_stats["branches_deleted"] += data["local_branches_deleted"] + data["remote_branches_deleted"]

                elif task_type == "large_files":
                    lines.append(f"  发现大文件: {data['large_files_found']}")
                    lines.append(f"  删除大文件: {data['large_files_deleted']}")
                    lines.append(f"  释放空间: {data['total_size_mb']} MB")
                    total_stats["large_files_deleted"] += data["large_files_deleted"]
                    total_stats["total_size_saved_mb"] += data["total_size_mb"]

                elif task_type == "history_rewrite":
                    lines.append(f"  删除文件: {data['files_deleted']}")
                    lines.append(f"  删除文件夹: {data['folders_deleted']}")
                    lines.append(f"  清除大对象: {data['blobs_stripped']}")
                    lines.append(f"  文本替换: {data['text_replaced']}")
                    lines.append(f"  脱敏机密: {data['secrets_redacted']}")
                    lines.append(f"  执行清理: {'是' if data['cleanup_executed'] else '否'}")
                    lines.append(f"  推送到远程: {'是' if data['push_executed'] else '否'}")
                    total_stats["history_cleanups"] += 1

                if data.get("dry_run", False):
                    lines.append("  [试运行模式] 未实际执行操作")

                lines.append("")

        lines.append("=" * 60)
        lines.append("汇总统计")
        lines.append("=" * 60)
        lines.append(f"处理的仓库数: {len(total_stats['repos_processed'])}")
        lines.append(f"删除的分支总数: {total_stats['branches_deleted']}")
        lines.append(f"删除的大文件数: {total_stats['large_files_deleted']}")
        lines.append(f"释放的总空间: {round(total_stats['total_size_saved_mb'], 2)} MB")
        lines.append(f"历史重写次数: {total_stats['history_cleanups']}")
        lines.append("")

        return "\n".join(lines)

    def generate_html_report(self) -> str:
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git 仓库清理报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }
        .summary-card { flex: 1; min-width: 200px; background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card .number { font-size: 32px; font-weight: bold; color: #2980b9; }
        .summary-card .label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
        .repo-section { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #3498db; }
        .repo-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }
        .task-type { color: #e74c3c; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #34495e; color: white; }
        tr:hover { background-color: #f1f1f1; }
        .dry-run { background-color: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 10px; color: #856404; }
        .timestamp { font-size: 12px; color: #95a5a6; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #7f8c8d; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Git 仓库清理报告</h1>
        <div class="timestamp">生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</div>
        <div class="timestamp">开始时间: """ + self.start_time.strftime('%Y-%m-%d %H:%M:%S') + """</div>
"""

        total_stats = {
            "repos_processed": set(),
            "branches_deleted": 0,
            "large_files_deleted": 0,
            "total_size_saved_mb": 0,
            "history_cleanups": 0
        }

        for key, entries in self.reports.items():
            for entry in entries:
                repo_name = entry["repo_name"]
                data = entry["data"]
                total_stats["repos_processed"].add(repo_name)

                if entry["task_type"] == "branch_cleanup":
                    total_stats["branches_deleted"] += data["local_branches_deleted"] + data["remote_branches_deleted"]
                elif entry["task_type"] == "large_files":
                    total_stats["large_files_deleted"] += data["large_files_deleted"]
                    total_stats["total_size_saved_mb"] += data["total_size_mb"]
                elif entry["task_type"] == "history_rewrite":
                    total_stats["history_cleanups"] += 1

        html += f"""
        <div class="summary">
            <div class="summary-card">
                <div class="number">{len(total_stats['repos_processed'])}</div>
                <div class="label">处理的仓库数</div>
            </div>
            <div class="summary-card">
                <div class="number">{total_stats['branches_deleted']}</div>
                <div class="label">删除的分支总数</div>
            </div>
            <div class="summary-card">
                <div class="number">{total_stats['large_files_deleted']}</div>
                <div class="label">删除的大文件数</div>
            </div>
            <div class="summary-card">
                <div class="number">{round(total_stats['total_size_saved_mb'], 2)}</div>
                <div class="label">释放空间 (MB)</div>
            </div>
            <div class="summary-card">
                <div class="number">{total_stats['history_cleanups']}</div>
                <div class="label">历史重写次数</div>
            </div>
        </div>
"""

        for key, entries in self.reports.items():
            for entry in entries:
                repo_name = entry["repo_name"]
                task_type = entry["task_type"]
                data = entry["data"]

                task_display = {
                    "branch_cleanup": "分支清理",
                    "large_files": "大文件清理",
                    "history_rewrite": "历史重写"
                }.get(task_type, task_type)

                html += f"""
        <div class="repo-section">
            <div class="repo-title">{repo_name}</div>
            <div><span class="task-type">{task_display}</span> - {entry['timestamp']}</div>
"""

                if task_type == "branch_cleanup":
                    html += f"""
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>本地分支删除</td><td>{data['local_branches_deleted']}</td></tr>
                <tr><td>远程分支删除</td><td>{data['remote_branches_deleted']}</td></tr>
                <tr><td>跳过受保护分支</td><td>{data['skipped_protected']}</td></tr>
                <tr><td>跳过未合并分支</td><td>{data['skipped_not_merged']}</td></tr>
            </table>
"""
                elif task_type == "large_files":
                    html += f"""
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>发现大文件</td><td>{data['large_files_found']}</td></tr>
                <tr><td>删除大文件</td><td>{data['large_files_deleted']}</td></tr>
                <tr><td>释放空间</td><td>{data['total_size_mb']} MB</td></tr>
            </table>
"""
                elif task_type == "history_rewrite":
                    html += f"""
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>删除文件</td><td>{data['files_deleted']}</td></tr>
                <tr><td>删除文件夹</td><td>{data['folders_deleted']}</td></tr>
                <tr><td>清除大对象</td><td>{data['blobs_stripped']}</td></tr>
                <tr><td>文本替换</td><td>{data['text_replaced']}</td></tr>
                <tr><td>脱敏机密</td><td>{data['secrets_redacted']}</td></tr>
                <tr><td>执行清理</td><td>{'是' if data['cleanup_executed'] else '否'}</td></tr>
                <tr><td>推送到远程</td><td>{'是' if data['push_executed'] else '否'}</td></tr>
            </table>
"""

                if data.get("dry_run", False):
                    html += '<div class="dry-run">⚠️ 试运行模式 - 未实际执行操作</div>'

                html += "</div>"

        html += """
        <div class="footer">
            Git 仓库自动清理工具 | 报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>
    </div>
</body>
</html>
"""
        return html

    def save_report(self, format: str = "both") -> Dict[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}

        if format in ["text", "both"]:
            text_report = self.generate_text_report()
            text_path = os.path.join(self.report_dir, f"cleanup_report_{timestamp}.txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text_report)
            saved_files["text"] = text_path

        if format in ["html", "both"]:
            html_report = self.generate_html_report()
            html_path = os.path.join(self.report_dir, f"cleanup_report_{timestamp}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_report)
            saved_files["html"] = html_path

        return saved_files

    def get_summary(self) -> Dict[str, Any]:
        total_stats = {
            "repos_processed": set(),
            "branches_deleted": 0,
            "large_files_deleted": 0,
            "total_size_saved_mb": 0,
            "history_cleanups": 0,
            "total_operations": 0
        }

        for key, entries in self.reports.items():
            for entry in entries:
                repo_name = entry["repo_name"]
                data = entry["data"]
                total_stats["repos_processed"].add(repo_name)
                total_stats["total_operations"] += 1

                if entry["task_type"] == "branch_cleanup":
                    total_stats["branches_deleted"] += data["local_branches_deleted"] + data["remote_branches_deleted"]
                elif entry["task_type"] == "large_files":
                    total_stats["large_files_deleted"] += data["large_files_deleted"]
                    total_stats["total_size_saved_mb"] += data["total_size_mb"]
                elif entry["task_type"] == "history_rewrite":
                    total_stats["history_cleanups"] += 1

        total_stats["repos_processed"] = len(total_stats["repos_processed"])
        total_stats["total_size_saved_mb"] = round(total_stats["total_size_saved_mb"], 2)

        return total_stats
