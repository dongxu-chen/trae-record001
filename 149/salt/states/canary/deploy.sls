# ==========================================
# 金丝雀发布 Orchestration SLS
# 分阶段安全补丁部署
# ==========================================

{% set canary_percent = pillar.get('canary_percent', 1) %}
{% set batch_sizes = pillar.get('batch_sizes', [1, 5, 15, 30, 60, 100]) %}
{% set patch_id = pillar.get('patch_id', salt['cmd.run']('date +%Y%m%d_%H%M%S')) %}
{% set health_check_timeout = pillar.get('health_timeout', 60) %}
{% set auto_rollback = pillar.get('auto_rollback', True) %}

# 阶段 0: 初始化部署信息
canary_init:
  salt.function:
    - name: event.send
    - tgt: '{{ grains["id"] }}'
    - arg:
      - patch/canary/start
      - patch_id: {{ patch_id }}
        canary_percent: {{ canary_percent }}
        batch_sizes: {{ batch_sizes | join(',') }}
        total_hosts: {{ salt['saltutil.runner']('manage.up') | length }}

# 获取在线主机列表
get_online_minions:
  salt.runner:
    - name: manage.up
    - register: online_minions

{% set total_minions = online_minions | length %}

# 按批次执行部署
{% for batch_percent in batch_sizes %}
{% set batch_size = (total_minions * batch_percent / 100) | round | int %}
{% if batch_size > 0 %}

# 阶段 {{ loop.index }}: {{ batch_percent }}% 节点部署
canary_batch_{{ loop.index }}:
  salt.state:
    - tgt: 'G@role:{{ grains.get("role", "default") }} and {{ batch_size }}%'
    - tgt_type: compound
    - sls: patch.install
    - pillar:
        patch_id: {{ patch_id }}
        batch: {{ loop.index }}
        batch_percent: {{ batch_percent }}
    - batch: {{ batch_percent }}%
    - batch_wait: 2
    - require:
      {% if loop.index > 1 %}
      - salt: canary_health_check_{{ loop.index - 1 }}
      {% else %}
      - salt: get_online_minions
      {% endif %}

# 阶段 {{ loop.index }} 健康检查
canary_health_check_{{ loop.index }}:
  salt.function:
    - name: status.health
    - tgt: 'G@role:{{ grains.get("role", "default") }} and {{ batch_percent }}%'
    - tgt_type: compound
    - require:
      - salt: canary_batch_{{ loop.index }}

# 检查健康状态并决定是否继续
canary_verify_{{ loop.index }}:
  module.run:
    - name: event.send
    - data:
        patch_id: {{ patch_id }}
        batch: {{ loop.index }}
        batch_percent: {{ batch_percent }}
        hosts_updated: {{ batch_size }}
        status: proceed
    - require:
      - salt: canary_health_check_{{ loop.index }}

{% endif %}
{% endfor %}

# 最终部署完成事件
canary_complete:
  salt.function:
    - name: event.send
    - tgt: '{{ grains["id"] }}'
    - arg:
      - patch/canary/complete
      - patch_id: {{ patch_id }}
        total_hosts: {{ total_minions }}
        status: success
    - require:
      {% if batch_sizes | length > 0 %}
      - salt: canary_verify_{{ batch_sizes | length }}
      {% else %}
      - salt: get_online_minions
      {% endif %}
