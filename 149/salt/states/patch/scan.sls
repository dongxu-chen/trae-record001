# ==========================================
# 补丁扫描 SLS
# 快速扫描目标主机的安全补丁状态
# ==========================================

{% set patch_backup_dir = pillar.get('patch_backup_dir', '/var/log/patch-backups') %}

# 创建备份目录
patch_backup_dir:
  file.directory:
    - name: {{ patch_backup_dir }}
    - user: root
    - group: root
    - mode: '0755'
    - makedirs: True

# 扫描可用更新（Debian/Ubuntu）
{% if grains['os_family'] == 'Debian' %}
apt_update_cache:
  pkg.uptodate:
    - refresh: True
    - require:
      - file: patch_backup_dir

apt_list_upgrades:
  module.run:
    - name: pkg.list_upgrades
    - refresh: False
    - require:
      - pkg: apt_update_cache
    - register: apt_upgrades

apt_security_updates:
  module.run:
    - name: cmd.run
    - cmd: "apt-get upgrade -s 2>/dev/null | grep -i security | wc -l"
    - shell: /bin/bash
    - register: security_count
    - require:
      - pkg: apt_update_cache

# 检查内核更新
kernel_check_debian:
  module.run:
    - name: cmd.run
    - cmd: "dpkg -l | grep linux-image | grep -v $(uname -r) | wc -l"
    - shell: /bin/bash
    - register: kernel_updates
    - require:
      - pkg: apt_update_cache

{% elif grains['os_family'] == 'RedHat' %}
# 扫描可用更新（RHEL/CentOS）
yum_update_cache:
  module.run:
    - name: pkg.refresh_db
    - require:
      - file: patch_backup_dir

yum_list_upgrades:
  module.run:
    - name: pkg.list_upgrades
    - require:
      - module: yum_update_cache
    - register: yum_upgrades

yum_security_updates:
  module.run:
    - name: cmd.run
    - cmd: "yum updateinfo list security all 2>/dev/null | wc -l"
    - shell: /bin/bash
    - register: security_count
    - require:
      - module: yum_update_cache

# 检查内核更新（RHEL）
kernel_check_rhel:
  module.run:
    - name: cmd.run
    - cmd: "rpm -q kernel --last 2>/dev/null | grep -v $(uname -r) | wc -l"
    - shell: /bin/bash
    - register: kernel_updates
    - require:
      - module: yum_update_cache

{% endif %}

# 收集系统信息
gather_patch_info:
  module.run:
    - name: grains.items
    - register: sys_info

# 发送扫描完成事件
scan_complete_event:
  event.send:
    - name: patch/scan/complete
    - data:
        id: {{ grains['id'] }}
        os_family: {{ grains['os_family'] }}
        os: {{ grains['os'] }}
        osrelease: {{ grains['osrelease'] }}
        kernel: {{ grains['kernelrelease'] }}
        total_upgrades: {{ apt_upgrades | length if apt_upgrades is defined else yum_upgrades | length }}
        security_updates: {{ security_count.stdout | int if security_count is defined else 0 }}
        kernel_updates: {{ kernel_updates.stdout | int if kernel_updates is defined else 0 }}
        scan_time: {{ salt['cmd.run']('date +%Y-%m-%dT%H:%M:%S%z') }}
    - require:
      - module: gather_patch_info
