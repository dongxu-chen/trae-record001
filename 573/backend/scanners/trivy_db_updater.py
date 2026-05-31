import asyncio
import os
import logging
import subprocess
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TrivyDBUpdater:
    def __init__(
        self,
        trivy_path: str = "trivy",
        cache_dir: str = "/tmp/trivy-cache",
        db_dir: Optional[str] = None,
        auto_update: bool = True,
        update_interval_hours: int = 24
    ):
        self.trivy_path = trivy_path
        self.cache_dir = cache_dir
        self.db_dir = db_dir or os.path.join(cache_dir, "db")
        self.auto_update = auto_update
        self.update_interval_hours = update_interval_hours
        self.db_metadata_file = os.path.join(self.db_dir, "metadata.json")
        self._update_task: Optional[asyncio.Task] = None
        
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

    async def start_auto_update(self):
        if not self.auto_update:
            logger.info("Trivy DB auto-update is disabled")
            return
        
        if self._update_task and not self._update_task.done():
            logger.warning("Trivy DB auto-update is already running")
            return
        
        logger.info(f"Starting Trivy DB auto-update (interval: {self.update_interval_hours}h)")
        self._update_task = asyncio.create_task(self._auto_update_loop())

    async def stop_auto_update(self):
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            logger.info("Trivy DB auto-update stopped")

    async def _auto_update_loop(self):
        while True:
            try:
                if await self.needs_update():
                    logger.info("Starting scheduled Trivy DB update")
                    result = await self.update_database()
                    if result.get("success"):
                        logger.info(f"Trivy DB updated successfully. Version: {result.get('version', 'unknown')}")
                    else:
                        logger.error(f"Trivy DB update failed: {result.get('error', 'unknown error')}")
                else:
                    logger.info("Trivy DB is up to date, skipping update")
                
                next_update = datetime.now() + timedelta(hours=self.update_interval_hours)
                logger.info(f"Next Trivy DB update scheduled for: {next_update}")
                
                await asyncio.sleep(self.update_interval_hours * 3600)
                
            except asyncio.CancelledError:
                logger.info("Trivy DB auto-update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Trivy DB auto-update loop: {e}")
                await asyncio.sleep(3600)

    async def needs_update(self) -> bool:
        if not os.path.exists(self.db_metadata_file):
            logger.info("Trivy DB metadata not found, needs update")
            return True
        
        try:
            with open(self.db_metadata_file, 'r') as f:
                metadata = json.load(f)
            
            last_update = datetime.fromisoformat(metadata.get("last_update", ""))
            next_update = last_update + timedelta(hours=self.update_interval_hours)
            
            if datetime.now() >= next_update:
                logger.info(f"Trivy DB last updated at {last_update}, needs update")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking Trivy DB update status: {e}")
            return True

    async def update_database(self, force: bool = False) -> Dict[str, Any]:
        result = {
            "success": False,
            "version": None,
            "last_update": None,
            "error": None
        }

        try:
            logger.info("Updating Trivy vulnerability database...")
            
            update_cmd = [
                self.trivy_path,
                "image",
                "--download-db-only",
                "--cache-dir", self.cache_dir
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *update_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
            
            if proc.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                logger.error(f"Trivy DB download failed: {error_msg}")
                result["error"] = error_msg
                return result
            
            db_info = await self._get_database_info()
            
            metadata = {
                "last_update": datetime.now().isoformat(),
                "version": db_info.get("version"),
                "next_update": (datetime.now() + timedelta(hours=self.update_interval_hours)).isoformat()
            }
            
            with open(self.db_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            result["success"] = True
            result["version"] = db_info.get("version")
            result["last_update"] = metadata["last_update"]
            result["next_update"] = metadata["next_update"]
            
            logger.info(f"Trivy DB updated successfully to version: {result['version']}")
            return result
            
        except asyncio.TimeoutError:
            error_msg = "Trivy DB update timed out"
            logger.error(error_msg)
            result["error"] = error_msg
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Trivy DB update failed with exception: {e}")
            result["error"] = error_msg
            return result

    async def _get_database_info(self) -> Dict[str, Any]:
        info = {"version": None, "updated_at": None}
        
        try:
            version_file = os.path.join(self.cache_dir, "db", "trivy.db.metadata")
            if os.path.exists(version_file):
                with open(version_file, 'r') as f:
                    metadata = json.load(f)
                    info["version"] = metadata.get("Version")
                    info["updated_at"] = metadata.get("NextUpdate")
            else:
                cmd = [self.trivy_path, "--version"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                version_output = stdout.decode('utf-8').strip()
                info["version"] = version_output.split('\n')[0] if version_output else None
                
        except Exception as e:
            logger.debug(f"Error getting DB info: {e}")
        
        return info

    def get_update_status(self) -> Dict[str, Any]:
        status = {
            "auto_update_enabled": self.auto_update,
            "update_interval_hours": self.update_interval_hours,
            "last_update": None,
            "next_update": None,
            "version": None,
            "needs_update": False,
            "update_running": False
        }
        
        if self._update_task and not self._update_task.done():
            status["update_running"] = True
        
        try:
            if os.path.exists(self.db_metadata_file):
                with open(self.db_metadata_file, 'r') as f:
                    metadata = json.load(f)
                status["last_update"] = metadata.get("last_update")
                status["next_update"] = metadata.get("next_update")
                status["version"] = metadata.get("version")
        except Exception as e:
            logger.debug(f"Error reading metadata: {e}")
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._check_needs_update_async(status))
            else:
                status["needs_update"] = asyncio.run(self.needs_update())
        except Exception:
            pass
        
        return status

    async def _check_needs_update_async(self, status_dict: Dict):
        try:
            status_dict["needs_update"] = await self.needs_update()
        except Exception:
            pass

    async def check_database_integrity(self) -> Dict[str, Any]:
        result = {
            "valid": False,
            "db_exists": False,
            "db_size": 0,
            "error": None
        }
        
        try:
            db_path = os.path.join(self.cache_dir, "db")
            if os.path.exists(db_path):
                result["db_exists"] = True
                result["db_size"] = self._get_dir_size(db_path)
                
                if result["db_size"] > 1024 * 1024:
                    result["valid"] = True
                else:
                    result["error"] = "Database file too small"
            else:
                result["error"] = "Database directory not found"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result

    def _get_dir_size(self, path: str) -> int:
        total = 0
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += self._get_dir_size(entry.path)
        return total

    async def export_offline_db(self, export_path: str) -> Dict[str, Any]:
        result = {"success": False, "export_path": None, "error": None}
        
        try:
            db_path = os.path.join(self.cache_dir, "db")
            if not os.path.exists(db_path):
                result["error"] = "Database not found"
                return result
            
            os.makedirs(export_path, exist_ok=True)
            
            export_file = os.path.join(
                export_path, 
                f"trivy-db-{datetime.now().strftime('%Y%m%d')}.tar.gz"
            )
            
            cmd = ["tar", "-czf", export_file, "-C", self.cache_dir, "db"]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            
            if proc.returncode == 0:
                result["success"] = True
                result["export_path"] = export_file
                result["size"] = os.path.getsize(export_file)
            else:
                result["error"] = "Failed to create offline DB archive"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result

    async def import_offline_db(self, import_path: str) -> Dict[str, Any]:
        result = {"success": False, "error": None}
        
        try:
            if not os.path.exists(import_path):
                result["error"] = "Offline DB file not found"
                return result
            
            os.makedirs(self.cache_dir, exist_ok=True)
            
            cmd = ["tar", "-xzf", import_path, "-C", self.cache_dir]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            
            if proc.returncode == 0:
                metadata = {
                    "last_update": datetime.now().isoformat(),
                    "source": "offline_import",
                    "source_file": import_path,
                    "next_update": (datetime.now() + timedelta(hours=self.update_interval_hours)).isoformat()
                }
                
                with open(self.db_metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                result["success"] = True
            else:
                result["error"] = "Failed to extract offline DB archive"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
