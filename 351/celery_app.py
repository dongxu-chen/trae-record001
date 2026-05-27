from celery import Celery
from celery.schedules import crontab
from config import Config

celery = Celery(
    'spam_filter',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'tasks.classify_email': {'queue': 'classification'},
        'tasks.train_model': {'queue': 'training'},
        'tasks.update_reputation': {'queue': 'reputation'},
        'tasks.process_feedback': {'queue': 'feedback'},
        'tasks.online_learn_single': {'queue': 'training'},
        'tasks.incremental_model_update': {'queue': 'training'},
        'tasks.scheduled_hourly_update': {'queue': 'scheduled'},
    },
    beat_schedule={
        'hourly-model-update': {
            'task': 'tasks.scheduled_hourly_update',
            'schedule': crontab(minute=0, hour=f'*/{Config.MODEL_UPDATE_INTERVAL_HOURS}'),
        },
    } if Config.ONLINE_LEARNING_ENABLED else {}
)

celery.autodiscover_tasks(['app.tasks'])
