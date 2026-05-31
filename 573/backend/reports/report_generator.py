import json
import os
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class JUnitReportGenerator:
    @staticmethod
    def generate_junit_report(job_results: Dict, filepath: str) -> str:
        testsuites = ET.Element("testsuites")
        
        job_id = job_results.get("job_id", "unknown")
        results = job_results.get("results", {})
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        total_time = 0
        
        for image_name, image_result in results.items():
            if "error" in image_result:
                continue
            
            testsuite, tests, failures, errors, skipped, time = JUnitReportGenerator._create_testsuite(
                image_name, 
                image_result
            )
            testsuites.append(testsuite)
            
            total_tests += tests
            total_failures += failures
            total_errors += errors
            total_skipped += skipped
            total_time += time
        
        testsuites.set("tests", str(total_tests))
        testsuites.set("failures", str(total_failures))
        testsuites.set("errors", str(total_errors))
        testsuites.set("skipped", str(total_skipped))
        testsuites.set("time", str(round(total_time, 2)))
        
        xml_str = ET.tostring(testsuites, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding='utf-8')
        
        with open(filepath, 'wb') as f:
            f.write(pretty_xml)
        
        return filepath

    @staticmethod
    def _create_testsuite(image_name: str, image_result: Dict) -> tuple:
        testsuite = ET.Element("testsuite")
        safe_name = image_name.replace(':', '_').replace('/', '_').replace('.', '_')
        testsuite.set("name", f"Docker Security Scan - {image_name}")
        testsuite.set("package", f"docker_security.{safe_name}")
        testsuite.set("timestamp", datetime.now().isoformat())
        
        test_cases = []
        
        vuln_cases = JUnitReportGenerator._create_vulnerability_testcases(image_name, image_result)
        test_cases.extend(vuln_cases)
        
        secret_cases = JUnitReportGenerator._create_secrets_testcases(image_name, image_result)
        test_cases.extend(secret_cases)
        
        rule_cases = JUnitReportGenerator._create_rules_testcases(image_name, image_result)
        test_cases.extend(rule_cases)
        
        risk_cases = JUnitReportGenerator._create_risk_testcase(image_name, image_result)
        test_cases.extend(risk_cases)
        
        for tc in test_cases:
            testsuite.append(tc)
        
        tests = len(test_cases)
        failures = sum(1 for tc in test_cases if tc.find('failure') is not None)
        errors = sum(1 for tc in test_cases if tc.find('error') is not None)
        skipped = sum(1 for tc in test_cases if tc.find('skipped') is not None)
        time = 0
        
        testsuite.set("tests", str(tests))
        testsuite.set("failures", str(failures))
        testsuite.set("errors", str(errors))
        testsuite.set("skipped", str(skipped))
        testsuite.set("time", str(time))
        
        return testsuite, tests, failures, errors, skipped, time

    @staticmethod
    def _create_vulnerability_testcases(image_name: str, image_result: Dict) -> List[ET.Element]:
        test_cases = []
        vulns = image_result.get("vulnerabilities", {})
        
        if isinstance(vulns, dict) and "error" not in vulns:
            vulnerabilities = vulns.get("vulnerabilities", [])
            
            if not vulnerabilities:
                tc = ET.Element("testcase")
                tc.set("classname", f"vulnerabilities.{image_name.replace('/', '.')}")
                tc.set("name", "No vulnerabilities found")
                tc.set("time", "0")
                test_cases.append(tc)
            else:
                severity_priority = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
                sorted_vulns = sorted(
                    vulnerabilities[:100],
                    key=lambda v: severity_priority.get(v.get("severity", "UNKNOWN"), 4)
                )
                
                for vuln in sorted_vulns:
                    tc = ET.Element("testcase")
                    vuln_id = vuln.get("id", "UNKNOWN")
                    severity = vuln.get("severity", "UNKNOWN")
                    package = vuln.get("package", "unknown")
                    
                    tc.set("classname", f"vulnerabilities.{image_name.replace('/', '.')}.{package}")
                    tc.set("name", f"{vuln_id} - {severity} - {vuln.get('title', '')[:50]}")
                    tc.set("time", "0")
                    
                    failure = ET.SubElement(tc, "failure")
                    failure.set("message", f"{severity} vulnerability detected: {vuln_id}")
                    failure.set("type", severity)
                    
                    details = (
                        f"CVE ID: {vuln_id}\n"
                        f"Severity: {severity}\n"
                        f"Title: {vuln.get('title', '')}\n"
                        f"Description: {vuln.get('description', '')[:200]}\n"
                        f"Package: {package} {vuln.get('installed_version', '')}\n"
                        f"Fixed Version: {vuln.get('fixed_version', 'Not available')}\n"
                        f"CVSS Score: {vuln.get('cvss_score', 'N/A')}\n"
                        f"Target: {vuln.get('target', image_name)}\n"
                    )
                    failure.text = details
                    
                    test_cases.append(tc)
        
        return test_cases

    @staticmethod
    def _create_secrets_testcases(image_name: str, image_result: Dict) -> List[ET.Element]:
        test_cases = []
        secrets = image_result.get("secrets", {})
        
        if isinstance(secrets, dict) and "error" not in secrets:
            findings = secrets.get("findings", [])
            
            if not findings:
                tc = ET.Element("testcase")
                tc.set("classname", f"secrets.{image_name.replace('/', '.')}")
                tc.set("name", "No sensitive data found")
                tc.set("time", "0")
                test_cases.append(tc)
            else:
                for finding in findings[:50]:
                    tc = ET.Element("testcase")
                    pattern_name = finding.get("pattern_name", "Unknown")
                    severity = finding.get("severity", "MEDIUM")
                    file_path = finding.get("file_path", "unknown")
                    detection_type = finding.get("detection_type", "unknown")
                    
                    safe_classname = file_path.replace('/', '.').replace(':', '_')
                    tc.set("classname", f"secrets.{image_name.replace('/', '.')}.{safe_classname}")
                    tc.set("name", f"{pattern_name} [{detection_type}] in {file_path}")
                    tc.set("time", "0")
                    
                    failure = ET.SubElement(tc, "failure")
                    failure.set("message", f"{severity} sensitive data detected: {pattern_name}")
                    failure.set("type", severity)
                    
                    details = (
                        f"Pattern: {pattern_name}\n"
                        f"Severity: {severity}\n"
                        f"Description: {finding.get('description', '')}\n"
                        f"File: {file_path}\n"
                        f"Line: {finding.get('line_number', 'N/A')}\n"
                        f"Detection Type: {detection_type}\n"
                        f"Category: {finding.get('category', 'unknown')}\n"
                        f"Match: {finding.get('match', '')}\n"
                    )
                    failure.text = details
                    
                    test_cases.append(tc)
        
        return test_cases

    @staticmethod
    def _create_rules_testcases(image_name: str, image_result: Dict) -> List[ET.Element]:
        test_cases = []
        rules = image_result.get("rules", {})
        
        if isinstance(rules, dict) and "error" not in rules:
            rule_results = rules.get("results", [])
            
            for rule in rule_results:
                tc = ET.Element("testcase")
                rule_id = rule.get("rule_id", "UNKNOWN")
                severity = rule.get("severity", "MEDIUM")
                passed = rule.get("passed", True)
                
                tc.set("classname", f"rules.{image_name.replace('/', '.')}.{rule.get('category', 'general')}")
                tc.set("name", f"{rule_id}: {rule.get('rule_name', '')}")
                tc.set("time", "0")
                
                if not passed:
                    failure = ET.SubElement(tc, "failure")
                    failure.set("message", f"{severity} rule violation: {rule_id}")
                    failure.set("type", severity)
                    
                    details = (
                        f"Rule ID: {rule_id}\n"
                        f"Rule Name: {rule.get('rule_name', '')}\n"
                        f"Severity: {severity}\n"
                        f"Category: {rule.get('category', '')}\n"
                        f"Description: {rule.get('description', '')}\n"
                        f"Remediation: {rule.get('remediation', '')}\n"
                    )
                    failure.text = details
                else:
                    pass
        
                test_cases.append(tc)
        
        return test_cases

    @staticmethod
    def _create_risk_testcase(image_name: str, image_result: Dict) -> List[ET.Element]:
        test_cases = []
        risk_score = image_result.get("overall_risk_score", 0)
        
        tc = ET.Element("testcase")
        tc.set("classname", f"risk.{image_name.replace('/', '.')}")
        tc.set("name", f"Overall Risk Score Assessment")
        tc.set("time", "0")
        
        risk_level = "Safe"
        threshold = 0
        if risk_score >= 70:
            risk_level = "Critical"
            threshold = 70
        elif risk_score >= 50:
            risk_level = "High"
            threshold = 50
        elif risk_score >= 30:
            risk_level = "Medium"
            threshold = 30
        elif risk_score > 0:
            risk_level = "Low"
            threshold = 1
        
        if risk_score >= 30:
            failure = ET.SubElement(tc, "failure")
            failure.set("message", f"Risk score {risk_score} exceeds threshold {threshold} ({risk_level})")
            failure.set("type", "RISK_" + risk_level.upper())
            
            details = (
                f"Risk Score: {risk_score}\n"
                f"Risk Level: {risk_level}\n"
                f"Threshold: {threshold}\n"
                f"Image: {image_name}\n"
                f"\n"
                f"Risk Assessment:\n"
                f"- 0-29: Low/Safe\n"
                f"- 30-49: Medium (Action Recommended)\n"
                f"- 50-69: High (Action Required)\n"
                f"- 70+: Critical (Immediate Action Required)\n"
            )
            failure.text = details
        
        test_cases.append(tc)
        return test_cases

