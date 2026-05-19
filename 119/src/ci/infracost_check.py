#!/usr/bin/env python3
"""
Infracost PR 成本变更检查脚本
集成到 CI 流程，自动分析成本变更并评论到 PR
"""
import json
import subprocess
import argparse
import os
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CostChange:
    resource_address: str
    old_monthly_cost: float
    new_monthly_cost: float
    change_monthly: float
    change_percent: float
    change_type: str
    cost_components: List[Dict]


class InfracostChecker:
    def __init__(self, threshold_percent: float = 20, threshold_amount: float = 100):
        self.threshold_percent = threshold_percent
        self.threshold_amount = threshold_amount
        self.changes = []
        self.summary = {}

    def run_infracost(self, path: str = ".") -> Dict:
        try:
            cmd = [
                "infracost", "breakdown",
                "--path", path,
                "--format", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running infracost: {e.stderr}")
            raise
        except FileNotFoundError:
            print("Error: infracost CLI not found. Install it first:")
            print("  curl -fsSL https://git.io/get-infracost | sh")
            sys.exit(1)

    def run_diff(self, base_path: str, target_path: str) -> Dict:
        try:
            cmd = [
                "infracost", "diff",
                "--path", target_path,
                "--compare-to", base_path,
                "--format", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running infracost diff: {e.stderr}")
            raise

    def parse_cost_changes(self, diff_result: Dict) -> List[CostChange]:
        changes = []
        
        projects = diff_result.get('projects', [])
        for project in projects:
            breakdown = project.get('breakdown', {})
            resources = breakdown.get('resources', [])
            
            for resource in resources:
                resource_address = resource.get('name', '')
                cost_components = resource.get('costComponents', [])
                
                old_monthly = float(resource.get('pastMonthlyCost', 0) or 0)
                new_monthly = float(resource.get('monthlyCost', 0) or 0)
                change_monthly = new_monthly - old_monthly
                
                if abs(change_monthly) < 0.01:
                    continue
                
                change_percent = (change_monthly / abs(old_monthly) * 100) if old_monthly != 0 else float('inf')
                
                change_type = 'added' if old_monthly == 0 else 'removed' if new_monthly == 0 else 'changed'
                
                changes.append(CostChange(
                    resource_address=resource_address,
                    old_monthly_cost=old_monthly,
                    new_monthly_cost=new_monthly,
                    change_monthly=change_monthly,
                    change_percent=change_percent,
                    change_type=change_type,
                    cost_components=cost_components
                ))
        
        self.changes = changes
        return changes

    def get_summary(self) -> Dict:
        total_old = sum(c.old_monthly_cost for c in self.changes)
        total_new = sum(c.new_monthly_cost for c in self.changes)
        total_change = total_new - total_old
        
        added = [c for c in self.changes if c.change_type == 'added']
        removed = [c for c in self.changes if c.change_type == 'removed']
        changed = [c for c in self.changes if c.change_type == 'changed']
        
        significant_increases = [
            c for c in self.changes 
            if c.change_monthly > 0 and 
               (c.change_percent > self.threshold_percent or c.change_monthly > self.threshold_amount)
        ]
        
        significant_decreases = [
            c for c in self.changes 
            if c.change_monthly < 0 and 
               (abs(c.change_percent) > self.threshold_percent or abs(c.change_monthly) > self.threshold_amount)
        ]
        
        self.summary = {
            'total_old_monthly': round(total_old, 2),
            'total_new_monthly': round(total_new, 2),
            'total_change_monthly': round(total_change, 2),
            'change_percent': round((total_change / abs(total_old) * 100) if total_old != 0 else 0, 1),
            'total_resources_changed': len(self.changes),
            'resources_added': len(added),
            'resources_removed': len(removed),
            'resources_modified': len(changed),
            'significant_increases': significant_increases,
            'significant_decreases': significant_decreases,
            'has_significant_changes': len(significant_increases) > 0 or len(significant_decreases) > 0,
        }
        
        return self.summary

    def generate_markdown_report(self) -> str:
        summary = self.get_summary()
        
        emoji = "🔴" if summary['total_change_monthly'] > 100 else "🟡" if summary['total_change_monthly'] > 0 else "🟢"
        
        md = f"""
{emoji} # Terraform 成本变更分析报告

## 💰 成本概览

| 指标 | 金额 |
|------|------|
| **变更前月度成本** | ${summary['total_old_monthly']:.2f} |
| **变更后月度成本** | ${summary['total_new_monthly']:.2f} |
| **月度成本变更** | ${summary['total_change_monthly']:+.2f} ({summary['change_percent']:+.1f}%) |
| **年度成本变更** | ${summary['total_change_monthly'] * 12:+.2f} |

## 📊 变更统计

- **新增资源**: {summary['resources_added']} 个
- **删除资源**: {summary['resources_removed']} 个
- **修改资源**: {summary['resources_modified']} 个

"""
        
        if summary['significant_increases']:
            md += """
### ⚠️ 成本显著增加（需关注）

| 资源 | 原成本 | 新成本 | 变更额 | 变更比例 |
|------|--------|--------|--------|----------|
"""
            for c in summary['significant_increases']:
                md += f"| `{c.resource_address}` | ${c.old_monthly_cost:.2f} | ${c.new_monthly_cost:.2f} | **+${c.change_monthly:.2f}** | +{c.change_percent:.1f}% |\n"

        if summary['significant_decreases']:
            md += """
### ✅ 成本显著降低

| 资源 | 原成本 | 新成本 | 变更额 | 变更比例 |
|------|--------|--------|--------|----------|
"""
            for c in summary['significant_decreases']:
                md += f"| `{c.resource_address}` | ${c.old_monthly_cost:.2f} | ${c.new_monthly_cost:.2f} | **${c.change_monthly:.2f}** | {c.change_percent:.1f}% |\n"

        if self.changes:
            md += """
### 📋 所有成本变更明细

| 资源 | 类型 | 原成本 | 新成本 | 变更额 |
|------|------|--------|--------|--------|
"""
            for c in sorted(self.changes, key=lambda x: abs(x.change_monthly), reverse=True):
                type_emoji = "➕" if c.change_type == "added" else "➖" if c.change_type == "removed" else "🔄"
                md += f"| `{c.resource_address}` | {type_emoji} {c.change_type} | ${c.old_monthly_cost:.2f} | ${c.new_monthly_cost:.2f} | ${c.change_monthly:+.2f} |\n"

        md += """
---
*此报告由 Infracost 自动生成，所有成本为估算值，实际费用以云服务商账单为准。*
*建议：对于显著增加的成本，请确认是否必要，或考虑优化方案（预留实例、实例类型调整等）。*
"""
        return md

    def save_report(self, output_path: str = "cost_change_report.md"):
        md = self.generate_markdown_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"Report saved to {output_path}")
        return md

    def check_should_block_merge(self) -> Tuple[bool, str]:
        summary = self.get_summary()
        
        if summary['total_change_monthly'] > self.threshold_amount * 2:
            return True, f"成本增加超过 ${self.threshold_amount * 2:.2f}/月，请确认或优化后合并"
        
        if summary['total_change_monthly'] > self.threshold_amount:
            return False, f"注意：成本增加超过 ${self.threshold_amount:.2f}/月，建议审核"
        
        return False, "成本变更在可接受范围内"


def main():
    parser = argparse.ArgumentParser(description='Infracost PR Cost Checker')
    parser.add_argument('--path', default='.', help='Terraform project path')
    parser.add_argument('--base-path', help='Base path for comparison (e.g., main branch)')
    parser.add_argument('--threshold-percent', type=float, default=20, help='Warning threshold percentage')
    parser.add_argument('--threshold-amount', type=float, default=100, help='Warning threshold amount in USD')
    parser.add_argument('--output', default='cost_change_report.md', help='Output report path')
    parser.add_argument('--json-output', help='JSON output path')
    parser.add_argument('--check-block', action='store_true', help='Check if should block merge')
    
    args = parser.parse_args()
    
    checker = InfracostChecker(
        threshold_percent=args.threshold_percent,
        threshold_amount=args.threshold_amount
    )
    
    if args.base_path:
        print(f"Running infracost diff: {args.base_path} vs {args.path}")
        diff_result = checker.run_diff(args.base_path, args.path)
    else:
        print(f"Running infracost breakdown on {args.path}")
        diff_result = checker.run_infracost(args.path)
        
        base_result = {'projects': [{'breakdown': {'resources': []}}]}
        for project in diff_result.get('projects', []):
            for resource in project.get('breakdown', {}).get('resources', []):
                resource['pastMonthlyCost'] = 0
        
        diff_result['projects'] = diff_result.get('projects', [])
    
    changes = checker.parse_cost_changes(diff_result)
    summary = checker.get_summary()
    
    print(f"\n{'='*60}")
    print(f"Cost Change Summary: ${summary['total_change_monthly']:+.2f} / month ({summary['change_percent']:+.1f}%)")
    print(f"Total resources changed: {summary['total_resources_changed']}")
    print(f"{'='*60}\n")
    
    md_report = checker.save_report(args.output)
    
    if args.json_output:
        result = {
            'summary': summary,
            'changes': [c.__dict__ for c in changes],
            'report': md_report
        }
        with open(args.json_output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    
    if args.check_block:
        should_block, reason = checker.check_should_block_merge()
        print(f"\nMerge Check: {'BLOCKED' if should_block else 'ALLOWED'} - {reason}")
        if should_block:
            sys.exit(1)


if __name__ == '__main__':
    main()
