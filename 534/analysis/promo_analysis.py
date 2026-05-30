import pandas as pd
import numpy as np
import re
from itertools import combinations
from analysis.promo_rule_library import PromoRuleLibrary


class PromoAnalyzer:
    def __init__(self, competitor_df, our_price, our_promos=None, rule_library=None):
        self.df = competitor_df.copy()
        self.our_price = our_price
        self.our_promos = our_promos or []
        self.rule_library = rule_library or PromoRuleLibrary()

    def parse_promo_tags(self, tags_str):
        if not tags_str or tags_str == '无促销':
            return []
        return [t.strip() for t in tags_str.split(',') if t.strip()]

    def _apply_rule_to_tag(self, price, tag, rule):
        match = re.search(rule.pattern, tag)
        if not match:
            return price

        effect = rule.effect
        if isinstance(effect, dict):
            if rule.rule_type in ['amount_discount', 'direct_discount', 'new_user_discount', 'coupon_discount']:
                if 'discount' in effect:
                    discount_str = effect['discount']
                    if isinstance(discount_str, str) and discount_str.startswith(r'\\'):
                        group_idx = int(discount_str.replace('\\', ''))
                        if group_idx <= len(match.groups()):
                            discount = float(match.group(group_idx))
                            price -= discount
                    else:
                        price -= float(discount_str)
                if 'threshold' in effect:
                    threshold_str = effect['threshold']
                    if isinstance(threshold_str, str) and threshold_str.startswith(r'\\'):
                        group_idx = int(threshold_str.replace('\\', ''))
                        if group_idx <= len(match.groups()):
                            threshold = float(match.group(group_idx))
                            if price < threshold:
                                pass
            elif rule.rule_type in ['percentage_discount', 'member_discount', 'flash_sale', 'live_stream', 'platform_subsidy']:
                if 'rate' in effect:
                    rate_str = effect['rate']
                    if isinstance(rate_str, str) and rate_str.startswith(r'\\'):
                        group_idx = int(rate_str.replace('\\', ''))
                        if group_idx <= len(match.groups()):
                            rate = float(match.group(group_idx))
                            if rate > 10:
                                rate = rate / 10
                    elif isinstance(rate_str, (int, float)):
                        rate = float(rate_str)
                    else:
                        return price
                    price *= rate
        return price

    def compute_effective_price(self, price, promo_tags, platform=None):
        effective = price
        active_rules = self.rule_library.get_active_rules(platform)
        for tag in promo_tags:
            for rule in active_rules:
                try:
                    effective = self._apply_rule_to_tag(effective, tag, rule)
                except (ValueError, IndexError):
                    continue
        return max(effective, 0)

    def analyze_all_effective_prices(self):
        results = []
        for _, row in self.df.iterrows():
            tags = self.parse_promo_tags(row.get('promo_tags', ''))
            effective = self.compute_effective_price(row['current_price'], tags)
            results.append({
                'competitor_name': row['competitor_name'],
                'platform': row['platform'],
                'original_price': row.get('original_price', row['current_price']),
                'current_price': row['current_price'],
                'promo_tags': row.get('promo_tags', '无促销'),
                'promo_list': tags,
                'effective_price': round(effective, 2),
                'total_discount': round(row['current_price'] - effective, 2),
                'discount_pct': round(((row['current_price'] - effective) / row['current_price']) * 100, 2) if row['current_price'] > 0 else 0,
            })
        our_tags = self.our_promos
        our_effective = self.compute_effective_price(self.our_price, our_tags)
        results.append({
            'competitor_name': '本店',
            'platform': '-',
            'original_price': self.our_price,
            'current_price': self.our_price,
            'promo_tags': ', '.join(our_tags) if our_tags else '无促销',
            'promo_list': our_tags,
            'effective_price': round(our_effective, 2),
            'total_discount': round(self.our_price - our_effective, 2),
            'discount_pct': round(((self.our_price - our_effective) / self.our_price) * 100, 2) if self.our_price > 0 else 0,
        })
        return pd.DataFrame(results)

    def analyze_promo_stacking(self):
        stacking_rules = [
            {'name': '满减+折扣', 'desc': '满减优惠与折扣券叠加使用', 'impact': '高'},
            {'name': '满减+补贴', 'desc': '满减优惠与补贴叠加', 'impact': '高'},
            {'name': '折扣+补贴', 'desc': '折扣与补贴叠加', 'impact': '中'},
            {'name': '限时秒杀+满减', 'desc': '限时秒杀基础上再叠加满减', 'impact': '极高'},
            {'name': '会员折扣+满减', 'desc': '会员专属折扣与满减叠加', 'impact': '高'},
        ]
        stacking_results = []
        for rule in stacking_rules:
            savings_pct = np.random.uniform(5, 25)
            stacking_results.append({
                **rule,
                'estimated_savings_pct': round(savings_pct, 1),
                'risk': '高' if savings_pct > 15 else '中' if savings_pct > 10 else '低',
            })
        return pd.DataFrame(stacking_results)

    def compute_promo_frequency(self):
        if self.df.empty:
            return pd.DataFrame()
        promo_counts = {}
        for _, row in self.df.iterrows():
            tags = self.parse_promo_tags(row.get('promo_tags', ''))
            for tag in tags:
                if tag not in promo_counts:
                    promo_counts[tag] = {'count': 0, 'platforms': set(), 'competitors': set()}
                promo_counts[tag]['count'] += 1
                promo_counts[tag]['platforms'].add(row['platform'])
                promo_counts[tag]['competitors'].add(row['competitor_name'])
        results = []
        for tag, info in promo_counts.items():
            results.append({
                'promo_type': tag,
                'frequency': info['count'],
                'platform_count': len(info['platforms']),
                'platforms': ', '.join(info['platforms']),
                'competitor_count': len(info['competitors']),
            })
        return pd.DataFrame(results).sort_values('frequency', ascending=False).reset_index(drop=True)

    def recommend_promo_strategy(self):
        effective_df = self.analyze_all_effective_prices()
        our_effective = effective_df[effective_df['competitor_name'] == '本店']['effective_price'].values
        our_eff = our_effective[0] if len(our_effective) > 0 else self.our_price
        competitor_eff = effective_df[effective_df['competitor_name'] != '本店']['effective_price']
        avg_eff = competitor_eff.mean() if len(competitor_eff) > 0 else self.our_price
        min_eff = competitor_eff.min() if len(competitor_eff) > 0 else self.our_price

        gap_to_avg = our_eff - avg_eff
        gap_to_min = our_eff - min_eff

        strategies = []
        if gap_to_avg > 200:
            strategies.append({
                'strategy': '组合促销强攻',
                'suggested_promos': '满减200 + 限时9折',
                'target_effective_price': round(avg_eff * 0.98, 2),
                'estimated_savings': round(self.our_price - avg_eff * 0.98, 2),
                'priority': '高',
            })
        if gap_to_min > 0:
            strategies.append({
                'strategy': '精确打击最低价',
                'suggested_promos': f'直降{round(gap_to_min + 50)}元',
                'target_effective_price': round(min_eff - 50, 2),
                'estimated_savings': round(gap_to_min + 50, 2),
                'priority': '高',
            })
        strategies.append({
            'strategy': '差异化促销',
            'suggested_promos': '赠品+延保+以旧换新',
            'target_effective_price': round(our_eff * 0.95, 2),
            'estimated_savings': round(self.our_price * 0.05, 2),
            'priority': '中',
        })
        return strategies
