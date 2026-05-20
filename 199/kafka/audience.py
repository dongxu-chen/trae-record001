from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import json
import time
import random
from collections import defaultdict


AGE_GROUPS = [
    {'name': '18-24岁', 'weight': 0.25, 'min_age': 18, 'max_age': 24, 'color': '#00ffff'},
    {'name': '25-30岁', 'weight': 0.35, 'min_age': 25, 'max_age': 30, 'color': '#00ff88'},
    {'name': '31-40岁', 'weight': 0.25, 'min_age': 31, 'max_age': 40, 'color': '#ffaa00'},
    {'name': '41-50岁', 'weight': 0.10, 'min_age': 41, 'max_age': 50, 'color': '#ff4466'},
    {'name': '50岁以上', 'weight': 0.05, 'min_age': 51, 'max_age': 70, 'color': '#aa44ff'},
]

REGIONS = [
    {'name': '华东', 'weight': 0.30, 'provinces': ['上海', '江苏', '浙江', '安徽', '福建', '江西', '山东'], 'color': '#00ffff'},
    {'name': '华南', 'weight': 0.25, 'provinces': ['广东', '广西', '海南', '香港', '澳门'], 'color': '#00ff88'},
    {'name': '华北', 'weight': 0.20, 'provinces': ['北京', '天津', '河北', '山西', '内蒙古'], 'color': '#ffaa00'},
    {'name': '华中', 'weight': 0.12, 'provinces': ['湖北', '湖南', '河南'], 'color': '#ff4466'},
    {'name': '西南', 'weight': 0.08, 'provinces': ['四川', '重庆', '贵州', '云南', '西藏'], 'color': '#aa44ff'},
    {'name': '东北', 'weight': 0.03, 'provinces': ['辽宁', '吉林', '黑龙江'], 'color': '#44aaff'},
    {'name': '西北', 'weight': 0.02, 'provinces': ['陕西', '甘肃', '青海', '宁夏', '新疆'], 'color': '#ff8800'},
]

PURCHASE_POWER = [
    {'name': '低消费', 'range': '<¥100', 'weight': 0.20, 'min_amount': 0, 'max_amount': 100, 'color': '#aaaaaa'},
    {'name': '中低消费', 'range': '¥100-500', 'weight': 0.35, 'min_amount': 100, 'max_amount': 500, 'color': '#00ff88'},
    {'name': '中消费', 'range': '¥500-1000', 'weight': 0.25, 'min_amount': 500, 'max_amount': 1000, 'color': '#00ffff'},
    {'name': '中高消费', 'range': '¥1000-5000', 'weight': 0.15, 'min_amount': 1000, 'max_amount': 5000, 'color': '#ffaa00'},
    {'name': '高消费', 'range': '>¥5000', 'weight': 0.05, 'min_amount': 5000, 'max_amount': 50000, 'color': '#ff4466'},
]

GENDER_DISTRIBUTION = [
    {'name': '女性', 'weight': 0.65, 'color': '#ff66b2'},
    {'name': '男性', 'weight': 0.35, 'color': '#44aaff'},
]

DEVICE_DISTRIBUTION = [
    {'name': 'iOS', 'weight': 0.45, 'color': '#aaaaaa'},
    {'name': 'Android', 'weight': 0.50, 'color': '#00ff88'},
    {'name': '其他', 'weight': 0.05, 'color': '#ffaa00'},
]


