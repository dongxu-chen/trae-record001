import os
import subprocess
import json
import re
from typing import Dict, List, Any, Optional


class LintingAnalyzer:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
    def run_pylint(self, file_path: str, config_file: str = None) -> Dict[str, Any]:
        if not file_path.endswith('.py'):
            return {"issues": [], "summary": {"error": 0, "warning": 0, "convention": 0, "refactor": 0}}
        
        try:
            cmd = ["pylint", file_path, "--output-format=json"]
            if config_file and os.path.exists(config_file):
                cmd.extend(["--rcfile", config_file])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            issues = []
            if result.stdout.strip():
                try:
                    pylint_output = json.loads(result.stdout)
                    for item in pylint_output:
                        issues.append({
                            "type": "pylint",
                            "file": item.get("path", file_path),
                            "line": item.get("line", 0),
                            "column": item.get("column", 0),
                            "severity": self._map_pylint_severity(item.get("type", "")),
                            "rule_id": item.get("message-id", ""),
                            "message": item.get("message", ""),
                            "symbol": item.get("symbol", "")
                        })
                except json.JSONDecodeError:
                    pass
            
            summary = self._summarize_issues(issues)
            return {"issues": issues, "summary": summary}
            
        except Exception as e:
            return {"issues": [], "summary": {"error": 0, "warning": 0, "convention": 0, "refactor": 0}, "error": str(e)}
    
    def _map_pylint_severity(self, pylint_type: str) -> str:
        severity_map = {
            "error": "critical",
            "warning": "high",
            "convention": "low",
            "refactor": "medium",
            "fatal": "critical"
        }
        return severity_map.get(pylint_type, "low")
    
    def run_eslint(self, file_path: str, config_file: str = None) -> Dict[str, Any]:
        if not any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
            return {"issues": [], "summary": {"error": 0, "warning": 0}}
        
        try:
            eslint_path = self._find_eslint()
            if not eslint_path:
                return {"issues": [], "summary": {"error": 0, "warning": 0}, "error": "ESLint not found"}
            
            cmd = [eslint_path, file_path, "--format", "json"]
            if config_file and os.path.exists(config_file):
                cmd.extend(["--config", config_file])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            issues = []
            if result.stdout.strip():
                try:
                    eslint_output = json.loads(result.stdout)
                    for file_result in eslint_output:
                        for msg in file_result.get("messages", []):
                            issues.append({
                                "type": "eslint",
                                "file": file_result.get("filePath", file_path),
                                "line": msg.get("line", 0),
                                "column": msg.get("column", 0),
                                "severity": self._map_eslint_severity(msg.get("severity", 1)),
                                "rule_id": msg.get("ruleId", ""),
                                "message": msg.get("message", "")
                            })
                except json.JSONDecodeError:
                    pass
            
            summary = self._summarize_issues(issues)
            return {"issues": issues, "summary": summary}
            
        except Exception as e:
            return {"issues": [], "summary": {"error": 0, "warning": 0}, "error": str(e)}
    
    def _find_eslint(self) -> Optional[str]:
        local_eslint = os.path.join(os.getcwd(), "node_modules", ".bin", "eslint")
        if os.path.exists(local_eslint) or os.path.exists(local_eslint + ".cmd"):
            return local_eslint
        
        try:
            subprocess.run(["eslint", "--version"], capture_output=True)
            return "eslint"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def _map_eslint_severity(self, eslint_severity: int) -> str:
        if eslint_severity == 2:
            return "high"
        elif eslint_severity == 1:
            return "medium"
        return "low"
    
    def _summarize_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity in summary:
                summary[severity] += 1
        return summary
    
    def analyze_directory(self, directory: str, run_pylint: bool = True, 
                          run_eslint: bool = True) -> Dict[str, Any]:
        all_issues = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                if run_pylint and file.endswith('.py'):
                    pylint_config = self.config.get('linting', {}).get('pylint', {}).get('config_file')
                    result = self.run_pylint(file_path, pylint_config)
                    all_issues.extend(result.get("issues", []))
                
                if run_eslint and any(file.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
                    eslint_config = self.config.get('linting', {}).get('eslint', {}).get('config_file')
                    result = self.run_eslint(file_path, eslint_config)
                    all_issues.extend(result.get("issues", []))
        
        summary = self._summarize_issues(all_issues)
        return {"issues": all_issues, "summary": summary, "total_issues": len(all_issues)}
