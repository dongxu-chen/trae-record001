import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os


class CompensationPolicyLearner:
    def __init__(self, policy_file='compensation_policy.json'):
        self.policy_file = policy_file
        self.current_policy = self._initialize_policy()
        self.policy_history = []
        self.learning_rate = 0.1
        self.adjustment_threshold = 0.1
        
        self.policy_change_log = []
        
    def _initialize_policy(self):
        return {
            'version': '1.0',
            'effective_date': datetime.now().strftime('%Y-%m-%d'),
            'reason_multipliers': {
                '天气原因': 0.8,
                '流量控制': 0.7,
                '机械故障': 1.5,
                '航空公司计划': 1.3,
                '机场保障': 1.1,
                '旅客原因': 0.5,
                '空中交通管制': 0.9,
                '油料供应': 1.2,
            },
            'delay_thresholds': [
                {'threshold': 240, 'ratio': 4.0, 'label': '4小时以上'},
                {'threshold': 180, 'ratio': 3.0, 'label': '3-4小时'},
                {'threshold': 120, 'ratio': 2.0, 'label': '2-3小时'},
                {'threshold': 60, 'ratio': 1.0, 'label': '1-2小时'},
                {'threshold': 30, 'ratio': 0.5, 'label': '30-60分钟'},
            ],
            'base_rate_adjustment': 1.0,
            'seasonal_adjustments': {
                '1': 1.1, '2': 1.1, '7': 1.2, '8': 1.2,
                '3': 1.0, '4': 1.0, '5': 1.0, '6': 1.0,
                '9': 1.0, '10': 1.0, '11': 1.0, '12': 1.0
            },
            'special_rules': {
                'minimum_compensation': 100,
                'maximum_compensation': 2000,
                'no_compensation_minutes': 30,
                'force_compensation_minutes': 240
            }
        }
    
    def adjust_reason_multipliers(self, base_multipliers):
        adjusted = {}
        for reason, base_value in base_multipliers.items():
            policy_value = self.current_policy['reason_multipliers'].get(reason, base_value)
            adjusted[reason] = policy_value
        return adjusted
    
    def adjust_delay_thresholds(self, base_thresholds):
        policy_thresholds = self.current_policy['delay_thresholds']
        result = []
        for pt in policy_thresholds:
            result.append((pt['threshold'], pt['ratio']))
        return result
    
    def adjust_base_rate(self, base_rate, month=None):
        adjusted_rate = base_rate * self.current_policy['base_rate_adjustment']
        
        if month:
            season_factor = self.current_policy['seasonal_adjustments'].get(str(month), 1.0)
            adjusted_rate *= season_factor
        
        return adjusted_rate
    
    def apply_final_adjustment(self, comp, delay_minutes, delay_reason):
        rules = self.current_policy['special_rules']
        
        if delay_minutes >= rules['force_compensation_minutes']:
            comp = max(comp, rules['minimum_compensation'] * 2)
        
        comp = max(comp, rules.get('minimum_compensation', 0) if delay_minutes >= 60 else 0)
        comp = min(comp, rules.get('maximum_compensation', float('inf')))
        
        return comp
    
    def learn_from_feedback(self, feedback_data: pd.DataFrame):
        if len(feedback_data) < 10:
            return "数据量不足，无法进行学习"
        
        analysis = self._analyze_feedback(feedback_data)
        adjustments = self._generate_adjustments(analysis)
        
        if adjustments:
            self._apply_adjustments(adjustments)
            self._log_policy_change(adjustments, analysis)
            return f"已完成政策更新，共调整 {len(adjustments)} 项参数"
        
        return "无需调整，当前政策已最优"
    
    def _analyze_feedback(self, feedback_data: pd.DataFrame):
        analysis = {}
        
        for reason in self.current_policy['reason_multipliers'].keys():
            reason_data = feedback_data[feedback_data['delay_reason'] == reason]
            if len(reason_data) >= 5:
                avg_expected = reason_data['expected_compensation'].mean()
                avg_actual = reason_data['compensation'].mean()
                diff_ratio = (avg_expected - avg_actual) / max(avg_actual, 1)
                analysis[reason] = {
                    'sample_count': len(reason_data),
                    'diff_ratio': diff_ratio,
                    'needs_adjustment': abs(diff_ratio) > self.adjustment_threshold
                }
        
        delay_bins = [(0, 60), (60, 120), (120, 180), (180, 240), (240, float('inf'))]
        for bin_min, bin_max in delay_bins:
            bin_data = feedback_data[
                (feedback_data['delay_minutes'] >= bin_min) & 
                (feedback_data['delay_minutes'] < bin_max)
            ]
            if len(bin_data) >= 5:
                avg_expected = bin_data['expected_compensation'].mean()
                avg_actual = bin_data['compensation'].mean()
                diff_ratio = (avg_expected - avg_actual) / max(avg_actual, 1)
                analysis[f'delay_{bin_min}_{bin_max}'] = {
                    'sample_count': len(bin_data),
                    'diff_ratio': diff_ratio,
                    'needs_adjustment': abs(diff_ratio) > self.adjustment_threshold
                }
        
        return analysis
    
    def _generate_adjustments(self, analysis: Dict) -> List[Dict]:
        adjustments = []
        
        for reason, result in analysis.items():
            if result.get('needs_adjustment') and reason in self.current_policy['reason_multipliers']:
                current_value = self.current_policy['reason_multipliers'][reason]
                adjustment = result['diff_ratio'] * self.learning_rate
                new_value = max(0.3, min(2.0, current_value * (1 + adjustment)))
                
                adjustments.append({
                    'type': 'reason_multiplier',
                    'target': reason,
                    'old_value': current_value,
                    'new_value': round(new_value, 2),
                    'rationale': f"样本量: {result['sample_count']}, 偏差率: {result['diff_ratio']:.1%}"
                })
        
        return adjustments
    
    def _apply_adjustments(self, adjustments: List[Dict]):
        self.policy_history.append(self.current_policy.copy())
        
        for adj in adjustments:
            if adj['type'] == 'reason_multiplier':
                self.current_policy['reason_multipliers'][adj['target']] = adj['new_value']
        
        self.current_policy['version'] = f"{float(self.current_policy['version']) + 0.1:.1f}"
        self.current_policy['effective_date'] = datetime.now().strftime('%Y-%m-%d')
        
        self.save_policy()
    
    def _log_policy_change(self, adjustments, analysis):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'old_version': self.policy_history[-1]['version'] if self.policy_history else 'N/A',
            'new_version': self.current_policy['version'],
            'adjustments': adjustments,
            'analysis_summary': {k: v for k, v in analysis.items() if v.get('needs_adjustment')}
        }
        self.policy_change_log.append(log_entry)
    
    def simulate_policy_impact(self, test_data: pd.DataFrame) -> Dict:
        old_comp_sum = test_data['compensation'].sum()
        
        new_comp = []
        for _, row in test_data.iterrows():
            if row['delay_minutes'] >= 30:
                from data_generator import calculate_compensation
                from data_generator import AIRLINES
                base_rate = AIRLINES.get(row['airline'], {'compensation_base': 250})['compensation_base']
                new_c = calculate_compensation(
                    row['delay_minutes'], base_rate, row['delay_reason'], self
                )
                new_comp.append(new_c)
            else:
                new_comp.append(0)
        
        new_comp_sum = sum(new_comp)
        
        return {
            'old_total': old_comp_sum,
            'new_total': new_comp_sum,
            'change_percent': ((new_comp_sum - old_comp_sum) / old_comp_sum * 100) if old_comp_sum > 0 else 0,
            'sample_count': len(test_data)
        }
    
    def get_policy_report(self) -> Dict:
        return {
            'version': self.current_policy['version'],
            'effective_date': self.current_policy['effective_date'],
            'reason_multipliers': self.current_policy['reason_multipliers'],
            'delay_thresholds': self.current_policy['delay_thresholds'],
            'change_history_count': len(self.policy_history),
            'recent_changes': self.policy_change_log[-5:] if self.policy_change_log else []
        }
    
    def reset_to_default(self):
        old_policy = self.current_policy.copy()
        self.policy_history.append(old_policy)
        self.current_policy = self._initialize_policy()
        self.save_policy()
        return "已重置为默认政策"
    
    def save_policy(self):
        with open(self.policy_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_policy, f, ensure_ascii=False, indent=2)
    
    def load_policy(self):
        if os.path.exists(self.policy_file):
            with open(self.policy_file, 'r', encoding='utf-8') as f:
                self.current_policy = json.load(f)
            return True
        return False


