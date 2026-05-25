import requests
import json
from datetime import datetime
import pandas as pd
from typing import List, Dict, Optional


class AlertNotifier:
    def __init__(self):
        self.wecom_webhook = None
        self.dingtalk_webhook = None
        self.alert_history = []
        self.min_alert_interval = 300

    def set_wecom_webhook(self, webhook_url):
        self.wecom_webhook = webhook_url

    def set_dingtalk_webhook(self, webhook_url, secret=None):
        self.dingtalk_webhook = webhook_url
        self.dingtalk_secret = secret

    def send_wecom_alert(self, title, content, mentioned_list=None, mentioned_mobile_list=None):
        if not self.wecom_webhook:
            return False, "未配置企业微信Webhook"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n\n{content}"
            }
        }

        if mentioned_list or mentioned_mobile_list:
            data["markdown"]["mentioned_list"] = mentioned_list or []
            data["markdown"]["mentioned_mobile_list"] = mentioned_mobile_list or []

        try:
            response = requests.post(self.wecom_webhook, json=data, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                self._record_alert('wecom', title, 'success')
                return True, "发送成功"
            else:
                self._record_alert('wecom', title, 'failed', result.get('errmsg'))
                return False, result.get('errmsg', '发送失败')
        except Exception as e:
            self._record_alert('wecom', title, 'error', str(e))
            return False, str(e)

    def send_dingtalk_alert(self, title, content, at_mobiles=None, is_at_all=False):
        if not self.dingtalk_webhook:
            return False, "未配置钉钉Webhook"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"# {title}\n\n{content}"
            },
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": is_at_all
            }
        }

        try:
            response = requests.post(self.dingtalk_webhook, json=data, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                self._record_alert('dingtalk', title, 'success')
                return True, "发送成功"
            else:
                self._record_alert('dingtalk', title, 'failed', result.get('errmsg'))
                return False, result.get('errmsg', '发送失败')
        except Exception as e:
            self._record_alert('dingtalk', title, 'error', str(e))
            return False, str(e)

    def _record_alert(self, platform, title, status, error_msg=None):
        self.alert_history.append({
            'time': datetime.now(),
            'platform': platform,
            'title': title,
            'status': status,
            'error': error_msg
        })

    def generate_anomaly_alert_content(self, asset_name, anomaly_date, anomaly_type,
                                       anomaly_score, attribution_result=None,
                                       is_systemic=False, involved_assets=None):
        type_names = {
            'flash_crash': '价格闪崩',
            'volatility_spike': '异常波动',
            'missing_data': '数据缺失',
            'timestamp_gap': '时间戳跳点',
            'anomaly': '一般异常'
        }

        alert_level = self._get_alert_level(anomaly_score, is_systemic)
        alert_icon = self._get_alert_icon(alert_level)

        content = []
        content.append(f"**告警级别**: {alert_icon} {alert_level.upper()}")
        content.append(f"**资产名称**: {asset_name}")
        content.append(f"**异常时间**: {anomaly_date.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**异常类型**: {type_names.get(anomaly_type, anomaly_type)}")
        content.append(f"**异常评分**: {anomaly_score:.2f}")

        if is_systemic and involved_assets:
            content.append(f"**系统性风险**: ✅ 多资产协同异常")
            content.append(f"**涉及资产**: {', '.join(involved_assets)}")

        if attribution_result:
            content.append("\n**异常归因**:")
            content.append(f"> {attribution_result.get('explanation', '无解释')}")
            content.append("\n**贡献因子**:")
            factors = attribution_result.get('factors', {})
            for factor, contrib in list(factors.items())[:3]:
                if contrib > 0.1:
                    factor_cn = self._get_factor_name_cn(factor)
                    content.append(f"- {factor_cn}: {contrib*100:.1f}%")

        content.append("\n---")
        content.append(f"*告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return alert_level, "\n".join(content)

    def _get_alert_level(self, score, is_systemic=False):
        if is_systemic or score > 3.0:
            return 'critical'
        elif score > 2.0:
            return 'high'
        elif score > 1.0:
            return 'medium'
        else:
            return 'low'

    def _get_alert_icon(self, level):
        icons = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        return icons.get(level, '⚪')

    def _get_factor_name_cn(self, factor):
        names = {
            'price_volatility': '价格波动率异常',
            'trend_deviation': '趋势偏离',
            'volume_spike': '成交量异常放大',
            'price_jump': '价格跳变',
            'prophet_residual': '模型预测残差',
            'seasonal_anomaly': '季节性异常'
        }
        return names.get(factor, factor)

    def send_anomaly_alert(self, asset_name, anomaly_date, anomaly_type,
                           anomaly_score, attribution_result=None,
                           is_systemic=False, involved_assets=None,
                           platforms=None):
        if platforms is None:
            platforms = ['wecom', 'dingtalk']

        title = f"异常检测告警 - {asset_name}"
        alert_level, content = self.generate_anomaly_alert_content(
            asset_name, anomaly_date, anomaly_type,
            anomaly_score, attribution_result,
            is_systemic, involved_assets
        )

        results = {}

        if 'wecom' in platforms and self.wecom_webhook:
            success, msg = self.send_wecom_alert(title, content)
            results['wecom'] = {'success': success, 'message': msg}

        if 'dingtalk' in platforms and self.dingtalk_webhook:
            success, msg = self.send_dingtalk_alert(title, content)
            results['dingtalk'] = {'success': success, 'message': msg}

        return alert_level, results

    def send_systemic_risk_alert(self, event_date, assets_involved, avg_score,
                                  severity, anomaly_types, platforms=None):
        title = "⚠️ 系统性风险预警"

        content = []
        content.append(f"**风险等级**: {self._get_alert_icon(severity)} {severity.upper()}")
        content.append(f"**事件时间**: {event_date.strftime('%Y-%m-%d')}")
        content.append(f"**涉及资产数**: {assets_involved} 个")
        content.append(f"**平均异常评分**: {avg_score:.2f}")
        content.append(f"**异常类型**: {', '.join(anomaly_types)}")
        content.append("\n**风险提示**: 多个资产同时出现异常，可能存在系统性风险，请密切关注市场变化。")
        content.append("\n---")
        content.append(f"*预警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        content_str = "\n".join(content)
        results = {}

        if platforms is None:
            platforms = ['wecom', 'dingtalk']

        if 'wecom' in platforms and self.wecom_webhook:
            success, msg = self.send_wecom_alert(title, content_str)
            results['wecom'] = {'success': success, 'message': msg}

        if 'dingtalk' in platforms and self.dingtalk_webhook:
            success, msg = self.send_dingtalk_alert(title, content_str)
            results['dingtalk'] = {'success': success, 'message': msg}

        return results

    def get_alert_history(self, limit=50):
        if not self.alert_history:
            return pd.DataFrame()

        df = pd.DataFrame(self.alert_history[-limit:])
        df['time'] = pd.to_datetime(df['time'])
        return df.sort_values('time', ascending=False)

    def test_webhook(self, platform='wecom'):
        title = "📢 测试消息"
        content = "这是一条测试消息，用于验证Webhook配置是否正确。\n\n"
        content += f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        if platform == 'wecom':
            return self.send_wecom_alert(title, content)
        elif platform == 'dingtalk':
            return self.send_dingtalk_alert(title, content)
        else:
            return False, "不支持的平台"
