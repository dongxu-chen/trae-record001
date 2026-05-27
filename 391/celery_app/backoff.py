import math
import random
from datetime import datetime, timedelta
from models.task_model import get_db_session, TaskDefinition, TaskExecutionLog


def compute_exponential_backoff(task_id, retry_count, base_delay=None, max_delay=None):
    session = get_db_session()
    try:
        task_def = session.query(TaskDefinition).filter_by(task_id=task_id).first()
        if task_def:
            base = task_def.retry_delay_sec
            use_backoff = task_def.retry_backoff
            max_d = task_def.retry_backoff_max_sec
        else:
            base = base_delay or 60
            use_backoff = True
            max_d = max_delay or 3600

        if not use_backoff:
            return base

        delay = base * (2 ** (retry_count - 1))
        jitter = random.uniform(0, delay * 0.1)
        delay_with_jitter = delay + jitter
        return min(delay_with_jitter, max_d)
    finally:
        session.close()


def compute_next_retry_time(task_id, retry_count):
    delay = compute_exponential_backoff(task_id, retry_count)
    return datetime.now() + timedelta(seconds=delay)


def retry_with_backoff(self, exc, **kwargs):
    task_id = kwargs.get('task_id', self.name)
    retry_count = self.request.retries if hasattr(self.request, 'retries') else 0
    delay = compute_exponential_backoff(task_id, retry_count)
    next_time = datetime.now() + timedelta(seconds=delay)

    session = get_db_session()
    try:
        dag_id = kwargs.get('dag_id', 'unknown')
        run_id = kwargs.get('run_id', 'unknown')
        log_entry = TaskExecutionLog(
            dag_id=dag_id,
            task_id=task_id,
            run_id=run_id,
            celery_task_id=self.request.id,
            execution_date=datetime.now(),
            status='RETRY',
            attempt=retry_count + 2,
            error_message=str(exc),
            retry_count=retry_count + 1,
            next_retry_time=next_time,
        )
        session.add(log_entry)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    raise self.retry(exc=exc, countdown=delay)
