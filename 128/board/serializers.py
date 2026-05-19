from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Board, BoardList, Card, Comment
from .workflow import WorkflowStatus, WorkflowTransition
from core.serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'card', 'author', 'author_id', 'content', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SimpleCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ['id', 'title', 'status']


class CardSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    dependencies = SimpleCardSerializer(many=True, read_only=True)
    dependency_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Card.objects.all(), source='dependencies', required=False
    )
    blocked_status = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ['id', 'list', 'title', 'description', 'priority', 'status', 'order',
                  'assignee', 'assignee_id', 'created_by', 'due_date', 'story_points',
                  'version', 'is_blocked', 'blocked_reason', 'dependencies', 'dependency_ids',
                  'blocked_status', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_blocked_status(self, obj):
        return obj.get_blocked_status()


class BoardListSerializer(serializers.ModelSerializer):
    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = BoardList
        fields = ['id', 'board', 'name', 'order', 'cards', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class BoardSerializer(serializers.ModelSerializer):
    lists = BoardListSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'project', 'name', 'lists', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CardMoveSerializer(serializers.Serializer):
    list_id = serializers.IntegerField()
    new_order = serializers.IntegerField()
    current_version = serializers.IntegerField(required=False, default=None)


class WorkflowStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStatus
        fields = ['id', 'project', 'name', 'type', 'color', 'order', 'is_active', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    from_status_name = serializers.CharField(source='from_status.name', read_only=True)
    to_status_name = serializers.CharField(source='to_status.name', read_only=True)

    class Meta:
        model = WorkflowTransition
        fields = ['id', 'project', 'from_status', 'from_status_name', 'to_status', 'to_status_name',
                  'name', 'requires_comment', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class CardBlockSerializer(serializers.Serializer):
    is_blocked = serializers.BooleanField()
    blocked_reason = serializers.CharField(required=False, allow_blank=True)


class CardDependencySerializer(serializers.Serializer):
    dependency_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['add', 'remove', 'replace'])

