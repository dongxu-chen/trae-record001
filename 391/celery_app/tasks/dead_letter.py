from celery import shared_task
from celery.utils.log import get_task_logger
from models.task_model import get_db_session, DeadLetterQueue, TaskRerunRecord
from datetime import datetime, timedelta
import importlib

logger = get_task_logger(__name__)


@shared_task(bind=True, name='celery_app.dead_letter.process_dead_letter',
              max_retries=3, default_retry_delay=60, queue='dead_letter')
def process_dead_letter(self, dlq_id, **kwargs):
    logger.info(f"Processing dead letter queue entry: {dlq_id}")
    session = get_db_session()
    try:
        dlq_entry = session.query(DeadLetterQueue).filter_by(dlq_id=dlq_id, status='PENDING').first()
        if not dlq_entry:
            logger.warning(f"DLQ entry {dlq_id} not found or already processed")
            return {'status': 'skipped', 'reason': 'entry not found'}

        if dlq_entry.expires_at and dlq_entry.expires_at < datetime.now():
            dlq_entry.status = 'DISCARDED'
            dlq_entry.notes = f"TTL expired at {dlq_entry.expires_at}, auto-cleaned"
            session.commit()
            logger.warning(f"DLQ entry {dlq_id} expired (TTL={dlq_entry.ttl_seconds}s), auto-discarded")
            return {'status': 'expired', 'dlq_id': dlq_id}

        task_module = dlq_entry.task_module
        task_function = dlq_entry.task_function
        input_params = dlq_entry.input_params or {}

        logger.info(f"Re-processing task: {task_module}.{task_function}")
        logger.info(f"Input params: {input_params}")

        module = importlib.import_module(task_module)
        task_func = getattr(module, task_function)

        result = task_func(**input_params)

        dlq_entry.status = 'REPROCESSED'
        dlq_entry.reprocessed_at = datetime.now()
        dlq_entry.reprocessed_by = kwargs.get('triggered_by', 'system')

        rerun_record = TaskRerunRecord(
            original_log_id=0,
            original_celery_id=dlq_entry.celery_task_id,
            dag_id=dlq_entry.dag_id,
            task_id=dlq_entry.task_id,
            run_id=dlq_entry.run_id,
            rerun_type='DLQ_REPROCESS',
            rerun_celery_id=self.request.id,
            rerun_status='SUCCESS',
            triggered_by=kwargs.get('triggered_by', 'system'),
        )
        session.add(rerun_record)
        session.commit()

        logger.info(f"DLQ entry {dlq_id} reprocessed successfully")
        return {'status': 'success', 'dlq_id': dlq_id, 'result': result}

    except Exception as e:
        logger.error(f"Error reprocessing DLQ entry {dlq_id}: {e}")
        session.rollback()
        raise self.retry(exc=e)
    finally:
        session.close()


@shared_task(bind=True, name='celery_app.dead_letter.batch_reprocess_dead_letters',
              max_retries=1, queue='dead_letter')
def batch_reprocess_dead_letters(self, task_id=None, dag_id=None, limit=10, **kwargs):
    logger.info(f"Batch reprocessing dead letters - task_id={task_id}, dag_id={dag_id}, limit={limit}")
    session = get_db_session()
    try:
        query = session.query(DeadLetterQueue).filter_by(status='PENDING')
        query = query.filter(
            (DeadLetterQueue.expires_at == None) | (DeadLetterQueue.expires_at >= datetime.now())
        )
        if task_id:
            query = query.filter_by(task_id=task_id)
        if dag_id:
            query = query.filter_by(dag_id=dag_id)

        dlq_entries = query.order_by(DeadLetterQueue.dead_lettered_at.desc()).limit(limit).all()

        results = []
        for entry in dlq_entries:
            try:
                r = process_dead_letter.delay(dlq_id=entry.dlq_id, triggered_by=kwargs.get('triggered_by', 'batch'))
                results.append({'dlq_id': entry.dlq_id, 'rerun_celery_id': r.id})
            except Exception as e:
                logger.error(f"Failed to reprocess DLQ entry {entry.dlq_id}: {e}")
                results.append({'dlq_id': entry.dlq_id, 'error': str(e)})

        logger.info(f"Batch reprocessing submitted: {len(results)} entries")
        return {'status': 'submitted', 'count': len(results), 'entries': results}

    finally:
        session.close()


@shared_task(bind=True, name='celery_app.dead_letter.discard_dead_letter', queue='dead_letter')
def discard_dead_letter(self, dlq_id, reason='', **kwargs):
    logger.info(f"Discarding dead letter queue entry: {dlq_id}")
    session = get_db_session()
    try:
        dlq_entry = session.query(DeadLetterQueue).filter_by(dlq_id=dlq_id).first()
        if not dlq_entry:
            return {'status': 'not_found', 'dlq_id': dlq_id}

        dlq_entry.status = 'DISCARDED'
        dlq_entry.notes = reason or f"Discarded by {kwargs.get('triggered_by', 'system')}"
        session.commit()

        logger.info(f"DLQ entry {dlq_id} discarded: {reason}")
        return {'status': 'discarded', 'dlq_id': dlq_id}

    except Exception as e:
        logger.error(f"Error discarding DLQ entry {dlq_id}: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(bind=True, name='celery_app.dead_letter.cleanup_expired_dlq', queue='dead_letter')
def cleanup_expired_dlq(self, **kwargs):
    logger.info("Running DLQ TTL cleanup task")
    session = get_db_session()
    try:
        now = datetime.now()
        expired_entries = session.query(DeadLetterQueue).filter(
            DeadLetterQueue.status == 'PENDING',
            DeadLetterQueue.expires_at != None,
            DeadLetterQueue.expires_at < now
        ).all()

        cleaned_count = 0
        for entry in expired_entries:
            entry.status = 'DISCARDED'
            entry.notes = f"TTL expired at {entry.expires_at}, auto-cleaned by cleanup job"
            cleaned_count += 1
            logger.warning(
                f"DLQ entry {entry.dlq_id} expired "
                f"(dead_lettered_at={entry.dead_lettered_at}, ttl={entry.ttl_seconds}s), auto-discarded"
            )

        session.commit()
        logger.info(f"DLQ TTL cleanup completed: {cleaned_count} expired entries discarded")
        return {'status': 'success', 'cleaned_count': cleaned_count}

    except Exception as e:
        logger.error(f"Error in DLQ TTL cleanup: {e}")
        session.rollback()
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()


@shared_task(bind=True, name='celery_app.dead_letter.update_dlq_ttl', queue='dead_letter')
def update_dlq_ttl(self, dlq_id, ttl_seconds=None, **kwargs):
    logger.info(f"Updating TTL for DLQ entry: {dlq_id}, ttl={ttl_seconds}")
    session = get_db_session()
    try:
        dlq_entry = session.query(DeadLetterQueue).filter_by(dlq_id=dlq_id).first()
        if not dlq_entry:
            return {'status': 'not_found', 'dlq_id': dlq_id}

        if ttl_seconds is not None:
            dlq_entry.ttl_seconds = ttl_seconds
            dlq_entry.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        session.commit()
        logger.info(f"DLQ entry {dlq_id} TTL updated: {ttl_seconds}s, expires at {dlq_entry.expires_at}")
        return {'status': 'success', 'dlq_id': dlq_id, 'ttl_seconds': ttl_seconds, 'expires_at': str(dlq_entry.expires_at)}

    except Exception as e:
        logger.error(f"Error updating DLQ TTL: {e}")
        session.rollback()
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()
