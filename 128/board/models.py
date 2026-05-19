from django.db import models
from django.contrib.auth.models import User
from core.models import Project


class Board(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='board', verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='看板名称')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '看板'
        verbose_name_plural = '看板'

    def __str__(self):
        return f'{self.project.name} - {self.name}'


class BoardList(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='lists', verbose_name='所属看板')
    name = models.CharField(max_length=200, verbose_name='列表名称')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '列表'
        verbose_name_plural = '列表'
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Card(models.Model):
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    STATUS_CHOICES = [
        ('todo', '待办'),
        ('in_progress', '进行中'),
        ('review', '评审中'),
        ('done', '已完成'),
    ]

    list = models.ForeignKey(BoardList, on_delete=models.CASCADE, related_name='cards', verbose_name='所属列表')
    title = models.CharField(max_length=200, verbose_name='标题')
    description = models.TextField(blank=True, verbose_name='描述')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', verbose_name='状态')
    order = models.IntegerField(default=0, verbose_name='排序')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cards', verbose_name='负责人')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cards', verbose_name='创建人')
    due_date = models.DateField(null=True, blank=True, verbose_name='截止日期')
    story_points = models.IntegerField(default=0, verbose_name='故事点')
    version = models.IntegerField(default=0, verbose_name='版本号')
    is_blocked = models.BooleanField(default=False, verbose_name='是否阻塞')
    blocked_reason = models.TextField(blank=True, verbose_name='阻塞原因')
    dependencies = models.ManyToManyField('self', symmetrical=False, related_name='dependents', blank=True, verbose_name='依赖卡片')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '卡片'
        verbose_name_plural = '卡片'
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.version += 1
        super().save(*args, **kwargs)

    def get_blocked_status(self):
        if self.is_blocked:
            return 'blocked'
        if self.dependencies.filter(status__in=['todo', 'in_progress']).exists():
            return 'waiting'
        return None


class Comment(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='comments', verbose_name='所属卡片')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='作者')
    content = models.TextField(verbose_name='内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author.username} - {self.content[:20]}'
