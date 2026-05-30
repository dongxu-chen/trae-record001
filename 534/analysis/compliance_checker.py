import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os


class ComplianceIssue:
    def __init__(self, issue_id, issue_type, severity, message, price_data,
                 timestamp=None, is_resolved=False):
        self.issue_id = issue_id
        self.issue_type = issue_type
        self.severity = severity
        self.message = message
        self.price_data = price_data
        self.timestamp = timestamp or datetime.now()
        self.is_resolved = is_resolved

    def to_dict(self):
        return {
            'issue_id': self.issue_id,
            'issue_type': self.issue_type,
            'severity': self.severity,
            'message': self.message,
            'price_data': self.price_data,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'is_resolved': self.is_resolved,
        }


class PricingComplianceChecker:
    def __init__(self, storage_path=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'compliance_issues.json')
        self.storage_path = storage_path
        self.issues = []
        self.rules = {
            'price_accuracy_window': 7,
            'max_markup_pct': 200,
            'min_comparison_days': 7,
            'min_valid_comparison_days': 3,
            'fake_original_price_threshold': 1.5,
            'price_frequency_threshold': 5,
            'price_frequency_days': 7,
            'predatory_pricing_threshold': 0.8,
            'bait_and_switch_threshold': 0.5,
        }
        self._ensure_storage_dir()
        self._load_issues()

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_issues(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.issues = [
                        ComplianceIssue(
                            **{k: datetime.fromisoformat(v) if 'timestamp' in k and isinstance(v, str) else v
                               for k, v in issue.items()}
                        ) for issue in data
                    ]
            except (json.JSONDecodeError, IOError):
                self.issues = []

    def _save_issues(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([i.to_dict() for i in self.issues], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving issues: {e}")

    def _generate_issue_id(self):
        return f"compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{np.random.randint(1000, 9999)}"

    def update_rules(self, **kwargs):
        self.rules.update(kwargs)

    def add_issue(self, issue_type, severity, message, price_data):
        issue = ComplianceIssue(
            issue_id=self._generate_issue_id(),
            issue_type=issue_type,
            severity=severity,
            message=message,
            price_data=price_data,
        )
        self.issues.append(issue)
        self._save_issues()
        return issue

    def check_fake_original_price(self, current_price, original_price, history_df=None):
        issues = []

        if original_price and original_price > 0:
            markup_ratio = original_price / current_price
            if markup_ratio >= self.rules['fake_original_price_threshold']:
                issues.append({
                    'type': 'fake_original_price',
                    'severity': 'high',
                    'message': f'原价虚高风险：原价¥{original_price}，现价¥{current_price}，折扣超过{int((self.rules["fake_original_price_threshold"]-1)*100)}%',
                    'data': {'current_price': current_price, 'original_price': original_price, 'ratio': round(markup_ratio, 2)},
                    'recommendation': '建议核实原价真实性，确保原价在过去7天内有真实销售记录',
                })

        if history_df is not None and len(history_df) >= self.rules['min_comparison_days']:
            recent_prices = history_df.sort_values('date').tail(30)['price'].values
            if len(recent_prices) >= self.rules['min_valid_comparison_days']:
                historical_high = np.max(recent_prices)
                if original_price and original_price > historical_high * 1.2:
                    issues.append({
                        'type': 'fake_original_price_history',
                        'severity': 'high',
                        'message': f'原价无历史依据：原价¥{original_price}高于过去30天最高价¥{historical_high:.2f}',
                        'data': {'original_price': original_price, 'historical_high': round(historical_high, 2)},
                        'recommendation': '建议使用历史真实成交价作为原价参考',
                    })

        return issues

    def check_price_frequency(self, history_df, current_price):
        issues = []
        if history_df is None or len(history_df) < 2:
            return issues

        recent = history_df[
            history_df['date'] >= datetime.now() - timedelta(days=self.rules['price_frequency_days'])
        ]
        price_changes = len(recent['price'].unique()) - 1

        if price_changes >= self.rules['price_frequency_threshold']:
            issues.append({
                'type': 'excessive_price_changes',
                'severity': 'medium',
                'message': f'价格变动过于频繁：{self.rules["price_frequency_days"]}天内变动{price_changes}次',
                'data': {'changes_count': price_changes, 'days': self.rules['price_frequency_days']},
                'recommendation': '建议保持价格相对稳定，避免消费者产生价格不信任感',
            })

        return issues

    def check_predatory_pricing(self, current_price, cost_price, competitor_prices=None):
        issues = []

        if cost_price and cost_price > 0:
            if current_price < cost_price * self.rules['predatory_pricing_threshold']:
                issues.append({
                    'type': 'predatory_pricing',
                    'severity': 'high',
                    'message': f'掠夺性定价风险：售价¥{current_price}低于成本¥{cost_price}的80%',
                    'data': {'current_price': current_price, 'cost_price': cost_price, 'ratio': round(current_price/cost_price, 2)},
                    'recommendation': '低价策略需谨慎，避免触发不正当竞争调查',
                })

        return issues

    def check_bait_and_switch(self, listed_price, actual_price, stock_status='in_stock'):
        issues = []

        if stock_status in ['out_of_stock', '预售'] and actual_price < listed_price * self.rules['bait_and_switch_threshold']:
            issues.append({
                'type': 'bait_pricing',
                'severity': 'high',
                'message': f'低价诱饵风险：商品{stock_status}时以低价吸引，但实际可用价格可能更高',
                'data': {'listed_price': listed_price, 'actual_price': actual_price, 'stock_status': stock_status},
                'recommendation': '缺货商品建议下架或标注真实价格，避免价格欺诈指控',
            })

        return issues

    def check_price_accuracy_period(self, history_df, current_price, days=7):
        issues = []
        if history_df is None or len(history_df) < days:
            return issues

        window_start = datetime.now() - timedelta(days=days)
        window_data = history_df[history_df['date'] >= window_start]

        if len(window_data) > 0:
            valid_prices = window_data[window_data['price'] > 0]
            if len(valid_prices) > 0:
                avg_price = valid_prices['price'].mean()
                if current_price > avg_price * 1.2:
                    issues.append({
                        'type': 'price_accuracy',
                        'severity': 'medium',
                        'message': f'价格准确性风险：当前价格¥{current_price}高于{days}天均价¥{avg_price:.2f}超过20%',
                        'data': {'current_price': current_price, 'avg_price': round(avg_price, 2), 'days': days},
                        'recommendation': '促销价格需确保原价在过去7天内有真实交易',
                    })

        return issues

    def check_drip_pricing(self, base_price, additional_fees=None):
        issues = []
        if additional_fees and len(additional_fees) > 0:
            total_fees = sum(additional_fees)
            fee_ratio = total_fees / base_price if base_price > 0 else 0

            if fee_ratio >= 0.2:
                issues.append({
                    'type': 'drip_pricing',
                    'severity': 'medium',
                    'message': f'附加费用过高：附加费用占基础价格的{int(fee_ratio*100)}%',
                    'data': {'base_price': base_price, 'total_fees': total_fees, 'fee_ratio': round(fee_ratio, 2)},
                    'recommendation': '建议在显著位置披露全部费用，避免隐性收费指控',
                })

        return issues

    def check_region_price_discrimination(self, price_data):
        issues = []
        if len(price_data) < 2:
            return issues

        prices = [d['price'] for d in price_data]
        max_price = max(prices)
        min_price = min(prices)
        price_diff_ratio = (max_price - min_price) / min_price if min_price > 0 else 0

        if price_diff_ratio >= 0.3:
            issues.append({
                'type': 'price_discrimination',
                'severity': 'low',
                'message': f'区域价差过大：最高¥{max_price} vs 最低¥{min_price}，相差{int(price_diff_ratio*100)}%',
                'data': {'max_price': max_price, 'min_price': min_price, 'diff_ratio': round(price_diff_ratio, 2)},
                'recommendation': '关注区域价格差异合理性，避免价格歧视指控',
            })

        return issues

    def full_compliance_check(self, current_price, original_price=None, cost_price=None,
                               history_df=None, competitor_prices=None, stock_status='in_stock',
                               additional_fees=None, region_prices=None):
        all_issues = []

        all_issues.extend(self.check_fake_original_price(current_price, original_price, history_df))
        all_issues.extend(self.check_price_frequency(history_df, current_price))
        all_issues.extend(self.check_predatory_pricing(current_price, cost_price, competitor_prices))
        all_issues.extend(self.check_bait_and_switch(current_price, current_price, stock_status))
        all_issues.extend(self.check_price_accuracy_period(history_df, current_price, self.rules['price_accuracy_window']))

        if additional_fees:
            all_issues.extend(self.check_drip_pricing(current_price, additional_fees))
        if region_prices:
            all_issues.extend(self.check_region_price_discrimination(region_prices))

        for issue in all_issues:
            self.add_issue(
                issue_type=issue['type'],
                severity=issue['severity'],
                message=issue['message'],
                price_data=issue['data'],
            )

        high_count = sum(1 for i in all_issues if i['severity'] == 'high')
        medium_count = sum(1 for i in all_issues if i['severity'] == 'medium')
        low_count = sum(1 for i in all_issues if i['severity'] == 'low')

        if high_count > 0:
            overall_risk = 'high'
            overall_status = '高风险'
        elif medium_count >= 2:
            overall_risk = 'medium'
            overall_status = '中风险'
        elif medium_count == 1 or low_count > 0:
            overall_risk = 'low'
            overall_status = '低风险'
        else:
            overall_risk = 'safe'
            overall_status = '合规'

        return {
            'overall_risk': overall_risk,
            'overall_status': overall_status,
            'issues_count': {'high': high_count, 'medium': medium_count, 'low': low_count},
            'issues': all_issues,
        }

    def get_issues(self, severity=None, unresolved_only=False, limit=50):
        filtered = self.issues
        if severity:
            filtered = [i for i in filtered if i.severity == severity]
        if unresolved_only:
            filtered = [i for i in filtered if not i.is_resolved]

        filtered.sort(key=lambda x: x.timestamp if isinstance(x.timestamp, datetime)
                       else datetime.fromisoformat(x.timestamp), reverse=True)
        return filtered[:limit]

    def mark_resolved(self, issue_id):
        for issue in self.issues:
            if issue.issue_id == issue_id:
                issue.is_resolved = True
                self._save_issues()
                return True
        return False

    def get_compliance_score(self):
        recent_issues = self.get_issues(unresolved_only=True)
        severity_weights = {'high': 3, 'medium': 2, 'low': 1}
        weighted_score = sum(severity_weights.get(i.severity, 1) for i in recent_issues)
        max_score = 100
        final_score = max(0, max_score - weighted_score * 10)
        return {
            'score': final_score,
            'grade': 'A' if final_score >= 90 else 'B' if final_score >= 70 else 'C' if final_score >= 50 else 'D',
            'unresolved_count': len(recent_issues),
        }
