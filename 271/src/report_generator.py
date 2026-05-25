import os
import json
from datetime import datetime
from typing import Dict, List, Any


class ReportGenerator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.severity_weights = self.config.get('rules', {}).get('severity_weights', {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1
        })
        self.risk_thresholds = self.config.get('rules', {}).get('risk_thresholds', {
            "critical": 80,
            "high": 50,
            "medium": 20,
            "low": 0
        })
    
    def calculate_risk_score(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        total_score = 0
        issue_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        
        linting = analysis_results.get('linting', {})
        for severity, count in linting.get('summary', {}).items():
            if severity in issue_counts:
                issue_counts[severity] += count
        
        custom_rules = analysis_results.get('custom_rules', {})
        for severity, count in custom_rules.get('summary', {}).items():
            if severity in issue_counts:
                issue_counts[severity] += count
        
        dsl_rules = analysis_results.get('dsl_rules', {})
        for severity, count in dsl_rules.get('summary', {}).items():
            if severity in issue_counts:
                issue_counts[severity] += count
        
        sonarqube = analysis_results.get('sonarqube', {})
        for severity, count in sonarqube.get('summary', {}).items():
            if severity in issue_counts:
                issue_counts[severity] += count
        
        complexity = analysis_results.get('complexity', {}).get('summary', {})
        high_risk_count = complexity.get('high_risk_count', 0)
        if high_risk_count > 0:
            issue_counts["high"] += high_risk_count
        
        duplication = analysis_results.get('duplication', {}).get('summary', {})
        dup_count = duplication.get('total_duplicates', 0)
        if dup_count > 0:
            issue_counts["medium"] += dup_count
        
        ai_review = analysis_results.get('ai_review', {}).get('summary', {})
        for severity, count in ai_review.get('by_severity', {}).items():
            if severity in issue_counts:
                issue_counts[severity] += count
        
        impact_risk = analysis_results.get('impact_analysis', {}).get('risk_assessment', {})
        impact_level = impact_risk.get('level', 'low')
        if impact_level == 'critical':
            issue_counts["high"] += 2
        elif impact_level == 'high':
            issue_counts["medium"] += 2
        
        for severity, count in issue_counts.items():
            total_score += count * self.severity_weights.get(severity, 1)
        
        risk_level = self._determine_risk_level(total_score)
        
        return {
            "risk_score": total_score,
            "risk_level": risk_level,
            "issue_counts": issue_counts,
            "severity_weights": self.severity_weights
        }
    
    def _determine_risk_level(self, score: int) -> str:
        if score >= self.risk_thresholds.get("critical", 80):
            return "critical"
        elif score >= self.risk_thresholds.get("high", 50):
            return "high"
        elif score >= self.risk_thresholds.get("medium", 20):
            return "medium"
        elif score >= self.risk_thresholds.get("low", 0):
            return "low"
        else:
            return "none"
    
    def generate_json_report(self, analysis_results: Dict[str, Any], 
                              output_path: str = None) -> str:
        if output_path is None:
            report_dir = self.config.get('output', {}).get('report_dir', 'reports')
            os.makedirs(report_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(report_dir, f"code_review_report_{timestamp}.json")
        
        risk_assessment = self.calculate_risk_score(analysis_results)
        
        full_report = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "pr_info": analysis_results.get('pr_info', {}),
            "risk_assessment": risk_assessment,
            "results": {
                "linting": analysis_results.get('linting', {}),
                "complexity": analysis_results.get('complexity', {}),
                "duplication": analysis_results.get('duplication', {}),
                "custom_rules": analysis_results.get('custom_rules', {}),
                "dsl_rules": analysis_results.get('dsl_rules', {}),
                "impact_analysis": analysis_results.get('impact_analysis', {}),
                "ai_review": analysis_results.get('ai_review', {}),
                "effort_estimate": analysis_results.get('effort_estimate', {}),
                "sonarqube": analysis_results.get('sonarqube', {})
            },
            "summary": self._generate_summary(analysis_results, risk_assessment)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def generate_text_report(self, analysis_results: Dict[str, Any], 
                              output_path: str = None) -> str:
        if output_path is None:
            report_dir = self.config.get('output', {}).get('report_dir', 'reports')
            os.makedirs(report_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(report_dir, f"code_review_report_{timestamp}.txt")
        
        risk_assessment = self.calculate_risk_score(analysis_results)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("                    CODE REVIEW REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        pr_info = analysis_results.get('pr_info', {})
        if pr_info:
            report_lines.append("-" * 80)
            report_lines.append("PULL REQUEST INFORMATION")
            report_lines.append("-" * 80)
            report_lines.append(f"Title: {pr_info.get('title', 'N/A')}")
            report_lines.append(f"Author: {pr_info.get('author', 'N/A')}")
            report_lines.append(f"Branch: {pr_info.get('head_branch', 'N/A')} -> {pr_info.get('base_branch', 'N/A')}")
            report_lines.append(f"Changed files: {pr_info.get('changed_files', 0)}")
            report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append("RISK ASSESSMENT")
        report_lines.append("-" * 80)
        report_lines.append(f"Risk Score: {risk_assessment['risk_score']}")
        report_lines.append(f"Risk Level: {risk_assessment['risk_level'].upper()}")
        report_lines.append("")
        report_lines.append("Issue Counts:")
        for severity, count in risk_assessment['issue_counts'].items():
            report_lines.append(f"  {severity.upper()}: {count}")
        report_lines.append("")
        
        linting = analysis_results.get('linting', {})
        report_lines.append("-" * 80)
        report_lines.append("LINTING RESULTS")
        report_lines.append("-" * 80)
        report_lines.append(f"Total issues: {linting.get('total_issues', 0)}")
        
        issues = linting.get('issues', [])
        if issues:
            report_lines.append("")
            report_lines.append("Top Issues:")
            for issue in issues[:10]:
                report_lines.append(
                    f"  [{issue.get('severity', 'low').upper()}] {issue.get('type', '')}: "
                    f"{issue.get('message', '')} ({issue.get('file', '')}:{issue.get('line', 0)})"
                )
        report_lines.append("")
        
        complexity = analysis_results.get('complexity', {}).get('summary', {})
        report_lines.append("-" * 80)
        report_lines.append("COMPLEXITY ANALYSIS")
        report_lines.append("-" * 80)
        report_lines.append(f"Total files analyzed: {complexity.get('total_files', 0)}")
        report_lines.append(f"Total lines of code: {complexity.get('total_nloc', 0)}")
        report_lines.append(f"Total functions: {complexity.get('total_functions', 0)}")
        report_lines.append(f"Average CCN: {complexity.get('average_ccn', 0)}")
        report_lines.append(f"Max CCN: {complexity.get('max_ccn', 0)}")
        report_lines.append(f"High risk functions: {complexity.get('high_risk_count', 0)}")
        report_lines.append(f"Complexity Risk Level: {complexity.get('risk_level', 'none').upper()}")
        report_lines.append("")
        
        high_risk_funcs = analysis_results.get('complexity', {}).get('high_risk_functions', [])
        if high_risk_funcs:
            report_lines.append("High Risk Functions:")
            for func in high_risk_funcs[:5]:
                report_lines.append(
                    f"  [{func.get('risk_level', 'medium').upper()}] "
                    f"{func.get('long_name', func.get('name', ''))} "
                    f"(CCN: {func.get('ccn', 0)}, Lines: {func.get('nloc', 0)})"
                )
        report_lines.append("")
        
        duplication = analysis_results.get('duplication', {}).get('summary', {})
        report_lines.append("-" * 80)
        report_lines.append("CODE DUPLICATION")
        report_lines.append("-" * 80)
        report_lines.append(f"Total duplicates: {duplication.get('total_duplicates', 0)}")
        report_lines.append(f"Cross-file duplicates: {duplication.get('cross_file_duplicates', 0)}")
        report_lines.append(f"Internal duplicates: {duplication.get('internal_duplicates', 0)}")
        report_lines.append(f"Duplication Risk Level: {duplication.get('risk_level', 'none').upper()}")
        report_lines.append("")
        
        custom_rules = analysis_results.get('custom_rules', {}).get('summary', {})
        report_lines.append("-" * 80)
        report_lines.append("CUSTOM RULES")
        report_lines.append("-" * 80)
        report_lines.append(f"Total violations: {custom_rules.get('total', 0)}")
        for severity in ["critical", "high", "medium", "low"]:
            if custom_rules.get(severity, 0) > 0:
                report_lines.append(f"  {severity.upper()}: {custom_rules.get(severity, 0)}")
        report_lines.append("")
        
        impact_analysis = analysis_results.get('impact_analysis', {})
        impact_summary = impact_analysis.get('impact_summary', {})
        report_lines.append("-" * 80)
        report_lines.append("IMPACT ANALYSIS")
        report_lines.append("-" * 80)
        report_lines.append(f"Changed functions: {len(impact_analysis.get('changed_functions', []))}")
        report_lines.append(f"Impacted functions: {impact_summary.get('total_impacted_functions', 0)}")
        report_lines.append(f"Max impact depth: {impact_summary.get('max_impact_depth', 0)}")
        report_lines.append(f"Impacted files: {len(impact_summary.get('impacted_files', []))}")
        impact_risk = impact_analysis.get('risk_assessment', {})
        report_lines.append(f"Impact Risk Level: {impact_risk.get('level', 'unknown').upper()}")
        
        impact_chains = impact_analysis.get('impact_chains', [])
        if impact_chains:
            report_lines.append("")
            report_lines.append("Top Impact Chains:")
            for chain in impact_chains[:5]:
                source = chain.get('source', '').split('::')[-1]
                target = chain.get('target', '').split('::')[-1]
                report_lines.append(f"  {source} -> ... -> {target} (depth: {chain.get('depth', 0)})")
        report_lines.append("")
        
        ai_review = analysis_results.get('ai_review', {})
        ai_summary = ai_review.get('summary', {})
        report_lines.append("-" * 80)
        report_lines.append("AI CODE REVIEW")
        report_lines.append("-" * 80)
        report_lines.append(f"Total suggestions: {ai_summary.get('total_comments', 0)}")
        report_lines.append(f"Overall Grade: {ai_summary.get('overall_grade', 'N/A')}")
        report_lines.append(f"Risk Score: {ai_summary.get('risk_score', 0)}")
        report_lines.append("")
        report_lines.append("Suggestions by Severity:")
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = ai_summary.get('by_severity', {}).get(severity, 0)
            if count > 0:
                report_lines.append(f"  {severity.upper()}: {count}")
        
        ai_comments = ai_review.get('all_comments', [])
        if ai_comments:
            report_lines.append("")
            report_lines.append("Top AI Suggestions:")
            for comment in ai_comments[:5]:
                report_lines.append(
                    f"  [{comment.get('severity', 'low').upper()}] {comment.get('title', '')}: "
                    f"{comment.get('message', '')} ({comment.get('file', '')}:{comment.get('line', 0)})"
                )
        report_lines.append("")
        
        effort_estimate = analysis_results.get('effort_estimate', {})
        report_lines.append("-" * 80)
        report_lines.append("REVIEW EFFORT ESTIMATE")
        report_lines.append("-" * 80)
        report_lines.append(f"Estimated Review Time: {effort_estimate.get('human_readable', 'N/A')}")
        report_lines.append(f"Complexity Level: {effort_estimate.get('complexity_level', 'unknown').upper()}")
        report_lines.append(f"Total Files: {effort_estimate.get('summary', {}).get('total_files', 0)}")
        
        risk_factors = effort_estimate.get('risk_factors', [])
        if risk_factors:
            report_lines.append("")
            report_lines.append("Risk Factors:")
            for factor in risk_factors:
                report_lines.append(f"  ⚠️  {factor}")
        
        recommendations = effort_estimate.get('recommendations', [])
        if recommendations:
            report_lines.append("")
            report_lines.append("Recommendations:")
            for rec in recommendations:
                report_lines.append(f"  💡 {rec}")
        report_lines.append("")
        
        report_lines.append("-" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        return output_path
    
    def _generate_summary(self, analysis_results: Dict[str, Any], 
                           risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "total_linting_issues": analysis_results.get('linting', {}).get('total_issues', 0),
            "total_complexity_issues": analysis_results.get('complexity', {}).get('summary', {}).get('high_risk_count', 0),
            "total_duplication_issues": analysis_results.get('duplication', {}).get('summary', {}).get('total_duplicates', 0),
            "total_custom_rule_violations": analysis_results.get('custom_rules', {}).get('summary', {}).get('total', 0),
            "risk_score": risk_assessment['risk_score'],
            "risk_level": risk_assessment['risk_level'],
            "overall_status": "PASS" if risk_assessment['risk_level'] in ["low", "none"] else "FAIL"
        }
    
    def print_summary(self, analysis_results: Dict[str, Any]):
        risk_assessment = self.calculate_risk_score(analysis_results)
        
        print("\n" + "=" * 80)
        print("CODE REVIEW SUMMARY")
        print("=" * 80)
        print(f"Risk Score: {risk_assessment['risk_score']}")
        print(f"Risk Level: {risk_assessment['risk_level'].upper()}")
        print()
        
        print("Issue Breakdown:")
        for severity, count in risk_assessment['issue_counts'].items():
            if count > 0:
                print(f"  {severity.upper()}: {count}")
        
        print()
        if risk_assessment['risk_level'] in ["critical", "high"]:
            print("⚠️  RECOMMENDATION: Significant issues detected. Review recommended before merging.")
        elif risk_assessment['risk_level'] == "medium":
            print("⚠️  RECOMMENDATION: Some issues found. Consider reviewing.")
        else:
            print("✅ RECOMMENDATION: Code quality looks good.")
        print("=" * 80 + "\n")
