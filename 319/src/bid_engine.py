import uuid
import time
from typing import Any, Dict, List, Optional, Tuple

from config import config
from src.prediction_model import PredictionModel
from src.traffic_layer import TrafficLayer
from src.frequency_control import FrequencyController
from src.budget_manager import BudgetManager
from src.redis_client import RedisClient
from src.exploration import ExplorationEngine, ExplorationStrategy, BiddingStrategy


class BidRequest:
    def __init__(
        self,
        request_id: str,
        user_id: str,
        ad_id: str,
        campaign_id: str,
        user_profile: Dict[str, Any],
        context: Dict[str, Any],
        ad_info: Dict[str, Any],
        floor_price: float = 0.01,
        cpa_goal: float = 10.0,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.ad_id = ad_id
        self.campaign_id = campaign_id
        self.user_profile = user_profile
        self.context = context
        self.ad_info = ad_info
        self.floor_price = floor_price
        self.cpa_goal = cpa_goal
        self.timestamp = int(time.time() * 1000)


class BidResponse:
    def __init__(
        self,
        request_id: str,
        bid_id: str,
        success: bool,
        bid_price: float = 0.0,
        reason: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.bid_id = bid_id
        self.success = success
        self.bid_price = bid_price
        self.reason = reason
        self.details = details or {}
        self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "bid_id": self.bid_id,
            "success": self.success,
            "bid_price": self.bid_price,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class BidEngine:
    def __init__(self, campaign_id: str = "default", enable_exploration: bool = None):
        self.campaign_id = campaign_id
        self.prediction_model = PredictionModel()
        self.traffic_layer = TrafficLayer()
        self.frequency_controller = FrequencyController()
        self.budget_manager = BudgetManager(campaign_id)
        self.redis_client = RedisClient()
        
        self.enable_exploration = enable_exploration if enable_exploration is not None else config.exploration.enabled
        if self.enable_exploration:
            strategy_map = {
                "epsilon_greedy": ExplorationStrategy.EPSILON_GREEDY,
                "ucb": ExplorationStrategy.UCB,
                "thompson_sampling": ExplorationStrategy.THOMPSON_SAMPLING,
                "boltzmann": ExplorationStrategy.BOLTZMANN,
            }
            strategy = strategy_map.get(config.exploration.strategy, ExplorationStrategy.UCB)
            self.exploration_engine = ExplorationEngine(
                strategy=strategy,
                epsilon=config.exploration.epsilon,
                epsilon_decay=config.exploration.epsilon_decay,
                min_epsilon=config.exploration.min_epsilon,
                ucb_c=config.exploration.ucb_c,
                boltzmann_temperature=config.exploration.boltzmann_temperature,
                min_trials_for_exploitation=config.exploration.min_trials_for_exploitation,
                exploration_budget_share=config.exploration.exploration_budget_share,
            )
        else:
            self.exploration_engine = None
        
        self.traffic_layer.allocate_budget(campaign_id, config.budget.daily_budget)
        self.prediction_model.warm_up()
        print(f"BidEngine initialized for campaign: {campaign_id}")
        print(f"  Exploration enabled: {self.enable_exploration}")

    def _check_preconditions(self, bid_request: BidRequest) -> Tuple[bool, str, Dict[str, Any]]:
        details = {}
        remaining_budget = self.budget_manager.get_remaining_budget()
        details["remaining_budget"] = remaining_budget
        if remaining_budget <= 0:
            return False, "NO_BUDGET", details
        if remaining_budget < bid_request.floor_price:
            return False, "INSUFFICIENT_BUDGET", details
        hourly_remaining = self.budget_manager.get_hourly_remaining()
        details["hourly_remaining"] = hourly_remaining
        if hourly_remaining < bid_request.floor_price:
            return False, "HOURLY_BUDGET_EXHAUSTED", details
        allowed, violated, freq_counts = self.frequency_controller.can_show(
            bid_request.user_id, bid_request.ad_id
        )
        details["frequency_violated"] = violated
        details["frequency_counts"] = freq_counts
        if not allowed:
            return False, f"FREQUENCY_LIMIT_EXCEEDED:{','.join(violated)}", details
        return True, "", details

    def _calculate_base_bid(
        self, bid_request: BidRequest, ctr: float, cvr: float
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        expected_value = ctr * cvr * bid_request.cpa_goal
        details["ctr"] = ctr
        details["cvr"] = cvr
        details["expected_value"] = expected_value
        base_bid = expected_value * 0.5
        details["base_bid"] = base_bid
        return base_bid, details

    def _apply_traffic_layer_adjustment(
        self, bid_request: BidRequest, base_bid: float, ctr: float, cvr: float
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        layer_name, layer_info = self.traffic_layer.classify(ctr, cvr)
        details["traffic_layer"] = layer_name
        details["layer_info"] = layer_info
        layer_budget_remaining = self.traffic_layer.get_layer_budget_remaining(
            layer_name, self.campaign_id
        )
        details["layer_budget_remaining"] = layer_budget_remaining
        if layer_budget_remaining < base_bid:
            details["bid_skipped"] = "LAYER_BUDGET_EXHAUSTED"
            return 0.0, details
        dynamic_multiplier = self.traffic_layer.dynamic_adjust_multiplier(
            layer_name, self.campaign_id
        )
        details["dynamic_multiplier"] = dynamic_multiplier
        adjusted_bid = base_bid * dynamic_multiplier
        details["layer_adjusted_bid"] = adjusted_bid
        return adjusted_bid, details

    def _apply_frequency_adjustment(
        self, bid_request: BidRequest, current_bid: float, ctr: float
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        bid_adjustment, forecast_details = self.frequency_controller.get_optimal_bid_adjustment(
            bid_request.user_id, bid_request.ad_id, current_bid, ctr
        )
        details["frequency_adjustment"] = bid_adjustment
        details["frequency_penalty"] = forecast_details.get("decay_penalty", 1.0)
        details["frequency_forecast_factor"] = forecast_details.get("forecast_factor", 1.0)
        details["frequency_forecast"] = forecast_details.get("frequency_forecast", {})
        details["window_details"] = forecast_details.get("window_details", {})
        adjusted_bid = current_bid * bid_adjustment
        details["frequency_adjusted_bid"] = adjusted_bid
        return adjusted_bid, details

    def _apply_budget_adjustment(
        self, current_bid: float
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        budget_multiplier = self.budget_manager.get_bid_multiplier()
        pace_adjustment = self.budget_manager.get_pace_adjustment()
        smooth_rate = self.budget_manager.get_smooth_consumption_rate()
        details["budget_multiplier"] = budget_multiplier
        details["pace_adjustment"] = pace_adjustment
        details["smooth_consumption_rate"] = smooth_rate
        adjusted_bid = current_bid * budget_multiplier
        details["budget_adjusted_bid"] = adjusted_bid
        return adjusted_bid, details

    def _apply_exploration_adjustment(
        self,
        current_bid: float,
        ctr: float,
        cvr: float,
        frequency_penalty: float = 1.0,
        budget_pace: float = 1.0,
        floor_price: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        if not self.enable_exploration or self.exploration_engine is None:
            details["exploration_enabled"] = False
            return current_bid, details
        
        strategy_name, strategy, exploration_details = self.exploration_engine.select_strategy(context)
        details.update(exploration_details)
        
        adjusted_bid = self.exploration_engine.apply_strategy_to_bid(
            base_bid=current_bid,
            strategy=strategy,
            ctr=ctr,
            cvr=cvr,
            frequency_penalty=frequency_penalty,
            budget_pace=budget_pace,
            floor_price=floor_price,
        )
        
        details["exploration_strategy"] = strategy_name
        details["strategy_bid_multiplier"] = strategy.bid_multiplier
        details["exploration_adjusted_bid"] = adjusted_bid
        
        return adjusted_bid, details

    def record_exploration_result(
        self,
        strategy_name: str,
        bid_price: float,
        ctr: float,
        cvr: float,
        was_clicked: bool = False,
        was_converted: bool = False,
    ):
        if not self.enable_exploration or self.exploration_engine is None:
            return
        
        reward = (
            was_clicked * config.exploration.reward_click_weight
            + was_converted * config.exploration.reward_conversion_weight
            - bid_price * config.exploration.reward_cost_penalty
        )
        reward = max(0.0, reward)
        
        success = was_clicked or was_converted
        self.exploration_engine.record_result(
            strategy_name=strategy_name,
            reward=reward,
            success=success,
            metadata={
                "bid_price": bid_price,
                "ctr": ctr,
                "cvr": cvr,
                "was_clicked": was_clicked,
                "was_converted": was_converted,
            },
        )

    def get_exploration_status(self) -> Dict[str, Any]:
        if not self.enable_exploration or self.exploration_engine is None:
            return {"enabled": False}
        status = self.exploration_engine.get_strategy_summary()
        status["enabled"] = True
        return status

    def _finalize_bid(
        self, bid_request: BidRequest, current_bid: float
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}
        clamped_bid = self.budget_manager.clamp_bid(current_bid)
        details["clamped_bid"] = clamped_bid
        if clamped_bid < bid_request.floor_price:
            details["bid_skipped"] = "BELOW_FLOOR_PRICE"
            return 0.0, details
        can_consume, consume_details = self.budget_manager.can_consume(clamped_bid)
        details["consume_check"] = consume_details
        if not can_consume:
            details["bid_skipped"] = "CANNOT_CONSUME_BUDGET"
            return 0.0, details
        return clamped_bid, details

    def process_bid(self, bid_request: BidRequest) -> BidResponse:
        bid_id = str(uuid.uuid4())
        all_details = {"request_id": bid_request.request_id, "bid_id": bid_id}
        try:
            success, reason, pre_details = self._check_preconditions(bid_request)
            all_details.update(pre_details)
            if not success:
                self._record_bid_result(bid_request, bid_id, 0.0, success, reason, all_details)
                return BidResponse(
                    request_id=bid_request.request_id,
                    bid_id=bid_id,
                    success=False,
                    bid_price=0.0,
                    reason=reason,
                    details=all_details,
                )
            ctr, cvr = self.prediction_model.predict(
                bid_request.user_profile, bid_request.context, bid_request.ad_info
            )
            all_details["ctr"] = ctr
            all_details["cvr"] = cvr
            base_bid, base_details = self._calculate_base_bid(bid_request, ctr, cvr)
            all_details.update(base_details)
            layer_bid, layer_details = self._apply_traffic_layer_adjustment(
                bid_request, base_bid, ctr, cvr
            )
            all_details.update(layer_details)
            if layer_bid <= 0:
                self._record_bid_result(bid_request, bid_id, 0.0, False, all_details.get("bid_skipped", "LAYER_BUDGET"), all_details)
                return BidResponse(
                    request_id=bid_request.request_id,
                    bid_id=bid_id,
                    success=False,
                    bid_price=0.0,
                    reason=all_details.get("bid_skipped", "LAYER_BUDGET_EXHAUSTED"),
                    details=all_details,
                )
            freq_bid, freq_details = self._apply_frequency_adjustment(bid_request, layer_bid, ctr)
            all_details.update(freq_details)
            if freq_bid <= 0:
                self._record_bid_result(bid_request, bid_id, 0.0, False, "FREQUENCY_PENALTY", all_details)
                return BidResponse(
                    request_id=bid_request.request_id,
                    bid_id=bid_id,
                    success=False,
                    bid_price=0.0,
                    reason="FREQUENCY_PENALTY",
                    details=all_details,
                )
            
            context = {
                "user_id": bid_request.user_id,
                "ad_id": bid_request.ad_id,
                "user_profile": bid_request.user_profile,
                "context": bid_request.context,
                "ad_info": bid_request.ad_info,
                "traffic_layer": all_details.get("traffic_layer", "B"),
            }
            exploration_bid, exploration_details = self._apply_exploration_adjustment(
                current_bid=freq_bid,
                ctr=ctr,
                cvr=cvr,
                frequency_penalty=freq_details.get("frequency_penalty", 1.0),
                budget_pace=all_details.get("pace_adjustment", 1.0),
                floor_price=bid_request.floor_price,
                context=context,
            )
            all_details.update(exploration_details)
            if exploration_bid <= 0:
                self._record_bid_result(bid_request, bid_id, 0.0, False, "EXPLORATION_SKIP", all_details)
                return BidResponse(
                    request_id=bid_request.request_id,
                    bid_id=bid_id,
                    success=False,
                    bid_price=0.0,
                    reason="EXPLORATION_SKIP",
                    details=all_details,
                )
            
            budget_bid, budget_details = self._apply_budget_adjustment(exploration_bid)
            all_details.update(budget_details)
            final_bid, final_details = self._finalize_bid(bid_request, budget_bid)
            all_details.update(final_details)
            if final_bid <= 0:
                self._record_bid_result(bid_request, bid_id, 0.0, False, all_details.get("bid_skipped", "FINAL_CHECK_FAILED"), all_details)
                return BidResponse(
                    request_id=bid_request.request_id,
                    bid_id=bid_id,
                    success=False,
                    bid_price=0.0,
                    reason=all_details.get("bid_skipped", "FINAL_CHECK_FAILED"),
                    details=all_details,
                )
            self._record_bid_result(bid_request, bid_id, final_bid, True, "SUCCESS", all_details)
            return BidResponse(
                request_id=bid_request.request_id,
                bid_id=bid_id,
                success=True,
                bid_price=round(final_bid, 4),
                reason="SUCCESS",
                details=all_details,
            )
        except Exception as e:
            error_reason = f"ERROR:{str(e)}"
            all_details["error"] = str(e)
            self._record_bid_result(bid_request, bid_id, 0.0, False, error_reason, all_details)
            return BidResponse(
                request_id=bid_request.request_id,
                bid_id=bid_id,
                success=False,
                bid_price=0.0,
                reason=error_reason,
                details=all_details,
            )

    def _record_bid_result(
        self,
        bid_request: BidRequest,
        bid_id: str,
        bid_price: float,
        success: bool,
        reason: str,
        details: Dict[str, Any],
    ):
        bid_data = {
            "request_id": bid_request.request_id,
            "bid_id": bid_id,
            "user_id": bid_request.user_id,
            "ad_id": bid_request.ad_id,
            "campaign_id": self.campaign_id,
            "bid_price": bid_price,
            "success": success,
            "reason": reason,
            "details": details,
            "timestamp": int(time.time() * 1000),
        }
        self.redis_client.record_bid(bid_id, bid_data)
        if success and bid_price > 0:
            self.budget_manager.consume_budget(bid_price)
            layer_name = details.get("traffic_layer", "C")
            self.traffic_layer.consume_layer_budget(layer_name, self.campaign_id, bid_price)
            self.traffic_layer.record_layer_impression(layer_name, self.campaign_id)
            self.traffic_layer.record_layer_cost(layer_name, self.campaign_id, bid_price)
            self.frequency_controller.record_impression(bid_request.user_id, bid_request.ad_id)

    def record_click(self, bid_id: str) -> bool:
        bid_history = self.redis_client.get_bid_history(bid_id)
        if not bid_history:
            return False
        layer_name = bid_history.get("details", {}).get("traffic_layer", "C")
        self.traffic_layer.record_layer_click(layer_name, self.campaign_id)
        return True

    def process_batch_bids(self, bid_requests: List[BidRequest]) -> List[BidResponse]:
        return [self.process_bid(req) for req in bid_requests]

    def get_engine_status(self) -> Dict[str, Any]:
        status = {
            "campaign_id": self.campaign_id,
            "budget_status": self.budget_manager.get_budget_status(),
            "traffic_layers": self.traffic_layer.get_all_layers_performance(self.campaign_id),
            "exploration_enabled": self.enable_exploration,
        }
        if self.enable_exploration and self.exploration_engine is not None:
            status["exploration_status"] = self.exploration_engine.get_strategy_summary()
        return status

    def reset_engine(self):
        self.budget_manager.reset_budget()
        self.traffic_layer.allocate_budget(self.campaign_id, config.budget.daily_budget)
        self.redis_client.clear_all()
        print(f"BidEngine reset for campaign: {self.campaign_id}")
