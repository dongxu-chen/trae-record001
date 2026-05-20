from django.contrib import admin
from .models import Sprint, BurndownEntry


class BurndownEntryInline(admin.TabularInline):
    model = BurndownEntry
    extra = 0


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'goal')
    filter_horizontal = ('cards',)
    inlines = [BurndownEntryInline]


@admin.register(BurndownEntry)
class BurndownEntryAdmin(admin.ModelAdmin):
    list_display = ('sprint', 'date', 'remaining_points', 'completed_points')
    list_filter = ('date',)
