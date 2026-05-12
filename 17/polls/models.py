from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


class Question(models.Model):
    title = models.CharField(max_length=200, verbose_name="问题标题")
    description = models.TextField(blank=True, null=True, verbose_name="问题描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    allow_multiple = models.BooleanField(default=False, verbose_name="允许多选")
    allow_custom_choices = models.BooleanField(default=False, verbose_name="允许用户自定义选项")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True,
        verbose_name="创建者"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "问题"
        verbose_name_plural = "问题"

    def __str__(self):
        return self.title

    @classmethod
    def annotate_with_counts(cls, queryset=None):
        from django.db.models import Count

        if queryset is None:
            queryset = cls.objects.all()

        return queryset.prefetch_related(
            models.Prefetch(
                'choices',
                queryset=Choice.objects.annotate(
                    _vote_count=Count('votes')
                )
            )
        ).annotate(
            _total_votes=Count('choices__votes', distinct=True)
        ).annotate(
            _choice_count=Count('choices', distinct=True)
        )

    @staticmethod
    def get_voter_identifier(request):
        if request.user.is_authenticated:
            return ('user', request.user.id)
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        return ('session', session_key)


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name="所属问题"
    )
    text = models.CharField(max_length=200, verbose_name="选项内容")
    is_custom = models.BooleanField(default=False, verbose_name="是否用户自定义")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_choices',
        verbose_name="自定义选项创建者"
    )
    created_at = models.DateTimeField(default=None, null=True, blank=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "选项"
        verbose_name_plural = "选项"
        ordering = ['id']

    def __str__(self):
        prefix = "[自定义] " if self.is_custom else ""
        return f"{prefix}{self.text}"


class Vote(models.Model):
    choice = models.ForeignKey(
        Choice,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name="投票选项"
    )
    voter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="投票用户"
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="Session Key"
    )
    voter_ip = models.GenericIPAddressField(verbose_name="投票IP", null=True, blank=True)
    voted_at = models.DateTimeField(auto_now_add=True, verbose_name="投票时间")

    class Meta:
        ordering = ['-voted_at']
        verbose_name = "投票"
        verbose_name_plural = "投票"
        constraints = [
            models.UniqueConstraint(
                fields=['choice', 'voter'],
                condition=Q(voter__isnull=False),
                name='unique_vote_per_choice_user'
            ),
            models.UniqueConstraint(
                fields=['choice', 'session_key'],
                condition=Q(session_key__isnull=False),
                name='unique_vote_per_choice_session'
            ),
        ]

    def __str__(self):
        return f"{self.choice.text} - {self.voted_at}"

