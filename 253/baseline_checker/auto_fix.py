import logging
from typing import Dict, List, Optional, Tuple
from .ssh_client import SSHClient
from .data_store import DataStore

logger = logging.getLogger(__name__)


class AutoFix:
    AUTO_FIXABLE_TYPES = ["file_permission", "file_content", "sysctl", "ssh_config"]
    
    AUTO_FIXABLE_CATEGORIES = {
        "critical": False,
        "high": True,
        "medium": True,
        "low": True
    }

    def __init__(self, ssh_client: SSHClient, data_store: DataStore = None):
        self.ssh_client = ssh_client
        self.data_store = data_store
        self.fix_results: List[Dict] = []

    def is_auto_fixable(self, check_result: Dict) -> bool:
        check_type = check_result.get("check_type", "")
        severity = check_result.get("severity", "medium")
        fix_command = check_result.get("fix_command", "")
        
        if check_type not in self.AUTO_FIXABLE_TYPES:
            return False
        
        if not self.AUTO_FIXABLE_CATEGORIES.get(severity, True):
            return False
        
        if not fix_command or fix_command.startswith("#"):
            return False
        
        if "<" in fix_command and ">" in fix_command:
            return False
        
        return True

    def get_fixable_checks(self, results: List[Dict], 
                           include_categories: List[str] = None) -> List[Dict]:
        failed = [r for r in results if r["status"] == "fail"]
        
        if include_categories:
            failed = [r for r in failed 
                     if r.get("category", "") in include_categories]
        
        return [r for r in failed if self.is_auto_fixable(r)]

    def execute_fix(self, check_result: Dict) -> Dict:
        check_id = check_result.get("id")
        check_name = check_result.get("name")
        fix_command = check_result.get("fix_command", "")
        severity = check_result.get("severity", "medium")
        
        result = {
            "check_id": check_id,
            "check_name": check_name,
            "fix_command": fix_command,
            "success": False,
            "output": "",
            "error": ""
        }
        
        if not self.is_auto_fixable(check_result):
            result["error"] = "This check is not auto-fixable"
            return result
        
        logger.info(f"Executing fix for {check_id}: {check_name}")
        logger.info(f"Command: {fix_command}")
        
        try:
            exit_code, output, error = self.ssh_client.execute_command(fix_command)
            
            result["success"] = exit_code == 0
            result["output"] = output
            result["error"] = error
            
            if exit_code == 0:
                logger.info(f"Fix {check_id} succeeded")
            else:
                logger.warning(f"Fix {check_id} failed with exit code {exit_code}: {error}")
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Fix {check_id} exception: {str(e)}")
        
        if self.data_store:
            self.data_store.save_fix_record(
                hostname=self.ssh_client.hostname,
                check_id=check_id,
                check_name=check_name,
                fix_command=fix_command,
                success=result["success"],
                output=result.get("output", "") + result.get("error", "")
            )
        
        self.fix_results.append(result)
        return result

    def fix_all(self, results: List[Dict], 
                include_severity: List[str] = None,
                exclude_ids: List[str] = None,
                dry_run: bool = False) -> Tuple[List[Dict], List[Dict]]:
        fixable = self.get_fixable_checks(results)
        
        if include_severity:
            fixable = [f for f in fixable 
                      if f.get("severity", "") in include_severity]
        
        if exclude_ids:
            fixable = [f for f in fixable 
                      if f.get("id", "") not in exclude_ids]
        
        executed = []
        skipped = []
        
        for check in fixable:
            if dry_run:
                skipped.append({
                    "check_id": check["id"],
                    "check_name": check["name"],
                    "fix_command": check["fix_command"],
                    "reason": "Dry run mode"
                })
                continue
            
            result = self.execute_fix(check)
            if result["success"]:
                executed.append(result)
            else:
                skipped.append({
                    "check_id": check["id"],
                    "check_name": check["name"],
                    "fix_command": check["fix_command"],
                    "reason": result.get("error", "Failed")
                })
        
        return executed, skipped

    def generate_fix_preview(self, results: List[Dict]) -> Dict:
        fixable = self.get_fixable_checks(results)
        
        preview = {
            "total_failed": len([r for r in results if r["status"] == "fail"]),
            "auto_fixable": len(fixable),
            "by_severity": {},
            "fixes": []
        }
        
        for check in fixable:
            severity = check.get("severity", "medium")
            if severity not in preview["by_severity"]:
                preview["by_severity"][severity] = 0
            preview["by_severity"][severity] += 1
            
            preview["fixes"].append({
                "id": check["id"],
                "name": check["name"],
                "severity": severity,
                "category": check.get("category", ""),
                "fix_command": check["fix_command"],
                "message": check.get("message", "")
            })
        
        return preview

    def verify_fixes(self, check_engine, 
                     original_results: List[Dict]) -> List[Dict]:
        fixed_ids = [r["check_id"] for r in self.fix_results if r["success"]]
        checks_to_verify = [r for r in original_results 
                           if r["id"] in fixed_ids]
        
        if not checks_to_verify:
            return []
        
        logger.info(f"Verifying {len(checks_to_verify)} fixes...")
        
        all_checks = check_engine.baseline.get("checks", {})
        check_map = {}
        for category, checks in all_checks.items():
            for check in checks:
                check_map[check["id"]] = check
        
        verification_results = []
        for orig_result in checks_to_verify:
            check_id = orig_result["id"]
            check_def = check_map.get(check_id)
            if not check_def:
                continue
            
            new_result = check_engine._run_single_check(check_def)
            new_result["category"] = orig_result.get("category", "")
            
            verification_results.append({
                "check_id": check_id,
                "check_name": orig_result["name"],
                "original_status": orig_result["status"],
                "new_status": new_result["status"],
                "fixed": new_result["status"] == "pass",
                "original_value": orig_result["actual_value"],
                "new_value": new_result["actual_value"]
            })
        
        return verification_results
