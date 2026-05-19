import pytz
from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user_tz = request.session.get('user_timezone', 'Asia/Shanghai')
            try:
                timezone.activate(pytz.timezone(user_tz))
            except pytz.UnknownTimeZoneError:
                timezone.activate(pytz.timezone('Asia/Shanghai'))
        else:
            timezone.activate(pytz.timezone('Asia/Shanghai'))
        
        response = self.get_response(request)
        timezone.deactivate()
        return response
