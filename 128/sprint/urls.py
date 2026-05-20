from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SprintViewSet, BurndownEntryViewSet

router = DefaultRouter()
router.register(r'sprints', SprintViewSet)
router.register(r'burndown', BurndownEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
