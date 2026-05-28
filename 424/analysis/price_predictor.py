"""
价格走势预测模块
使用移动平均、加权移动平均、线性回归等方法预测未来价格走势
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

from loguru import logger


class PricePredictor:
    def __init__(self, config=None):
        if config is None:
            from config import ANALYSIS_CONFIG as config
        self.config = config
        self.prediction_days = config.get('prediction_days', 7)
        self.min_data_points = config.get('min_data_points', 5)
        self.moving_avg_window = config.get('moving_avg_window', 7)
        self.trend_threshold = config.get('trend_threshold', 0.03)
        self.seasonality_days = config.get('seasonality_days', 7)

    def predict(self, price_history: List[dict]) -> Optional[Dict]:
        if len(price_history) < self.min_data_points:
            logger.debug(f"价格数据点不足，至少需要 {self.min_data_points} 个")
            return None

        prices = [p.get('price') for p in price_history if p.get('price') is not None]
        timestamps = [p.get('timestamp') for p in price_history if p.get('price') is not None]

        if len(prices) < self.min_data_points:
            return None

        prices = [float(p) for p in prices]

        last_price = prices[-1]
        last_timestamp = timestamps[-1] if isinstance(timestamps[-1], datetime) else datetime.utcnow()

        predictions = {
            'current_price': last_price,
            'last_update': last_timestamp,
            'data_points': len(prices),
            'predictions': {},
            'trend': None,
            'volatility': None,
        }

        ma_pred = self._moving_average_prediction(prices)
        if ma_pred:
            predictions['predictions']['moving_average'] = ma_pred

        wma_pred = self._weighted_moving_average_prediction(prices)
        if wma_pred:
            predictions['predictions']['weighted_moving_average'] = wma_pred

        lr_pred = self._linear_regression_prediction(prices, timestamps)
        if lr_pred:
            predictions['predictions']['linear_regression'] = lr_pred

        predictions['trend'] = self._detect_trend(prices, timestamps)
        predictions['volatility'] = self._calculate_volatility(prices)

        predictions['combined'] = self._combine_predictions(predictions['predictions'], last_price)

        predictions['alert_level'] = self._determine_alert_level(predictions['combined'], last_price)

        return predictions

    def _moving_average_prediction(self, prices: List[float]) -> Optional[Dict]:
        if len(prices) < self.moving_avg_window:
            return None

        window = min(self.moving_avg_window, len(prices))
        recent_prices = prices[-window:]
        ma_value = sum(recent_prices) / len(recent_prices)

        trend = self._calculate_recent_trend(prices)
        predicted_prices = []
        for day in range(1, self.prediction_days + 1):
            predicted = ma_value + (trend * day)
            predicted_prices.append({
                'day': day,
                'price': round(predicted, 2),
            })

        return {
            'ma_value': round(ma_value, 2),
            'trend': round(trend, 2),
            'forecast': predicted_prices,
            'next_1d': predicted_prices[0]['price'] if predicted_prices else None,
            'next_7d': predicted_prices[-1]['price'] if predicted_prices else None,
        }

    def _weighted_moving_average_prediction(self, prices: List[float]) -> Optional[Dict]:
        if len(prices) < self.moving_avg_window:
            return None

        window = min(self.moving_avg_window, len(prices))
        recent_prices = prices[-window:]
        weights = list(range(1, window + 1))
        wma_value = sum(p * w for p, w in zip(recent_prices, weights)) / sum(weights)

        trend = self._calculate_recent_trend(prices, weighted=True)
        predicted_prices = []
        for day in range(1, self.prediction_days + 1):
            predicted = wma_value + (trend * day)
            predicted_prices.append({
                'day': day,
                'price': round(predicted, 2),
            })

        return {
            'wma_value': round(wma_value, 2),
            'trend': round(trend, 2),
            'forecast': predicted_prices,
            'next_1d': predicted_prices[0]['price'] if predicted_prices else None,
            'next_7d': predicted_prices[-1]['price'] if predicted_prices else None,
        }

    def _linear_regression_prediction(self, prices: List[float], timestamps: List) -> Optional[Dict]:
        if len(prices) < self.min_data_points:
            return None

        n = len(prices)
        x = list(range(n))
        y = prices

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = (n * sum_x2 - sum_x ** 2)
        if denominator == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        predicted_prices = []
        for day in range(1, self.prediction_days + 1):
            predicted = intercept + slope * (n + day - 1)
            predicted_prices.append({
                'day': day,
                'price': round(predicted, 2),
            })

        r_squared = self._calculate_r_squared(x, y, slope, intercept)

        return {
            'slope': round(slope, 4),
            'intercept': round(intercept, 2),
            'r_squared': round(r_squared, 4),
            'forecast': predicted_prices,
            'next_1d': predicted_prices[0]['price'] if predicted_prices else None,
            'next_7d': predicted_prices[-1]['price'] if predicted_prices else None,
        }

    def _calculate_r_squared(self, x: List[float], y: List[float], slope: float, intercept: float) -> float:
        y_mean = sum(y) / len(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
        if ss_tot == 0:
            return 1.0
        return 1 - (ss_res / ss_tot)

    def _calculate_recent_trend(self, prices: List[float], weighted: bool = False) -> float:
        if len(prices) < 3:
            return 0.0

        window = min(7, len(prices))
        recent = prices[-window:]

        if weighted:
            weights = list(range(1, len(recent) + 1))
            weighted_avg_first = sum(p * w for p, w in zip(recent[:3], weights[:3])) / sum(weights[:3])
            weighted_avg_last = sum(p * w for p, w in zip(recent[-3:], weights[-3:])) / sum(weights[-3:])
            return (weighted_avg_last - weighted_avg_first) / 3
        else:
            avg_first = sum(recent[:3]) / 3
            avg_last = sum(recent[-3:]) / 3
            return (avg_last - avg_first) / 3

    def _detect_trend(self, prices: List[float], timestamps: List) -> Dict:
        if len(prices) < 5:
            return {'direction': 'unknown', 'strength': 0}

        n = len(prices)
        x = list(range(n))
        y = prices

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = (n * sum_x2 - sum_x ** 2)
        if denominator == 0:
            return {'direction': 'unknown', 'strength': 0}

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        avg_price = sum(prices) / len(prices)
        if avg_price == 0:
            return {'direction': 'unknown', 'strength': 0}

        relative_change = (slope * (n - 1)) / avg_price

        direction = 'stable'
        if relative_change > self.trend_threshold:
            direction = 'rising'
        elif relative_change < -self.trend_threshold:
            direction = 'falling'

        strength = min(abs(relative_change) * 10, 1.0)

        return {
            'direction': direction,
            'strength': round(strength, 2),
            'slope': round(slope, 4),
            'relative_change': round(relative_change, 4),
        }

    def _calculate_volatility(self, prices: List[float]) -> Dict:
        if len(prices) < 3:
            return {'value': 0, 'level': 'low'}

        avg_price = sum(prices) / len(prices)
        if avg_price == 0:
            return {'value': 0, 'level': 'low'}

        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        volatility = std_dev / avg_price

        level = 'low'
        if volatility > 0.1:
            level = 'high'
        elif volatility > 0.05:
            level = 'medium'

        return {
            'value': round(volatility, 4),
            'level': level,
            'std_dev': round(std_dev, 2),
            'variance': round(variance, 2),
        }

    def _combine_predictions(self, predictions: Dict, last_price: float) -> Dict:
        components = []
        weights = []

        if 'linear_regression' in predictions and predictions['linear_regression']:
            lr = predictions['linear_regression']
            r_squared = lr.get('r_squared', 0)
            if r_squared > 0.5:
                components.append(lr)
                weights.append(r_squared * 0.5)

        if 'weighted_moving_average' in predictions and predictions['weighted_moving_average']:
            components.append(predictions['weighted_moving_average'])
            weights.append(0.3)

        if 'moving_average' in predictions and predictions['moving_average']:
            components.append(predictions['moving_average'])
            weights.append(0.2)

        if not components:
            return {
                'next_1d': last_price,
                'next_7d': last_price,
                'expected_change_1d': 0.0,
                'expected_change_7d': 0.0,
                'confidence': 0.0,
            }

        total_weight = sum(weights)
        if total_weight == 0:
            return {
                'next_1d': last_price,
                'next_7d': last_price,
                'expected_change_1d': 0.0,
                'expected_change_7d': 0.0,
                'confidence': 0.0,
            }

        next_1d = sum(c.get('next_1d', last_price) * w for c, w in zip(components, weights)) / total_weight
        next_7d = sum(c.get('next_7d', last_price) * w for c, w in zip(components, weights)) / total_weight

        change_1d = (next_1d - last_price) / last_price if last_price != 0 else 0
        change_7d = (next_7d - last_price) / last_price if last_price != 0 else 0

        return {
            'next_1d': round(next_1d, 2),
            'next_7d': round(next_7d, 2),
            'expected_change_1d': round(change_1d, 4),
            'expected_change_7d': round(change_7d, 4),
            'confidence': round(min(total_weight, 1.0), 2),
        }

    def _determine_alert_level(self, combined: Dict, last_price: float) -> str:
        if last_price == 0 or combined.get('confidence', 0) < 0.3:
            return 'normal'

        change_7d = combined.get('expected_change_7d', 0)

        if change_7d <= -0.10:
            return 'high_drop_expected'
        elif change_7d <= -0.05:
            return 'moderate_drop_expected'
        elif change_7d >= 0.10:
            return 'high_rise_expected'
        elif change_7d >= 0.05:
            return 'moderate_rise_expected'
        else:
            return 'stable'


predictor: Optional[PricePredictor] = None


def get_predictor():
    global predictor
    if predictor is None:
        predictor = PricePredictor()
    return predictor