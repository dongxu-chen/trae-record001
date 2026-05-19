# ==========================================
# 补丁安装 SLS
# 高性能并发补丁安装
# ==========================================

{% set patch_backup_dir = pillar.get('patch_backup_dir', '/var/log/patch-backups') %}
{% set patch_id = pillar.get('patch_id', salt['cmd.run']('date +%Y%m%d_%H%M%S')) %}
{% set security_only = pillar.get('security_only', True) %}
{% set auto_reboot = pillar.get('auto_reboot', False) %}

# 创建本次补丁备份目录
patch_backup_{{ patch_id }}:
  file.directory:
    - name: {{ patch_backup_dir }}/{{ patch_id }}
    - user: root
    - group: root
    - mode: '0755'
    - makedirs: True

# 备份当前软件包列表
{% if grains['os_family'] == 'Debian' %}
backup_package_list_deb:
  module.run:
    - name: cmd.run
    - cmd: dpkg --get-selections > {{ patch_backup_dir }}/{{ patch_id }}/packages_before.txt
    - shell: /bin/bash
    - require:
      - file: patch_backup_{{ patch_id }}

# 安装安全补丁（Debian）
install_security_patches_deb:
  pkg.uptodate:
    {% if security_only %}
    - dist_upgrade: False
    {% else %}
    - dist_upgrade: True
    {% endif %}
    - refresh: False
    - require:
      - module: backup_package_list_deb
    - register: patch_result

# 记录安装后的软件包列表
backup_after_deb:
  module.run:
    - name: cmd.run
    - cmd: dpkg --get-selections > {{ patch_backup_dir }}/{{ patch_id }}/packages_after.txt
    - shell: /bin/bash
    - require:
      - pkg: install_security_patches_deb

{% elif grains['os_family'] == 'RedHat' %}
backup_package_list_rpm:
  module.run:
    - name: cmd.run
    - cmd: rpm -qa > {{ patch_backup_dir }}/{{ patch_id }}/packages_before.txt
    - shell: /bin/bash
    - require:
      - file: patch_backup_{{ patch_id }}

# 安装安全补丁（RHEL）
install_security_patches_rhel:
  pkg.uptodate:
    {% if security_only %}
    - security: True
    {% else %}
    - security: False
    {% endif %}
    - refresh: False
    - require:
      - module: backup_package_list_rpm
    - register: patch_result

# 记录安装后的软件包列表
backup_after_rhel:
  module.run:
    - name: cmd.run
    - cmd: rpm -qa > {{ patch_backup_dir }}/{{ patch_id }}/packages_after.txt
    - shell: /bin/bash
    - require:
      - pkg: install_security_patches_rhel

{% endif %}

# 检查是否需要重启
check_reboot_required:
  module.run:
    - name: cmd.run
    - cmd: |
        if [ -f /var/run/reboot-required ]; then
          echo "reboot_required"
        else
          # 检查内核版本变化
          if [ -n "$(ls /boot/vmlinuz-* 2>/dev/null | sort -V | tail -1 | grep -v $(uname -r))" ]; then
            echo "reboot_required"
          else
            echo "no_reboot"
          fi
        fi
    - shell: /bin/bash
    - register: reboot_check

# 自动重启（如果配置启用）
{% if auto_reboot %}
auto_reboot_if_needed:
  module.run:
    - name: system.reboot
    - when: reboot_check.stdout == "reboot_required"
    - delay: 60
    - require:
      - module: check_reboot_required
{% endif %}

# 发送补丁安装完成事件
patch_install_complete_event:
  event.send:
    - name: patch/install/complete
    - data:
        id: {{ grains['id'] }}
        patch_id: {{ patch_id }}
        os_family: {{ grains['os_family'] }}
        changes: {{ patch_result.changes | length if patch_result.changes is defined else 0 }}
        result: {{ patch_result.result | default('success') }}
        reboot_required: {{ 'true' if reboot_check.stdout == 'reboot_required' else 'false' }}
        auto_reboot_enabled: {{ 'true' if auto_reboot else 'false' }}
        install_time: {{ salt['cmd.run']('date +%Y-%m-%dT%H:%M:%S%z') }}
    - require:
      - module: check_reboot_required
