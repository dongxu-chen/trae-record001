from django.db import models
from core.models import Project
from board.models import Card


class Sprint(models.Model):
    STATUS_CHOICES = [
        ('planning', '规划中'),
        ('active', '进行中'),
        ('completed', '已完成'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints', verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='Sprint名称')
    goal = models.TextField(blank=True, verbose_name='Sprint目标')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name='状态')
    cards = models.ManyToManyField(Card, related_name='sprints', blank=True, verbose_name='关联卡片')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'Sprint'
        verbose_name_plural = 'Sprint'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def get_total_story_points(self):
        return sum(card.story_points for card in self.cards.all())

    def get_completed_story_points(self):
        return sum(card.story_points for card in self.cards.filter(status='done'))


class BurndownEntry(models.Model):
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE, related_name='burndown_entries', verbose_name='所属Sprint')
    date = models.DateField(verbose_name='日期')
    remaining_points = models.IntegerField(default=0, verbose_name='剩余故事点')
    completed_points = models.IntegerField(default=0, verbose_name='已完成故事点')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '燃尽图记录'
        verbose_name_plural = '燃尽图记录'
        ordering = ['date']
        unique_together = ['sprint', 'date']

    def __str__(self):
        return f'{self.sprint.name} - {self.date}'
