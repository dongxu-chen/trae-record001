import time
import random
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class TaskBase:
    """任务基类，提供通用的日志记录和上下文处理"""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {self.name} [{task_id}] succeeded with result: {retval}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name} [{task_id}] failed: {exc}\n{einfo}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {self.name} [{task_id}] retrying after failure: {exc}")


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.etl.extract_data',
              max_retries=3, default_retry_delay=30, time_limit=600)
def extract_data(self, dag_id, run_id, task_id, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting data extraction")
    logger.info(f"Input params: {kwargs}")
    time.sleep(random.uniform(2, 5))
    result = {
        'status': 'success',
        'records_extracted': random.randint(1000, 10000),
        'source': 'data_source_a',
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Extraction completed: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.etl.transform_data',
              max_retries=3, default_retry_delay=30, time_limit=1200)
def transform_data(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting data transformation")
    logger.info(f"Upstream result: {upstream_result}")
    time.sleep(random.uniform(3, 8))
    result = {
        'status': 'success',
        'records_transformed': upstream_result.get('records_extracted', 0) if upstream_result else random.randint(500, 8000),
        'transformation_type': 'standardize',
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Transformation completed: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.etl.load_data',
              max_retries=3, default_retry_delay=60, time_limit=1800)
def load_data(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting data loading")
    logger.info(f"Upstream result: {upstream_result}")
    time.sleep(random.uniform(4, 10))
    result = {
        'status': 'success',
        'records_loaded': upstream_result.get('records_transformed', 0) if upstream_result else random.randint(500, 8000),
        'target': 'data_warehouse',
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Loading completed: {result}")
    return result
