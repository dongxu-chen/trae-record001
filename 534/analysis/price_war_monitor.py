import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os


class PriceWarAlert:
    def __init__(self, alert_id, alert_type, severity, message, competitor_name,
                 competitor_price, our_price, timestamp, is_read=False):
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.competitor_name = competitor_name
        self.competitor_price = competitor_price
        self.our_price = our_price
        self.timestamp = timestamp
        self.is_read = is_read

    def to_dict(self):
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'competitor_name': self.competitor_name,
            'competitor_price': self.competitor_price,
            'our_price': self.our_price,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'is_read': self.is_read,
        }


class PriceWarMonitor:
    def __init__(self, storage_path=None, our_price=None, our_cost=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, 'data', 'price_war_alerts.json')
        self.storage_path = storage_path
        self.our_price = our_price
        self.our_cost = our_cost
        self.alerts = []
        self.alert_thresholds = {
            'critical': 0.85,
            'warning': 0.90,
            'info': 0.95,
        }
        self.price_drop_threshold = 0.05
        self._ensure_storage_dir()
        self._load_alerts()

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_alerts(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = [
                        PriceWarAlert(
                            **{k: datetime.fromisoformat(v) if 'timestamp' in k and isinstance(v, str) else v
                               for k, v in alert.items()}
                        ) for alert in data
                    ]
            except (json.JSONDecodeError, IOError):
                self.alerts = []

    def _save_alerts(self):
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([a.to_dict() for a in self.alerts], f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving alerts: {e}")

    def _generate_alert_id(self):
        return f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{np.random.randint(1000, 9999)}"

    def set_thresholds(self, critical=0.85, warning=0.90, info=0.95, price_drop=0.05):
        self.alert_thresholds = {
            'critical': critical,
            'warning': warning,
            'info': info,
        }
        self.price_drop_threshold = price_drop

    def check_competitor_prices(self, competitor_df):
        if self.our_price is None or competitor_df.empty:
            return []

        new_alerts = []
        for _, row in competitor_df.iterrows():
            comp_price = row['current_price']
            price_ratio = comp_price / self.our_price
            alert_type = None
            severity = None
            message = None

            if price_ratio <= self.alert_thresholds['critical']:
                severity = 'critical'
                alert_type = 'extreme_low_price'
                diff_pct = round((1 - price_ratio) * 100, 1)
                message = f"【严重预警】{row['competitor_name']}价格比本店低{diff_pct}%"
            elif price_ratio <= self.alert_thresholds['warning']:
                severity = 'warning'
                alert_type = 'low_price'
                diff_pct = round((1 - price_ratio) * 100, 1)
                message = f"【警告】{row['competitor_name']}价格比本店低{diff_pct}%"
            elif price_ratio <= self.alert_thresholds['info']:
                severity = 'info'
                alert_type = 'price_attention'
                diff_pct = round((1 - price_ratio) * 100, 1)
                message = f"【关注】{row['competitor_name']}价格比本店低{diff_pct}%"

            if alert_type:
                alert_exists = any(
                    a.competitor_name == row['competitor_name'] and
                    a.severity == severity and
                    (datetime.now() - (a.timestamp if isinstance(a.timestamp, datetime)
                                       else datetime.fromisoformat(a.timestamp))).total_seconds() < 3600
                    for a in self.alerts
                )

                if not alert_exists:
                    alert = PriceWarAlert(
                        alert_id=self._generate_alert_id(),
                        alert_type=alert_type,
                        severity=severity,
                        message=message,
                        competitor_name=row['competitor_name'],
                        competitor_price=comp_price,
                        our_price=self.our_price,
                        timestamp=datetime.now(),
                        is_read=False,
                    )
                    new_alerts.append(alert)
                    self.alerts.append(alert)

        if new_alerts:
            self._save_alerts()

        return new_alerts

    def detect_price_drop_war(self, competitor_df, history_df=None):
        if history_df is None or self.our_price is None:
            return []

        drop_alerts = []
        recent_prices = {}

        for _, row in history_df.iterrows():
            source = row['source']
            if source != '本店':
                if source not in recent_prices:
                    recent_prices[source] = []
                recent_prices[source].append((row['date'], row['price']))

        for source, prices in recent_prices.items():
            if len(prices) >= 2:
                prices.sort(key=lambda x: x[0])
                old_price = prices[-2][1]
                new_price = prices[-1][1]
                drop_pct = (old_price - new_price) / old_price if old_price > 0 else 0

                if drop_pct >= self.price_drop_threshold:
                    alert = PriceWarAlert(
                        alert_id=self._generate_alert_id(),
                        alert_type='price_drop',
                        severity='warning' if drop_pct >= 0.1 else 'info',
                        message=f"【降价预警】{source}在短期内降价{round(drop_pct*100,1)}%",
                        competitor_name=source,
                        competitor_price=new_price,
                        our_price=self.our_price,
                        timestamp=datetime.now(),
                        is_read=False,
                    )
                    drop_alerts.append(alert)
                    self.alerts.append(alert)

        if drop_alerts:
            self._save_alerts()

        return drop_alerts

    def get_alerts(self, severity=None, unread_only=False, limit=50):
        filtered = self.alerts
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        if unread_only:
            filtered = [a for a in filtered if not a.is_read]

        filtered.sort(key=lambda x: x.timestamp if isinstance(x.timestamp, datetime)
                       else datetime.fromisoformat(x.timestamp), reverse=True)
        return filtered[:limit]

    def mark_as_read(self, alert_id):
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.is_read = True
                self._save_alerts()
                return True
        return False

    def mark_all_as_read(self):
        for alert in self.alerts:
            alert.is_read = True
        self._save_alerts()
        return True

    def get_alert_stats(self):
        total = len(self.alerts)
        unread = len([a for a in self.alerts if not a.is_read])
        critical = len([a for a in self.alerts if a.severity == 'critical'])
        warning = len([a for a in self.alerts if a.severity == 'warning'])
        info = len([a for a in self.alerts if a.severity == 'info'])
        last_24h = len([
            a for a in self.alerts
            if (datetime.now() - (a.timestamp if isinstance(a.timestamp, datetime)
                                  else datetime.fromisoformat(a.timestamp))).total_seconds() < 86400
        ])

        return {
            'total': total,
            'unread': unread,
            'critical': critical,
            'warning': warning,
            'info': info,
            'last_24h': last_24h,
        }

    def analyze_threat_level(self, competitor_df):
        if self.our_price is None or competitor_df.empty:
            return {'level': 'unknown', 'score': 0, 'description': '数据不足'}

        prices = competitor_df['current_price'].values
        avg_competitor = np.mean(prices)
        min_competitor = np.min(prices)

        price_gap_pct = (self.our_price - min_competitor) / self.our_price if self.our_price > 0 else 0
        below_count = np.sum(prices < self.our_price)
        below_ratio = below_count / len(prices)

        threat_score = 0
        threat_score += min(price_gap_pct * 3, 0.5)
        threat_score += below_ratio * 0.5

        if threat_score >= 0.7:
            level = 'extreme'
            desc = '极度危险 - 多个竞品价格大幅低于本店，必须立即响应'
        elif threat_score >= 0.5:
            level = 'high'
            desc = '高风险 - 部分竞品价格显著低于本店，建议跟进'
        elif threat_score >= 0.3:
            level = 'medium'
            desc = '中风险 - 存在低价竞品，需要关注'
        elif threat_score >= 0.1:
            level = 'low'
            desc = '低风险 - 价格竞争温和'
        else:
            level = 'safe'
            desc = '安全 - 本店价格具有竞争力'

        return {
            'level': level,
            'score': round(threat_score, 2),
            'description': desc,
            'below_count': int(below_count),
            'below_ratio': round(below_ratio * 100, 1),
            'min_competitor_price': round(min_competitor, 2),
            'avg_competitor_price': round(avg_competitor, 2),
        }
