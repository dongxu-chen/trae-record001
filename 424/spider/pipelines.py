"""
Scrapy数据管道
处理爬取到的数据，存储到MongoDB，生成价格历史，检测告警
告警使用同比分析：比较一周前价格消除周期性影响
"""
import hashlib
from datetime import datetime, timedelta
from loguru import logger

from database.models import Product, PriceHistory, Alert, Promotion
from config import SPIDER_CONFIG, ALERT_CONFIG


class ProductPipeline:
    def process_item(self, item, spider):
        if hasattr(item, 'keys') and 'product_id' in item:
            product_data = dict(item)
            source = product_data.get('source', spider.name)

            if not product_data.get('product_id'):
                raw_id = f"{source}:{product_data.get('url', '')}"
                product_data['product_id'] = hashlib.md5(
                    raw_id.encode()
                ).hexdigest()

            product_data['source'] = source

            try:
                Product.upsert(product_data)
                logger.debug(f"商品数据已保存: {product_data['product_id']}")
            except Exception as e:
                logger.error(f"商品数据保存失败: {e}")

        return item


class PriceHistoryPipeline:
    def process_item(self, item, spider):
        if hasattr(item, 'keys') and 'product_id' in item and 'current_price' in item:
            price_data = {
                'product_id': item['product_id'],
                'source': item.get('source', spider.name),
                'price': item.get('current_price'),
                'original_price': item.get('original_price'),
                'currency': item.get('currency', 'CNY'),
                'in_stock': item.get('in_stock'),
                'is_on_promotion': item.get('is_on_promotion'),
                'promotion_info': item.get('promotion_info'),
            }

            try:
                PriceHistory.insert(price_data)
                logger.debug(
                    f"价格记录已保存: {item['product_id']} - "
                    f"{item.get('current_price')}"
                )
            except Exception as e:
                logger.error(f"价格记录保存失败: {e}")

        return item


