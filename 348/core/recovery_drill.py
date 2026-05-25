import logging
import time
import threading
import json
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

from config import AppConfig, load_config
from core.db_driver import create_driver
from core.backup_restore import BackupRestoreManager
from core.validation_engine import ValidationEngine, CheckStatus
from core.data_diff import DataDiffAnalyzer
from core.quick_validate import QuickValidator
from report.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class DrillResult:
    drill_id: str
    start_time: float
    end_time: float
    duration_seconds: float
    restore_success: bool
    validation_success: bool
    overall_status: HealthStatus
    restore_result: Optional[Dict] = None
    validation_summary: Optional[Dict] = None
    diff_report: Optional[Dict] = None
    quick_validation: Optional[Dict] = None
    error_message: Optional[str] = None
    health_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'drill_id': self.drill_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.duration_seconds,
            'restore_success': self.restore_success,
            'validation_success': self.validation_success,
            'overall_status': self.overall_status.value,
            'restore_result': self.restore_result,
            'validation_summary': self._serializable_summary(self.validation_summary),
            'diff_report': self.diff_report.to_dict() if self.diff_report else None,
            'quick_validation': self.quick_validation.to_dict() if self.quick_validation else None,
            'error_message': self.error_message,
            'health_score': self.health_score
        }

    def _serializable_summary(self, summary: Optional[Dict]) -> Optional[Dict]:
        if not summary:
            return None
        data = summary.copy()
        if 'results' in data:
            data['results'] = [
                {
                    'check_name': r.check_name,
                    'status': r.status.value,
                    'table_name': r.table_name,
                    'message': r.message,
                    'duration_seconds': r.duration_seconds
                }
                for r in data['results']
            ]
        if 'overall_status' in data and hasattr(data['overall_status'], 'value'):
            data['overall_status'] = data['overall_status'].value
        return data


@dataclass
class HealthReport:
    generated_at: float
    period_start: float
    period_end: float
    total_drills: int
    successful_drills: int
    failed_drills: int
    average_health_score: float
    current_health_status: HealthStatus
    drill_history: List[DrillResult] = field(default_factory=list)
    trends: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'generated_at': self.generated_at,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'total_drills': self.total_drills,
            'successful_drills': self.successful_drills,
            'failed_drills': self.failed_drills,
            'average_health_score': self.average_health_score,
            'current_health_status': self.current_health_status.value,
            'drill_history': [d.to_dict() for d in self.drill_history],
            'trends': self.trends,
            'recommendations': self.recommendations
        }


