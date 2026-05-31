import asyncio
import uuid
import logging
import docker
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from backend.config.config import settings
from backend.scanners.trivy_scanner import TrivyScanner
from backend.scanners.trivy_db_updater import TrivyDBUpdater
from backend.scanners.sensitive_scanner import SensitiveDataScanner
from backend.engine.rules_engine import RulesEngine

logger = logging.getLogger(__name__)

class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScanJob:
    job_id: str
    image_names: List[str]
    status: ScanStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    scan_types: List[str] = field(default_factory=lambda: ["vulnerabilities", "secrets", "rules"])

class ScanManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.jobs: Dict[str, ScanJob] = {}
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCANS)
        
        self.trivy_scanner = TrivyScanner(
            trivy_path=settings.TRIVY_PATH,
            cache_dir=settings.TRIVY_CACHE_DIR,
            timeout=settings.TRIVY_TIMEOUT
        )
        
        self.trivy_db_updater = TrivyDBUpdater(
            trivy_path=settings.TRIVY_PATH,
            cache_dir=settings.TRIVY_CACHE_DIR,
            db_dir=settings.TRIVY_DB_DIR,
            auto_update=settings.TRIVY_DB_AUTO_UPDATE,
            update_interval_hours=settings.TRIVY_DB_UPDATE_INTERVAL_HOURS
        )
        
        self.sensitive_scanner = SensitiveDataScanner(
            patterns_file=settings.SENSITIVE_PATTERNS_FILE
        )
        
        self.rules_engine = RulesEngine(
            rules_file=settings.RULES_CONFIG_FILE
        )
        
        self.docker_client = None
        self._init_docker_client()

    def _init_docker_client(self):
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Docker client: {e}")
            self.docker_client = None

    async def create_scan_job(self, image_names: List[str], scan_types: List[str] = None) -> str:
        job_id = str(uuid.uuid4())
        
        job = ScanJob(
            job_id=job_id,
            image_names=image_names,
            status=ScanStatus.PENDING,
            created_at=datetime.now(),
            scan_types=scan_types or ["vulnerabilities", "secrets", "rules"]
        )
        
        self.jobs[job_id] = job
        
        asyncio.create_task(self._execute_scan_job(job_id))
        
        return job_id

    async def _execute_scan_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        job.status = ScanStatus.RUNNING
        job.started_at = datetime.now()

        try:
            async with self.semaphore:
                for image_name in job.image_names:
                    try:
                        result = await self._scan_single_image(image_name, job.scan_types)
                        job.results[image_name] = result
                    except Exception as e:
                        error_msg = f"Failed to scan {image_name}: {str(e)}"
                        logger.error(error_msg)
                        job.errors.append(error_msg)
                        job.results[image_name] = {"error": str(e)}

            job.status = ScanStatus.COMPLETED if not job.errors else ScanStatus.FAILED
        except Exception as e:
            job.status = ScanStatus.FAILED
            job.errors.append(f"Scan job failed: {str(e)}")
            logger.error(f"Scan job {job_id} failed: {e}")
        finally:
            job.completed_at = datetime.now()

    async def _scan_single_image(self, image_name: str, scan_types: List[str]) -> Dict[str, Any]:
        result = {
            "image_name": image_name,
            "scan_time": datetime.now().isoformat(),
            "summary": {},
            "vulnerabilities": None,
            "secrets": None,
            "rules": None
        }

        if "vulnerabilities" in scan_types:
            try:
                vuln_result = await self.trivy_scanner.scan_image(image_name)
                result["vulnerabilities"] = vuln_result
                result["summary"]["vulnerabilities"] = vuln_result["summary"]
            except Exception as e:
                logger.warning(f"Vulnerability scan failed for {image_name}: {e}")
                result["vulnerabilities"] = {"error": str(e)}

        if "secrets" in scan_types and self.docker_client:
            try:
                secrets_result = await self.sensitive_scanner.scan_image(
                    image_name, 
                    self.docker_client
                )
                result["secrets"] = secrets_result
                result["summary"]["secrets"] = secrets_result["summary"]
            except Exception as e:
                logger.warning(f"Secrets scan failed for {image_name}: {e}")
                result["secrets"] = {"error": str(e)}

        if "rules" in scan_types and self.docker_client:
            try:
                image_config = self._get_image_config(image_name)
                rules_result = await self.rules_engine.evaluate_image(
                    image_config, 
                    image_name
                )
                result["rules"] = rules_result
                result["summary"]["rules"] = rules_result["summary"]
            except Exception as e:
                logger.warning(f"Rules scan failed for {image_name}: {e}")
                result["rules"] = {"error": str(e)}

        result["overall_risk_score"] = self._calculate_overall_risk(result)
        result["summary"]["overall_risk_score"] = result["overall_risk_score"]

        return result

    def _get_image_config(self, image_name: str) -> Dict:
        try:
            image = self.docker_client.images.get(image_name)
            return image.attrs
        except Exception as e:
            logger.warning(f"Failed to get image config: {e}")
            return {}

    def _calculate_overall_risk(self, result: Dict) -> float:
        total_score = 0.0
        weight_sum = 0.0

        if result.get("vulnerabilities") and "summary" in result["vulnerabilities"]:
            vuln_summary = result["vulnerabilities"]["summary"]
            by_sev = vuln_summary.get("by_severity", {})
            vuln_score = (
                by_sev.get("CRITICAL", 0) * 10 +
                by_sev.get("HIGH", 0) * 5 +
                by_sev.get("MEDIUM", 0) * 2 +
                by_sev.get("LOW", 0) * 1
            )
            max_vuln = 100
            total_score += (min(vuln_score, max_vuln) / max_vuln) * 40
            weight_sum += 40

        if result.get("secrets") and "summary" in result["secrets"]:
            secrets_summary = result["secrets"]["summary"]
            by_sev = secrets_summary.get("by_severity", {})
            secrets_score = (
                by_sev.get("CRITICAL", 0) * 10 +
                by_sev.get("HIGH", 0) * 5 +
                by_sev.get("MEDIUM", 0) * 2 +
                by_sev.get("LOW", 0) * 1
            )
            max_secrets = 50
            total_score += (min(secrets_score, max_secrets) / max_secrets) * 30
            weight_sum += 30

        if result.get("rules") and "summary" in result["rules"]:
            rules_score = result["rules"]["summary"].get("risk_score", 0)
            total_score += (rules_score / 100) * 30
            weight_sum += 30

        if weight_sum > 0:
            return round(total_score, 2)
        return 0.0

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "image_names": job.image_names,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "errors": job.errors,
            "progress": self._calculate_progress(job)
        }

    def get_job_results(self, job_id: str) -> Optional[Dict]:
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "image_names": job.image_names,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "results": job.results,
            "errors": job.errors
        }

    def _calculate_progress(self, job: ScanJob) -> Dict:
        total = len(job.image_names)
        completed = len(job.results)
        percentage = int((completed / total) * 100) if total > 0 else 0
        
        return {
            "total_images": total,
            "completed_images": completed,
            "percentage": percentage
        }

    def list_jobs(self, limit: int = 100) -> List[Dict]:
        jobs_list = sorted(
            self.jobs.values(),
            key=lambda j: j.created_at,
            reverse=True
        )[:limit]
        
        return [
            {
                "job_id": job.job_id,
                "image_names": job.image_names,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs_list
        ]

    async def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or job.status in [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]:
            return False
        
        job.status = ScanStatus.CANCELLED
        job.completed_at = datetime.now()
        return True

    def get_scanner_status(self) -> Dict:
        return {
            "trivy_available": asyncio.run(self.trivy_scanner.check_availability()),
            "docker_available": self.docker_client is not None,
            "max_concurrent_scans": settings.MAX_CONCURRENT_SCANS,
            "active_scans": len([j for j in self.jobs.values() if j.status == ScanStatus.RUNNING]),
            "trivy_db": self.trivy_db_updater.get_update_status(),
            "sensitive_scanner": self.sensitive_scanner.get_scanner_stats()
        }

    async def start_db_auto_update(self):
        await self.trivy_db_updater.start_auto_update()
        return {"status": "started"}

    async def stop_db_auto_update(self):
        await self.trivy_db_updater.stop_auto_update()
        return {"status": "stopped"}

    async def update_trivy_db(self, force: bool = False) -> Dict:
        result = await self.trivy_db_updater.update_database(force=force)
        return result

    async def get_trivy_db_status(self) -> Dict:
        update_status = self.trivy_db_updater.get_update_status()
        integrity = await self.trivy_db_updater.check_database_integrity()
        return {
            "update_status": update_status,
            "integrity": integrity
        }

    async def export_trivy_db(self, export_path: str) -> Dict:
        result = await self.trivy_db_updater.export_offline_db(export_path)
        return result

    async def import_trivy_db(self, import_path: str) -> Dict:
        result = await self.trivy_db_updater.import_offline_db(import_path)
        return result
