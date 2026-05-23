#!/usr/bin/env python3
import subprocess
import json
import sys
import os
from datetime import datetime, timedelta, timezone
import argparse
import shutil
import platform
import configparser


def run_docker_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None


def check_fzf_available():
    return shutil.which('fzf') is not None


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_system_disk_usage():
    output = run_docker_command("docker system df --format '{{json .}}'")
    if output:
        data = json.loads(output)
        return {
            'images': int(data.get('ImagesSize', 0)),
            'volumes': int(data.get('VolumesSize', 0)),
            'total': int(data.get('ImagesSize', 0)) + int(data.get('VolumesSize', 0))
        }
    return {'images': 0, 'volumes': 0, 'total': 0}


def get_all_images_with_details():
    output = run_docker_command("docker images --format '{{json .}}' --no-trunc")
    if not output:
        return []
    
    images = []
    for line in output.split('\n'):
        if line:
            img = json.loads(line)
            inspect_output = run_docker_command(f"docker inspect --format '{{{{json .}}}}' {img.get('ID')}")
            parent_id = ""
            created_utc = datetime.now(timezone.utc)
            if inspect_output:
                inspect_data = json.loads(inspect_output)
                parent_id = inspect_data.get('Parent', '')
                created_str = inspect_data.get('Created', '')
                try:
                    created_utc = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                except:
                    pass
            
            images.append({
                'id': img.get('ID'),
                'repository': img.get('Repository'),
                'tag': img.get('Tag'),
                'size': int(img.get('Size', 0)),
                'created': created_utc,
                'parent_id': parent_id,
                'is_dangling': img.get('Repository') == '<none>' and img.get('Tag') == '<none>'
            })
    return images


def get_used_image_ids():
    output = run_docker_command("docker ps -a --format '{{.Image}}' --no-trunc")
    if not output:
        return set()
    
    used_ids = set()
    for image_ref in output.split('\n'):
        if image_ref:
            if image_ref.startswith('sha256:'):
                used_ids.add(image_ref)
            else:
                inspect_output = run_docker_command(f"docker inspect --format '{{{{.ID}}}}' {image_ref}")
                if inspect_output:
                    used_ids.add(inspect_output)
    return used_ids


def get_image_dependencies(all_images):
    dependency_map = {}
    
    for img in all_images:
        dependency_map[img['id']] = []
    
    for img in all_images:
        parent_id = img.get('parent_id', '')
        if parent_id and parent_id in dependency_map:
            child_name = f"{img['repository']}:{img['tag']}"
            if img['is_dangling']:
                child_name = f"<dangling>:{img['id'][:12]}"
            dependency_map[parent_id].append(child_name)
    
    return dependency_map


def get_unused_images(all_images, used_ids, dependency_map):
    unused_images = []
    
    for img in all_images:
        is_used_by_container = img['id'] in used_ids
        is_used_by_other_image = len(dependency_map.get(img['id'], [])) > 0
        
        if not is_used_by_container and not is_used_by_other_image:
            unused_images.append(img)
    
    unused_images.sort(key=lambda x: x['created'])
    return unused_images


def get_all_volumes():
    output = run_docker_command("docker volume ls --format '{{json .}}'")
    if not output:
        return []
    
    volumes = []
    for line in output.split('\n'):
        if line:
            vol = json.loads(line)
            inspect_output = run_docker_command(f"docker volume inspect --format '{{{{json .}}}}' {vol.get('Name')}")
            if inspect_output:
                inspect_data = json.loads(inspect_output)[0]
                created_str = inspect_data.get('CreatedAt', '')
                try:
                    created_utc = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                except:
                    created_utc = datetime.now(timezone.utc)
                
                usage_output = run_docker_command(f"docker system df -v --format '{{{{json .}}}}' 2>/dev/null | grep -A 100 'VOLUMES' | grep {vol.get('Name')} || true")
                
                volumes.append({
                    'name': vol.get('Name'),
                    'driver': vol.get('Driver'),
                    'mountpoint': inspect_data.get('Mountpoint', ''),
                    'created': created_utc,
                    'size': 0,
                    'labels': inspect_data.get('Labels', {})
                })
    return volumes


