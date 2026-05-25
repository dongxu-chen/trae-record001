import json
import time
import tempfile
import os
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import optuna
    from optuna import Trial, Study
    from optuna.samplers import TPESampler, RandomSampler, GridSampler
    from optuna.pruners import MedianPruner, SuccessiveHalvingPruner
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from config import config
from src.auction_simulator import AuctionSimulator, SimulationStats
from src.bid_engine import BidEngine
from src.exploration import ExplorationStrategy


class OptimizationMetric(Enum):
    TOTAL_PROFIT = "total_profit"
    ROAS = "roas"
    WIN_RATE = "win_rate"
    CTR = "ctr"
    CVR = "cvr"
    CLICKS = "total_clicks"
    CONVERSIONS = "total_conversions"


class SamplerType(Enum):
    TPE = "tpe"
    RANDOM = "random"
    GRID = "grid"


class PrunerType(Enum):
    MEDIAN = "median"
    SUCCESSIVE_HALVING = "successive_halving"
    NONE = "none"


@dataclass
class TuningResult:
    best_params: Dict[str, Any]
    best_value: float
    metric: str
    n_trials: int
    study_name: str
    duration: float
    trial_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_params": self.best_params,
            "best_value": self.best_value,
            "metric": self.metric,
            "n_trials": self.n_trials,
            "study_name": self.study_name,
            "duration": self.duration,
            "trial_results": self.trial_results,
        }
    
    def save(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str) -> "TuningResult":
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            best_params=data["best_params"],
            best_value=data["best_value"],
            metric=data["metric"],
            n_trials=data["n_trials"],
            study_name=data["study_name"],
            duration=data["duration"],
            trial_results=data.get("trial_results", []),
        )


@dataclass
class ParameterRange:
    name: str
    param_type: str
    low: Optional[float] = None
    high: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[List[Any]] = None
    log: bool = False


