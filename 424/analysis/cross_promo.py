"""
交叉促销识别模块
检测关联购买优惠（买A降B、组合套餐、满赠等）
"""
import re
from typing import List, Dict, Optional, Set
from datetime import datetime
from collections import defaultdict

from loguru import logger


class CrossPromotionDetector:
    def __init__(self, config=None):
        if config is None:
            from config import ANALYSIS_CONFIG as config
        self.config = config
        self.cross_promo_keywords = config.get('cross_promo_keywords', {
            'buy_x_get_y': ['买.*送', '买.*赠', '买一送', 'buy.*get', 'bundle'],
            'package_deal': ['套餐', '组合', '套装', 'combo', 'package'],
            'bundle_discount': ['两件', '三件', '第2件', '第3件', '2件', '3件'],
            'conditional_discount': ['满.*送', '满.*减', '满.*享', 'spend.*save'],
            'free_gift': ['赠品', '礼品', 'free gift', 'gift with'],
        })
        self.price_relation_threshold = config.get('price_relation_threshold', 0.1)

    def detect(self, product_data: Dict, related_products: List[Dict] = None) -> List[Dict]:
        promotions = []
        product_name = product_data.get('name', '')
        product_desc = product_data.get('description', '') or product_data.get('extra_info', '') or ''
        product_price = product_data.get('current_price')
        promo_text = product_data.get('promotion_info', '') or ''

        full_text = f"{product_name} {product_desc} {promo_text}".lower()

        buy_x_get_y = self._detect_buy_x_get_y(full_text, product_data, related_products)
        promotions.extend(buy_x_get_y)

        package_deal = self._detect_package_deal(full_text, product_data)
        promotions.extend(package_deal)

        bundle_discount = self._detect_bundle_discount(full_text, product_data)
        promotions.extend(bundle_discount)

        conditional = self._detect_conditional_discount(full_text, product_data)
        promotions.extend(conditional)

        free_gift = self._detect_free_gift(full_text, product_data)
        promotions.extend(free_gift)

        if related_products:
            cross_price = self._detect_cross_price_relation(product_data, related_products)
            promotions.extend(cross_price)

        return promotions

    def _detect_buy_x_get_y(self, text: str, product_data: Dict, related: List[Dict] = None) -> List[Dict]:
        promotions = []
        patterns = self.cross_promo_keywords['buy_x_get_y']

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                match_text = match.group()
                promo_detail = self._parse_buy_x_get_y_detail(match_text, text)
                promotions.append({
                    'promo_type': 'buy_x_get_y',
                    'trigger_product': product_data.get('product_id'),
                    'trigger_name': product_data.get('name'),
                    'source': product_data.get('source'),
                    'matched_text': match_text,
                    'detail': promo_detail,
                    'benefit_product': promo_detail.get('gift_item'),
                    'conditions': promo_detail.get('conditions'),
                    'estimated_value': promo_detail.get('value'),
                })

        return promotions

    def _parse_buy_x_get_y_detail(self, match_text: str, full_text: str) -> Dict:
        detail = {'conditions': {}, 'gift_item': None, 'value': None}

        buy_match = re.search(r'买(\d+)?', match_text)
        get_match = re.search(r'(?:送|赠|get)(\d+)?', match_text)
        free_match = re.search(r'(免费|free)', match_text)

        if buy_match and buy_match.group(1):
            detail['conditions']['buy_quantity'] = int(buy_match.group(1))
        if get_match and get_match.group(1):
            detail['gift_quantity'] = int(get_match.group(1))
        detail['is_free'] = bool(free_match)

        gift_patterns = [
            r'送([^，。！,!]+)',
            r'赠([^，。！,!]+)',
            r'get ([^\.,!]+)',
        ]
        for p in gift_patterns:
            m = re.search(p, full_text)
            if m:
                detail['gift_item'] = m.group(1).strip()
                break

        return detail

    def _detect_package_deal(self, text: str, product_data: Dict) -> List[Dict]:
        promotions = []
        patterns = self.cross_promo_keywords['package_deal']

        for pattern in patterns:
            if re.search(pattern, text):
                product_name = product_data.get('name', '')

                products_included = self._extract_package_items(text, product_name)

                package_price = product_data.get('current_price')
                original_total = product_data.get('original_price') or product_data.get('current_price')

                savings = None
                if package_price and original_total and original_total > package_price:
                    savings = original_total - package_price

                promotions.append({
                    'promo_type': 'package_deal',
                    'trigger_product': product_data.get('product_id'),
                    'trigger_name': product_data.get('name'),
                    'source': product_data.get('source'),
                    'matched_pattern': pattern,
                    'products_included': products_included,
                    'package_price': package_price,
                    'original_total': original_total,
                    'savings': savings,
                    'savings_percent': round(savings / original_total, 4) if savings and original_total else None,
                })

        return promotions

    def _extract_package_items(self, text: str, product_name: str) -> List[str]:
        items = [product_name]
        separator_patterns = [
            r'\+([^\+]+)',
            r'\+ ([^\+]+)',
            r'和([^，。,!]+)',
            r'与([^，。,!]+)',
        ]
        for p in separator_patterns:
            found = re.findall(p, text)
            items.extend([f.strip() for f in found for f in f.split() if len(f.strip()) > 2])
        return list(set(items))

    def _detect_bundle_discount(self, text: str, product_data: Dict) -> List[Dict]:
        promotions = []
        patterns = self.cross_promo_keywords['bundle_discount']

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                match_text = match.group()
                discount_detail = self._parse_bundle_discount(match_text, text)

                promotions.append({
                    'promo_type': 'bundle_discount',
                    'trigger_product': product_data.get('product_id'),
                    'trigger_name': product_data.get('name'),
                    'source': product_data.get('source'),
                    'matched_text': match_text,
                    'min_quantity': discount_detail.get('min_quantity'),
                    'discount_percent': discount_detail.get('discount_percent'),
                    'discount_price': discount_detail.get('discount_price'),
                    'detail': discount_detail,
                })

        return promotions

    def _parse_bundle_discount(self, match_text: str, full_text: str) -> Dict:
        detail = {}

        qty_match = re.search(r'(\d+)(?:件|个|个)', match_text)
        if qty_match:
            detail['min_quantity'] = int(qty_match.group(1))

        discount_match = re.search(r'(\d+)折|(\d+)% off|减(\d+)', match_text)
        if discount_match:
            for g in discount_match.groups():
                if g:
                    detail['discount_percent'] = float(g) / 10 if '折' in match_text else float(g) / 100
                    break

        price_match = re.search(r'(\d+(?:\.\d+)?)元?', full_text)
        if price_match:
            detail['discount_price'] = float(price_match.group(1))

        return detail

    def _detect_conditional_discount(self, text: str, product_data: Dict) -> List[Dict]:
        promotions = []
        patterns = self.cross_promo_keywords['conditional_discount']

        for pattern in patterns:
            if re.search(pattern, text):
                condition = self._parse_conditional(text)
                promotions.append({
                    'promo_type': 'conditional_discount',
                    'trigger_product': product_data.get('product_id'),
                    'trigger_name': product_data.get('name'),
                    'source': product_data.get('source'),
                    'threshold_amount': condition.get('threshold'),
                    'discount_amount': condition.get('discount'),
                    'discount_percent': condition.get('discount_percent'),
                    'condition_text': condition.get('text'),
                })

        return promotions

    def _parse_conditional(self, text: str) -> Dict:
        condition = {}

        threshold_match = re.search(r'满(\d+(?:\.\d+)?)', text)
        if threshold_match:
            condition['threshold'] = float(threshold_match.group(1))

        discount_match = re.search(r'(?:减|省|优惠)(\d+(?:\.\d+)?)', text)
        if discount_match:
            condition['discount'] = float(discount_match.group(1))

        percent_match = re.search(r'(\d+)%?折扣|(\d+)% off', text)
        if percent_match:
            for g in percent_match.groups():
                if g:
                    condition['discount_percent'] = float(g) / 100
                    break

        condition['text'] = text[:100]
        return condition

    def _detect_free_gift(self, text: str, product_data: Dict) -> List[Dict]:
        promotions = []
        patterns = self.cross_promo_keywords['free_gift']

        for pattern in patterns:
            if re.search(pattern, text):
                gift_desc = self._extract_gift_description(text)
                promotions.append({
                    'promo_type': 'free_gift',
                    'trigger_product': product_data.get('product_id'),
                    'trigger_name': product_data.get('name'),
                    'source': product_data.get('source'),
                    'gift_description': gift_desc,
                })

        return promotions

    def _extract_gift_description(self, text: str) -> str:
        patterns = [
            r'赠品([^，。！,!]+)',
            r'赠送([^，。！,!]+)',
            r'gift[^.]*',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip() if len(m.groups()) > 0 else m.group(0).strip()
        return ''

    def _detect_cross_price_relation(self, product: Dict, related_products: List[Dict]) -> List[Dict]:
        promotions = []
        main_price = product.get('current_price')

        if not main_price or not related_products:
            return promotions

        for related in related_products:
            rel_price = related.get('current_price')
            rel_name = related.get('name', '')
            rel_id = related.get('product_id')

            if not rel_price:
                continue

            combined_patterns = [r'一起买', r'组合购买', r'bundle', r'套餐']
            for pat in combined_patterns:
                if re.search(pat, rel_name, re.IGNORECASE):
                    promotions.append({
                        'promo_type': 'cross_product_discount',
                        'trigger_product': product.get('product_id'),
                        'trigger_name': product.get('name'),
                        'source': product.get('source'),
                        'related_product_id': rel_id,
                        'related_product_name': rel_name,
                        'main_price': main_price,
                        'related_price': rel_price,
                        'total_individual': main_price + rel_price,
                        'bundle_price': None,
                        'potential_savings': None,
                    })

        return promotions

    def analyze_cross_promotion_impact(self, promotions: List[Dict]) -> Dict:
        if not promotions:
            return {'total': 0, 'by_type': {}, 'estimated_savings': 0}

        by_type = defaultdict(int)
        total_savings = 0
        for promo in promotions:
            ptype = promo.get('promo_type', 'unknown')
            by_type[ptype] += 1
            savings = promo.get('savings') or promo.get('discount_amount') or 0
            total_savings += savings

        return {
            'total': len(promotions),
            'by_type': dict(by_type),
            'estimated_savings': round(total_savings, 2),
        }


cross_promo_detector: Optional[CrossPromotionDetector] = None


def get_cross_promo_detector():
    global cross_promo_detector
    if cross_promo_detector is None:
        cross_promo_detector = CrossPromotionDetector()
    return cross_promo_detector