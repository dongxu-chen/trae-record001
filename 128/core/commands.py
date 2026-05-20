from dataclasses import dataclass
from typing import Optional, List
from django.db import transaction
from django.contrib.auth import get_user_model
from .event_store import EventStore
from board.models import Card, BoardList
from sprint.models import Sprint

User = get_user_model()


@dataclass
class BaseCommand:
    user: Optional[User] = None


@dataclass
class MoveCardCommand(BaseCommand):
    card_id: int = 0
    new_list_id: int = 0
    new_order: int = 0


@dataclass
class ChangeCardStatusCommand(BaseCommand):
    card_id: int = 0
    new_status: str = ''


@dataclass
class BlockCardCommand(BaseCommand):
    card_id: int = 0
    reason: str = ''


@dataclass
class UnblockCardCommand(BaseCommand):
    card_id: int = 0


@dataclass
class AddCardDependencyCommand(BaseCommand):
    card_id: int = 0
    dependency_id: int = 0


@dataclass
class RemoveCardDependencyCommand(BaseCommand):
    card_id: int = 0
    dependency_id: int = 0


@dataclass
class UpdateCardCommand(BaseCommand):
    card_id: int = 0
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[int] = None
    story_points: Optional[int] = None


@dataclass
class StartSprintCommand(BaseCommand):
    sprint_id: int = 0


@dataclass
class CompleteSprintCommand(BaseCommand):
    sprint_id: int = 0


@dataclass
class AddCardToSprintCommand(BaseCommand):
    sprint_id: int = 0
    card_id: int = 0


@dataclass
class RemoveCardFromSprintCommand(BaseCommand):
    sprint_id: int = 0
    card_id: int = 0


