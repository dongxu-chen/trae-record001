"""
高级分析管道
价格预测、交叉促销识别、价格欺诈检测
"""
from loguru import logger

from config import ANALYSIS_CONFIG, ALERT_CONFIG
from database.models import (
    PriceHistory, PricePrediction, CrossPromotion,
    ComplianceCheck, Alert,
)
from analysis.price_predictor import get_predictor
from analysis.cross_promo import get_cross_promo_detector
from analysis.fraud_detector import get_fraud_detector


class AnalysisPipeline:
    def __init__(self):
        self.enable_prediction = ANALYSIS_CONFIG.get('enable_price_prediction', True)
        self.enable_cross_promo = ANALYSIS_CONFIG.get('enable_cross_promo', True)
        self.enable_fraud_detection = ANALYSIS_CONFIG.get('enable_fraud_detection', True)
        self.fraud_alert_severity = ANALYSIS_CONFIG.get('fraud_alert_severity', ['high', 'critical'])

        self.predictor = get_predictor() if self.enable_prediction else None
        self.cross_promo_detector = get_cross_promo_detector() if self.enable_cross_promo else None
        self.fraud_detector = get_fraud_detector() if self.enable_fraud_detection else None

    def process_item(self, item, spider):
        if not hasattr(item, 'keys') or 'product_id' not in item:
            return item

        product_id = item['product_id']

        try:
            price_history = PriceHistory.get_history(product_id)
            product_dict = dict(item)

            if self.enable_prediction and self.predictor:
                self._process_price_prediction(product_id, product_dict, price_history)

            if self.enable_cross_promo and self.cross_promo_detector:
                self._process_cross_promotion(product_id, product_dict)

            if self.enable_fraud_detection and self.fraud_detector:
                self._process_fraud_detection(product_id, product_dict, price_history)

        except Exception as e:
            logger.error(f"商品 {product_id} 高级分析失败: {e}")

        return item

    def _process_price_prediction(self, product_id, product_dict, price_history):
        prediction = self.predictor.predict(price_history)
        if not prediction:
            return

        prediction_data = {
            'product_id': product_id,
            'product_name': product_dict.get('name', ''),
            'source': product_dict.get('source', ''),
            'current_price': prediction['current_price'],
            'alert_level': prediction['alert_level'],
            'trend': prediction['trend'],
            'volatility': prediction['volatility'],
            'predictions': prediction['predictions'],
            'combined': prediction['combined'],
            'data_points': prediction['data_points'],
        }

        try:
            PricePrediction.insert(prediction_data)
            logger.debug(f"商品 {product_id} 价格预测已保存: {prediction['alert_level']}")

            self._check_prediction_alert(product_id, product_dict, prediction)

        except Exception as e:
            logger.error(f"价格预测保存失败: {e}")

    def _check_prediction_alert(self, product_id, product_dict, prediction):
        alert_level = prediction['alert_level']
        combined = prediction.get('combined', {})
        thresholds = ANALYSIS_CONFIG.get('prediction_alert_thresholds', {})

        if not ALERT_CONFIG.get('enable', True):
            return

        change_7d = combined.get('expected_change_7d', 0)
        next_7d_price = combined.get('next_7d', product_dict.get('current_price'))

        if alert_level == 'high_drop_expected':
            alert_data = {
                'alert_type': 'price_predicted_drop',
                'product_id': product_id,
                'product_name': product_dict.get('name', ''),
                'source': product_dict.get('source', ''),
                'current_price': product_dict.get('current_price'),
                'predicted_price': next_7d_price,
                'expected_change': change_7d,
                'message': (
                    f"预测价格将下跌 {abs(change_7d) * 100:.1f}%: "
                    f"{product_dict.get('name', product_id)} "
                    f"预计7天后价格 ¥{next_7d_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

        elif alert_level == 'high_rise_expected':
            alert_data = {
                'alert_type': 'price_predicted_rise',
                'product_id': product_id,
                'product_name': product_dict.get('name', ''),
                'source': product_dict.get('source', ''),
                'current_price': product_dict.get('current_price'),
                'predicted_price': next_7d_price,
                'expected_change': change_7d,
                'message': (
                    f"预测价格将上涨 {change_7d * 100:.1f}%: "
                    f"{product_dict.get('name', product_id)} "
                    f"预计7天后价格 ¥{next_7d_price}"
                ),
            }
            Alert.insert(alert_data)
            logger.warning(alert_data['message'])

        elif alert_level == 'moderate_drop_expected' and abs(change_7d) >= abs(thresholds.get('moderate_drop', -0.05)):
            alert_data = {
                'alert_type': 'price_predicted_moderate_drop',
                'product_id': product_id,
                'product_name': product_dict.get('name', ''),
                'source': product_dict.get('source', ''),
                'current_price': product_dict.get('current_price'),
                'predicted_price': next_7d_price,
                'expected_change': change_7d,
                'message': (
                    f"预测价格将小幅下跌 {abs(change_7d) * 100:.1f}%: "
                    f"{product_dict.get('name', product_id)}"
                ),
            }
            Alert.insert(alert_data)
            logger.info(alert_data['message'])

        elif alert_level == 'moderate_rise_expected' and change_7d >= thresholds.get('moderate_rise', 0.05):
            alert_data = {
                'alert_type': 'price_predicted_moderate_rise',
                'product_id': product_id,
                'product_name': product_dict.get('name', ''),
                'source': product_dict.get('source', ''),
                'current_price': product_dict.get('current_price'),
                'predicted_price': next_7d_price,
                'expected_change': change_7d,
                'message': (
                    f"预测价格将小幅上涨 {change_7d * 100:.1f}%: "
                    f"{product_dict.get('name', product_id)}"
                ),
            }
            Alert.insert(alert_data)
            logger.info(alert_data['message'])

    def _process_cross_promotion(self, product_id, product_dict):
        related_products = []
        promotions = self.cross_promo_detector.detect(product_dict, related_products)

        if not promotions:
            return

        for promo in promotions:
            promo['product_id'] = product_id
            try:
                CrossPromotion.insert(promo)
                logger.debug(f"交叉促销识别: {product_id} - {promo.get('promo_type')}")

                if promo.get('promo_type') == 'buy_x_get_y':
                    alert_data = {
                        'alert_type': 'cross_promotion',
                        'product_id': product_id,
                        'product_name': product_dict.get('name', ''),
                        'source': product_dict.get('source', ''),
                        'promo_type': promo.get('promo_type'),
                        'promo_detail': promo.get('detail', {}),
                        'message': (
                            f"发现交叉促销: {product_dict.get('name', product_id)} "
                            f"- {promo.get('matched_text', promo.get('promo_type'))}"
                        ),
                    }
                    Alert.insert(alert_data)
                    logger.warning(alert_data['message'])

            except Exception as e:
                logger.error(f"交叉促销保存失败: {e}")

    def _process_fraud_detection(self, product_id, product_dict, price_history):
        frauds = self.fraud_detector.detect(product_dict, price_history)

        if not frauds:
            report = {
                'product_id': product_id,
                'product_name': product_dict.get('name', ''),
                'source': product_dict.get('source', ''),
                'compliance_level': 'compliant',
                'fraud_count': 0,
                'frauds': [],
                'risk_score': 0,
                'recommendations': ['价格行为合规'],
            }
            try:
                ComplianceCheck.insert(report)
            except Exception as e:
                logger.error(f"合规检查保存失败: {e}")
            return

        report = self.fraud_detector.generate_compliance_report(product_dict, frauds)

        try:
            ComplianceCheck.insert(report)
            logger.warning(
                f"合规检查: {product_id} - "
                f"风险等级: {report['compliance_level']}, "
                f"风险分数: {report['risk_score']}"
            )

            self._check_fraud_alert(product_id, product_dict, report)

        except Exception as e:
            logger.error(f"合规检查保存失败: {e}")

    def _check_fraud_alert(self, product_id, product_dict, report):
        if not ALERT_CONFIG.get('enable', True):
            return

        frauds = report.get('frauds', [])
        for fraud in frauds:
            severity = fraud.get('severity', 'low')
            if severity in self.fraud_alert_severity:
                alert_data = {
                    'alert_type': 'price_fraud',
                    'product_id': product_id,
                    'product_name': product_dict.get('name', ''),
                    'source': product_dict.get('source', ''),
                    'fraud_type': fraud.get('fraud_type'),
                    'severity': severity,
                    'risk_score': report.get('risk_score'),
                    'message': (
                        f"疑似{fraud.get('description', '价格欺诈')}: "
                        f"{product_dict.get('name', product_id)} - "
                        f"{fraud.get('detail', '')}"
                    ),
                }
                Alert.insert(alert_data)
                logger.critical(alert_data['message'])


analysis_pipeline = None


def get_analysis_pipeline():
    global analysis_pipeline
    if analysis_pipeline is None:
        analysis_pipeline = AnalysisPipeline()
    return analysis_pipeline