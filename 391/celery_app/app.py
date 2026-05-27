from celery import Celery
from celery.signals import task_failure, task_success, task_retry
import os

BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://:redis123@localhost:6379/1')
RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://:redis123@localhost:6379/2')

app = Celery('task_scheduler', broker=BROKER_URL, backend=RESULT_BACKEND)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=200000,
    task_default_queue='celery',
    task_default_exchange='task_exchange',
    task_default_routing_key='celery',
    task_queues={
        'celery': {
            'exchange': 'task_exchange',
            'exchange_type': 'direct',
            'routing_key': 'celery',
        },
        'etl': {
            'exchange': 'task_exchange',
            'exchange_type': 'direct',
            'routing_key': 'etl',
        },
        'report': {
            'exchange': 'task_exchange',
            'exchange_type': 'direct',
            'routing_key': 'report',
        },
        'ml': {
            'exchange': 'task_exchange',
            'exchange_type': 'direct',
            'routing_key': 'ml',
        },
        'dead_letter': {
            'exchange': 'task_exchange',
            'exchange_type': 'direct',
            'routing_key': 'dead_letter',
        },
    },
    task_routes={
        'celery_app.tasks.etl.*': {'queue': 'etl'},
        'celery_app.tasks.report.*': {'queue': 'report'},
        'celery_app.tasks.ml.*': {'queue': 'ml'},
        'celery_app.dead_letter.*': {'queue': 'dead_letter'},
    },
    beat_schedule={
        'cleanup-expired-dlq': {
            'task': 'celery_app.dead_letter.cleanup_expired_dlq',
            'schedule': 3600.0,
            'options': {'queue': 'dead_letter'},
        },
    },
)


from celery_app.tasks.handlers import (
    on_task_failure_handler,
    on_task_success_handler,
    on_task_retry_handler,
)

task_failure.connect(on_task_failure_handler)
task_success.connect(on_task_success_handler)
task_retry.connect(on_task_retry_handler)
