import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np

from ..cloud_providers import BillingRecord
from ..config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """预测结果"""
    forecast_date: date
    forecast_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    method: str
    trend: str
    seasonality: List[float] = field(default_factory=list)


@dataclass
class ModelForecast:
    """单个模型的预测结果"""
    model_name: str
    forecasts: List[ForecastResult]
    metrics: Dict[str, float]
    weight: float = 1.0


@dataclass
class EnsembleForecast:
    """集成预测结果"""
    forecast_period: Dict[str, date]
    total_forecast: float
    lower_bound: float
    upper_bound: float
    confidence: float
    method: str
    individual_forecasts: List[ModelForecast]
    historical_data: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    recommendations: List[str]


class CostForecaster:
    """费用预测器 - 多算法集成预测"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.min_history_days = 14
        self.min_confidence = 0.6

    def forecast_next_month(
        self,
        records: List[BillingRecord],
    ) -> EnsembleForecast:
        """预测下月费用（多算法集成）"""
        daily_costs = self._prepare_daily_costs(records)

        if len(daily_costs) < self.min_history_days:
            return self._generate_simple_forecast(daily_costs)

        historical_series = np.array(list(daily_costs.values()))
        historical_dates = list(daily_costs.keys())

        model_forecasts = []

        if len(historical_series) >= 30:
            arima_forecast = self._arima_forecast(historical_series, 30)
            if arima_forecast:
                model_forecasts.append(arima_forecast)

        if len(historical_series) >= 14:
            ma_forecast = self._moving_average_forecast(historical_series, 30)
            model_forecasts.append(ma_forecast)

            es_forecast = self._exponential_smoothing_forecast(historical_series, 30)
            model_forecasts.append(es_forecast)

        if len(historical_series) >= 90:
            prophet_forecast = self._prophet_style_forecast(historical_series, historical_dates, 30)
            if prophet_forecast:
                model_forecasts.append(prophet_forecast)

        if not model_forecasts:
            return self._generate_simple_forecast(daily_costs)

        ensemble = self._ensemble_forecasts(model_forecasts, historical_series)
        ensemble.historical_data = {
            "days": len(historical_series),
            "start_date": historical_dates[0].isoformat(),
            "end_date": historical_dates[-1].isoformat(),
            "total_historical_cost": float(np.sum(historical_series)),
            "daily_avg": float(np.mean(historical_series)),
            "daily_std": float(np.std(historical_series)),
        }

        ensemble.trend_analysis = self._analyze_trend(historical_series)
        ensemble.recommendations = self._generate_forecast_recommendations(ensemble)

        return ensemble

    def _prepare_daily_costs(
        self,
        records: List[BillingRecord],
    ) -> Dict[date, float]:
        """准备每日费用数据"""
        daily_costs = defaultdict(float)
        for record in records:
            daily_costs[record.usage_start_date] += record.pretax_amount
        return dict(sorted(daily_costs.items()))

    def _generate_simple_forecast(
        self,
        daily_costs: Dict[date, float],
    ) -> EnsembleForecast:
        """生成简单预测（数据不足时使用）"""
        values = list(daily_costs.values())
        if not values:
            return EnsembleForecast(
                forecast_period={"start": date.today(), "end": date.today()},
                total_forecast=0.0,
                lower_bound=0.0,
                upper_bound=0.0,
                confidence=0.0,
                method="no_data",
                individual_forecasts=[],
                historical_data={},
                trend_analysis={},
                recommendations=["数据不足，无法生成准确预测"],
            )

        avg_daily = np.mean(values)
        total_forecast = avg_daily * 30
        std = np.std(values) if len(values) > 1 else avg_daily * 0.3

        start_date = date.today()
        end_date = start_date + timedelta(days=30)

        return EnsembleForecast(
            forecast_period={"start": start_date, "end": end_date},
            total_forecast=float(total_forecast),
            lower_bound=float(total_forecast - std * 30),
            upper_bound=float(total_forecast + std * 30),
            confidence=0.5,
            method="simple_average",
            individual_forecasts=[],
            historical_data={
                "days": len(values),
                "daily_avg": float(avg_daily),
                "daily_std": float(std),
            },
            trend_analysis={"trend": "unknown"},
            recommendations=["建议积累更多历史数据以提高预测准确性"],
        )

    def _moving_average_forecast(
        self,
        series: np.ndarray,
        horizon: int,
    ) -> ModelForecast:
        """移动平均预测"""
        forecasts = []
        last_date = date.today()

        window_sizes = [7, 14, 30]
        predictions = []

        for window in window_sizes:
            if len(series) >= window:
                ma = np.mean(series[-window:])
                predictions.append(ma)

        avg_prediction = np.mean(predictions) if predictions else np.mean(series[-7:])
        std = np.std(series[-7:]) if len(series) >= 7 else np.std(series)

        total_forecast = avg_prediction * horizon
        lower = (avg_prediction - std * 1.96) * horizon
        upper = (avg_prediction + std * 1.96) * horizon

        for i in range(horizon):
            forecasts.append(ForecastResult(
                forecast_date=last_date + timedelta(days=i),
                forecast_value=float(avg_prediction),
                lower_bound=float(avg_prediction - std * 1.96),
                upper_bound=float(avg_prediction + std * 1.96),
                confidence=0.7,
                method="moving_average",
                trend="stable",
            ))

        metrics = self._calculate_metrics(series, avg_prediction)

        return ModelForecast(
            model_name="Moving Average",
            forecasts=forecasts,
            metrics=metrics,
            weight=0.3,
        )

    def _exponential_smoothing_forecast(
        self,
        series: np.ndarray,
        horizon: int,
    ) -> ModelForecast:
        """指数平滑预测"""
        forecasts = []
        last_date = date.today()

        alphas = [0.1, 0.3, 0.5]
        smoothed_values = []

        for alpha in alphas:
            smoothed = self._simple_exp_smoothing(series, alpha)
            smoothed_values.append(smoothed[-1])

        prediction = np.mean(smoothed_values)
        std = np.std(series[-7:]) if len(series) >= 7 else np.std(series)

        total_forecast = prediction * horizon

        for i in range(horizon):
            forecasts.append(ForecastResult(
                forecast_date=last_date + timedelta(days=i),
                forecast_value=float(prediction),
                lower_bound=float(prediction - std * 1.96),
                upper_bound=float(prediction + std * 1.96),
                confidence=0.75,
                method="exponential_smoothing",
                trend="stable",
            ))

        metrics = self._calculate_metrics(series, prediction)

        return ModelForecast(
            model_name="Exponential Smoothing",
            forecasts=forecasts,
            metrics=metrics,
            weight=0.35,
        )

    def _simple_exp_smoothing(self, series: np.ndarray, alpha: float) -> np.ndarray:
        """简单指数平滑"""
        smoothed = np.zeros_like(series, dtype=float)
        smoothed[0] = series[0]
        for i in range(1, len(series)):
            smoothed[i] = alpha * series[i] + (1 - alpha) * smoothed[i - 1]
        return smoothed

    def _arima_forecast(
        self,
        series: np.ndarray,
        horizon: int,
    ) -> Optional[ModelForecast]:
        """简化的ARIMA风格预测"""
        try:
            forecasts = []
            last_date = date.today()

            diff_series = np.diff(series)
            mean_diff = np.mean(diff_series[-7:]) if len(diff_series) >= 7 else np.mean(diff_series)
            last_value = series[-1]

            trend_factor = 1.0
            if mean_diff > 0:
                trend_factor = 1.0 + abs(mean_diff) / last_value
            elif mean_diff < 0:
                trend_factor = 1.0 - abs(mean_diff) / last_value

            prediction = last_value * trend_factor
            std = np.std(series[-7:]) if len(series) >= 7 else np.std(series)

            for i in range(horizon):
                daily_pred = prediction * (trend_factor ** (i / horizon))
                forecasts.append(ForecastResult(
                    forecast_date=last_date + timedelta(days=i),
                    forecast_value=float(daily_pred),
                    lower_bound=float(daily_pred - std * 1.96),
                    upper_bound=float(daily_pred + std * 1.96),
                    confidence=0.8,
                    method="arima_style",
                    trend="upward" if trend_factor > 1 else "downward" if trend_factor < 1 else "stable",
                ))

            total_forecast = sum(f.forecast_value for f in forecasts)
            metrics = self._calculate_metrics(series, prediction)

            return ModelForecast(
                model_name="ARIMA Style",
                forecasts=forecasts,
                metrics=metrics,
                weight=0.2,
            )
        except Exception as e:
            logger.warning(f"ARIMA forecast failed: {e}")
            return None

    def _prophet_style_forecast(
        self,
        series: np.ndarray,
        dates: List[date],
        horizon: int,
    ) -> Optional[ModelForecast]:
        """Prophet风格预测（包含趋势和季节性）"""
        try:
            forecasts = []
            last_date = date.today()

            weekly_seasonality = self._detect_weekly_seasonality(series, dates)
            monthly_seasonality = self._detect_monthly_seasonality(series, dates)

            trend_slope = self._estimate_trend_slope(series)
            base_value = series[-1]

            for i in range(horizon):
                future_date = last_date + timedelta(days=i)
                day_of_week = future_date.weekday()
                day_of_month = future_date.day

                weekly_component = weekly_seasonality.get(day_of_week, 1.0)
                monthly_component = monthly_seasonality.get(day_of_month, 1.0)

                trend_component = 1.0 + (trend_slope * i / len(series))
                prediction = base_value * trend_component * weekly_component * monthly_component

                std = np.std(series[-7:]) if len(series) >= 7 else np.std(series)

                forecasts.append(ForecastResult(
                    forecast_date=future_date,
                    forecast_value=float(max(0, prediction)),
                    lower_bound=float(max(0, prediction - std * 1.96)),
                    upper_bound=float(prediction + std * 1.96),
                    confidence=0.85,
                    method="prophet_style",
                    trend="upward" if trend_slope > 0 else "downward" if trend_slope < 0 else "stable",
                    seasonality=[weekly_component, monthly_component],
                ))

            prediction = np.mean([f.forecast_value for f in forecasts[:7]])
            metrics = self._calculate_metrics(series, prediction)

            return ModelForecast(
                model_name="Prophet Style",
                forecasts=forecasts,
                metrics=metrics,
                weight=0.15,
            )
        except Exception as e:
            logger.warning(f"Prophet style forecast failed: {e}")
            return None

    def _detect_weekly_seasonality(
        self,
        series: np.ndarray,
        dates: List[date],
    ) -> Dict[int, float]:
        """检测周季节性"""
        if len(series) < 14:
            return {i: 1.0 for i in range(7)}

        day_costs = defaultdict(list)
        for i, d in enumerate(dates):
            day_costs[d.weekday()].append(series[i])

        overall_mean = np.mean(series)
        seasonality = {}
        for day in range(7):
            if day_costs[day]:
                seasonality[day] = np.mean(day_costs[day]) / overall_mean if overall_mean > 0 else 1.0
            else:
                seasonality[day] = 1.0

        return seasonality

    def _detect_monthly_seasonality(
        self,
        series: np.ndarray,
        dates: List[date],
    ) -> Dict[int, float]:
        """检测月季节性"""
        if len(series) < 60:
            return {i: 1.0 for i in range(1, 32)}

        day_costs = defaultdict(list)
        for i, d in enumerate(dates):
            day_costs[d.day].append(series[i])

        overall_mean = np.mean(series)
        seasonality = {}
        for day in range(1, 32):
            if day_costs[day]:
                seasonality[day] = np.mean(day_costs[day]) / overall_mean if overall_mean > 0 else 1.0
            else:
                seasonality[day] = 1.0

        return seasonality

    def _estimate_trend_slope(self, series: np.ndarray) -> float:
        """估计趋势斜率"""
        if len(series) < 2:
            return 0.0

        x = np.arange(len(series))
        slope = np.polyfit(x, series, 1)[0]
        return slope

    def _ensemble_forecasts(
        self,
        model_forecasts: List[ModelForecast],
        historical_series: np.ndarray,
    ) -> EnsembleForecast:
        """集成多个模型的预测结果"""
        total_weight = sum(m.weight for m in model_forecasts)
        weights = [m.weight / total_weight for m in model_forecasts]

        horizon = len(model_forecasts[0].forecasts)
        ensemble_forecasts = []
        last_date = date.today()

        for i in range(horizon):
            values = []
            lowers = []
            uppers = []
            confidences = []

            for j, model in enumerate(model_forecasts):
                if i < len(model.forecasts):
                    values.append(model.forecasts[i].forecast_value * weights[j])
                    lowers.append(model.forecasts[i].lower_bound * weights[j])
                    uppers.append(model.forecasts[i].upper_bound * weights[j])
                    confidences.append(model.forecasts[i].confidence * weights[j])

            ensemble_forecasts.append(ForecastResult(
                forecast_date=last_date + timedelta(days=i),
                forecast_value=float(sum(values)),
                lower_bound=float(sum(lowers)),
                upper_bound=float(sum(uppers)),
                confidence=float(sum(confidences)),
                method="ensemble",
                trend="stable",
            ))

        total_forecast = sum(f.forecast_value for f in ensemble_forecasts)
        total_lower = sum(f.lower_bound for f in ensemble_forecasts)
        total_upper = sum(f.upper_bound for f in ensemble_forecasts)
        avg_confidence = np.mean([f.confidence for f in ensemble_forecasts])

        start_date = date.today()
        end_date = start_date + timedelta(days=horizon)

        return EnsembleForecast(
            forecast_period={"start": start_date, "end": end_date},
            total_forecast=float(total_forecast),
            lower_bound=float(max(0, total_lower)),
            upper_bound=float(total_upper),
            confidence=float(min(0.95, avg_confidence)),
            method="ensemble",
            individual_forecasts=model_forecasts,
            historical_data={},
            trend_analysis={},
            recommendations=[],
        )

    def _calculate_metrics(self, series: np.ndarray, prediction: float) -> Dict[str, float]:
        """计算预测指标"""
        if len(series) < 2:
            return {"mae": 0.0, "rmse": 0.0, "mape": 0.0}

        errors = series - prediction
        mae = np.mean(np.abs(errors))
        rmse = np.sqrt(np.mean(errors ** 2))
        mape = np.mean(np.abs(errors / series)) * 100 if np.all(series > 0) else 0.0

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
        }

    def _analyze_trend(self, series: np.ndarray) -> Dict[str, Any]:
        """分析历史趋势"""
        if len(series) < 7:
            return {"trend": "insufficient_data"}

        recent_avg = np.mean(series[-7:])
        previous_avg = np.mean(series[-14:-7]) if len(series) >= 14 else np.mean(series[:-7])

        change_pct = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0.0

        slope = self._estimate_trend_slope(series)
        volatility = np.std(series) / np.mean(series) if np.mean(series) > 0 else 0

        if slope > 0 and change_pct > 5:
            trend = "upward"
        elif slope < 0 and change_pct < -5:
            trend = "downward"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_percentage": float(change_pct),
            "slope": float(slope),
            "volatility": float(volatility),
            "recent_7d_avg": float(recent_avg),
            "previous_7d_avg": float(previous_avg),
        }

    def _generate_forecast_recommendations(
        self,
        forecast: EnsembleForecast,
    ) -> List[str]:
        """根据预测生成建议"""
        recommendations = []

        trend = forecast.trend_analysis.get("trend", "stable")
        volatility = forecast.trend_analysis.get("volatility", 0)

        if trend == "upward":
            recommendations.append("费用呈上升趋势，建议关注成本增长的原因")
            change_pct = forecast.trend_analysis.get("change_percentage", 0)
            if change_pct > 20:
                recommendations.append(f"近期费用增长较快 ({change_pct:.1f}%)，建议立即检查异常支出")
        elif trend == "downward":
            recommendations.append("费用呈下降趋势，成本优化措施正在生效")
        else:
            recommendations.append("费用趋势稳定，继续保持当前成本控制策略")

        if volatility > 0.5:
            recommendations.append("费用波动性较大，建议分析波动原因")

        if forecast.confidence < 0.7:
            recommendations.append("预测置信度较低，建议结合实际情况进行判断")

        return recommendations

    def forecast_by_service(
        self,
        records: List[BillingRecord],
        top_n: int = 5,
    ) -> Dict[str, EnsembleForecast]:
        """按服务预测费用"""
        service_records = defaultdict(list)
        for record in records:
            service_records[record.service_name].append(record)

        service_costs = {
            service: sum(r.pretax_amount for r in recs)
            for service, recs in service_records.items()
        }
        top_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:top_n]

        forecasts = {}
        for service, _ in top_services:
            forecasts[service] = self.forecast_next_month(service_records[service])

        return forecasts

    def forecast_by_provider(
        self,
        records: List[BillingRecord],
    ) -> Dict[str, EnsembleForecast]:
        """按云厂商预测费用"""
        provider_records = defaultdict(list)
        for record in records:
            provider_records[record.provider].append(record)

        forecasts = {}
        for provider, recs in provider_records.items():
            forecasts[provider] = self.forecast_next_month(recs)

        return forecasts

    def ensemble_to_dict(self, forecast: EnsembleForecast) -> Dict[str, Any]:
        """将集成预测转换为字典"""
        return {
            "forecast_period": {
                "start": forecast.forecast_period["start"].isoformat(),
                "end": forecast.forecast_period["end"].isoformat(),
            },
            "total_forecast": forecast.total_forecast,
            "lower_bound": forecast.lower_bound,
            "upper_bound": forecast.upper_bound,
            "confidence": forecast.confidence,
            "method": forecast.method,
            "historical_data": forecast.historical_data,
            "trend_analysis": forecast.trend_analysis,
            "recommendations": forecast.recommendations,
            "daily_forecasts": [
                {
                    "date": f.forecast_date.isoformat(),
                    "forecast": f.forecast_value,
                    "lower": f.lower_bound,
                    "upper": f.upper_bound,
                    "confidence": f.confidence,
                }
                for f in forecast.individual_forecasts[0].forecasts if forecast.individual_forecasts else []
            ],
        }
