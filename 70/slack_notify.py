import os
import yaml
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


class SlackNotifier:
    def __init__(self):
        self._config = None

    def load_config(self) -> Dict[str, Any]:
        if self._config is None:
            config_file = os.path.join(os.path.dirname(__file__), "test_data.yaml")
            with open(config_file, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f) or {}
            self._config = full_config.get("slack", {})
        return self._config

    def _format_results(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        stats = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(results)
        }
        for r in results:
            status = r.get("status", "unknown")
            if status in stats:
                stats[status] += 1
        return stats

    def _build_message(self, results: List[Dict[str, Any]], report_path: Optional[str] = None) -> Dict[str, Any]:
        stats = self._format_results(results)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        passed = stats["passed"]
        failed = stats["failed"]
        skipped = stats["skipped"]
        total = stats["total"]

        if failed == 0:
            status_text = "✅ 测试通过"
            color = "good"
        elif failed > 0:
            status_text = "❌ 测试失败"
            color = "danger"
        else:
            status_text = "⚠️ 测试跳过"
            color = "warning"

        success_rate = (passed / total * 100) if total > 0 else 0

        fields = [
            {
                "title": "执行时间",
                "value": now,
                "short": True
            },
            {
                "title": "通过率",
                "value": f"{success_rate:.1f}%",
                "short": True
            },
            {
                "title": "通过",
                "value": f"✅ {passed}",
                "short": True
            },
            {
                "title": "失败",
                "value": f"❌ {failed}",
                "short": True
            }
        ]

        if skipped > 0:
            fields.append({
                "title": "跳过",
                "value": f"⏭ {skipped}",
                "short": True
            })

        fields.append({
            "title": "总计",
            "value": f"{total}",
            "short": True
        })

        if report_path:
            fields.append({
                "title": "测试报告",
                "value": report_path,
                "short": False
            })

        attachments = [
            {
                "color": color,
                "title": f"API 自动化测试 - {status_text}",
                "fields": fields
            }
        ]

        if failed > 0:
            failed_cases = [r for r in results if r.get("status") == "failed"]
            if failed_cases:
                failed_text = "\n".join([
                    f"• *{r.get('name')}*\n  错误: {r.get('error', '未知错误')}"
                    for r in failed_cases[:5]
                ])
                if len(failed_cases) > 5:
                    failed_text += f"\n... 还有 {len(failed_cases) - 5} 个失败"

                attachments.append({
                    "color": "danger",
                    "title": "失败用例详情",
                    "text": failed_text,
                    "mrkdwn_in": ["text"]
                })

        return {
            "attachments": attachments
        }

    def send_notification(
        self,
        results: List[Dict[str, Any]],
        report_path: Optional[str] = None,
        force: bool = False
    ) -> bool:
        config = self.load_config()
        enabled = config.get("enabled", False)
        webhook_url = config.get("webhook_url")
        channel = config.get("channel", "#test-alerts")
        username = config.get("username", "API Test Bot")

        if not enabled and not force:
            return False

        if not webhook_url:
            return False

        message = self._build_message(results, report_path)
        message["channel"] = channel
        message["username"] = username

        try:
            response = requests.post(
                webhook_url,
                data=json.dumps(message),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def send_custom_message(self, title: str, message: str, color: str = "good") -> bool:
        config = self.load_config()
        enabled = config.get("enabled", False)
        webhook_url = config.get("webhook_url")
        channel = config.get("channel", "#test-alerts")
        username = config.get("username", "API Test Bot")

        if not enabled or not webhook_url:
            return False

        payload = {
            "channel": channel,
            "username": username,
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message
                }
            ]
        }

        try:
            response = requests.post(
                webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False


slack_notifier = SlackNotifier()
