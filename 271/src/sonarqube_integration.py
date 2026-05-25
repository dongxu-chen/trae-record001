import requests
import subprocess
import os
from typing import Dict, List, Any, Optional


class SonarQubeIntegration:
    def __init__(self, config: Dict[str, Any] = None, sonarqube_url: str = None, token: str = None):
        self.config = config or {}
        self.sonarqube_url = sonarqube_url or self.config.get('sonarqube', {}).get('url', 'http://localhost:9000')
        self.token = token or self.config.get('sonarqube', {}).get('token', '')
        self.project_key = self.config.get('sonarqube', {}).get('project_key', 'project')
        
    def get_project_issues(self, project_key: str = None) -> Dict[str, Any]:
        project_key = project_key or self.project_key
        url = f"{self.sonarqube_url}/api/issues/search"
        params = {
            "componentKeys": project_key,
            "resolved": "false",
            "ps": 500
        }
        
        try:
            response = requests.get(url, params=params, auth=(self.token, ''), timeout=30)
            if response.status_code == 200:
                data = response.json()
                return self._process_sonarqube_issues(data)
            return {"issues": [], "summary": {}, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"issues": [], "summary": {}, "error": str(e)}
    
    def _process_sonarqube_issues(self, data: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        for issue in data.get("issues", []):
            severity = issue.get("severity", "INFO").lower()
            if severity == "blocker":
                severity = "critical"
            elif severity == "major":
                severity = "high"
            elif severity == "minor":
                severity = "medium"
            elif severity == "info":
                severity = "low"
            
            if severity in summary:
                summary[severity] += 1
            
            issues.append({
                "type": "sonarqube",
                "rule": issue.get("rule", ""),
                "severity": severity,
                "component": issue.get("component", ""),
                "line": issue.get("line", 0),
                "message": issue.get("message", ""),
                "type": issue.get("type", ""),
                "debt": issue.get("debt", "")
            })
        
        return {"issues": issues, "summary": summary, "total": len(issues)}
    
    def get_quality_gate_status(self, project_key: str = None) -> Dict[str, Any]:
        project_key = project_key or self.project_key
        url = f"{self.sonarqube_url}/api/qualitygates/project_status"
        params = {"projectKey": project_key}
        
        try:
            response = requests.get(url, params=params, auth=(self.token, ''), timeout=30)
            if response.status_code == 200:
                data = response.json()
                project_status = data.get("projectStatus", {})
                return {
                    "status": project_status.get("status", "UNKNOWN"),
                    "conditions": project_status.get("conditions", []),
                    "periods": project_status.get("periods", [])
                }
            return {"status": "ERROR", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    def get_project_metrics(self, project_key: str = None) -> Dict[str, Any]:
        project_key = project_key or self.project_key
        url = f"{self.sonarqube_url}/api/measures/component"
        params = {
            "component": project_key,
            "metricKeys": "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc"
        }
        
        try:
            response = requests.get(url, params=params, auth=(self.token, ''), timeout=30)
            if response.status_code == 200:
                data = response.json()
                measures = data.get("component", {}).get("measures", [])
                metrics = {}
                for measure in measures:
                    metrics[measure["metric"]] = measure.get("value", "0")
                return metrics
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def run_scanner(self, source_dir: str, project_key: str = None) -> Dict[str, Any]:
        project_key = project_key or self.project_key
        
        sonar_scanner = self._find_sonar_scanner()
        if not sonar_scanner:
            return {"success": False, "error": "SonarQube Scanner not found"}
        
        cmd = [
            sonar_scanner,
            f"-Dsonar.projectKey={project_key}",
            f"-Dsonar.sources={source_dir}",
            f"-Dsonar.host.url={self.sonarqube_url}",
            f"-Dsonar.login={self.token}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=source_dir, timeout=300)
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_sonar_scanner(self) -> Optional[str]:
        candidates = [
            "sonar-scanner",
            "sonar-scanner.bat",
            os.path.join(os.getcwd(), "sonar-scanner", "bin", "sonar-scanner"),
            os.path.join(os.getcwd(), "sonar-scanner", "bin", "sonar-scanner.bat")
        ]
        
        for candidate in candidates:
            try:
                subprocess.run([candidate, "--version"], capture_output=True, timeout=10)
                return candidate
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        return None
