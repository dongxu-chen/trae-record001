from celery import shared_task
from celery.utils.log import get_task_logger
from models.task_model import get_db_session, TaskExecutionLog, TaskRerunRecord, TaskDefinition
from datetime import datetime
import importlib

logger = get_task_logger(__name__)


@shared_task(bind=True, name='scripts.rerun.rerun_task')
def rerun_task(self, log_id, triggered_by='system', **kwargs):
    logger.info(f"Rerunning task from log entry: {log_id}")
    session = get_db_session()
    try:
        log_entry = session.query(TaskExecutionLog).filter_by(log_id=log_id).first()
        if not log_entry:
            logger.error(f"Log entry {log_id} not found")
            return {'status': 'error', 'reason': 'log entry not found'}

        task_def = session.query(TaskDefinition).filter_by(task_id=log_entry.task_id).first()
        if not task_def:
            logger.error(f"Task definition for {log_entry.task_id} not found")
            return {'status': 'error', 'reason': 'task definition not found'}

        if not task_def.enabled:
            logger.warning(f"Task {log_entry.task_id} is disabled, cannot rerun")
            return {'status': 'error', 'reason': 'task is disabled'}

        input_params = log_entry.input_params or {}
        input_params['dag_id'] = log_entry.dag_id
        input_params['run_id'] = log_entry.run_id
        input_params['task_id'] = log_entry.task_id
        input_params['triggered_by'] = triggered_by

        module_path = task_def.task_module
        func_name = task_def.task_function

        logger.info(f"Rerunning {module_path}.{func_name} with params: {input_params}")

        module = importlib.import_module(module_path)
        task_func = getattr(module, func_name)

        result = task_func(**input_params)

        rerun_record = TaskRerunRecord(
            original_log_id=log_entry.log_id,
            original_celery_id=log_entry.celery_task_id or '',
            dag_id=log_entry.dag_id,
            task_id=log_entry.task_id,
            run_id=log_entry.run_id,
            rerun_type='MANUAL',
            rerun_celery_id=self.request.id,
            rerun_status='SUCCESS',
            triggered_by=triggered_by,
        )
        session.add(rerun_record)
        session.commit()

        logger.info(f"Task rerun completed successfully: {log_id}")
        return {
            'status': 'success',
            'log_id': log_id,
            'original_celery_id': log_entry.celery_task_id,
            'rerun_celery_id': self.request.id,
            'result': result,
        }

    except Exception as e:
        logger.error(f"Error rerunning task {log_id}: {e}")
        session.rollback()
        return {'status': 'error', 'log_id': log_id, 'error': str(e)}
    finally:
        session.close()


@shared_task(bind=True, name='scripts.rerun.batch_rerun_tasks')
def batch_rerun_tasks(self, log_ids, triggered_by='system', **kwargs):
    logger.info(f"Batch rerunning {len(log_ids)} tasks")
    results = []
    for log_id in log_ids:
        try:
            r = rerun_task.delay(log_id=log_id, triggered_by=triggered_by)
            results.append({'log_id': log_id, 'rerun_celery_id': r.id, 'status': 'submitted'})
        except Exception as e:
            logger.error(f"Failed to submit rerun for log {log_id}: {e}")
            results.append({'log_id': log_id, 'status': 'error', 'error': str(e)})

    return {'status': 'submitted', 'count': len(results), 'results': results}


@shared_task(bind=True, name='scripts.rerun.rerun_dag_run')
def rerun_dag_run(self, dag_id, run_id, triggered_by='system', **kwargs):
    logger.info(f"Rerunning entire DAG run: {dag_id}/{run_id}")
    session = get_db_session()
    try:
        log_entries = session.query(TaskExecutionLog).filter_by(
            dag_id=dag_id, run_id=run_id
        ).order_by(TaskExecutionLog.execution_date).all()

        if not log_entries:
            return {'status': 'error', 'reason': 'no log entries found'}

        log_ids = [entry.log_id for entry in log_entries]
        result = batch_rerun_tasks(log_ids=log_ids, triggered_by=triggered_by)
        session.close()
        return {
            'status': 'submitted',
            'dag_id': dag_id,
            'run_id': run_id,
            'task_count': len(log_ids),
            'rerun_result': result,
        }
    finally:
        session.close()
