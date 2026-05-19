from django.db import models
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
import io
import csv
from .models import TimeEntry
from .serializers import (
    TimeEntrySerializer,
    TimeReportSerializer,
    DailySummarySerializer,
    UserSummarySerializer,
    CardSummarySerializer
)
from sprint.models import Sprint


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TimeEntry.objects.select_related(
            'user',
            'card',
            'card__list',
            'card__list__board'
        ).filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def report(self, request):
        serializer = TimeReportSerializer(data=request.data)
        if serializer.is_valid():
            entries = TimeEntry.objects.select_related('user', 'card').all()
            
            if serializer.validated_data.get('user_id'):
                entries = entries.filter(user_id=serializer.validated_data['user_id'])
            if serializer.validated_data.get('start_date'):
                entries = entries.filter(date__gte=serializer.validated_data['start_date'])
            if serializer.validated_data.get('end_date'):
                entries = entries.filter(date__lte=serializer.validated_data['end_date'])
            if serializer.validated_data.get('project_id'):
                entries = entries.filter(card__list__board__project_id=serializer.validated_data['project_id'])
            if serializer.validated_data.get('sprint_id'):
                try:
                    sprint = Sprint.objects.get(id=serializer.validated_data['sprint_id'])
                    sprint_card_ids = sprint.cards.values_list('id', flat=True)
                    entries = entries.filter(card_id__in=sprint_card_ids)
                except Sprint.DoesNotExist:
                    pass
            
            return Response(TimeEntrySerializer(entries, many=True).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def daily_summary(self, request):
        serializer = TimeReportSerializer(data=request.data)
        if serializer.is_valid():
            entries = TimeEntry.objects.all()
            
            if serializer.validated_data.get('user_id'):
                entries = entries.filter(user_id=serializer.validated_data['user_id'])
            if serializer.validated_data.get('start_date'):
                entries = entries.filter(date__gte=serializer.validated_data['start_date'])
            if serializer.validated_data.get('end_date'):
                entries = entries.filter(date__lte=serializer.validated_data['end_date'])
            
            summary = entries.values('date').annotate(
                total_hours=models.Sum('hours'),
                entry_count=models.Count('id')
            ).order_by('date')
            
            return Response(DailySummarySerializer(summary, many=True).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def user_summary(self, request):
        serializer = TimeReportSerializer(data=request.data)
        if serializer.is_valid():
            entries = TimeEntry.objects.all()
            
            if serializer.validated_data.get('start_date'):
                entries = entries.filter(date__gte=serializer.validated_data['start_date'])
            if serializer.validated_data.get('end_date'):
                entries = entries.filter(date__lte=serializer.validated_data['end_date'])
            
            summary = entries.values('user_id', 'user__username').annotate(
                total_hours=models.Sum('hours'),
                entry_count=models.Count('id')
            ).order_by('user__username')
            
            result = [
                {
                    'user_id': item['user_id'],
                    'username': item['user__username'],
                    'total_hours': item['total_hours'],
                    'entry_count': item['entry_count']
                }
                for item in summary
            ]
            
            return Response(UserSummarySerializer(result, many=True).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def card_summary(self, request):
        serializer = TimeReportSerializer(data=request.data)
        if serializer.is_valid():
            entries = TimeEntry.objects.all()
            
            if serializer.validated_data.get('user_id'):
                entries = entries.filter(user_id=serializer.validated_data['user_id'])
            if serializer.validated_data.get('start_date'):
                entries = entries.filter(date__gte=serializer.validated_data['start_date'])
            if serializer.validated_data.get('end_date'):
                entries = entries.filter(date__lte=serializer.validated_data['end_date'])
            
            summary = entries.values('card_id', 'card__title').annotate(
                total_hours=models.Sum('hours'),
                entry_count=models.Count('id')
            ).order_by('-total_hours')
            
            result = [
                {
                    'card_id': item['card_id'],
                    'card_title': item['card__title'],
                    'total_hours': item['total_hours'],
                    'entry_count': item['entry_count']
                }
                for item in summary
            ]
            
            return Response(CardSummarySerializer(result, many=True).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def export_excel(self, request):
        serializer = TimeReportSerializer(data=request.data)
        if serializer.is_valid():
            entries = TimeEntry.objects.select_related('user', 'card').all()
            
            if serializer.validated_data.get('user_id'):
                entries = entries.filter(user_id=serializer.validated_data['user_id'])
            if serializer.validated_data.get('start_date'):
                entries = entries.filter(date__gte=serializer.validated_data['start_date'])
            if serializer.validated_data.get('end_date'):
                entries = entries.filter(date__lte=serializer.validated_data['end_date'])
            if serializer.validated_data.get('project_id'):
                entries = entries.filter(card__list__board__project_id=serializer.validated_data['project_id'])
            
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(['日期', '用户', '卡片标题', '工时(小时)', '工作描述', '创建时间'])
            
            for entry in entries:
                writer.writerow([
                    entry.date.strftime('%Y-%m-%d'),
                    entry.user.username,
                    entry.card.title,
                    float(entry.hours),
                    entry.description,
                    entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="time_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
