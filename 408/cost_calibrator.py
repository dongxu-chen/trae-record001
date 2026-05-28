import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from db_connector import DBConnector


class CostModelCalibrator:
    def __init__(self):
        self.db = DBConnector()
        self._data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self._calibration_file = os.path.join(self._data_dir, 'cost_calibration.json')
        self._ensure_data_dir()
        self._calibration_data = self._load_calibration_data()

    def _ensure_data_dir(self):
        os.makedirs(self._data_dir, exist_ok=True)

    def _load_calibration_data(self):
        if os.path.exists(self._calibration_file):
            try:
                with open(self._calibration_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._default_calibration()
        return self._default_calibration()

    def _default_calibration(self):
        return {
            'version': '1.0',
            'last_calibrated': None,
            'total_samples': 0,
            'base_cost_multiplier': 1.0,
            'factor_weights': {
                'select_star': 20.0,
                'full_scan': 50.0,
                'distinct': 30.0,
                'order_by': 25.0,
                'group_by': 30.0,
                'join': 40.0,
                'subquery': 60.0,
                'or_condition': 25.0,
                'like_prefix': 35.0,
                'filesort': 70.0,
                'temporary': 80.0
            },
            'bias': 0.0,
            'accuracy_metrics': {
                'mae': 0.0,
                'rmse': 0.0,
                'mape': 0.0,
                'r_squared': 0.0
            },
            'history': []
        }

    def _save_calibration_data(self):
        with open(self._calibration_file, 'w', encoding='utf-8') as f:
            json.dump(self._calibration_data, f, ensure_ascii=False, indent=2, default=str)

    def _parse_query_time(self, qt):
        if qt is None:
            return 0.0
        if isinstance(qt, (int, float)):
            return float(qt)
        if isinstance(qt, timedelta):
            return qt.total_seconds()
        if isinstance(qt, str):
            try:
                parts = qt.split(':')
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                return float(qt)
            except:
                return 0.0
        return 0.0

    def collect_training_data(self, queries, cost_estimates):
        training_data = []
        for i, q in enumerate(queries):
            actual_time = self._parse_query_time(q.get('query_time', 0))
            if actual_time <= 0:
                continue
            sql = q.get('sql_text', '') or q.get('argument', '') or q.get('query', '')
            if i < len(cost_estimates):
                estimated = cost_estimates[i]
            else:
                estimated = self._estimate_cost_features(sql)
            training_data.append({
                'sql': sql,
                'features': estimated['features'],
                'estimated_cost': estimated['base_cost'],
                'actual_time': actual_time,
                'timestamp': datetime.now().isoformat()
            })
        return training_data

    def _estimate_cost_features(self, sql):
        from query_optimizer import QueryOptimizer
        opt = QueryOptimizer()
        result = opt.estimate_cost(sql)
        features = {}
        sql_upper = sql.upper()
        sql_lower = sql.lower()
        features['has_select_star'] = 1 if 'SELECT *' in sql_upper else 0
        features['has_distinct'] = 1 if 'DISTINCT' in sql_upper else 0
        features['has_order_by'] = 1 if 'ORDER BY' in sql_upper else 0
        features['has_group_by'] = 1 if 'GROUP BY' in sql_upper else 0
        features['join_count'] = sql_upper.count(' JOIN ')
        features['has_subquery'] = 1 if sql_lower.count('select') > 1 else 0
        features['or_count'] = sql_upper.count(' OR ')
        features['has_like_prefix'] = 1 if 'LIKE \'%' in sql or 'LIKE "%' in sql else 0
        return {
            'features': features,
            'base_cost': result.get('base_cost', 100)
        }

    def calibrate(self, training_data):
        if not training_data:
            return {'success': False, 'message': '没有训练数据'}
        X = []
        y = []
        estimates = []
        for sample in training_data:
            f = sample['features']
            features = [
                f.get('has_select_star', 0),
                f.get('has_distinct', 0),
                f.get('has_order_by', 0),
                f.get('has_group_by', 0),
                f.get('join_count', 0),
                f.get('has_subquery', 0),
                f.get('or_count', 0),
                f.get('has_like_prefix', 0)
            ]
            X.append(features)
            y.append(sample['actual_time'])
            estimates.append(sample['estimated_cost'])
        X = np.array(X)
        y = np.array(y)
        estimates = np.array(estimates)
        if len(y) > 1:
            mae = np.mean(np.abs(estimates - y))
            rmse = np.sqrt(np.mean((estimates - y) ** 2))
            mape = np.mean(np.abs((estimates - y) / (y + 1e-10))) * 100
            ss_res = np.sum((y - estimates) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / (ss_tot + 1e-10))
            try:
                if X.shape[0] > X.shape[1] and np.linalg.matrix_rank(X) == X.shape[1]:
                    weights = np.linalg.lstsq(X, y, rcond=None)[0]
                    self._calibration_data['factor_weights'] = {
                        'select_star': float(max(0, weights[0])),
                        'distinct': float(max(0, weights[1])),
                        'order_by': float(max(0, weights[2])),
                        'group_by': float(max(0, weights[3])),
                        'join': float(max(0, weights[4])),
                        'subquery': float(max(0, weights[5])),
                        'or_condition': float(max(0, weights[6])),
                        'like_prefix': float(max(0, weights[7]))
                    }
            except:
                pass
            self._calibration_data['total_samples'] = len(training_data)
            self._calibration_data['last_calibrated'] = datetime.now().isoformat()
            self._calibration_data['accuracy_metrics'] = {
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'r_squared': float(max(0, r_squared))
            }
            self._calibration_data['history'].append({
                'timestamp': datetime.now().isoformat(),
                'samples': len(training_data),
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape)
            })
            if len(self._calibration_data['history']) > 50:
                self._calibration_data['history'] = self._calibration_data['history'][-50:]
            self._save_calibration_data()
            return {
                'success': True,
                'samples': len(training_data),
                'metrics': self._calibration_data['accuracy_metrics']
            }
        return {'success': False, 'message': '样本数量不足'}

    def get_accuracy_report(self):
        metrics = self._calibration_data.get('accuracy_metrics', {})
        return {
            'success': True,
            'last_calibrated': self._calibration_data.get('last_calibrated'),
            'total_samples': self._calibration_data.get('total_samples', 0),
            'metrics': {
                'mae': round(metrics.get('mae', 0), 4),
                'rmse': round(metrics.get('rmse', 0), 4),
                'mape': round(metrics.get('mape', 0), 2),
                'r_squared': round(metrics.get('r_squared', 0), 4)
            },
            'factor_weights': self._calibration_data.get('factor_weights', {}),
            'history': self._calibration_data.get('history', [])
        }

    def compare_estimated_actual(self, sql_list, queries=None):
        from query_optimizer import QueryOptimizer
        opt = QueryOptimizer()
        results = []
        for i, sql in enumerate(sql_list):
            estimated = opt.estimate_cost(sql)
            actual_time = 0
            if queries and i < len(queries):
                actual_time = self._parse_query_time(queries[i].get('query_time', 0))
            estimated_cost = estimated.get('base_cost', 100)
            deviation = 0
            deviation_percent = 0
            if actual_time > 0:
                deviation = estimated_cost - actual_time
                deviation_percent = (deviation / actual_time) * 100
            results.append({
                'sql': sql,
                'estimated_cost': estimated_cost,
                'actual_time': actual_time,
                'deviation': deviation,
                'deviation_percent': deviation_percent,
                'rating': estimated.get('rating'),
                'cost_factors': estimated.get('cost_factors', [])
            })
        return results

    def analyze_deviation_patterns(self, comparison_results):
        patterns = {
            'under_estimated': [],
            'over_estimated': [],
            'accurate': [],
            'problematic_patterns': defaultdict(list)
        }
        for r in comparison_results:
            if r['actual_time'] > 0:
                if abs(r['deviation_percent']) < 20:
                    patterns['accurate'].append(r)
                elif r['deviation_percent'] < -20:
                    patterns['under_estimated'].append(r)
                else:
                    patterns['over_estimated'].append(r)
        for r in patterns['under_estimated']:
            for f in r.get('cost_factors', []):
                patterns['problematic_patterns'][f['factor']].append(r['sql'])
        summary = {
            'total': len(comparison_results),
            'accurate_count': len(patterns['accurate']),
            'under_count': len(patterns['under_estimated']),
            'over_count': len(patterns['over_estimated']),
            'accuracy_rate': len(patterns['accurate']) / max(1, len(comparison_results)) * 100,
            'problematic_patterns': dict(patterns['problematic_patterns'])
        }
        return summary

    def reset_calibration(self):
        self._calibration_data = self._default_calibration()
        self._save_calibration_data()
        return {'success': True, 'message': '校准数据已重置'}
