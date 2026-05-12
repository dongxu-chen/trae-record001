from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not hasattr(obj, 'created_by'):
            return False
        return obj.created_by == request.user or request.user.is_staff


class IsQuestionOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        question = getattr(obj, 'question', None)
        if question is None:
            return False
        if hasattr(question, 'created_by'):
            return question.created_by == request.user or request.user.is_staff
        return request.user.is_staff


class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if not hasattr(obj, 'created_by'):
            return False
        return obj.created_by == request.user


class CanCreateQuestion(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user.is_authenticated
        return True
