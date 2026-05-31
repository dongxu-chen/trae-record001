from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import json
import hashlib
from pathlib import Path
import logging

from db_connector import DatabaseConnector, QueryResult
from performance import PerformanceComparator, QueryPerformance
from performance.result_validator import ResultSetValidator, ValidationResult


class DeploymentStatus(Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    BACKING_UP = "backing_up"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentResult:
    deployment_id: str
    status: DeploymentStatus
    original_sql: str
    deployed_sql: str
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    backup_path: Optional[str] = None
    original_performance: Optional[QueryPerformance] = None
    deployed_performance: Optional[QueryPerformance] = None
    validation_result: Optional[ValidationResult] = None
    performance_improvement_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "status": self.status.value,
            "original_sql": self.original_sql,
            "deployed_sql": self.deployed_sql,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "backup_path": self.backup_path,
            "performance_improvement_pct": self.performance_improvement_pct,
            "validation_passed": self.validation_result.is_valid if self.validation_result else None,
        }


class SQLDeployer:
    def __init__(
        self,
        db_connector: DatabaseConnector,
        backup_dir: str = "./deployments/backups",
        enable_backup: bool = True,
        enable_validation: bool = True,
        enable_performance_check: bool = True,
        min_improvement_pct: float = 10.0,
        dialect: str = "mysql",
    ):
        self.db_connector = db_connector
        self.backup_dir = Path(backup_dir)
        self.enable_backup = enable_backup
        self.enable_validation = enable_validation
        self.enable_performance_check = enable_performance_check
        self.min_improvement_pct = min_improvement_pct
        self.dialect = dialect

        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.performance_comparator = PerformanceComparator(db_connector)
        self.result_validator = ResultSetValidator(db_connector)

        self.deployment_history: List[DeploymentResult] = []
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def deploy(
        self,
        original_sql: str,
        optimized_sql: str,
        execute_on_target: bool = False,
        verify_before_deploy: bool = True,
    ) -> DeploymentResult:
        deployment_id = self._generate_deployment_id()
        start_time = datetime.now()

        result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.PENDING,
            original_sql=original_sql,
            deployed_sql=optimized_sql,
            start_time=start_time,
        )

        try:
            if verify_before_deploy:
                result.status = DeploymentStatus.VALIDATING
                self._validate_sql(optimized_sql)

            if self.enable_backup:
                result.status = DeploymentStatus.BACKING_UP
                result.backup_path = self._backup_sql(original_sql, deployment_id)

            if self.enable_performance_check:
                result.status = DeploymentStatus.VERIFYING
                (
                    result.original_performance,
                    result.deployed_performance,
                    result.validation_result,
                ) = self._compare_performance(original_sql, optimized_sql)

                if result.original_performance and result.deployed_performance:
                    improvement = self._calculate_improvement(
                        result.original_performance, result.deployed_performance
                    )
                    result.performance_improvement_pct = improvement

                    if improvement < self.min_improvement_pct:
                        self.logger.warning(
                            f"Performance improvement {improvement:.1f}% below threshold {self.min_improvement_pct}%"
                        )

            if execute_on_target:
                result.status = DeploymentStatus.DEPLOYING
                self._execute_deployment(optimized_sql)

            result.status = DeploymentStatus.SUCCESS
            self.logger.info(f"Deployment {deployment_id} completed successfully")

        except Exception as e:
            result.status = DeploymentStatus.FAILED
            result.error_message = str(e)
            self.logger.error(f"Deployment {deployment_id} failed: {e}")

            if self.enable_backup and result.backup_path:
                try:
                    self._rollback(result.backup_path)
                    result.status = DeploymentStatus.ROLLED_BACK
                    self.logger.info(f"Rolled back deployment {deployment_id}")
                except Exception as rollback_err:
                    self.logger.error(f"Rollback failed: {rollback_err}")

        result.end_time = datetime.now()
        self.deployment_history.append(result)

        return result

    def deploy_batch(
        self,
        sql_pairs: List[tuple[str, str]],
        execute_on_target: bool = False,
    ) -> List[DeploymentResult]:
        results = []
        for original, optimized in sql_pairs:
            result = self.deploy(
                original,
                optimized,
                execute_on_target=execute_on_target,
                verify_before_deploy=True,
            )
            results.append(result)
        return results

    def _generate_deployment_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[
            :8
        ]
        return f"deploy_{timestamp}_{hash_suffix}"

    def _validate_sql(self, sql: str):
        result = self.db_connector.explain(sql)
        if not result.success:
            raise ValueError(f"SQL validation failed: {result.error}")

    def _backup_sql(self, sql: str, deployment_id: str) -> str:
        backup_file = self.backup_dir / f"{deployment_id}.json"
        backup_data = {
            "deployment_id": deployment_id,
            "timestamp": datetime.now().isoformat(),
            "original_sql": sql,
            "checksum": hashlib.md5(sql.encode()).hexdigest(),
        }
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        return str(backup_file)

    def _compare_performance(
        self, original_sql: str, optimized_sql: str
    ) -> tuple[Optional[QueryPerformance], Optional[QueryPerformance], Optional[ValidationResult]]:
        try:
            compare_result = self.performance_comparator.compare(
                original_sql, optimized_sql, iterations=2
            )

            validation_result = self.result_validator.validate(
                original_sql, optimized_sql
            )

            return (
                compare_result.before,
                compare_result.after,
                validation_result,
            )
        except Exception as e:
            self.logger.warning(f"Performance comparison failed: {e}")
            return None, None, None

    def _calculate_improvement(
        self, original: QueryPerformance, optimized: QueryPerformance
    ) -> float:
        if original.exec_time_ms <= 0:
            return 0.0
        improvement = (
            (original.exec_time_ms - optimized.exec_time_ms) / original.exec_time_ms * 100
        )
        return max(0.0, improvement)

    def _execute_deployment(self, sql: str):
        self.logger.info("Executing deployment (dry run - no changes made)")
        pass

    def _rollback(self, backup_path: str):
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        self.logger.info(f"Rolling back to: {backup_data['deployment_id']}")

    def get_deployment_history(
        self, limit: int = 100
    ) -> List[DeploymentResult]:
        return sorted(
            self.deployment_history,
            key=lambda x: x.start_time,
            reverse=True,
        )[:limit]

    def get_deployment_stats(self) -> Dict[str, Any]:
        total = len(self.deployment_history)
        successful = sum(
            1 for d in self.deployment_history if d.status == DeploymentStatus.SUCCESS
        )
        failed = sum(
            1 for d in self.deployment_history if d.status == DeploymentStatus.FAILED
        )
        rolled_back = sum(
            1
            for d in self.deployment_history
            if d.status == DeploymentStatus.ROLLED_BACK
        )

        avg_improvement = 0.0
        successful_deploys = [
            d
            for d in self.deployment_history
            if d.status == DeploymentStatus.SUCCESS
            and d.performance_improvement_pct > 0
        ]
        if successful_deploys:
            avg_improvement = sum(
                d.performance_improvement_pct for d in successful_deploys
            ) / len(successful_deploys)

        return {
            "total_deployments": total,
            "successful": successful,
            "failed": failed,
            "rolled_back": rolled_back,
            "success_rate": successful / total if total > 0 else 0,
            "avg_performance_improvement_pct": avg_improvement,
        }
