# ==========================================
# 健康检查 Reactor
# 实时监控主机健康状态，自动回滚
# ==========================================

{% set data = data.get('data', {}) %}
{% set minion_id = data.get('id', '') %}
{% set patch_id = data.get('patch_id', '') %}
{% set health_status = data.get('status', 'healthy') %}
{% set metrics = data.get('metrics', {}) %}

# 记录健康状态
store_health_status:
  runner.redis.set:
    - key: "health:{{ minion_id }}:{{ patch_id }}"
    - value: "{{ data | json }}"
    - expire: 86400

{% if health_status != 'healthy' %}
# 主机不健康，记录到异常列表
mark_unhealthy:
  runner.redis.sadd:
    - key: "patch:{{ patch_id }}:unhealthy"
    - value: "{{ minion_id }}"

# 计算不健康率
calculate_unhealthy_rate:
  runner.cmd.run:
    - name: |
        #!/bin/bash
        PATCH_ID="{{ patch_id }}"
        MINION_ID="{{ minion_id }}"
        
        # 获取已处理主机数和不健康主机数
        TOTAL=$(redis-cli scard "patch:{{ patch_id }}:hosts")
        UNHEALTHY=$(redis-cli scard "patch:{{ patch_id }}:unhealthy")
        
        if [ "$TOTAL" -gt 0 ]; then
          UNHEALTHY_RATE=$((UNHEALTHY * 100 / TOTAL))
          
          # 不健康率超过10%，触发自动回滚
          if [ "$UNHEALTHY_RATE" -gt 10 ]; then
            echo "UNHEALTHY_RATE_TRIGGER_ROLLBACK:$UNHEALTHY_RATE%"
            
            # 发送回滚事件
            salt-call event.send patch/rollback/trigger "patch_id={{ patch_id }} rate=$UNHEALTHY_RATE unhealthy=$UNHEALTHY total=$TOTAL"
            
            # 执行回滚
            salt -G "patch_id:{{ patch_id }}" state.apply patch.rollback pillar="{'patch_id':'{{ patch_id }}'}"
          fi
        fi
    - shell: /bin/bash
    - bg: True

# 发送告警
send_health_alert:
  runner.cmd.run:
    - name: |
        #!/bin/bash
        # 这里可以接入钉钉/企业微信告警
        ALERT_MSG="⚠️ 补丁健康异常 主机:{{ minion_id }} 补丁:{{ patch_id }} 状态:{{ health_status }}"
        echo "$ALERT_MSG" >> /var/log/patch/alerts.log
        # 实际环境接入 webhook
    - shell: /bin/bash
    - bg: True

{% endif %}

# 更新统计
update_health_stats:
  runner.redis.hincrby:
    - key: "patch:{{ patch_id }}:health_stats"
    - field: "{{ health_status }}"
    - value: 1
