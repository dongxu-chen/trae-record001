from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BoardViewSet, BoardListViewSet, CardViewSet, CommentViewSet,
    WorkflowStatusViewSet, WorkflowTransitionViewSet
)

router = DefaultRouter()
router.register(r'boards', BoardViewSet)
router.register(r'lists', BoardListViewSet)
router.register(r'cards', CardViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'workflow-statuses', WorkflowStatusViewSet)
router.register(r'workflow-transitions', WorkflowTransitionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
