from django.db import models, connection
from django.db.models import Sum, Case, When, IntegerField, Count, Q
from typing import List, Dict, Any, Optional
from datetime import date


class MaterializedViewManager(models.Manager):
    def refresh(self, concurrently: bool = False) -> None:
        table_name = self.model._meta.db_table
        with connection.cursor() as cursor:
            if concurrently:
                cursor.execute(f'REINDEX MATERIALIZED VIEW CONCURRENTLY {table_name}')
            else:
                cursor.execute(f'REINDEX MATERIALIZED VIEW {table_name}')


class SprintBurndownMV(models.Model):
    """燃尽图物化视图 - 读模型"""
    sprint_id = models.IntegerField(primary_key=True)
    sprint_name = models.CharField(max_length=200)
    project_id = models.IntegerField()
    date = models.DateField()
    total_points = models.IntegerField(default=0)
    completed_points = models.IntegerField(default=0)
    remaining_points = models.IntegerField(default=0)
    total_cards = models.IntegerField(default=0)
    completed_cards = models.IntegerField(default=0)
    in_progress_cards = models.IntegerField(default=0)
    todo_cards = models.IntegerField(default=0)
    blocked_cards = models.IntegerField(default=0)
    velocity = models.FloatField(default=0.0)
    completion_rate = models.FloatField(default=0.0)
    last_updated = models.DateTimeField()

    objects = MaterializedViewManager()

    class Meta:
        managed = False
        db_table = 'mv_sprint_burndown'
        verbose_name = 'Sprint燃尽图(物化视图)'
        verbose_name_plural = 'Sprint燃尽图(物化视图)'
        unique_together = ['sprint_id', 'date']


class SprintDashboardMV(models.Model):
    """Sprint仪表盘物化视图"""
    sprint_id = models.IntegerField(primary_key=True)
    sprint_name = models.CharField(max_length=200)
    project_id = models.IntegerField()
    status = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    days_remaining = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    completed_points = models.IntegerField(default=0)
    remaining_points = models.IntegerField(default=0)
    total_cards = models.IntegerField(default=0)
    completed_cards = models.IntegerField(default=0)
    completion_rate = models.FloatField(default=0.0)
    velocity = models.FloatField(default=0.0)
    projected_completion_date = models.DateField(null=True)
    total_hours_logged = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_hours_per_point = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    blocked_cards_count = models.IntegerField(default=0)
    dependency_issues_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField()

    objects = MaterializedViewManager()

    class Meta:
        managed = False
        db_table = 'mv_sprint_dashboard'
        verbose_name = 'Sprint仪表盘(物化视图)'
        verbose_name_plural = 'Sprint仪表盘(物化视图)'


class CardReadModelMV(models.Model):
    """卡片读模型物化视图"""
    card_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    order = models.IntegerField()
    list_id = models.IntegerField()
    list_name = models.CharField(max_length=200)
    board_id = models.IntegerField()
    project_id = models.IntegerField()
    assignee_id = models.IntegerField(null=True)
    assignee_username = models.CharField(max_length=150, null=True)
    created_by_id = models.IntegerField()
    story_points = models.IntegerField(default=0)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField()
    version = models.IntegerField(default=0)
    sprint_ids = models.JSONField(default=list)
    dependency_ids = models.JSONField(default=list)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    last_event_at = models.DateTimeField()

    objects = MaterializedViewManager()

    class Meta:
        managed = False
        db_table = 'mv_card_read_model'
        verbose_name = '卡片读模型(物化视图)'
        verbose_name_plural = '卡片读模型(物化视图)'


