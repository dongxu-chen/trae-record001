from rest_framework.throttling import BaseThrottle, SimpleRateThrottle
from rest_framework.settings import api_settings
import time


class RegisterThrottle(SimpleRateThrottle):
    scope = 'register'
    rate = '3/hour'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class LoginThrottle(SimpleRateThrottle):
    scope = 'login'
    rate = '10/minute'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class CreateQuestionThrottle(SimpleRateThrottle):
    scope = 'create_question'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = f"user_{request.user.pk}"
        else:
            ident = f"ip_{self.get_ident(request)}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class VoteThrottle(SimpleRateThrottle):
    scope = 'vote'
    rate = '30/minute'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = f"user_{request.user.pk}"
        else:
            session_key = request.session.session_key or self.get_ident(request)
            ident = f"session_{session_key}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class BurstRateThrottle(SimpleRateThrottle):
    scope = 'burst'
    rate = '60/minute'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class SustainedRateThrottle(SimpleRateThrottle):
    scope = 'sustained'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class CustomChoiceThrottle(SimpleRateThrottle):
    scope = 'custom_choice'
    rate = '20/hour'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = f"user_{request.user.pk}"
        else:
            ident = f"ip_{self.get_ident(request)}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class DynamicRateThrottle(SimpleRateThrottle):
    scope = 'dynamic'

    def __init__(self):
        super().__init__()

    def allow_request(self, request, view):
        if request.user.is_authenticated:
            if request.user.is_staff:
                self.rate = '1000/minute'
            else:
                self.rate = '60/minute'
        else:
            self.rate = '20/minute'

        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
