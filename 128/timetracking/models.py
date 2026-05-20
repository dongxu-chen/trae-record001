from django.db import models
from django.contrib.auth.models import User
from board.models import Card


class TimeEntry(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='time_entries', verbose_name='所属卡片')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_entries', verbose_name='登记人')
    date = models.DateField(verbose_name='日期')
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='工时（小时）')
    description = models.TextField(blank=True, verbose_name='工作描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '工时登记'
        verbose_name_plural = '工时登记'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.card.title} - {self.hours}h'
