# ==========================================
# 补丁结果 Reactor
# 实时处理补丁安装结果事件
# ==========================================

{% set data = data.get('data', {}) %}
{% set minion_id = data.get('id', '') %}
{% set patch_id = data.get('patch_id', '') %}
{% set changes = data.get('changes', 0) %}
{% set result = data.get('result', 'success') %}
{% set reboot_required = data.get('reboot_required', 'false') %}

# 记录到Redis
store_patch_result:
  runner.redis.set:
    - key: "patch:{{ patch_id }}:{{ minion_id }}"
    - value: "{{ data | json }}"
    - expire: 86400

# 更新统计
update_patch_stats:
  runner.redis.hincrby:
    - key: "patch:{{ patch_id }}:stats"
    - field: "total"
    - value: 1

{% if result == 'success' %}
update_success_count:
  runner.redis.hincrby:
    - key: "patch:{{ patch_id }}:stats"
    - field: "success"
    - value: 1

{% if changes > 0 %}
update_changed_count:
  runner.redis.hincrby:
    - key: "patch:{{ patch_id }}:stats"
    - field: "changed"
    - value: 1
{% endif %}

{% if reboot_required == 'true' %}
# 记录需要重启的主机
mark_reboot_required:
  runner.redis.sadd:
    - key: "patch:{{ patch_id }}:reboot_required"
    - value: "{{ minion_id }}"
{% endif %}

{% else %}
# 记录失败
update_failed_count:
  runner.redis.hincrby:
    - key: "patch:{{ patch_id }}:stats"
    - field: "failed"
    - value: 1

add_failed_host:
  runner.redis.sadd:
    - key: "patch:{{ patch_id }}:failed_hosts"
    - value: "{{ minion_id }}"

{% endif %}

# 检查失败率，决定是否触发自动回滚
check_failure_rate:
  runner.cmd.run:
    - name: |
        #!/bin/bash
        STATS=$(redis-cli hgetall patch:{{ patch_id }}:stats)
        TOTAL=$(echo "$STATS" | grep -A1 total | tail -1)
        FAILED=$(echo "$STATS" | grep -A1 failed | tail -1)
        if [ "$TOTAL" -gt 0 ]; then
          FAILURE_RATE=$((FAILED * 100 / TOTAL))
          if [ "$FAILURE_RATE" -gt 20 ]; then
            # 失败率超过20%，触发自动回滚警报
            redis-cli publish patch:alerts "HIGH_FAILURE_RATE:{{ patch_id }}:$FAILURE_RATE%"
          fi
        fi
    - shell: /bin/bash
    - bg: True
