import json
from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Dict, Any, List, Optional

User = get_user_model()


class Event(models.Model):
    AGGREGATE_TYPES = [
        ('card', '卡片'),
        ('sprint', 'Sprint'),
        ('project', '项目'),
        ('board', '看板'),
    ]

    EVENT_TYPES = [
        # 卡片相关事件
        ('card_created', '卡片创建'),
        ('card_moved', '卡片移动'),
        ('card_status_changed', '卡片状态变更'),
        ('card_blocked', '卡片标记阻塞'),
        ('card_unblocked', '卡片取消阻塞'),
        ('card_dependency_added', '添加卡片依赖'),
        ('card_dependency_removed', '移除卡片依赖'),
        ('card_updated', '卡片更新'),
        ('card_deleted', '卡片删除'),
        
        # Sprint相关事件
        ('sprint_created', 'Sprint创建'),
        ('sprint_started', 'Sprint开始'),
        ('sprint_completed', 'Sprint完成'),
        ('sprint_card_added', '卡片添加到Sprint'),
        ('sprint_card_removed', '卡片从Sprint移除'),
    ]

    id = models.BigAutoField(primary_key=True)
    aggregate_type = models.CharField(max_length=50, choices=AGGREGATE_TYPES, db_index=True)
    aggregate_id = models.IntegerField(db_index=True, verbose_name='聚合根ID')
    event_type = models.CharField(max_length=100, choices=EVENT_TYPES, db_index=True, verbose_name='事件类型')
    payload = models.JSONField(verbose_name='事件数据')
    metadata = models.JSONField(default=dict, verbose_name='元数据')
    version = models.IntegerField(default=1, verbose_name='版本号')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='events')
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '事件'
        verbose_name_plural = '事件'
        ordering = ['-created_at']
        unique_together = ['aggregate_type', 'aggregate_id', 'version']
        indexes = [
            models.Index(fields=['aggregate_type', 'aggregate_id', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.event_type} - {self.aggregate_type}#{self.aggregate_id} v{self.version}'


class EventStore:
    @staticmethod
    def append_event(
        aggregate_type: str,
        aggregate_id: int,
        event_type: str,
        payload: Dict[str, Any],
        user: Optional[User] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        with transaction.atomic():
            last_event = Event.objects.filter(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id
            ).order_by('-version').first()

            next_version = last_event.version + 1 if last_event else 1

            event = Event.objects.create(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                metadata=metadata or {},
                version=next_version,
                created_by=user
            )

            from .signals import event_stored
            event_stored.send(sender=EventStore, event=event)

            return event

    @staticmethod
    def get_events(
        aggregate_type: str,
        aggregate_id: Optional[int] = None,
        event_type: Optional[str] = None,
        since_version: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        queryset = Event.objects.filter(aggregate_type=aggregate_type)

        if aggregate_id is not None:
            queryset = queryset.filter(aggregate_id=aggregate_id)

        if event_type is not None:
            queryset = queryset.filter(event_type=event_type)

        if since_version is not None:
            queryset = queryset.filter(version__gte=since_version)

        queryset = queryset.order_by('version')

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    @staticmethod
    def reconstruct_aggregate(
        aggregate_type: str,
        aggregate_id: int,
        until_version: Optional[int] = None
    ) -> Dict[str, Any]:
        events = EventStore.get_events(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id
        )

        if until_version:
            events = [e for e in events if e.version <= until_version]

        state = {}
        for event in events:
            state = EventStore.apply_event(state, event)

        return state

    @staticmethod
    def apply_event(state: Dict[str, Any], event: Event) -> Dict[str, Any]:
        new_state = state.copy()

        handlers = {
            'card_created': EventStore._handle_card_created,
            'card_moved': EventStore._handle_card_moved,
            'card_status_changed': EventStore._handle_card_status_changed,
            'card_blocked': EventStore._handle_card_blocked,
            'card_unblocked': EventStore._handle_card_unblocked,
            'card_dependency_added': EventStore._handle_card_dependency_added,
            'card_dependency_removed': EventStore._handle_card_dependency_removed,
            'card_updated': EventStore._handle_card_updated,
            'sprint_created': EventStore._handle_sprint_created,
            'sprint_started': EventStore._handle_sprint_started,
            'sprint_completed': EventStore._handle_sprint_completed,
            'sprint_card_added': EventStore._handle_sprint_card_added,
            'sprint_card_removed': EventStore._handle_sprint_card_removed,
        }

        handler = handlers.get(event.event_type)
        if handler:
            new_state = handler(new_state, event.payload)

        new_state['version'] = event.version
        return new_state

    @staticmethod
    def _handle_card_created(state: Dict, payload: Dict) -> Dict:
        return {**state, **payload}

    @staticmethod
    def _handle_card_moved(state: Dict, payload: Dict) -> Dict:
        state.update({
            'list_id': payload['new_list_id'],
            'order': payload['new_order'],
            'previous_list_id': payload.get('old_list_id')
        })
        return state

    @staticmethod
    def _handle_card_status_changed(state: Dict, payload: Dict) -> Dict:
        state.update({
            'status': payload['new_status'],
            'previous_status': payload.get('old_status')
        })
        return state

    @staticmethod
    def _handle_card_blocked(state: Dict, payload: Dict) -> Dict:
        state.update({
            'is_blocked': True,
            'blocked_reason': payload.get('reason', '')
        })
        return state

    @staticmethod
    def _handle_card_unblocked(state: Dict, payload: Dict) -> Dict:
        state.update({
            'is_blocked': False,
            'blocked_reason': ''
        })
        return state

    @staticmethod
    def _handle_card_dependency_added(state: Dict, payload: Dict) -> Dict:
        dependencies = state.get('dependencies', [])
        if payload['dependency_id'] not in dependencies:
            dependencies.append(payload['dependency_id'])
        state['dependencies'] = dependencies
        return state

    @staticmethod
    def _handle_card_dependency_removed(state: Dict, payload: Dict) -> Dict:
        dependencies = state.get('dependencies', [])
        if payload['dependency_id'] in dependencies:
            dependencies.remove(payload['dependency_id'])
        state['dependencies'] = dependencies
        return state

    @staticmethod
    def _handle_card_updated(state: Dict, payload: Dict) -> Dict:
        return {**state, **payload}

    @staticmethod
    def _handle_sprint_created(state: Dict, payload: Dict) -> Dict:
        return {**state, **payload, 'cards': []}

    @staticmethod
    def _handle_sprint_started(state: Dict, payload: Dict) -> Dict:
        state['status'] = 'active'
        return state

    @staticmethod
    def _handle_sprint_completed(state: Dict, payload: Dict) -> Dict:
        state['status'] = 'completed'
        return state

    @staticmethod
    def _handle_sprint_card_added(state: Dict, payload: Dict) -> Dict:
        cards = state.get('cards', [])
        if payload['card_id'] not in cards:
            cards.append(payload['card_id'])
        state['cards'] = cards
        return state

    @staticmethod
    def _handle_sprint_card_removed(state: Dict, payload: Dict) -> Dict:
        cards = state.get('cards', [])
        if payload['card_id'] in cards:
            cards.remove(payload['card_id'])
        state['cards'] = cards
        return state
