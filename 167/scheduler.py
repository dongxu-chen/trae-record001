from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import logging
import asyncio
from typing import Dict
from executor import TaskExecutor
from database import SessionLocal
import crud
import schemas
from webhook import WebhookNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_cron_expression(cron_expression: str) -> Dict[str, str]:
    parts = cron_expression.strip().split()
    if len(parts) != 6:
        raise ValueError("Cron expression must have 6 fields (second minute hour day month weekday)")
    
    return {
        'second': parts[0],
        'minute': parts[1],
        'hour': parts[2],
        'day': parts[3],
        'month': parts[4],
        'day_of_week': parts[5]
    }


class SchedulerManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.job_ids: Dict[int, str] = {}
        self._running = False

    def start(self):
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def shutdown(self):
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Scheduler shutdown")

    @staticmethod
    def _send_webhook(task, task_log, status: str):
        if not task.webhook_url:
            return
        
        try:
            payload = WebhookNotifier.build_task_payload(task, task_log, status)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                WebhookNotifier.send_notification(
                    url=task.webhook_url,
                    method=task.webhook_method or "POST",
                    headers=task.webhook_headers,
                    payload=payload
                )
            )
            loop.close()
        except Exception as e:
            logger.error(f"Failed to send webhook for task {task.id}: {e}")

    @staticmethod
    def _trigger_dependent_tasks(task_id: int):
        db = SessionLocal()
        try:
            dependents = crud.get_dependent_tasks(db, task_id)
            for dep in dependents:
                deps_met, _ = crud.check_dependencies_met(db, dep.task_id)
                if deps_met:
                    logger.info(f"All dependencies met for task {dep.task_id}, triggering execution")
                    SchedulerManager.schedule_immediate_execution(dep.task_id, triggered_by=task_id)
        finally:
            db.close()

    @staticmethod
    def schedule_immediate_execution(task_id: int, triggered_by: int = None, retry_attempt: int = 0):
        scheduler_manager.scheduler.add_job(
            SchedulerManager._execute_job_with_retry,
            trigger=DateTrigger(run_date=datetime.now()),
            args=[task_id, triggered_by, retry_attempt],
            id=f"immediate_{task_id}_{datetime.now().timestamp()}",
            replace_existing=False
        )

    @staticmethod
    def _execute_job_with_retry(task_id: int, triggered_by: int = None, retry_attempt: int = 0):
        db = SessionLocal()
        try:
            task = crud.get_task(db, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if retry_attempt == 0:
                deps_met, failed_deps = crud.check_dependencies_met(db, task_id)
                if not deps_met:
                    logger.info(f"Task {task_id} dependencies not met: {failed_deps}")
                    return

            logger.info(f"Executing task: {task.name} (ID: {task_id}), timeout: {task.timeout}s, attempt: {retry_attempt}")

            log_create = schemas.TaskLogCreate(
                task_id=task_id,
                status="running",
                started_at=datetime.utcnow(),
                retry_attempt=retry_attempt,
                triggered_by=triggered_by
            )
            task_log = crud.create_task_log(db, log_create)

            output, error, execution_time = TaskExecutor.execute_task(
                task.task_type,
                task.script_content,
                task.timeout
            )

            status = "success" if error is None else "failed"
            crud.update_task_log(
                db,
                task_log.id,
                status=status,
                output=output,
                error=error,
                completed_at=datetime.utcnow(),
                execution_time=execution_time
            )

            logger.info(f"Task {task.name} (ID: {task_id}) completed with status: {status}")

            if task.webhook_url:
                SchedulerManager._send_webhook(task, task_log, status)

            if status == "success":
                SchedulerManager._trigger_dependent_tasks(task_id)
            else:
                if retry_attempt < task.retry_count:
                    logger.info(f"Scheduling retry {retry_attempt + 1}/{task.retry_count} for task {task_id} in {task.retry_delay}s")
                    retry_time = datetime.now() + timedelta(seconds=task.retry_delay)
                    scheduler_manager.scheduler.add_job(
                        SchedulerManager._execute_job_with_retry,
                        trigger=DateTrigger(run_date=retry_time),
                        args=[task_id, triggered_by, retry_attempt + 1],
                        id=f"retry_{task_id}_{retry_attempt + 1}",
                        replace_existing=False
                    )

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
        finally:
            db.close()

    @staticmethod
    def _execute_job(task_id: int):
        SchedulerManager._execute_job_with_retry(task_id)

    def add_task(self, task_id: int, cron_expression: str):
        if task_id in self.job_ids:
            self.remove_task(task_id)

        try:
            cron_params = parse_cron_expression(cron_expression)
            trigger = CronTrigger(**cron_params)
            
            job = self.scheduler.add_job(
                self._execute_job,
                trigger=trigger,
                args=[task_id],
                id=f"task_{task_id}",
                replace_existing=True
            )
            self.job_ids[task_id] = job.id
            logger.info(f"Task {task_id} scheduled with cron: {cron_expression}")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule task {task_id}: {str(e)}")
            return False

    def remove_task(self, task_id: int):
        if task_id in self.job_ids:
            job_id = self.job_ids[task_id]
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            del self.job_ids[task_id]
            logger.info(f"Task {task_id} removed from scheduler")

    def pause_task(self, task_id: int):
        if task_id in self.job_ids:
            job_id = self.job_ids[task_id]
            if self.scheduler.get_job(job_id):
                self.scheduler.pause_job(job_id)
                logger.info(f"Task {task_id} paused")

    def resume_task(self, task_id: int):
        if task_id in self.job_ids:
            job_id = self.job_ids[task_id]
            if self.scheduler.get_job(job_id):
                self.scheduler.resume_job(job_id)
                logger.info(f"Task {task_id} resumed")

    def get_jobs(self):
        return self.scheduler.get_jobs()

    def load_tasks_from_db(self):
        db = SessionLocal()
        try:
            tasks = crud.get_tasks(db)
            for task in tasks:
                if task.is_active:
                    self.add_task(task.id, task.cron_expression)
            logger.info(f"Loaded {len([t for t in tasks if t.is_active])} active tasks")
        finally:
            db.close()

    def add_log_cleanup_job(self):
        try:
            from log_rotation import perform_rotation_cleanup
            self.scheduler.add_job(
                perform_rotation_cleanup,
                trigger=CronTrigger(hour=1, minute=0),
                id="log_cleanup",
                replace_existing=True
            )
            logger.info("Log cleanup job scheduled (daily at 01:00)")
        except Exception as e:
            logger.error(f"Failed to add log cleanup job: {str(e)}")


scheduler_manager = SchedulerManager()