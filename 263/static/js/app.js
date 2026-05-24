let cy = null;
let currentGraphData = null;
let currentAnalysisResult = null;
let charts = {};
let monitorInterval = null;
let monitorRunning = false;

document.addEventListener('DOMContentLoaded', function() {
    initCytoscape();
    bindEvents();
});

function bindEvents() {
    document.getElementById('analysisForm').addEventListener('submit', function(e) {
        e.preventDefault();
        analyzeLog();
    });
}

function initCytoscape() {
    cy = cytoscape({
        container: document.getElementById('cyGraph'),
        elements: [],
        style: [
            {
                selector: 'node[type="deadlock"]',
                style: {
                    'background-color': '#e74c3c',
                    'label': 'data(label)',
                    'color': '#fff',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '14px',
                    'font-weight': 'bold',
                    'width': '60px',
                    'height': '60px',
                    'border-width': '2px',
                    'border-color': '#c0392b',
                    'shape': 'octagon'
                }
            },
            {
                selector: 'node[type="transaction"]',
                style: {
                    'background-color': '#3498db',
                    'label': 'data(label)',
                    'color': '#fff',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'font-weight': 'bold',
                    'width': '50px',
                    'height': '50px',
                    'border-width': '2px',
                    'border-color': '#2980b9',
                    'shape': 'roundrectangle'
                }
            },
            {
                selector: 'node[is_victim="true"]',
                style: {
                    'background-color': '#e67e22',
                    'border-color': '#d35400'
                }
            },
            {
                selector: 'node[type="lock"]',
                style: {
                    'background-color': '#2ecc71',
                    'label': 'data(label)',
                    'color': '#fff',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '11px',
                    'width': '45px',
                    'height': '45px',
                    'border-width': '2px',
                    'border-color': '#27ae60',
                    'shape': 'diamond'
                }
            },
            {
                selector: 'edge[type="involved"]',
                style: {
                    'width': 2,
                    'line-color': '#95a5a6',
                    'target-arrow-color': '#95a5a6',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'text-rotation': 'autorotate',
                    'font-size': '10px',
                    'color': '#7f8c8d'
                }
            },
            {
                selector: 'edge[type="waiting_for"]',
                style: {
                    'width': 3,
                    'line-color': '#e74c3c',
                    'target-arrow-color': '#e74c3c',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'text-rotation': 'autorotate',
                    'font-size': '10px',
                    'color': '#e74c3c',
                    'line-style': 'dashed'
                }
            },
            {
                selector: 'edge[type="held_by"]',
                style: {
                    'width': 2,
                    'line-color': '#27ae60',
                    'target-arrow-color': '#27ae60',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'text-rotation': 'autorotate',
                    'font-size': '10px',
                    'color': '#27ae60'
                }
            },
            {
                selector: 'edge[type="holds"]',
                style: {
                    'width': 2,
                    'line-color': '#3498db',
                    'target-arrow-color': '#3498db',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'text-rotation': 'autorotate',
                    'font-size': '10px',
                    'color': '#3498db'
                }
            }
        ],
        layout: {
            name: 'cose',
            animate: true,
            animationDuration: 500,
            nodeRepulsion: 800000,
            idealEdgeLength: 100,
            edgeElasticity: 100,
            padding: 50
        }
    });

    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        const data = node.data();
        showNodeInfo(data);
    });

    cy.on('tap', 'edge', function(evt) {
        const edge = evt.target;
        const data = edge.data();
        showEdgeInfo(data);
    });
}

function showNodeInfo(data) {
    let content = '';
    if (data.type === 'deadlock') {
        content = `
            <div class="alert alert-danger">
                <h6><i class="bi bi-shield-exclamation"></i> 死锁节点</h6>
                <p><strong>时间戳:</strong> ${data.timestamp || '未知'}</p>
                <p><strong>被选中牺牲的事务:</strong> ${data.victims ? data.victims.join(', ') : '无'}</p>
            </div>
        `;
    } else if (data.type === 'transaction') {
        content = `
            <div class="alert alert-primary">
                <h6><i class="bi bi-arrow-left-right"></i> 事务节点</h6>
                <p><strong>事务ID:</strong> ${data.txn_id}</p>
                <p><strong>状态:</strong> ${data.status}</p>
                <p><strong>是否被选中牺牲:</strong> ${data.is_victim ? '是' : '否'}</p>
                ${data.wait_time ? `<p><strong>等待时间:</strong> ${data.wait_time}秒</p>` : ''}
                ${data.sql_statements && data.sql_statements.length > 0 ? `
                    <p><strong>SQL语句:</strong></p>
                    ${data.sql_statements.map(sql => `<div class="sql-statement">${escapeHtml(sql)}</div>`).join('')}
                ` : ''}
            </div>
        `;
    } else if (data.type === 'lock') {
        content = `
            <div class="alert alert-success">
                <h6><i class="bi bi-lock"></i> 锁节点</h6>
                <p><strong>锁类型:</strong> ${data.lock_type}</p>
                <p><strong>锁模式:</strong> ${data.lock_mode}</p>
                <p><strong>表:</strong> ${data.table}</p>
                ${data.index ? `<p><strong>索引:</strong> ${data.index}</p>` : ''}
            </div>
        `;
    }

    if (content) {
        alert(content);
    }
}

