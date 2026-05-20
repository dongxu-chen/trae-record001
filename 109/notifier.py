import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import logging

logger = logging.getLogger(__name__)


class DingTalkNotifier:
    def __init__(self, config):
        self.config = config['dingtalk']
        self.webhook_url = self.config['webhook_url']
        self.secret = self.config.get('secret')
        self.timestamp_validity = 3600

    def _validate_timestamp(self, timestamp):
        try:
            ts = int(timestamp)
            current_ts = int(round(time.time() * 1000))
            diff = abs(current_ts - ts) / 1000
            if diff > self.timestamp_validity:
                logger.warning(f"时间戳已过期，差值: {diff:.0f} 秒")
                return False
            return True
        except:
            return False

    def _generate_sign(self):
        if not self.secret:
            logger.warning("未配置钉钉secret，使用无签名模式")
            return None, None
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f"{timestamp}\n{self.secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        logger.info(f"生成钉钉签名，时间戳: {timestamp}")
        return timestamp, sign

    def send_message(self, title, content, is_success=True):
        try:
            timestamp, sign = self._generate_sign()
            url = self.webhook_url

            if timestamp and sign:
                if not self._validate_timestamp(timestamp):
                    logger.error("时间戳校验失败，重新生成签名")
                    timestamp, sign = self._generate_sign()
                url = f"{url}&timestamp={timestamp}&sign={sign}"
                logger.info("使用加签安全模式发送通知")

            status_text = "✅ 成功" if is_success else "❌ 失败"
            text_content = f"""# {title} {status_text}

{content}

*时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""

            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text_content
                },
                "at": {
                    "atMobiles": self.config.get('at_mobiles', []),
                    "isAtAll": self.config.get('at_all', False)
                }
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                logger.info("钉钉通知发送成功")
                return True
            elif result.get('errcode') == 310000:
                logger.error(f"签名校验失败: {result.get('errmsg')}")
                return False
            else:
                logger.error(f"钉钉通知发送失败: {result}")
                return False

        except Exception as e:
            logger.error(f"钉钉通知异常: {str(e)}")
            return False

    def send_backup_result(self, backup_files, upload_results, cleanup_results, verify_results=None):
        if verify_results is None:
            verify_results = []
        success_count = sum(1 for r in upload_results if r['success'])
        total_count = len(upload_results)
        verify_success = sum(1 for v in verify_results if v.get('success', False))
        verify_total = len(verify_results)

        content_parts = [f"## 备份统计",
                         f"- 备份文件数量: {len(backup_files)}",
                         f"- OSS上传成功: {success_count}/{total_count}",
                         f"- 备份验证成功: {verify_success}/{verify_total}",
                         f"- 清理文件: {len(cleanup_results)}个"]

        if backup_files:
            content_parts.append("\n## 备份文件列表")
            for f in backup_files:
                ftype = "📈 增量" if "binlog" in f or "incremental" in f else "📦 全量"
                size = os.path.getsize(f) / 1024 / 1024
                content_parts.append(f"- {os.path.basename(f)} ({size:.2f} MB) - {ftype}")

        if verify_results:
            content_parts.append("\n## 备份验证结果")
            for v in verify_results:
                status = "✅ 成功" if v.get('success') else "❌ 失败"
                content_parts.append(f"- {os.path.basename(v.get('file', ''))}: {status}, 表数量: {v.get('table_count', 0)}")

        if cleanup_results:
            content_parts.append("\n## 清理文件")
            for f in cleanup_results:
                content_parts.append(f"- {f}")

        content = "\n".join(content_parts)
        is_success = success_count == total_count and verify_success == verify_total and total_count > 0

        return self.send_message("数据库备份巡检", content, is_success)
