import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
import json
import os
import logging

logger = logging.getLogger(__name__)


class PriceExperiment:
    def __init__(self, experiment_id, start_date, end_date, price,
                 base_price, units_sold, revenue, profit,
                 control_group_units=None, status='completed', notes=''):
        self.experiment_id = experiment_id
        self.start_date = start_date
        self.end_date = end_date
        self.price = price
        self.base_price = base_price
        self.units_sold = units_sold
        self.revenue = revenue
        self.profit = profit
        self.control_group_units = control_group_units
        self.status = status
        self.notes = notes

    def to_dict(self):
        return {
            'experiment_id': self.experiment_id,
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, datetime) else self.start_date,
            'end_date': self.end_date.isoformat() if isinstance(self.end_date, datetime) else self.end_date,
            'price': self.price,
            'base_price': self.base_price,
            'units_sold': self.units_sold,
            'revenue': self.revenue,
            'profit': self.profit,
            'control_group_units': self.control_group_units,
            'status': self.status,
            'notes': self.notes,
        }


class ElasticityCalibrator:
    def __init__(self, storage_path=None, default_elasticity=-1.5):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'price_experiments.json')
        self.storage_path = storage_path
        self.experiments = []
        self.default_elasticity = default_elasticity
        self._ensure_storage_dir()
        self._load_experiments()

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_experiments(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.experiments = [
                        PriceExperiment(
                            **{k: datetime.fromisoformat(v) if 'date' in k and isinstance(v, str) else v
                               for k, v in exp.items()}
                        ) for exp in data
                    ]
            except (json.JSONDecodeError, IOError):
                self.experiments = []

    def _save_experiments(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([exp.to_dict() for exp in self.experiments], f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Error saving experiments: {e}")

    def add_experiment(self, start_date, end_date, price, base_price, units_sold,
                       revenue=None, profit=None, control_group_units=None, notes=''):
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if revenue is None:
            revenue = price * units_sold
        if profit is None:
            profit = revenue * 0.3
        exp = PriceExperiment(
            experiment_id=exp_id,
            start_date=start_date,
            end_date=end_date,
            price=price,
            base_price=base_price,
            units_sold=units_sold,
            revenue=revenue,
            profit=profit,
            control_group_units=control_group_units,
            status='completed',
            notes=notes,
        )
        self.experiments.append(exp)
        self._save_experiments()
        return exp_id

    def get_recent_experiments(self, days=90):
        cutoff = datetime.now() - timedelta(days=days)
        return [
            exp for exp in self.experiments
            if (isinstance(exp.end_date, datetime) and exp.end_date >= cutoff)
            or (isinstance(exp.end_date, str) and datetime.fromisoformat(exp.end_date) >= cutoff)
        ]

    def calculate_point_elasticity(self, experiment):
        price_change_pct = (experiment.price - experiment.base_price) / experiment.base_price
        if experiment.control_group_units:
            baseline_units = experiment.control_group_units
        else:
            baseline_units = experiment.units_sold * (experiment.base_price / experiment.price)
        demand_change_pct = (experiment.units_sold - baseline_units) / baseline_units
        if price_change_pct == 0:
            return self.default_elasticity
        elasticity = demand_change_pct / price_change_pct
        return elasticity

    def calibrate_elasticity_linear(self, days=90):
        recent_exps = self.get_recent_experiments(days)
        if len(recent_exps) < 2:
            return {
                'elasticity': self.default_elasticity,
                'confidence': 'low',
                'sample_size': len(recent_exps),
                'method': 'default',
                'r_squared': None,
            }

        X = []
        y = []
        for exp in recent_exps:
            price_change_pct = (exp.price - exp.base_price) / exp.base_price
            baseline_units = exp.control_group_units if exp.control_group_units else exp.units_sold * (exp.base_price / exp.price)
            demand_change_pct = (exp.units_sold - baseline_units) / baseline_units
            X.append([price_change_pct])
            y.append(demand_change_pct)

        X = np.array(X)
        y = np.array(y)

        model = LinearRegression()
        model.fit(X, y)
        elasticity = model.coef_[0] if len(model.coef_) > 0 else self.default_elasticity
        r_squared = model.score(X, y)

        if r_squared > 0.7:
            confidence = 'high'
        elif r_squared > 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'elasticity': round(elasticity, 4),
            'confidence': confidence,
            'sample_size': len(recent_exps),
            'method': 'linear_regression',
            'r_squared': round(r_squared, 4),
            'intercept': round(model.intercept_, 4),
        }

    def calibrate_elasticity_weighted(self, days=90, decay_rate=0.95):
        recent_exps = self.get_recent_experiments(days)
        if len(recent_exps) < 2:
            return {
                'elasticity': self.default_elasticity,
                'confidence': 'low',
                'sample_size': len(recent_exps),
                'method': 'default',
            }

        elasticities = []
        weights = []
        now = datetime.now()
        for i, exp in enumerate(recent_exps):
            elasticity = self.calculate_point_elasticity(exp)
            days_ago = (now - (exp.end_date if isinstance(exp.end_date, datetime)
                          else datetime.fromisoformat(exp.end_date))).days
            weight = decay_rate ** days_ago
            elasticities.append(elasticity)
            weights.append(weight)

        weighted_elasticity = np.average(elasticities, weights=weights)
        variance = np.average((np.array(elasticities) - weighted_elasticity) ** 2, weights=weights)
        std = np.sqrt(variance)

        cv = std / abs(weighted_elasticity) if weighted_elasticity != 0 else float('inf')
        if cv < 0.2:
            confidence = 'high'
        elif cv < 0.5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'elasticity': round(weighted_elasticity, 4),
            'confidence': confidence,
            'sample_size': len(recent_exps),
            'method': 'weighted_average',
            'std_dev': round(std, 4),
            'cv': round(cv, 4),
        }

    def calibrate_elasticity_ridge(self, days=90, alpha=1.0):
        recent_exps = self.get_recent_experiments(days)
        if len(recent_exps) < 3:
            return self.calibrate_elasticity_linear(days)

        X = []
        y = []
        for exp in recent_exps:
            price_change_pct = (exp.price - exp.base_price) / exp.base_price
            baseline_units = exp.control_group_units if exp.control_group_units else exp.units_sold * (exp.base_price / exp.price)
            demand_change_pct = (exp.units_sold - baseline_units) / baseline_units
            X.append([price_change_pct])
            y.append(demand_change_pct)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = Ridge(alpha=alpha)
        model.fit(X_scaled, y)
        elasticity = model.coef_[0]
        r_squared = model.score(X_scaled, y)

        if r_squared > 0.7:
            confidence = 'high'
        elif r_squared > 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'elasticity': round(elasticity, 4),
            'confidence': confidence,
            'sample_size': len(recent_exps),
            'method': 'ridge_regression',
            'r_squared': round(r_squared, 4),
            'alpha': alpha,
        }

    def calibrate(self, days=90, method='auto'):
        recent_exps = self.get_recent_experiments(days)
        if len(recent_exps) < 2:
            return {
                'elasticity': self.default_elasticity,
                'confidence': 'low',
                'sample_size': len(recent_exps),
                'method': 'default',
                'note': '实验数据不足，使用默认弹性系数',
            }

        if method == 'auto':
            linear_result = self.calibrate_elasticity_linear(days)
            weighted_result = self.calibrate_elasticity_weighted(days)
            if linear_result.get('r_squared', 0) > 0.6:
                return linear_result
            return weighted_result
        elif method == 'linear':
            return self.calibrate_elasticity_linear(days)
        elif method == 'weighted':
            return self.calibrate_elasticity_weighted(days)
        elif method == 'ridge':
            return self.calibrate_elasticity_ridge(days)
        else:
            return self.calibrate_elasticity_linear(days)

    def get_elasticity_trend(self, window=7):
        if len(self.experiments) < 3:
            return pd.DataFrame()
        sorted_exps = sorted(self.experiments, key=lambda x: x.end_date)
        trend_data = []
        for i in range(len(sorted_exps)):
            start_idx = max(0, i - window + 1)
            window_exps = sorted_exps[start_idx:i + 1]
            if len(window_exps) >= 2:
                elasticities = [self.calculate_point_elasticity(exp) for exp in window_exps]
                avg_elasticity = np.mean(elasticities)
                trend_data.append({
                    'date': window_exps[-1].end_date,
                    'avg_elasticity': round(avg_elasticity, 4),
                    'experiment_count': len(window_exps),
                })
        return pd.DataFrame(trend_data)

    def delete_experiment(self, experiment_id):
        self.experiments = [exp for exp in self.experiments if exp.experiment_id != experiment_id]
        self._save_experiments()
        return True

    def get_stats(self):
        return {
            'total_experiments': len(self.experiments),
            'recent_90_days': len(self.get_recent_experiments(90)),
            'recent_30_days': len(self.get_recent_experiments(30)),
            'current_elasticity': self.calibrate()['elasticity'],
            'price_range': {
                'min': min(exp.price for exp in self.experiments) if self.experiments else None,
                'max': max(exp.price for exp in self.experiments) if self.experiments else None,
            },
        }
