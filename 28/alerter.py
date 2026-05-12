import time
import hmac
import hashlib
import base64
import urllib.parse
import json
import logging
from typing import Dict, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, field
from stats import WindowStats

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)

@dataclass
class AlertThresholds:
    error_rate: float = 5.0
    five_hundred_rate: float = 1.0
    four_hundred_rate: float = 20.0
    qps_spike: float = 2.0

@dataclass
class AlertConfig:
    enabled: bool = True
    window_seconds: int = 60
    min_requests: int = 10
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    cooldown_seconds: int = 300

@dataclass
class DingtalkConfig:
    webhook: str = ""
    secret: str = ""
    at_mobiles: List[str] = field(default_factory=list)
    at_all: bool = False

class AlertManager:
    def __init__(
        self,
        alert_config: AlertConfig,
        dingtalk_config: Optional[DingtalkConfig] = None
    ):
        self.config = alert_config
        self.dingtalk_config = dingtalk_config or DingtalkConfig()
        self._last_alert_time: Dict[str, float] = {}
        self._alert_history: List[Dict] = []
        self._baseline_qps: Optional[float] = None
        self._baseline_samples: int = 0
    
    def _get_sign(self, timestamp: int) -> str:
        if not self.dingtalk_config.secret:
            return ""
        
        secret = self.dingtalk_config.secret
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign
    
    def _send_dingtalk(self, title: str, content: str) -> bool:
        if not HAS_REQUESTS:
            logger.warning("requests 库未安装，跳过钉钉通知")
            return False
        
        if not self.dingtalk_config.webhook:
            logger.warning("钉钉 webhook 未配置")
            return False
        
        timestamp = str(round(time.time() * 1000))
        sign = self._get_sign(int(timestamp))
        
        webhook_url = self.dingtalk_config.webhook
        if sign:
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        headers = {"Content-Type": "application/json"}
        
        at = {
            "atMobiles": self.dingtalk_config.at_mobiles,
            "isAtAll": self.dingtalk_config.at_all
        }
        
        markdown_text = f"""### {title}

{content}

---
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": markdown_text
            },
            "at": at
        }
        
        try:
            response = requests.post(
                webhook_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )
            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"钉钉报警发送成功: {title}")
                return True
            else:
                logger.error(f"钉钉报警发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"钉钉报警发送异常: {e}")
            return False
    
    def _should_alert(self, alert_type: str) -> bool:
        if not self.config.enabled:
            return False
        
        last_time = self._last_alert_time.get(alert_type, 0)
        cooldown_until = last_time + self.config.cooldown_seconds
        
        if time.time() < cooldown_until:
            return False
        
        return True
    
    def _record_alert(self, alert_type: str, details: Dict):
        self._last_alert_time[alert_type] = time.time()
        
        alert_record = {
            "type": alert_type,
            "time": datetime.now().isoformat(),
            "details": details
        }
        self._alert_history.append(alert_record)
        
        if len(self._alert_history) > 100:
            self._alert_history = self._alert_history[-100:]
    
    def _update_baseline(self, current_qps: float):
        if current_qps <= 0:
            return
        
        if self._baseline_qps is None:
            self._baseline_qps = current_qps
            self._baseline_samples = 1
        else:
            alpha = 0.1
            self._baseline_qps = (1 - alpha) * self._baseline_qps + alpha * current_qps
            self._baseline_samples += 1
    
    def check(self, window_stats: WindowStats, current_qps: float) -> List[Dict]:
        alerts = []
        
        if window_stats.total_requests < self.config.min_requests:
            return alerts
        
        thresholds = self.config.thresholds
        
        error_rate = window_stats.error_rate()
        five_rate = window_stats.five_hundred_rate()
        four_rate = window_stats.four_hundred_rate()
        
        self._update_baseline(current_qps)
        
        if error_rate >= thresholds.error_rate:
            if self._should_alert("high_error_rate"):
                alert_details = {
                    "error_rate": error_rate,
                    "threshold": thresholds.error_rate,
                    "total_requests": window_stats.total_requests,
                    "error_count": window_stats.error_count(),
                    "window_seconds": self.config.window_seconds
                }
                
                content = f"""
