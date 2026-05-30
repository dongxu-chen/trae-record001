import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import format_timestamp


@dataclass
class ScalingAction:
    action_id: str
    resource_type: str
    action_type: str
    timestamp: datetime
    reason: str
    current_capacity: float
    target_capacity: float
    change_percent: float
    status: str = "pending"
    cooldown_ends: Optional[datetime] = None
    predicted_value: Optional[float] = None


@dataclass
class ScalingPolicy:
    resource_type: str
    min_instances: int
    max_instances: int
    scale_up_threshold: float
    scale_down_threshold: float
    scale_up_step: float
    scale_down_step: float
    cooldown_minutes: int
    enabled: bool = True


class AutoScaler:
    def __init__(self):
        self.policies: Dict[str, ScalingPolicy] = {}
        self.scaling_history: List[ScalingAction] = []
        self.current_capacity: Dict[str, float] = {'cpu': 100.0, 'memory': 100.0, 'disk': 100.0}
        self.cooldown_until: Dict[str, datetime] = {'cpu': None, 'memory': None, 'disk': None}
        self._initialize_policies()

    def _initialize_policies(self):
        for resource_type, res_config in config.resources.items():
            self.policies[resource_type] = ScalingPolicy(
                resource_type=resource_type,
                min_instances=config.auto_scaling_min_instances,
                max_instances=config.auto_scaling_max_instances,
                scale_up_threshold=res_config.warning_threshold,
                scale_down_threshold=res_config.warning_threshold * 0.5,
                scale_up_step=config.auto_scaling_step_percent,
                scale_down_step=config.auto_scaling_down_step_percent,
                cooldown_minutes=config.auto_scaling_cooldown_minutes,
                enabled=config.auto_scaling_enabled
            )

    def update_policy(self, resource_type: str, **kwargs) -> None:
        if resource_type not in self.policies:
            raise ValueError(f"资源类型 {resource_type} 不存在")
        for key, value in kwargs.items():
            if hasattr(self.policies[resource_type], key):
                setattr(self.policies[resource_type], key, value)

    def _is_in_cooldown(self, resource_type: str) -> bool:
        cooldown = self.cooldown_until.get(resource_type)
        if cooldown is None:
            return False
        return datetime.now() < cooldown

    def _enter_cooldown(self, resource_type: str) -> None:
        policy = self.policies[resource_type]
        self.cooldown_until[resource_type] = datetime.now() + timedelta(minutes=policy.cooldown_minutes)

    def _generate_action_id(self) -> str:
        return f"scale_{datetime.now().strftime('%Y%m%d%H%M%S')}_{np.random.randint(1000, 9999)}"

    def evaluate_scaling_need(self, forecast_df: pd.DataFrame,
                               resource_type: str,
                               current_value: float) -> Optional[ScalingAction]:
        policy = self.policies[resource_type]
        if not policy.enabled:
            return None

        if self._is_in_cooldown(resource_type):
            cooldown_end = self.cooldown_until[resource_type]
            return ScalingAction(
                action_id=self._generate_action_id(),
                resource_type=resource_type,
                action_type="cooldown",
                timestamp=datetime.now(),
                reason=f"冷却期内，下次可调整时间: {format_timestamp(cooldown_end)}",
                current_capacity=self.current_capacity[resource_type],
                target_capacity=self.current_capacity[resource_type],
                change_percent=0.0,
                status="blocked"
            )

        future_only = forecast_df[forecast_df['ds'] > datetime.now()]
        if len(future_only) == 0:
            return None

        max_predicted = future_only['yhat'].max()
        mean_predicted = future_only['yhat'].mean()

        effective_capacity = self.current_capacity[resource_type]
        effective_max = (max_predicted / effective_capacity) * 100
        effective_mean = (mean_predicted / effective_capacity) * 100

        if effective_max >= policy.scale_up_threshold:
            target_capacity = min(
                effective_capacity * (1 + policy.scale_up_step / 100),
                policy.max_instances * 100
            )
            if target_capacity > effective_capacity:
                action = ScalingAction(
                    action_id=self._generate_action_id(),
                    resource_type=resource_type,
                    action_type="scale_up",
                    timestamp=datetime.now(),
                    reason=f"预测峰值将达到 {max_predicted:.1f}% (当前容量 {effective_capacity:.0f}%)，"
                           f"超过阈值 {policy.scale_up_threshold}%",
                    current_capacity=effective_capacity,
                    target_capacity=round(target_capacity, 2),
                    change_percent=round(policy.scale_up_step, 2),
                    status="pending",
                    predicted_value=round(max_predicted, 2)
                )
                return action

        elif effective_mean < policy.scale_down_threshold:
            min_capacity = policy.min_instances * 100
            if effective_capacity > min_capacity:
                target_capacity = max(
                    effective_capacity * (1 - policy.scale_down_step / 100),
                    min_capacity
                )
                if target_capacity < effective_capacity:
                    action = ScalingAction(
                        action_id=self._generate_action_id(),
                        resource_type=resource_type,
                        action_type="scale_down",
                        timestamp=datetime.now(),
                        reason=f"预测均值仅为 {mean_predicted:.1f}%，低于缩容阈值 {policy.scale_down_threshold:.1f}%，"
                               f"当前容量有冗余",
                        current_capacity=effective_capacity,
                        target_capacity=round(target_capacity, 2),
                        change_percent=-round(policy.scale_down_step, 2),
                        status="pending",
                        predicted_value=round(mean_predicted, 2)
                    )
                    return action

        return None

    def execute_action(self, action: ScalingAction) -> ScalingAction:
        if action.status == "blocked":
            return action

        resource_type = action.resource_type
        self.current_capacity[resource_type] = action.target_capacity
        self._enter_cooldown(resource_type)
        action.status = "executed"
        action.cooldown_ends = self.cooldown_until[resource_type]
        self.scaling_history.append(action)
        return action

    def evaluate_all_resources(self, forecasts: Dict[str, pd.DataFrame],
                                current_values: Dict[str, float]) -> List[ScalingAction]:
        actions = []
        for resource_type in config.resources.keys():
            if resource_type in forecasts and resource_type in current_values:
                action = self.evaluate_scaling_need(
                    forecasts[resource_type], resource_type, current_values[resource_type])
                if action:
                    actions.append(action)
        return actions

    def get_scaling_plan(self, forecasts: Dict[str, pd.DataFrame],
                         current_values: Dict[str, float],
                         horizon_hours: int = 24) -> Dict[str, any]:
        plan = {
            'timestamp': datetime.now(),
            'horizon_hours': horizon_hours,
            'actions': [],
            'summary': {},
            'capacity_projection': []
        }

        actions = self.evaluate_all_resources(forecasts, current_values)
        pending_actions = [a for a in actions if a.status == "pending"]
        plan['actions'] = pending_actions

        for resource_type in config.resources.keys():
            forecast = forecasts.get(resource_type)
            current_cap = self.current_capacity[resource_type]
            policy = self.policies[resource_type]

            if forecast is not None:
                future = forecast[forecast['ds'] > datetime.now()]
                if len(future) > 0:
                    max_pred = future['yhat'].max()
                    effective_max = (max_pred / current_cap) * 100

                    will_scale_up = effective_max >= policy.scale_up_threshold
                    will_scale_down = effective_max < policy.scale_down_threshold and current_cap > policy.min_instances * 100

                    plan['summary'][resource_type] = {
                        'current_capacity': current_cap,
                        'max_predicted': round(max_pred, 2),
                        'effective_max_percent': round(effective_max, 2),
                        'will_scale_up': will_scale_up,
                        'will_scale_down': will_scale_down,
                        'in_cooldown': self._is_in_cooldown(resource_type),
                        'cooldown_remaining': self._get_cooldown_remaining(resource_type)
                    }

        project_time = datetime.now()
        projected_capacity = self.current_capacity.copy()
        for _ in range(horizon_hours):
            project_time += timedelta(hours=1)
            projection = {'timestamp': project_time}
            for r in config.resources.keys():
                projection[r] = projected_capacity[r]
            plan['capacity_projection'].append(projection)

        return plan

    def _get_cooldown_remaining(self, resource_type: str) -> Optional[int]:
        cooldown = self.cooldown_until.get(resource_type)
        if cooldown is None:
            return None
        remaining = (cooldown - datetime.now()).total_seconds() / 60
        return max(0, int(remaining))

    def get_scaling_history_df(self, limit: int = 50) -> pd.DataFrame:
        if not self.scaling_history:
            return pd.DataFrame()

        data = []
        for action in self.scaling_history[-limit:]:
            data.append({
                '操作ID': action.action_id,
                '资源类型': action.resource_type,
                '操作类型': action.action_type,
                '时间': action.timestamp,
                '原因': action.reason,
                '当前容量': action.current_capacity,
                '目标容量': action.target_capacity,
                '变化(%)': action.change_percent,
                '状态': action.status,
                '预测值': action.predicted_value
            })

        df = pd.DataFrame(data)
        if len(df) > 0:
            df = df.sort_values('时间', ascending=False).reset_index(drop=True)
        return df

    def simulate_auto_scaling(self, df: pd.DataFrame, forecasts: Dict[str, pd.DataFrame],
                               hours: int = 24) -> Dict[str, any]:
        simulation = {
            'initial_capacity': self.current_capacity.copy(),
            'timeline': [],
            'total_scale_ups': 0,
            'total_scale_downs': 0,
            'final_capacity': {},
            'resource_events': {r: [] for r in config.resources.keys()}
        }

        current_time = datetime.now()
        for hour in range(hours):
            time_point = current_time + timedelta(hours=hour)

            hour_state = {'timestamp': time_point, 'capacity': {}}
            for r in config.resources.keys():
                hour_state['capacity'][r] = self.current_capacity[r]

            for resource_type in config.resources.keys():
                if resource_type in forecasts:
                    forecast = forecasts[resource_type]
                    hour_forecast = forecast[(forecast['ds'] >= time_point) &
                                             (forecast['ds'] < time_point + timedelta(hours=1))]
                    if len(hour_forecast) > 0:
                        current_value = df[resource_type].iloc[-1]
                        action = self.evaluate_scaling_need(hour_forecast, resource_type, current_value)

                        if action and action.status == "pending":
                            executed = self.execute_action(action)
                            simulation['resource_events'][resource_type].append(executed)
                            if action.action_type == "scale_up":
                                simulation['total_scale_ups'] += 1
                            elif action.action_type == "scale_down":
                                simulation['total_scale_downs'] += 1

            simulation['timeline'].append(hour_state)

        simulation['final_capacity'] = self.current_capacity.copy()
        return simulation

    def get_resource_efficiency_score(self, forecast: pd.DataFrame,
                                       resource_type: str) -> float:
        future = forecast[forecast['ds'] > datetime.now()]
        if len(future) == 0:
            return 100.0

        current_cap = self.current_capacity[resource_type]
        predicted_values = future['yhat']

        over_provisioning = np.mean(np.maximum(0, current_cap - predicted_values))
        under_provisioning = np.mean(np.maximum(0, predicted_values - current_cap * 0.8))

        efficiency = 100 - (over_provisioning + under_provisioning * 2)
        return max(0, min(100, round(efficiency, 2)))

    def reset(self) -> None:
        self.scaling_history = []
        self.current_capacity = {'cpu': 100.0, 'memory': 100.0, 'disk': 100.0}
        self.cooldown_until = {'cpu': None, 'memory': None, 'disk': None}
