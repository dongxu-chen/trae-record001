const API_BASE = '/api/Guacamole';
let currentSessionId = null;
let wsConnection = null;
let selectedConnectionId = null;

document.addEventListener('DOMContentLoaded', function() {
    initNavigation();
    loadDashboard();
    loadConnections();
    loadConnectionsForClient();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            const page = this.dataset.page;
            navigateTo(page);
        });
    });
}

function navigateTo(page) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === page) {
            item.classList.add('active');
        }
    });

    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(page).classList.add('active');

    switch(page) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'connections':
            loadConnections();
            break;
        case 'sessions':
            loadSessions();
            break;
        case 'recordings':
            loadRecordings();
            break;
    }
}

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();

        document.getElementById('stat-connections').textContent = stats.TotalConnections;
        document.getElementById('stat-active-sessions').textContent = stats.ActiveSessions;
        document.getElementById('stat-total-sessions').textContent = stats.TotalSessions;
        document.getElementById('stat-recordings').textContent = stats.RecordedSessions;

        const protocolStats = document.getElementById('protocol-stats');
        if (stats.ProtocolStats && stats.ProtocolStats.length > 0) {
            protocolStats.innerHTML = stats.ProtocolStats.map(p => `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <span class="protocol-badge protocol-${p.Protocol.toLowerCase()}">${p.Protocol}</span>
                    </div>
                    <div class="flex-grow-1 mx-3">
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar" style="width: ${(p.Count / stats.TotalSessions * 100) || 0}%"></div>
                        </div>
                    </div>
                    <div class="text-end" style="width: 60px;">${p.Count}</div>
                </div>
            `).join('');
        } else {
            protocolStats.innerHTML = '<p class="text-center text-muted">暂无数据</p>';
        }

        await loadRecentSessions();
    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
    }
}

async function loadRecentSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions?limit=5`);
        const sessions = await response.json();
        const list = document.getElementById('recent-sessions-list');

        if (sessions.length === 0) {
            list.innerHTML = '<div class="p-3 text-center text-muted">暂无会话记录</div>';
            return;
        }

        list.innerHTML = sessions.map(session => `
            <div class="session-item">
                <div>
                    <div class="d-flex align-items-center">
                        <span class="status-badge ${session.State === 2 ? 'status-active' : 'status-inactive'}"></span>
                        <strong>${session.ConnectionName || session.Id.substring(0, 8)}</strong>
                        <span class="protocol-badge protocol-${session.Protocol.toLowerCase()} ms-2">${session.Protocol}</span>
                    </div>
                    <small class="text-muted">${session.User?.Username || '未知用户'} · ${formatDate(session.ConnectedAt || session.CreatedAt)}</small>
                </div>
                <div>
                    ${session.State === 2 ? '<span class="badge bg-success">已连接</span>' : '<span class="badge bg-secondary">已断开</span>'}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('加载最近会话失败:', error);
    }
}

