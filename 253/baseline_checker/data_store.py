import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DataStore:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.scans_dir = self.base_dir / "scans"
        self.baselines_dir = self.base_dir / "baselines"
        self.fixes_dir = self.base_dir / "fixes"
        
        for d in [self.scans_dir, self.baselines_dir, self.fixes_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_scan_result(self, hostname: str, results: List[Dict], summary: Dict, 
                        template_name: str) -> str:
        scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{scan_id}.json"
        filepath = self.scans_dir / filename
        
        data = {
            "scan_id": scan_id,
            "hostname": hostname,
            "template": template_name,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "results": results
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved scan result: {filepath}")
        return str(filepath)

    def get_scan_history(self, hostname: str = None, limit: int = 10) -> List[Dict]:
        files = sorted(self.scans_dir.glob("*.json"), reverse=True)
        
        if hostname:
            files = [f for f in files if f.name.startswith(hostname)]
        
        history = []
        for f in files[:limit]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    history.append({
                        "scan_id": data.get("scan_id"),
                        "hostname": data.get("hostname"),
                        "template": data.get("template"),
                        "timestamp": data.get("timestamp"),
                        "summary": data.get("summary"),
                        "file": str(f)
                    })
            except Exception as e:
                logger.warning(f"Failed to load scan history {f}: {e}")
        
        return history

    def get_scan_result(self, scan_id: str) -> Optional[Dict]:
        files = self.scans_dir.glob(f"*_{scan_id}.json")
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except Exception as e:
                logger.warning(f"Failed to load scan {scan_id}: {e}")
        return None

    def save_baseline_version(self, template_path: str, version: str, 
                               description: str = "") -> str:
        template_name = Path(template_path).name
        version_file = self.baselines_dir / f"{template_name}.versions.json"
        
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        version_entry = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "content": content
        }
        
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                versions = json.load(f)
        else:
            versions = []
        
        versions.append(version_entry)
        
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(versions, f, indent=2, ensure_ascii=False)
        
        backup_file = self.baselines_dir / f"{template_name}_{version}.yaml"
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Saved baseline version {version} for {template_name}")
        return str(backup_file)

    def get_baseline_versions(self, template_name: str) -> List[Dict]:
        version_file = self.baselines_dir / f"{template_name}.versions.json"
        if not version_file.exists():
            return []
        
        with open(version_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def rollback_baseline(self, template_name: str, version: str, 
                          target_path: str) -> bool:
        versions = self.get_baseline_versions(template_name)
        target_version = next((v for v in versions if v["version"] == version), None)
        
        if not target_version:
            logger.error(f"Version {version} not found for {template_name}")
            return False
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(target_version["content"])
        
        logger.info(f"Rolled back {template_name} to version {version}")
        return True

    def save_fix_record(self, hostname: str, check_id: str, check_name: str,
                        fix_command: str, success: bool, output: str = "") -> str:
        fix_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{fix_id}.json"
        filepath = self.fixes_dir / filename
        
        data = {
            "fix_id": fix_id,
            "hostname": hostname,
            "check_id": check_id,
            "check_name": check_name,
            "fix_command": fix_command,
            "success": success,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)

    def get_fix_history(self, hostname: str = None, limit: int = 20) -> List[Dict]:
        files = sorted(self.fixes_dir.glob("*.json"), reverse=True)
        
        if hostname:
            files = [f for f in files if f.name.startswith(hostname)]
        
        history = []
        for f in files[:limit]:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    history.append(json.load(fp))
            except Exception as e:
                logger.warning(f"Failed to load fix history {f}: {e}")
        
        return history
