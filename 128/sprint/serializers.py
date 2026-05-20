from rest_framework import serializers
from .models import Sprint, BurndownEntry
from board.models import Card
from board.serializers import CardSerializer


class BurndownEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BurndownEntry
        fields = ['id', 'sprint', 'date', 'remaining_points', 'completed_points', 'created_at']
        read_only_fields = ['created_at']


class SprintSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)
    card_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Card.objects.all(), source='cards', required=False
    )
    burndown_entries = BurndownEntrySerializer(many=True, read_only=True)
    total_story_points = serializers.IntegerField(read_only=True)
    completed_story_points = serializers.IntegerField(read_only=True)

    class Meta:
        model = Sprint
        fields = ['id', 'project', 'name', 'goal', 'start_date', 'end_date', 'status',
                  'cards', 'card_ids', 'burndown_entries', 'total_story_points',
                  'completed_story_points', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_story_points(self, obj):
        return obj.get_total_story_points()

    def get_completed_story_points(self, obj):
        return obj.get_completed_story_points()


class SprintRetrospectiveSerializer(serializers.Serializer):
    sprint_id = serializers.IntegerField()
    sprint_name = serializers.CharField()
    goal = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    status = serializers.CharField()
    
    total_cards = serializers.IntegerField()
    completed_cards = serializers.IntegerField()
    in_progress_cards = serializers.IntegerField()
    todo_cards = serializers.IntegerField()
    
    total_story_points = serializers.IntegerField()
    completed_story_points = serializers.IntegerField()
    
    completion_rate = serializers.FloatField()
    velocity = serializers.FloatField()
    throughput = serializers.IntegerField()
    
    total_hours_logged = serializers.DecimalField(max_digits=10, decimal_places=2)
    avg_hours_per_point = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    blocked_cards_count = serializers.IntegerField()
    dependency_issues_count = serializers.IntegerField()


class VelocitySerializer(serializers.Serializer):
    sprint_id = serializers.IntegerField()
    sprint_name = serializers.CharField()
    completed_points = serializers.IntegerField()
    total_days = serializers.IntegerField()
    velocity = serializers.FloatField()