async function loadConnections() {
    try {
        const response = await fetch(`${API_BASE}/connections`);
        const connections = await response.json();
        const list = document.getElementById('connections-list');

        if (connections.length === 0) {
            list.innerHTML = '<div class="col-12"><div class="card p-4 text-center text-muted">暂无连接，点击"新建连接"创建</div></div>';
            return;
        }

        list.innerHTML = connections.map(conn => `
            <div class="col-md-4 mb-3">
                <div class="card connection-card p-3 h-100">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="mb-1">${conn.Name}</h6>
                            <span class="protocol-badge protocol-${conn.Protocol.toLowerCase()}">${conn.Protocol}</span>
                        </div>
                        <span class="badge ${conn.IsActive ? 'bg-success' : 'bg-secondary'}">
                            ${conn.IsActive ? '启用' : '停用'}
                        </span>
                    </div>
                    <div class="text-muted small mb-3">
                        <div><i class="bi bi-hdd-network me-1"></i> ${conn.Hostname}:${conn.Port}</div>
                        ${conn.Description ? `<div><i class="bi bi-info-circle me-1"></i> ${conn.Description}</div>` : ''}
                    </div>
                    <div class="mt-auto d-flex gap-2">
                        <button class="btn btn-sm btn-outline-light flex-grow-1" onclick="connectTo('${conn.Id}')">
                            <i class="bi bi-play-fill me-1"></i> 连接
                        </button>
                        <button class="btn btn-sm btn-outline-light" onclick="deleteConnection('${conn.Id}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('加载连接失败:', error);
    }
}

async function loadConnectionsForClient() {
    try {
        const response = await fetch(`${API_BASE}/connections?isActive=true`);
        const connections = await response.json();
        const select = document.getElementById('client-connection');

        select.innerHTML = '<option value="">-- 请选择连接 --</option>' +
            connections.map(conn => `<option value="${conn.Id}">${conn.Name} (${conn.Protocol})</option>`).join('');
    } catch (error) {
        console.error('加载连接列表失败:', error);
    }
}

function updateConnectionParams() {
    selectedConnectionId = document.getElementById('client-connection').value;
}

async function createConnection() {
    const name = document.getElementById('conn-name').value;
    const protocol = document.getElementById('conn-protocol').value;
    const hostname = document.getElementById('conn-hostname').value;
    const port = parseInt(document.getElementById('conn-port').value) || getDefaultPort(protocol);
    const username = document.getElementById('conn-username').value;
    const password = document.getElementById('conn-password').value;
    const domain = document.getElementById('conn-domain').value;
    const colorDepth = parseInt(document.getElementById('conn-colordepth').value);
    const enableAudio = document.getElementById('conn-audio').checked;
    const enableClipboard = document.getElementById('conn-clipboard').checked;
    const enableRecording = document.getElementById('conn-recording').checked;
    const description = document.getElementById('conn-description').value;

    const connection = {
        Name: name,
        Protocol: protocol,
        Hostname: hostname,
        Port: port,
        Username: username || null,
        Password: password || null,
        Domain: domain || null,
        ColorDepth: colorDepth,
        Width: 1920,
        Height: 1080,
        Dpi: 96,
        EnableAudio: enableAudio,
        EnableClipboard: enableClipboard,
        EnableRecording: enableRecording,
        Description: description || null,
        IsActive: true
    };

    try {
        const response = await fetch(`${API_BASE}/connections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(connection)
        });

        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('connectionModal')).hide();
            document.getElementById('connection-form').reset();
            await loadConnections();
            await loadConnectionsForClient();
            await loadDashboard();
            showToast('连接创建成功', 'success');
        } else {
            showToast('连接创建失败', 'error');
        }
    } catch (error) {
        console.error('创建连接失败:', error);
        showToast('连接创建失败', 'error');
    }
}

