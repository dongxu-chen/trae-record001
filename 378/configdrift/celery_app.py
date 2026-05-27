"""Celery 应用 + 定时巡检任务.

启动 worker::

    celery -A configdrift.celery_app worker -l INFO

启动 beat (定时调度)::

    celery -A configdrift.celery_app beat -l INFO

或同时启动::

    celery -A configdrift.celery_app worker --beat -l INFO

任务排队机制:
    - 使用 :func:`inspection_lock` 防止任务重叠
    - 使用队列 ``inspection:queue`` 存储待执行任务,worker 空闲时自动消费
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from configdrift.config import settings
from configdrift.logger import get_logger
from configdrift.orchestrator import (dequeue_task, enqueue_task,
                                      inspection_lock, run_inspection)

logger = get_logger(__name__)

app = Celery(
    "configdrift",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "configdrift.*": {"queue": "inspection"},
    },
)

# 定时任务
app.conf.beat_schedule = {
    "periodic-inspection": {
        "task": "configdrift.celery_app.schedule_inspection",
        "schedule": crontab(minute=f"*/{settings.schedule_minutes}"),
        "args": (),
    },
}


@app.task(name="configdrift.celery_app.schedule_inspection", bind=True)
def schedule_inspection(self):
    """定时调度入口: 若空闲则立即执行,否则进入队列."""
    with inspection_lock() as acquired:
        if acquired:
            return _do_inspection()
        # 已有任务在跑,排队等候
        pos = enqueue_task("inspection:queue")
        logger.info("已有巡检在执行,已进入队列,当前队列长度: %d", pos)
        # 延迟 60s 后尝试消费队列
        process_queue.apply_async(countdown=60)
        return {"status": "queued", "queue_position": pos}


@app.task(name="configdrift.celery_app.process_queue")
def process_queue():
    """消费队列: 依次执行排队中的巡检."""
    with inspection_lock() as acquired:
        if not acquired:
            # 还在跑,下一轮再试
            process_queue.apply_async(countdown=60)
            return {"status": "busy"}
        item = dequeue_task("inspection:queue")
        if not item:
            logger.info("队列为空,无需执行")
            return {"status": "empty"}
        logger.info("开始执行队列中的巡检: %s", item)
        return _do_inspection()


@app.task(name="configdrift.celery_app.run_async_inspection")
def run_async_inspection(only_server: str | None = None,
                         only_service: str | None = None):
    """异步执行单次巡检 (供 API/CLI 调用)."""
    with inspection_lock() as acquired:
        if not acquired:
            pos = enqueue_task("inspection:queue")
            return {"status": "queued", "queue_position": pos}
        return _do_inspection(only_server, only_service)


def _do_inspection(only_server: str | None = None,
                   only_service: str | None = None) -> dict:
    try:
        results = run_inspection(only_server=only_server,
                                 only_service=only_service)
        drift_count = sum(
            r.drift.summary.get("total", 0) if r.drift else 0
            for r in results
        )
        compliance_scores = [
            r.compliance.score for r in results if r.compliance
        ]
        avg_score = (sum(compliance_scores) / len(compliance_scores)
                     if compliance_scores else 0.0)
        result = {
            "status": "ok",
            "total_servers": len(set(r.server for r in results)),
            "total_services": len(results),
            "total_drift": drift_count,
            "compliance_avg_score": round(avg_score, 2),
            "details": [r.to_dict() for r in results],
        }
        if settings.email_on_drift and drift_count > 0:
            logger.info("检测到漂移,应发送邮件通知 (smtp 未配置或已发送)")
        return result
    except Exception as e:
        logger.exception("巡检执行失败")
        return {"status": "error", "error": str(e)}
