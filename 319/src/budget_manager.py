import time
import math
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import config
from src.redis_client import RedisClient


class AdaptivePIDController:
    def __init__(
        self,
        kp_init: float = 1.0,
        ki_init: float = 0.1,
        kd_init: float = 0.05,
        min_kp: float = 0.1,
        max_kp: float = 3.0,
        min_ki: float = 0.01,
        max_ki: float = 0.5,
        min_kd: float = 0.01,
        max_kd: float = 0.3,
        history_size: int = 100,
        adaptation_rate: float = 0.1,
    ):
        self.kp = kp_init
        self.ki = ki_init
        self.kd = kd_init
        self.kp_init = kp_init
        self.ki_init = ki_init
        self.kd_init = kd_init
        self.min_kp = min_kp
        self.max_kp = max_kp
        self.min_ki = min_ki
        self.max_ki = max_ki
        self.min_kd = min_kd
        self.max_kd = max_kd
        self.history_size = history_size
        self.adaptation_rate = adaptation_rate
        
        self.errors = deque(maxlen=history_size)
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_output = 0.0
        
        self.error_history = deque(maxlen=history_size)
        self.output_history = deque(maxlen=history_size)
        
        self.performance_window = deque(maxlen=50)
        
        self.tuning_mode = "auto"
        self.last_tuning_time = 0
        self.tuning_interval = 10

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    def _calculate_performance_metrics(self) -> Dict[str, float]:
        if len(self.errors) < 10:
            return {"mae": 0.0, "mse": 0.0, "rmse": 0.0, "mape": 0.0, "oscillation": 0.0}
        
        errors = list(self.errors)[-50:]
        mae = sum(abs(e) for e in errors) / len(errors)
        mse = sum(e ** 2 for e in errors) / len(errors)
        rmse = math.sqrt(mse)
        
        abs_errors = [abs(e) for e in errors if abs(e) > 1e-6]
        mape = sum(abs(e) for e in abs_errors) / len(abs_errors) * 100 if abs_errors else 0
        
        oscillations = 0
        for i in range(1, len(errors)):
            if (errors[i] > 0 and errors[i-1] < 0) or (errors[i] < 0 and errors[i-1] > 0):
                oscillations += 1
        oscillation_rate = oscillations / (len(errors) - 1) if len(errors) > 1 else 0
        
        return {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "mape": mape,
            "oscillation": oscillation_rate,
        }

    def _adapt_parameters(self, current_time: float):
        if current_time - self.last_tuning_time < self.tuning_interval:
            return
        
        self.last_tuning_time = current_time
        
        metrics = self._calculate_performance_metrics()
        mae = metrics["mae"]
        oscillation = metrics["oscillation"]
        
        if mae > 0.3:
            self.kp = self._clamp(self.kp * (1 + self.adaptation_rate), self.min_kp, self.max_kp)
            self.ki = self._clamp(self.ki * (1 + self.adaptation_rate * 0.5), self.min_ki, self.max_ki)
        elif mae < 0.1:
            self.kp = self._clamp(self.kp * (1 - self.adaptation_rate * 0.5), self.min_kp, self.max_kp)
            self.ki = self._clamp(self.ki * (1 - self.adaptation_rate * 0.3), self.min_ki, self.max_ki)
        
        if oscillation > 0.3:
            self.kd = self._clamp(self.kd * (1 + self.adaptation_rate * 0.8), self.min_kd, self.max_kd)
            self.kp = self._clamp(self.kp * (1 - self.adaptation_rate * 0.3), self.min_kp, self.max_kp)
        elif oscillation < 0.1:
            self.kd = self._clamp(self.kd * (1 - self.adaptation_rate * 0.3), self.min_kd, self.max_kd)
        
        if mae > 0.5 or oscillation > 0.5:
            self.kp = self._clamp(self.kp * 0.8, self.min_kp, self.max_kp)
            self.ki = self._clamp(self.ki * 0.8, self.min_ki, self.max_ki)
            self.kd = self._clamp(self.kd * 1.2, self.min_kd, self.max_kd)
        
        recent_errors = list(self.errors)[-10:]
        if len(recent_errors) >= 10:
            trend = sum(recent_errors[i] - recent_errors[i-1] for i in range(1, 10)) / 9
            if abs(trend) > 0.1:
                if trend > 0:
                    self.kp = self._clamp(self.kp * 1.1, self.min_kp, self.max_kp)
                else:
                    self.kp = self._clamp(self.kp * 0.95, self.min_kp, self.max_kp)

    def _calculate_target_spend(self, day_progress: float) -> float:
        target_curve = 1 - math.exp(-3 * day_progress)
        return target_curve

    def calculate_output(
        self,
        actual_spend: float,
        target_spend: float,
        day_progress: float,
    ) -> Tuple[float, Dict[str, float]]:
        current_time = time.time()
        
        error = target_spend - actual_spend
        self.errors.append(error)
        self.error_history.append(error)
        
        self.integral = self._clamp(self.integral + error, -10, 10)
        
        derivative = error - self.prev_error
        self.prev_error = error
        
        self._adapt_parameters(current_time)
        
        output = (
            self.kp * error
            + self.ki * self.integral
            + self.kd * derivative
        )
        
        output = self._clamp(output, 0.3, 1.8)
        
        self.prev_output = output
        self.output_history.append(output)
        
        metrics = self._calculate_performance_metrics()
        
        self.performance_window.append({
            "time": current_time,
            "error": error,
            "output": output,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "actual": actual_spend,
            "target": target_spend,
        })
        
        return output, {
            "error": error,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "integral": self.integral,
            "derivative": derivative,
            "output": output,
            **metrics,
        }

    def reset(self):
        self.kp = self.kp_init
        self.ki = self.ki_init
        self.kd = self.kd_init
        self.errors.clear()
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_output = 0.0
        self.error_history.clear()
        self.output_history.clear()
        self.performance_window.clear()
        self.last_tuning_time = 0

    def get_parameters(self) -> Dict[str, float]:
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "kp_init": self.kp_init,
            "ki_init": self.ki_init,
            "kd_init": self.kd_init,
        }

    def get_performance_history(self, limit: int = 50) -> List[Dict]:
        return list(self.performance_window)[-limit:]


