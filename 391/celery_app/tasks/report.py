import time
import random
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class TaskBase:
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {self.name} [{task_id}] succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name} [{task_id}] failed: {exc}\n{einfo}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {self.name} [{task_id}] retrying after failure: {exc}")


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.report.generate_daily_report',
              max_retries=3, default_retry_delay=30, time_limit=600)
def generate_daily_report(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting daily report generation")
    logger.info(f"Upstream result: {upstream_result}")
    time.sleep(random.uniform(3, 8))
    result = {
        'status': 'success',
        'report_type': 'daily',
        'report_url': f'/reports/daily/{run_id}.pdf',
        'records_included': upstream_result.get('records_loaded', 0) if upstream_result else 0,
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Daily report generated: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.report.generate_weekly_report',
              max_retries=3, default_retry_delay=60, time_limit=1200)
def generate_weekly_report(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting weekly report generation")
    logger.info(f"Upstream result: {upstream_result}")
    time.sleep(random.uniform(5, 12))
    result = {
        'status': 'success',
        'report_type': 'weekly',
        'report_url': f'/reports/weekly/{run_id}.pdf',
        'summary': 'Weekly performance metrics summary',
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Weekly report generated: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.report.send_report_notification',
              max_retries=3, default_retry_delay=10, time_limit=120)
def send_report_notification(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Sending report notification")
    logger.info(f"Upstream result: {upstream_result}")
    recipients = kwargs.get('recipients', ['admin@example.com'])
    time.sleep(random.uniform(1, 3))
    result = {
        'status': 'success',
        'notified': recipients,
        'report_url': upstream_result.get('report_url', '') if upstream_result else '',
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Notification sent: {result}")
    return result