def get_used_volumes():
    output = run_docker_command("docker ps -a --format '{{json .}}'")
    if not output:
        return set()
    
    used_volumes = set()
    for line in output.split('\n'):
        if line:
            container = json.loads(line)
            inspect_output = run_docker_command(f"docker inspect --format '{{{{json .}}}}' {container.get('ID')}")
            if inspect_output:
                inspect_data = json.loads(inspect_output)[0]
                mounts = inspect_data.get('Mounts', [])
                for mount in mounts:
                    if mount.get('Type') == 'volume' and mount.get('Name'):
                        used_volumes.add(mount.get('Name'))
    
    return used_volumes


def get_unused_volumes(all_volumes, used_volumes):
    unused = []
    for vol in all_volumes:
        if vol['name'] not in used_volumes:
            unused.append(vol)
    unused.sort(key=lambda x: x['created'])
    return unused


def get_all_networks():
    output = run_docker_command("docker network ls --format '{{json .}}'")
    if not output:
        return []
    
    networks = []
    default_networks = {'bridge', 'host', 'none'}
    
    for line in output.split('\n'):
        if line:
            net = json.loads(line)
            name = net.get('Name', '')
            if name in default_networks:
                continue
            
            inspect_output = run_docker_command(f"docker network inspect --format '{{{{json .}}}}' {name}")
            if inspect_output:
                inspect_data = json.loads(inspect_output)[0]
                created_str = inspect_data.get('Created', '')
                try:
                    created_utc = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                except:
                    created_utc = datetime.now(timezone.utc)
                
                containers = inspect_data.get('Containers', {})
                used_by_count = len(containers)
                
                networks.append({
                    'id': net.get('ID'),
                    'name': name,
                    'driver': net.get('Driver'),
                    'created': created_utc,
                    'used_by_count': used_by_count,
                    'containers': list(containers.keys()) if containers else []
                })
    return networks


def get_unused_networks(all_networks):
    unused = []
    for net in all_networks:
        if net['used_by_count'] == 0:
            unused.append(net)
    unused.sort(key=lambda x: x['created'])
    return unused


