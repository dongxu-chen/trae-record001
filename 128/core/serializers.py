from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Project


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_id = serializers.IntegerField(write_only=True)
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=User.objects.all(), source='members'
    )

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'owner_id', 'members', 'member_ids', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