**错误率过高报警**

- 当前错误率: **{error_rate:.2f}%**
- 阈值: {thresholds.error_rate}%
- 窗口请求数: {window_stats.total_requests}
- 错误请求数: {window_stats.error_count()}
- 时间窗口: {self.config.window_seconds}秒
"""
                
                self._send_dingtalk("🚨 Nginx 错误率过高报警", content.strip())
                self._record_alert("high_error_rate", alert_details)
                alerts.append({"type": "high_error_rate", **alert_details})
        
        if five_rate >= thresholds.five_hundred_rate:
            if self._should_alert("high_5xx_rate"):
                alert_details = {
                    "five_hundred_rate": five_rate,
                    "threshold": thresholds.five_hundred_rate,
                    "total_requests": window_stats.total_requests,
                    "five_hundred_count": window_stats.total_5xx
                }
                
                content = f"""
**5xx 错误率过高报警**

- 当前 5xx 率: **{five_rate:.2f}%**
- 阈值: {thresholds.five_hundred_rate}%
- 窗口请求数: {window_stats.total_requests}
- 5xx 请求数: {window_stats.total_5xx}
"""
                
                self._send_dingtalk("🔴 Nginx 5xx 错误报警", content.strip())
                self._record_alert("high_5xx_rate", alert_details)
                alerts.append({"type": "high_5xx_rate", **alert_details})
        
        if four_rate >= thresholds.four_hundred_rate:
            if self._should_alert("high_4xx_rate"):
                alert_details = {
                    "four_hundred_rate": four_rate,
                    "threshold": thresholds.four_hundred_rate,
                    "total_requests": window_stats.total_requests,
                    "four_hundred_count": window_stats.total_4xx
                }
                
                content = f"""
**4xx 错误率过高警告**

- 当前 4xx 率: **{four_rate:.2f}%**
- 阈值: {thresholds.four_hundred_rate}%
- 窗口请求数: {window_stats.total_requests}
- 4xx 请求数: {window_stats.total_4xx}
"""
                
                self._send_dingtalk("🟡 Nginx 4xx 警告", content.strip())
                self._record_alert("high_4xx_rate", alert_details)
                alerts.append({"type": "high_4xx_rate", **alert_details})
        
        if (self._baseline_qps is not None and 
            self._baseline_samples >= 5 and
            current_qps > self._baseline_qps * thresholds.qps_spike):
            if self._should_alert("qps_spike"):
                alert_details = {
                    "current_qps": current_qps,
                    "baseline_qps": self._baseline_qps,
                    "spike_ratio": current_qps / self._baseline_qps,
                    "threshold": thresholds.qps_spike
                }
                
                content = f"""
**QPS 突增报警**

- 当前 QPS: **{current_qps:.2f}**
- 基线 QPS: {self._baseline_qps:.2f}
- 突增倍数: {alert_details['spike_ratio']:.2f}x
- 阈值: {thresholds.qps_spike}x
"""
                
                self._send_dingtalk("⚡ Nginx QPS 突增报警", content.strip())
                self._record_alert("qps_spike", alert_details)
                alerts.append({"type": "qps_spike", **alert_details})
        
        return alerts
    
    def get_alert_history(self) -> List[Dict]:
        return list(self._alert_history)
    
    def get_cooldown_status(self) -> Dict[str, Dict]:
        status = {}
        now = time.time()
        for alert_type, last_time in self._last_alert_time.items():
            remaining = int(max(0, last_time + self.config.cooldown_seconds - now))
            status[alert_type] = {
                "last_alert_time": datetime.fromtimestamp(last_time).strftime("%Y-%m-%d %H:%M:%S"),
                "cooldown_remaining_seconds": remaining
            }
        return status
