#!/bin/bash

BASE_URL="http://localhost:8080/api/v1"

echo "=== Creating Cron Task ==="
curl -X POST "$BASE_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每分钟日志任务",
    "description": "每分钟执行一次的日志记录任务",
    "task_type": "log",
    "payload": "{\"message\": \"Cron任务执行了\", \"level\": \"INFO\"}",
    "trigger_type": "cron",
    "cron_expr": "0 * * * * *",
    "max_retries": 3,
    "retry_delay": 5
  }'

echo -e "\n\n=== Creating Interval Task ==="
curl -X POST "$BASE_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每30秒间隔任务",
    "description": "每30秒执行一次的间隔任务",
    "task_type": "log",
    "payload": "{\"message\": \"间隔任务执行了\", \"level\": \"DEBUG\"}",
    "trigger_type": "interval",
    "interval_sec": 30,
    "max_retries": 2,
    "retry_delay": 10
  }'

echo -e "\n\n=== Creating Task A (Dependency) ==="
TASK_A=$(curl -s -X POST "$BASE_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "任务A - 前置任务",
    "description": "任务链中的第一个任务",
    "task_type": "log",
    "payload": "{\"message\": \"任务A执行完成\", \"level\": \"INFO\"}",
    "trigger_type": "manual",
    "max_retries": 3
  }' | grep -o '"id":"[^"]*"' | cut -d'"' -f4)

echo "Task A ID: $TASK_A"

echo -e "\n\n=== Creating Task B (Depends on A) ==="
curl -X POST "$BASE_URL/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "任务B - 依赖任务A",
    "description": "任务A完成后自动触发",
    "task_type": "log",
    "payload": "{\"message\": \"任务B执行了 - 任务A已完成\", \"level\": \"INFO\"}",
    "trigger_type": "manual",
    "dependencies": "'"$TASK_A"'",
    "max_retries": 3
  }'

echo -e "\n\n=== List All Tasks ==="
curl "$BASE_URL/tasks?limit=10"

echo -e "\n"