async function deleteConnection(id) {
    if (!confirm('确定要删除此连接吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/connections/${id}`, { method: 'DELETE' });

        if (response.ok) {
            await loadConnections();
            await loadConnectionsForClient();
            await loadDashboard();
            showToast('连接已删除', 'success');
        } else {
            showToast('删除失败', 'error');
        }
    } catch (error) {
        console.error('删除连接失败:', error);
        showToast('删除失败', 'error');
    }
}

function connectTo(connectionId) {
    selectedConnectionId = connectionId;
    navigateTo('client');
    document.getElementById('client-connection').value = connectionId;
}

async function startConnection() {
    const connectionId = document.getElementById('client-connection').value;
    let userId = document.getElementById('client-userid').value.trim();

    if (!connectionId) {
        showToast('请选择连接', 'warning');
        return;
    }

    if (!userId) {
        userId = '00000000-0000-0000-0000-000000000001';
    }

    const resolution = document.getElementById('client-resolution').value;
    const [width, height] = resolution.split('x').map(Number);
    const dpi = parseInt(document.getElementById('client-dpi').value);

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}${API_BASE}/ws?connectionId=${connectionId}&userId=${userId}`;

    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = function() {
            console.log('WebSocket连接已建立');
            document.getElementById('connection-status').classList.remove('d-none');
            document.getElementById('display-container').innerHTML = `
                <div style="width: ${width}px; height: ${height}px; background: #000; position: relative;">
                    <canvas id="guac-display" width="${width}" height="${height}" style="border: 1px solid #333;"></canvas>
                    <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px;">
                        <i class="bi bi-info-circle me-1"></i> 已连接 - ${width}x${height} @ ${dpi} DPI
                    </div>
                </div>
            `;
            showToast('连接已建立', 'success');
        };

        wsConnection.onmessage = function(event) {
            console.log('收到消息:', event.data.substring(0, 100));
        };

        wsConnection.onerror = function(error) {
            console.error('WebSocket错误:', error);
            showToast('连接错误', 'error');
        };

        wsConnection.onclose = function(event) {
            console.log('WebSocket连接已关闭:', event.code, event.reason);
            document.getElementById('connection-status').classList.add('d-none');
            document.getElementById('display-container').innerHTML = `
                <div style="text-align: center; color: #64748b;">
                    <i class="bi bi-display" style="font-size: 4rem; margin-bottom: 1rem;"></i>
                    <p>连接已断开</p>
                    <p class="small">代码: ${event.code} ${event.reason ? ' - ' + event.reason : ''}</p>
                </div>
            `;
        };
    } catch (error) {
        console.error('启动连接失败:', error);
        showToast('启动连接失败', 'error');
    }
}

function disconnectSession() {
    if (wsConnection) {
        wsConnection.close();
        wsConnection = null;
    }
    showToast('已断开连接', 'info');
}

async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions?limit=50`);
        const sessions = await response.json();
        const table = document.getElementById('sessions-table');

        if (sessions.length === 0) {
            table.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">暂无会话记录</td></tr>';
            return;
        }

        table.innerHTML = sessions.map(session => `
            <tr>
                <td><code class="text-info">${session.Id.substring(0, 8)}...</code></td>
                <td>${session.ConnectionName || session.ConnectionId.substring(0, 8)}</td>
                <td><span class="protocol-badge protocol-${session.Protocol.toLowerCase()}">${session.Protocol}</span></td>
                <td>${session.User?.Username || '未知'}</td>
                <td>${session.State === 2 ? '<span class="badge bg-success">已连接</span>' : '<span class="badge bg-secondary">已断开</span>'}</td>
                <td>${formatDate(session.ConnectedAt || session.CreatedAt)}</td>
                <td>${session.Duration ? formatDuration(session.Duration) : '-'}</td>
                <td>
                    ${session.State === 2 ? `
                        <button class="btn btn-sm btn-outline-danger" onclick="disconnectSessionById('${session.Id}')">
                            <i class="bi bi-stop-fill"></i>
                        </button>
                    ` : '<span class="text-muted">-</span>'}
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载会话失败:', error);
    }
}

async function disconnectSessionById(sessionId) {
    if (!confirm('确定要断开此会话吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}/disconnect`, { method: 'POST' });

        if (response.ok) {
            await loadSessions();
            await loadDashboard();
            showToast('会话已断开', 'success');
        } else {
            showToast('断开会话失败', 'error');
        }
    } catch (error) {
        console.error('断开会话失败:', error);
        showToast('断开会话失败', 'error');
    }
}

async function loadRecordings() {
    try {
        const response = await fetch(`${API_BASE}/recordings`);
        const recordings = await response.json();
        const table = document.getElementById('recordings-table');

        if (recordings.length === 0) {
            table.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">暂无录像记录</td></tr>';
            return;
        }

        table.innerHTML = recordings.map(rec => `
            <tr>
                <td><code class="text-info">${rec.Id.substring(0, 8)}...</code></td>
                <td>${rec.ConnectionName || rec.ConnectionId.substring(0, 8)}</td>
                <td><span class="protocol-badge protocol-${rec.Protocol.toLowerCase()}">${rec.Protocol}</span></td>
                <td>${rec.UserName || '未知'}</td>
                <td>${formatDate(rec.ConnectedAt)}</td>
                <td>${rec.Duration ? formatDuration(rec.Duration) : '-'}</td>
                <td>${formatBytes(rec.RecordingSizeBytes)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-light" onclick="downloadRecording('${rec.Id}')">
                        <i class="bi bi-download me-1"></i> 下载
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载录像失败:', error);
    }
}

async function downloadRecording(sessionId) {
    window.open(`${API_BASE}/recordings/${sessionId}/download`, '_blank');
}

function toggleProtocolFields() {
    const protocol = document.getElementById('conn-protocol').value;
    const rdpOnly = document.querySelectorAll('.rdp-only');

    rdpOnly.forEach(el => {
        el.style.display = protocol === 'RDP' ? 'block' : 'none';
    });
}

function getDefaultPort(protocol) {
    switch(protocol) {
        case 'RDP': return 3389;
        case 'VNC': return 5900;
        case 'SSH': return 22;
        default: return 3389;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDuration(ticks) {
    const seconds = Math.floor(ticks / 10000000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const bgColor = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    }[type] || 'bg-info';

    toast.className = `toast align-items-center text-white ${bgColor} border-0 position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}