class AutoTuner:
    def __init__(
        self,
        metric: str = "total_profit",
        direction: str = "maximize",
        n_trials: Optional[int] = None,
        timeout: Optional[int] = None,
        sampler_type: str = "tpe",
        pruner_type: str = "median",
        study_name: Optional[str] = None,
        storage: Optional[str] = None,
        random_seed: int = 42,
    ):
        if not OPTUNA_AVAILABLE:
            raise ImportError(
                "Optuna is not installed. Install it with: pip install optuna"
            )
        
        self.metric = metric
        self.direction = direction
        self.n_trials = n_trials or config.auto_tuner.n_trials
        self.timeout = timeout or config.auto_tuner.timeout
        self.study_name = study_name or config.auto_tuner.study_name
        self.storage = storage
        self.random_seed = random_seed
        
        self.sampler = self._create_sampler(sampler_type)
        self.pruner = self._create_pruner(pruner_type)
        
        self.parameter_ranges = self._get_default_parameter_ranges()
        self._study: Optional[Study] = None
    
    def _create_sampler(self, sampler_type: str):
        if sampler_type == "tpe":
            return TPESampler(seed=self.random_seed)
        elif sampler_type == "random":
            return RandomSampler(seed=self.random_seed)
        elif sampler_type == "grid":
            return None
        else:
            return TPESampler(seed=self.random_seed)
    
    def _create_pruner(self, pruner_type: str):
        if pruner_type == "median":
            return MedianPruner(
                n_startup_trials=5,
                n_warmup_steps=0,
                interval_steps=1,
            )
        elif pruner_type == "successive_halving":
            return SuccessiveHalvingPruner(
                min_resource=1,
                reduction_factor=4,
            )
        else:
            return None
    
    def _get_default_parameter_ranges(self) -> List[ParameterRange]:
        return [
            ParameterRange(
                name="bid_base_multiplier",
                param_type="float",
                low=0.3,
                high=1.5,
                step=0.05,
            ),
            ParameterRange(
                name="ctr_weight",
                param_type="float",
                low=0.5,
                high=2.0,
                step=0.1,
            ),
            ParameterRange(
                name="cvr_weight",
                param_type="float",
                low=0.5,
                high=3.0,
                step=0.1,
            ),
            ParameterRange(
                name="frequency_penalty_weight",
                param_type="float",
                low=0.3,
                high=2.0,
                step=0.1,
            ),
            ParameterRange(
                name="budget_pace_weight",
                param_type="float",
                low=0.5,
                high=1.5,
                step=0.1,
            ),
            ParameterRange(
                name="exploration_strategy",
                param_type="categorical",
                choices=["ucb", "epsilon_greedy", "boltzmann", "thompson_sampling"],
            ),
            ParameterRange(
                name="exploration_epsilon",
                param_type="float",
                low=0.01,
                high=0.3,
                log=True,
            ),
            ParameterRange(
                name="ucb_c",
                param_type="float",
                low=0.5,
                high=3.0,
                step=0.1,
            ),
            ParameterRange(
                name="pid_kp",
                param_type="float",
                low=0.1,
                high=3.0,
                step=0.1,
            ),
            ParameterRange(
                name="pid_ki",
                param_type="float",
                low=0.01,
                high=0.5,
                step=0.01,
            ),
            ParameterRange(
                name="pid_kd",
                param_type="float",
                low=0.01,
                high=0.3,
                step=0.01,
            ),
        ]
    
    def add_parameter_range(self, param_range: ParameterRange):
        self.parameter_ranges.append(param_range)
    
    def _suggest_params(self, trial: Trial) -> Dict[str, Any]:
        params = {}
        for pr in self.parameter_ranges:
            if pr.param_type == "float":
                if pr.choices:
                    params[pr.name] = trial.suggest_float(
                        pr.name, pr.low, pr.high, step=pr.step, log=pr.log
                    )
                else:
                    params[pr.name] = trial.suggest_float(
                        pr.name, pr.low, pr.high, step=pr.step, log=pr.log
                    )
            elif pr.param_type == "int":
                params[pr.name] = trial.suggest_int(
                    pr.name, int(pr.low), int(pr.high), step=int(pr.step or 1), log=pr.log
                )
            elif pr.param_type == "categorical":
                params[pr.name] = trial.suggest_categorical(pr.name, pr.choices)
            elif pr.param_type == "bool":
                params[pr.name] = trial.suggest_categorical(pr.name, [True, False])
        return params
    
    def _apply_params_to_config(self, params: Dict[str, Any]):
        if "bid_base_multiplier" in params:
            config.budget.bid_base_multiplier = params["bid_base_multiplier"]
        
        if "ctr_weight" in params:
            config.exploration.reward_click_weight = params["ctr_weight"]
        
        if "cvr_weight" in params:
            config.exploration.reward_conversion_weight = params["cvr_weight"]
        
        if "exploration_strategy" in params:
            config.exploration.strategy = params["exploration_strategy"]
        
        if "exploration_epsilon" in params:
            config.exploration.epsilon = params["exploration_epsilon"]
        
        if "ucb_c" in params:
            config.exploration.ucb_c = params["ucb_c"]
        
        if "pid_kp" in params:
            config.budget.pid_kp_init = params["pid_kp"]
        
        if "pid_ki" in params:
            config.budget.pid_ki_init = params["pid_ki"]
        
        if "pid_kd" in params:
            config.budget.pid_kd_init = params["pid_kd"]
    
    def _evaluate_params(
        self,
        params: Dict[str, Any],
        num_auctions: int = 200,
    ) -> Tuple[float, SimulationStats]:
        self._apply_params_to_config(params)
        
        bid_engine = BidEngine("tuning_campaign", enable_exploration=True)
        
        if bid_engine.budget_manager is not None and hasattr(bid_engine.budget_manager, 'pid_controller') and bid_engine.budget_manager.pid_controller is not None:
            bid_engine.budget_manager.pid_controller.kp = params.get("pid_kp", config.budget.pid_kp_init)
            bid_engine.budget_manager.pid_controller.ki = params.get("pid_ki", config.budget.pid_ki_init)
            bid_engine.budget_manager.pid_controller.kd = params.get("pid_kd", config.budget.pid_kd_init)
        
        if bid_engine.exploration_engine is not None:
            freq_weight = params.get("frequency_penalty_weight", 1.0)
            budget_weight = params.get("budget_pace_weight", 1.0)
            ctr_w = params.get("ctr_weight", 1.0)
            cvr_w = params.get("cvr_weight", 1.0)
            bid_mult = params.get("bid_base_multiplier", 1.0)
            
            for strategy_name, strategy in bid_engine.exploration_engine.strategies.items():
                strategy.frequency_penalty_weight = freq_weight
                strategy.budget_pace_weight = budget_weight
                strategy.ctr_weight = ctr_w
                strategy.cvr_weight = cvr_w
                strategy.bid_multiplier = bid_mult
        
        simulator = AuctionSimulator(
            bid_engine=bid_engine,
            num_competitors=3,
            random_seed=self.random_seed,
        )
        
        stats = simulator.run_simulation(num_auctions=num_auctions)
        
        metric_value = self._extract_metric(stats)
        
        return metric_value, stats
    
    def _extract_metric(self, stats: SimulationStats) -> float:
        if self.metric == "total_profit":
            return stats.total_profit
        elif self.metric == "roas":
            return stats.roas
        elif self.metric == "win_rate":
            return stats.win_rate
        elif self.metric == "ctr":
            return stats.ctr
        elif self.metric == "cvr":
            return stats.cvr
        elif self.metric == "total_clicks":
            return float(stats.total_clicks)
        elif self.metric == "total_conversions":
            return float(stats.total_conversions)
        else:
            return stats.total_profit
    
    def _objective(self, trial: Trial) -> float:
        params = self._suggest_params(trial)
        metric_value, stats = self._evaluate_params(params, num_auctions=100)
        
        trial.set_user_attr("stats", stats.to_dict())
        
        return metric_value
    
    def optimize(
        self,
        callback: Optional[Callable[[int, Dict[str, Any], float], None]] = None,
    ) -> TuningResult:
        start_time = time.time()
        
        self._study = optuna.create_study(
            study_name=self.study_name,
            direction=self.direction,
            sampler=self.sampler,
            pruner=self.pruner,
            storage=self.storage,
            load_if_exists=True,
        )
        
        def _trial_callback(study, trial):
            if callback is not None:
                callback(trial.number, trial.params, trial.value)
        
        self._study.optimize(
            self._objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            callbacks=[_trial_callback] if callback else None,
            show_progress_bar=True,
        )
        
        duration = time.time() - start_time
        
        trial_results = []
        for trial in self._study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                trial_results.append({
                    "trial_number": trial.number,
                    "params": trial.params,
                    "value": trial.value,
                    "stats": trial.user_attrs.get("stats", {}),
                })
        
        result = TuningResult(
            best_params=self._study.best_params,
            best_value=self._study.best_value,
            metric=self.metric,
            n_trials=len(trial_results),
            study_name=self.study_name,
            duration=duration,
            trial_results=trial_results,
        )
        
        return result
    
    def optimize_with_simulator(
        self,
        simulator: AuctionSimulator,
        num_trials_per_param: int = 100,
        callback: Optional[Callable[[int, Dict[str, Any], float], None]] = None,
    ) -> TuningResult:
        def _objective_wrapper(trial: Trial) -> float:
            params = self._suggest_params(trial)
            self._apply_params_to_config(params)
            
            for strategy_name, strategy in simulator.bid_engine.exploration_engine.strategies.items():
                strategy.frequency_penalty_weight = params.get("frequency_penalty_weight", 1.0)
                strategy.budget_pace_weight = params.get("budget_pace_weight", 1.0)
                strategy.ctr_weight = params.get("ctr_weight", 1.0)
                strategy.cvr_weight = params.get("cvr_weight", 1.0)
                strategy.bid_multiplier = params.get("bid_base_multiplier", 1.0)
            
            simulator.reset()
            stats = simulator.run_simulation(num_auctions=num_trials_per_param)
            metric_value = self._extract_metric(stats)
            
            trial.set_user_attr("stats", stats.to_dict())
            
            return metric_value
        
        start_time = time.time()
        
        self._study = optuna.create_study(
            study_name=self.study_name,
            direction=self.direction,
            sampler=self.sampler,
            pruner=self.pruner,
        )
        
        def _trial_callback(study, trial):
            if callback is not None:
                callback(trial.number, trial.params, trial.value)
        
        self._study.optimize(
            _objective_wrapper,
            n_trials=self.n_trials,
            timeout=self.timeout,
            callbacks=[_trial_callback] if callback else None,
            show_progress_bar=True,
        )
        
        duration = time.time() - start_time
        
        trial_results = []
        for trial in self._study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                trial_results.append({
                    "trial_number": trial.number,
                    "params": trial.params,
                    "value": trial.value,
                    "stats": trial.user_attrs.get("stats", {}),
                })
        
        result = TuningResult(
            best_params=self._study.best_params,
            best_value=self._study.best_value,
            metric=self.metric,
            n_trials=len(trial_results),
            study_name=self.study_name,
            duration=duration,
            trial_results=trial_results,
        )
        
        return result
    
    def get_study_summary(self) -> Dict[str, Any]:
        if self._study is None:
            return {"status": "not_run"}
        
        return {
            "study_name": self._study.study_name,
            "best_params": self._study.best_params,
            "best_value": self._study.best_value,
            "n_trials": len(self._study.trials),
            "metric": self.metric,
            "direction": self.direction,
            "trials": [
                {
                    "number": t.number,
                    "params": t.params,
                    "value": t.value,
                    "state": t.state.name,
                }
                for t in self._study.trials
                if t.state == optuna.trial.TrialState.COMPLETE
            ],
        }
    
    def apply_best_params(self, result: Optional[TuningResult] = None):
        if result is None and self._study is None:
            raise ValueError("No tuning result available. Run optimize() first.")
        
        params = result.best_params if result else self._study.best_params
        self._apply_params_to_config(params)
    
    def generate_optimal_strategy(
        self,
        result: TuningResult,
        name: str = "optimal",
    ) -> Dict[str, Any]:
        params = result.best_params
        return {
            "name": name,
            "bid_multiplier": params.get("bid_base_multiplier", 1.0),
            "ctr_weight": params.get("ctr_weight", 1.0),
            "cvr_weight": params.get("cvr_weight", 1.0),
            "frequency_penalty_weight": params.get("frequency_penalty_weight", 1.0),
            "budget_pace_weight": params.get("budget_pace_weight", 1.0),
            "exploration_strategy": params.get("exploration_strategy", "ucb"),
            "exploration_epsilon": params.get("exploration_epsilon", 0.1),
            "ucb_c": params.get("ucb_c", 2.0),
            "pid_kp": params.get("pid_kp", 1.0),
            "pid_ki": params.get("pid_ki", 0.1),
            "pid_kd": params.get("pid_kd", 0.05),
        }
    
    def visualize_optimization_history(self, filepath: Optional[str] = None):
        if self._study is None:
            return None
        
        try:
            import matplotlib.pyplot as plt
            
            fig = optuna.visualization.plot_optimization_history(self._study)
            
            if filepath is not None:
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                    fig.write_html(f.name)
                    if filepath:
                        import shutil
                        shutil.move(f.name, filepath)
            
            return fig
        except Exception as e:
            print(f"Visualization error: {e}")
            return None
    
    def visualize_param_importances(self, filepath: Optional[str] = None):
        if self._study is None:
            return None
        
        try:
            fig = optuna.visualization.plot_param_importances(self._study)
            
            if filepath is not None:
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                    fig.write_html(f.name)
                    if filepath:
                        import shutil
                        shutil.move(f.name, filepath)
            
            return fig
        except Exception as e:
            print(f"Visualization error: {e}")
            return None
