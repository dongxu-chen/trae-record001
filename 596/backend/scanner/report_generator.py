import json
from typing import Dict, List
from .config import ScanResult, Vulnerability
from datetime import datetime


class ReportGenerator:
    @staticmethod
    def generate_json_report(result: ScanResult) -> str:
        return json.dumps(result.dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def generate_html_report(result: ScanResult) -> str:
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745"
        }
        
        vulns_by_severity = ReportGenerator._group_by_severity(result.vulnerabilities)
        vulns_by_type = ReportGenerator._group_by_type(result.vulnerabilities)
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API安全漏洞扫描报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 15px; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card .number {{ font-size: 32px; font-weight: bold; color: #007bff; }}
        .summary-card .label {{ color: #666; margin-top: 5px; }}
        .severity-stats {{ display: flex; gap: 10px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
        .severity-badge {{ padding: 8px 16px; border-radius: 20px; color: white; font-weight: bold; }}
        .vulnerability-list {{ margin-top: 30px; }}
        .vuln-item {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
        .vuln-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }}
        .vuln-type {{ font-size: 18px; font-weight: bold; color: #333; }}
        .vuln-severity {{ padding: 5px 15px; border-radius: 20px; color: white; font-size: 14px; font-weight: bold; }}
        .vuln-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; }}
        .detail-item {{ padding: 10px; background: #f8f9fa; border-radius: 5px; }}
        .detail-label {{ font-weight: bold; color: #666; font-size: 12px; }}
        .detail-value {{ margin-top: 5px; color: #333; word-break: break-all; }}
        .evidence {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; font-size: 12px; }}
        .verification {{ background: #e3f2fd; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 13px; }}
        .verification .score {{ font-weight: bold; font-size: 16px; }}
        .verification .score.high {{ color: #dc3545; }}
        .verification .score.medium {{ color: #ffc107; }}
        .role-context {{ background: #f3e5f5; padding: 8px 12px; border-radius: 5px; margin-top: 10px; font-size: 13px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #666; font-size: 12px; }}
        .type-stats {{ display: flex; gap: 10px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
        .type-badge {{ padding: 8px 16px; border-radius: 20px; background: #667eea; color: white; font-weight: bold; }}
        .scan-meta {{ background: #f0f4ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .scan-meta span {{ margin-right: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 API安全漏洞扫描报告</h1>
        
        <div class="scan-meta">
            <span><strong>目标:</strong> {result.target_url}</span>
            <span><strong>扫描时间:</strong> {result.scan_time}</span>
            {f'<span><strong>会话ID:</strong> {result.session_id}</span>' if result.session_id else ''}
            {f'<span><strong>扫描角色:</strong> {", ".join(result.roles_scanned)}</span>' if result.roles_scanned else ''}
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{len(result.vulnerabilities)}</div>
                <div class="label">发现漏洞数</div>
            </div>
            <div class="summary-card">
                <div class="number">{result.total_requests}</div>
                <div class="label">总请求数</div>
            </div>
        </div>
        
        <div class="severity-stats">
            {ReportGenerator._generate_severity_badges(vulns_by_severity)}
        </div>
        
        <div class="type-stats">
            {ReportGenerator._generate_type_badges(vulns_by_type)}
        </div>
        
        <div class="vulnerability-list">
            <h2 style="margin-bottom: 20px; color: #333;">漏洞详情</h2>
            {ReportGenerator._generate_vulnerability_list(result.vulnerabilities, severity_colors)}
        </div>
        
        <div class="footer">
            报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 目标: {result.target_url}
        </div>
    </div>
</body>
</html>
        """
        return html

    @staticmethod
    def _group_by_severity(vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        grouped = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            if vuln.severity in grouped:
                grouped[vuln.severity] += 1
        return grouped

    @staticmethod
    def _group_by_type(vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        grouped = {}
        for vuln in vulnerabilities:
            if vuln.type not in grouped:
                grouped[vuln.type] = 0
            grouped[vuln.type] += 1
        return grouped

    @staticmethod
    def _generate_severity_badges(vulns_by_severity: Dict[str, int]) -> str:
        colors = {"critical": "#dc3545", "high": "#fd7e14", "medium": "#ffc107", "low": "#28a745"}
        labels = {"critical": "严重", "high": "高危", "medium": "中危", "low": "低危"}
        
        badges = []
        for severity, count in vulns_by_severity.items():
            badges.append(f'<span class="severity-badge" style="background: {colors[severity]};">{labels[severity]}: {count}</span>')
        return "".join(badges)

    @staticmethod
    def _generate_type_badges(vulns_by_type: Dict[str, int]) -> str:
        badges = []
        for vuln_type, count in vulns_by_type.items():
            badges.append(f'<span class="type-badge">{vuln_type}: {count}</span>')
        return "".join(badges) if badges else '<span style="color: #666;">按漏洞类型统计: 暂无</span>'

    @staticmethod
    def _generate_vulnerability_list(vulnerabilities: List[Vulnerability], severity_colors: Dict[str, str]) -> str:
        if not vulnerabilities:
            return '<p style="text-align: center; color: #28a745; padding: 40px;">🎉 未发现漏洞</p>'
        
        items = []
        for vuln in vulnerabilities:
            color = severity_colors.get(vuln.severity, "#6c757d")
            
            verification_html = ""
            if hasattr(vuln, 'verification_result') and vuln.verification_result:
                vr = vuln.verification_result
                score_class = "high" if vr.consistency_score >= 0.8 else "medium"
                verification_html = f"""
                <div class="verification">
                    <strong>🔍 重放验证结果:</strong><br>
                    重放次数: {vr.replay_count} | 成功次数: {vr.success_count} | 
                    一致性评分: <span class="score {score_class}">{vr.consistency_score:.2%}</span> | 
                    状态: {'✅ 漏洞复现成功' if vr.is_consistent else '⚠️ 结果不一致'}
                </div>
                """
            
            role_html = ""
            if vuln.role_context:
                role_html = f'<div class="role-context"><strong>👤 角色上下文:</strong> {vuln.role_context}</div>'
            
            item = f"""
            <div class="vuln-item">
                <div class="vuln-header">
                    <span class="vuln-type">{vuln.type}</span>
                    <span class="vuln-severity" style="background: {color};">{vuln.severity.upper()}</span>
                </div>
                <div class="vuln-details">
                    <div class="detail-item">
                        <div class="detail-label">端点</div>
                        <div class="detail-value">{vuln.endpoint}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">方法</div>
                        <div class="detail-value">{vuln.method}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">描述</div>
                        <div class="detail-value">{vuln.description}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">验证状态</div>
                        <div class="detail-value">{'✅ 已验证' if vuln.verified else '⏳ 待验证'}</div>
                    </div>
                </div>
                {role_html}
                <div class="evidence">
                    <strong>证据:</strong> {vuln.evidence}<br>
                    <strong>Payload:</strong> {vuln.payload[:200]}
                </div>
                {verification_html}
                <div style="margin-top: 15px; padding: 10px; background: #d4edda; border-radius: 5px;">
                    <strong>💡 修复建议:</strong> {vuln.recommendation}
                </div>
            </div>
            """
            items.append(item)
        return "".join(items)

    @staticmethod
    def generate_markdown_report(result: ScanResult) -> str:
        md = f"# API安全漏洞扫描报告\n\n"
        md += f"- **目标URL**: {result.target_url}\n"
        md += f"- **扫描时间**: {result.scan_time}\n"
        md += f"- **总请求数**: {result.total_requests}\n"
        md += f"- **发现漏洞数**: {len(result.vulnerabilities)}\n"
        if result.roles_scanned:
            md += f"- **扫描角色**: {', '.join(result.roles_scanned)}\n"
        if result.session_id:
            md += f"- **会话ID**: {result.session_id}\n"
        md += "\n"
        
        if result.vulnerabilities:
            vulns_by_severity = ReportGenerator._group_by_severity(result.vulnerabilities)
            md += "## 严重程度统计\n\n"
            md += f"- 🔴 严重: {vulns_by_severity.get('critical', 0)}\n"
            md += f"- 🟠 高危: {vulns_by_severity.get('high', 0)}\n"
            md += f"- 🟡 中危: {vulns_by_severity.get('medium', 0)}\n"
            md += f"- 🟢 低危: {vulns_by_severity.get('low', 0)}\n\n"
            
            md += "## 漏洞详情\n\n"
            for i, vuln in enumerate(result.vulnerabilities, 1):
                md += f"### {i}. {vuln.type} ({vuln.severity.upper()})\n\n"
                md += f"- **端点**: `{vuln.endpoint}`\n"
                md += f"- **方法**: {vuln.method}\n"
                md += f"- **描述**: {vuln.description}\n"
                md += f"- **证据**: {vuln.evidence}\n"
                md += f"- **Payload**: `{vuln.payload[:100]}`\n"
                md += f"- **验证状态**: {'✅ 已验证' if vuln.verified else '⏳ 待验证'}\n"
                
                if vuln.role_context:
                    md += f"- **角色上下文**: {vuln.role_context}\n"
                
                if hasattr(vuln, 'verification_result') and vuln.verification_result:
                    vr = vuln.verification_result
                    md += f"- **重放验证**: 重放{vr.replay_count}次, 成功{vr.success_count}次, 一致性{vr.consistency_score:.2%}\n"
                
                md += f"- **修复建议**: {vuln.recommendation}\n\n"
        else:
            md += "## 扫描结果\n\n🎉 未发现漏洞！\n"
        
        return md
