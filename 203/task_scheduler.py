import logging
import time
import threading
from typing import Callable, Optional, Dict, Any, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_PAUSED, EVENT_JOB_RESUMED


class TaskScheduler:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.scheduler = BackgroundScheduler()
        self._job_listeners_added = False
        self._paused_jobs: set = set()
        self._lock = threading.Lock()

    def _on_job_executed(self, event) -> None:
        job_id = event.job_id
        self.logger.info(f"任务执行完成: {job_id}")

    def _on_job_error(self, event) -> None:
        job_id = event.job_id
        exception = event.exception
        traceback = event.traceback
        self.logger.error(f"任务执行失败: {job_id}, 错误: {exception}\n{traceback}")

    def _on_job_paused(self, event) -> None:
        job_id = event.job_id
        with self._lock:
            self._paused_jobs.add(job_id)
        self.logger.info(f"任务已暂停: {job_id}")

    def _on_job_resumed(self, event) -> None:
        job_id = event.job_id
        with self._lock:
            self._paused_jobs.discard(job_id)
        self.logger.info(f"任务已恢复: {job_id}")

    def _add_listeners(self) -> None:
        if not self._job_listeners_added:
            self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
            self.scheduler.add_listener(self._on_job_paused, EVENT_JOB_PAUSED)
            self.scheduler.add_listener(self._on_job_resumed, EVENT_JOB_RESUMED)
            self._job_listeners_added = True

    def add_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> None:
        self._add_listeners()

        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                args=args,
                kwargs=kwargs,
                replace_existing=True
            )
            self.logger.info(f"已添加定时任务: {job_id}, Cron表达式: {cron_expression}")
        except Exception as e:
            self.logger.error(f"添加定时任务失败 {job_id}: {e}")

    def pause_job(self, job_id: str) -> bool:
        try:
            self.scheduler.pause_job(job_id)
            return True
        except Exception as e:
            self.logger.error(f"暂停任务失败 {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        try:
            self.scheduler.resume_job(job_id)
            return True
        except Exception as e:
            self.logger.error(f"恢复任务失败 {job_id}: {e}")
            return False

    def is_job_paused(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._paused_jobs

    def start(self) -> None:
        self.logger.info("启动任务调度器")
        self.scheduler.start()

    def shutdown(self) -> None:
        self.logger.info("停止任务调度器")
        self.scheduler.shutdown()

    def run_job(self, job_id: str) -> None:
        job = self.scheduler.get_job(job_id)
        if job:
            self.logger.info(f"手动执行任务: {job_id}")
            job.func(*job.args, **job.kwargs)
        else:
            self.logger.warning(f"任务不存在: {job_id}")

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        for job in self.scheduler.get_jobs():
            with self._lock:
                is_paused = job.id in self._paused_jobs
            jobs.append({
                'id': job.id,
                'next_run_time': str(job.next_run_time) if job.next_run_time else '暂停中',
                'paused': is_paused,
                'trigger': str(job.trigger)
            })
        return jobs

    def remove_job(self, job_id: str) -> None:
        try:
            self.scheduler.remove_job(job_id)
            with self._lock:
                self._paused_jobs.discard(job_id)
            self.logger.info(f"已移除定时任务: {job_id}")
        except Exception as e:
            self.logger.error(f"移除任务失败 {job_id}: {e}")

    def run_forever(self) -> None:
        try:
            self.start()
            self.logger.info("备份系统已启动，按 Ctrl+C 停止")
            self.logger.info("可用命令: pause <任务名>, resume <任务名>, list, status, quit")
            
            def input_thread():
                while True:
                    try:
                        cmd = input().strip()
                        if cmd == 'quit':
                            self.logger.info("收到退出命令")
                            break
                        elif cmd == 'list' or cmd == 'status':
                            jobs = self.list_jobs()
                            print("\n当前任务列表:")
                            print("-" * 80)
                            for job in jobs:
                                status = "暂停" if job['paused'] else "运行"
                                print(f"任务: {job['id']}")
                                print(f"  状态: {status}")
                                print(f"  下次执行: {job['next_run_time']}")
                                print("-" * 80)
                        elif cmd.startswith('pause '):
                            job_id = cmd[6:].strip()
                            if self.pause_job(job_id):
                                print(f"任务 {job_id} 已暂停")
                            else:
                                print(f"暂停任务 {job_id} 失败")
                        elif cmd.startswith('resume '):
                            job_id = cmd[7:].strip()
                            if self.resume_job(job_id):
                                print(f"任务 {job_id} 已恢复")
                            else:
                                print(f"恢复任务 {job_id} 失败")
                        elif cmd:
                            print(f"未知命令: {cmd}")
                            print("可用命令: pause <任务名>, resume <任务名>, list, status, quit")
                    except EOFError:
                        break
                    except Exception as e:
                        self.logger.error(f"命令处理错误: {e}")
            
            thread = threading.Thread(target=input_thread, daemon=True)
            thread.start()
            
            while thread.is_alive():
                time.sleep(1)
                
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()