class ReadModelQueries:
    """读模型查询服务"""

    @staticmethod
    def get_sprint_burndown(sprint_id: int) -> List[Dict[str, Any]]:
        results = SprintBurndownMV.objects.filter(
            sprint_id=sprint_id
        ).order_by('date').values(
            'date', 'total_points', 'completed_points', 'remaining_points',
            'total_cards', 'completed_cards', 'velocity', 'completion_rate'
        )
        return list(results)

    @staticmethod
    def get_sprint_dashboard(sprint_id: int) -> Optional[Dict[str, Any]]:
        try:
            dashboard = SprintDashboardMV.objects.filter(sprint_id=sprint_id).values(
                'sprint_id', 'sprint_name', 'status', 'start_date', 'end_date',
                'days_remaining', 'total_points', 'completed_points', 'remaining_points',
                'total_cards', 'completed_cards', 'completion_rate', 'velocity',
                'projected_completion_date', 'total_hours_logged', 'avg_hours_per_point',
                'blocked_cards_count', 'dependency_issues_count'
            ).first()
            return dashboard
        except SprintDashboardMV.DoesNotExist:
            return None

    @staticmethod
    def get_project_sprints_dashboard(project_id: int) -> List[Dict[str, Any]]:
        results = SprintDashboardMV.objects.filter(
            project_id=project_id
        ).order_by('-start_date').values(
            'sprint_id', 'sprint_name', 'status', 'start_date', 'end_date',
            'total_points', 'completed_points', 'completion_rate', 'velocity'
        )
        return list(results)

    @staticmethod
    def get_board_cards(board_id: int) -> List[Dict[str, Any]]:
        results = CardReadModelMV.objects.filter(
            board_id=board_id
        ).order_by('list_id', 'order').values(
            'card_id', 'title', 'priority', 'status', 'order', 'list_id',
            'list_name', 'story_points', 'is_blocked', 'assignee_username',
            'dependency_ids', 'version', 'updated_at'
        )
        return list(results)

    @staticmethod
    def get_card_details(card_id: int) -> Optional[Dict[str, Any]]:
        try:
            card = CardReadModelMV.objects.filter(card_id=card_id).values(
                'card_id', 'title', 'description', 'priority', 'status',
                'list_id', 'list_name', 'story_points', 'is_blocked', 'blocked_reason',
                'assignee_id', 'assignee_username', 'sprint_ids', 'dependency_ids',
                'version', 'created_at', 'updated_at', 'last_event_at'
            ).first()
            return card
        except CardReadModelMV.DoesNotExist:
            return None

    @staticmethod
    def refresh_materialized_view(view_name: str, concurrently: bool = False) -> None:
        with connection.cursor() as cursor:
            if concurrently:
                cursor.execute(f'REINDEX MATERIALIZED VIEW CONCURRENTLY {view_name}')
            else:
                cursor.execute(f'REINDEX MATERIALIZED VIEW {view_name}')


