from django.contrib import admin
from .models import Board, BoardList, Card, Comment


class BoardListInline(admin.TabularInline):
    model = BoardList
    extra = 0


class CardInline(admin.TabularInline):
    model = Card
    extra = 0


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_at')
    inlines = [BoardListInline]


@admin.register(BoardList)
class BoardListAdmin(admin.ModelAdmin):
    list_display = ('name', 'board', 'order', 'created_at')
    inlines = [CardInline]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('title', 'list', 'status', 'priority', 'assignee', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('card', 'author', 'created_at')
    search_fields = ('content',)
