#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.scan_manager import ScanManager
from backend.reports.report_generator import ReportGenerator

class SecurityScannerCLI:
    def __init__(self):
        self.scan_manager = ScanManager()
        self.report_generator = ReportGenerator()

    async def scan(self, args):
        print(f"🚀 开始扫描镜像: {', '.join(args.images)}")
        print(f"📋 扫描类型: {', '.join(args.scan_types)}")
        
        job_id = await self.scan_manager.create_scan_job(
            image_names=args.images,
            scan_types=args.scan_types
        )
        
        print(f"🔖 任务ID: {job_id}")
        
        if args.wait:
            await self._wait_for_completion(job_id, args)
        else:
            print(f"💡 任务已提交，使用以下命令查看状态:")
            print(f"   python cli/scanner_cli.py status {job_id}")

    async def _wait_for_completion(self, job_id: str, args):
        while True:
            status = self.scan_manager.get_job_status(job_id)
            if not status:
                print("❌ 任务不存在")
                return
            
            progress = status.get("progress", {})
            print(f"\r⏳ 状态: {status['status']:10} | "
                  f"进度: {progress.get('percentage', 0)}% "
                  f"({progress.get('completed_images', 0)}/{progress.get('total_images', 0)})",
                  end="", flush=True)
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                print()
                break
            
            await asyncio.sleep(2)
        
        results = self.scan_manager.get_job_results(job_id)
        if results:
            self._print_summary(results)
            
            report_formats = []
            if args.output_json:
                report_formats.append("json")
            if args.output_html:
                report_formats.append("html")
            if args.output_junit:
                report_formats.append("junit")
            
            if not report_formats and args.output_all:
                report_formats = ["json", "html", "junit"]
            
            for fmt in report_formats:
                if fmt == "json":
                    path = self.report_generator.generate_json_report(results)
                    print(f"📄 JSON报告已保存: {path}")
                elif fmt == "html":
                    path = self.report_generator.generate_html_report(results)
                    print(f"📄 HTML报告已保存: {path}")
                elif fmt == "junit":
                    path = self.report_generator.generate_junit_report(results)
                    print(f"📄 JUnit报告已保存: {path}")
            
            if args.fail_on_risk:
                risk_score = self._get_avg_risk_score(results)
                if risk_score >= args.fail_on_risk:
                    print(f"❌ 风险分数 {risk_score} 超过阈值 {args.fail_on_risk}，退出码: 1")
                    sys.exit(1)
            
            if args.fail_on_severity:
                has_failure = self._check_severity_threshold(results, args.fail_on_severity)
                if has_failure:
                    print(f"❌ 发现 {args.fail_on_severity} 及以上严重程度的问题，退出码: 1")
                    sys.exit(1)

    def _check_severity_threshold(self, results: dict, threshold: str) -> bool:
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        threshold_level = severity_order.get(threshold.upper(), 2)
        
        for image_name, image_result in results.get("results", {}).items():
            if "vulnerabilities" in image_result and isinstance(image_result["vulnerabilities"], dict):
                by_sev = image_result["vulnerabilities"].get("summary", {}).get("by_severity", {})
                for sev, count in by_sev.items():
                    if severity_order.get(sev, 0) >= threshold_level and count > 0:
                        return True
            
            if "secrets" in image_result and isinstance(image_result["secrets"], dict):
                by_sev = image_result["secrets"].get("summary", {}).get("by_severity", {})
                for sev, count in by_sev.items():
                    if severity_order.get(sev, 0) >= threshold_level and count > 0:
                        return True
        
        return False

    def _print_summary(self, results: dict):
        print("\n" + "="*60)
        print("📊 扫描结果摘要")
        print("="*60)
        
        for image_name, image_result in results.get("results", {}).items():
            if "error" in image_result:
                print(f"\n❌ {image_name}: {image_result['error']}")
                continue
            
            risk_score = image_result.get("overall_risk_score", 0)
            risk_level = self._get_risk_level(risk_score)
            
            print(f"\n📦 {image_name}")
            print(f"   风险分数: {risk_score} ({risk_level})")
            
            if "vulnerabilities" in image_result and image_result["vulnerabilities"]:
                vuln_summary = image_result["vulnerabilities"].get("summary", {})
                by_sev = vuln_summary.get("by_severity", {})
                print(f"   漏洞: C={by_sev.get('CRITICAL', 0)}, "
                      f"H={by_sev.get('HIGH', 0)}, "
                      f"M={by_sev.get('MEDIUM', 0)}, "
                      f"L={by_sev.get('LOW', 0)}")
            
            if "secrets" in image_result and image_result["secrets"]:
                secrets_summary = image_result["secrets"].get("summary", {})
                print(f"   敏感信息: {secrets_summary.get('total_findings', 0)} 个发现")
                by_type = secrets_summary.get("by_detection_type", {})
                if by_type:
                    type_str = ", ".join([f"{k}={v}" for k, v in by_type.items()])
                    print(f"   检测类型: {type_str}")
            
            if "rules" in image_result and image_result["rules"]:
                rules_summary = image_result["rules"].get("summary", {})
                print(f"   规则检查: {rules_summary.get('passed', 0)}/{rules_summary.get('total_rules', 0)} 通过")

    def _get_risk_level(self, score: float) -> str:
        if score >= 70:
            return "严重"
        elif score >= 50:
            return "高"
        elif score >= 30:
            return "中"
        elif score > 0:
            return "低"
        else:
            return "安全"

    def _get_avg_risk_score(self, results: dict) -> float:
        total = 0
        count = 0
        for image_result in results.get("results", {}).values():
            if "overall_risk_score" in image_result:
                total += image_result["overall_risk_score"]
                count += 1
        return total / count if count > 0 else 0

    def status(self, args):
        status = self.scan_manager.get_job_status(args.job_id)
        if not status:
            print("❌ 任务不存在")
            return
        
        print(f"📋 任务状态: {status['job_id']}")
        print(f"   状态: {status['status']}")
        print(f"   创建时间: {status['created_at']}")
        if status['started_at']:
            print(f"   开始时间: {status['started_at']}")
        if status['completed_at']:
            print(f"   完成时间: {status['completed_at']}")
        
        progress = status.get("progress", {})
        print(f"   进度: {progress.get('percentage', 0)}% "
              f"({progress.get('completed_images', 0)}/{progress.get('total_images', 0)} 镜像)")
        
        if status.get('errors'):
            print(f"   错误: {status['errors']}")

    def results(self, args):
        results = self.scan_manager.get_job_results(args.job_id)
        if not results:
            print("❌ 任务不存在")
            return
        
        if args.format == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif args.format == "junit":
            filepath = self.report_generator.generate_junit_report(results)
            with open(filepath, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            self._print_summary(results)

    def list_jobs(self, args):
        jobs = self.scan_manager.list_jobs(args.limit)
        print(f"📋 最近 {len(jobs)} 个任务:\n")
        
        for job in jobs:
            status_icon = {
                "completed": "✅",
                "running": "⏳",
                "pending": "📋",
                "failed": "❌",
                "cancelled": "🚫"
            }.get(job["status"], "❓")
            
            print(f"{status_icon} {job['job_id']}")
            print(f"   镜像: {', '.join(job['image_names'][:2])}"
                  f"{'...' if len(job['image_names']) > 2 else ''}")
            print(f"   状态: {job['status']}")
            print(f"   创建时间: {job['created_at']}")
            print()

    def list_reports(self, args):
        reports = self.report_generator.get_report_list()
        print(f"📄 报告列表 ({len(reports)}):\n")
        
        for report in reports:
            size_mb = report["size"] / (1024 * 1024)
            print(f"   {report['filename']} ({report['type']}, {size_mb:.2f} MB)")
            print(f"   创建时间: {report['created_at']}\n")

    async def db_status(self, args):
        status = await self.scan_manager.get_trivy_db_status()
        update_status = status.get("update_status", {})
        integrity = status.get("integrity", {})
        
        print("🔍 Trivy 漏洞库状态:")
        print(f"   自动更新: {'已启用' if update_status.get('auto_update_enabled') else '已禁用'}")
        print(f"   更新间隔: {update_status.get('update_interval_hours')} 小时")
        print(f"   上次更新: {update_status.get('last_update') or '未知'}")
        print(f"   下次更新: {update_status.get('next_update') or '未知'}")
        print(f"   版本: {update_status.get('version') or '未知'}")
        print(f"   需要更新: {'是' if update_status.get('needs_update') else '否'}")
        print(f"   更新运行中: {'是' if update_status.get('update_running') else '否'}")
        print()
        print("📦 数据库完整性:")
        print(f"   数据库存在: {'是' if integrity.get('db_exists') else '否'}")
        print(f"   数据库大小: {integrity.get('db_size', 0) / (1024*1024):.2f} MB")
        print(f"   完整性检查: {'通过' if integrity.get('valid') else '失败'}")
        if integrity.get('error'):
            print(f"   错误: {integrity.get('error')}")

    async def db_update(self, args):
        print("🔄 正在更新 Trivy 漏洞库...")
        if args.force:
            print("   (强制更新模式)")
        
        result = await self.scan_manager.update_trivy_db(force=args.force)
        
        if result.get("success"):
            print(f"✅ 更新成功!")
            print(f"   版本: {result.get('version')}")
            print(f"   完成时间: {result.get('last_update')}")
            print(f"   下次更新: {result.get('next_update')}")
        else:
            print(f"❌ 更新失败: {result.get('error')}")
            sys.exit(1)

    async def db_start_auto(self, args):
        await self.scan_manager.start_db_auto_update()
        print("✅ Trivy 漏洞库自动更新已启动")

    async def db_stop_auto(self, args):
        await self.scan_manager.stop_db_auto_update()
        print("✅ Trivy 漏洞库自动更新已停止")

    async def db_export(self, args):
        print(f"📦 正在导出离线漏洞库到: {args.path}")
        result = await self.scan_manager.export_trivy_db(args.path)
        
        if result.get("success"):
            size_mb = result.get("size", 0) / (1024 * 1024)
            print(f"✅ 导出成功!")
            print(f"   文件: {result.get('export_path')}")
            print(f"   大小: {size_mb:.2f} MB")
        else:
            print(f"❌ 导出失败: {result.get('error')}")
            sys.exit(1)

    async def db_import(self, args):
        print(f"📦 正在从离线包导入漏洞库: {args.path}")
        result = await self.scan_manager.import_trivy_db(args.path)
        
        if result.get("success"):
            print(f"✅ 导入成功!")
        else:
            print(f"❌ 导入失败: {result.get('error')}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Docker镜像安全扫描工具 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描单个镜像
  python cli/scanner_cli.py scan --images nginx:latest --wait
  
  # 扫描多个镜像并生成所有报告
  python cli/scanner_cli.py scan --images nginx:latest alpine:3.18 --wait --output-all
  
  # 生成JUnit报告用于CI
  python cli/scanner_cli.py scan --images myapp:latest --wait --output-junit
  
  # CI集成: 风险分数超过50则失败
  python cli/scanner_cli.py scan --images myapp:latest --wait --fail-on-risk 50
  
  # CI集成: 发现HIGH及以上漏洞则失败
  python cli/scanner_cli.py scan --images myapp:latest --wait --fail-on-severity HIGH
  
  # 漏洞库管理
  python cli/scanner_cli.py db status
  python cli/scanner_cli.py db update --force
  python cli/scanner_cli.py db export --path /tmp/trivy-db
  python cli/scanner_cli.py db import --path /tmp/trivy-db/trivy-db-20240101.tar.gz
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    scan_parser = subparsers.add_parser("scan", help="创建扫描任务")
    scan_parser.add_argument("--images", nargs="+", required=True, help="要扫描的镜像列表")
    scan_parser.add_argument("--scan-types", nargs="+", 
                           default=["vulnerabilities", "secrets", "rules"],
                           help="扫描类型")
    scan_parser.add_argument("--wait", action="store_true", help="等待扫描完成")
    scan_parser.add_argument("--output-json", action="store_true", help="输出JSON报告")
    scan_parser.add_argument("--output-html", action="store_true", help="输出HTML报告")
    scan_parser.add_argument("--output-junit", action="store_true", help="输出JUnit XML报告")
    scan_parser.add_argument("--output-all", action="store_true", help="输出所有格式报告")
    scan_parser.add_argument("--fail-on-risk", type=int, default=None,
                           help="风险分数超过此值时退出码为1 (CI集成用)")
    scan_parser.add_argument("--fail-on-severity", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                           default=None, help="发现此严重程度及以上的问题时退出码为1")
    
    status_parser = subparsers.add_parser("status", help="查看任务状态")
    status_parser.add_argument("job_id", help="任务ID")
    
    results_parser = subparsers.add_parser("results", help="查看任务结果")
    results_parser.add_argument("job_id", help="任务ID")
    results_parser.add_argument("--format", choices=["text", "json", "junit"], default="text")
    
    list_parser = subparsers.add_parser("list", help="列出所有任务")
    list_parser.add_argument("--limit", type=int, default=20, help="显示数量")
    
    reports_parser = subparsers.add_parser("reports", help="列出所有报告")
    
    db_parser = subparsers.add_parser("db", help="漏洞库管理")
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="漏洞库命令")
    
    db_status_parser = db_subparsers.add_parser("status", help="查看漏洞库状态")
    
    db_update_parser = db_subparsers.add_parser("update", help="更新漏洞库")
    db_update_parser.add_argument("--force", action="store_true", help="强制更新")
    
    db_subparsers.add_parser("start-auto", help="启动自动更新")
    db_subparsers.add_parser("stop-auto", help="停止自动更新")
    
    db_export_parser = db_subparsers.add_parser("export", help="导出离线漏洞库")
    db_export_parser.add_argument("--path", required=True, help="导出路径")
    
    db_import_parser = db_subparsers.add_parser("import", help="导入离线漏洞库")
    db_import_parser.add_argument("--path", required=True, help="离线包路径")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = SecurityScannerCLI()
    
    if args.command == "scan":
        asyncio.run(cli.scan(args))
    elif args.command == "status":
        cli.status(args)
    elif args.command == "results":
        cli.results(args)
    elif args.command == "list":
        cli.list_jobs(args)
    elif args.command == "reports":
        cli.list_reports(args)
    elif args.command == "db":
        if args.db_command == "status":
            asyncio.run(cli.db_status(args))
        elif args.db_command == "update":
            asyncio.run(cli.db_update(args))
        elif args.db_command == "start-auto":
            asyncio.run(cli.db_start_auto(args))
        elif args.db_command == "stop-auto":
            asyncio.run(cli.db_stop_auto(args))
        elif args.db_command == "export":
            asyncio.run(cli.db_export(args))
        elif args.db_command == "import":
            asyncio.run(cli.db_import(args))
        else:
            db_parser.print_help()

if __name__ == "__main__":
    main()
