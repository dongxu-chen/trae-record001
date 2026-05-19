import os
from celery import Celery
from kombu import Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agile_pm.settings')

app = Celery('agile_pm')

app.conf.task_queues = (
    Queue('default', routing_key='task.#'),
    Queue('high', routing_key='high.#'),
    Queue('periodic', routing_key='periodic.#'),
)

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'tasks'
app.conf.task_default_exchange_type = 'topic'
app.conf.task_default_routing_key = 'task.default'

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
