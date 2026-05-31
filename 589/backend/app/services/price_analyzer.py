from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from decimal import Decimal
import numpy as np
import pandas as pd
from ..models.price import PlatformPrice, PriceHistory
from ..models.product import Product


class PriceAnalyzer:
    def __init__(self, db: Session, history_db: Session):
        self.db = db
        self.history_db = history_db

    def calculate_price_stats(self, product_id: str, days: int = 30) -> Dict:
        history = self.get_price_history(product_id, days)
        if not history:
            return {"lowest": 0, "highest": 0, "average": 0, "current": 0, "trend": 0}

        prices = [float(h.price) for h in history]
        current_price = prices[-1] if prices else 0

        return {
            "lowest": min(prices),
            "highest": max(prices),
            "average": sum(prices) / len(prices),
            "current": current_price,
            "trend": self.calculate_trend(prices),
            "volatility": np.std(prices) if len(prices) > 1 else 0,
            "is_lowest": current_price == min(prices)
        }

    def get_price_history(self, product_id: str, days: int = 30) -> List[PriceHistory]:
        start_date = datetime.now().date() - timedelta(days=days)
        return self.history_db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id,
            PriceHistory.record_date >= start_date
        ).order_by(PriceHistory.record_date).all()

    def calculate_trend(self, prices: List[float]) -> float:
        if len(prices) < 7:
            return 0.0
        recent = prices[-7:]
        previous = prices[-14:-7] if len(prices) >= 14 else prices[:7]
        recent_avg = sum(recent) / len(recent)
        prev_avg = sum(previous) / len(previous)
        return ((recent_avg - prev_avg) / prev_avg) * 100 if prev_avg > 0 else 0

    def predict_future_price(self, product_id: str, days_ahead: int = 7) -> Optional[float]:
        history = self.get_price_history(product_id, days=90)
        if len(history) < 14:
            return None

        df = pd.DataFrame([
            {"date": h.record_date, "price": float(h.price)}
            for h in history
        ])
        df["day"] = (df["date"] - df["date"].min()).dt.days

        x = df["day"].values
        y = df["price"].values

        if len(x) >= 2:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            future_day = x[-1] + days_ahead
            return float(p(future_day))
        return None

    def get_optimal_purchase_time(self, product_id: str) -> Dict:
        stats = self.calculate_price_stats(product_id, days=90)
        history = self.get_price_history(product_id, days=365)
        prediction = self.predict_future_price(product_id, days_ahead=14)

        prices = [float(h.price) for h in history] if history else []
        current_price = stats["current"]

        month_patterns = self.analyze_monthly_pattern(history) if history else {}

        recommendation = "buy_now"
        if prediction and prediction < current_price * 0.95:
            recommendation = "wait_for_drop"
        elif stats["is_lowest"]:
            recommendation = "buy_now"
        elif month_patterns.get("best_month") and current_price > stats["average"] * 1.05:
            recommendation = "wait_for_sale"

        return {
            "recommendation": recommendation,
            "confidence": self.calculate_confidence(prices),
            "predicted_price": prediction,
            "best_month": month_patterns.get("best_month"),
            "current_price": current_price,
            "savings_if_wait": current_price - prediction if prediction else 0
        }

    def analyze_monthly_pattern(self, history: List[PriceHistory]) -> Dict:
        if not history:
            return {}

        df = pd.DataFrame([
            {"date": h.record_date, "price": float(h.price), "platform": h.platform}
            for h in history
        ])
        df["month"] = df["date"].dt.month
        monthly_avg = df.groupby("month")["price"].mean()

        if not monthly_avg.empty:
            best_month = monthly_avg.idxmin()
            month_names = ["1月", "2月", "3月", "4月", "5月", "6月",
                          "7月", "8月", "9月", "10月", "11月", "12月"]
            return {
                "best_month": month_names[best_month - 1],
                "monthly_prices": monthly_avg.to_dict()
            }
        return {}

    def calculate_confidence(self, prices: List[float]) -> float:
        if len(prices) < 30:
            return len(prices) / 30 * 0.7
        return min(0.7 + (len(prices) - 30) / 100, 0.95)
