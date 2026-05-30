import logging
import threading
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from es_ilm_tool.lifecycle import LifecycleEngine
from es_ilm_tool.metrics import MetricsExporter
from es_ilm_tool.audit import AuditLogger
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class ILMJob:
    def __init__(self, job_id: str, name: str, func, interval_seconds: int, enabled: bool = True):
        self.job_id = job_id
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run = None
        self.last_status = None
        self.run_count = 0
        self.error_count = 0

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "last_status": self.last_status,
            "run_count": self.run_count,
            "error_count": self.error_count,
        }


class ILMScheduler:
    def __init__(self):
        self.engine = LifecycleEngine()
        self.metrics = MetricsExporter()
        self.audit = AuditLogger()
        from es_ilm_tool.ccr import CCRManager
        self.ccr_manager = CCRManager()
        self._scheduler = BackgroundScheduler()
        self._jobs = {}
        self._lock = threading.Lock()
        self._setup_default_jobs()

    def _setup_default_jobs(self):
        self.add_job(
            job_id="auto_lifecycle",
            name="Auto Lifecycle Management",
            func=self._run_auto_lifecycle,
            interval_seconds=config.SCHEDULER_INTERVAL_SECONDS,
        )
        self.add_job(
            job_id="metrics_update",
            name="Metrics Update",
            func=self._run_metrics_update,
            interval_seconds=30,
        )
        self.add_job(
            job_id="auto_rebuild",
            name="Auto Index Rebuild",
            func=self._run_auto_rebuild,
            interval_seconds=config.REBUILD_INTERVAL_SECONDS,
            enabled=config.REBUILD_ENABLE_AUTO,
        )
        self.add_job(
            job_id="ccr_sync",
            name="CCR Hot Index Sync",
            func=self._run_ccr_sync,
            interval_seconds=300,
            enabled=config.CCR_ENABLED,
        )

    def add_job(self, job_id: str, name: str, func, interval_seconds: int, enabled: bool = True):
        job = ILMJob(job_id, name, func, interval_seconds, enabled)
        self._jobs[job_id] = job

    def remove_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
            del self._jobs[job_id]
            return True
        return False

    def enable_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
            return True
        return False

    def list_jobs(self) -> list:
        return [job.to_dict() for job in self._jobs.values()]

    def _run_auto_lifecycle(self):
        job = self._jobs.get("auto_lifecycle")
        if not job or not job.enabled:
            return

        try:
            logger.info("Running auto lifecycle management...")
            result = self.engine.auto_lifecycle(pattern="*", dry_run=False)
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "success"
            job.run_count += 1

            executed = result.get("executed_actions", {})
            for action_name, action_list in executed.items():
                for action_result in action_list:
                    index_name = action_result.get("index", "")
                    success = action_result.get("success", False)
                    self.audit.log(
                        action=action_name,
                        target=index_name,
                        status="success" if success else "error",
                        source="scheduler",
                        details=action_result,
                    )

                    if action_name == "rollover":
                        self.metrics.record_rollover(index_name, success)
                    elif action_name == "freeze":
                        self.metrics.record_freeze(index_name, success)
                    elif action_name == "delete":
                        self.metrics.record_delete(index_name, success)
                    elif action_name.startswith("migrate_to_"):
                        tier = action_name.replace("migrate_to_", "")
                        self.metrics.record_migrate(index_name, tier, success)

            logger.info("Auto lifecycle completed: %s", result.get("recommended_actions", {}))
        except Exception as e:
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "error"
            job.error_count += 1
            logger.error("Auto lifecycle job failed: %s", e)

    def _run_metrics_update(self):
        job = self._jobs.get("metrics_update")
        if not job or not job.enabled:
            return

        try:
            self.metrics.update_all_metrics()
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "success"
            job.run_count += 1
        except Exception as e:
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "error"
            job.error_count += 1
            logger.error("Metrics update job failed: %s", e)

    def _run_auto_rebuild(self):
        job = self._jobs.get("auto_rebuild")
        if not job or not job.enabled:
            return

        try:
            logger.info("Running auto rebuild for fragmented indices...")
            result = self.engine.auto_rebuild(pattern="*", dry_run=False)
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "success"
            job.run_count += 1

            for rebuild_result in result.get("rebuild_results", []):
                index_name = rebuild_result.get("index", "")
                success = rebuild_result.get("success", False)
                self.audit.log(
                    action="rebuild",
                    target=index_name,
                    status="success" if success else "error",
                    source="scheduler",
                    details=rebuild_result,
                )

            logger.info("Auto rebuild completed: %d candidates, %d processed",
                        result.get("total_candidates", 0), result.get("processed", 0))
        except Exception as e:
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "error"
            job.error_count += 1
            logger.error("Auto rebuild job failed: %s", e)

    def _run_ccr_sync(self):
        job = self._jobs.get("ccr_sync")
        if not job or not job.enabled:
            return

        try:
            logger.info("Running CCR sync for hot indices...")
            result = self.ccr_manager.auto_create_followers(dry_run=False)
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "success"
            job.run_count += 1

            for ccr_result in result.get("results", []):
                index_name = ccr_result.get("index", "")
                success = ccr_result.get("success", True)
                self.audit.log(
                    action="ccr_follow",
                    target=index_name,
                    status="success" if success else "error",
                    source="scheduler",
                    details=ccr_result,
                )

            logger.info("CCR sync completed: %d candidates, %d results",
                        result.get("candidates_count", 0), len(result.get("results", [])))
        except Exception as e:
            job.last_run = datetime.now(tz=timezone.utc).isoformat()
            job.last_status = "error"
            job.error_count += 1
            logger.error("CCR sync job failed: %s", e)

    def start(self):
        for job_id, job in self._jobs.items():
            if job.enabled:
                self._scheduler.add_job(
                    job.func,
                    trigger=IntervalTrigger(seconds=job.interval_seconds),
                    id=job.job_id,
                    name=job.name,
                    replace_existing=True,
                )
                logger.info("Scheduled job: %s (interval: %ds)", job.name, job.interval_seconds)

        self._scheduler.start()
        logger.info("ILM Scheduler started")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("ILM Scheduler stopped")

    def trigger_job(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"Job {job_id} not found"}

        try:
            job.func()
            return {"success": True, "job_id": job_id, "status": job.last_status}
        except Exception as e:
            return {"success": False, "job_id": job_id, "error": str(e)}

    def get_status(self) -> dict:
        running = self._scheduler.running
        return {
            "scheduler_running": running,
            "jobs": self.list_jobs(),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
