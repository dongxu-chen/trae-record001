# ==========================================
# 补丁回滚 SLS
# 安全回滚到上一次补丁
# ==========================================

{% set patch_id = pillar.get('patch_id', '') %}
{% set patch_backup_dir = pillar.get('patch_backup_dir', '/var/log/patch-backups') %}

# 检查patch_id是否提供
{% if patch_id == '' %}
# 自动查找最新的备份
find_latest_backup:
  module.run:
    - name: cmd.run
    - cmd: "ls -td {{ patch_backup_dir }}/*/packages_before.txt 2>/dev/null | head -1 | xargs dirname | xargs basename
    - shell: /bin/bash
    - register: latest_backup

{% set patch_id = latest_backup.stdout | default('') %}
{% endif %}

# 验证备份目录存在
validate_backup:
  file.exists:
    - name: {{ patch_backup_dir }}/{{ patch_id }}/packages_before.txt
    - failhard: True

{% if grains['os_family'] == 'Debian' %}
# Debian/Ubuntu 回滚
perform_rollback_deb:
  module.run:
    - name: cmd.run
    - cmd: |
        # 使用备份恢复软件包状态
        dpkg --set-selections < {{ patch_backup_dir }}/{{ patch_id }}/packages_before.txt
        apt-get -y dselect-upgrade --allow-downgrades
    - shell: /bin/bash
    - require:
      - file: validate_backup
    - register: rollback_result

{% elif grains['os_family'] == 'RedHat' %}
# RHEL/CentOS 回滚
find_last_transaction:
  module.run:
    - name: cmd.run
    - cmd: yum history list last 1 2>/dev/null | grep -E '^[[:space:]]*[0-9]+' | awk '{print $1}' | head -1
    - shell: /bin/bash
    - register: yum_tid
    - require:
      - file: validate_backup

perform_rollback_rhel:
  module.run:
    - name: cmd.run
    - cmd: yum history undo -y {{ yum_tid.stdout }}
    - shell: /bin/bash
    - require:
      - module: find_last_transaction
    - register: rollback_result

{% endif %}

# 发送回滚完成事件
rollback_complete_event:
  event.send:
    - name: patch/rollback/complete
    - data:
        id: {{ grains['id'] }}
        patch_id: {{ patch_id }}
        success: {{ 'true' if rollback_result is defined else 'false' }}
        rollback_time: {{ salt['cmd.run']('date +%Y-%m-%dT%H:%M:%S%z') }}
