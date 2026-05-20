from django.contrib import admin
from .models import TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('card', 'user', 'date', 'hours', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('description',)