function showEdgeInfo(data) {
    const typeNames = {
        'involved': '涉及',
        'waiting_for': '等待',
        'held_by': '被持有',
        'holds': '持有'
    };

    alert(`
        <div class="alert alert-info">
            <h6><i class="bi bi-arrow-right"></i> 边信息</h6>
            <p><strong>类型:</strong> ${typeNames[data.type] || data.type}</p>
            <p><strong>从:</strong> ${data.source}</p>
            <p><strong>到:</strong> ${data.target}</p>
        </div>
    `);
}

async function analyzeLog() {
    const btn = document.getElementById('analyzeBtn');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="loading"></span> 分析中...';
    btn.disabled = true;

    try {
        const formData = new FormData(document.getElementById('analysisForm'));
        const response = await fetch('/api/parse', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            currentAnalysisResult = result;
            renderResults(result);
            renderIndexRecommendations(result.index_recommendations);
            updateDeadlockSelectors(result.deadlocks);
            showAlert(result.message, 'success');
        }
    } catch (error) {
        showAlert('请求失败: ' + error.message, 'danger');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

function updateDeadlockSelectors(deadlocks) {
    const options = deadlocks.map((_, i) => `<option value="${i}">死锁 #${i + 1}</option>`).join('');
    
    const simSelect = document.getElementById('simDeadlockSelect');
    const apmSelect = document.getElementById('apmDeadlockSelect');
    
    simSelect.innerHTML = '<option value="">请选择死锁</option>' + options;
    apmSelect.innerHTML = '<option value="">请选择死锁</option>' + options;
}

function renderResults(result) {
    document.getElementById('summaryCard').style.display = 'block';
    document.getElementById('resultTabs').style.display = 'flex';

    const totalTxns = result.deadlocks.reduce((sum, d) => sum + d.transactions.length, 0);

    document.getElementById('totalDeadlocks').textContent = result.statistics.total_deadlocks || 0;
    document.getElementById('totalTxns').textContent = totalTxns;
    document.getElementById('totalTables').textContent = result.statistics.involved_tables ? result.statistics.involved_tables.length : 0;
    document.getElementById('avgWaitTime').textContent = (result.statistics.average_wait_time || 0).toFixed(1) + 's';
    document.getElementById('indexCount').textContent = result.index_recommendations ? result.index_recommendations.length : 0;
    document.getElementById('detectedVersion').textContent = result.detected_version || '-';

    renderDeadlocksList(result.deadlocks);
    renderGraph(result.graph);
    renderStatistics(result.statistics);
    renderSuggestions(result.suggestions);
    renderDeadlockSelector(result.deadlocks.length);
}

function renderIndexRecommendations(recommendations) {
    const container = document.getElementById('indexContent');
    
    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">暂无索引建议</p>';
        return;
    }

    let html = '';
    recommendations.forEach((rec, index) => {
        const benefitClass = rec.estimated_benefit > 70 ? 'text-success' : rec.estimated_benefit > 40 ? 'text-warning' : 'text-info';
        
        html += `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="bi bi-search text-info"></i>
                            表: <strong>${rec.table_name}</strong>
                        </h6>
                        <span class="badge ${benefitClass}">预计收益: ${rec.estimated_benefit}%</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="mb-2">
                        <strong>建议索引:</strong> ${rec.index_name} (${rec.index_columns.join(', ')})
                    </div>
                    <div class="mb-2 text-muted small">
                        <i class="bi bi-info-circle"></i> ${rec.reason}
                    </div>
                    <div class="mb-2">
                        <strong>创建语句:</strong>
                        <code class="d-block bg-light p-2 mt-1">${rec.create_statement}</code>
                    </div>
                    ${rec.sql_sample ? `
                        <div>
                            <strong>相关SQL示例:</strong>
                            <div class="sql-statement small mt-1">${escapeHtml(rec.sql_sample)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderDeadlocksList(deadlocks) {
    const container = document.getElementById('deadlocksContent');

    if (!deadlocks || deadlocks.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">未检测到死锁</p>';
        return;
    }

    let html = '';
    deadlocks.forEach((deadlock, index) => {
        html += `
            <div class="card deadlock-card mb-3">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="bi bi-shield-exclamation text-danger"></i>
                            死锁 #${index + 1}
                            ${deadlock.timestamp ? `<span class="text-muted ms-2 small">${deadlock.timestamp}</span>` : ''}
                        </h6>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-warning" onclick="runSimulationForIndex(${index})">
                                <i class="bi bi-play"></i> 模拟
                            </button>
                            <button class="btn btn-sm btn-outline-dark" onclick="correlateAPMForIndex(${index})">
                                <i class="bi bi-link-45deg"></i> APM
                            </button>
                            <button class="btn btn-sm btn-outline-primary" onclick="showDeadlockDetail(${index})">
                                <i class="bi bi-eye"></i> 详情
                            </button>
                        </div>
                    </div>
                    ${deadlock.victim_txns && deadlock.victim_txns.length > 0 ? `
                        <div class="mt-2 small text-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            被选中牺牲的事务: ${deadlock.victim_txns.join(', ')}
                        </div>
                    ` : ''}
                </div>
                <div class="card-body">
                    <div class="row">
                        ${deadlock.transactions.map(txn => renderTransactionCard(txn, deadlock.victim_txns)).join('')}
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function runSimulationForIndex(index) {
    document.getElementById('simDeadlockSelect').value = index;
    const tabTrigger = document.querySelector('a[href="#simulationTab"]');
    const tab = new bootstrap.Tab(tabTrigger);
    tab.show();
    runSimulation();
}

function correlateAPMForIndex(index) {
    document.getElementById('apmDeadlockSelect').value = index;
    const tabTrigger = document.querySelector('a[href="#apmTab"]');
    const tab = new bootstrap.Tab(tabTrigger);
    tab.show();
    correlateAPM();
}

function renderTransactionCard(txn, victimTxns) {
    const isVictim = victimTxns && victimTxns.includes(txn.txn_id);
    return `
        <div class="col-md-6 mb-3">
            <div class="card transaction-card ${isVictim ? 'victim' : ''}">
                <div class="card-header bg-light py-2">
                    <h6 class="mb-0 small">
                        <i class="bi ${isVictim ? 'bi-exclamation-triangle text-warning' : 'bi-arrow-left-right text-primary'}"></i>
                        事务 ${txn.txn_id}
                        <span class="badge ${txn.status === 'WAITING' ? 'bg-warning' : 'bg-info'} ms-2">${txn.status}</span>
                        ${isVictim ? '<span class="badge bg-danger ms-1">被选中牺牲</span>' : ''}
                    </h6>
                </div>
                <div class="card-body p-2">
                    ${txn.wait_time ? `<div class="small text-muted mb-2">等待时间: ${txn.wait_time}秒</div>` : ''}

                    ${txn.holding_locks && txn.holding_locks.length > 0 ? `
                        <div class="mb-2">
                            <div class="small text-success mb-1"><i class="bi bi-lock-fill"></i> 持有的锁:</div>
                            ${txn.holding_locks.map(lock => `
                                <div class="lock-info holding-lock">
                                    ${lock.lock_mode} on ${lock.table_name}
                                    ${lock.index_name ? `(索引: ${lock.index_name})` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    ${txn.waiting_lock ? `
                        <div class="mb-2">
                            <div class="small text-danger mb-1"><i class="bi bi-hourglass-split"></i> 等待的锁:</div>
                            <div class="lock-info waiting-lock">
                                ${txn.waiting_lock.lock_mode} on ${txn.waiting_lock.table_name}
                                ${txn.waiting_lock.index_name ? `(索引: ${txn.waiting_lock.index_name})` : ''}
                            </div>
                        </div>
                    ` : ''}

                    ${txn.sql_statements && txn.sql_statements.length > 0 ? `
                        <div>
                            <div class="small text-primary mb-1"><i class="bi bi-code-slash"></i> 执行的SQL:</div>
                            ${txn.sql_statements.map(sql => `<div class="sql-statement">${escapeHtml(sql)}</div>`).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

function showDeadlockDetail(index) {
    const deadlock = currentAnalysisResult.deadlocks[index];
    const modal = new bootstrap.Modal(document.getElementById('deadlockDetailModal'));
    const content = document.getElementById('deadlockDetailContent');

    content.innerHTML = `
        <h5><i class="bi bi-shield-exclamation text-danger"></i> 死锁 #${index + 1} 详情</h5>
        <p class="text-muted">${deadlock.timestamp || '时间戳未知'}</p>

        ${deadlock.victim_txns && deadlock.victim_txns.length > 0 ? `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>被选中牺牲的事务:</strong> ${deadlock.victim_txns.join(', ')}
            </div>
        ` : ''}

        <h6 class="mt-3">事务详情:</h6>
        <div class="row">
            ${deadlock.transactions.map(txn => renderTransactionDetail(txn, deadlock.victim_txns)).join('')}
        </div>

        <h6 class="mt-3">原始日志:</h6>
        <pre class="small">${escapeHtml(deadlock.raw_log || '无')}</pre>
    `;

    modal.show();
}

function renderTransactionDetail(txn, victimTxns) {
    const isVictim = victimTxns && victimTxns.includes(txn.txn_id);
    return `
        <div class="col-md-6 mb-3">
            <div class="card transaction-card ${isVictim ? 'victim' : ''}">
                <div class="card-header">
                    <h6 class="mb-0">
                        事务 ${txn.txn_id}
                        ${isVictim ? '<span class="badge bg-danger ms-2">被选中牺牲</span>' : ''}
                    </h6>
                </div>
                <div class="card-body">
                    <p><strong>状态:</strong> ${txn.status}</p>
                    ${txn.start_time ? `<p><strong>开始时间:</strong> ${txn.start_time}</p>` : ''}
                    ${txn.wait_time ? `<p><strong>等待时间:</strong> ${txn.wait_time}秒</p>` : ''}

                    ${txn.holding_locks && txn.holding_locks.length > 0 ? `
                        <p><strong>持有的锁:</strong></p>
                        ${txn.holding_locks.map(lock => `
                            <div class="lock-info holding-lock">
                                <strong>${lock.lock_mode}</strong> on <strong>${lock.table_name}</strong>
                                ${lock.index_name ? `<br>索引: ${lock.index_name}` : ''}
                                ${lock.record_info ? `<br>记录: ${lock.record_info}` : ''}
                            </div>
                        `).join('')}
                    ` : ''}

                    ${txn.waiting_lock ? `
                        <p class="mt-2"><strong>等待的锁:</strong></p>
                        <div class="lock-info waiting-lock">
                            <strong>${txn.waiting_lock.lock_mode}</strong> on <strong>${txn.waiting_lock.table_name}</strong>
                            ${txn.waiting_lock.index_name ? `<br>索引: ${txn.waiting_lock.index_name}` : ''}
                            ${txn.waiting_lock.record_info ? `<br>记录: ${txn.waiting_lock.record_info}` : ''}
                        </div>
                    ` : ''}

                    ${txn.sql_statements && txn.sql_statements.length > 0 ? `
                        <p class="mt-2"><strong>执行的SQL:</strong></p>
                        ${txn.sql_statements.map(sql => `<div class="sql-statement">${escapeHtml(sql)}</div>`).join('')}
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

function renderGraph(graphData) {
    currentGraphData = graphData;

    cy.elements().remove();
    cy.add(graphData.elements);

    const layout = cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 800,
        nodeRepulsion: 800000,
        idealEdgeLength: 120,
        edgeElasticity: 100,
        padding: 60
    });

    layout.run();
}

function renderStatistics(statistics) {
    renderTableChart(statistics.table_stats);
    renderTimeChart(statistics.time_distribution);
    renderLockChart(statistics.lock_mode_stats);
    renderTopTables(statistics.table_stats);
}

function renderTableChart(tableStats) {
    const ctx = document.getElementById('tableChart').getContext('2d');

    if (charts.tableChart) {
        charts.tableChart.destroy();
    }

    const labels = Object.keys(tableStats || {}).slice(0, 10);
    const data = Object.values(tableStats || {}).slice(0, 10);

    charts.tableChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '死锁次数',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } }
            }
        }
    });
}

function renderTimeChart(timeDistribution) {
    const ctx = document.getElementById('timeChart').getContext('2d');

    if (charts.timeChart) {
        charts.timeChart.destroy();
    }

    const labels = Object.keys(timeDistribution || {});
    const data = Object.values(timeDistribution || {});

    charts.timeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function renderLockChart(lockModeStats) {
    const ctx = document.getElementById('lockChart').getContext('2d');

    if (charts.lockChart) {
        charts.lockChart.destroy();
    }

    const labels = Object.keys(lockModeStats || {});
    const data = Object.values(lockModeStats || {});

    charts.lockChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(231, 76, 60, 0.7)',
                    'rgba(46, 204, 113, 0.7)',
                    'rgba(52, 152, 219, 0.7)',
                    'rgba(155, 89, 182, 0.7)',
                    'rgba(241, 196, 15, 0.7)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function renderTopTables(tableStats) {
    const container = document.getElementById('topTables');
    const entries = Object.entries(tableStats || {}).sort((a, b) => b[1] - a[1]).slice(0, 10);

    if (entries.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无数据</p>';
        return;
    }

    const maxCount = entries[0][1];

    let html = '';
    entries.forEach(([table, count]) => {
        const percentage = (count / maxCount * 100).toFixed(1);
        html += `
            <div class="table-stats-row">
                <div>
                    <i class="bi bi-table text-primary"></i>
                    <strong>${table}</strong>
                </div>
                <div class="text-end">
                    <span class="badge bg-primary me-2">${count}</span>
                    <div class="d-inline-block" style="width: 100px;">
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar bg-primary" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderSuggestions(suggestions) {
    const container = document.getElementById('suggestionsContent');

    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">暂无优化建议</p>';
        return;
    }

    let html = '';
    suggestions.forEach((suggestion, index) => {
        const priorityClass = suggestion.priority;
        const priorityText = { high: '高', medium: '中', low: '低' }[suggestion.priority] || suggestion.priority;
        const priorityBadgeClass = `badge-priority-${suggestion.priority}`;

        html += `
            <div class="card suggestion-card ${priorityClass}">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <span class="badge ${priorityBadgeClass} me-2">${priorityText}优先级</span>
                            ${suggestion.category}: ${suggestion.title}
                        </h6>
                        <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="collapse" data-bs-target="#suggestion-${index}">
                            <i class="bi bi-chevron-down"></i>
                        </button>
                    </div>
                </div>
                <div id="suggestion-${index}" class="collapse ${index === 0 ? 'show' : ''}">
                    <div class="card-body">
                        <p class="mb-3">${suggestion.description}</p>

                        ${suggestion.affected_tables && suggestion.affected_tables.length > 0 ? `
                            <p class="mb-2"><strong>受影响的表:</strong></p>
                            <div class="mb-3">
                                ${suggestion.affected_tables.map(t => `<span class="badge bg-secondary me-1">${t}</span>`).join('')}
                            </div>
                        ` : ''}

                        ${suggestion.affected_sql_patterns && suggestion.affected_sql_patterns.length > 0 ? `
                            <p class="mb-2"><strong>相关SQL模式:</strong></p>
                            ${suggestion.affected_sql_patterns.map(sql => `<div class="sql-statement">${escapeHtml(sql)}</div>`).join('')}
                        ` : ''}

                        <div class="alert alert-info mb-3">
                            <h6><i class="bi bi-lightbulb"></i> 建议操作:</h6>
                            <p class="mb-0" style="white-space: pre-line;">${suggestion.suggested_action}</p>
                        </div>

                        <div class="text-end">
                            <span class="text-muted small">预期影响: ${suggestion.estimated_impact}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderDeadlockSelector(count) {
    const selector = document.getElementById('deadlockSelector');
    let options = '<option value="-1">查看全部死锁</option>';

    for (let i = 0; i < count; i++) {
        options += `<option value="${i}">死锁 #${i + 1}</option>`;
    }

    selector.innerHTML = options;
}

async function viewSingleDeadlock() {
    const selector = document.getElementById('deadlockSelector');
    const index = parseInt(selector.value);

    if (index === -1) {
        if (currentGraphData) {
            renderGraph(currentGraphData);
        }
        return;
    }

    const logContent = document.getElementById('logContent').value;
    const dbType = document.getElementById('dbType').value;

    try {
        const response = await fetch(`/api/graph/${index}?db_type=${dbType}&log_content=${encodeURIComponent(logContent)}`);
        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            renderGraph(result.graph);
        }
    } catch (error) {
        showAlert('请求失败: ' + error.message, 'danger');
    }
}

function fitGraph() {
    cy.fit(50);
}

function exportGraph() {
    const png = cy.png({ full: true, scale: 2 });
    const link = document.createElement('a');
    link.download = 'deadlock-graph.png';
    link.href = png;
    link.click();
}

async function loadSample(dbType) {
    try {
        const response = await fetch(`/api/sample/${dbType}`);
        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            document.getElementById('dbType').value = dbType;
            document.getElementById('logContent').value = result.content;
            showAlert(`已加载 ${dbType.toUpperCase()} 示例日志`, 'success');
        }
    } catch (error) {
        showAlert('加载示例失败: ' + error.message, 'danger');
    }
}

function clearAll() {
    document.getElementById('analysisForm').reset();
    document.getElementById('summaryCard').style.display = 'none';
    document.getElementById('resultTabs').style.display = 'none';
    cy.elements().remove();
    currentGraphData = null;
    currentAnalysisResult = null;

    Object.values(charts).forEach(chart => chart.destroy());
    charts = {};
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show fixed-top mx-auto mt-4`;
    alertDiv.style.maxWidth = '500px';
    alertDiv.style.left = '0';
    alertDiv.style.right = '0';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        <i class="bi bi-${type === 'danger' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startMonitor() {
    try {
        const dbType = document.getElementById('dbType').value;
        
        const response = await fetch('/api/monitor/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ db_type: dbType })
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            monitorRunning = true;
            document.getElementById('startMonitorBtn').disabled = true;
            document.getElementById('stopMonitorBtn').disabled = false;
            updateMonitorStatus(result.status);
            
            monitorInterval = setInterval(pollMonitorStatus, 5000);
            
            showAlert('实时监控已启动，每5秒检测一次', 'success');
        }
    } catch (error) {
        showAlert('启动监控失败: ' + error.message, 'danger');
    }
}

async function stopMonitor() {
    try {
        const response = await fetch('/api/monitor/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            monitorRunning = false;
            document.getElementById('startMonitorBtn').disabled = false;
            document.getElementById('stopMonitorBtn').disabled = true;
            updateMonitorStatus(result.status);
            
            if (monitorInterval) {
                clearInterval(monitorInterval);
                monitorInterval = null;
            }
            
            showAlert('实时监控已停止', 'info');
        }
    } catch (error) {
        showAlert('停止监控失败: ' + error.message, 'danger');
    }
}

async function pollMonitorStatus() {
    if (!monitorRunning) return;
    
    try {
        await checkMonitorNow();
    } catch (e) {
        console.error('Poll error:', e);
    }
}

async function checkMonitorNow() {
    try {
        const response = await fetch('/api/monitor/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            updateMonitorStatus(result.status);
            renderMonitorAlerts(result.alerts);
            renderLockWaits(result.lock_waits);
        }
    } catch (error) {
        console.error('Check error:', error);
    }
}

function updateMonitorStatus(status) {
    const statusEl = document.getElementById('monitorStatus');
    const checksEl = document.getElementById('monitorChecks');

    if (status.is_running) {
        statusEl.textContent = '运行中';
        statusEl.className = 'fw-bold text-success';
    } else {
        statusEl.textContent = '未启动';
        statusEl.className = 'fw-bold text-secondary';
    }

    checksEl.textContent = status.total_checks || 0;
}

function renderMonitorAlerts(alerts) {
    const container = document.getElementById('monitorAlerts');

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="text-muted small"><i class="bi bi-check-circle text-success"></i> 暂无异常</div>';
        return;
    }

    const criticalCount = alerts.filter(a => a.level === 'critical').length;
    const warningCount = alerts.filter(a => a.level === 'warning').length;

    if (criticalCount > 0) {
        const alertToast = document.getElementById('alertToast');
        const toastBody = document.getElementById('alertToastBody');
        toastBody.textContent = `检测到 ${criticalCount} 个潜在死锁！请立即查看。`;
        const toast = new bootstrap.Toast(alertToast);
        toast.show();
    }

    let html = `<div class="mb-2">
        <span class="badge bg-danger me-1">严重: ${criticalCount}</span>
        <span class="badge bg-warning me-1">警告: ${warningCount}</span>
    </div>`;

    alerts.slice(0, 5).forEach(alert => {
        const bgClass = alert.level === 'critical' ? 'bg-danger' : 'bg-warning';
        html += `
            <div class="alert ${bgClass} text-white p-2 mb-2 small">
                <div class="d-flex justify-content-between">
                    <strong>${alert.title}</strong>
                    <small>${alert.timestamp}</small>
                </div>
                <div>${alert.message}</div>
            </div>
        `;
    });

    if (alerts.length > 5) {
        html += `<div class="text-center"><small class="text-muted">还有 ${alerts.length - 5} 条告警...</small></div>`;
    }

    container.innerHTML = html;
}

function renderLockWaits(lockWaits) {
    if (!lockWaits || lockWaits.length === 0) return;

    const container = document.getElementById('monitorAlerts');
    
    let html = container.innerHTML + `<div class="mt-3">
        <h6 class="small text-muted"><i class="bi bi-clock"></i> 当前锁等待 (${lockWaits.length})</h6>
    </div>`;

    lockWaits.slice(0, 3).forEach(wait => {
        const durationClass = wait.wait_duration > 10 ? 'text-danger' : wait.wait_duration > 5 ? 'text-warning' : 'text-info';
        html += `
            <div class="small border-start border-3 border-warning ps-2 mb-2">
                <div>事务 ${wait.waiting_txn_id} <i class="bi bi-arrow-right"></i> ${wait.holding_txn_id}</div>
                <div class="${durationClass}">${wait.lock_mode} on ${wait.table_name} - ${wait.wait_duration}s</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

async function runSimulation() {
    const index = parseInt(document.getElementById('simDeadlockSelect').value);
    
    if (isNaN(index) || !currentAnalysisResult) {
        showAlert('请先解析死锁日志并选择死锁', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/simulate/${index}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            document.getElementById('simulationResults').style.display = 'block';
            renderSimulationSteps(result);
            renderOrderTests(result.order_tests);
        }
    } catch (error) {
        showAlert('模拟失败: ' + error.message, 'danger');
    }
}

function renderSimulationSteps(result) {
    const originalContainer = document.getElementById('originalSteps');
    const optimizedContainer = document.getElementById('optimizedSteps');

    let originalHtml = `<div class="mb-2">
        <span class="badge ${result.simulation_result.original_has_deadlock ? 'bg-danger' : 'bg-success'}">
            ${result.simulation_result.original_has_deadlock ? '发生死锁' : '无死锁'}
        </span>
    </div>`;

    result.original_steps.forEach(step => {
        const stepBg = step.is_deadlock ? 'bg-danger text-white' : 'bg-light';
        originalHtml += `
            <div class="sim-step border ${stepBg} p-2 mb-2 rounded">
                <div class="d-flex justify-content-between small">
                    <strong>T=${step.time.toFixed(1)}s</strong>
                    <span>${step.description}</span>
                </div>
                ${step.operations.map(op => `
                    <div class="small mt-1 ${op.is_waiting ? 'text-warning' : ''}">
                        <i class="bi bi-${op.is_waiting ? 'hourglass-split' : 'check-circle'}"></i>
                        Txn ${op.txn_id}: ${op.operation_type} ${op.lock_mode} on ${op.table_name}
                        ${op.is_waiting ? ' <strong>(等待)</strong>' : ''}
                    </div>
                `).join('')}
            </div>
        `;
    });

    originalContainer.innerHTML = originalHtml;

    let optimizedHtml = `<div class="mb-2">
        <span class="badge ${result.simulation_result.optimized_has_deadlock ? 'bg-danger' : 'bg-success'}">
            ${result.simulation_result.optimized_has_deadlock ? '仍存在死锁' : '死锁已消除'}
        </span>
    </div>`;

    result.optimized_steps.forEach(step => {
        const stepBg = step.is_deadlock ? 'bg-danger text-white' : 'bg-light';
        optimizedHtml += `
            <div class="sim-step border ${stepBg} p-2 mb-2 rounded">
                <div class="d-flex justify-content-between small">
                    <strong>T=${step.time.toFixed(1)}s</strong>
                    <span>${step.description}</span>
                </div>
                ${step.operations.map(op => `
                    <div class="small mt-1 ${op.is_waiting ? 'text-warning' : ''}">
                        <i class="bi bi-${op.is_waiting ? 'hourglass-split' : 'check-circle'}"></i>
                        Txn ${op.txn_id}: ${op.operation_type} ${op.lock_mode} on ${op.table_name}
                        ${op.is_waiting ? ' <strong>(等待)</strong>' : ''}
                    </div>
                `).join('')}
            </div>
        `;
    });

    optimizedContainer.innerHTML = optimizedHtml;
}

function renderOrderTests(orderTests) {
    const container = document.getElementById('orderTests');

    if (!orderTests || orderTests.length === 0) {
        container.innerHTML = '<p class="text-muted">无多种顺序测试结果</p>';
        return;
    }

    let html = '<div class="row">';

    orderTests.forEach((test, index) => {
        const bgClass = test.has_deadlock ? 'bg-danger text-white' : 'bg-success text-white';
        const iconClass = test.has_deadlock ? 'bi-x-circle' : 'bi-check-circle';

        html += `
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-header ${bgClass} py-2">
                        <h6 class="mb-0 small">
                            <i class="bi ${iconClass}"></i>
                            方案 ${index + 1}
                            ${test.is_original ? ' (原始)' : ''}
                            ${test.is_optimized ? ' (推荐)' : ''}
                        </h6>
                    </div>
                    <div class="card-body p-2">
                        <div class="small mb-2">
                            <strong>事务顺序:</strong> ${test.transaction_order.join(' → ')}
                        </div>
                        <div class="small">
                            <strong>结果:</strong> ${test.has_deadlock ? '死锁' : '正常执行'}
                        </div>
                        ${test.description ? `<div class="small text-muted mt-2">${test.description}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

async function configureAPM() {
    const apmType = document.getElementById('apmType').value;
    const baseUrl = document.getElementById('apmUrl').value;
    const serviceName = document.getElementById('apmService').value;

    try {
        const response = await fetch('/api/apm/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                apm_type: apmType,
                config: {
                    base_url: baseUrl,
                    service_name: serviceName
                }
            })
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            showAlert(result.message, 'success');
        }
    } catch (error) {
        showAlert('配置APM失败: ' + error.message, 'danger');
    }
}

async function correlateAPM() {
    const index = parseInt(document.getElementById('apmDeadlockSelect').value);
    const before = parseInt(document.getElementById('beforeWindow').value);
    const after = parseInt(document.getElementById('afterWindow').value);

    if (isNaN(index) || !currentAnalysisResult) {
        showAlert('请先解析死锁日志并选择死锁', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/apm/correlate/${index}?before=${before}&after=${after}`, {
            method: 'GET'
        });

        const result = await response.json();

        if (result.error) {
            showAlert(result.error, 'danger');
        } else {
            document.getElementById('apmResults').style.display = 'block';
            renderAPMCorrelations(result);
        }
    } catch (error) {
        showAlert('APM关联失败: ' + error.message, 'danger');
    }
}

function renderAPMCorrelations(result) {
    const container = document.getElementById('apmContent');

    if (!result.correlations || result.correlations.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">未找到关联的调用链</p>';
        return;
    }

    let html = '';

    result.correlations.forEach((corr, index) => {
        html += `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="bi bi-link-45deg text-dark"></i>
                            关联 #${index + 1} - 事务 ${corr.transaction_id}
                        </h6>
                        <span class="badge bg-info">相关度: ${(corr.correlation_score * 100).toFixed(0)}%</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-md-6">
                            <small class="text-muted">Trace ID</small>
                            <div><strong>${corr.trace_id}</strong></div>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">服务</small>
                            <div>${corr.service_name || '-'}</div>
                        </div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-6">
                            <small class="text-muted">操作</small>
                            <div>${corr.operation_name || '-'}</div>
                        </div>
                        <div class="col-md-6">
                            <small class="text-muted">耗时</small>
                            <div>${corr.duration_ms ? corr.duration_ms + 'ms' : '-'}</div>
                        </div>
                    </div>
                    ${corr.matched_sql ? `
                        <div class="mb-2">
                            <small class="text-muted">匹配的SQL:</small>
                            <div class="sql-statement small mt-1">${escapeHtml(corr.matched_sql)}</div>
                        </div>
                    ` : ''}
                    ${result.trace_links && result.trace_links[index] ? `
                        <div class="mt-2">
                            <a href="${result.trace_links[index].url}" target="_blank" class="btn btn-dark btn-sm">
                                <i class="bi bi-box-arrow-up-right"></i> 查看调用链详情
                            </a>
                        </div>
                    ` : ''}
                    ${corr.spans && corr.spans.length > 0 ? `
                        <div class="mt-3">
                            <small class="text-muted d-block mb-2">调用栈:</small>
                            ${corr.spans.map(span => `
                                <div class="ps-3 py-1 border-start border-2 ${span.has_error ? 'border-danger' : 'border-primary'} mb-1">
                                    <div class="small">
                                        <i class="bi bi-arrow-right"></i>
                                        <strong>${span.operation_name}</strong>
                                        <span class="text-muted ms-2">${span.duration_ms}ms</span>
                                        ${span.has_error ? '<span class="text-danger ms-2"><i class="bi bi-exclamation-triangle"></i> 错误</span>' : ''}
                                    </div>
                                    ${span.component ? `<div class="text-muted small ms-4">${span.component}</div>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}
