from datetime import datetime, timedelta
from sqlalchemy import func
import logging
from database import SessionLocal
import models
from log_config import log_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogRotationManager:
    @staticmethod
    def rotate_task_logs(db, task_id: int):
        if not log_settings.enable_rotation:
            return

        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            return

        log_count = db.query(func.count(models.TaskLog.id)).filter(
            models.TaskLog.task_id == task_id
        ).scalar()

        if log_count > log_settings.max_logs_per_task:
            logs_to_delete = log_count - log_settings.max_logs_per_task
            subquery = db.query(models.TaskLog.id).filter(
                models.TaskLog.task_id == task_id
            ).order_by(models.TaskLog.started_at.asc()).limit(logs_to_delete).subquery()
            
            deleted = db.query(models.TaskLog).filter(
                models.TaskLog.id.in_(subquery)
            ).delete(synchronize_session=False)
            
            logger.info(f"Rotated {deleted} logs for task {task_id}")

        if log_settings.max_log_age_days:
            cutoff_date = datetime.utcnow() - timedelta(days=log_settings.max_log_age_days)
            old_logs = db.query(models.TaskLog).filter(
                models.TaskLog.task_id == task_id,
                models.TaskLog.started_at < cutoff_date
            )
            
            deleted_count = old_logs.delete(synchronize_session=False)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} logs older than {log_settings.max_log_age_days} days for task {task_id}")

    @staticmethod
    def rotate_all_logs(db):
        if not log_settings.enable_rotation:
            return

        total_logs = db.query(func.count(models.TaskLog.id)).scalar()
        if total_logs > log_settings.max_total_logs:
            logs_to_delete = total_logs - log_settings.max_total_logs
            subquery = db.query(models.TaskLog.id).order_by(
                models.TaskLog.started_at.asc()
            ).limit(logs_to_delete).subquery()
            
            deleted = db.query(models.TaskLog).filter(
                models.TaskLog.id.in_(subquery)
            ).delete(synchronize_session=False)
            
            logger.info(f"Global rotation: deleted {deleted} oldest logs")

        if log_settings.max_log_age_days:
            cutoff_date = datetime.utcnow() - timedelta(days=log_settings.max_log_age_days)
            old_logs = db.query(models.TaskLog).filter(
                models.TaskLog.started_at < cutoff_date
            )
            
            deleted_count = old_logs.delete(synchronize_session=False)
            if deleted_count > 0:
                logger.info(f"Age-based rotation: deleted {deleted_count} logs older than {log_settings.max_log_age_days} days")

    @staticmethod
    def on_log_created(db, task_id: int):
        LogRotationManager.rotate_task_logs(db, task_id)
        LogRotationManager.rotate_all_logs(db)
        db.commit()


def perform_rotation_cleanup():
    db = SessionLocal()
    try:
        LogRotationManager.rotate_all_logs(db)
        db.commit()
        logger.info("Scheduled log rotation completed")
    except Exception as e:
        logger.error(f"Log rotation failed: {e}")
        db.rollback()
    finally:
        db.close()