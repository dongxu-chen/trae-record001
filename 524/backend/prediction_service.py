import numpy as np
from datetime import datetime, timedelta
from database import get_db, get_events_for_datetime
from sensor_simulator import _calculate_event_impact


class ARIMAPredictor:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self.phi = np.array([0.6, -0.2, 0.1])
        self.theta = np.array([0.4, 0.2])
        self.sigma = 1.5
        self.last_residuals = [0.0, 0.0]
        self.event_weight = 0.7

    async def _get_history(self, hours: int = 24) -> list[float]:
        db = await get_db()
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            async with db.execute(
                "SELECT available_spots FROM sensor_readings WHERE zone_id = ? AND timestamp > ? ORDER BY timestamp",
                (self.zone_id, cutoff),
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        finally:
            await db.close()

    def _arima_forecast(
        self, series: list[float], steps: int, event_factors: list[float] = None
    ) -> tuple[list[float], list[float]]:
        n = len(series)
        if n < 5:
            mean_val = np.mean(series) if series else 0
            result = []
            confs = []
            for i in range(steps):
                ef = event_factors[i] if event_factors else 1.0
                result.append(mean_val / ef)
                confs.append(0.3)
            return result, confs

        series_arr = np.array(series, dtype=float)
        demeaned = series_arr - np.mean(series_arr)

        forecasts = []
        confidences = []

        history = list(demeaned[-max(len(self.phi), len(self.theta) + 1):])
        residuals = list(self.last_residuals)

        for step in range(steps):
            ar_term = sum(
                self.phi[i] * history[-(i + 1)] if i < len(history) else 0
                for i in range(len(self.phi))
            )
            ma_term = sum(
                self.theta[i] * residuals[-(i + 1)] if i < len(residuals) else 0
                for i in range(len(self.theta))
            )
            forecast_val = ar_term + ma_term
            noise = np.random.normal(0, self.sigma)
            new_val = forecast_val + noise
            base_forecast = forecast_val + np.mean(series_arr)

            ef = event_factors[step] if event_factors else 1.0
            if ef > 1.0:
                adjusted = base_forecast * (1 - self.event_weight * (ef - 1))
            else:
                adjusted = base_forecast

            forecasts.append(adjusted)
            conf_step = max(0.1, 1.0 - 0.05 * step)
            if ef > 1.0:
                conf_step = max(0.1, conf_step * 0.75)
            confidences.append(conf_step)

            history.append(new_val)
            residuals.append(noise)
            if len(residuals) > len(self.theta) + 1:
                residuals = residuals[-(len(self.theta) + 1):]

        return forecasts, confidences

    def _calculate_event_factors(self, minutes: int) -> list[float]:
        steps = max(1, minutes // 5)
        factors = []
        now = datetime.now()
        for i in range(steps):
            target_time = now + timedelta(minutes=(i + 1) * 5)
            events_for_time = []
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    pass
            except RuntimeError:
                pass
            factors.append(1.0)
        return factors

    async def predict(self, minutes: int = 30) -> dict:
        series = await self._get_history(hours=24)
        steps = max(1, minutes // 5)

        active_events = []
        now = datetime.now()
        current_events = await get_events_for_datetime(now)
        for event in current_events:
            if self.zone_id in event["impact_zone_ids"].split(","):
                active_events.append({
                    "id": event["id"],
                    "title": event["title"],
                    "type": event["event_type"],
                    "factor": event["impact_factor"],
                })

        event_factors = []
        for i in range(steps):
            target_time = now + timedelta(minutes=(i + 1) * 5)
            events_future = await get_events_for_datetime(target_time)
            ef, _ = _calculate_event_impact(self.zone_id, target_time, events_future)
            event_factors.append(ef)

        forecasts, confidences = self._arima_forecast(series, steps, event_factors)

        predictions = []
        for i, (val, conf) in enumerate(zip(forecasts, confidences)):
            target_time = now + timedelta(minutes=(i + 1) * 5)
            predictions.append({
                "timestamp": target_time.isoformat(),
                "available_spots": max(0, round(val, 1)),
                "confidence": round(conf, 3),
                "event_impact": round(event_factors[i], 3) if event_factors[i] > 1.0 else None,
            })

        mae, rmse = await self._compute_accuracy(series)

        return {
            "zone_id": self.zone_id,
            "predictions": predictions,
            "model_type": "ARIMA(3,0,2)+EventFeature",
            "accuracy_metrics": {"mae": round(mae, 2), "rmse": round(rmse, 2)},
            "active_events": active_events,
        }

    async def _compute_accuracy(self, series: list[float]) -> tuple[float, float]:
        if len(series) < 10:
            return 0.0, 0.0
        split = int(len(series) * 0.8)
        train = series[:split]
        test = series[split:]
        if len(test) == 0:
            return 0.0, 0.0

        forecasts, _ = self._arima_forecast(train, len(test))
        min_len = min(len(forecasts), len(test))
        errors = [forecasts[i] - test[i] for i in range(min_len)]
        if not errors:
            return 0.0, 0.0
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(np.array(errors) ** 2)))
        return mae, rmse
