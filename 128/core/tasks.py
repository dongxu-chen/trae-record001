from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import connection
from .signals import event_stored
from .event_store import Event

logger = get_task_logger(__name__)


@shared_task(queue='high')
def refresh_materialized_view(view_name: str, concurrently: bool = False) -> None:
    """刷新物化视图"""
    logger.info(f'Refreshing materialized view: {view_name}')

    with connection.cursor() as cursor:
        if concurrently:
            cursor.execute(f'REINDEX MATERIALIZED VIEW CONCURRENTLY {view_name}')
        else:
            cursor.execute(f'REINDEX MATERIALIZED VIEW {view_name}')

    logger.info(f'Materialized view {view_name} refreshed successfully')


@shared_task(queue='high')
def refresh_sprint_materialized_views(sprint_id: int) -> None:
    """刷新Sprint相关的所有物化视图"""
    logger.info(f'Refreshing materialized views for sprint: {sprint_id}')

    views = ['mv_sprint_burndown', 'mv_sprint_dashboard', 'mv_card_read_model']

    for view in views:
        refresh_materialized_view.delay(view)

    logger.info(f'All materialized views refreshed for sprint {sprint_id}')


@shared_task(queue='default')
def handle_event_stored(event_id: int) -> None:
    """处理事件存储后的异步操作"""
    try:
        event = Event.objects.get(id=event_id)
        logger.info(f'Handling event: {event.event_type} for {event.aggregate_type}#{event.aggregate_id}')

        if event.aggregate_type == 'card':
            refresh_materialized_view.delay('mv_card_read_model')

            if event.event_type in ['card_status_changed', 'card_sprint_updated']:
                refresh_materialized_view.delay('mv_sprint_burndown')
                refresh_materialized_view.delay('mv_sprint_dashboard')

        elif event.aggregate_type == 'sprint':
            refresh_materialized_view.delay('mv_sprint_burndown')
            refresh_materialized_view.delay('mv_sprint_dashboard')
            refresh_materialized_view.delay('mv_card_read_model')

    except Event.DoesNotExist:
        logger.error(f'Event {event_id} not found')


def on_event_stored(sender, event, **kwargs):
    """事件存储信号处理器"""
    handle_event_stored.delay(event.id)


# 连接信号
event_stored.connect(on_event_stored, dispatch_uid='event_stored_handler')
