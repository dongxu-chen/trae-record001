"""
价格欺诈检测模块
检测先涨后降、虚构原价、虚假折扣等价格欺诈行为
参考《价格法》《禁止价格欺诈行为的规定》
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from loguru import logger


class PriceFraudDetector:
    def __init__(self, config=None):
        if config is None:
            from config import ANALYSIS_CONFIG as config
        self.config = config
        self.fraud_window_days = config.get('fraud_window_days', 30)
        self.baseline_days = config.get('baseline_days', 7)
        self.min_rise_ratio = config.get('min_rise_ratio', 0.05)
        self.min_drop_ratio = config.get('min_drop_ratio', 0.10)
        self.min_original_price_deviation = config.get('min_original_price_deviation', 0.30)
        self.fake_discount_threshold = config.get('fake_discount_threshold', 0.50)
        self.short_term_window = config.get('short_term_window', 7)

    def detect(self, product_data: Dict, price_history: List[Dict]) -> List[Dict]:
        frauds = []

        if len(price_history) < 10:
            logger.debug(f"价格历史数据不足，无法检测价格欺诈")
            return frauds

        current_price = product_data.get('current_price')
        original_price = product_data.get('original_price')

        if current_price is None:
            return frauds

        prices = [p.get('price') for p in price_history if p.get('price') is not None]
        timestamps = [p.get('timestamp') for p in price_history if p.get('price') is not None]

        if len(prices) < 10:
            return frauds

        rise_drop = self._detect_rise_then_drop(prices, timestamps, current_price)
        if rise_drop:
            frauds.append(rise_drop)

        fake_original = self._detect_fake_original_price(current_price, original_price, prices)
        if fake_original:
            frauds.append(fake_original)

        fake_discount = self._detect_fake_discount(current_price, original_price, prices, timestamps)
        if fake_discount:
            frauds.append(fake_discount)

        price_manipulation = self._detect_price_manipulation(prices, timestamps)
        if price_manipulation:
            frauds.append(price_manipulation)

        return frauds

    def _detect_rise_then_drop(self, prices: List[float], timestamps: List, current_price: float) -> Optional[Dict]:
        if len(prices) < 20:
            return None

        recent_prices = prices[-self.fraud_window_days * 4:] if len(prices) >= self.fraud_window_days * 4 else prices
        n = len(recent_prices)

        if n < 10:
            return None

        avg_price = sum(recent_prices) / len(recent_prices)

        if avg_price == 0:
            return None

        max_price = max(recent_prices)
        min_price = min(recent_prices)
        max_idx = recent_prices.index(max_price)

        max_ratio = (max_price - avg_price) / avg_price
        min_ratio = (min_price - avg_price) / avg_price

        if max_ratio >= self.min_rise_ratio and min_ratio <= -self.min_drop_ratio:
            if max_idx < n * 0.7:
                post_max_prices = recent_prices[max_idx:]
                post_max_avg = sum(post_max_prices) / len(post_max_prices)
                post_max_drop = (post_max_avg - max_price) / max_price

                if post_max_drop <= -self.min_drop_ratio:
                    if current_price <= post_max_avg:
                        severity = 'high'
                        if abs(post_max_drop) > 0.3:
                            severity = 'critical'

                        return {
                            'fraud_type': 'rise_then_drop',
                            'severity': severity,
                            'description': '疑似先涨后降价格欺诈',
                            'detail': (
                                f"在检测周期内价格先上涨至 ¥{max_price:.2f} "
                                f"(较均价上涨 {max_ratio * 100:.1f}%)，"
                                f"后下跌至 ¥{min_price:.2f} "
                                f"(较最高价下跌 {((min_price - max_price) / max_price) * 100:.1f}%)"
                            ),
                            'baseline_price': avg_price,
                            'peak_price': max_price,
                            'trough_price': min_price,
                            'current_price': current_price,
                            'rise_ratio': round(max_ratio, 4),
                            'drop_ratio': round(post_max_drop, 4),
                        }

        return None

    def _detect_fake_original_price(self, current_price: float, original_price: Optional[float], prices: List[float]) -> Optional[Dict]:
        if original_price is None or original_price == 0:
            return None

        if current_price >= original_price:
            return None

        historical_max = max(prices)
        historical_avg = sum(prices) / len(prices)

        if original_price > historical_max * (1 + self.min_original_price_deviation):
            claimed_discount = (original_price - current_price) / original_price
            actual_discount = (historical_avg - current_price) / historical_avg if historical_avg > 0 else 0

            deviation = (original_price - historical_max) / historical_max if historical_max > 0 else 0

            severity = 'high'
            if deviation > 0.5:
                severity = 'critical'

            return {
                'fraud_type': 'fake_original_price',
                'severity': severity,
                'description': '疑似虚构原价价格欺诈',
                'detail': (
                    f"标注原价 ¥{original_price:.2f}，"
                    f"但历史最高价仅 ¥{historical_max:.2f}，"
                    f"历史均价 ¥{historical_avg:.2f}，"
                    f"虚构幅度达 {deviation * 100:.1f}%"
                ),
                'claimed_original': original_price,
                'historical_max': historical_max,
                'historical_avg': historical_avg,
                'current_price': current_price,
                'deviation_ratio': round(deviation, 4),
                'claimed_discount': round(claimed_discount, 4),
                'actual_discount': round(actual_discount, 4),
            }

        return None

    def _detect_fake_discount(self, current_price: float, original_price: Optional[float], prices: List[float], timestamps: List) -> Optional[Dict]:
        if original_price is None or original_price == 0:
            return None

        if len(prices) < 14:
            return None

        short_term_prices = prices[-self.short_term_window * 4:] if len(prices) >= self.short_term_window * 4 else prices
        short_term_avg = sum(short_term_prices) / len(short_term_prices)

        if short_term_avg == 0:
            return None

        if current_price >= short_term_avg:
            return None

        claimed_discount = (original_price - current_price) / original_price
        actual_discount_from_recent = (short_term_avg - current_price) / short_term_avg

        if claimed_discount >= self.fake_discount_threshold:
            if actual_discount_from_recent < claimed_discount * 0.5:
                price_stability = self._calculate_price_stability(short_term_prices)

                severity = 'high'
                if price_stability > 0.9 and claimed_discount > 0.6:
                    severity = 'critical'

                return {
                    'fraud_type': 'fake_discount',
                    'severity': severity,
                    'description': '疑似虚假折扣价格欺诈',
                    'detail': (
                        f"宣称折扣 {claimed_discount * 100:.1f}%，"
                        f"但基于近{self.short_term_window}天均价的实际折扣仅为 {actual_discount_from_recent * 100:.1f}%"
                    ),
                    'claimed_original': original_price,
                    'current_price': current_price,
                    'short_term_avg': short_term_avg,
                    'claimed_discount': round(claimed_discount, 4),
                    'actual_discount': round(actual_discount_from_recent, 4),
                    'price_stability': round(price_stability, 4),
                }

        return None

    def _calculate_price_stability(self, prices: List[float]) -> float:
        if len(prices) < 2:
            return 1.0

        avg = sum(prices) / len(prices)
        if avg == 0:
            return 0.0

        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        coefficient_of_variation = std_dev / avg

        stability = max(0, 1 - coefficient_of_variation)
        return stability

    def _detect_price_manipulation(self, prices: List[float], timestamps: List) -> Optional[Dict]:
        if len(prices) < 14:
            return None

        window_size = min(7, len(prices) // 2)
        suspicious_patterns = []

        for i in range(window_size, len(prices)):
            window = prices[i - window_size:i]
            current = prices[i]
            avg_window = sum(window) / len(window)

            if avg_window == 0:
                continue

            change_ratio = (current - avg_window) / avg_window

            if abs(change_ratio) >= 0.15:
                suspicious_patterns.append({
                    'index': i,
                    'change_ratio': change_ratio,
                    'window_avg': avg_window,
                    'current': current,
                })

        if len(suspicious_patterns) >= 3:
            total_suspicious = len(suspicious_patterns)
            avg_change = sum(abs(p['change_ratio']) for p in suspicious_patterns) / total_suspicious

            severity = 'moderate'
            if total_suspicious >= 5 or avg_change > 0.25:
                severity = 'high'
            if total_suspicious >= 7:
                severity = 'critical'

            return {
                'fraud_type': 'price_manipulation',
                'severity': severity,
                'description': '疑似价格异常波动或人为操纵',
                'detail': (
                    f"在检测周期内发现 {total_suspicious} 次异常价格波动，"
                    f"平均波动幅度 {avg_change * 100:.1f}%"
                ),
                'suspicious_events': total_suspicious,
                'avg_change_ratio': round(avg_change, 4),
                'patterns': suspicious_patterns[:5],
            }

        return None

    def generate_compliance_report(self, product_data: Dict, frauds: List[Dict]) -> Dict:
        report = {
            'product_id': product_data.get('product_id'),
            'product_name': product_data.get('name'),
            'source': product_data.get('source'),
            'check_time': datetime.utcnow(),
            'compliance_level': 'compliant',
            'fraud_count': len(frauds),
            'frauds': frauds,
            'risk_score': 0,
            'recommendations': [],
        }

        if frauds:
            max_severity = max(f.get('severity', 'low') for f in frauds)
            severity_scores = {'low': 25, 'moderate': 50, 'high': 75, 'critical': 100}
            report['risk_score'] = severity_scores.get(max_severity, 50)

            if max_severity == 'critical':
                report['compliance_level'] = 'high_risk'
            elif max_severity == 'high':
                report['compliance_level'] = 'moderate_risk'
            else:
                report['compliance_level'] = 'low_risk'

            report['recommendations'] = self._generate_recommendations(frauds)

        return report

    def _generate_recommendations(self, frauds: List[Dict]) -> List[str]:
        recommendations = []
        fraud_types = {f.get('fraud_type') for f in frauds}

        if 'rise_then_drop' in fraud_types:
            recommendations.append('建议核实促销前价格历史，确保促销价格真实有效')

        if 'fake_original_price' in fraud_types:
            recommendations.append('建议核实标注的原价是否有历史销售记录支撑')

        if 'fake_discount' in fraud_types:
            recommendations.append('建议审查折扣宣传的真实性，避免虚构优惠幅度')

        if 'price_manipulation' in fraud_types:
            recommendations.append('建议关注价格波动模式，排查是否存在人为操纵迹象')

        if recommendations:
            recommendations.append('建议保留完整的价格历史记录和促销活动档案')

        return recommendations


fraud_detector: Optional[PriceFraudDetector] = None


def get_fraud_detector():
    global fraud_detector
    if fraud_detector is None:
        fraud_detector = PriceFraudDetector()
    return fraud_detector