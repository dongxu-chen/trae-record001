import os
from urllib.parse import urlparse
from celery import Celery
from kombu import Queue, Exchange
from dotenv import load_dotenv

load_dotenv()

TASK_PRIORITY_HIGH = 9
TASK_PRIORITY_NORMAL = 5
TASK_PRIORITY_LOW = 1

QUEUE_HIGH = 'image_tasks_high'
QUEUE_NORMAL = 'image_tasks'
QUEUE_LOW = 'image_tasks_low'

def _get_redis_pool_size():
    return int(os.getenv('REDIS_POOL_SIZE', '20'))

def _get_redis_retry_options():
    return {
        'socket_timeout': 30,
        'socket_connect_timeout': 10,
        'socket_keepalive': True,
        'retry_on_timeout': True,
        'health_check_interval': 30,
        'max_connections': _get_redis_pool_size()
    }

def _get_task_queues():
    exchange = Exchange('image_tasks', type='direct')
    return [
        Queue(QUEUE_HIGH, exchange, routing_key=QUEUE_HIGH, queue_arguments={'x-max-priority': 10}),
        Queue(QUEUE_NORMAL, exchange, routing_key=QUEUE_NORMAL, queue_arguments={'x-max-priority': 10}),
        Queue(QUEUE_LOW, exchange, routing_key=QUEUE_LOW, queue_arguments={'x-max-priority': 10}),
    ]

def _get_task_routes():
    return {
        'tasks.process_thumbnail': {
            'queue': QUEUE_NORMAL,
            'routing_key': QUEUE_NORMAL
        },
        'tasks.process_filter': {
            'queue': QUEUE_NORMAL,
            'routing_key': QUEUE_NORMAL
        },
        'tasks.batch_process': {
            'queue': QUEUE_NORMAL,
            'routing_key': QUEUE_NORMAL
        },
    }

def get_queue_for_priority(priority):
    if priority is None:
        return QUEUE_NORMAL, TASK_PRIORITY_NORMAL
    
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        return QUEUE_NORMAL, TASK_PRIORITY_NORMAL
    
    if priority >= 7:
        return QUEUE_HIGH, min(priority, TASK_PRIORITY_HIGH)
    elif priority <= 3:
        return QUEUE_LOW, max(priority, TASK_PRIORITY_LOW)
    else:
        return QUEUE_NORMAL, priority

def make_celery(app=None):
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    backend_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    redis_options = _get_redis_retry_options()
    
    celery = Celery(
        'image_processor',
        broker=broker_url,
        backend=backend_url
    )

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,
        task_soft_time_limit=240,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_disable_rate_limits=True,
        result_expires=3600,
        result_persistent=False,
        broker_pool_limit=_get_redis_pool_size(),
        redis_max_connections=_get_redis_pool_size(),
        broker_transport_options=redis_options,
        redis_backend_transport_options={
            **redis_options,
            'result_chord_retry_interval': 2,
            'result_chord_retry_backoff': True
        },
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_queue=QUEUE_NORMAL,
        task_default_routing_key=QUEUE_NORMAL,
        task_default_exchange='image_tasks',
        task_default_exchange_type='direct',
        task_queues=_get_task_queues(),
        task_routes=_get_task_routes(),
        task_default_priority=TASK_PRIORITY_NORMAL,
        worker_direct=True
    )

    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery

celery = make_celery()
