import json
import os
import sys
import time
import random
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    from scipy import stats
    STATS_AVAILABLE = True
except ImportError:
    STATS_AVAILABLE = False
    print("Warning: scipy not available. Some statistical tests will be limited.")

from common.logger import get_logger
from common.utils import (
    load_config,
    to_json_safe,
    parse_json_safe
)
from redis.cache_manager import RedisCacheManager

logger = get_logger("ABTestManager")


class VariantType(Enum):
    CONTROL = "control"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class ExperimentVariant:
    variant_id: str
    name: str
    description: str = ""
    traffic_split: float = 0.5
    configuration: Dict[str, Any] = field(default_factory=dict)
    is_control: bool = False


@dataclass
class Experiment:
    experiment_id: str
    name: str
    description: str = ""
    variants: List[ExperimentVariant] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    target_metrics: List[str] = field(default_factory=list)
    min_sample_size: int = 100
    confidence_level: float = 0.95
    randomization_key: str = "user_id"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["variants"] = [asdict(v) for v in self.variants]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Experiment":
        variants = [ExperimentVariant(**v) for v in data["variants"]]
        status = ExperimentStatus(data["status"])
        return cls(
            experiment_id=data["experiment_id"],
            name=data["name"],
            description=data.get("description", ""),
            variants=variants,
            status=status,
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            target_metrics=data.get("target_metrics", []),
            min_sample_size=data.get("min_sample_size", 100),
            confidence_level=data.get("confidence_level", 0.95),
            randomization_key=data.get("randomization_key", "user_id"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExperimentEvent:
    experiment_id: str
    variant_id: str
    user_id: str
    event_type: str
    event_name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ABTestManager:
    def __init__(self, cache_manager: RedisCacheManager):
        self.config = load_config()
        self.ab_config = self.config["ab_testing"]
        self.cache = cache_manager
        
        self.experiments_path = self.ab_config["experiments_path"]
        self.results_path = self.ab_config["results_path"]
        self.default_traffic_split = self.ab_config["traffic_split"]
        self.min_sample_size = self.ab_config["min_sample_size"]
        self.confidence_level = self.ab_config["confidence_level"]
        
        self._experiment_prefix = "ab:experiment:"
        self._assignment_prefix = "ab:assignment:"
        self._event_prefix = "ab:event:"
        self._results_prefix = "ab:results:"
        
        self.experiments: Dict[str, Experiment] = {}
        self._load_experiments()
    
    def _load_experiments(self):
        os.makedirs(os.path.dirname(self.experiments_path), exist_ok=True)
        
        if os.path.exists(self.experiments_path):
            try:
                with open(self.experiments_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for exp_data in data:
                    exp = Experiment.from_dict(exp_data)
                    self.experiments[exp.experiment_id] = exp
                
                logger.info(f"Loaded {len(self.experiments)} experiments")
            except Exception as e:
                logger.error(f"Error loading experiments: {e}")
    
    def _save_experiments(self):
        os.makedirs(os.path.dirname(self.experiments_path), exist_ok=True)
        
        data = [exp.to_dict() for exp in self.experiments.values()]
        with open(self.experiments_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.experiments)} experiments")
    
    def create_experiment(self, 
                         name: str,
                         variants: List[Dict],
                         description: str = "",
                         target_metrics: Optional[List[str]] = None,
                         min_sample_size: Optional[int] = None,
                         confidence_level: Optional[float] = None) -> Experiment:
        exp_id = f"exp_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        experiment_variants = []
        has_control = False
        
        for i, var_data in enumerate(variants):
            is_control = var_data.get("is_control", i == 0)
            if is_control:
                has_control = True
            
            variant = ExperimentVariant(
                variant_id=var_data.get("variant_id", f"var_{i}"),
                name=var_data.get("name", f"Variant {i}"),
                description=var_data.get("description", ""),
                traffic_split=var_data.get("traffic_split", 1.0 / len(variants)),
                configuration=var_data.get("configuration", {}),
                is_control=is_control
            )
            experiment_variants.append(variant)
        
        if not has_control and experiment_variants:
            experiment_variants[0].is_control = True
        
        total_split = sum(v.traffic_split for v in experiment_variants)
        if abs(total_split - 1.0) > 0.01:
            logger.warning(f"Traffic splits sum to {total_split}, normalizing to 1.0")
            for v in experiment_variants:
                v.traffic_split = v.traffic_split / total_split
        
        experiment = Experiment(
            experiment_id=exp_id,
            name=name,
            description=description,
            variants=experiment_variants,
            status=ExperimentStatus.DRAFT,
            target_metrics=target_metrics or self.ab_config["metrics"],
            min_sample_size=min_sample_size or self.min_sample_size,
            confidence_level=confidence_level or self.confidence_level
        )
        
        self.experiments[exp_id] = experiment
        self._save_experiments()
        
        exp_key = f"{self._experiment_prefix}{exp_id}"
        self.cache._execute("set", exp_key, to_json_safe(experiment.to_dict()))
        
        logger.info(f"Created experiment: {name} ({exp_id}) with {len(variants)} variants")
        return experiment
    
    def start_experiment(self, experiment_id: str, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> bool:
        if experiment_id not in self.experiments:
            logger.error(f"Experiment not found: {experiment_id}")
            return False
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.RUNNING
        exp.start_date = start_date or datetime.now().isoformat()
        exp.end_date = end_date
        exp.updated_at = datetime.now().isoformat()
        
        self._save_experiments()
        
        exp_key = f"{self._experiment_prefix}{experiment_id}"
        self.cache._execute("set", exp_key, to_json_safe(exp.to_dict()))
        
        logger.info(f"Started experiment: {exp.name} ({experiment_id})")
        return True
    
    def pause_experiment(self, experiment_id: str) -> bool:
        if experiment_id not in self.experiments:
            return False
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.PAUSED
        exp.updated_at = datetime.now().isoformat()
        
        self._save_experiments()
        logger.info(f"Paused experiment: {exp.name} ({experiment_id})")
        return True
    
    def stop_experiment(self, experiment_id: str) -> bool:
        if experiment_id not in self.experiments:
            return False
        
        exp = self.experiments[experiment_id]
        exp.status = ExperimentStatus.COMPLETED
        exp.end_date = datetime.now().isoformat()
        exp.updated_at = datetime.now().isoformat()
        
        self._save_experiments()
        logger.info(f"Stopped experiment: {exp.name} ({experiment_id})")
        return True
    
    def assign_variant(self, experiment_id: str, 
                      user_id: str,
                      force_variant: Optional[str] = None) -> Optional[str]:
        if experiment_id not in self.experiments:
            return None
        
        exp = self.experiments[experiment_id]
        
        if exp.status != ExperimentStatus.RUNNING:
            logger.warning(f"Experiment {experiment_id} is not running")
            return None
        
        assignment_key = f"{self._assignment_prefix}{experiment_id}:{user_id}"
        existing = self.cache._execute("get", assignment_key)
        
        if existing and not force_variant:
            return existing
        
        if force_variant:
            variant_id = force_variant
        else:
            variant_id = self._deterministic_assignment(exp, user_id)
        
        self.cache._execute("set", assignment_key, variant_id)
        
        self._record_event(ExperimentEvent(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            event_type="assignment",
            event_name="assigned_to_variant"
        ))
        
        logger.debug(f"Assigned user {user_id} to variant {variant_id} in experiment {experiment_id}")
        return variant_id
    
    def _deterministic_assignment(self, exp: Experiment, user_id: str) -> str:
        hash_input = f"{exp.experiment_id}:{user_id}".encode("utf-8")
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        normalized = hash_value / 2**128
        
        cumulative = 0.0
        for variant in exp.variants:
            cumulative += variant.traffic_split
            if normalized < cumulative:
                return variant.variant_id
        
        return exp.variants[-1].variant_id
    
    def batch_assign_variants(self, experiment_id: str, 
                             user_ids: List[str]) -> Dict[str, str]:
        assignments = {}
        for user_id in user_ids:
            variant = self.assign_variant(experiment_id, user_id)
            if variant:
                assignments[user_id] = variant
        return assignments
    
    def get_assignment(self, experiment_id: str, user_id: str) -> Optional[str]:
        assignment_key = f"{self._assignment_prefix}{experiment_id}:{user_id}"
        return self.cache._execute("get", assignment_key)
    
    def track_event(self, experiment_id: str,
                   user_id: str,
                   event_name: str,
                   properties: Optional[Dict] = None) -> bool:
        if experiment_id not in self.experiments:
            return False
        
        variant_id = self.get_assignment(experiment_id, user_id)
        if not variant_id:
            logger.warning(f"No assignment found for user {user_id} in experiment {experiment_id}")
            return False
        
        event = ExperimentEvent(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            event_type="metric",
            event_name=event_name,
            properties=properties or {}
        )
        
        self._record_event(event)
        logger.debug(f"Tracked event {event_name} for user {user_id} in variant {variant_id}")
        return True
    
    def _record_event(self, event: ExperimentEvent):
        event_key = f"{self._event_prefix}{event.experiment_id}:{int(time.time()*1000)}"
        self.cache._execute("set", event_key, to_json_safe(asdict(event)))
        
        results_key = f"{self._results_prefix}{event.experiment_id}:{event.variant_id}"
        metric_key = f"{event.event_name}"
        
        self.cache._execute("hincrby", results_key, metric_key, 1)
        self.cache._execute("hincrby", results_key, "total_events", 1)
        
        users_key = f"{results_key}:users"
        self.cache._execute("sadd", users_key, event.user_id)
    
    def get_experiment_results(self, experiment_id: str) -> Dict:
        if experiment_id not in self.experiments:
            return {"error": "Experiment not found"}
        
        exp = self.experiments[experiment_id]
        results = {
            "experiment_id": experiment_id,
            "experiment_name": exp.name,
            "status": exp.status.value,
            "variants": {},
            "metrics_summary": {},
            "statistical_tests": {}
        }
        
        for variant in exp.variants:
            results_key = f"{self._results_prefix}{experiment_id}:{variant.variant_id}"
            users_key = f"{results_key}:users"
            
            metric_data = self.cache._execute("hgetall", results_key)
            users = self.cache._execute("smembers", users_key)
            
            variant_results = {
                "variant_id": variant.variant_id,
                "variant_name": variant.name,
                "is_control": variant.is_control,
                "traffic_split": variant.traffic_split,
                "user_count": len(users),
                "metrics": {}
            }
            
            for metric, count in metric_data.items():
                if metric != "total_events":
                    try:
                        variant_results["metrics"][metric] = int(count)
                    except (ValueError, TypeError):
                        variant_results["metrics"][metric] = count
            
            for metric in exp.target_metrics:
                count = variant_results["metrics"].get(metric, 0)
                user_count = variant_results["user_count"]
                variant_results["metrics"][f"{metric}_rate"] = (
                    count / user_count if user_count > 0 else 0
                )
            
            results["variants"][variant.variant_id] = variant_results
        
        results["statistical_tests"] = self._run_statistical_tests(exp, results)
        
        control_variant = next((v for v in exp.variants if v.is_control), None)
        if control_variant:
            for variant in exp.variants:
                if variant.is_control:
                    continue
                
                control_results = results["variants"][control_variant.variant_id]
                test_results = results["variants"][variant.variant_id]
                
                uplifts = {}
                for metric in exp.target_metrics:
                    control_rate = control_results["metrics"].get(f"{metric}_rate", 0)
                    test_rate = test_results["metrics"].get(f"{metric}_rate", 0)
                    
                    if control_rate > 0:
                        uplift = ((test_rate - control_rate) / control_rate) * 100
                    else:
                        uplift = 100 if test_rate > 0 else 0
                    
                    uplifts[metric] = round(uplift, 2)
                
                results["variants"][variant.variant_id]["uplift_vs_control"] = uplifts
        
        return results
    
    def _run_statistical_tests(self, exp: Experiment, results: Dict) -> Dict:
        if not STATS_AVAILABLE:
            return {"note": "scipy not available, statistical tests skipped"}
        
        tests = {}
        control_variant = next((v for v in exp.variants if v.is_control), None)
        
        if not control_variant:
            return {"note": "No control variant defined"}
        
        control_results = results["variants"][control_variant.variant_id]
        
        for variant in exp.variants:
            if variant.is_control:
                continue
            
            test_results = results["variants"][variant.variant_id]
            variant_tests = {}
            
            for metric in exp.target_metrics:
                control_conversions = control_results["metrics"].get(metric, 0)
                control_total = control_results["user_count"]
                test_conversions = test_results["metrics"].get(metric, 0)
                test_total = test_results["user_count"]
                
                if control_total > 0 and test_total > 0:
                    try:
                        contingency = [
                            [control_conversions, control_total - control_conversions],
                            [test_conversions, test_total - test_conversions]
                        ]
                        
                        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
                        
                        control_rate = control_conversions / control_total
                        test_rate = test_conversions / test_total
                        
                        se = ((control_rate * (1 - control_rate) / control_total) +
                              (test_rate * (1 - test_rate) / test_total)) ** 0.5
                        
                        z_score = (test_rate - control_rate) / se if se > 0 else 0
                        
                        ci_low = (test_rate - control_rate) - 1.96 * se
                        ci_high = (test_rate - control_rate) + 1.96 * se
                        
                        is_significant = p_value < (1 - self.confidence_level)
                        
                        variant_tests[metric] = {
                            "chi_square": chi2,
                            "p_value": p_value,
                            "z_score": z_score,
                            "confidence_interval": [ci_low, ci_high],
                            "is_significant": is_significant,
                            "control_rate": control_rate,
                            "test_rate": test_rate,
                            "absolute_difference": test_rate - control_rate,
                            "relative_lift": (test_rate - control_rate) / control_rate if control_rate > 0 else None
                        }
                    except Exception as e:
                        variant_tests[metric] = {"error": str(e)}
            
            tests[variant.variant_id] = variant_tests
        
        return tests
    
    def get_winning_variant(self, experiment_id: str, 
                           primary_metric: str) -> Dict:
        results = self.get_experiment_results(experiment_id)
        if "error" in results:
            return results
        
        exp = self.experiments[experiment_id]
        control_variant = next((v for v in exp.variants if v.is_control), None)
        
        if not control_variant:
            return {"error": "No control variant"}
        
        best_variant = None
        best_lift = float("-inf")
        best_p_value = 1.0
        
        for variant_id, variant_data in results["variants"].items():
            if variant_id == control_variant.variant_id:
                continue
            
            stat_tests = results["statistical_tests"].get(variant_id, {})
            metric_test = stat_tests.get(primary_metric, {})
            
            lift = metric_test.get("relative_lift", 0) or 0
            p_value = metric_test.get("p_value", 1.0)
            is_significant = metric_test.get("is_significant", False)
            
            sample_size = variant_data["user_count"]
            if sample_size < exp.min_sample_size:
                continue
            
            if is_significant and lift > best_lift:
                best_variant = variant_id
                best_lift = lift
                best_p_value = p_value
        
        if best_variant:
            return {
                "has_winner": True,
                "winning_variant": best_variant,
                "winning_variant_name": results["variants"][best_variant]["variant_name"],
                "primary_metric": primary_metric,
                "relative_lift": best_lift,
                "p_value": best_p_value,
                "confidence_level": self.confidence_level,
                "can_stop_experiment": True
            }
        else:
            return {
                "has_winner": False,
                "recommendation": "Continue experiment",
                "details": "No statistically significant winner found yet"
            }
    
    def list_experiments(self, status: Optional[ExperimentStatus] = None) -> List[Dict]:
        experiments = []
        
        for exp in self.experiments.values():
            if status and exp.status != status:
                continue
            
            experiments.append({
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "description": exp.description,
                "status": exp.status.value,
                "num_variants": len(exp.variants),
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "created_at": exp.created_at
            })
        
        experiments.sort(key=lambda x: x["created_at"], reverse=True)
        return experiments
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self.experiments.get(experiment_id)
    
    def export_results(self, experiment_id: str, output_path: Optional[str] = None) -> str:
        if not output_path:
            output_path = os.path.join(
                self.results_path,
                f"{experiment_id}_results_{datetime.now().strftime('%Y%m%d')}.json"
            )
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        results = self.get_experiment_results(experiment_id)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported results for experiment {experiment_id} to {output_path}")
        return output_path


def main():
    cache = RedisCacheManager(use_redis=False)
    manager = ABTestManager(cache)
    
    print("=" * 60)
    print("A/B Test Manager")
    print("=" * 60)
    
    print("\n1. Create new experiment")
    print("2. List experiments")
    print("3. Start experiment")
    print("4. Assign variant to users")
    print("5. Track events")
    print("6. View experiment results")
    print("7. Find winning variant")
    print("8. Export results")
    
    choice = input("\nEnter your choice (1-8): ").strip()
    
    if choice == "1":
        name = input("Experiment name: ").strip()
        description = input("Description (optional): ").strip()
        
        num_variants = int(input("Number of variants (including control): ") or "2")
        
        variants = []
        for i in range(num_variants):
            print(f"\nVariant {i}:")
            var_name = input(f"  Name (default: {'Control' if i==0 else 'Variant '+str(i)}): ").strip()
            if not var_name:
                var_name = "Control" if i == 0 else f"Variant {i}"
            
            traffic_split = float(input(f"  Traffic split (0-1, default: {1.0/num_variants:.2f}): ") or f"{1.0/num_variants}")
            is_control = i == 0
            
            if i == 0:
                control_choice = input("  Is control variant? (y/n, default: y): ").strip().lower()
                is_control = control_choice != "n"
            
            variants.append({
                "name": var_name,
                "traffic_split": traffic_split,
                "is_control": is_control
            })
        
        metrics = input("Target metrics (comma-separated, default: churn_rate,conversion_rate): ").strip()
        if not metrics:
            metrics = "churn_rate,conversion_rate"
        target_metrics = [m.strip() for m in metrics.split(",")]
        
        exp = manager.create_experiment(
            name=name,
            variants=variants,
            description=description,
            target_metrics=target_metrics
        )
        
        print(f"\nCreated experiment: {exp.name} ({exp.experiment_id})")
        print(f"Variants:")
        for v in exp.variants:
            print(f"  - {v.name} (id={v.variant_id}, split={v.traffic_split:.2%}, control={v.is_control})")
        
        start = input("\nStart experiment now? (y/n): ").strip().lower()
        if start == "y":
            manager.start_experiment(exp.experiment_id)
            print(f"Experiment started!")
    
    elif choice == "2":
        status_filter = input("Filter by status (draft/running/paused/completed/all, default: all): ").strip().lower()
        status_map = {
            "draft": ExperimentStatus.DRAFT,
            "running": ExperimentStatus.RUNNING,
            "paused": ExperimentStatus.PAUSED,
            "completed": ExperimentStatus.COMPLETED
        }
        
        status = status_map.get(status_filter) if status_filter != "all" else None
        experiments = manager.list_experiments(status=status)
        
        print(f"\nExperiments ({len(experiments)} total):")
        print("-" * 60)
        for exp in experiments:
            print(f"  {exp['name']:30s} [{exp['status']:12s}] "
                  f"variants={exp['num_variants']} id={exp['experiment_id']}")
    
    elif choice == "3":
        experiments = manager.list_experiments(status=ExperimentStatus.DRAFT)
        if not experiments:
            experiments = manager.list_experiments()
        
        print("\nAvailable experiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} [{exp['status']}] (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        manager.start_experiment(exp_id)
        print(f"Experiment started!")
    
    elif choice == "4":
        experiments = manager.list_experiments(status=ExperimentStatus.RUNNING)
        if not experiments:
            print("No running experiments")
            return
        
        print("\nRunning experiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        num_users = int(input("Number of users to assign: ") or "100")
        
        import random
        assignments = {}
        for i in range(num_users):
            user_id = f"test_user_{i:04d}"
            variant = manager.assign_variant(exp_id, user_id)
            assignments[variant] = assignments.get(variant, 0) + 1
        
        print(f"\nAssignment distribution:")
        for variant, count in sorted(assignments.items()):
            print(f"  {variant}: {count} ({count/num_users:.1%})")
    
    elif choice == "5":
        experiments = manager.list_experiments(status=ExperimentStatus.RUNNING)
        if not experiments:
            print("No running experiments")
            return
        
        print("\nRunning experiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        event_name = input("Event name (e.g., churn_rate, conversion_rate): ").strip() or "conversion_rate"
        num_events = int(input("Number of events to simulate: ") or "50")
        
        for i in range(num_events):
            user_id = f"test_user_{random.randint(0, 99):04d}"
            manager.track_event(exp_id, user_id, event_name)
        
        print(f"Tracked {num_events} events")
    
    elif choice == "6":
        experiments = manager.list_experiments()
        if not experiments:
            print("No experiments")
            return
        
        print("\nExperiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} [{exp['status']}] (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        results = manager.get_experiment_results(exp_id)
        
        print("\n" + "=" * 60)
        print(f"Results for: {results['experiment_name']}")
        print(f"Status: {results['status']}")
        print("-" * 60)
        
        for variant_id, variant_data in results["variants"].items():
            print(f"\nVariant: {variant_data['variant_name']} (id={variant_id})")
            print(f"  Users: {variant_data['user_count']}")
            print(f"  Is Control: {variant_data['is_control']}")
            print(f"  Traffic Split: {variant_data['traffic_split']:.1%}")
            print(f"  Metrics:")
            for metric, value in sorted(variant_data["metrics"].items()):
                if isinstance(value, float):
                    print(f"    {metric}: {value:.4f}")
                else:
                    print(f"    {metric}: {value}")
            
            if "uplift_vs_control" in variant_data:
                print(f"  Uplift vs Control:")
                for metric, uplift in variant_data["uplift_vs_control"].items():
                    print(f"    {metric}: {uplift:+.2f}%")
        
        if "statistical_tests" in results and "note" not in results["statistical_tests"]:
            print(f"\nStatistical Tests:")
            for variant_id, tests in results["statistical_tests"].items():
                if not tests or "error" in tests:
                    continue
                print(f"  Variant {variant_id}:")
                for metric, test_data in tests.items():
                    if isinstance(test_data, dict) and "p_value" in test_data:
                        sig = "*" if test_data.get("is_significant", False) else ""
                        print(f"    {metric}: p={test_data['p_value']:.4f} "
                              f"lift={test_data.get('relative_lift', 0)*100:+.1f}%{sig}")
        print("=" * 60)
    
    elif choice == "7":
        experiments = manager.list_experiments()
        if not experiments:
            print("No experiments")
            return
        
        print("\nExperiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} [{exp['status']}] (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        exp = manager.get_experiment(exp_id)
        if exp:
            print(f"\nAvailable metrics: {', '.join(exp.target_metrics)}")
        
        primary_metric = input("Primary metric: ").strip() or "conversion_rate"
        
        winner = manager.get_winning_variant(exp_id, primary_metric)
        
        print("\n" + "=" * 60)
        if winner.get("has_winner", False):
            print("WINNER FOUND!")
            print(f"  Winning Variant: {winner['winning_variant_name']} ({winner['winning_variant']})")
            print(f"  Primary Metric: {winner['primary_metric']}")
            print(f"  Relative Lift: {winner['relative_lift']*100:+.2f}%")
            print(f"  P-Value: {winner['p_value']:.4f}")
            print(f"  Confidence Level: {winner['confidence_level']:.0%}")
            print(f"  Recommendation: {'Stop experiment' if winner['can_stop_experiment'] else 'Continue'}")
        else:
            print("No winner yet")
            print(f"  {winner.get('recommendation', '')}")
            print(f"  Details: {winner.get('details', '')}")
        print("=" * 60)
    
    elif choice == "8":
        experiments = manager.list_experiments()
        if not experiments:
            print("No experiments")
            return
        
        print("\nExperiments:")
        for i, exp in enumerate(experiments):
            print(f"  {i+1}. {exp['name']} [{exp['status']}] (id={exp['experiment_id']})")
        
        idx = int(input("\nSelect experiment number: ")) - 1
        exp_id = experiments[idx]["experiment_id"]
        
        output_path = manager.export_results(exp_id)
        print(f"\nResults exported to: {output_path}")


if __name__ == "__main__":
    import time
    main()
