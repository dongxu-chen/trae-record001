from django.db import models, transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Board, BoardList, Card, Comment
from .workflow import WorkflowStatus, WorkflowTransition
from .serializers import (
    BoardSerializer, BoardListSerializer, CardSerializer, 
    CommentSerializer, CardMoveSerializer,
    WorkflowStatusSerializer, WorkflowTransitionSerializer,
    CardBlockSerializer, CardDependencySerializer
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Board.objects.select_related(
            'project'
        ).prefetch_related(
            'lists',
            'lists__cards',
            'lists__cards__assignee',
            'lists__cards__created_by',
            'lists__cards__dependencies'
        ).all()


class BoardListViewSet(viewsets.ModelViewSet):
    serializer_class = BoardListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BoardList.objects.select_related(
            'board'
        ).prefetch_related(
            'cards',
            'cards__dependencies'
        ).all()


class CardViewSet(viewsets.ModelViewSet):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.select_related(
            'list',
            'list__board',
            'assignee',
            'created_by'
        ).prefetch_related(
            'comments',
            'comments__author',
            'dependencies',
            'dependents'
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        card = self.get_object()
        serializer = CardMoveSerializer(data=request.data)
        if serializer.is_valid():
            list_id = serializer.validated_data['list_id']
            new_order = serializer.validated_data['new_order']
            current_version = serializer.validated_data.get('current_version')
            
            try:
                new_list = BoardList.objects.get(id=list_id)
            except BoardList.DoesNotExist:
                return Response({'error': 'List not found'}, status=status.HTTP_404_NOT_FOUND)
            
            if current_version is not None and card.version != current_version:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'board_{new_list.board.id}',
                    {
                        'type': 'conflict_detected',
                        'card_id': card.id,
                        'message': 'Card has been modified by another user. Please refresh and try again.'
                    }
                )
                return Response(
                    {
                        'error': 'Conflict detected',
                        'message': 'Card has been modified by another user. Please refresh and try again.',
                        'current_version': card.version,
                        'card': CardSerializer(card).data
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            with transaction.atomic():
                old_list = card.list
                old_order = card.order
                
                Card.objects.filter(list=old_list, order__gt=old_order).update(order=models.F('order') - 1)
                
                Card.objects.filter(list=new_list, order__gte=new_order).update(order=models.F('order') + 1)
                
                card.list = new_list
                card.order = new_order
                card.save()
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'board_{new_list.board.id}',
                {
                    'type': 'card_moved',
                    'card_id': card.id,
                    'old_list_id': old_list.id,
                    'new_list_id': new_list.id,
                    'new_order': new_order,
                    'new_version': card.version,
                }
            )
            
            return Response(CardSerializer(card).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_blocked(self, request, pk=None):
        card = self.get_object()
        serializer = CardBlockSerializer(data=request.data)
        if serializer.is_valid():
            card.is_blocked = serializer.validated_data['is_blocked']
            card.blocked_reason = serializer.validated_data.get('blocked_reason', '')
            card.save()
            return Response(CardSerializer(card).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def manage_dependencies(self, request, pk=None):
        card = self.get_object()
        serializer = CardDependencySerializer(data=request.data)
        if serializer.is_valid():
            action_type = serializer.validated_data['action']
            dependency_ids = serializer.validated_data['dependency_ids']
            
            dependencies = Card.objects.filter(id__in=dependency_ids).exclude(id=card.id)
            
            if action_type == 'add':
                card.dependencies.add(*dependencies)
            elif action_type == 'remove':
                card.dependencies.remove(*dependencies)
            elif action_type == 'replace':
                card.dependencies.set(dependencies)
            
            card.save()
            return Response(CardSerializer(card).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.select_related(
            'card',
            'author'
        ).all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class WorkflowStatusViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkflowStatus.objects.select_related('project').all()

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({'error': 'project_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        statuses = self.get_queryset().filter(project_id=project_id, is_active=True)
        return Response(WorkflowStatusSerializer(statuses, many=True).data)


class WorkflowTransitionViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowTransitionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkflowTransition.objects.select_related(
            'project',
            'from_status',
            'to_status'
        ).all()

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response({'error': 'project_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        transitions = self.get_queryset().filter(project_id=project_id, is_active=True)
        return Response(WorkflowTransitionSerializer(transitions, many=True).data)
