import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os


class DynamicPricingRule:
    def __init__(self, rule_id, name, rule_type, condition, action, priority=5,
                 status='active', min_price=None, max_price=None):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.condition = condition
        self.action = action
        self.priority = priority
        self.status = status
        self.min_price = min_price
        self.max_price = max_price

    def to_dict(self):
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'rule_type': self.rule_type,
            'condition': self.condition,
            'action': self.action,
            'priority': self.priority,
            'status': self.status,
            'min_price': self.min_price,
            'max_price': self.max_price,
        }


class DynamicPricingEngine:
    def __init__(self, our_cost, base_price, storage_path=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'dynamic_pricing_rules.json')
        self.storage_path = storage_path
        self.our_cost = our_cost
        self.base_price = base_price
        self.current_price = base_price
        self.rules = []
        self.price_history = []
        self.min_margin = 0.1
        self.max_price_change = 0.1
        self._ensure_storage_dir()
        self._load_rules()
        if not self.rules:
            self._initialize_default_rules()

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_rules(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rules = [DynamicPricingRule(**r) for r in data]
            except (json.JSONDecodeError, IOError):
                self.rules = []

    def _save_rules(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self.rules], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving rules: {e}")

    def _initialize_default_rules(self):
        default_rules = [
            {
                'name': '跟随最低价',
                'rule_type': 'competitor_based',
                'condition': {'type': 'below_min', 'threshold': 0.05},
                'action': {'type': 'match_min', 'offset': -0.01},
                'priority': 10,
                'min_price': None,
                'max_price': None,
            },
            {
                'name': '维持指数95',
                'rule_type': 'index_based',
                'condition': {'type': 'index_above', 'threshold': 98},
                'action': {'type': 'adjust_to_index', 'target_index': 95},
                'priority': 8,
                'min_price': None,
                'max_price': None,
            },
            {
                'name': '高库存降价',
                'rule_type': 'inventory_based',
                'condition': {'type': 'stock_above', 'threshold': 1000},
                'action': {'type': 'discount', 'rate': 0.05},
                'priority': 7,
                'min_price': None,
                'max_price': None,
            },
            {
                'name': '低库存涨价',
                'rule_type': 'inventory_based',
                'condition': {'type': 'stock_below', 'threshold': 100},
                'action': {'type': 'premium', 'rate': 0.03},
                'priority': 7,
                'min_price': None,
                'max_price': None,
            },
            {
                'name': '周末促销',
                'rule_type': 'time_based',
                'condition': {'type': 'is_weekend'},
                'action': {'type': 'discount', 'rate': 0.02},
                'priority': 5,
                'min_price': None,
                'max_price': None,
            },
        ]
        for i, rule_data in enumerate(default_rules):
            rule = DynamicPricingRule(
                rule_id=f"default_rule_{i+1}",
                name=rule_data['name'],
                rule_type=rule_data['rule_type'],
                condition=rule_data['condition'],
                action=rule_data['action'],
                priority=rule_data['priority'],
                status='active',
                min_price=rule_data['min_price'],
                max_price=rule_data['max_price'],
            )
            self.rules.append(rule)
        self._save_rules()

    def set_min_margin(self, margin):
        self.min_margin = margin

    def set_max_price_change(self, change_rate):
        self.max_price_change = change_rate

    def get_min_allowed_price(self):
        return self.our_cost * (1 + self.min_margin)

    def _evaluate_condition(self, rule, context):
        cond = rule.condition
        cond_type = cond.get('type', '')

        if cond_type == 'below_min':
            comp_min = context.get('competitor_min_price', float('inf'))
            threshold = cond.get('threshold', 0)
            return (self.current_price - comp_min) / self.current_price > threshold

        elif cond_type == 'index_above':
            price_index = context.get('price_index', 100)
            threshold = cond.get('threshold', 100)
            return price_index > threshold

        elif cond_type == 'stock_above':
            stock = context.get('stock_level', 0)
            threshold = cond.get('threshold', 0)
            return stock > threshold

        elif cond_type == 'stock_below':
            stock = context.get('stock_level', float('inf'))
            threshold = cond.get('threshold', 0)
            return stock < threshold

        elif cond_type == 'is_weekend':
            today = datetime.now().weekday()
            return today >= 5

        elif cond_type == 'price_trend':
            trend = context.get('price_trend', 'stable')
            return trend == cond.get('direction', '')

        return False

    def _apply_action(self, rule, context):
        action = rule.action
        action_type = action.get('type', '')
        suggested_price = self.current_price

        if action_type == 'match_min':
            comp_min = context.get('competitor_min_price', self.current_price)
            offset = action.get('offset', 0)
            suggested_price = comp_min * (1 + offset)

        elif action_type == 'adjust_to_index':
            target_index = action.get('target_index', 100)
            avg_price = context.get('competitor_avg_price', self.current_price)
            suggested_price = avg_price * target_index / 100

        elif action_type == 'discount':
            rate = action.get('rate', 0)
            suggested_price = self.current_price * (1 - rate)

        elif action_type == 'premium':
            rate = action.get('rate', 0)
            suggested_price = self.current_price * (1 + rate)

        elif action_type == 'fixed':
            suggested_price = action.get('price', self.current_price)

        min_allowed = self.get_min_allowed_price()
        if suggested_price < min_allowed:
            suggested_price = min_allowed

        if rule.min_price and suggested_price < rule.min_price:
            suggested_price = rule.min_price
        if rule.max_price and suggested_price > rule.max_price:
            suggested_price = rule.max_price

        max_change = self.current_price * self.max_price_change
        if suggested_price < self.current_price - max_change:
            suggested_price = self.current_price - max_change
        elif suggested_price > self.current_price + max_change:
            suggested_price = self.current_price + max_change

        return round(suggested_price, 2)

    def calculate_suggested_price(self, competitor_df, context=None):
        if context is None:
            context = {}

        if not competitor_df.empty:
            context['competitor_min_price'] = competitor_df['current_price'].min()
            context['competitor_avg_price'] = competitor_df['current_price'].mean()
            context['competitor_max_price'] = competitor_df['current_price'].max()
            context['price_index'] = (self.current_price / context['competitor_avg_price']) * 100

        active_rules = [r for r in self.rules if r.status == 'active']
        active_rules.sort(key=lambda x: -x.priority)

        suggestions = []
        for rule in active_rules:
            if self._evaluate_condition(rule, context):
                suggested = self._apply_action(rule, context)
                suggestions.append({
                    'rule_id': rule.rule_id,
                    'rule_name': rule.name,
                    'priority': rule.priority,
                    'suggested_price': suggested_price,
                })

        if not suggestions:
            return {
                'current_price': self.current_price,
                'suggested_price': self.current_price,
                'applied_rule': None,
                'all_suggestions': [],
                'min_allowed_price': round(self.get_min_allowed_price(), 2),
            }

        top_suggestion = suggestions[0]

        return {
            'current_price': self.current_price,
            'suggested_price': top_suggestion['suggested_price'],
            'applied_rule': top_suggestion['rule_name'],
            'applied_rule_id': top_suggestion['rule_id'],
            'all_suggestions': suggestions,
            'min_allowed_price': round(self.get_min_allowed_price(), 2),
            'price_change_pct': round((top_suggestion['suggested_price'] - self.current_price) / self.current_price * 100, 2),
        }

    def add_rule(self, name, rule_type, condition, action, priority=5, min_price=None, max_price=None):
        rule_id = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        rule = DynamicPricingRule(
            rule_id=rule_id,
            name=name,
            rule_type=rule_type,
            condition=condition,
            action=action,
            priority=priority,
            status='active',
            min_price=min_price,
            max_price=max_price,
        )
        self.rules.append(rule)
        self._save_rules()
        return rule_id

    def update_rule(self, rule_id, **kwargs):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                for key, value in kwargs.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                self._save_rules()
                return True
        return False

    def delete_rule(self, rule_id):
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        self._save_rules()
        return True

    def toggle_rule(self, rule_id):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.status = 'inactive' if rule.status == 'active' else 'active'
                self._save_rules()
                return rule.status
        return None

    def get_rules(self):
        return sorted(self.rules, key=lambda x: -x.priority)

    def get_rules_stats(self):
        return {
            'total': len(self.rules),
            'active': len([r for r in self.rules if r.status == 'active']),
            'inactive': len([r for r in self.rules if r.status == 'inactive']),
            'by_type': self._count_by(lambda r: r.rule_type),
        }

    def _count_by(self, key_func):
        counts = {}
        for rule in self.rules:
            key = key_func(rule)
            counts[key] = counts.get(key, 0) + 1
        return counts
