from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .commands import (
    CommandHandler,
    MoveCardCommand,
    ChangeCardStatusCommand,
    BlockCardCommand,
    UnblockCardCommand,
    AddCardDependencyCommand,
    RemoveCardDependencyCommand,
    UpdateCardCommand,
    StartSprintCommand,
    CompleteSprintCommand,
    AddCardToSprintCommand,
    RemoveCardFromSprintCommand
)
from .read_models import ReadModelQueries
from .event_replay import EventReplayer
from board.models import Card
from sprint.models import Sprint


class CommandAPIViewSet:
    """命令API - 写操作"""

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def move_card(request):
        command = MoveCardCommand(
            card_id=request.data.get('card_id'),
            new_list_id=request.data.get('new_list_id'),
            new_order=request.data.get('new_order'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_move_card(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def change_card_status(request):
        command = ChangeCardStatusCommand(
            card_id=request.data.get('card_id'),
            new_status=request.data.get('new_status'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_change_card_status(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'new_status': card.status,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def block_card(request):
        command = BlockCardCommand(
            card_id=request.data.get('card_id'),
            reason=request.data.get('reason', ''),
            user=request.user
        )

        try:
            card = CommandHandler.handle_block_card(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'is_blocked': card.is_blocked,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def unblock_card(request):
        command = UnblockCardCommand(
            card_id=request.data.get('card_id'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_unblock_card(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'is_blocked': card.is_blocked,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def add_dependency(request):
        command = AddCardDependencyCommand(
            card_id=request.data.get('card_id'),
            dependency_id=request.data.get('dependency_id'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_add_dependency(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def remove_dependency(request):
        command = RemoveCardDependencyCommand(
            card_id=request.data.get('card_id'),
            dependency_id=request.data.get('dependency_id'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_remove_dependency(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def update_card(request):
        command = UpdateCardCommand(
            card_id=request.data.get('card_id'),
            title=request.data.get('title'),
            description=request.data.get('description'),
            priority=request.data.get('priority'),
            assignee_id=request.data.get('assignee_id'),
            story_points=request.data.get('story_points'),
            user=request.user
        )

        try:
            card = CommandHandler.handle_update_card(command)
            return Response({
                'success': True,
                'card_id': card.id,
                'version': card.version
            })
        except (Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def start_sprint(request):
        command = StartSprintCommand(
            sprint_id=request.data.get('sprint_id'),
            user=request.user
        )

        try:
            sprint = CommandHandler.handle_start_sprint(command)
            return Response({
                'success': True,
                'sprint_id': sprint.id,
                'status': sprint.status
            })
        except (Sprint.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def complete_sprint(request):
        command = CompleteSprintCommand(
            sprint_id=request.data.get('sprint_id'),
            user=request.user
        )

        try:
            sprint = CommandHandler.handle_complete_sprint(command)
            return Response({
                'success': True,
                'sprint_id': sprint.id,
                'status': sprint.status
            })
        except (Sprint.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def add_card_to_sprint(request):
        command = AddCardToSprintCommand(
            sprint_id=request.data.get('sprint_id'),
            card_id=request.data.get('card_id'),
            user=request.user
        )

        try:
            sprint = CommandHandler.handle_add_card_to_sprint(command)
            return Response({
                'success': True,
                'sprint_id': sprint.id
            })
        except (Sprint.DoesNotExist, Card.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def remove_card_from_sprint(request):
        command = RemoveCardFromSprintCommand(
            sprint_id=request.data.get('sprint_id'),
            card_id=request.data.get('card_id'),
            user=request.user
        )

        try:
            sprint = CommandHandler.handle_remove_card_from_sprint(command)
            return Response({
                'success': True,
                'sprint_id': sprint.id
            })
        except (Sprint.DoesNotExist, ValueError) as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class QueryAPIViewSet:
    """查询API - 读操作（使用物化视图）"""

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_sprint_dashboard(request, sprint_id):
        dashboard = ReadModelQueries.get_sprint_dashboard(sprint_id)
        if dashboard:
            return Response(dashboard)
        return Response(
            {'error': 'Sprint dashboard not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_sprint_burndown(request, sprint_id):
        data = ReadModelQueries.get_sprint_burndown(sprint_id)
        return Response({
            'sprint_id': sprint_id,
            'data': data
        })

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_project_sprints(request, project_id):
        data = ReadModelQueries.get_project_sprints_dashboard(project_id)
        return Response({
            'project_id': project_id,
            'sprints': data
        })

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_board_cards(request, board_id):
        data = ReadModelQueries.get_board_cards(board_id)
        return Response({
            'board_id': board_id,
            'cards': data
        })

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_card_details(request, card_id):
        card = ReadModelQueries.get_card_details(card_id)
        if card:
            return Response(card)
        return Response(
            {'error': 'Card not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def refresh_materialized_view(request):
        view_name = request.data.get('view_name')
        concurrently = request.data.get('concurrently', False)

        valid_views = ['mv_sprint_burndown', 'mv_sprint_dashboard', 'mv_card_read_model']

        if view_name not in valid_views:
            return Response(
                {'error': f'Invalid view name. Valid options: {valid_views}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .tasks import refresh_materialized_view
        refresh_materialized_view.delay(view_name, concurrently)

        return Response({
            'success': True,
            'message': f'Refresh task queued for view: {view_name}'
        })


class EventReplayAPIViewSet:
    """事件回放API"""

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_card_history(request, card_id):
        limit = int(request.query_params.get('limit', 50))
        history = EventReplayer.get_card_history(card_id, limit)
        return Response({
            'card_id': card_id,
            'history': history
        })

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def compare_versions(request, card_id):
        version1 = int(request.query_params.get('version1'))
        version2 = int(request.query_params.get('version2'))

        comparison = EventReplayer.compare_versions(card_id, version1, version2)
        return Response(comparison)

    @staticmethod
    @api_view(['POST'])
    @permission_classes([permissions.IsAuthenticated])
    def replay_card_events(request, card_id):
        until_version = request.data.get('until_version')
        dry_run = request.data.get('dry_run', True)

        state = EventReplayer.replay_card_events(card_id, until_version, dry_run)

        return Response({
            'card_id': card_id,
            'until_version': until_version,
            'dry_run': dry_run,
            'state': state
        })

    @staticmethod
    @api_view(['GET'])
    @permission_classes([permissions.IsAuthenticated])
    def get_change_log(request):
        aggregate_type = request.query_params.get('aggregate_type', 'card')
        aggregate_id = request.query_params.get('aggregate_id')
        event_type = request.query_params.get('event_type')

        if aggregate_id:
            aggregate_id = int(aggregate_id)

        change_log = EventReplayer.get_change_log(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type
        )

        return Response({
            'aggregate_type': aggregate_type,
            'aggregate_id': aggregate_id,
            'change_log': change_log
        })
