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


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.ml.prepare_training_data',
              max_retries=3, default_retry_delay=60, time_limit=1800)
def prepare_training_data(self, dag_id, run_id, task_id, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Preparing ML training data")
    logger.info(f"Input params: {kwargs}")
    time.sleep(random.uniform(5, 15))
    result = {
        'status': 'success',
        'training_samples': random.randint(10000, 100000),
        'validation_samples': random.randint(1000, 10000),
        'feature_count': random.randint(50, 500),
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Training data prepared: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.ml.train_model',
              max_retries=2, default_retry_delay=300, time_limit=7200)
def train_model(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Starting model training")
    logger.info(f"Upstream result: {upstream_result}")
    model_type = kwargs.get('model_type', 'xgboost')
    time.sleep(random.uniform(10, 30))
    result = {
        'status': 'success',
        'model_type': model_type,
        'model_path': f'/models/{dag_id}/{run_id}/model.pkl',
        'training_loss': round(random.uniform(0.01, 0.1), 4),
        'epochs': random.randint(50, 200),
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Model training completed: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.ml.evaluate_model',
              max_retries=3, default_retry_delay=30, time_limit=600)
def evaluate_model(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Evaluating model")
    logger.info(f"Upstream result: {upstream_result}")
    time.sleep(random.uniform(3, 10))
    result = {
        'status': 'success',
        'accuracy': round(random.uniform(0.85, 0.99), 4),
        'precision': round(random.uniform(0.84, 0.98), 4),
        'recall': round(random.uniform(0.82, 0.97), 4),
        'f1_score': round(random.uniform(0.83, 0.98), 4),
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Model evaluation completed: {result}")
    return result


@shared_task(bind=True, base=TaskBase, name='celery_app.tasks.ml.deploy_model',
              max_retries=2, default_retry_delay=120, time_limit=1800)
def deploy_model(self, dag_id, run_id, task_id, upstream_result=None, **kwargs):
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Deploying model to production")
    logger.info(f"Upstream result: {upstream_result}")
    target_env = kwargs.get('target_env', 'production')
    time.sleep(random.uniform(5, 15))
    result = {
        'status': 'success',
        'deployed_to': target_env,
        'endpoint': f'/api/v1/predict/{dag_id}',
        'version': run_id,
    }
    logger.info(f"[{dag_id}:{run_id}:{task_id}] Model deployed: {result}")
    return result