class AlertPipeline:
    def __init__(self):
        self.alert_rules = ALERT_CONFIG.get('alert_rules', [])
        self.price_change_threshold = SPIDER_CONFIG.get(
            'price_change_threshold', 0.05
        )
        self.enable_yoy = ALERT_CONFIG.get('enable_yoy_analysis', True)
        self.yoy_days_back = ALERT_CONFIG.get('yoy_days_back', 7)
        self.yoy_tolerance = ALERT_CONFIG.get('yoy_tolerance_hours', 12)

    def process_item(self, item, spider):
        if not hasattr(item, 'keys') or 'product_id' not in item:
            return item

        product_id = item['product_id']
        current_price = item.get('current_price')

        try:
            if self.enable_yoy:
                self._check_yoy_price_change(product_id, item)
            else:
                latest = PriceHistory.get_latest(product_id)
                if latest and latest.get('price') is not None:
                    self._check_price_change(product_id, item, latest)

            self._check_promotion(product_id, item)
            self._check_stock(product_id, item)

        except Exception as e:
            logger.error(f"告警检测失败: {e}")

        return item

    def _check_yoy_price_change(self, product_id, item):
        if item.get('current_price') is None:
            return

        now = datetime.utcnow()
        target_date = now - timedelta(days=self.yoy_days_back)

        baseline_record = PriceHistory.get_price_at_date(
            product_id, target_date,
            tolerance_hours=self.yoy_tolerance,
        )

        if baseline_record is None or baseline_record.get('price') is None:
            latest = PriceHistory.get_latest(product_id)
            if latest and latest.get('price') is not None:
                logger.debug(
                    f"[{product_id}] 无 {self.yoy_days_back}天前数据，"
                    f"使用最近一次价格做对比"
                )
                self._check_price_change(product_id, item, latest, comparison_type='latest')
            return

        baseline_price = baseline_record['price']
        if baseline_price == 0:
            return

        current_price = item['current_price']
        change_ratio = (current_price - baseline_price) / baseline_price

        baseline_date_str = baseline_record['timestamp'].strftime('%Y-%m-%d %H:%M')

        drop_rule = next(
            (r for r in self.alert_rules if r['type'] == 'price_drop'), None
        )
        rise_rule = next(
            (r for r in self.alert_rules if r['type'] == 'price_rise'), None
        )

        if drop_rule and drop_rule.get('enabled') and change_ratio <= -abs(
            drop_rule.get('threshold', self.price_change_threshold)
        ):
            alert_data = {
                'alert_type': 'price_drop',
                'product_id': product_id,
                'product_name': item.get('name', ''),
                'source': item.get('source', ''),
                'old_price': baseline_price,
                'new_price': current_price,
                'change_ratio': round(change_ratio, 4),
                'comparison_type': f'yoy_{self.yoy_days_back}d',
                'baseline_date': baseline_date_str,
                'message': (
                    f"同比{self.yoy_days_back}天前下跌 {abs(change_ratio) * 100:.1f}%: "
                    f"{item.get('name', product_id)} "
                    f"({baseline_date_str}) ¥{baseline_price} -> ¥{current_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

        if rise_rule and rise_rule.get('enabled') and change_ratio >= abs(
            rise_rule.get('threshold', self.price_change_threshold)
        ):
            alert_data = {
                'alert_type': 'price_rise',
                'product_id': product_id,
                'product_name': item.get('name', ''),
                'source': item.get('source', ''),
                'old_price': baseline_price,
                'new_price': current_price,
                'change_ratio': round(change_ratio, 4),
                'comparison_type': f'yoy_{self.yoy_days_back}d',
                'baseline_date': baseline_date_str,
                'message': (
                    f"同比{self.yoy_days_back}天前上涨 {change_ratio * 100:.1f}%: "
                    f"{item.get('name', product_id)} "
                    f"({baseline_date_str}) ¥{baseline_price} -> ¥{current_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

    def _check_price_change(self, product_id, item, latest, comparison_type='latest'):
        if item.get('current_price') is None or latest.get('price') is None:
            return

        old_price = latest['price']
        new_price = item['current_price']

        if old_price == 0:
            return

        change_ratio = (new_price - old_price) / old_price

        drop_rule = next(
            (r for r in self.alert_rules if r['type'] == 'price_drop'), None
        )
        rise_rule = next(
            (r for r in self.alert_rules if r['type'] == 'price_rise'), None
        )

        if drop_rule and drop_rule.get('enabled') and change_ratio <= -abs(
            drop_rule.get('threshold', self.price_change_threshold)
        ):
            alert_data = {
                'alert_type': 'price_drop',
                'product_id': product_id,
                'product_name': item.get('name', ''),
                'source': item.get('source', ''),
                'old_price': old_price,
                'new_price': new_price,
                'change_ratio': round(change_ratio, 4),
                'comparison_type': comparison_type,
                'message': (
                    f"价格下跌 {abs(change_ratio) * 100:.1f}%: "
                    f"{item.get('name', product_id)} "
                    f"¥{old_price} -> ¥{new_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

        if rise_rule and rise_rule.get('enabled') and change_ratio >= abs(
            rise_rule.get('threshold', self.price_change_threshold)
        ):
            alert_data = {
                'alert_type': 'price_rise',
                'product_id': product_id,
                'product_name': item.get('name', ''),
                'source': item.get('source', ''),
                'old_price': old_price,
                'new_price': new_price,
                'change_ratio': round(change_ratio, 4),
                'comparison_type': comparison_type,
                'message': (
                    f"价格上涨 {change_ratio * 100:.1f}%: "
                    f"{item.get('name', product_id)} "
                    f"¥{old_price} -> ¥{new_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

    def _check_promotion(self, product_id, item):
        if not item.get('is_on_promotion'):
            return

        rule = next(
            (r for r in self.alert_rules if r['type'] == 'promotion'), None
        )
        if not rule or not rule.get('enabled'):
            return

        alert_data = {
            'alert_type': 'promotion',
            'product_id': product_id,
            'product_name': item.get('name', ''),
            'source': item.get('source', ''),
            'price': item.get('current_price'),
            'promotion_info': item.get('promotion_info', ''),
            'message': (
                f"促销活动: {item.get('name', product_id)} - "
                f"{item.get('promotion_info', '')}"
            ),
        }
        Alert.insert(alert_data)

        Promotion.upsert({
            'product_id': product_id,
            'product_name': item.get('name', ''),
            'source': item.get('source', ''),
            'price': item.get('current_price'),
            'original_price': item.get('original_price'),
            'promo_type': item.get('promotion_type', 'general'),
            'promo_info': item.get('promotion_info', ''),
            'active': True,
            'start_date': datetime.utcnow(),
        })

        logger.warning(alert_data['message'])

    def _check_stock(self, product_id, item):
        in_stock = item.get('in_stock')
        if in_stock is None:
            return

        rule = next(
            (r for r in self.alert_rules if r['type'] == 'stock_out'), None
        )
        if not rule or not rule.get('enabled'):
            return

        if not in_stock:
            alert_data = {
                'alert_type': 'stock_out',
                'product_id': product_id,
                'product_name': item.get('name', ''),
                'source': item.get('source', ''),
                'price': item.get('current_price'),
                'message': (
                    f"商品缺货: {item.get('name', product_id)}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])