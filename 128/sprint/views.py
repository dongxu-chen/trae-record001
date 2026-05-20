from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Sprint, BurndownEntry
from .serializers import (
    SprintSerializer,
    BurndownEntrySerializer,
    SprintRetrospectiveSerializer,
    VelocitySerializer
)
from board.models import Card
from timetracking.models import TimeEntry


class SprintViewSet(viewsets.ModelViewSet):
    serializer_class = SprintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Sprint.objects.select_related(
            'project'
        ).prefetch_related(
            'cards',
            'burndown_entries'
        ).all().order_by('-start_date')

    @action(detail=True, methods=['post'])
    def generate_burndown(self, request, pk=None):
        sprint = self.get_object()
        
        if sprint.status != 'active':
            return Response(
                {'error': 'Sprint must be active to generate burndown data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_date = sprint.start_date
        end_date = sprint.end_date
        
        total_points = sprint.cards.aggregate(
            total=Sum('story_points')
        )['total'] or 0
        
        cards_list = list(sprint.cards.all())
        
        current_date = start_date
        while current_date <= end_date:
            completed_points = sum(
                card.story_points for card in cards_list
                if card.status == 'done' and card.updated_at.date() <= current_date
            )
            remaining_points = total_points - completed_points
            
            BurndownEntry.objects.update_or_create(
                sprint=sprint,
                date=current_date,
                defaults={
                    'remaining_points': remaining_points,
                    'completed_points': completed_points
                }
            )
            
            current_date += timedelta(days=1)
        
        sprint_serializer = self.get_serializer(sprint)
        return Response(sprint_serializer.data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        sprint = self.get_object()
        sprint.status = 'active'
        sprint.save()
        return Response(self.get_serializer(sprint).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        sprint = self.get_object()
        sprint.status = 'completed'
        sprint.save()
        return Response(self.get_serializer(sprint).data)

    @action(detail=True, methods=['get'])
    def retrospective(self, request, pk=None):
        sprint = self.get_object()
        
        cards = sprint.cards.all()
        total_cards = cards.count()
        completed_cards = cards.filter(status='done').count()
        in_progress_cards = cards.filter(status='in_progress').count()
        todo_cards = cards.filter(status='todo').count()
        
        total_points = cards.aggregate(total=Sum('story_points'))['total'] or 0
        completed_points = cards.filter(status='done').aggregate(
            total=Sum('story_points')
        )['total'] or 0
        
        sprint_duration = (sprint.end_date - sprint.start_date).days
        completion_rate = (completed_points / total_points * 100) if total_points > 0 else 0
        velocity = completed_points / sprint_duration if sprint_duration > 0 else 0
        throughput = completed_cards
        
        sprint_card_ids = cards.values_list('id', flat=True)
        hours_logged = TimeEntry.objects.filter(
            card_id__in=sprint_card_ids
        ).aggregate(total=Sum('hours'))['total'] or 0
        avg_hours_per_point = hours_logged / completed_points if completed_points > 0 else 0
        
        blocked_count = cards.filter(is_blocked=True).count()
        dependency_issues = cards.filter(
            dependencies__status__in=['todo', 'in_progress']
        ).distinct().count()
        
        retrospective_data = {
            'sprint_id': sprint.id,
            'sprint_name': sprint.name,
            'goal': sprint.goal,
            'start_date': sprint.start_date,
            'end_date': sprint.end_date,
            'status': sprint.status,
            'total_cards': total_cards,
            'completed_cards': completed_cards,
            'in_progress_cards': in_progress_cards,
            'todo_cards': todo_cards,
            'total_story_points': total_points,
            'completed_story_points': completed_points,
            'completion_rate': round(completion_rate, 2),
            'velocity': round(velocity, 2),
            'throughput': throughput,
            'total_hours_logged': hours_logged,
            'avg_hours_per_point': round(avg_hours_per_point, 2),
            'blocked_cards_count': blocked_count,
            'dependency_issues_count': dependency_issues,
        }
        
        serializer = SprintRetrospectiveSerializer(retrospective_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def velocity_trend(self, request):
        project_id = request.query_params.get('project_id')
        sprints = self.get_queryset().filter(status='completed')
        
        if project_id:
            sprints = sprints.filter(project_id=project_id)
        
        velocity_data = []
        for sprint in sprints:
            completed_points = sprint.cards.filter(status='done').aggregate(
                total=Sum('story_points')
            )['total'] or 0
            sprint_duration = (sprint.end_date - sprint.start_date).days
            velocity = completed_points / sprint_duration if sprint_duration > 0 else 0
            
            velocity_data.append({
                'sprint_id': sprint.id,
                'sprint_name': sprint.name,
                'completed_points': completed_points,
                'total_days': sprint_duration,
                'velocity': round(velocity, 2),
            })
        
        serializer = VelocitySerializer(velocity_data, many=True)
        return Response(serializer.data)


class BurndownEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BurndownEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BurndownEntry.objects.select_related(
            'sprint'
        ).all().order_by('date')
