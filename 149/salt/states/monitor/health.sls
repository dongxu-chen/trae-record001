# ==========================================
# 健康检查状态 SLS
# 主机健康监控指标
# ==========================================

# 健康检查脚本
health_check_script:
  file.managed:
    - name: /usr/local/bin/health-check.sh
    - source: salt://monitor/files/health-check.sh
    - user: root
    - group: root
    - mode: '0755'
    - template: jinja

# 执行健康检查
run_health_check:
  module.run:
    - name: cmd.run
    - cmd: /usr/local/bin/health-check.sh
    - shell: /bin/bash
    - require:
      - file: health_check_script
    - register: health_result

# 解析健康检查结果
parse_health_result:
  module.run:
    - name: cmd.run
    - cmd: "echo '{{ health_result.stdout }}' | jq .status"
    - shell: /bin/bash
    - require:
      - module: run_health_check
    - register: health_status

# 发送健康事件
send_health_event:
  event.send:
    - name: patch/monitor/health
    - data:
        id: {{ grains['id'] }}
        status: {{ health_status.stdout | replace('"', '') | default('unknown') }}
        metrics: {{ health_result.stdout | from_json }}
        timestamp: {{ salt['cmd.run']('date +%Y-%m-%dT%H:%M:%S%z') }}
    - require:
      - module: parse_health_result
