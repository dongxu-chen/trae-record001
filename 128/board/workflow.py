from django.db import models
from core.models import Project


class WorkflowStatus(models.Model):
    TYPE_CHOICES = [
        ('initial', '初始状态'),
        ('active', '进行中'),
        ('review', '评审中'),
        ('completed', '完成状态'),
        ('blocked', '阻塞状态'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='workflow_statuses', verbose_name='所属项目')
    name = models.CharField(max_length=100, verbose_name='状态名称')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='active', verbose_name='状态类型')
    color = models.CharField(max_length=7, default='#6c757d', verbose_name='颜色')
    order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '工作流状态'
        verbose_name_plural = '工作流状态'
        ordering = ['order', 'id']
        unique_together = ['project', 'name']

    def __str__(self):
        return f'{self.project.name} - {self.name}'

    def save(self, *args, **kwargs):
        if self.is_default:
            WorkflowStatus.objects.filter(project=self.project, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class WorkflowTransition(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='workflow_transitions', verbose_name='所属项目')
    from_status = models.ForeignKey(WorkflowStatus, on_delete=models.CASCADE, related_name='outgoing_transitions', verbose_name='起始状态')
    to_status = models.ForeignKey(WorkflowStatus, on_delete=models.CASCADE, related_name='incoming_transitions', verbose_name='目标状态')
    name = models.CharField(max_length=100, verbose_name='转换名称')
    requires_comment = models.BooleanField(default=False, verbose_name='需要评论')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '工作流转换'
        verbose_name_plural = '工作流转换'
        unique_together = ['project', 'from_status', 'to_status']

    def __str__(self):
        return f'{self.from_status.name} → {self.to_status.name}'