def get_materialized_view_sql() -> Dict[str, str]:
    """获取创建物化视图的SQL语句"""
    return {
        'mv_sprint_burndown': '''
            CREATE MATERIALIZED VIEW mv_sprint_burndown AS
            WITH sprint_dates AS (
                SELECT 
                    s.id AS sprint_id,
                    s.name AS sprint_name,
                    s.project_id,
                    generate_series(s.start_date, s.end_date, '1 day'::interval)::date AS date
                FROM sprint_sprint s
            ),
            card_events AS (
                SELECT 
                    sc.sprint_id,
                    c.id AS card_id,
                    c.status,
                    c.story_points,
                    c.updated_at
                FROM sprint_sprint_cards sc
                JOIN board_card c ON sc.card_id = c.id
            ),
            daily_stats AS (
                SELECT 
                    sd.sprint_id,
                    sd.sprint_name,
                    sd.project_id,
                    sd.date,
                    COALESCE(SUM(ce.story_points), 0) AS total_points,
                    COALESCE(SUM(CASE WHEN ce.status = 'done' THEN ce.story_points ELSE 0 END), 0) AS completed_points,
                    COALESCE(COUNT(ce.card_id), 0) AS total_cards,
                    COALESCE(COUNT(CASE WHEN ce.status = 'done' THEN 1 END), 0) AS completed_cards,
                    COALESCE(COUNT(CASE WHEN ce.status = 'in_progress' THEN 1 END), 0) AS in_progress_cards,
                    COALESCE(COUNT(CASE WHEN ce.status = 'todo' THEN 1 END), 0) AS todo_cards,
                    COALESCE(COUNT(CASE WHEN c.is_blocked THEN 1 END), 0) AS blocked_cards
                FROM sprint_dates sd
                LEFT JOIN card_events ce ON sd.sprint_id = ce.sprint_id 
                    AND ce.updated_at::date <= sd.date
                LEFT JOIN board_card c ON ce.card_id = c.id
                GROUP BY sd.sprint_id, sd.sprint_name, sd.project_id, sd.date
            )
            SELECT 
                (sprint_id::text || '_' || to_char(date, 'YYYYMMDD'))::integer AS id,
                sprint_id,
                sprint_name,
                project_id,
                date,
                total_points,
                completed_points,
                (total_points - completed_points) AS remaining_points,
                total_cards,
                completed_cards,
                in_progress_cards,
                todo_cards,
                blocked_cards,
                CASE WHEN (current_date - (SELECT MIN(date) FROM sprint_dates WHERE sprint_id = ds.sprint_id)) > 0
                     THEN completed_points::float / (current_date - (SELECT MIN(date) FROM sprint_dates WHERE sprint_id = ds.sprint_id))
                     ELSE 0 END AS velocity,
                CASE WHEN total_points > 0 THEN (completed_points::float / total_points * 100) ELSE 0 END AS completion_rate,
                NOW() AS last_updated
            FROM daily_stats ds;
        ''',

        'mv_sprint_dashboard': '''
            CREATE MATERIALIZED VIEW mv_sprint_dashboard AS
            WITH sprint_stats AS (
                SELECT 
                    s.id AS sprint_id,
                    s.name AS sprint_name,
                    s.project_id,
                    s.status,
                    s.start_date,
                    s.end_date,
                    COALESCE((s.end_date - current_date), 0) AS days_remaining,
                    COALESCE(SUM(c.story_points), 0) AS total_points,
                    COALESCE(SUM(CASE WHEN c.status = 'done' THEN c.story_points ELSE 0 END), 0) AS completed_points,
                    COALESCE(COUNT(c.id), 0) AS total_cards,
                    COALESCE(COUNT(CASE WHEN c.status = 'done' THEN 1 END), 0) AS completed_cards,
                    COALESCE(COUNT(CASE WHEN c.is_blocked THEN 1 END), 0) AS blocked_cards_count,
                    COALESCE(SUM(CASE WHEN EXISTS (
                        SELECT 1 FROM board_card_dependencies cd 
                        WHERE cd.from_card_id = c.id 
                        AND EXISTS (SELECT 1 FROM board_card dep WHERE dep.id = cd.to_card_id AND dep.status != 'done')
                    ) THEN 1 ELSE 0 END), 0) AS dependency_issues_count
                FROM sprint_sprint s
                LEFT JOIN sprint_sprint_cards sc ON s.id = sc.sprint_id
                LEFT JOIN board_card c ON sc.card_id = c.id
                GROUP BY s.id, s.name, s.project_id, s.status, s.start_date, s.end_date
            ),
            sprint_hours AS (
                SELECT 
                    sc.sprint_id,
                    COALESCE(SUM(e.hours), 0) AS total_hours_logged
                FROM sprint_sprint_cards sc
                LEFT JOIN timetracking_timeentry e ON sc.card_id = e.card_id
                GROUP BY sc.sprint_id
            )
            SELECT 
                ss.sprint_id,
                ss.sprint_name,
                ss.project_id,
                ss.status,
                ss.start_date,
                ss.end_date,
                ss.days_remaining,
                ss.total_points,
                ss.completed_points,
                (ss.total_points - ss.completed_points) AS remaining_points,
                ss.total_cards,
                ss.completed_cards,
                CASE WHEN ss.total_points > 0 THEN (ss.completed_points::float / ss.total_points * 100) ELSE 0 END AS completion_rate,
                CASE WHEN (current_date - ss.start_date) > 0 
                     THEN ss.completed_points::float / (current_date - ss.start_date) 
                     ELSE 0 END AS velocity,
                CASE WHEN ss.completed_points > 0 
                     THEN ss.start_date + ((ss.total_points - ss.completed_points) / 
                          NULLIF(CASE WHEN (current_date - ss.start_date) > 0 
                                     THEN ss.completed_points::float / (current_date - ss.start_date) 
                                     ELSE 0 END, 0))::integer
                     ELSE NULL END AS projected_completion_date,
                COALESCE(sh.total_hours_logged, 0) AS total_hours_logged,
                CASE WHEN ss.completed_points > 0 
                     THEN COALESCE(sh.total_hours_logged, 0)::decimal / ss.completed_points 
                     ELSE 0 END AS avg_hours_per_point,
                ss.blocked_cards_count,
                ss.dependency_issues_count,
                NOW() AS last_updated
            FROM sprint_stats ss
            LEFT JOIN sprint_hours sh ON ss.sprint_id = sh.sprint_id;
        ''',

        'mv_card_read_model': '''
            CREATE MATERIALIZED VIEW mv_card_read_model AS
            WITH card_sprints AS (
                SELECT 
                    card_id,
                    ARRAY_AGG(sprint_id ORDER BY sprint_id) AS sprint_ids
                FROM sprint_sprint_cards
                GROUP BY card_id
            ),
            card_deps AS (
                SELECT 
                    from_card_id,
                    ARRAY_AGG(to_card_id ORDER BY to_card_id) AS dependency_ids
                FROM board_card_dependencies
                GROUP BY from_card_id
            ),
            last_events AS (
                SELECT 
                    aggregate_id AS card_id,
                    MAX(created_at) AS last_event_at
                FROM core_event
                WHERE aggregate_type = 'card'
                GROUP BY aggregate_id
            )
            SELECT 
                c.id AS card_id,
                c.title,
                c.description,
                c.priority,
                c.status,
                c.order,
                l.id AS list_id,
                l.name AS list_name,
                b.id AS board_id,
                b.project_id,
                c.assignee_id,
                u.username AS assignee_username,
                c.created_by_id,
                c.story_points,
                c.is_blocked,
                c.blocked_reason,
                c.version,
                COALESCE(cs.sprint_ids, ARRAY[]::integer[]) AS sprint_ids,
                COALESCE(cd.dependency_ids, ARRAY[]::integer[]) AS dependency_ids,
                c.created_at,
                c.updated_at,
                COALESCE(le.last_event_at, c.updated_at) AS last_event_at
            FROM board_card c
            JOIN board_boardlist l ON c.list_id = l.id
            JOIN board_board b ON l.board_id = b.id
            LEFT JOIN auth_user u ON c.assignee_id = u.id
            LEFT JOIN card_sprints cs ON c.id = cs.card_id
            LEFT JOIN card_deps cd ON c.id = cd.from_card_id
            LEFT JOIN last_events le ON c.id = le.card_id;
        '''
    }