def generate_mock_feedback_data(n_samples=200):
    np.random.seed(42)
    
    from data_generator import generate_flight_data, AIRLINES
    base_data = generate_flight_data(n_samples=n_samples)
    
    feedback = base_data.copy()
    
    feedback['expected_compensation'] = feedback['compensation'] * (
        0.8 + np.random.random(n_samples) * 0.4
    )
    
    feedback.loc[feedback['delay_reason'] == '机械故障', 'expected_compensation'] *= 1.2
    feedback.loc[feedback['delay_reason'] == '天气原因', 'expected_compensation'] *= 0.9
    
    feedback['customer_feedback'] = np.random.choice(
        ['满意', '基本满意', '不满意'],
        n_samples,
        p=[0.3, 0.4, 0.3]
    )
    
    return feedback


if __name__ == '__main__':
    learner = CompensationPolicyLearner()
    
    print("当前政策:")
    print(json.dumps(learner.get_policy_report(), ensure_ascii=False, indent=2))
    
    print("\n生成模拟反馈数据...")
    feedback = generate_mock_feedback_data(500)
    
    print("\n政策学习中...")
    result = learner.learn_from_feedback(feedback)
    print(result)
    
    print("\n更新后的政策:")
    print(json.dumps(learner.get_policy_report(), ensure_ascii=False, indent=2))
    
    impact = learner.simulate_policy_impact(feedback)
    print(f"\n政策影响模拟: {impact}")
