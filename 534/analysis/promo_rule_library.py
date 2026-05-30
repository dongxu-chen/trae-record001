import json
import os
from datetime import datetime
import hashlib


class PromoRule:
    def __init__(self, rule_id, name, pattern, rule_type, effect,
                 platform=None, priority=5, status='active',
                 created_by='system', created_at=None, votes=0):
        self.rule_id = rule_id
        self.name = name
        self.pattern = pattern
        self.rule_type = rule_type
        self.effect = effect
        self.platform = platform or 'general'
        self.priority = priority
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now().isoformat()
        self.votes = votes

    def to_dict(self):
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'pattern': self.pattern,
            'rule_type': self.rule_type,
            'effect': self.effect,
            'platform': self.platform,
            'priority': self.priority,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'votes': self.votes,
        }


class PromoRuleLibrary:
    def __init__(self, storage_path=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'promo_rules.json')
        self.storage_path = storage_path
        self.rules = []
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
                    self.rules = [PromoRule(**r) for r in data]
            except (json.JSONDecodeError, IOError):
                self.rules = []

    def _save_rules(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self.rules], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving rules: {e}")

    def _generate_rule_id(self, name, pattern):
        hash_input = f"{name}|{pattern}|{datetime.now().isoformat()}".encode('utf-8')
        return hashlib.md5(hash_input).hexdigest()[:12]

    def _initialize_default_rules(self):
        default_rules = [
            {
                'name': '满减规则 - 满X减Y',
                'pattern': r'满(\d+)减(\d+)',
                'rule_type': 'amount_discount',
                'effect': {'threshold': r'\1', 'discount': r'\2'},
                'platform': 'general',
                'priority': 10,
            },
            {
                'name': '直降规则 - 直降X元',
                'pattern': r'(?:直降|立减|减)(\d+)元?',
                'rule_type': 'direct_discount',
                'effect': {'discount': r'\1'},
                'platform': 'general',
                'priority': 9,
            },
            {
                'name': '折扣规则 - X折',
                'pattern': r'(\d+(?:\.\d+)?)折',
                'rule_type': 'percentage_discount',
                'effect': {'rate': r'\1'},
                'platform': 'general',
                'priority': 8,
            },
            {
                'name': '补贴规则 - 补贴X元',
                'pattern': r'(?:补贴|立省|省)(\d+)元?',
                'rule_type': 'direct_discount',
                'effect': {'discount': r'\1'},
                'platform': 'general',
                'priority': 7,
            },
            {
                'name': '新人专享 - 新人立减X',
                'pattern': r'新人(?:立减|减)(\d+)',
                'rule_type': 'new_user_discount',
                'effect': {'discount': r'\1'},
                'platform': 'general',
                'priority': 6,
            },
            {
                'name': '百亿补贴',
                'pattern': r'百亿补贴',
                'rule_type': 'platform_subsidy',
                'effect': {'rate': 0.9, 'max_discount': 500},
                'platform': 'pinduoduo',
                'priority': 10,
            },
            {
                'name': 'PLUS会员专享',
                'pattern': r'PLUS会员(?:专享|)?(?:(\d+(?:\.\d+)?)折|减(\d+))?',
                'rule_type': 'member_discount',
                'effect': {'rate': r'\1', 'discount': r'\2'},
                'platform': 'jd',
                'priority': 8,
            },
            {
                'name': '天猫品类券',
                'pattern': r'(?:品类|购物)券.*?(\d+)',
                'rule_type': 'coupon_discount',
                'effect': {'discount': r'\1'},
                'platform': 'tmall',
                'priority': 7,
            },
            {
                'name': '限时秒杀',
                'pattern': r'(?:限时|整点|)秒杀',
                'rule_type': 'flash_sale',
                'effect': {'rate': 0.85},
                'platform': 'general',
                'priority': 10,
            },
            {
                'name': '直播间专享',
                'pattern': r'(?:直播|直播间)专享',
                'rule_type': 'live_stream',
                'effect': {'rate': 0.9},
                'platform': 'general',
                'priority': 9,
            },
        ]
        for rule_data in default_rules:
            rule_id = self._generate_rule_id(rule_data['name'], rule_data['pattern'])
            rule = PromoRule(
                rule_id=rule_id,
                name=rule_data['name'],
                pattern=rule_data['pattern'],
                rule_type=rule_data['rule_type'],
                effect=rule_data['effect'],
                platform=rule_data['platform'],
                priority=rule_data['priority'],
                status='active',
                created_by='system',
                created_at=datetime.now().isoformat(),
                votes=100,
            )
            self.rules.append(rule)
        self._save_rules()

    def add_rule(self, name, pattern, rule_type, effect, platform='general', priority=5, created_by='user'):
        for rule in self.rules:
            if rule.pattern == pattern and rule.status == 'active':
                return False, '规则已存在'
        rule_id = self._generate_rule_id(name, pattern)
        rule = PromoRule(
            rule_id=rule_id,
            name=name,
            pattern=pattern,
            rule_type=rule_type,
            effect=effect,
            platform=platform,
            priority=priority,
            status='pending',
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            votes=0,
        )
        self.rules.append(rule)
        self._save_rules()
        return True, rule_id

    def vote_rule(self, rule_id, positive=True):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.votes += 1 if positive else -1
                self._save_rules()
                return True
        return False

    def approve_rule(self, rule_id, approved=True):
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.status = 'active' if approved else 'rejected'
                self._save_rules()
                return True
        return False

    def get_active_rules(self, platform=None):
        rules = [r for r in self.rules if r.status == 'active']
        if platform and platform != 'general':
            platform_rules = [r for r in rules if r.platform == platform]
            general_rules = [r for r in rules if r.platform == 'general']
            rules = platform_rules + general_rules
        rules.sort(key=lambda x: (-x.priority, -x.votes))
        return rules

    def get_pending_rules(self):
        return [r for r in self.rules if r.status == 'pending']

    def get_rules_by_type(self, rule_type):
        return [r for r in self.rules if r.rule_type == rule_type and r.status == 'active']

    def search_rules(self, keyword):
        keyword = keyword.lower()
        return [
            r for r in self.rules
            if keyword in r.name.lower() or keyword in r.rule_type.lower()
        ]

    def delete_rule(self, rule_id):
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        self._save_rules()
        return True

    def get_stats(self):
        return {
            'total': len(self.rules),
            'active': len([r for r in self.rules if r.status == 'active']),
            'pending': len([r for r in self.rules if r.status == 'pending']),
            'rejected': len([r for r in self.rules if r.status == 'rejected']),
            'by_type': self._count_by(lambda r: r.rule_type),
            'by_platform': self._count_by(lambda r: r.platform),
            'top_voted': sorted(self.rules, key=lambda x: -x.votes)[:5],
        }

    def _count_by(self, key_func):
        counts = {}
        for rule in self.rules:
            if rule.status != 'active':
                continue
            key = key_func(rule)
            counts[key] = counts.get(key, 0) + 1
        return counts
