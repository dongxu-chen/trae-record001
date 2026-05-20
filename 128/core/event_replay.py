from typing import List, Dict, Any, Optional
from datetime import datetime
from django.db import transaction
from .event_store import EventStore, Event
from board.models import Card, BoardList


class EventReplayer:
    """事件回放服务"""

    @staticmethod
    def replay_card_events(
        card_id: int,
        until_version: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """回放卡片事件"""
        state = EventStore.reconstruct_aggregate('card', card_id, until_version)

        if not dry_run and state:
            with transaction.atomic():
                card = Card.objects.select_for_update().get(id=card_id)

                if 'list_id' in state:
                    try:
                        new_list = BoardList.objects.get(id=state['list_id'])
                        card.list = new_list
                    except BoardList.DoesNotExist:
                        pass

                if 'order' in state:
                    card.order = state['order']

                if 'status' in state:
                    card.status = state['status']

                if 'title' in state:
                    card.title = state['title']

                if 'description' in state:
                    card.description = state['description']

                if 'priority' in state:
                    card.priority = state['priority']

                if 'is_blocked' in state:
                    card.is_blocked = state['is_blocked']

                if 'blocked_reason' in state:
                    card.blocked_reason = state['blocked_reason']

                card.save()

        return state

    @staticmethod
    def get_card_history(card_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取卡片历史事件"""
        events = EventStore.get_events('card', card_id, limit=limit)

        history = []
        current_state = {}

        for event in events:
            current_state = EventStore.apply_event(current_state, event)

            history.append({
                'event_id': event.id,
                'event_type': event.event_type,
                'version': event.version,
                'created_at': event.created_at,
                'created_by': event.created_by.username if event.created_by else None,
                'payload': event.payload,
                'state_after': current_state.copy()
            })

        return history

    @staticmethod
    def compare_versions(card_id: int, version1: int, version2: int) -> Dict[str, Any]:
        """比较两个版本之间的差异"""
        state1 = EventStore.reconstruct_aggregate('card', card_id, version1)
        state2 = EventStore.reconstruct_aggregate('card', card_id, version2)

        changes = {}
        all_keys = set(state1.keys()) | set(state2.keys())

        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)

            if val1 != val2:
                changes[key] = {
                    'from': val1,
                    'to': val2
                }

        return {
            'card_id': card_id,
            'from_version': version1,
            'to_version': version2,
            'changes': changes
        }

    @staticmethod
    def get_change_log(
        aggregate_type: str,
        aggregate_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取变更日志"""
        queryset = Event.objects.filter(aggregate_type=aggregate_type)

        if aggregate_id:
            queryset = queryset.filter(aggregate_id=aggregate_id)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        if event_type:
            queryset = queryset.filter(event_type=event_type)

        events = queryset.select_related('created_by').order_by('-created_at')

        return [{
            'event_id': e.id,
            'aggregate_type': e.aggregate_type,
            'aggregate_id': e.aggregate_id,
            'event_type': e.event_type,
            'version': e.version,
            'created_at': e.created_at,
            'created_by': e.created_by.username if e.created_by else None,
            'payload': e.payload,
            'metadata': e.metadata
        } for e in events]
