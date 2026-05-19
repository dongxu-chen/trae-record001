#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agile_pm.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Project
from board.models import Board, BoardList, Card
from sprint.models import Sprint
from datetime import date, timedelta


def init_demo_data():
    print('Creating demo user...')
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_superuser': True,
            'is_staff': True,
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
        print('Created admin user (password: admin123)')
    else:
        print('Admin user already exists')

    print('Creating demo project...')
    project, created = Project.objects.get_or_create(
        name='Demo Project',
        defaults={
            'description': '这是一个演示项目，展示敏捷项目管理工具的功能',
            'owner': user,
        }
    )
    if created:
        project.members.add(user)
        print('Created demo project')
    else:
        print('Demo project already exists')

    print('Creating demo board...')
    board, created = Board.objects.get_or_create(
        project=project,
        defaults={'name': '开发看板'}
    )
    if created:
        print('Created demo board')

        print('Creating board lists...')
        list_todo = BoardList.objects.create(board=board, name='待办', order=0)
        list_progress = BoardList.objects.create(board=board, name='进行中', order=1)
        list_review = BoardList.objects.create(board=board, name='评审中', order=2)
        list_done = BoardList.objects.create(board=board, name='已完成', order=3)
        print('Created 4 board lists')

        print('Creating demo cards...')
        cards_data = [
            (list_todo, '用户认证功能', '实现用户登录、注册、密码重置功能', 'high', 8, 0),
            (list_todo, '数据库设计', '设计项目数据库表结构和关系', 'medium', 5, 1),
            (list_progress, 'API接口开发', '开发RESTful API接口', 'high', 13, 0),
            (list_review, '前端页面设计', '设计项目前端页面原型', 'medium', 3, 0),
            (list_done, '需求分析文档', '完成项目需求分析和文档编写', 'low', 2, 0),
        ]

        for card_list, title, desc, priority, points, order in cards_data:
            Card.objects.create(
                list=card_list,
                title=title,
                description=desc,
                priority=priority,
                status='todo' if card_list == list_todo else 'in_progress' if card_list == list_progress else 'review' if card_list == list_review else 'done',
                order=order,
                assignee=user,
                created_by=user,
                story_points=points,
            )
        print('Created 5 demo cards')

    print('Creating demo sprint...')
    sprint, created = Sprint.objects.get_or_create(
        name='Sprint 1',
        project=project,
        defaults={
            'goal': '完成用户认证和基础API开发',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=14),
            'status': 'active',
        }
    )
    if created:
        for card in Card.objects.all()[:3]:
            sprint.cards.add(card)
        print('Created demo sprint')

    print('\nDemo data initialization complete!')
    print('Username: admin')
    print('Password: admin123')


if __name__ == '__main__':
    init_demo_data()
