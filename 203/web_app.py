import os
import shutil
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
from database import BackupDatabase


app = Flask(__name__)
app.config['SECRET_KEY'] = 'backup-tool-secret-key'

db = BackupDatabase()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>备份管理系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background-color: #f5f7fa;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 5px;
        }
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        .container {
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 20px;
        }
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .nav-tab {
            padding: 12px 24px;
            background: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
            color: #666;
        }
        .nav-tab:hover {
            background: #e8ecf5;
        }
        .nav-tab.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .section {
            display: none;
        }
        .section.active {
            display: block;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .stat-card h3 {
            font-size: 13px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }
        .stat-card .value.success { color: #4CAF50; }
        .stat-card .value.danger { color: #f44336; }
        .stat-card .value.info { color: #2196F3; }
        .stat-card .value.warning { color: #FF9800; }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            overflow: hidden;
            margin-bottom: 20px;
        }
        .card-header {
            padding: 20px 25px;
            border-bottom: 1px solid #eee;
            font-weight: 600;
            font-size: 16px;
        }
        .card-body {
            padding: 20px 25px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            font-size: 13px;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge.success {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .badge.failed {
            background: #ffebee;
            color: #c62828;
        }
        .badge.running {
            background: #e3f2fd;
            color: #1565c0;
        }
        .disk-bar {
            height: 24px;
            background: #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
            margin: 10px 0;
        }
        .disk-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 500;
        }
        .disk-fill.warning {
            background: linear-gradient(90deg, #FF9800, #FFC107);
        }
        .disk-fill.danger {
            background: linear-gradient(90deg, #f44336, #E91E63);
        }
        .log-viewer {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            max-height: 500px;
            overflow-y: auto;
            line-height: 1.6;
        }
        .log-line {
            margin-bottom: 5px;
        }
        .log-line .time { color: #6A9955; }
        .log-line .level.INFO { color: #4FC1FF; }
        .log-line .level.WARNING { color: #CE9178; }
        .log-line .level.ERROR { color: #F48771; }
        .log-line .level.DEBUG { color: #C586C0; }
        .filter-bar {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        .filter-bar select, .filter-bar input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .btn {
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover {
            background: #5a6fd8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>💾 备份管理系统</h1>
        <p>自动化数据备份工具管理界面</p>
    </div>
    <div class="container">
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showSection('dashboard')">📊 仪表盘</button>
            <button class="nav-tab" onclick="showSection('history')">📋 备份历史</button>
            <button class="nav-tab" onclick="showSection('logs')">📝 日志查看</button>
            <button class="nav-tab" onclick="showSection('disk')">💿 磁盘使用</button>
        </div>

        <div id="dashboard" class="section active">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>总备份次数</h3>
                    <div class="value info">{{ stats.total_backups }}</div>
                </div>
                <div class="stat-card">
                    <h3>成功备份</h3>
                    <div class="value success">{{ stats.successful_backups }}</div>
                </div>
                <div class="stat-card">
                    <h3>失败备份</h3>
                    <div class="value danger">{{ stats.failed_backups }}</div>
                </div>
                <div class="stat-card">
                    <h3>成功率</h3>
                    <div class="value warning">{{ stats.success_rate }}%</div>
                </div>
                <div class="stat-card">
                    <h3>总备份数据量</h3>
                    <div class="value info">{{ stats.total_data_backed_up_mb }} MB</div>
                </div>
                <div class="stat-card">
                    <h3>平均执行时间</h3>
                    <div class="value warning">{{ stats.avg_duration_seconds }} 秒</div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">最近备份记录</div>
                <div class="card-body">
                    <table>
                        <thead>
                            <tr>
                                <th>任务名称</th>
                                <th>备份类型</th>
                                <th>状态</th>
                                <th>文件数</th>
                                <th>大小</th>
                                <th>开始时间</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for record in recent_backups %}
                            <tr>
                                <td>{{ record.task_name }}</td>
                                <td>{{ '全量' if record.backup_type == 'full' else '增量' }}</td>
                                <td><span class="badge {{ record.status }}">{{ '成功' if record.status == 'success' else '失败' if record.status == 'failed' else '运行中' }}</span></td>
                                <td>{{ record.files_backed_up }}/{{ record.total_files }}</td>
                                <td>{{ record.archive_size_mb }} MB</td>
                                <td>{{ record.start_time }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="history" class="section">
            <div class="card">
                <div class="card-header">备份历史记录</div>
                <div class="card-body">
                    <div class="filter-bar">
                        <select id="taskFilter" onchange="filterHistory()">
                            <option value="">所有任务</option>
                            {% for task in tasks %}
                            <option value="{{ task }}">{{ task }}</option>
                            {% endfor %}
                        </select>
                        <input type="number" id="limitInput" value="50" min="10" max="500" onchange="filterHistory()">
                        <button class="btn" onclick="filterHistory()">筛选</button>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>任务名称</th>
                                <th>备份类型</th>
                                <th>状态</th>
                                <th>文件数</th>
                                <th>大小</th>
                                <th>MD5</th>
                                <th>执行时间</th>
                                <th>耗时</th>
                            </tr>
                        </thead>
                        <tbody id="historyTable">
                            {% for record in history %}
                            <tr data-task="{{ record.task_name }}">
                                <td>{{ record.id }}</td>
                                <td>{{ record.task_name }}</td>
                                <td>{{ '全量' if record.backup_type == 'full' else '增量' }}</td>
                                <td><span class="badge {{ record.status }}">{{ '成功' if record.status == 'success' else '失败' if record.status == 'failed' else '运行中' }}</span></td>
                                <td>{{ record.files_backed_up }}/{{ record.total_files }}</td>
                                <td>{{ record.archive_size_mb }} MB</td>
                                <td><code>{{ record.md5_hash or '-' }}</code></td>
                                <td>{{ record.start_time }}</td>
                                <td>{{ record.duration_seconds or '-' }}s</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="logs" class="section">
            <div class="card">
                <div class="card-header">日志查看器</div>
                <div class="card-body">
                    <div class="filter-bar">
                        <select id="logLevel" onchange="filterLogs()">
                            <option value="">所有级别</option>
                            <option value="INFO">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                            <option value="DEBUG">DEBUG</option>
                        </select>
                        <button class="btn" onclick="loadLogs()">刷新</button>
                    </div>
                    <div class="log-viewer" id="logViewer">
                        {{ log_content|safe }}
                    </div>
                </div>
            </div>
        </div>

        <div id="disk" class="section">
            <div class="card">
                <div class="card-header">磁盘使用情况</div>
                <div class="card-body">
                    {% for disk in disk_info %}
                    <div style="margin-bottom: 30px;">
                        <h3 style="margin-bottom: 10px;">{{ disk.mountpoint }}</h3>
                        <div class="disk-bar">
                            <div class="disk-fill {{ 'danger' if disk.percent > 90 else 'warning' if disk.percent > 70 else '' }}" style="width: {{ disk.percent }}%">
                                {{ disk.percent }}%
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; color: #666; font-size: 14px;">
                            <span>已使用: {{ disk.used }} GB</span>
                            <span>空闲: {{ disk.free }} GB</span>
                            <span>总计: {{ disk.total }} GB</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            <div class="card">
                <div class="card-header">临时目录使用</div>
                <div class="card-body">
                    <div class="disk-bar">
                        <div class="disk-fill {{ 'danger' if temp_disk.percent > 90 else 'warning' if temp_disk.percent > 70 else '' }}" style="width: {{ temp_disk.percent }}%">
                            {{ temp_disk.percent }}%
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; color: #666; font-size: 14px;">
                        <span>已使用: {{ temp_disk.used }} GB</span>
                        <span>空闲: {{ temp_disk.free }} GB</span>
                        <span>总计: {{ temp_disk.total }} GB</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showSection(sectionId) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            event.target.classList.add('active');
        }

        function filterHistory() {
            const task = document.getElementById('taskFilter').value;
            const limit = document.getElementById('limitInput').value;
            location.href = '/history?task=' + task + '&limit=' + limit;
        }

        function filterLogs() {
            const level = document.getElementById('logLevel').value;
            location.href = '/logs?level=' + level;
        }

        function loadLogs() {
            location.reload();
        }
    </script>
</body>
</html>
"""


def get_disk_usage():
    disk_info = []
    for mount in ['/'] if os.name != 'nt' else ['C:\\', 'D:\\']:
        try:
            if os.path.exists(mount):
                usage = shutil.disk_usage(mount)
                disk_info.append({
                    'mountpoint': mount,
                    'total': round(usage.total / (1024**3), 2),
                    'used': round(usage.used / (1024**3), 2),
                    'free': round(usage.free / (1024**3), 2),
                    'percent': round(usage.used / usage.total * 100, 1)
                })
        except:
            pass
    return disk_info


def get_temp_disk_usage():
    temp_dir = os.path.abspath('./temp')
    try:
        usage = shutil.disk_usage(temp_dir)
        return {
            'total': round(usage.total / (1024**3), 2),
            'used': round(usage.used / (1024**3), 2),
            'free': round(usage.free / (1024**3), 2),
            'percent': round(usage.used / usage.total * 100, 1)
        }
    except:
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}


def read_log_file(level_filter=None):
    log_file = 'backup.log'
    if not os.path.exists(log_file):
        return '<div class="log-line">日志文件不存在</div>'
    
    lines = []
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f.readlines()[-500:]:
                if level_filter and level_filter not in line:
                    continue
                parts = line.split(' - ', 3)
                if len(parts) >= 4:
                    time_str = parts[0]
                    level = parts[2]
                    msg = parts[3].strip()
                    lines.append(
                        f'<div class="log-line">'
                        f'<span class="time">{time_str}</span> - '
                        f'<span class="level {level}">[{level}]</span> '
                        f'{msg}'
                        f'</div>'
                    )
                else:
                    lines.append(f'<div class="log-line">{line}</div>')
    except Exception as e:
        return f'<div class="log-line">读取日志失败: {e}</div>'
    
    return '\n'.join(reversed(lines))


@app.route('/')
def dashboard():
    stats = db.get_backup_statistics(days=30)
    recent_backups = db.get_backup_history(limit=10)
    history = db.get_backup_history(limit=100)
    tasks = list(set([h['task_name'] for h in history]))
    disk_info = get_disk_usage()
    temp_disk = get_temp_disk_usage()
    log_content = read_log_file()
    
    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        recent_backups=recent_backups,
        history=history,
        tasks=tasks,
        disk_info=disk_info,
        temp_disk=temp_disk,
        log_content=log_content
    )


@app.route('/history')
def history():
    task = request.args.get('task', '')
    limit = int(request.args.get('limit', 100))
    
    if task:
        history_data = db.get_backup_history(task_name=task, limit=limit)
    else:
        history_data = db.get_backup_history(limit=limit)
    
    stats = db.get_backup_statistics(days=30)
    recent_backups = db.get_backup_history(limit=10)
    all_history = db.get_backup_history(limit=100)
    tasks = list(set([h['task_name'] for h in all_history]))
    disk_info = get_disk_usage()
    temp_disk = get_temp_disk_usage()
    log_content = read_log_file()
    
    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        recent_backups=recent_backups,
        history=history_data,
        tasks=tasks,
        disk_info=disk_info,
        temp_disk=temp_disk,
        log_content=log_content
    )


@app.route('/logs')
def logs():
    level = request.args.get('level', '')
    stats = db.get_backup_statistics(days=30)
    recent_backups = db.get_backup_history(limit=10)
    history = db.get_backup_history(limit=100)
    tasks = list(set([h['task_name'] for h in history]))
    disk_info = get_disk_usage()
    temp_disk = get_temp_disk_usage()
    log_content = read_log_file(level_filter=level)
    
    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        recent_backups=recent_backups,
        history=history,
        tasks=tasks,
        disk_info=disk_info,
        temp_disk=temp_disk,
        log_content=log_content
    )


@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_backup_statistics(days=30))


@app.route('/api/history')
def api_history():
    task = request.args.get('task', '')
    limit = int(request.args.get('limit', 100))
    if task:
        return jsonify(db.get_backup_history(task_name=task, limit=limit))
    return jsonify(db.get_backup_history(limit=limit))


def run_web_server(host='0.0.0.0', port=5000):
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    run_web_server()