class BudgetManager:
    def __init__(self, campaign_id: str = "default"):
        self.campaign_id = campaign_id
        self.redis_client = RedisClient()
        self.total_budget = config.budget.total_budget
        self.daily_budget = config.budget.daily_budget
        self.smooth_factor = config.budget.smooth_factor
        self.emergency_threshold = config.budget.emergency_threshold
        self.min_bid = config.budget.min_bid
        self.max_bid = config.budget.max_bid
        
        self.pid_controller = AdaptivePIDController(
            kp_init=getattr(config.budget, "pid_kp_init", 1.0),
            ki_init=getattr(config.budget, "pid_ki_init", 0.1),
            kd_init=getattr(config.budget, "pid_kd_init", 0.05),
            adaptation_rate=getattr(config.budget, "pid_adaptation_rate", 0.1),
        )
        
        self.last_pid_output = 1.0
        self.pid_enabled = getattr(config.budget, "pid_enabled", True)
        
        self._initialize_budget()

    def _initialize_budget(self):
        existing = self.redis_client.get_budget(self.campaign_id)
        if existing is None or "total" not in existing:
            self.redis_client.set_budget(self.campaign_id, self.total_budget, init_spent=True)

    def get_remaining_budget(self) -> float:
        return self.redis_client.get_remaining_budget(self.campaign_id)

    def get_total_spent(self) -> float:
        budget_data = self.redis_client.get_budget(self.campaign_id)
        return float(budget_data.get("spent", 0)) if budget_data else 0.0

    def get_budget_utilization_rate(self) -> float:
        budget_data = self.redis_client.get_budget(self.campaign_id)
        if not budget_data:
            return 0.0
        total = float(budget_data.get("total", 0))
        spent = float(budget_data.get("spent", 0))
        return spent / total if total > 0 else 0.0

    def get_current_hour(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H")

    def get_hourly_budget(self) -> float:
        hour = self.get_current_hour()
        key = f"budget:hourly:{self.campaign_id}:{hour}"
        with self.redis_client.get_client() as r:
            budget = r.get(key)
            if budget is None:
                hourly = self.daily_budget / 24 * self.smooth_factor
                r.setex(key, 86400, hourly)
                return hourly
            return float(budget)

    def get_hourly_remaining(self) -> float:
        hour = self.get_current_hour()
        return self.redis_client.get_hourly_remaining(self.campaign_id, hour)

    def get_pace(self) -> float:
        return self.redis_client.get_pace(self.campaign_id)

    def update_pace(self) -> float:
        current_hour = datetime.now().hour
        hour_progress = current_hour / 24.0
        utilization = self.get_budget_utilization_rate()
        if hour_progress > 0:
            pace = utilization / hour_progress
        else:
            pace = 1.0
        pace = max(0.1, min(2.0, pace))
        self.redis_client.update_pace(self.campaign_id, pace)
        return pace

    def get_smooth_consumption_rate(self) -> float:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        day_progress = (hour * 60 + minute) / (24 * 60)
        target_spend = self.daily_budget * day_progress
        actual_spend = self.get_total_spent()
        if target_spend > 0:
            smooth_rate = actual_spend / target_spend
        else:
            smooth_rate = 1.0
        return max(0.5, min(1.5, smooth_rate))

    def calculate_pid_adjustment(self) -> Tuple[float, Dict[str, float]]:
        if not self.pid_enabled:
            return 1.0, {}
        
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        day_progress = (hour * 60 + minute) / (24 * 60)
        
        target_spend = self.daily_budget * day_progress
        actual_spend = self.get_total_spent()
        
        target_normalized = target_spend / self.daily_budget if self.daily_budget > 0 else 0
        actual_normalized = actual_spend / self.daily_budget if self.daily_budget > 0 else 0
        
        output, pid_info = self.pid_controller.calculate_output(
            actual_normalized,
            target_normalized,
            day_progress,
        )
        
        self.last_pid_output = output
        return output, pid_info

    def get_pace_adjustment(self) -> float:
        pace = self.get_pace()
        utilization = self.get_budget_utilization_rate()
        
        if utilization > self.emergency_threshold:
            emergency_factor = (1.0 - utilization) / (1.0 - self.emergency_threshold)
            emergency_factor = max(0.1, emergency_factor)
            return emergency_factor
        
        if self.pid_enabled:
            pid_output, _ = self.calculate_pid_adjustment()
            base_adjustment = pid_output
        else:
            base_adjustment = 1.0
        
        if pace > 1.2:
            pace_factor = max(0.5, 1.0 - (pace - 1.0) * 0.5)
            return base_adjustment * pace_factor
        elif pace < 0.8:
            pace_factor = min(1.5, 1.0 + (0.8 - pace) * 0.5)
            return base_adjustment * pace_factor
        
        return base_adjustment

    def get_pid_status(self) -> Dict[str, Any]:
        pid_params = self.pid_controller.get_parameters()
        _, pid_info = self.calculate_pid_adjustment()
        return {
            "enabled": self.pid_enabled,
            "parameters": pid_params,
            "last_output": self.last_pid_output,
            "metrics": pid_info,
            "performance_history": self.pid_controller.get_performance_history(limit=10),
        }

    def reset_pid_controller(self):
        self.pid_controller.reset()
        self.last_pid_output = 1.0

    def can_consume(self, amount: float) -> Tuple[bool, Dict[str, float]]:
        remaining_total = self.get_remaining_budget()
        hourly_remaining = self.get_hourly_remaining()
        details = {
            "remaining_total": remaining_total,
            "hourly_remaining": hourly_remaining,
            "requested_amount": amount,
        }
        if amount <= 0:
            return False, details
        if remaining_total < amount:
            return False, details
        if hourly_remaining < amount:
            return False, details
        return True, details

    def consume_budget(self, amount: float) -> Tuple[bool, Dict[str, float]]:
        can_consume, details = self.can_consume(amount)
        if not can_consume:
            return False, details
        total_ok = self.redis_client.consume_budget(self.campaign_id, amount)
        if not total_ok:
            return False, details
        hour = self.get_current_hour()
        hourly_ok = self.redis_client.consume_hourly_budget(self.campaign_id, hour, amount)
        if not hourly_ok:
            return False, details
        self.update_pace()
        details["new_remaining_total"] = self.get_remaining_budget()
        details["new_hourly_remaining"] = self.get_hourly_remaining()
        details["new_utilization"] = self.get_budget_utilization_rate()
        return True, details

    def get_bid_multiplier(self) -> float:
        pace_adj = self.get_pace_adjustment()
        utilization = self.get_budget_utilization_rate()
        if utilization > 0.9:
            return 0.3 * pace_adj
        elif utilization > 0.7:
            return 0.6 * pace_adj
        elif utilization > 0.5:
            return 0.8 * pace_adj
        return 1.0 * pace_adj

    def clamp_bid(self, bid_price: float) -> float:
        return max(self.min_bid, min(self.max_bid, bid_price))

    def get_budget_status(self) -> Dict:
        return {
            "campaign_id": self.campaign_id,
            "total_budget": self.total_budget,
            "daily_budget": self.daily_budget,
            "remaining_total": self.get_remaining_budget(),
            "total_spent": self.get_total_spent(),
            "utilization_rate": self.get_budget_utilization_rate(),
            "hourly_budget": self.get_hourly_budget(),
            "hourly_remaining": self.get_hourly_remaining(),
            "current_pace": self.get_pace(),
            "pace_adjustment": self.get_pace_adjustment(),
            "bid_multiplier": self.get_bid_multiplier(),
            "smooth_consumption_rate": self.get_smooth_consumption_rate(),
            "emergency_mode": self.get_budget_utilization_rate() > self.emergency_threshold,
            "pid_status": self.get_pid_status() if self.pid_enabled else None,
        }

    def reset_budget(self, new_total: Optional[float] = None, new_daily: Optional[float] = None):
        if new_total is not None:
            self.total_budget = new_total
            self.redis_client.set_budget(self.campaign_id, new_total)
        if new_daily is not None:
            self.daily_budget = new_daily
        with self.redis_client.get_client() as r:
            r.hset(f"budget:{self.campaign_id}", "spent", 0)
        hour = self.get_current_hour()
        self.redis_client.set_hourly_budget(self.campaign_id, hour, self.daily_budget / 24 * self.smooth_factor)
        self.redis_client.update_pace(self.campaign_id, 1.0)
        self.reset_pid_controller()
