#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import sys
import yaml
from typing import List, Dict
from datetime import datetime

from baseline_checker.ssh_client import SSHClient
from baseline_checker.check_engine import CheckEngine
from baseline_checker.report_generator import ReportGenerator
from baseline_checker.ansible_runner import AnsibleRunner
from baseline_checker.data_store import DataStore
from baseline_checker.auto_fix import AutoFix
from baseline_checker.trend_analyzer import TrendAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/baseline_checker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

data_store = DataStore()


def load_hosts_config(config_path: str) -> List[Dict]:
    if not os.path.exists(config_path):
        logger.error(f"Hosts config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("hosts", [])


def check_single_host(host: Dict, baseline_template: str, categories: List[str] = None,
                      output_formats: List[str] = None, auto_fix: bool = False,
                      save_scan: bool = True) -> Dict:
    hostname = host.get("hostname")
    port = host.get("port", 22)
    username = host.get("username", "root")
    password = host.get("password")
    key_file = host.get("key_file")

    logger.info(f"Connecting to {hostname}:{port} as {username}...")

    ssh_client = SSHClient(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        key_file=key_file
    )

    if not ssh_client.connect():
        logger.error(f"Failed to connect to {hostname}")
        return {
            "hostname": hostname,
            "success": False,
            "error": "Connection failed"
        }

    try:
        logger.info(f"Running baseline checks on {hostname}...")
        engine = CheckEngine(ssh_client, baseline_template)
        results = engine.run_all_checks(categories=categories)
        summary = engine.get_summary()

        report_generator = ReportGenerator(output_dir="baseline_checker/reports")

        console_report = report_generator.generate_console_report(hostname, results, summary)
        print(console_report)

        output_files = {}
        if output_formats:
            if "json" in output_formats:
                output_files["json"] = report_generator.generate_json_report(hostname, results, summary)
            if "text" in output_formats:
                output_files["text"] = report_generator.generate_text_report(hostname, results, summary)
            if "script" in output_formats:
                output_files["fix_script"] = report_generator.generate_fix_script(hostname, results)
            if "html" in output_formats:
                output_files["html"] = report_generator.generate_html_report(hostname, results, summary)

        for fmt, filepath in output_files.items():
            logger.info(f"Generated {fmt} report: {filepath}")

        if save_scan:
            template_name = os.path.basename(baseline_template)
            data_store.save_scan_result(hostname, results, summary, template_name)

        fix_results = None
        if auto_fix:
            from colorama import Fore, Style, init
            init()
            
            print(f"\n{Fore.YELLOW}=== 自动修复模式 ==={Style.RESET_ALL}")
            auto_fixer = AutoFix(ssh_client, data_store)
            preview = auto_fixer.generate_fix_preview(results)
            
            print(f"可自动修复项: {preview['auto_fixable']} / {preview['total_failed']}")
            for sev, count in preview["by_severity"].items():
                print(f"  {sev}: {count}")
            
            if preview["auto_fixable"] > 0:
                print(f"\n{Fore.CYAN}以下项将自动修复:{Style.RESET_ALL}")
                for fix in preview["fixes"]:
                    print(f"  [{fix['severity']}] {fix['id']} - {fix['name']}")
                    print(f"    命令: {fix['fix_command']}")
                
                confirm = input(f"\n{Fore.YELLOW}确认执行以上修复? (yes/no): {Style.RESET_ALL}")
                if confirm.lower() == "yes":
                    print(f"\n{Fore.CYAN}正在执行修复...{Style.RESET_ALL}")
                    executed, skipped = auto_fixer.fix_all(results)
                    
                    print(f"\n{Fore.GREEN}修复完成:{Style.RESET_ALL}")
                    print(f"  成功: {len(executed)}")
                    print(f"  跳过/失败: {len(skipped)}")
                    
                    fix_results = {"executed": executed, "skipped": skipped}
                    
                    print(f"\n{Fore.CYAN}正在验证修复结果...{Style.RESET_ALL}")
                    verification = auto_fixer.verify_fixes(engine, results)
                    
                    fixed_count = sum(1 for v in verification if v["fixed"])
                    print(f"  验证通过: {fixed_count} / {len(verification)}")
                    
                    for v in verification:
                        status = f"{Fore.GREEN}✓ 已修复{Style.RESET_ALL}" if v["fixed"] else f"{Fore.RED}✗ 未修复{Style.RESET_ALL}"
                        print(f"    {v['check_id']} - {v['check_name']}: {status}")
                else:
                    print("已取消自动修复")
            else:
                print("没有可自动修复的项")

        return {
            "hostname": hostname,
            "success": True,
            "summary": summary,
            "results": results,
            "output_files": output_files,
            "fix_results": fix_results
        }

    finally:
        ssh_client.close()


def run_ansible_checks(hosts: List[Dict], baseline_template: str):
    logger.info("Running checks via Ansible...")

    with open(baseline_template, "r", encoding="utf-8") as f:
        baseline = yaml.safe_load(f)

    all_checks = []
    for category_checks in baseline.get("checks", {}).values():
        all_checks.extend(category_checks)

    runner = AnsibleRunner()
    inventory_path = runner.generate_inventory(hosts)
    playbook_path = runner.generate_playbook(all_checks, output_dir="baseline_checker/reports")

    logger.info(f"Generated inventory: {inventory_path}")
    logger.info(f"Generated playbook: {playbook_path}")

    result = runner.run_playbook(playbook_path, inventory_path)

    if result["success"]:
        logger.info("Ansible playbook executed successfully")
        print(result["stdout"])
    else:
        logger.error(f"Ansible playbook failed: {result['stderr']}")

    return result


def list_baseline_templates(templates_dir: str):
    if not os.path.exists(templates_dir):
        logger.error(f"Templates directory not found: {templates_dir}")
        return

    templates = [f for f in os.listdir(templates_dir) if f.endswith((".yaml", ".yml"))]

    if not templates:
        print("No baseline templates found.")
        return

    print("Available baseline templates:")
    for template in templates:
        template_path = os.path.join(templates_dir, template)
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                name = data.get("name", template)
                version = data.get("version", "unknown")
                description = data.get("description", "")
                checks_count = sum(len(v) for v in data.get("checks", {}).values())
                print(f"  - {template}: {name} (v{version}) - {checks_count} checks")
                if description:
                    print(f"      {description}")
        except Exception as e:
            print(f"  - {template}: (error loading: {e})")


def show_baseline_versions(template_name: str):
    versions = data_store.get_baseline_versions(template_name)
    
    if not versions:
        print(f"No versions found for template: {template_name}")
        return
    
    print(f"版本历史: {template_name}")
    print("=" * 80)
    for v in versions:
        print(f"  版本: {v['version']}")
        print(f"  时间: {v['timestamp']}")
        print(f"  描述: {v['description']}")
        print("-" * 80)


def rollback_baseline(template_name: str, version: str, templates_dir: str):
    target_path = os.path.join(templates_dir, template_name)
    success = data_store.rollback_baseline(template_name, version, target_path)
    
    if success:
        print(f"✓ 成功回滚 {template_name} 到版本 {version}")
    else:
        print(f"✗ 回滚失败，版本 {version} 不存在")


def save_baseline_version(template_path: str, version: str, description: str):
    saved_path = data_store.save_baseline_version(template_path, version, description)
    print(f"✓ 已保存版本 {version} 到 {saved_path}")


def show_trend_analysis(hostname: str = None, days: int = 30, output_html: str = None):
    analyzer = TrendAnalyzer(data_store)
    
    if output_html:
        html = analyzer.generate_html_report(hostname, days)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ HTML趋势报告已生成: {output_html}")
    else:
        analyzer.print_text_report(hostname, days)


def show_scan_history(hostname: str = None, limit: int = 10):
    history = data_store.get_scan_history(hostname=hostname, limit=limit)
    
    if not history:
        print("没有找到扫描历史记录")
        return
    
    print("=" * 80)
    print(f"扫描历史记录 (最近 {len(history)} 条)")
    print("=" * 80)
    print(f"{'时间':25s} {'主机':20s} {'模板':25s} {'合规率':>10s} {'状态':>10s}")
    print("-" * 80)
    
    for h in history:
        summary = h.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("pass", 0)
        rate = (passed / total * 100) if total > 0 else 0
        
        template = h.get("template", "")
        if len(template) > 24:
            template = template[:21] + "..."
        
        print(f"{h['timestamp'][:19]:25s} {h['hostname']:20s} {template:25s} {rate:>9.1f}% "
              f"P:{summary.get('pass',0):3d} F:{summary.get('fail',0):3d} W:{summary.get('warn',0):3d}")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="服务器配置基线检查工具 - 扫描Linux服务器安全配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 检查单台服务器
  python main.py --host 192.168.1.100 --username root --password secret

  # 使用密钥文件认证
  python main.py --host 192.168.1.100 --username root --key-file ~/.ssh/id_rsa

  # 使用主机配置文件批量检查
  python main.py --hosts-config hosts.yaml

  # 指定基线模板
  python main.py --hosts-config hosts.yaml --template minimal_baseline.yaml

  # 只检查特定类别
  python main.py --hosts-config hosts.yaml --categories ssh,kernel

  # 生成多种格式报告
  python main.py --hosts-config hosts.yaml --output json,text,script,html

  # 使用Ansible批量检查
  python main.py --hosts-config hosts.yaml --ansible

  # 列出可用基线模板
  python main.py --list-templates

  # 启用自动修复
  python main.py --host 192.168.1.100 --auto-fix

  # 查看趋势分析
  python main.py --trend --hostname 192.168.1.100 --days 30

  # 查看扫描历史
  python main.py --history --hostname 192.168.1.100 --limit 20

  # 基线版本管理
  python main.py --save-version default_baseline.yaml --version v2.1 --desc "添加新检查项"
  python main.py --list-versions default_baseline.yaml
  python main.py --rollback default_baseline.yaml --version v2.0
        """
    )

    parser.add_argument("--host", help="目标服务器主机名/IP")
    parser.add_argument("--port", type=int, default=22, help="SSH端口 (默认: 22)")
    parser.add_argument("--username", default="root", help="SSH用户名 (默认: root)")
    parser.add_argument("--password", help="SSH密码")
    parser.add_argument("--key-file", help="SSH私钥文件路径")

    parser.add_argument("--hosts-config", default="hosts.yaml",
                        help="主机配置文件路径 (默认: hosts.yaml)")

    parser.add_argument("--template", default="default_baseline.yaml",
                        help="基线模板文件名 (默认: default_baseline.yaml)")

    parser.add_argument("--categories",
                        help="指定检查类别，逗号分隔 (如: ssh,kernel,files)")

    parser.add_argument("--output", default="text,script",
                        help="输出报告格式，逗号分隔: json,text,script,html (默认: text,script)")

    parser.add_argument("--ansible", action="store_true",
                        help="使用Ansible模式批量检查")

    parser.add_argument("--list-templates", action="store_true",
                        help="列出可用的基线模板")

    parser.add_argument("--auto-fix", action="store_true",
                        help="启用自动修复模式")

    parser.add_argument("--no-save", action="store_true",
                        help="不保存扫描结果到历史记录")

    parser.add_argument("--trend", action="store_true",
                        help="显示趋势分析报告")
    parser.add_argument("--trend-html", help="输出HTML趋势报告到指定文件")

    parser.add_argument("--history", action="store_true",
                        help="显示扫描历史记录")
    parser.add_argument("--limit", type=int, default=10,
                        help="历史记录显示数量 (默认: 10)")

    parser.add_argument("--save-version", help="保存当前基线模板为新版本")
    parser.add_argument("--version", help="版本号 (用于保存或回滚)")
    parser.add_argument("--version-desc", default="", help="版本描述")
    parser.add_argument("--list-versions", help="列出指定模板的版本历史")
    parser.add_argument("--rollback", help="回滚指定模板到指定版本")

    parser.add_argument("--verbose", "-v", action="store_true",
                        help="启用详细日志输出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    templates_dir = os.path.join(os.path.dirname(__file__), "baseline_checker", "templates")

    if args.list_templates:
        list_baseline_templates(templates_dir)
        return

    if args.list_versions:
        show_baseline_versions(args.list_versions)
        return

    if args.save_version:
        template_path = os.path.join(templates_dir, args.save_version)
        if not os.path.exists(template_path):
            logger.error(f"Template not found: {template_path}")
            sys.exit(1)
        if not args.version:
            logger.error("Please specify --version")
            sys.exit(1)
        save_baseline_version(template_path, args.version, args.version_desc)
        return

    if args.rollback:
        if not args.version:
            logger.error("Please specify --version for rollback")
            sys.exit(1)
        rollback_baseline(args.rollback, args.version, templates_dir)
        return

    if args.trend or args.trend_html:
        show_trend_analysis(
            hostname=args.host,
            days=args.limit if args.limit != 10 else 30,
            output_html=args.trend_html
        )
        return

    if args.history:
        show_scan_history(hostname=args.host, limit=args.limit)
        return

    baseline_template = os.path.join(templates_dir, args.template)
    if not os.path.exists(baseline_template):
        logger.error(f"Baseline template not found: {baseline_template}")
        sys.exit(1)

    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]

    output_formats = [f.strip() for f in args.output.split(",")]

    if args.host:
        host = {
            "hostname": args.host,
            "port": args.port,
            "username": args.username,
            "password": args.password,
            "key_file": args.key_file
        }
        hosts = [host]
    else:
        hosts = load_hosts_config(args.hosts_config)

    if not hosts:
        logger.error("No hosts specified for checking")
        sys.exit(1)

    logger.info(f"Starting baseline check for {len(hosts)} host(s)...")

    results = []
    if args.ansible:
        result = run_ansible_checks(hosts, baseline_template)
        results.append({"ansible_result": result})
    else:
        for host in hosts:
            result = check_single_host(
                host,
                baseline_template,
                categories=categories,
                output_formats=output_formats,
                auto_fix=args.auto_fix,
                save_scan=not args.no_save
            )
            results.append(result)

    failed_hosts = [r for r in results if not r.get("success", True)]
    if failed_hosts:
        logger.warning(f"Failed to check {len(failed_hosts)} host(s)")
        sys.exit(1)

    logger.info("Baseline check completed successfully!")


if __name__ == "__main__":
    main()
