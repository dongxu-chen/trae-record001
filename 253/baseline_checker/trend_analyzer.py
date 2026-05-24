import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .data_store import DataStore

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def get_compliance_trend(self, hostname: str = None, 
                            days: int = 30) -> Dict[str, Any]:
        history = self.data_store.get_scan_history(hostname=hostname, limit=100)
        
        if not history:
            return {"message": "No scan history available"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = [h for h in history 
                   if datetime.fromisoformat(h["timestamp"]) >= cutoff_date]
        filtered.sort(key=lambda x: x["timestamp"])
        
        trend_data = {
            "period": f"Last {days} days",
            "total_scans": len(filtered),
            "hosts_analyzed": list(set(h["hostname"] for h in filtered)),
            "compliance_over_time": [],
            "average_compliance": 0.0,
            "trend": "stable"
        }
        
        compliance_rates = []
        for scan in filtered:
            summary = scan.get("summary", {})
            total = summary.get("total", 0)
            passed = summary.get("pass", 0)
            rate = (passed / total * 100) if total > 0 else 0
            
            trend_data["compliance_over_time"].append({
                "timestamp": scan["timestamp"],
                "hostname": scan["hostname"],
                "scan_id": scan["scan_id"],
                "total_checks": total,
                "passed": passed,
                "failed": summary.get("fail", 0),
                "warnings": summary.get("warn", 0),
                "compliance_rate": round(rate, 2)
            })
            compliance_rates.append(rate)
        
        if compliance_rates:
            trend_data["average_compliance"] = round(sum(compliance_rates) / len(compliance_rates), 2)
            
            if len(compliance_rates) >= 2:
                first_half = compliance_rates[:len(compliance_rates)//2]
                second_half = compliance_rates[len(compliance_rates)//2:]
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                
                if avg_second > avg_first + 5:
                    trend_data["trend"] = "improving"
                elif avg_second < avg_first - 5:
                    trend_data["trend"] = "declining"
                else:
                    trend_data["trend"] = "stable"
        
        return trend_data

    def get_top_issues(self, hostname: str = None, 
                       limit: int = 10, days: int = 30) -> Dict[str, Any]:
        history = self.data_store.get_scan_history(hostname=hostname, limit=50)
        
        if not history:
            return {"message": "No scan history available"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = [h for h in history 
                   if datetime.fromisoformat(h["timestamp"]) >= cutoff_date]
        
        issue_counter = Counter()
        issue_details = {}
        
        for scan_meta in filtered:
            scan_data = self.data_store.get_scan_result(scan_meta["scan_id"])
            if not scan_data:
                continue
            
            for result in scan_data.get("results", []):
                if result["status"] in ["fail", "warn"]:
                    check_id = result["id"]
                    issue_counter[check_id] += 1
                    
                    if check_id not in issue_details:
                        issue_details[check_id] = {
                            "name": result["name"],
                            "severity": result["severity"],
                            "category": result.get("category", ""),
                            "description": result.get("description", ""),
                            "first_seen": scan_meta["timestamp"],
                            "last_seen": scan_meta["timestamp"],
                            "hosts": set()
                        }
                    else:
                        issue_details[check_id]["last_seen"] = scan_meta["timestamp"]
                    
                    issue_details[check_id]["hosts"].add(scan_meta["hostname"])
        
        top_issues = []
        for check_id, count in issue_counter.most_common(limit):
            details = issue_details[check_id]
            top_issues.append({
                "check_id": check_id,
                "name": details["name"],
                "severity": details["severity"],
                "category": details["category"],
                "occurrences": count,
                "affected_hosts": len(details["hosts"]),
                "hosts": list(details["hosts"]),
                "first_seen": details["first_seen"],
                "last_seen": details["last_seen"],
                "description": details["description"]
            })
        
        return {
            "period": f"Last {days} days",
            "total_unique_issues": len(issue_counter),
            "top_issues": top_issues
        }

    def get_severity_distribution(self, hostname: str = None, 
                                  days: int = 30) -> Dict[str, Any]:
        history = self.data_store.get_scan_history(hostname=hostname, limit=50)
        
        if not history:
            return {"message": "No scan history available"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = [h for h in history 
                   if datetime.fromisoformat(h["timestamp"]) >= cutoff_date]
        
        distribution = defaultdict(lambda: {"pass": 0, "fail": 0, "warn": 0, "total": 0})
        
        for scan_meta in filtered:
            scan_data = self.data_store.get_scan_result(scan_meta["scan_id"])
            if not scan_data:
                continue
            
            for result in scan_data.get("results", []):
                severity = result.get("severity", "medium")
                status = result["status"]
                
                distribution[severity]["total"] += 1
                if status in distribution[severity]:
                    distribution[severity][status] += 1
        
        result = {}
        for severity, counts in distribution.items():
            total = counts["total"]
            pass_rate = (counts["pass"] / total * 100) if total > 0 else 0
            result[severity] = {
                **counts,
                "pass_rate": round(pass_rate, 2)
            }
        
        return result

    def get_category_performance(self, hostname: str = None,
                                  days: int = 30) -> Dict[str, Any]:
        history = self.data_store.get_scan_history(hostname=hostname, limit=50)
        
        if not history:
            return {"message": "No scan history available"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = [h for h in history 
                   if datetime.fromisoformat(h["timestamp"]) >= cutoff_date]
        
        category_stats = defaultdict(lambda: {"pass": 0, "fail": 0, "warn": 0, "total": 0})
        
        for scan_meta in filtered:
            scan_data = self.data_store.get_scan_result(scan_meta["scan_id"])
            if not scan_data:
                continue
            
            for result in scan_data.get("results", []):
                category = result.get("category", "other")
                status = result["status"]
                
                category_stats[category]["total"] += 1
                if status in category_stats[category]:
                    category_stats[category][status] += 1
        
        result = []
        for category, stats in category_stats.items():
            total = stats["total"]
            pass_rate = (stats["pass"] / total * 100) if total > 0 else 0
            result.append({
                "category": category,
                **stats,
                "pass_rate": round(pass_rate, 2)
            })
        
        result.sort(key=lambda x: x["pass_rate"])
        return {"categories": result}

    def generate_html_report(self, hostname: str = None, 
                              days: int = 30) -> str:
        compliance = self.get_compliance_trend(hostname, days)
        top_issues = self.get_top_issues(hostname, limit=10, days=days)
        severity_dist = self.get_severity_distribution(hostname, days)
        category_perf = self.get_category_performance(hostname, days)
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基线检查趋势分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metric {{ display: inline-block; margin-right: 30px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .trend-improving {{ color: #28a745; }}
        .trend-declining {{ color: #dc3545; }}
        .trend-stable {{ color: #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        tr:hover {{ background: #f5f5f5; }}
        .severity-critical {{ color: #dc3545; font-weight: bold; }}
        .severity-high {{ color: #fd7e14; font-weight: bold; }}
        .severity-medium {{ color: #ffc107; font-weight: bold; }}
        .severity-low {{ color: #17a2b8; font-weight: bold; }}
        .pass-rate-high {{ color: #28a745; }}
        .pass-rate-low {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 基线检查趋势分析报告</h1>
        <p>分析周期: {compliance.get('period', 'N/A')}</p>
        
        <div class="summary">
            <div class="metric">
                <div>总扫描次数</div>
                <div class="metric-value">{compliance.get('total_scans', 0)}</div>
            </div>
            <div class="metric">
                <div>平均合规率</div>
                <div class="metric-value">{compliance.get('average_compliance', 0)}%</div>
            </div>
            <div class="metric">
                <div>趋势</div>
                <div class="metric-value trend-{compliance.get('trend', 'stable')}">{compliance.get('trend', 'stable').upper()}</div>
            </div>
        </div>
        
        <h2>📊 合规率变化趋势</h2>
        <table>
            <tr>
                <th>时间</th>
                <th>主机</th>
                <th>检查项总数</th>
                <th>通过</th>
                <th>失败</th>
                <th>警告</th>
                <th>合规率</th>
            </tr>
"""
        
        for entry in compliance.get("compliance_over_time", []):
            rate_class = "pass-rate-high" if entry["compliance_rate"] >= 80 else "pass-rate-low"
            html += f"""
            <tr>
                <td>{entry['timestamp']}</td>
                <td>{entry['hostname']}</td>
                <td>{entry['total_checks']}</td>
                <td>{entry['passed']}</td>
                <td>{entry['failed']}</td>
                <td>{entry['warnings']}</td>
                <td class="{rate_class}">{entry['compliance_rate']}%</td>
            </tr>
"""
        
        html += f"""
        </table>
        
        <h2>🔥 TOP 问题项</h2>
        <table>
            <tr>
                <th>检查ID</th>
                <th>检查项</th>
                <th>严重程度</th>
                <th>类别</th>
                <th>出现次数</th>
                <th>影响主机数</th>
                <th>最近出现</th>
            </tr>
"""
        
        for issue in top_issues.get("top_issues", []):
            sev_class = f"severity-{issue['severity']}"
            html += f"""
            <tr>
                <td>{issue['check_id']}</td>
                <td>{issue['name']}</td>
                <td class="{sev_class}">{issue['severity'].upper()}</td>
                <td>{issue['category']}</td>
 <td>{issue['occurrences']}</td>
                <td>{issue['affected_hosts']}</td>
                <td>{issue['last_seen']}</td>
            </tr>
"""
        
        html += f"""
        </table>
        
        <h2>📈 按类别表现</h2>
        <table>
            <tr>
                <th>类别</th>
                <th>总检查数</th>
                <th>通过</th>
                <th>失败</th>
                <th>警告</th>
                <th>通过率</th>
            </tr>
"""
        
        for cat in category_perf.get("categories", []):
            rate_class = "pass-rate-high" if cat["pass_rate"] >= 80 else "pass-rate-low"
            html += f"""
            <tr>
                <td>{cat['category']}</td>
                <td>{cat['total']}</td>
                <td>{cat['pass']}</td>
                <td>{cat['fail']}</td>
                <td>{cat['warn']}</td>
                <td class="{rate_class}">{cat['pass_rate']}%</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        return html

    def print_text_report(self, hostname: str = None, days: int = 30):
        compliance = self.get_compliance_trend(hostname, days)
        top_issues = self.get_top_issues(hostname, limit=10, days=days)
        category_perf = self.get_category_performance(hostname, days)
        
        from colorama import Fore, Style, init
        init()
        
        print("=" * 80)
        print(f"{Fore.CYAN}📊 基线检查趋势分析报告{Style.RESET_ALL}")
        print("=" * 80)
        print(f"分析周期: {compliance.get('period', 'N/A')}")
        print()
        
        trend_icon = {
            "improving": "📈",
            "declining": "📉",
            "stable": "➡️"
        }.get(compliance.get("trend", "stable"), "➡️")
        
        trend_color = {
            "improving": Fore.GREEN,
            "declining": Fore.RED,
            "stable": Fore.YELLOW
        }.get(compliance.get("trend", "stable"), Fore.YELLOW)
        
        print(f"总扫描次数: {compliance.get('total_scans', 0)}")
        print(f"平均合规率: {Fore.CYAN}{compliance.get('average_compliance', 0)}%{Style.RESET_ALL}")
        print(f"趋势: {trend_color}{trend_icon} {compliance.get('trend', 'stable').upper()}{Style.RESET_ALL}")
        print()
        
        if compliance.get("compliance_over_time"):
            print(f"{Fore.CYAN}合规率变化:{Style.RESET_ALL}")
            print("-" * 60)
            for entry in compliance["compliance_over_time"][-10:]:
                rate_color = Fore.GREEN if entry["compliance_rate"] >= 80 else Fore.RED
                print(f"  {entry['timestamp'][:19]} | {entry['hostname']:20s} | "
                      f"{rate_color}{entry['compliance_rate']:>6.1f}%{Style.RESET_ALL} | "
                      f"P:{entry['passed']:3d} F:{entry['failed']:3d} W:{entry['warnings']:3d}")
            print()
        
        if top_issues.get("top_issues"):
            print(f"{Fore.RED}🔥 TOP 问题项:{Style.RESET_ALL}")
            print("-" * 80)
            for i, issue in enumerate(top_issues["top_issues"][:10], 1):
                sev_color = {
                    "critical": Fore.MAGENTA,
                    "high": Fore.RED,
                    "medium": Fore.YELLOW,
                    "low": Fore.CYAN
                }.get(issue["severity"], "")
                
                print(f"  {i:2d}. [{sev_color}{issue['severity'].upper():8s}{Style.RESET_ALL}] "
                      f"{issue['check_id']} - {issue['name']}")
                print(f"      出现次数: {issue['occurrences']} | 影响主机: {issue['affected_hosts']} | "
                      f"最近: {issue['last_seen'][:19]}")
            print()
        
        if category_perf.get("categories"):
            print(f"{Fore.CYAN}📈 按类别表现:{Style.RESET_ALL}")
            print("-" * 60)
            for cat in category_perf["categories"]:
                rate_color = Fore.GREEN if cat["pass_rate"] >= 80 else Fore.RED
                print(f"  {cat['category']:20s} | 总数:{cat['total']:4d} | "
                      f"通过:{cat['pass']:4d} | 失败:{cat['fail']:4d} | "
                      f"{rate_color}{cat['pass_rate']:>6.1f}%{Style.RESET_ALL}")
        
        print("=" * 80)