class RecoveryDrillScheduler:
    """自动化恢复演练调度器 - 定期自动执行备份恢复验证"""

    def __init__(
        self,
        config_path: str,
        schedule_config: Optional[Dict[str, Any]] = None
    ):
        self.config_path = config_path
        self.app_config: Optional[AppConfig] = None
        self.schedule_config = schedule_config or {}

        self.interval_seconds = self.schedule_config.get('interval_seconds', 3600)
        self.max_history = self.schedule_config.get('max_history', 100)
        self.auto_run = self.schedule_config.get('auto_run', True)
        self.run_diff_analysis = self.schedule_config.get('run_diff_analysis', True)
        self.run_quick_validate = self.schedule_config.get('run_quick_validate', True)
        self.health_report_dir = self.schedule_config.get('health_report_dir', './output/health')

        self.drill_history: List[DrillResult] = []
        self._stop_event = threading.Event()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._is_running = False

        self._ensure_directories()
        self._load_history()

    def _ensure_directories(self):
        for d in [self.health_report_dir]:
            if not os.path.exists(d):
                os.makedirs(d)
                logger.info(f"Created directory: {d}")

    def _history_file_path(self) -> str:
        return os.path.join(self.health_report_dir, 'drill_history.json')

    def _load_history(self):
        history_file = self._history_file_path()
        if not os.path.exists(history_file):
            return

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data.get('history', [])[:self.max_history]:
                try:
                    status = HealthStatus[item.get('overall_status', 'UNKNOWN')]
                except (KeyError, ValueError):
                    status = HealthStatus.UNKNOWN

                self.drill_history.append(DrillResult(
                    drill_id=item.get('drill_id', ''),
                    start_time=item.get('start_time', 0),
                    end_time=item.get('end_time', 0),
                    duration_seconds=item.get('duration_seconds', 0),
                    restore_success=item.get('restore_success', False),
                    validation_success=item.get('validation_success', False),
                    overall_status=status,
                    error_message=item.get('error_message'),
                    health_score=item.get('health_score', 0)
                ))

            logger.info(f"Loaded {len(self.drill_history)} historical drill records")
        except Exception as e:
            logger.warning(f"Failed to load drill history: {e}")

    def _save_history(self):
        history_file = self._history_file_path()
        try:
            data = {
                'updated_at': time.time(),
                'history': [d.to_dict() for d in self.drill_history[-self.max_history:]]
            }
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save drill history: {e}")

    def _calculate_health_score(
        self,
        restore_success: bool,
        validation_summary: Optional[Dict]
    ) -> int:
        if not restore_success:
            return 0

        if not validation_summary:
            return 50

        pass_rate = validation_summary.get('pass_rate', 0)
        failed = validation_summary.get('failed', 0)
        errors = validation_summary.get('errors', 0)
        warnings = validation_summary.get('warnings', 0)

        score = pass_rate

        if errors > 0:
            score = max(0, score - 30)
        if failed > 0:
            score = max(0, score - 20)
        if warnings > 0:
            score = max(0, score - 5)

        return int(min(100, max(0, score)))

    def _determine_health_status(self, health_score: int, restore_success: bool) -> HealthStatus:
        if not restore_success:
            return HealthStatus.UNHEALTHY
        if health_score >= 90:
            return HealthStatus.HEALTHY
        elif health_score >= 70:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def run_single_drill(self) -> DrillResult:
        drill_id = f"drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"{'='*60}")
        logger.info(f"Starting recovery drill: {drill_id}")
        logger.info(f"{'='*60}")

        start_time = time.time()
        app_config = load_config(self.config_path)

        source_driver = None
        verify_driver = None

        restore_success = False
        validation_success = False
        restore_result = None
        validation_summary = None
        diff_report = None
        quick_validation = None
        error_msg = None

        try:
            source_driver = create_driver(app_config.source_db)
            verify_driver = create_driver(app_config.verification_db)

            if not source_driver.connect() or not verify_driver.connect():
                raise RuntimeError("Failed to connect to databases")

            logger.info("Step 1: Running Quick Validation (pre-restore)...")
            if self.run_quick_validate:
                quick_validator = QuickValidator(source_driver, verify_driver, {
                    'row_count_tolerance': app_config.validation.row_count_tolerance
                })
                quick_validation = quick_validator.run_quick_validation()

            logger.info("Step 2: Deploying and restoring backup...")
            restore_manager = BackupRestoreManager(app_config.backup, verify_driver)
            restore_result = restore_manager.deploy_and_restore()
            restore_success = restore_result.get('success', False)

            if not restore_success:
                raise RuntimeError(f"Backup restore failed: {restore_result.get('error', 'Unknown error')}")

            logger.info("Step 3: Running full validation...")
            engine = ValidationEngine(app_config.validation, source_driver, verify_driver)
            validation_summary = engine.run_all_validations()

            validation_status = validation_summary.get('overall_status')
            validation_success = validation_status in (CheckStatus.PASSED, CheckStatus.WARNING)

            logger.info("Step 4: Running data diff analysis...")
            if self.run_diff_analysis:
                diff_analyzer = DataDiffAnalyzer(source_driver, verify_driver, {
                    'max_data_diffs_per_table': 50,
                    'compare_row_values': True,
                    'deep_compare': False
                })
                diff_report = diff_analyzer.run_diff_analysis()

            health_score = self._calculate_health_score(restore_success, validation_summary)
            health_status = self._determine_health_status(health_score, restore_success)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Drill failed: {e}", exc_info=True)
            health_score = 0
            health_status = HealthStatus.UNHEALTHY

        finally:
            if source_driver:
                source_driver.disconnect()
            if verify_driver:
                verify_driver.disconnect()

        end_time = time.time()
        duration = end_time - start_time

        result = DrillResult(
            drill_id=drill_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            restore_success=restore_success,
            validation_success=validation_success,
            overall_status=health_status,
            restore_result=restore_result,
            validation_summary=validation_summary,
            diff_report=diff_report,
            quick_validation=quick_validation,
            error_message=error_msg,
            health_score=health_score
        )

        self.drill_history.append(result)
        if len(self.drill_history) > self.max_history:
            self.drill_history = self.drill_history[-self.max_history:]
        self._save_history()

        self._generate_drill_report(result, app_config)

        logger.info(f"Drill {drill_id} complete: {health_status.value} (score={health_score}/100, duration={duration:.1f}s)")
        return result

    def _generate_drill_report(self, drill_result: DrillResult, app_config: AppConfig):
        try:
            report_gen = ReportGenerator(
                output_dir=os.path.join(self.health_report_dir, 'drills'),
                include_detailed_log=True
            )

            config_dict = {
                'source_db': {
                    'host': app_config.source_db.host,
                    'port': app_config.source_db.port,
                    'database': app_config.source_db.database
                },
                'verification_db': {
                    'host': app_config.verification_db.host,
                    'port': app_config.verification_db.port,
                    'database': app_config.verification_db.database
                },
                'backup': {
                    'backup_file_path': app_config.backup.backup_file_path,
                    'backup_type': app_config.backup.backup_type
                },
                'validation': {
                    'row_count_tolerance': app_config.validation.row_count_tolerance,
                    'sample_percentage': app_config.validation.sample_percentage
                }
            }

            validation_summary = drill_result.validation_summary or {
                'overall_status': CheckStatus.ERROR,
                'passed': 0, 'failed': 0, 'warnings': 0, 'errors': 0,
                'skipped': 0, 'pass_rate': 0, 'results': []
            }

            report_gen.generate_report(
                restore_result=drill_result.restore_result or {},
                validation_summary=validation_summary,
                config=config_dict
            )

        except Exception as e:
            logger.warning(f"Failed to generate drill report: {e}")

    def generate_health_report(self, period_hours: int = 24) -> HealthReport:
        logger.info(f"Generating health report for last {period_hours} hours")

        now = time.time()
        period_start = now - (period_hours * 3600)

        recent_drills = [
            d for d in self.drill_history
            if d.start_time >= period_start
        ]

        total = len(recent_drills)
        successful = sum(1 for d in recent_drills if d.overall_status != HealthStatus.UNHEALTHY)
        failed = total - successful
        avg_score = sum(d.health_score for d in recent_drills) / total if total > 0 else 0

        current_status = HealthStatus.UNKNOWN
        if recent_drills:
            current_status = recent_drills[-1].overall_status

        trends = self._analyze_trends(recent_drills)
        recommendations = self._generate_recommendations(recent_drills, trends)

        report = HealthReport(
            generated_at=now,
            period_start=period_start,
            period_end=now,
            total_drills=total,
            successful_drills=successful,
            failed_drills=failed,
            average_health_score=avg_score,
            current_health_status=current_status,
            drill_history=recent_drills,
            trends=trends,
            recommendations=recommendations
        )

        self._save_health_report(report)
        return report

    def _analyze_trends(self, recent_drills: List[DrillResult]) -> Dict[str, Any]:
        if len(recent_drills) < 2:
            return {'insufficient_data': True}

        scores = [d.health_score for d in recent_drills]
        durations = [d.duration_seconds for d in recent_drills]

        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        trend = 'stable'
        if avg_second > avg_first + 5:
            trend = 'improving'
        elif avg_second < avg_first - 5:
            trend = 'declining'

        consecutive_failures = 0
        for d in reversed(recent_drills):
            if d.overall_status == HealthStatus.UNHEALTHY:
                consecutive_failures += 1
            else:
                break

        return {
            'health_score_trend': trend,
            'average_score_first_half': avg_first,
            'average_score_second_half': avg_second,
            'score_improvement': avg_second - avg_first,
            'average_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'consecutive_failures': consecutive_failures,
            'success_rate': (len([d for d in recent_drills if d.overall_status != HealthStatus.UNHEALTHY]) / len(recent_drills) * 100) if recent_drills else 0
        }

    def _generate_recommendations(
        self,
        recent_drills: List[DrillResult],
        trends: Dict[str, Any]
    ) -> List[str]:
        recommendations = []

        if trends.get('insufficient_data'):
            recommendations.append("需要更多演练数据以进行趋势分析，建议增加演练频率")
            return recommendations

        if trends.get('health_score_trend') == 'declining':
            recommendations.append(f"健康评分呈下降趋势（{trends.get('score_improvement', 0):+.1f}），建议检查备份策略和数据一致性")

        if trends.get('consecutive_failures', 0) >= 2:
            recommendations.append(f"连续 {trends['consecutive_failures']} 次演练失败，建议紧急排查备份系统")

        if trends.get('success_rate', 100) < 80:
            recommendations.append(f"近期成功率仅 {trends['success_rate']:.1f}%，低于80%阈值，建议检查备份有效性")

        if trends.get('average_duration', 0) > 3600:
            recommendations.append(f"平均恢复时间 {trends['average_duration']/60:.1f} 分钟，超过1小时，建议优化恢复流程")

        failed_drills = [d for d in recent_drills if d.overall_status == HealthStatus.UNHEALTHY]
        if failed_drills:
            errors = set(d.error_message for d in failed_drills if d.error_message)
            for err in list(errors)[:3]:
                recommendations.append(f"常见错误: {err[:100]}")

        if not recommendations:
            recommendations.append("备份恢复系统运行正常，建议继续保持当前监控频率")

        return recommendations

    def _save_health_report(self, report: HealthReport):
        try:
            timestamp = datetime.fromtimestamp(report.generated_at).strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(
                self.health_report_dir,
                f'health_report_{timestamp}.json'
            )
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Health report saved: {file_path}")

            latest_path = os.path.join(self.health_report_dir, 'latest_health_report.json')
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Failed to save health report: {e}")

    def start(self, on_drill_complete: Optional[Callable[[DrillResult], None]] = None):
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        self._is_running = True
        self._stop_event.clear()

        def scheduler_loop():
            logger.info(f"Recovery drill scheduler started, interval={self.interval_seconds}s")

            while not self._stop_event.is_set():
                try:
                    result = self.run_single_drill()
                    if on_drill_complete:
                        try:
                            on_drill_complete(result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                    self.generate_health_report()

                except Exception as e:
                    logger.error(f"Scheduler loop error: {e}", exc_info=True)

                if self._stop_event.wait(self.interval_seconds):
                    break

            logger.info("Recovery drill scheduler stopped")
            self._is_running = False

        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def stop(self):
        logger.info("Stopping recovery drill scheduler...")
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running
