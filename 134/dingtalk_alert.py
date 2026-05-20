import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from datetime import datetime
from config import Config

class DingTalkAlerter:
    def __init__(self):
        self.enabled = Config.DINGTALK_ENABLED
        self.webhook_url = Config.DINGTALK_WEBHOOK
        self.secret = Config.DINGTALK_SECRET
        self.at_mobiles = Config.DINGTALK_AT_MOBILES
        self.last_alert_time = {}
        self.alert_cooldown = 300
    
    def _generate_sign(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f"{timestamp}\n{self.secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    def _send_message(self, title, text, is_at_all=False):
        if not self.enabled:
            print("钉钉告警功能已禁用")
            return False
        
        if not self.webhook_url:
            print("未配置钉钉Webhook URL")
            return False
        
        try:
            timestamp, sign = self._generate_sign()
            url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            
            at_data = {}
            if is_at_all:
                at_data['isAtAll'] = True
            elif self.at_mobiles:
                at_data['atMobiles'] = self.at_mobiles
            
            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': text
                },
                'at': at_data
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, data=json.dumps(data), headers=headers, timeout=10)
            
            result = response.json()
            if result.get('errcode') == 0:
                print(f"钉钉告警发送成功: {title}")
                return True
            else:
                print(f"钉钉告警发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"钉钉告警发送异常: {e}")
            return False
    
    def _should_alert(self, alert_type):
        last_time = self.last_alert_time.get(alert_type, 0)
        current_time = time.time()
        if current_time - last_time >= self.alert_cooldown:
            self.last_alert_time[alert_type] = current_time
            return True
        return False
    
    def alert_deadlock(self, deadlock_data):
        if not self._should_alert('deadlock'):
            print("死锁告警在冷却期内，跳过")
            return False
        
        timestamp = deadlock_data.get('timestamp', datetime.now().isoformat())
        transactions = deadlock_data.get('transactions', [])
        
        txn_summary = []
        tables_involved = set()
        
        for i, txn in enumerate(transactions[:3], 1):
            txn_id = txn.get('transaction_id', 'unknown')
            thread_id = txn.get('thread_id', 'unknown')
            
            for hold in txn.get('holds', []):
                table = hold.get('table')
                if table and table != 'UNKNOWN':
                    tables_involved.add(table)
            
            waiting = txn.get('waiting_for')
            if waiting:
                table = waiting.get('table')
                if table and table != 'UNKNOWN':
                    tables_involved.add(table)
            
            txn_summary.append(f"- 事务{i}: ID={txn_id}, 线程={thread_id}")
        
        title = f"🔒 数据库死锁告警 ({len(transactions)}个事务)"
        
        text = f"""
# 🔒 数据库死锁告警

**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**死锁发生时间**: {timestamp}
**涉及事务数**: {len(transactions)}个
**涉及表**: {', '.join(tables_involved) if tables_involved else '未知'}

## 事务详情
{chr(10).join(txn_summary)}

## 解决方案建议
1. **立即检查**: 查看是否有长事务未提交或回滚
2. **分析SQL**: 检查涉及表的更新/删除SQL是否需要优化
3. **索引优化**: 确保相关表有合适的索引减少锁范围
4. **调整顺序**: 检查是否存在不同事务以相反顺序更新相同表
5. **降低隔离级别**: 如业务允许可考虑使用READ COMMITTED

## 紧急处理
- 如果影响较大，可考虑kill阻塞的事务线程
- 检查是否有批量操作在业务高峰期执行
"""
        
        return self._send_message(title, text, is_at_all=True)
    
    def alert_high_risk_prediction(self, prediction):
        if not self._should_alert('high_risk_prediction'):
            return False
        
        risk_level = prediction.get('risk_level', 'unknown')
        probability = prediction.get('probability', 0)
        features = prediction.get('features', {})
        
        if risk_level != 'high':
            return False
        
        title = f"🔮 死锁高风险预警 ({int(probability * 100)}%)"
        
        text = f"""
# 🔮 数据库死锁高风险预警

**预警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**风险等级**: 🔴 高风险
**预测概率**: {int(probability * 100)}%
**预测方法**: {prediction.get('method', 'unknown')}

## 风险因素
- 过去1小时死锁数: {features.get('recent_deadlock_count_1h', 0)}
- 过去6小时死锁数: {features.get('recent_deadlock_count_6h', 0)}
- 过去24小时死锁数: {features.get('recent_deadlock_count_24h', 0)}
- 高风险表数: {features.get('high_risk_table_count', 0)}
- 写操作比例: {int(features.get('update_delete_ratio', 0) * 100)}%

## 预防建议
1. **立即监控**: 加强数据库锁等待情况监控
2. **限流准备**: 考虑对高风险表进行写操作限流
3. **检查长事务**: 查看是否有长时间未提交的事务
4. **SQL优化**: 审查慢查询日志，优化高频更新SQL

## 建议措施
- 通知相关开发和运维人员关注
- 准备好DBA随时介入处理
- 考虑在业务低峰期进行预防性维护
"""
        
        return self._send_message(title, text, is_at_all=True)
    
    def alert_auto_kill(self, killed_threads, reason):
        if not self._should_alert('auto_kill'):
            return False
        
        title = f"⚡ 自动Kill事务告警 ({len(killed_threads)}个)"
        
        threads_text = chr(10).join([f"- 线程ID: {t}" for t in killed_threads])
        
        text = f"""
# ⚡ 自动Kill事务告警

**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**触发原因**: {reason}
**终止线程数**: {len(killed_threads)}个

## 已终止线程
{threads_text}

## 后续处理建议
1. 检查被终止事务对应的业务SQL
2. 优化相关SQL，减少长事务或锁冲突
3. 监控是否有后续类似问题发生
4. 评估是否需要调整自动Kill阈值
"""
        
        return self._send_message(title, text)
    
    def alert_slow_sql_correlation(self, deadlock, related_slow_queries):
        if not self._should_alert('slow_sql_correlation'):
            return False
        
        title = f"🐢 死锁-慢查询关联告警"
        
        slow_sql_summary = []
        for i, sq in enumerate(related_slow_queries[:5], 1):
            query = sq.get('slow_query', {})
            sql_preview = query.get('sql', '')[:100]
            exec_time = query.get('query_time', 0)
            slow_sql_summary.append(f"{i}. 耗时{exec_time:.2f}s: {sql_preview}...")
        
        text = f"""
# 🐢 死锁-慢查询关联告警

**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**关联慢查询数**: {len(related_slow_queries)}个

## 关联慢查询TOP5
{chr(10).join(slow_sql_summary)}

## 分析说明
检测到死锁前后有慢查询发生，这些慢查询可能是导致死锁的诱因：
1. 慢查询持有锁时间过长，增加锁冲突概率
2. 慢查询可能导致事务长时间未提交

## 建议
1. 优先优化这些关联的慢查询SQL
2. 检查是否需要添加索引
3. 考虑拆分复杂查询，减少锁持有时间
"""
        
        return self._send_message(title, text)
    
    def send_custom_alert(self, title, message, is_at_all=False):
        return self._send_message(title, message, is_at_all=is_at_all)