@dataclass
class AudienceProfileMessage:
    timestamp: float
    viewer_id: str
    age_group: str
    age: int
    gender: str
    region: str
    province: str
    purchase_power: str
    purchase_amount: float
    device: str
    is_new_user: bool
    is_vip: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class AudienceProfileGenerator:
    def __init__(self):
        self._total_users = 0
        self._age_distribution = defaultdict(int)
        self._region_distribution = defaultdict(int)
        self._purchase_distribution = defaultdict(int)
        self._gender_distribution = defaultdict(int)
        self._device_distribution = defaultdict(int)
        self._total_purchase_amount = 0.0

    @staticmethod
    def _weighted_choice(options: List[Dict]) -> Dict:
        weights = [opt['weight'] for opt in options]
        total = sum(weights)
        r = random.uniform(0, total)
        cumsum = 0
        for opt in options:
            cumsum += opt['weight']
            if r <= cumsum:
                return opt
        return options[0]

    def generate(self, viewer_id: str = None) -> AudienceProfileMessage:
        age_group = self._weighted_choice(AGE_GROUPS)
        gender = self._weighted_choice(GENDER_DISTRIBUTION)
        region = self._weighted_choice(REGIONS)
        purchase = self._weighted_choice(PURCHASE_POWER)
        device = self._weighted_choice(DEVICE_DISTRIBUTION)

        age = random.randint(age_group['min_age'], age_group['max_age'])
        province = random.choice(region['provinces'])
        purchase_amount = random.uniform(purchase['min_amount'], purchase['max_amount'])

        profile = AudienceProfileMessage(
            timestamp=time.time(),
            viewer_id=viewer_id or f"user_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            age_group=age_group['name'],
            age=age,
            gender=gender['name'],
            region=region['name'],
            province=province,
            purchase_power=purchase['name'],
            purchase_amount=round(purchase_amount, 2),
            device=device['name'],
            is_new_user=random.random() < 0.15,
            is_vip=random.random() < 0.1,
        )

        self._update_statistics(profile)
        return profile

    def _update_statistics(self, profile: AudienceProfileMessage):
        self._total_users += 1
        self._age_distribution[profile.age_group] += 1
        self._region_distribution[profile.region] += 1
        self._purchase_distribution[profile.purchase_power] += 1
        self._gender_distribution[profile.gender] += 1
        self._device_distribution[profile.device] += 1
        self._total_purchase_amount += profile.purchase_amount

    def get_statistics(self) -> Dict:
        if self._total_users == 0:
            return {
                'total_users': 0,
                'age_distribution': [],
                'region_distribution': [],
                'purchase_distribution': [],
                'gender_distribution': [],
                'device_distribution': [],
                'avg_purchase': 0,
                'top_regions': [],
            }

        return {
            'total_users': self._total_users,
            'age_distribution': [
                {'name': g['name'], 'count': self._age_distribution[g['name']],
                 'rate': round(self._age_distribution[g['name']] / self._total_users, 4),
                 'color': g['color']}
                for g in AGE_GROUPS
            ],
            'region_distribution': [
                {'name': r['name'], 'count': self._region_distribution[r['name']],
                 'rate': round(self._region_distribution[r['name']] / self._total_users, 4),
                 'color': r['color']}
                for r in REGIONS
            ],
            'purchase_distribution': [
                {'name': p['name'], 'range': p['range'], 'count': self._purchase_distribution[p['name']],
                 'rate': round(self._purchase_distribution[p['name']] / self._total_users, 4),
                 'color': p['color']}
                for p in PURCHASE_POWER
            ],
            'gender_distribution': [
                {'name': g['name'], 'count': self._gender_distribution[g['name']],
                 'rate': round(self._gender_distribution[g['name']] / self._total_users, 4),
                 'color': g['color']}
                for g in GENDER_DISTRIBUTION
            ],
            'device_distribution': [
                {'name': d['name'], 'count': self._device_distribution[d['name']],
                 'rate': round(self._device_distribution[d['name']] / self._total_users, 4),
                 'color': d['color']}
                for d in DEVICE_DISTRIBUTION
            ],
            'avg_purchase': round(self._total_purchase_amount / self._total_users, 2),
            'top_regions': sorted(
                [{'name': r, 'count': c} for r, c in self._region_distribution.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:5],
        }

    def reset(self):
        self._total_users = 0
        self._age_distribution.clear()
        self._region_distribution.clear()
        self._purchase_distribution.clear()
        self._gender_distribution.clear()
        self._device_distribution.clear()
        self._total_purchase_amount = 0.0


class AudienceProfileAggregator:
    def __init__(self, window_seconds: int = 300):
        self._window_seconds = window_seconds
        self._profiles = []
        self._age_distribution = defaultdict(int)
        self._region_distribution = defaultdict(int)
        self._purchase_distribution = defaultdict(int)
        self._gender_distribution = defaultdict(int)
        self._total_purchase = 0.0
        self._total_count = 0

    def add_profile(self, data: Dict):
        timestamp = data.get('timestamp', time.time())
        self._profiles.append({'timestamp': timestamp, 'data': data})

        self._age_distribution[data.get('age_group', '未知')] += 1
        self._region_distribution[data.get('region', '未知')] += 1
        self._purchase_distribution[data.get('purchase_power', '未知')] += 1
        self._gender_distribution[data.get('gender', '未知')] += 1
        self._total_purchase += data.get('purchase_amount', 0)
        self._total_count += 1

        self._clean_old()

    def _clean_old(self):
        current = time.time()
        cutoff = current - self._window_seconds

        while self._profiles and self._profiles[0]['timestamp'] < cutoff:
            old = self._profiles.pop(0)
            data = old['data']
            self._age_distribution[data.get('age_group', '未知')] -= 1
            self._region_distribution[data.get('region', '未知')] -= 1
            self._purchase_distribution[data.get('purchase_power', '未知')] -= 1
            self._gender_distribution[data.get('gender', '未知')] -= 1
            self._total_purchase -= data.get('purchase_amount', 0)
            self._total_count -= 1

    def get_aggregated_data(self) -> Dict:
        self._clean_old()
        total = max(self._total_count, 1)

        age_data = [
            {'name': g['name'], 'value': self._age_distribution.get(g['name'], 0),
             'rate': round(self._age_distribution.get(g['name'], 0) / total, 4),
             'itemStyle': {'color': g['color']}}
            for g in AGE_GROUPS
        ]

        region_data = [
            {'name': r['name'], 'value': self._region_distribution.get(r['name'], 0),
             'rate': round(self._region_distribution.get(r['name'], 0) / total, 4),
             'itemStyle': {'color': r['color']}}
            for r in REGIONS
        ]
        region_data.sort(key=lambda x: x['value'], reverse=True)

        purchase_data = [
            {'name': p['name'], 'range': p['range'], 'value': self._purchase_distribution.get(p['name'], 0),
             'rate': round(self._purchase_distribution.get(p['name'], 0) / total, 4),
             'itemStyle': {'color': p['color']}}
            for p in PURCHASE_POWER
        ]

        gender_data = [
            {'name': g['name'], 'value': self._gender_distribution.get(g['name'], 0),
             'rate': round(self._gender_distribution.get(g['name'], 0) / total, 4),
             'itemStyle': {'color': g['color']}}
            for g in GENDER_DISTRIBUTION
        ]

        return {
            'total_samples': self._total_count,
            'age_distribution': age_data,
            'region_distribution': region_data,
            'purchase_distribution': purchase_data,
            'gender_distribution': gender_data,
            'avg_purchase': round(self._total_purchase / total, 2),
            'window_seconds': self._window_seconds,
        }
