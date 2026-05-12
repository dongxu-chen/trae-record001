from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import QuestionViewSet, VoteViewSet, CustomChoiceCreateView
from .auth import (
    RegisterView,
    LoginView,
    ProfileView,
    RefreshTokenView,
    LogoutView,
)

router = DefaultRouter()
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'votes', VoteViewSet, basename='vote')

urlpatterns = [
    path('', include(router.urls)),

    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/profile/', ProfileView.as_view(), name='auth-profile'),

    path('custom-choices/', CustomChoiceCreateView.as_view(), name='custom-choice-create'),
]
