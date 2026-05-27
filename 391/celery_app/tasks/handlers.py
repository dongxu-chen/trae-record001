from celery.utils.log import get_task_logger
from models.task_model import get_db_session, TaskExecutionLog, DeadLetterQueue, TaskDefinition
from datetime import datetime, timedelta
from celery_app.backoff import compute_exponential_backoff, compute_next_retry_time

logger = get_task_logger(__name__)


def on_task_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo, **other_kwargs):
    dag_id = kwargs.get('dag_id', 'unknown')
    run_id = kwargs.get('run_id', 'unknown')
    task_name = kwargs.get('task_id', sender.name)

    session = get_db_session()
    try:
        task_def = session.query(TaskDefinition).filter_by(
            task_module=sender.name.rsplit('.', 1)[0],
            task_function=sender.name.rsplit('.', 1)[-1]
        ).first()

        max_retries = task_def.max_retries if task_def else 3
        current_retry = kwargs.get('retry_count', 0)
        retry_delay = compute_exponential_backoff(task_name, current_retry + 1)
        next_retry_time = datetime.now() + timedelta(seconds=retry_delay)

        log_entry = TaskExecutionLog(
            dag_id=dag_id,
            task_id=task_name,
            run_id=run_id,
            celery_task_id=task_id,
            execution_date=datetime.now(),
            status='FAILURE' if current_retry >= max_retries else 'RETRY',
            attempt=kwargs.get('attempt', current_retry + 1),
            worker_name=sender.request.hostname if sender.request else 'unknown',
            input_params=kwargs,
            error_message=str(exception),
            error_traceback=str(traceback),
            retry_count=current_retry,
            next_retry_time=next_retry_time,
        )
        session.add(log_entry)
        session.commit()

        if current_retry >= max_retries:
            default_ttl = 604800
            dlq_entry = DeadLetterQueue(
                celery_task_id=task_id,
                dag_id=dag_id,
                task_id=task_name,
                run_id=run_id,
                task_module=sender.name.rsplit('.', 1)[0],
                task_function=sender.name.rsplit('.', 1)[-1],
                input_params=kwargs,
                error_message=str(exception),
                error_traceback=str(traceback),
                total_retries=current_retry,
                original_queued_at=datetime.now(),
                dead_lettered_at=datetime.now(),
                ttl_seconds=default_ttl,
                expires_at=datetime.now() + timedelta(seconds=default_ttl),
                status='PENDING',
            )
            session.add(dlq_entry)
            session.commit()
            logger.error(
                f"Task {sender.name} [{task_id}] moved to DLQ after {current_retry} retries, "
                f"TTL={default_ttl}s, expires at {dlq_entry.expires_at}"
            )
        else:
            logger.warning(
                f"Task {sender.name} [{task_id}] failed (attempt {current_retry + 1}/{max_retries}), "
                f"next retry in {retry_delay:.1f}s at {next_retry_time}"
            )

    except Exception as e:
        logger.error(f"Error in failure handler: {e}")
        session.rollback()
    finally:
        session.close()


def on_task_success_handler(sender, result, task_id, args, kwargs, **other_kwargs):
    dag_id = kwargs.get('dag_id', 'unknown')
    run_id = kwargs.get('run_id', 'unknown')
    task_name = kwargs.get('task_id', sender.name)

    session = get_db_session()
    try:
        log_entry = TaskExecutionLog(
            dag_id=dag_id,
            task_id=task_name,
            run_id=run_id,
            celery_task_id=task_id,
            execution_date=datetime.now(),
            status='SUCCESS',
            attempt=kwargs.get('attempt', 1),
            worker_name=sender.request.hostname if sender.request else 'unknown',
            input_params=kwargs,
            output_result=result if isinstance(result, dict) else {'result': str(result)},
            retry_count=kwargs.get('retry_count', 0),
        )
        session.add(log_entry)
        session.commit()
        logger.info(f"Task {sender.name} [{task_id}] success logged")
    except Exception as e:
        logger.error(f"Error in success handler: {e}")
        session.rollback()
    finally:
        session.close()


def on_task_retry_handler(sender, request, reason, **kwargs):
    dag_id = kwargs.get('dag_id', 'unknown') if kwargs else 'unknown'
    task_name = kwargs.get('task_id', sender.name) if kwargs else sender.name
    retry_count = request.retries if hasattr(request, 'retries') else 0

    delay = compute_exponential_backoff(task_name, retry_count + 1)
    next_time = datetime.now() + timedelta(seconds=delay)
    logger.info(
        f"Task {sender.name} [{request.id}] retry #{retry_count + 1} scheduled, "
        f"delay={delay:.1f}s, next at {next_time}"
    )
