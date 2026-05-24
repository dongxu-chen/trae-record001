import json
import os
from datetime import datetime
from typing import Dict, List
from tabulate import tabulate
from colorama import Fore, Style, init

init(autoreset=True)


class ReportGenerator:
    SEVERITY_COLORS = {
        "critical": Fore.MAGENTA,
        "high": Fore.RED,
        "medium": Fore.YELLOW,
        "low": Fore.CYAN
    }

    STATUS_COLORS = {
        "pass": Fore.GREEN,
        "fail": Fore.RED,
        "warn": Fore.YELLOW,
        "error": Fore.MAGENTA,
        "skipped": Fore.LIGHTBLACK_EX
    }

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_console_report(self, hostname: str, results: List[Dict], summary: Dict) -> str:
        output = []
        separator = "=" * 80

        output.append(separator)
        output.append(f"{Fore.CYAN}服务器配置基线检查报告{Style.RESET_ALL}")
        output.append(separator)
        output.append(f"目标主机: {Fore.YELLOW}{hostname}{Style.RESET_ALL}")
        output.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(separator)

        output.append(self._format_summary(summary))
        output.append("")

        output.append(f"{Fore.CYAN}详细检查结果:{Style.RESET_ALL}")
        output.append(separator)

        categories = {}
        for result in results:
            cat = result.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)

        for category, cat_results in categories.items():
            output.append(f"\n{Fore.BLUE}[{category.upper()}]{Style.RESET_ALL}")
            table_data = []
            for r in cat_results:
                status_color = self.STATUS_COLORS.get(r["status"], "")
                severity_color = self.SEVERITY_COLORS.get(r["severity"], "")
                status_icon = self._get_status_icon(r["status"])

                table_data.append([
                    f"{severity_color}{r['severity'].upper()}{Style.RESET_ALL}",
                    r["id"],
                    r["name"],
                    f"{status_color}{status_icon} {r['status']}{Style.RESET_ALL}",
                    r["message"][:50] if r["message"] else "-"
                ])

            output.append(tabulate(
                table_data,
                headers=["严重程度", "检查ID", "检查项", "状态", "说明"],
                tablefmt="simple"
            ))

        output.append("")
        output.append(separator)
        output.append(self._format_failed_checks(results))
        output.append(separator)

        return "\n".join(output)

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "pass": "✓",
            "fail": "✗",
            "warn": "⚠",
            "error": "✖",
            "skipped": "→"
        }
        return icons.get(status, "?")

    def _format_summary(self, summary: Dict) -> str:
        output = []
        output.append(f"{Fore.CYAN}检查概要:{Style.RESET_ALL}")

        total = summary["total"]
        pass_rate = (summary["pass"] / total * 100) if total > 0 else 0

        summary_data = [
            ["总检查项", total],
            [f"{Fore.GREEN}通过{Style.RESET_ALL}", summary["pass"]],
            [f"{Fore.RED}失败{Style.RESET_ALL}", summary["fail"]],
            [f"{Fore.YELLOW}警告{Style.RESET_ALL}", summary["warn"]],
            [f"{Fore.MAGENTA}错误{Style.RESET_ALL}", summary["error"]],
            [f"{Fore.CYAN}通过率{Style.RESET_ALL}", f"{pass_rate:.1f}%"]
        ]

        output.append(tabulate(summary_data, tablefmt="simple"))

        output.append(f"\n{Fore.CYAN}按严重程度分类:{Style.RESET_ALL}")
        severity_data = []
        for sev, counts in summary["by_severity"].items():
            if sum(counts.values()) > 0:
                sev_color = self.SEVERITY_COLORS.get(sev, "")
                severity_data.append([
                    f"{sev_color}{sev.upper()}{Style.RESET_ALL}",
                    f"{Fore.GREEN}{counts['pass']}{Style.RESET_ALL}",
                    f"{Fore.RED}{counts['fail']}{Style.RESET_ALL}",
                    f"{Fore.YELLOW}{counts['warn']}{Style.RESET_ALL}",
                    f"{Fore.MAGENTA}{counts['error']}{Style.RESET_ALL}"
                ])

        if severity_data:
            output.append(tabulate(
                severity_data,
                headers=["严重程度", "通过", "失败", "警告", "错误"],
                tablefmt="simple"
            ))

        return "\n".join(output)

    def _format_failed_checks(self, results: List[Dict]) -> str:
        output = []
        failed_checks = [r for r in results if r["status"] in ["fail", "warn", "error"]]

        if not failed_checks:
            output.append(f"{Fore.GREEN}✓ 所有检查项通过！{Style.RESET_ALL}")
            return "\n".join(output)

        output.append(f"{Fore.RED}需要修复的检查项:{Style.RESET_ALL}")
        output.append("")

        failed_checks.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

        for check in failed_checks:
            sev_color = self.SEVERITY_COLORS.get(check["severity"], "")
            status_color = self.STATUS_COLORS.get(check["status"], "")

            output.append(f"{sev_color}[{check['severity'].upper()}]{Style.RESET_ALL} {check['id']} - {check['name']}")
            output.append(f"  {status_color}状态: {check['status']}{Style.RESET_ALL}")
            if check["message"]:
                output.append(f"  说明: {check['message']}")
            output.append(f"  当前值: {check['actual_value']}")
            output.append(f"  期望值: {check['expected_value']}")
            if check["fix_command"]:
                output.append(f"  {Fore.YELLOW}修复命令:{Style.RESET_ALL}")
                output.append(f"    {Fore.LIGHTGREEN_EX}{check['fix_command']}{Style.RESET_ALL}")
            output.append("")

        return "\n".join(output)

    def generate_json_report(self, hostname: str, results: List[Dict], summary: Dict) -> str:
        report = {
            "hostname": hostname,
            "report_time": datetime.now().isoformat(),
            "summary": summary,
            "results": results,
            "fix_commands": self._extract_fix_commands(results)
        }

        filename = f"baseline_report_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return filepath

    def generate_text_report(self, hostname: str, results: List[Dict], summary: Dict) -> str:
        output = []
        separator = "=" * 80

        output.append(separator)
        output.append("服务器配置基线检查报告")
        output.append(separator)
        output.append(f"目标主机: {hostname}")
        output.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(separator)
        output.append("")

        output.append("检查概要:")
        output.append(f"  总检查项: {summary['total']}")
        output.append(f"  通过: {summary['pass']}")
        output.append(f"  失败: {summary['fail']}")
        output.append(f"  警告: {summary['warn']}")
        output.append(f"  错误: {summary['error']}")
        output.append("")

        output.append(separator)
        output.append("详细检查结果:")
        output.append(separator)
        output.append("")

        for result in results:
            output.append(f"[{result['severity'].upper()}] {result['id']} - {result['name']}")
            output.append(f"  类别: {result.get('category', 'other')}")
            output.append(f"  状态: {result['status']}")
            output.append(f"  描述: {result['description']}")
            if result["message"]:
                output.append(f"  说明: {result['message']}")
            output.append(f"  当前值: {result['actual_value']}")
            output.append(f"  期望值: {result['expected_value']}")
            if result["fix_command"]:
                output.append(f"  修复命令: {result['fix_command']}")
            output.append("")

        output.append(separator)
        output.append("修复命令汇总:")
        output.append(separator)
        output.append("")

        failed_checks = [r for r in results if r["status"] == "fail"]
        failed_checks.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

        for check in failed_checks:
            if check["fix_command"]:
                output.append(f"# {check['id']} - {check['name']} ({check['severity']})")
                output.append(check["fix_command"])
                output.append("")

        filename = f"baseline_report_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(output))

        return filepath

    def generate_fix_script(self, hostname: str, results: List[Dict]) -> str:
        failed_checks = [r for r in results if r["status"] == "fail" and r["fix_command"]]
        failed_checks.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))

        script_lines = [
            "#!/bin/bash",
            "#",
            f"# 服务器配置基线修复脚本",
            f"# 目标主机: {hostname}",
            f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "#",
            "# 警告: 请在执行前仔细审查每个命令！",
            "#",
            "",
            "set -e",
            "",
            'echo "开始执行基线修复..."',
            'echo "======================="',
            ""
        ]

        for check in failed_checks:
            script_lines.append(f"# {check['id']} - {check['name']} ({check['severity']})")
            script_lines.append(f"# 说明: {check['message']}")
            script_lines.append(f'echo "执行修复: {check["name"]}"')
            script_lines.append(check["fix_command"])
            script_lines.append('echo "完成"')
            script_lines.append("")

        script_lines.append('echo "======================="')
        script_lines.append('echo "所有修复命令执行完成！"')

        filename = f"fix_script_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(script_lines))

        os.chmod(filepath, 0o755)

        return filepath

    def _extract_fix_commands(self, results: List[Dict]) -> List[Dict]:
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "severity": r["severity"],
                "fix_command": r["fix_command"],
                "message": r["message"]
            }
            for r in results
            if r["status"] == "fail" and r["fix_command"]
        ]
