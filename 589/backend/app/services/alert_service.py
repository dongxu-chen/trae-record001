from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from ..models.alert import PriceAlert, User
from ..models.price import PlatformPrice
from ..schemas.alert import PriceAlertCreate
from .price_analyzer import PriceAnalyzer

load_dotenv()


class AlertService:
    def __init__(self, db: Session, history_db: Session, sio=None):
        self.db = db
        self.history_db = history_db
        self.sio = sio
        self.analyzer = PriceAnalyzer(db, history_db)

    def create_alert(self, user_id: str, alert_data: PriceAlertCreate) -> PriceAlert:
        alert = PriceAlert(
            user_id=user_id,
            product_id=alert_data.product_id,
            platform=alert_data.platform,
            target_price=alert_data.target_price,
            notify_type=alert_data.notify_type,
            is_active=True,
            triggered=False
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_user_alerts(self, user_id: str, active_only: bool = True) -> List[PriceAlert]:
        query = self.db.query(PriceAlert).filter(PriceAlert.user_id == user_id)
        if active_only:
            query = query.filter(PriceAlert.is_active == True)
        return query.order_by(PriceAlert.created_at.desc()).all()

    def deactivate_alert(self, alert_id: str, user_id: str) -> bool:
        alert = self.db.query(PriceAlert).filter(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == user_id
        ).first()
        if alert:
            alert.is_active = False
            self.db.commit()
            return True
        return False

    def delete_alert(self, alert_id: str, user_id: str) -> bool:
        alert = self.db.query(PriceAlert).filter(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == user_id
        ).first()
        if alert:
            self.db.delete(alert)
            self.db.commit()
            return True
        return False

    def check_alerts(self) -> List[Dict]:
        active_alerts = self.db.query(PriceAlert).filter(
            PriceAlert.is_active == True,
            PriceAlert.triggered == False
        ).all()

        triggered = []
        for alert in active_alerts:
            current_price = self._get_current_price(alert.product_id, alert.platform)
            if current_price and current_price <= float(alert.target_price):
                result = self._trigger_alert(alert, current_price)
                if result:
                    triggered.append(result)

        return triggered

    def _get_current_price(self, product_id: str, platform: str) -> Optional[float]:
        price = self.db.query(PlatformPrice).filter(
            PlatformPrice.product_id == product_id,
            PlatformPrice.platform == platform,
            PlatformPrice.in_stock == True
        ).first()
        return float(price.price) if price else None

    def _trigger_alert(self, alert: PriceAlert, current_price: float) -> Optional[Dict]:
        try:
            alert.triggered = True
            self.db.commit()

            user = self.db.query(User).filter(User.id == alert.user_id).first()
            if not user:
                return None

            notification = {
                "alert_id": alert.id,
                "user_id": alert.user_id,
                "user_email": user.email,
                "product_id": alert.product_id,
                "platform": alert.platform,
                "target_price": float(alert.target_price),
                "current_price": current_price,
                "savings": float(alert.target_price) - current_price,
                "notify_type": alert.notify_type,
                "triggered_at": datetime.now().isoformat()
            }

            if self.sio:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.sio.emit(
                        f"price_alert_{alert.user_id}",
                        notification,
                        namespace="/alerts"
                    )
                )
                loop.close()

            if alert.notify_type == "email":
                self._send_email_alert(user, alert, current_price)

            return notification
        except Exception as e:
            print(f"Error triggering alert: {e}")
            return None

    def _send_email_alert(self, user: User, alert: PriceAlert, current_price: float):
        smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("EMAIL_PORT", 587))
        smtp_user = os.getenv("EMAIL_USER")
        smtp_password = os.getenv("EMAIL_PASSWORD")

        if not smtp_user or not smtp_password:
            print("Email credentials not configured")
            return

        subject = "降价提醒！您关注的商品达到目标价格"
        body = f"""
        <html>
        <body>
            <h2>🎉 降价提醒</h2>
            <p>您好 {user.nickname or user.email},</p>
            <p>您关注的商品已达到目标价格！</p>
            <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>目标价格：</strong>¥{alert.target_price:.2f}</p>
                <p><strong>当前价格：</strong><span style="color: #ef4444; font-size: 24px; font-weight: bold;">¥{current_price:.2f}</span></p>
                <p><strong>预计节省：</strong><span style="color: #10b981; font-weight: bold;">¥{float(alert.target_price) - current_price:.2f}</span></p>
                <p><strong>平台：</strong>{alert.platform}</p>
            </div>
            <p>立即前往购买，享受优惠！</p>
            <p>此为系统自动邮件，请勿直接回复。</p>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = user.email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

    def get_alert_stats(self, user_id: str) -> Dict:
        alerts = self.db.query(PriceAlert).filter(PriceAlert.user_id == user_id).all()
        active = [a for a in alerts if a.is_active]
        triggered = [a for a in alerts if a.triggered]

        total_savings = 0
        for alert in triggered:
            current = self._get_current_price(alert.product_id, alert.platform)
            if current:
                total_savings += (float(alert.target_price) - current)

        return {
            "total_alerts": len(alerts),
            "active_alerts": len(active),
            "triggered_alerts": len(triggered),
            "total_savings": total_savings
        }