class ReportGenerator:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    def generate_json_report(self, job_results: Dict, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_report_{timestamp}.json"
        
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(job_results, f, indent=2, ensure_ascii=False)
        
        return filepath

    def generate_html_report(self, job_results: Dict, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_report_{timestamp}.html"
        
        filepath = os.path.join(self.reports_dir, filename)
        
        template = self.env.get_template("report_template.html")
        
        html_content = template.render(
            job_id=job_results.get("job_id", "unknown"),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results=job_results.get("results", {}),
            overall_stats=self._calculate_overall_stats(job_results),
            get_risk_level=self._get_risk_level
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath

    def generate_junit_report(self, job_results: Dict, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_report_{timestamp}.xml"
        
        filepath = os.path.join(self.reports_dir, filename)
        
        return JUnitReportGenerator.generate_junit_report(job_results, filepath)

    def _calculate_overall_stats(self, job_results: Dict) -> Dict:
        results = job_results.get("results", {})
        total_images = len(results)
        
        total_vulns = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_secrets = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_rules_failed = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_risk_score = 0.0
        
        for image_name, image_result in results.items():
            if isinstance(image_result, dict) and "error" not in image_result:
                vulns = image_result.get("vulnerabilities", {})
                if isinstance(vulns, dict):
                    vuln_sev = vulns.get("summary", {}).get("by_severity", {})
                    for sev in total_vulns:
                        total_vulns[sev] += vuln_sev.get(sev, 0)
                
                secrets = image_result.get("secrets", {})
                if isinstance(secrets, dict):
                    secret_sev = secrets.get("summary", {}).get("by_severity", {})
                    for sev in total_secrets:
                        total_secrets[sev] += secret_sev.get(sev, 0)
                
                rules = image_result.get("rules", {})
                if isinstance(rules, dict):
                    rule_sev = rules.get("summary", {}).get("by_severity", {})
                    for sev in total_rules_failed:
                        total_rules_failed[sev] += rule_sev.get(sev, 0)
                
                total_risk_score += image_result.get("overall_risk_score", 0)
        
        avg_risk_score = round(total_risk_score / total_images, 2) if total_images > 0 else 0
        
        return {
            "total_images": total_images,
            "total_vulnerabilities": sum(total_vulns.values()),
            "vulnerabilities_by_severity": total_vulns,
            "total_secrets": sum(total_secrets.values()),
            "secrets_by_severity": total_secrets,
            "total_rules_failed": sum(total_rules_failed.values()),
            "rules_by_severity": total_rules_failed,
            "avg_risk_score": avg_risk_score
        }

    def _get_risk_level(self, score: float) -> Dict:
        if score >= 70:
            return {"level": "Critical", "color": "#dc3545", "class": "risk-critical"}
        elif score >= 50:
            return {"level": "High", "color": "#fd7e14", "class": "risk-high"}
        elif score >= 30:
            return {"level": "Medium", "color": "#ffc107", "class": "risk-medium"}
        elif score > 0:
            return {"level": "Low", "color": "#28a745", "class": "risk-low"}
        else:
            return {"level": "Safe", "color": "#28a745", "class": "risk-safe"}

    def get_report_list(self) -> List[Dict]:
        reports = []
        for filename in os.listdir(self.reports_dir):
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                reports.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "type": os.path.splitext(filename)[1][1:].upper()
                })
        
        return sorted(reports, key=lambda r: r["created_at"], reverse=True)

    def delete_report(self, filename: str) -> bool:
        filepath = os.path.join(self.reports_dir, filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except Exception as e:
            logger.error(f"Error deleting report: {e}")
        return False
