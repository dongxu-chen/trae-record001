#!/usr/bin/env python3
"""
Terraform IaC 云成本管理工具 - 统一入口
整合 tfstate 分析、CI/CD 集成、可视化报告、多云成本分析
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analyzers.tfstate_analyzer import TfstateAnalyzer
from analyzers.multi_cloud_adapter import MultiCloudCostAnalyzer
from reporters.visual_report import VisualReportGenerator
from ci.infracost_check import InfracostChecker
from datetime import datetime, timedelta


def analyze_tfstate(args):
    """分析 Terraform 状态文件"""
    print(f"🔍 Analyzing Terraform state: {args.state}")
    print()
    
    analyzer = TfstateAnalyzer(args.state)
    analyzer.analyze()
    
    summary = analyzer.get_summary()
    
    print("=" * 60)
    print("📊 TFSTATE COST ANALYSIS")
    print("=" * 60)
    print(f"\n📁 Resources: {summary['total_resources']}")
    print(f"💰 Monthly Cost: ${summary['total_monthly_cost']:.2f}")
    print(f"📅 Annual Cost: ${summary['total_annual_cost']:.2f}")
    
    print(f"\n🏢 Cost by Provider:")
    for provider, cost in sorted(summary['cost_by_provider'].items(), key=lambda x: -x[1]):
        if cost > 0:
            print(f"   {provider.upper()}: ${cost:.2f}")
    
    print(f"\n📦 Top Resource Types:")
    for rtype, cost in sorted(summary['cost_by_resource_type'].items(), key=lambda x: -x[1])[:8]:
        if cost > 0:
            print(f"   {rtype}: ${cost:.2f}")
    
    print(f"\n🌍 Cost by Region:")
    for region, cost in sorted(summary['cost_by_region'].items(), key=lambda x: -x[1])[:5]:
        if cost > 0:
            print(f"   {region}: ${cost:.2f}")
    
    print(f"\n🏷️  Tag Compliance:")
    print(f"   Untagged/Incomplete Tags: {summary['resources_without_tags']} resources")
    
    if args.output_json:
        analyzer.export_json(args.output_json)
        print(f"\n💾 Detailed JSON exported to: {args.output_json}")
    
    if args.html_report:
        report_data = {
            'summary': summary,
            'resources': [r.__dict__ for r in analyzer.resources],
        }
        generator = VisualReportGenerator(report_data)
        generator.save(args.html_report)
        print(f"📊 HTML Visual report saved to: {args.html_report}")
    
    print()
    print("✅ Analysis complete!")


def analyze_cloud_costs(args):
    """分析多云实际账单成本"""
    print(f"☁️  Analyzing cloud billing data...")
    print()
    
    if args.start_date and args.end_date:
        start_date = datetime.fromisoformat(args.start_date)
        end_date = datetime.fromisoformat(args.end_date)
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    
    print(f"📅 Period: {start_date.date()} to {end_date.date()}")
    print()
    
    analyzer = MultiCloudCostAnalyzer(
        providers=args.providers,
        aws_region=args.aws_region,
        azure_subscription_id=args.azure_subscription,
        gcp_project_id=args.gcp_project
    )
    
    available = analyzer.get_available_providers()
    if not available:
        print("❌ No cloud providers available. Check your credentials.")
        return
    
    print(f"✅ Available providers: {', '.join(available).upper()}")
    print()
    
    report = analyzer.generate_report(start_date, end_date)
    
    print("=" * 60)
    print("💰 MULTI-CLOUD COST SUMMARY")
    print("=" * 60)
    print(f"\nTotal Cost: ${report['total_cost']['total']:.2f}")
    
    print("\nBy Provider:")
    for provider, cost in report['cost_by_provider'].items():
        print(f"   {provider.upper()}: ${cost:.2f}")
    
    print("\nTop Services:")
    for service, cost in list(report['top_services'].items())[:10]:
        if cost > 0:
            print(f"   {service}: ${cost:.2f}")
    
    if args.output:
        import json
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Report saved to: {args.output}")


def ci_diff_check(args):
    """CI/CD 成本变更检查"""
    print(f"🔄 Running Infracost diff check...")
    print()
    
    checker = InfracostChecker(
        threshold_percent=args.threshold_percent,
        threshold_amount=args.threshold_amount
    )
    
    if args.base_path and args.path:
        print(f"Comparing: {args.base_path} vs {args.path}")
        diff = checker.run_diff(args.base_path, args.path)
        changes = checker.parse_cost_changes(diff)
    else:
        print(f"Analyzing: {args.path}")
        breakdown = checker.run_infracost(args.path)
        diff = {'projects': [{'breakdown': breakdown}]}
        changes = []
    
    summary = checker.get_summary()
    
    print()
    print("=" * 60)
    print("📈 COST CHANGE SUMMARY")
    print("=" * 60)
    print(f"\nMonthly Cost Change: ${summary['total_change_monthly']:+.2f} ({summary['change_percent']:+.1f}%)")
    print(f"Resources Changed: {summary['total_resources_changed']}")
    print(f"  - Added: {summary['resources_added']}")
    print(f"  - Removed: {summary['resources_removed']}")
    print(f"  - Modified: {summary['resources_modified']}")
    
    if summary['significant_increases']:
        print(f"\n⚠️  Significant Cost Increases ({len(summary['significant_increases'])}):")
        for change in summary['significant_increases'][:5]:
            print(f"   {change.resource_address}: +${change.change_monthly:.2f}")
    
    if summary['significant_decreases']:
        print(f"\n✅ Significant Cost Decreases ({len(summary['significant_decreases'])}):")
        for change in summary['significant_decreases'][:5]:
            print(f"   {change.resource_address}: ${change.change_monthly:.2f}")
    
    if args.block_merge:
        should_block, reason = checker.check_should_block_merge()
        print(f"\n🚦 Merge Check: {'BLOCKED' if should_block else 'ALLOWED'}")
        print(f"   Reason: {reason}")
        if should_block:
            sys.exit(1)
    
    if args.output:
        checker.save_report(args.output)
        print(f"\n💾 Report saved to: {args.output}")


def generate_visual_report(args):
    """生成可视化成本报告"""
    print(f"📊 Generating visual report...")
    print()
    
    if args.state:
        analyzer = TfstateAnalyzer(args.state)
        analyzer.analyze()
        report_data = {
            'summary': analyzer.get_summary(),
            'resources': [r.__dict__ for r in analyzer.resources],
        }
    elif args.analysis_json:
        import json
        with open(args.analysis_json, 'r') as f:
            report_data = json.load(f)
    else:
        print("❌ Please provide either --state or --analysis-json")
        sys.exit(1)
    
    generator = VisualReportGenerator(report_data)
    output_path = generator.save(args.output or 'cost_report.html')
    
    print(f"✅ Visual report generated successfully!")
    print(f"   Open in browser: file://{os.path.abspath(output_path)}")


def main():
    parser = argparse.ArgumentParser(
        description='🌤️ Terraform IaC Cloud Cost Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Terraform state file
  %(prog)s tfstate --state terraform.tfstate --html-report report.html
  
  # Get actual cloud costs from billing
  %(prog)s cloud --providers aws azure --days 30 --summary
  
  # CI/CD cost diff check
  %(prog)s diff --base-path ./main --path ./feature --threshold-amount 100
  
  # Generate visual HTML report
  %(prog)s report --state terraform.tfstate --output my_report.html
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # TFState 分析子命令
    tf_parser = subparsers.add_parser('tfstate', help='Analyze Terraform tfstate file')
    tf_parser.add_argument('--state', required=True, help='Path to terraform.tfstate')
    tf_parser.add_argument('--output-json', help='Output detailed JSON')
    tf_parser.add_argument('--html-report', help='Generate HTML visual report')
    tf_parser.set_defaults(func=analyze_tfstate)
    
    # 多云成本分析子命令
    cloud_parser = subparsers.add_parser('cloud', help='Analyze actual cloud billing data')
    cloud_parser.add_argument('--providers', nargs='+', default=['aws', 'azure', 'gcp'],
                              help='Cloud providers to analyze')
    cloud_parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    cloud_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    cloud_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    cloud_parser.add_argument('--aws-region', default='us-east-1', help='AWS region')
    cloud_parser.add_argument('--azure-subscription', help='Azure subscription ID')
    cloud_parser.add_argument('--gcp-project', help='GCP project ID')
    cloud_parser.add_argument('--output', help='Output JSON report')
    cloud_parser.set_defaults(func=analyze_cloud_costs)
    
    # CI/CD Diff 检查子命令
    diff_parser = subparsers.add_parser('diff', help='CI/CD cost change check')
    diff_parser.add_argument('--path', default='.', help='Terraform project path')
    diff_parser.add_argument('--base-path', help='Base path for comparison')
    diff_parser.add_argument('--threshold-percent', type=float, default=20,
                             help='Warning threshold percentage')
    diff_parser.add_argument('--threshold-amount', type=float, default=100,
                             help='Warning threshold amount in USD')
    diff_parser.add_argument('--output', default='cost_diff_report.md', help='Output report')
    diff_parser.add_argument('--block-merge', action='store_true', help='Block merge on threshold')
    diff_parser.set_defaults(func=ci_diff_check)
    
    # 可视化报告子命令
    report_parser = subparsers.add_parser('report', help='Generate visual HTML report')
    report_parser.add_argument('--state', help='Path to terraform.tfstate')
    report_parser.add_argument('--analysis-json', help='Path to analysis JSON file')
    report_parser.add_argument('--output', help='Output HTML file')
    report_parser.set_defaults(func=generate_visual_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    print()
    print("=" * 60)
    print("🌤️  TERRAFORM IAC CLOUD COST MANAGEMENT TOOL")
    print("=" * 60)
    print()
    
    args.func(args)
    
    print()


if __name__ == '__main__':
    main()
