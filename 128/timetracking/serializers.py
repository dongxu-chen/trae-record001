from rest_framework import serializers
from .models import TimeEntry
from core.serializers import UserSerializer
from board.serializers import CardSerializer


class TimeEntrySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    card = CardSerializer(read_only=True)
    card_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TimeEntry
        fields = ['id', 'card', 'card_id', 'user', 'user_id', 'date', 'hours', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TimeReportSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    sprint_id = serializers.IntegerField(required=False)
    project_id = serializers.IntegerField(required=False)


class DailySummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()


class UserSummarySerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()


class CardSummarySerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    card_title = serializers.CharField()
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    entry_count = serializers.IntegerField()