class CommandHandler:
    @staticmethod
    @transaction.atomic
    def handle_move_card(command: MoveCardCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)
        new_list = BoardList.objects.get(id=command.new_list_id)
        
        old_list_id = card.list_id
        old_order = card.order

        Card.objects.filter(list=card.list, order__gt=old_order).update(order=models.F('order') - 1)
        Card.objects.filter(list=new_list, order__gte=command.new_order).update(order=models.F('order') + 1)

        card.list = new_list
        card.order = command.new_order
        card.save()

        EventStore.append_event(
            aggregate_type='card',
            aggregate_id=command.card_id,
            event_type='card_moved',
            payload={
                'old_list_id': old_list_id,
                'new_list_id': command.new_list_id,
                'old_order': old_order,
                'new_order': command.new_order,
            },
            user=command.user
        )

        return card

    @staticmethod
    @transaction.atomic
    def handle_change_card_status(command: ChangeCardStatusCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)
        old_status = card.status

        if old_status == command.new_status:
            return card

        card.status = command.new_status
        card.save()

        EventStore.append_event(
            aggregate_type='card',
            aggregate_id=command.card_id,
            event_type='card_status_changed',
            payload={
                'old_status': old_status,
                'new_status': command.new_status,
            },
            user=command.user
        )

        return card

    @staticmethod
    @transaction.atomic
    def handle_block_card(command: BlockCardCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)

        if card.is_blocked:
            return card

        card.is_blocked = True
        card.blocked_reason = command.reason
        card.save()

        EventStore.append_event(
            aggregate_type='card',
            aggregate_id=command.card_id,
            event_type='card_blocked',
            payload={'reason': command.reason},
            user=command.user
        )

        return card

    @staticmethod
    @transaction.atomic
    def handle_unblock_card(command: UnblockCardCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)

        if not card.is_blocked:
            return card

        card.is_blocked = False
        card.blocked_reason = ''
        card.save()

        EventStore.append_event(
            aggregate_type='card',
            aggregate_id=command.card_id,
            event_type='card_unblocked',
            payload={},
            user=command.user
        )

        return card

    @staticmethod
    @transaction.atomic
    def handle_add_dependency(command: AddCardDependencyCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)
        dependency = Card.objects.get(id=command.dependency_id)

        if not card.dependencies.filter(id=command.dependency_id).exists():
            card.dependencies.add(dependency)
            card.save()

            EventStore.append_event(
                aggregate_type='card',
                aggregate_id=command.card_id,
                event_type='card_dependency_added',
                payload={'dependency_id': command.dependency_id},
                user=command.user
            )

        return card

    @staticmethod
    @transaction.atomic
    def handle_remove_dependency(command: RemoveCardDependencyCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)

        if card.dependencies.filter(id=command.dependency_id).exists():
            card.dependencies.remove(command.dependency_id)
            card.save()

            EventStore.append_event(
                aggregate_type='card',
                aggregate_id=command.card_id,
                event_type='card_dependency_removed',
                payload={'dependency_id': command.dependency_id},
                user=command.user
            )

        return card

    @staticmethod
    @transaction.atomic
    def handle_update_card(command: UpdateCardCommand) -> Card:
        card = Card.objects.select_for_update().get(id=command.card_id)
        updates = {}

        if command.title is not None:
            card.title = command.title
            updates['title'] = command.title

        if command.description is not None:
            card.description = command.description
            updates['description'] = command.description

        if command.priority is not None:
            card.priority = command.priority
            updates['priority'] = command.priority

        if command.assignee_id is not None:
            card.assignee_id = command.assignee_id
            updates['assignee_id'] = command.assignee_id

        if command.story_points is not None:
            card.story_points = command.story_points
            updates['story_points'] = command.story_points

        if updates:
            card.save()

            EventStore.append_event(
                aggregate_type='card',
                aggregate_id=command.card_id,
                event_type='card_updated',
                payload=updates,
                user=command.user
            )

        return card

    @staticmethod
    @transaction.atomic
    def handle_start_sprint(command: StartSprintCommand) -> Sprint:
        sprint = Sprint.objects.select_for_update().get(id=command.sprint_id)

        if sprint.status != 'planning':
            raise ValueError(f'Sprint is already {sprint.status}')

        sprint.status = 'active'
        sprint.save()

        EventStore.append_event(
            aggregate_type='sprint',
            aggregate_id=command.sprint_id,
            event_type='sprint_started',
            payload={},
            user=command.user
        )

        return sprint

    @staticmethod
    @transaction.atomic
    def handle_complete_sprint(command: CompleteSprintCommand) -> Sprint:
        sprint = Sprint.objects.select_for_update().get(id=command.sprint_id)

        if sprint.status != 'active':
            raise ValueError(f'Sprint is {sprint.status}, cannot complete')

        sprint.status = 'completed'
        sprint.save()

        EventStore.append_event(
            aggregate_type='sprint',
            aggregate_id=command.sprint_id,
            event_type='sprint_completed',
            payload={},
            user=command.user
        )

        return sprint

    @staticmethod
    @transaction.atomic
    def handle_add_card_to_sprint(command: AddCardToSprintCommand) -> Sprint:
        sprint = Sprint.objects.select_for_update().get(id=command.sprint_id)
        card = Card.objects.get(id=command.card_id)

        if not sprint.cards.filter(id=command.card_id).exists():
            sprint.cards.add(card)

            EventStore.append_event(
                aggregate_type='sprint',
                aggregate_id=command.sprint_id,
                event_type='sprint_card_added',
                payload={'card_id': command.card_id},
                user=command.user
            )

        return sprint

    @staticmethod
    @transaction.atomic
    def handle_remove_card_from_sprint(command: RemoveCardFromSprintCommand) -> Sprint:
        sprint = Sprint.objects.select_for_update().get(id=command.sprint_id)

        if sprint.cards.filter(id=command.card_id).exists():
            sprint.cards.remove(command.card_id)

            EventStore.append_event(
                aggregate_type='sprint',
                aggregate_id=command.sprint_id,
                event_type='sprint_card_removed',
                payload={'card_id': command.card_id},
                user=command.user
            )

        return sprint


from django.db import models
