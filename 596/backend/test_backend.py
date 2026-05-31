import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    from scanner.config import ScanConfig, Vulnerability, ScanResult
    print("✓ scanner.config imported")
except Exception as e:
    print(f"✗ scanner.config failed: {e}")
    sys.exit(1)

try:
    from scanner.request_engine import RequestEngine
    print("✓ scanner.request_engine imported")
except Exception as e:
    print(f"✗ scanner.request_engine failed: {e}")
    sys.exit(1)

try:
    from scanner.vulnerability_detector import VulnerabilityDetector
    print("✓ scanner.vulnerability_detector imported")
except Exception as e:
    print(f"✗ scanner.vulnerability_detector failed: {e}")
    sys.exit(1)

try:
    from scanner.scan_manager import ScanManager
    print("✓ scanner.scan_manager imported")
except Exception as e:
    print(f"✗ scanner.scan_manager failed: {e}")
    sys.exit(1)

try:
    from scanner.report_generator import ReportGenerator
    print("✓ scanner.report_generator imported")
except Exception as e:
    print(f"✗ scanner.report_generator failed: {e}")
    sys.exit(1)

print("\nTesting models...")
config = ScanConfig(target_url="http://test.com")
print(f"✓ ScanConfig created: {config.target_url}")

vuln = Vulnerability(
    type="SQL Injection",
    severity="high",
    endpoint="/test",
    method="GET",
    payload="' OR 1=1 --",
    evidence="SQL error",
    description="Test vuln",
    recommendation="Fix it"
)
print(f"✓ Vulnerability created: {vuln.type}")

result = ScanResult(
    target_url="http://test.com",
    scan_time="2024-01-01",
    total_requests=100,
    vulnerabilities=[vuln],
    scan_status="completed"
)
print(f"✓ ScanResult created with {len(result.vulnerabilities)} vulnerabilities")

print("\nTesting report generator...")
html_report = ReportGenerator.generate_html_report(result)
print(f"✓ HTML report generated ({len(html_report)} chars)")

md_report = ReportGenerator.generate_markdown_report(result)
print(f"✓ Markdown report generated ({len(md_report)} chars)")

json_report = ReportGenerator.generate_json_report(result)
print(f"✓ JSON report generated ({len(json_report)} chars)")

print("\n" + "="*50)
print("All tests passed! Backend is working correctly.")
print("="*50)
