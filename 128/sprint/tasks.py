from celery import shared_task
from datetime import timedelta
from django.db.models import Sum
from .models import Sprint, BurndownEntry


@shared_task(queue='high')
def generate_burndown_data(sprint_id):
    try:
        sprint = Sprint.objects.select_related('project').prefetch_related('cards').get(id=sprint_id)
    except Sprint.DoesNotExist:
        return f'Sprint {sprint_id} not found'

    if sprint.status != 'active':
        return f'Sprint {sprint_id} is not active'

    start_date = sprint.start_date
    end_date = sprint.end_date
    
    total_points = sprint.cards.aggregate(
        total=Sum('story_points')
    )['total'] or 0
    
    cards_list = list(sprint.cards.all())

    current_date = start_date
    while current_date <= end_date:
        completed_points = sum(
            card.story_points for card in cards_list
            if card.status == 'done' and card.updated_at.date() <= current_date
        )
        remaining_points = total_points - completed_points

        BurndownEntry.objects.update_or_create(
            sprint=sprint,
            date=current_date,
            defaults={
                'remaining_points': remaining_points,
                'completed_points': completed_points
            }
        )

        current_date += timedelta(days=1)

    return f'Burndown data generated for sprint {sprint_id}'


@shared_task(queue='periodic')
def update_all_active_sprints_burndown():
    active_sprints = Sprint.objects.filter(status='active').prefetch_related('cards')
    for sprint in active_sprints:
        generate_burndown_data.apply_async(args=[sprint.id], queue='high')
    return f'Updated burndown data for {active_sprints.count()} sprints'
