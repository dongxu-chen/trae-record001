import asyncio
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

@dataclass
class Vulnerability:
    vulnerability_id: str
    severity: Severity
    title: str
    description: str
    package_name: str
    installed_version: str
    fixed_version: str
    cvss_score: Optional[float] = None
    references: List[str] = None

    def __post_init__(self):
        if self.references is None:
            self.references = []

class TrivyScanner:
    def __init__(self, trivy_path: str = "trivy", cache_dir: str = "/tmp/trivy-cache", timeout: int = 300):
        self.trivy_path = trivy_path
        self.cache_dir = cache_dir
        self.timeout = timeout

    async def check_availability(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                self.trivy_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Trivy not available: {e}")
            return False

    async def scan_image(self, image_name: str, scan_types: List[str] = None) -> Dict[str, Any]:
        if scan_types is None:
            scan_types = ["vuln", "config", "secret"]

        scan_results = {
            "vulnerabilities": [],
            "misconfigurations": [],
            "secrets": [],
            "summary": {
                "total_vulnerabilities": 0,
                "total_misconfigurations": 0,
                "total_secrets": 0,
                "by_severity": {
                    "CRITICAL": 0,
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0,
                    "UNKNOWN": 0
                }
            }
        }

        try:
            cmd = [
                self.trivy_path,
                "image",
                "--cache-dir", self.cache_dir,
                "--format", "json",
                "--scanners", ",".join(scan_types),
                image_name
            ]

            logger.info(f"Running Trivy scan for {image_name}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=self.timeout
            )

            if proc.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"Trivy scan failed for {image_name}: {error_msg}")
                raise Exception(f"Trivy scan failed: {error_msg[:200]}")

            raw_results = json.loads(stdout.decode('utf-8', errors='ignore'))
            return self._parse_trivy_results(raw_results, scan_results)

        except asyncio.TimeoutError:
            logger.error(f"Trivy scan timed out for {image_name}")
            raise Exception("Scan timed out")
        except Exception as e:
            logger.error(f"Error scanning {image_name}: {e}")
            raise

    def _parse_trivy_results(self, raw_results: Dict, scan_results: Dict) -> Dict:
        results = raw_results.get("Results", [])
        
        for result in results:
            target = result.get("Target", "unknown")
            
            vulns = result.get("Vulnerabilities", [])
            for vuln in vulns:
                vulnerability = {
                    "id": vuln.get("VulnerabilityID", ""),
                    "severity": vuln.get("Severity", "UNKNOWN").upper(),
                    "title": vuln.get("Title", ""),
                    "description": vuln.get("Description", ""),
                    "package": vuln.get("PkgName", ""),
                    "installed_version": vuln.get("InstalledVersion", ""),
                    "fixed_version": vuln.get("FixedVersion", ""),
                    "cvss_score": self._extract_cvss_score(vuln),
                    "references": vuln.get("References", []),
                    "target": target
                }
                scan_results["vulnerabilities"].append(vulnerability)
                
                severity = vulnerability["severity"]
                if severity in scan_results["summary"]["by_severity"]:
                    scan_results["summary"]["by_severity"][severity] += 1

            misconfigs = result.get("Misconfigurations", [])
            for misconfig in misconfigs:
                scan_results["misconfigurations"].append({
                    "id": misconfig.get("ID", ""),
                    "type": misconfig.get("Type", ""),
                    "title": misconfig.get("Title", ""),
                    "description": misconfig.get("Description", ""),
                    "severity": misconfig.get("Severity", "UNKNOWN").upper(),
                    "message": misconfig.get("Message", ""),
                    "resolution": misconfig.get("Resolution", ""),
                    "target": target
                })

            secrets = result.get("Secrets", [])
            for secret in secrets:
                scan_results["secrets"].append({
                    "rule_id": secret.get("RuleID", ""),
                    "category": secret.get("Category", ""),
                    "severity": secret.get("Severity", "UNKNOWN").upper(),
                    "title": secret.get("Title", ""),
                    "target": secret.get("Target", target),
                    "start_line": secret.get("StartLine", 0),
                    "end_line": secret.get("EndLine", 0)
                })

        scan_results["summary"]["total_vulnerabilities"] = len(scan_results["vulnerabilities"])
        scan_results["summary"]["total_misconfigurations"] = len(scan_results["misconfigurations"])
        scan_results["summary"]["total_secrets"] = len(scan_results["secrets"])

        return scan_results

    def _extract_cvss_score(self, vuln: Dict) -> Optional[float]:
        cvss = vuln.get("CVSS", {})
        if isinstance(cvss, dict):
            for source in ["nvd", "redhat", "debian"]:
                if source in cvss and "V3Score" in cvss[source]:
                    return cvss[source]["V3Score"]
        return None

    async def get_db_status(self) -> Dict[str, Any]:
        try:
            cmd = [self.trivy_path, "image", "--help"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return {"available": True}
        except Exception as e:
            return {"available": False, "error": str(e)}
