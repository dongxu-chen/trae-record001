import logging
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .monitor import ReplicationMetrics, Alert
from .latency_analyzer import LatencyAnalysis, LatencyCause
from .predictor import PredictionResult
from .large_transaction_detector import LargeTransaction
from .parallel_replication_optimizer import ParallelReplicationConfig

logger = logging.getLogger(__name__)


class ActionType(Enum):
    ALERT = "alert"
    KILL_TRANSACTION = "kill_transaction"
    ADJUST_PARALLEL_WORKERS = "adjust_parallel_workers"
    ENABLE_PARALLEL_REPLICATION = "enable_parallel_replication"
    SLOW_QUERY_NOTIFICATION = "slow_query_notification"
    CONFIGURATION_RECOMMENDATION = "configuration_recommendation"
    AUTO_RESTART_REPLICATION = "auto_restart_replication"


@dataclass
class RuleAction:
    action_type: ActionType
    priority: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    executed: bool = False
    execution_result: Optional[str] = None


@dataclass
class Rule:
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    action: ActionType
    priority: int
    enabled: bool = True
    cooldown_seconds: int = 300
    last_triggered: Optional[datetime] = None


class RuleEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules: List[Rule] = []
        self.actions_history: List[RuleAction] = []
        self.auto_optimize_enabled = config.get('rules', {}).get('auto_optimize', False)
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        self.rules.extend([
            Rule(
                name="critical_latency_alert",
                condition=self._check_critical_latency,
                action=ActionType.ALERT,
                priority=1,
                cooldown_seconds=60
            ),
            Rule(
                name="replication_stopped",
                condition=self._check_replication_stopped,
                action=ActionType.AUTO_RESTART_REPLICATION,
                priority=1,
                cooldown_seconds=300
            ),
            Rule(
                name="large_transaction_kill",
                condition=self._check_large_transaction_for_kill,
                action=ActionType.KILL_TRANSACTION,
                priority=2,
                cooldown_seconds=60
            ),
            Rule(
                name="predicted_latency_risk",
                condition=self._check_predicted_latency,
                action=ActionType.ALERT,
                priority=3,
                cooldown_seconds=120
            ),
            Rule(
                name="parallel_replication_optimization",
                condition=self._check_parallel_recommendation,
                action=ActionType.ADJUST_PARALLEL_WORKERS,
                priority=4,
                cooldown_seconds=600
            ),
            Rule(
                name="lock_wait_alert",
                condition=self._check_lock_waits,
                action=ActionType.ALERT,
                priority=3,
                cooldown_seconds=120
            ),
            Rule(
                name="network_latency_alert",
                condition=self._check_network_issues,
                action=ActionType.ALERT,
                priority=3,
                cooldown_seconds=180
            ),
        ])

    def _check_critical_latency(self, context: Dict[str, Any]) -> bool:
        metrics: ReplicationMetrics = context.get('metrics')
        if not metrics:
            return False
        threshold = self.config.get('monitoring', {}).get('latency_threshold_critical', 30)
        return metrics.seconds_behind_master >= threshold

    def _check_replication_stopped(self, context: Dict[str, Any]) -> bool:
        metrics: ReplicationMetrics = context.get('metrics')
        if not metrics:
            return False
        return not metrics.slave_io_running or not metrics.slave_sql_running

    def _check_large_transaction_for_kill(self, context: Dict[str, Any]) -> bool:
        transactions: List[LargeTransaction] = context.get('large_transactions', [])
        if not self.config.get('rules', {}).get('kill_long_transactions', False):
            return False
        return any(t.time >= 300 or (t.is_blocking and t.time >= 60) for t in transactions)

    def _check_predicted_latency(self, context: Dict[str, Any]) -> bool:
        prediction: PredictionResult = context.get('prediction')
        if not prediction:
            return False
        return prediction.will_exceed_threshold

    def _check_parallel_recommendation(self, context: Dict[str, Any]) -> bool:
        parallel_config: ParallelReplicationConfig = context.get('parallel_config')
        if not parallel_config or not self.config.get('rules', {}).get('enable_parallel_replication', False):
            return False
        return len(parallel_config.configuration_changes) > 0 and parallel_config.expected_improvement >= 20

    def _check_lock_waits(self, context: Dict[str, Any]) -> bool:
        analysis: LatencyAnalysis = context.get('analysis')
        if not analysis:
            return False
        return analysis.primary_cause == LatencyCause.LOCK_WAIT and analysis.confidence >= 0.5

    def _check_network_issues(self, context: Dict[str, Any]) -> bool:
        analysis: LatencyAnalysis = context.get('analysis')
        if not analysis:
            return False
        return analysis.primary_cause == LatencyCause.NETWORK and analysis.confidence >= 0.5

    def evaluate(self, context: Dict[str, Any]) -> List[RuleAction]:
        logger.info("开始评估规则...")
        actions = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.last_triggered:
                elapsed = (datetime.now() - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue

            try:
                if rule.condition(context):
                    action = self._create_action(rule, context)
                    if action:
                        actions.append(action)
                        rule.last_triggered = datetime.now()
                        logger.info(f"规则触发: {rule.name}, 动作: {rule.action.value}")
            except Exception as e:
                logger.error(f"评估规则 {rule.name} 失败: {str(e)}")

        actions.sort(key=lambda x: x.priority)
        logger.info(f"规则评估完成，生成{len(actions)}个动作")
        return actions

    def _create_action(self, rule: Rule, context: Dict[str, Any]) -> Optional[RuleAction]:
        params = {}

        if rule.action == ActionType.ALERT:
            params = self._build_alert_params(rule.name, context)
        elif rule.action == ActionType.KILL_TRANSACTION:
            params = self._build_kill_params(context)
        elif rule.action == ActionType.ADJUST_PARALLEL_WORKERS:
            params = self._build_parallel_params(context)
        elif rule.action == ActionType.AUTO_RESTART_REPLICATION:
            params = {"restart_type": "full"}
        else:
            params = {}

        return RuleAction(
            action_type=rule.action,
            priority=rule.priority,
            parameters=params,
            reason=f"规则 {rule.name} 触发"
        )

    def _build_alert_params(self, rule_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        params = {"rule_name": rule_name, "level": "WARNING"}
        metrics: ReplicationMetrics = context.get('metrics')

        if rule_name == "critical_latency_alert":
            params["level"] = "CRITICAL"
            params["message"] = f"复制延迟严重: {metrics.seconds_behind_master}秒"
            params["latency"] = metrics.seconds_behind_master
        elif rule_name == "predicted_latency_risk":
            prediction: PredictionResult = context.get('prediction')
            params["message"] = f"预测延迟将超标，趋势: {prediction.trend}"
            params["max_predicted"] = max(prediction.forecast_values)
        elif rule_name == "lock_wait_alert":
            analysis: LatencyAnalysis = context.get('analysis')
            params["level"] = "WARNING"
            params["message"] = "检测到锁等待导致的延迟问题"
        elif rule_name == "network_latency_alert":
            analysis: LatencyAnalysis = context.get('analysis')
            params["message"] = "网络问题导致延迟"

        return params

    def _build_kill_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        transactions: List[LargeTransaction] = context.get('large_transactions', [])
        to_kill = [
            t.id for t in transactions
            if t.time >= 300 or (t.is_blocking and t.time >= 60)
        ]
        return {"thread_ids": to_kill}

    def _build_parallel_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        parallel_config: ParallelReplicationConfig = context.get('parallel_config')
        changes = []
        for change in parallel_config.configuration_changes:
            if change['parameter'] == 'slave_parallel_workers':
                changes.append(change)
        return {"configuration_changes": changes}

    def execute_action(self, action: RuleAction, executor_fn: Callable) -> bool:
        if not self.auto_optimize_enabled and action.action_type not in [ActionType.ALERT]:
            logger.info(f"自动优化已禁用，跳过执行: {action.action_type.value}")
            action.executed = False
            action.execution_result = "自动优化已禁用"
            return False

        try:
            result = executor_fn(action)
            action.executed = True
            action.execution_result = str(result)
            self.actions_history.append(action)
            logger.info(f"执行动作成功: {action.action_type.value}")
            return True
        except Exception as e:
            logger.error(f"执行动作失败 {action.action_type.value}: {str(e)}")
            action.executed = False
            action.execution_result = str(e)
            return False

    def get_actions_summary(self) -> Dict[str, Any]:
        total = len(self.actions_history)
        executed = sum(1 for a in self.actions_history if a.executed)
        by_type = {}
        for action in self.actions_history:
            at = action.action_type.value
            if at not in by_type:
                by_type[at] = {"total": 0, "executed": 0}
            by_type[at]["total"] += 1
            if action.executed:
                by_type[at]["executed"] += 1

        return {
            "total_actions": total,
            "executed_actions": executed,
            "success_rate": executed / total if total > 0 else 0,
            "actions_by_type": by_type
        }

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def enable_rule(self, rule_name: str) -> bool:
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                return True
        return False
