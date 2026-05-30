from celery import Celery
from celery.schedules import crontab
from config import Config

app = Celery(
    'redis_defrag',
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    result_expires=86400,
)

app.conf.beat_schedule = {
    'check-and-defrag-periodically': {
        'task': 'tasks.periodic_defrag_check',
        'schedule': crontab(minute=f'*/{Config.SCHEDULE_INTERVAL_MINUTES}'),
    },
    'daily-fragmentation-report': {
        'task': 'tasks.daily_fragmentation_report',
        'schedule': crontab(hour=0, minute=0),
    },
}

app.autodiscover_tasks(['tasks'])
