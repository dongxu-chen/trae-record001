import json
import os
import re
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

class RuleConditionType(str, Enum):
    MERCHANT_CONTAINS = "merchant_contains"
    MERCHANT_MATCHES = "merchant_matches"
    AMOUNT_GREATER = "amount_greater"
    AMOUNT_LESS = "amount_less"
    AMOUNT_BETWEEN = "amount_between"
    TIME_BETWEEN = "time_between"
    DAY_OF_WEEK = "day_of_week"

class RuleAction(str, Enum):
    SET_CATEGORY = "set_category"
    FLAG_AS_ANOMALY = "flag_as_anomaly"
    ADD_TAG = "add_tag"

@dataclass
class RuleCondition:
    type: RuleConditionType
    value: Any
    field: str = "merchant"

@dataclass
class Rule:
    id: str
    name: str
    conditions: List[RuleCondition]
    action: RuleAction
    action_value: str
    priority: int = 0
    enabled: bool = True
    logical_op: str = "AND"

class RuleEngine:
    def __init__(self, rules_path: str = "data/rules.json"):
        self.rules_path = rules_path
        self.rules: List[Rule] = []
        self._load_rules()
    
    def _load_rules(self):
        if os.path.exists(self.rules_path):
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = [self._dict_to_rule(r) for r in data]
        else:
            self.rules = self._get_default_rules()
            self._save_rules()
    
    def _save_rules(self):
        os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
        data = [asdict(r) for r in self.rules]
        with open(self.rules_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _dict_to_rule(self, data: Dict) -> Rule:
        conditions = [
            RuleCondition(
                type=RuleConditionType(c['type']),
                value=c['value'],
                field=c.get('field', 'merchant')
            )
            for c in data['conditions']
        ]
        return Rule(
            id=data['id'],
            name=data['name'],
            conditions=conditions,
            action=RuleAction(data['action']),
            action_value=data['action_value'],
            priority=data.get('priority', 0),
            enabled=data.get('enabled', True),
            logical_op=data.get('logical_op', 'AND')
        )
    
    def _get_default_rules(self) -> List[Rule]:
        default_rules = [
            Rule(
                id="rule_001",
                name="大额消费标记",
                conditions=[RuleCondition(
                    type=RuleConditionType.AMOUNT_GREATER,
                    value=5000,
                    field="amount"
                )],
                action=RuleAction.FLAG_AS_ANOMALY,
                action_value="大额消费",
                priority=10
            ),
            Rule(
                id="rule_002",
                name="深夜餐饮",
                conditions=[
                    RuleCondition(
                        type=RuleConditionType.TIME_BETWEEN,
                        value=["22:00", "06:00"],
                        field="time"
                    ),
                    RuleCondition(
                        type=RuleConditionType.MERCHANT_CONTAINS,
                        value=["餐厅", "烧烤", "火锅", "咖啡"],
                        field="merchant"
                    )
                ],
                action=RuleAction.SET_CATEGORY,
                action_value="餐饮",
                priority=5
            ),
            Rule(
                id="rule_003",
                name="周末娱乐消费",
                conditions=[
                    RuleCondition(
                        type=RuleConditionType.DAY_OF_WEEK,
                        value=[5, 6],
                        field="date"
                    ),
                    RuleCondition(
                        type=RuleConditionType.AMOUNT_BETWEEN,
                        value=[100, 1000],
                        field="amount"
                    )
                ],
                action=RuleAction.ADD_TAG,
                action_value="周末消费",
                priority=3,
                logical_op="AND"
            ),
            Rule(
                id="rule_004",
                name="小额医疗",
                conditions=[
                    RuleCondition(
                        type=RuleConditionType.MERCHANT_CONTAINS,
                        value=["药房", "药店", "体检"],
                        field="merchant"
                    ),
                    RuleCondition(
                        type=RuleConditionType.AMOUNT_LESS,
                        value=500,
                        field="amount"
                    )
                ],
                action=RuleAction.SET_CATEGORY,
                action_value="医疗",
                priority=8
            )
        ]
        return default_rules
    
    def _evaluate_condition(self, condition: RuleCondition, transaction: Dict) -> bool:
        field_value = transaction.get(condition.field, '')
        
        if condition.type == RuleConditionType.MERCHANT_CONTAINS:
            keywords = condition.value if isinstance(condition.value, list) else [condition.value]
            return any(kw.lower() in str(field_value).lower() for kw in keywords)
        
        elif condition.type == RuleConditionType.MERCHANT_MATCHES:
            pattern = condition.value
            return bool(re.search(pattern, str(field_value), re.IGNORECASE))
        
        elif condition.type == RuleConditionType.AMOUNT_GREATER:
            return float(field_value) > float(condition.value)
        
        elif condition.type == RuleConditionType.AMOUNT_LESS:
            return float(field_value) < float(condition.value)
        
        elif condition.type == RuleConditionType.AMOUNT_BETWEEN:
            min_val, max_val = condition.value
            return float(min_val) <= float(field_value) <= float(max_val)
        
        elif condition.type == RuleConditionType.TIME_BETWEEN:
            start_time, end_time = condition.value
            from datetime import datetime
            current_time = datetime.strptime(field_value, "%H:%M:%S").time() if isinstance(field_value, str) else field_value
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            if start <= end:
                return start <= current_time <= end
            else:
                return current_time >= start or current_time <= end
        
        elif condition.type == RuleConditionType.DAY_OF_WEEK:
            target_days = condition.value if isinstance(condition.value, list) else [condition.value]
            from datetime import datetime
            if isinstance(field_value, str):
                date = datetime.strptime(field_value, "%Y-%m-%d")
            else:
                date = field_value
            return date.weekday() in target_days
        
        return False
    
    def _evaluate_conditions(self, conditions: List[RuleCondition], transaction: Dict, logical_op: str) -> bool:
        results = [self._evaluate_condition(c, transaction) for c in conditions]
        if logical_op == "AND":
            return all(results)
        elif logical_op == "OR":
            return any(results)
        return all(results)
    
    def apply_rules(self, transaction: Dict) -> Dict:
        result = {
            'category': None,
            'tags': [],
            'anomaly_flags': [],
            'matched_rules': []
        }
        
        sorted_rules = sorted([r for r in self.rules if r.enabled], key=lambda x: -x.priority)
        
        for rule in sorted_rules:
            if self._evaluate_conditions(rule.conditions, transaction, rule.logical_op):
                result['matched_rules'].append(rule.name)
                
                if rule.action == RuleAction.SET_CATEGORY:
                    if result['category'] is None:
                        result['category'] = rule.action_value
                
                elif rule.action == RuleAction.FLAG_AS_ANOMALY:
                    result['anomaly_flags'].append(rule.action_value)
                
                elif rule.action == RuleAction.ADD_TAG:
                    result['tags'].append(rule.action_value)
        
        return result
    
    def add_rule(self, rule: Rule) -> bool:
        if any(r.id == rule.id for r in self.rules):
            return False
        self.rules.append(rule)
        self._save_rules()
        return True
    
    def update_rule(self, rule_id: str, rule: Rule) -> bool:
        for i, r in enumerate(self.rules):
            if r.id == rule_id:
                self.rules[i] = rule
                self._save_rules()
                return True
        return False
    
    def delete_rule(self, rule_id: str) -> bool:
        for i, r in enumerate(self.rules):
            if r.id == rule_id:
                del self.rules[i]
                self._save_rules()
                return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        for r in self.rules:
            if r.id == rule_id:
                return r
        return None
    
    def get_all_rules(self) -> List[Rule]:
        return sorted(self.rules, key=lambda x: -x.priority)
    
    def toggle_rule(self, rule_id: str) -> bool:
        for r in self.rules:
            if r.id == rule_id:
                r.enabled = not r.enabled
                self._save_rules()
                return True
        return False