def fzf_select_generic(items, format_func, header):
    if not items:
        return []
    
    fzf_input = []
    for i, item in enumerate(items):
        line = f"{i:>3} | {format_func(item)}"
        fzf_input.append(line)
    
    fzf_cmd = [
        'fzf',
        '-m',
        '--height', '60%',
        '--layout', 'reverse',
        '--header', header,
        '--bind', 'ctrl-a:select-all,ctrl-d:deselect-all,tab:toggle'
    ]
    
    try:
        result = subprocess.run(
            fzf_cmd,
            input='\n'.join(fzf_input),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        selected = result.stdout.strip().split('\n')
        selected_indices = []
        for line in selected:
            if line:
                idx = int(line.split('|')[0].strip())
                selected_indices.append(idx)
        
        return [items[i] for i in selected_indices]
    except Exception as e:
        print(f"fzf 调用失败: {e}")
        return []


def interactive_select(items, item_type, format_func, info_func=None):
    if not items:
        return []
    
    print(f"\n找到 {len(items)} 个未使用的{item_type}:\n")
    
    if check_fzf_available():
        print(f"使用 fzf 进行选择 (支持模糊搜索):")
        print("  - TAB 键切换选中状态")
        print("  - Ctrl+A 全选 / Ctrl+D 取消全选")
        print("  - Enter 确认选择 / ESC 取消")
        input("按 Enter 继续...")
        
        def img_format(img):
            img_type = "悬空" if img['is_dangling'] else "未引用"
            created_str = img['created'].strftime('%Y-%m-%d %H:%M UTC')
            return f"{img['repository']:<30} | {img['tag']:<15} | {format_size(img['size']):>10} | {created_str:<20} | {img_type}"
        
        def vol_format(vol):
            created_str = vol['created'].strftime('%Y-%m-%d %H:%M UTC')
            return f"{vol['name']:<30} | {vol['driver']:<15} | {created_str:<20}"
        
        def net_format(net):
            created_str = net['created'].strftime('%Y-%m-%d %H:%M UTC')
            return f"{net['name']:<30} | {net['driver']:<15} | {created_str:<20}"
        
        if item_type == '镜像':
            return fzf_select_generic(items, img_format, '序号 | 仓库                          | 标签            |       大小 | 创建时间             | 类型')
        elif item_type == '卷':
            return fzf_select_generic(items, vol_format, '序号 | 名称                          | 驱动            | 创建时间')
        elif item_type == '网络':
            return fzf_select_generic(items, net_format, '序号 | 名称                          | 驱动            | 创建时间')
    
    print(f"{'序号':<5} {format_func('header')}")
    print("-" * 100)
    
    for i, item in enumerate(items, 1):
        print(f"{i:<5} {format_func(item)}")
    
    print("\n操作选项:")
    print("  - 输入数字删除单个")
    print("  - 输入范围 (如 1-5) 删除多个")
    print("  - 输入逗号分隔列表 (如 1,3,5) 删除多个")
    print("  - 输入 'all' 删除所有")
    print("  - 输入 'quit' 退出\n")
    
    while True:
        choice = input("请选择操作: ").strip().lower()
        
        if choice == 'quit':
            return []
        elif choice == 'all':
            return items
        elif ',' in choice:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected = [items[i] for i in indices if 0 <= i < len(items)]
                if selected:
                    return selected
            except:
                print("无效的选择")
        elif '-' in choice:
            try:
                start, end = map(int, choice.split('-'))
                if 1 <= start <= end <= len(items):
                    return items[start-1:end]
            except:
                print("无效的范围")
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(items):
                    return [items[idx-1]]
            except:
                print("无效的选择，请重试")


def auto_filter_by_age(items, days, date_key='created'):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    return [item for item in items if item.get(date_key, datetime.now(timezone.utc)) <= cutoff_date]


def delete_images_clean(images, dry_run=False):
    if not images:
        return [], 0
    
    deleted = []
    total_freed = 0
    
    for img in images:
        if not dry_run:
            result = run_docker_command(f"docker rmi -f {img['id']} 2>&1")
            if result and "Error" not in result:
                deleted.append(img)
                total_freed += img['size']
        else:
            deleted.append(img)
            total_freed += img['size']
    
    return deleted, total_freed


def delete_volumes(volumes, dry_run=False):
    if not volumes:
        return [], 0
    
    deleted = []
    for vol in volumes:
        if not dry_run:
            result = run_docker_command(f"docker volume rm -f {vol['name']} 2>&1")
            if result and "Error" not in result:
                deleted.append(vol)
        else:
            deleted.append(vol)
    
    return deleted, 0


def delete_networks(networks, dry_run=False):
    if not networks:
        return [], 0
    
    deleted = []
    for net in networks:
        if not dry_run:
            result = run_docker_command(f"docker network rm {net['name']} 2>&1")
            if result and "Error" not in result:
                deleted.append(net)
        else:
            deleted.append(net)
    
    return deleted, 0


def generate_html_report(report_data, output_path):
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docker清理报告 - {report_data['timestamp']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #2496ed 0%, #1a73e8 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .timestamp {{ opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stat-card .label {{ color: #666; font-size: 14px; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; color: #2496ed; }}
        .stat-card .value.success {{ color: #34a853; }}
        .stat-card .value.warning {{ color: #fbbc05; }}
        .section {{ background: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #333; margin-bottom: 20px; font-size: 20px; border-bottom: 2px solid #2496ed; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #e0e0e0; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f8f9fa; }}
        .dangling {{ background: #fff3cd; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        .unused {{ background: #d4edda; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        .footer {{ text-align: center; color: #666; margin-top: 30px; padding: 20px; }}
        .empty {{ color: #999; font-style: italic; text-align: center; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐳 Docker 清理报告</h1>
            <div class="timestamp">生成时间: {report_data['timestamp']}</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="label">清理镜像数量</div>
                <div class="value">{len(report_data['deleted_images'])}</div>
            </div>
            <div class="stat-card">
                <div class="label">清理卷数量</div>
                <div class="value">{len(report_data['deleted_volumes'])}</div>
            </div>
            <div class="stat-card">
                <div class="label">清理网络数量</div>
                <div class="value">{len(report_data['deleted_networks'])}</div>
            </div>
            <div class="stat-card">
                <div class="label">释放空间</div>
                <div class="value success">{format_size(report_data['space_freed'])}</div>
            </div>
            <div class="stat-card">
                <div class="label">执行耗时</div>
                <div class="value warning">{report_data['duration']}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📦 已清理的镜像</h2>
            <table>
                <thead>
                    <tr>
                        <th>仓库</th>
                        <th>标签</th>
                        <th>大小</th>
                        <th>创建时间</th>
                        <th>类型</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td>{img['repository']}</td>
                        <td>{img['tag']}</td>
                        <td>{format_size(img['size'])}</td>
                        <td>{img['created'].strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        <td><span class="{'dangling' if img['is_dangling'] else 'unused'}">{'悬空' if img['is_dangling'] else '未引用'}</span></td>
                    </tr>
                    ''' for img in report_data['deleted_images']]) if report_data['deleted_images'] else '<tr><td colspan="5" class="empty">无</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>💾 已清理的卷</h2>
            <table>
                <thead>
                    <tr>
                        <th>名称</th>
                        <th>驱动</th>
                        <th>创建时间</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td>{vol['name']}</td>
                        <td>{vol['driver']}</td>
                        <td>{vol['created'].strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    ''' for vol in report_data['deleted_volumes']]) if report_data['deleted_volumes'] else '<tr><td colspan="3" class="empty">无</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🌐 已清理的网络</h2>
            <table>
                <thead>
                    <tr>
                        <th>名称</th>
                        <th>驱动</th>
                        <th>创建时间</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td>{net['name']}</td>
                        <td>{net['driver']}</td>
                        <td>{net['created'].strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    ''' for net in report_data['deleted_networks']]) if report_data['deleted_networks'] else '<tr><td colspan="3" class="empty">无</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Docker 清理工具 v3.0 | 报告自动生成</p>
        </div>
    </div>
</body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    return output_path


def load_config(config_path):
    config = configparser.ConfigParser()
    
    default_config = {
        'schedule': {
            'enabled': 'false',
            'mode': 'auto',
            'days': '30',
            'clean_images': 'true',
            'clean_volumes': 'false',
            'clean_networks': 'false',
            'dangling_only': 'false',
            'dry_run': 'false',
            'generate_report': 'true',
            'report_dir': './reports'
        },
        'cron': {
            'minute': '0',
            'hour': '3',
            'day': '*',
            'month': '*',
            'weekday': '0'
        }
    }
    
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        config.read_dict(default_config)
    
    return config


def create_default_config(config_path):
    config = configparser.ConfigParser()
    
    config['schedule'] = {
        'enabled': 'false',
        'mode': 'auto',
        'days': '30',
        'clean_images': 'true',
        'clean_volumes': 'false',
        'clean_networks': 'false',
        'dangling_only': 'false',
        'dry_run': 'false',
        'generate_report': 'true',
        'report_dir': './reports'
    }
    
    config['cron'] = {
        'minute': '0',
        'hour': '3',
        'day': '*',
        'month': '*',
        'weekday': '0'
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        config.write(f)
    
    return config_path


def setup_scheduled_task(config_path, script_path):
    config = load_config(config_path)
    
    cron_minute = config.get('cron', 'minute', fallback='0')
    cron_hour = config.get('cron', 'hour', fallback='3')
    cron_day = config.get('cron', 'day', fallback='*')
    cron_month = config.get('cron', 'month', fallback='*')
    cron_weekday = config.get('cron', 'weekday', fallback='0')
    
    script_abs_path = os.path.abspath(script_path)
    config_abs_path = os.path.abspath(config_path)
    
    python_exe = sys.executable
    
    cron_cmd = f"{cron_minute} {cron_hour} {cron_day} {cron_month} {cron_weekday} {python_exe} {script_abs_path} --config {config_abs_path} --scheduled >> /var/log/docker_cleanup.log 2>&1"
    
    system = platform.system()
    
    if system == 'Linux' or system == 'Darwin':
        existing_cron = run_docker_command("crontab -l 2>/dev/null | grep -v 'docker_cleanup' || true")
        new_cron = f"{existing_cron}\n{cron_cmd}\n" if existing_cron else f"{cron_cmd}\n"
        
        result = subprocess.run(
            ['crontab'],
            input=new_cron,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ 已设置定时任务: {cron_cmd}")
        else:
            print(f"✗ 设置定时任务失败: {result.stderr}")
    
    elif system == 'Windows':
        task_name = "DockerCleanup"
        ps_cmd = f"""
        $action = New-ScheduledTaskAction -Execute '{python_exe}' -Argument '{script_abs_path} --config {config_abs_path} --scheduled'
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek {int(cron_weekday) + 1} -At {cron_hour}:{cron_minute}
        Register-ScheduledTask -TaskName '{task_name}' -Action $action -Trigger $trigger -RunLevel Highest -Force
        """
        
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ 已设置Windows计划任务: {task_name}")
        else:
            print(f"✗ 设置计划任务失败: {result.stderr}")


def run_scheduled_cleanup(config_path):
    config = load_config(config_path)
    
    days = config.getint('schedule', 'days', fallback=30)
    clean_images = config.getboolean('schedule', 'clean_images', fallback=True)
    clean_volumes = config.getboolean('schedule', 'clean_volumes', fallback=False)
    clean_networks = config.getboolean('schedule', 'clean_networks', fallback=False)
    dangling_only = config.getboolean('schedule', 'dangling_only', fallback=False)
    dry_run = config.getboolean('schedule', 'dry_run', fallback=False)
    generate_report = config.getboolean('schedule', 'generate_report', fallback=True)
    report_dir = config.get('schedule', 'report_dir', fallback='./reports')
    
    start_time = datetime.now()
    
    before_usage = get_system_disk_usage()
    
    all_images = get_all_images_with_details()
    used_image_ids = get_used_image_ids()
    image_deps = get_image_dependencies(all_images)
    unused_images = get_unused_images(all_images, used_image_ids, image_deps)
    
    if dangling_only:
        unused_images = [img for img in unused_images if img['is_dangling']]
    
    unused_images = auto_filter_by_age(unused_images, days)
    
    all_volumes = get_all_volumes()
    used_volumes = get_used_volumes()
    unused_volumes = get_unused_volumes(all_volumes, used_volumes)
    unused_volumes = auto_filter_by_age(unused_volumes, days)
    
    all_networks = get_all_networks()
    unused_networks = get_unused_networks(all_networks)
    unused_networks = auto_filter_by_age(unused_networks, days)
    
    deleted_images = []
    deleted_volumes = []
    deleted_networks = []
    space_freed = 0
    
    if clean_images and unused_images:
        imgs, freed = delete_images_clean(unused_images, dry_run=dry_run)
        deleted_images = imgs
        space_freed += freed
    
    if clean_volumes and unused_volumes:
        vols, _ = delete_volumes(unused_volumes, dry_run=dry_run)
        deleted_volumes = vols
    
    if clean_networks and unused_networks:
        nets, _ = delete_networks(unused_networks, dry_run=dry_run)
        deleted_networks = nets
    
    duration = datetime.now() - start_time
    
    if generate_report:
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        report_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deleted_images': deleted_images,
            'deleted_volumes': deleted_volumes,
            'deleted_networks': deleted_networks,
            'space_freed': space_freed,
            'duration': str(duration).split('.')[0]
        }
        
        generate_html_report(report_data, report_path)
        print(f"报告已生成: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='Docker镜像批量清理工具 v3.0')
    parser.add_argument('--auto', type=int, metavar='DAYS', 
                        help='自动模式: 删除指定天数前的资源 (UTC时间)')
    parser.add_argument('--dangling-only', action='store_true',
                        help='仅清理悬空镜像')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式: 显示将要删除的资源但不实际删除')
    parser.add_argument('--no-fzf', action='store_true',
                        help='不使用fzf，使用传统交互模式')
    parser.add_argument('--show-deps', action='store_true',
                        help='显示所有镜像的依赖关系')
    parser.add_argument('--clean-volumes', action='store_true',
                        help='同时清理未使用的卷')
    parser.add_argument('--clean-networks', action='store_true',
                        help='同时清理未使用的自定义网络')
    parser.add_argument('--clean-all', action='store_true',
                        help='清理所有未使用资源（镜像、卷、网络）')
    parser.add_argument('--report', metavar='PATH',
                        help='生成HTML报告到指定路径')
    parser.add_argument('--config', metavar='PATH',
                        help='使用配置文件')
    parser.add_argument('--create-config', metavar='PATH',
                        help='创建默认配置文件')
    parser.add_argument('--setup-schedule', action='store_true',
                        help='设置定时清理任务')
    parser.add_argument('--scheduled', action='store_true',
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    
    if args.create_config:
        path = create_default_config(args.create_config)
        print(f"✓ 已创建默认配置文件: {path}")
        return
    
    if args.config and args.scheduled:
        run_scheduled_cleanup(args.config)
        return
    
    if args.setup_schedule:
        config_path = args.config if args.config else 'docker_cleanup.ini'
        if not os.path.exists(config_path):
            create_default_config(config_path)
        setup_scheduled_task(config_path, __file__)
        return
    
    print("=" * 70)
    print("Docker资源批量清理工具 v3.0")
    print("=" * 70)
    
    print("\n检查Docker环境...")
    if run_docker_command("docker info") is None:
        print("无法连接到Docker服务，请确保Docker已启动")
        sys.exit(1)
    print("✓ Docker服务正常\n")
    
    before_usage = get_system_disk_usage()
    print(f"当前镜像占用: {format_size(before_usage['images'])}")
    print(f"当前卷占用: {format_size(before_usage['volumes'])}")
    print(f"总计占用: {format_size(before_usage['total'])}")
    
    if args.show_deps:
        print("\n获取镜像信息...")
        all_images = get_all_images_with_details()
        deps = get_image_dependencies(all_images)
        
        print("\n镜像依赖关系:")
        for img in all_images:
            img_deps = deps.get(img['id'], [])
            if img_deps:
                print(f"\n  {img['repository']}:{img['tag']}")
                for dep in img_deps:
                    print(f"    ↳ {dep}")
        return
    
    start_time = datetime.now()
    
    print("\n获取镜像信息...")
    all_images = get_all_images_with_details()
    used_image_ids = get_used_image_ids()
    image_deps = get_image_dependencies(all_images)
    unused_images = get_unused_images(all_images, used_image_ids, image_deps)
    
    if args.dangling_only:
        unused_images = [img for img in unused_images if img['is_dangling']]
        print(f"找到 {len(unused_images)} 个悬空镜像")
    else:
        print(f"找到 {len(unused_images)} 个未使用且未被依赖的镜像")
    
    all_volumes = []
    unused_volumes = []
    if args.clean_volumes or args.clean_all:
        print("\n获取卷信息...")
        all_volumes = get_all_volumes()
        used_volumes = get_used_volumes()
        unused_volumes = get_unused_volumes(all_volumes, used_volumes)
        print(f"找到 {len(unused_volumes)} 个未使用的卷")
    
    all_networks = []
    unused_networks = []
    if args.clean_networks or args.clean_all:
        print("\n获取网络信息...")
        all_networks = get_all_networks()
        unused_networks = get_unused_networks(all_networks)
        print(f"找到 {len(unused_networks)} 个未使用的自定义网络")
    
    images_to_delete = []
    volumes_to_delete = []
    networks_to_delete = []
    
    if args.auto:
        images_to_delete = auto_filter_by_age(unused_images, args.auto)
        if args.clean_volumes or args.clean_all:
            volumes_to_delete = auto_filter_by_age(unused_volumes, args.auto)
        if args.clean_networks or args.clean_all:
            networks_to_delete = auto_filter_by_age(unused_networks, args.auto)
        
        print(f"\n自动模式: 删除 {args.auto} 天前创建的资源 (UTC时间)")
        print(f"当前时间 (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.auto)
        print(f"截止日期 (UTC): {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - 镜像: {len(images_to_delete)} 个")
        if volumes_to_delete:
            print(f"  - 卷: {len(volumes_to_delete)} 个")
        if networks_to_delete:
            print(f"  - 网络: {len(networks_to_delete)} 个")
    else:
        if unused_images:
            def img_format(item):
                if item == 'header':
                    return f"{'仓库':<30} {'标签':<15} {'大小':<12} {'创建时间':<20} {'类型':<10}"
                img_type = "悬空" if item['is_dangling'] else "未引用"
                created_str = item['created'].strftime('%Y-%m-%d %H:%M UTC')
                return f"{item['repository']:<30} {item['tag']:<15} {format_size(item['size']):<12} {created_str:<20} {img_type:<10}"
            
            images_to_delete = interactive_select(unused_images, '镜像', img_format)
        
        if (args.clean_volumes or args.clean_all) and unused_volumes:
            def vol_format(item):
                if item == 'header':
                    return f"{'名称':<30} {'驱动':<15} {'创建时间':<20}"
                created_str = item['created'].strftime('%Y-%m-%d %H:%M UTC')
                return f"{item['name']:<30} {item['driver']:<15} {created_str:<20}"
            
            volumes_to_delete = interactive_select(unused_volumes, '卷', vol_format)
        
        if (args.clean_networks or args.clean_all) and unused_networks:
            def net_format(item):
                if item == 'header':
                    return f"{'名称':<30} {'驱动':<15} {'创建时间':<20}"
                created_str = item['created'].strftime('%Y-%m-%d %H:%M UTC')
                return f"{item['name']:<30} {item['driver']:<15} {created_str:<20}"
            
            networks_to_delete = interactive_select(unused_networks, '网络', net_format)
    
    deleted_images = []
    deleted_volumes = []
    deleted_networks = []
    space_freed = 0
    
    if images_to_delete:
        print(f"\n--- 清理镜像 ---")
        imgs, freed = delete_images_clean(images_to_delete, dry_run=args.dry_run)
        deleted_images = imgs
        space_freed += freed
        print(f"{'[预览] ' if args.dry_run else ''}已清理 {len(deleted_images)} 个镜像")
    
    if volumes_to_delete:
        print(f"\n--- 清理卷 ---")
        vols, _ = delete_volumes(volumes_to_delete, dry_run=args.dry_run)
        deleted_volumes = vols
        print(f"{'[预览] ' if args.dry_run else ''}已清理 {len(deleted_volumes)} 个卷")
    
    if networks_to_delete:
        print(f"\n--- 清理网络 ---")
        nets, _ = delete_networks(networks_to_delete, dry_run=args.dry_run)
        deleted_networks = nets
        print(f"{'[预览] ' if args.dry_run else ''}已清理 {len(deleted_networks)} 个网络")
    
    duration = datetime.now() - start_time
    
    if args.report:
        report_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deleted_images': deleted_images,
            'deleted_volumes': deleted_volumes,
            'deleted_networks': deleted_networks,
            'space_freed': space_freed,
            'duration': str(duration).split('.')[0]
        }
        
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        generate_html_report(report_data, args.report)
        print(f"\n报告已生成: {args.report}")
    
    after_usage = get_system_disk_usage()
    
    print("\n" + "=" * 70)
    print("清理统计")
    print("=" * 70)
    print(f"执行耗时: {str(duration).split('.')[0]}")
    print(f"镜像: {format_size(before_usage['images'])} → {format_size(after_usage['images'])}")
    print(f"卷:   {format_size(before_usage['volumes'])} → {format_size(after_usage['volumes'])}")
    print(f"总计: {format_size(before_usage['total'])} → {format_size(after_usage['total'])}")
    print(f"释放空间: {format_size(max(0, space_freed))}")
    print("=" * 70)


if __name__ == "__main__":
    main()
