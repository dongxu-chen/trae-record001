from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, UserViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
