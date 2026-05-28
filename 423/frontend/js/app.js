let topologyGraph;
let analysisPanel;
let faultPanel;
let historyPanel;
let currentTimeWindow = 60;

document.addEventListener("DOMContentLoaded", function() {
    topologyGraph = new TopologyGraph("topologyGraph");
    analysisPanel = new AnalysisPanel();
    faultPanel = new FaultPanel();
    historyPanel = new HistoryPanel();

    setupEventListeners();
    loadAllData();
});

function setupEventListeners() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });

    document.getElementById("timeWindowSelect").addEventListener("change", function() {
        currentTimeWindow = parseInt(this.value);
        loadTopology();
    });

    document.getElementById("refreshBtn").addEventListener("click", loadAllData);
    document.getElementById("importBtn").addEventListener("click", importTraces);
    document.getElementById("snapshotBtn").addEventListener("click", createSnapshot);

    document.getElementById("analyzeFaultBtn").addEventListener("click", function() {
        faultPanel.analyzeFault();
    });

    document.getElementById("compareBtn").addEventListener("click", function() {
        historyPanel.compareSnapshots();
    });

    document.getElementById("listSnapshotsBtn").addEventListener("click", function() {
        historyPanel.loadSnapshots();
    });

    document.getElementById("collapseAllBtn").addEventListener("click", function() {
        if (topologyGraph) {
            topologyGraph.collapseAllGroups();
        }
    });

    document.getElementById("expandAllBtn").addEventListener("click", function() {
        if (topologyGraph) {
            topologyGraph.expandAllGroups();
        }
    });

    document.getElementById("animateBtn").addEventListener("click", function() {
        const selectedNode = topologyGraph.selectedNode;
        if (!selectedNode) {
            alert("请先在拓扑图中选择一个服务作为起点");
            return;
        }
        startAnimation(selectedNode.name);
    });

    document.getElementById("animateCriticalBtn").addEventListener("click", function() {
        if (topologyGraph) {
            topologyGraph.animateCriticalPaths();
            showAnimationUI();
        }
    });

    document.getElementById("stopAnimateBtn").addEventListener("click", function() {
        if (topologyGraph) {
            topologyGraph.stopAnimation();
        }
        hideAnimationUI();
    });

    document.getElementById("analyzeVersionBtn").addEventListener("click", analyzeVersionImpact);

    topologyGraph.onSelectNode = function(node) {
        showServiceDetails(node);
        if (node && node.type !== "message_queue") {
            const versionSelect = document.getElementById("versionServiceSelect");
            if (versionSelect) {
                versionSelect.value = node.name;
            }
        }
    };
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.remove("active");
    });

    document.querySelector(`.tab-btn[data-tab="${tabName}"]`).classList.add("active");
    document.getElementById(tabName).classList.add("active");

    if (tabName === "fault") {
        faultPanel.loadServices();
        faultPanel.loadBroadcastRisk();
    } else if (tabName === "history") {
        historyPanel.loadSnapshots();
    } else if (tabName === "analysis") {
        loadVersionServices();
    }
}

async function loadAllData() {
    await loadTopology();
    analysisPanel.loadAnalysis();
}

async function loadTopology() {
    try {
        const topologyResponse = fetch(`${API_BASE}/topology?time_window=${currentTimeWindow}`);
        const layersResponse = fetch(`${API_BASE}/topology/layers?time_window=${currentTimeWindow}`);

        const [topologyResult, layersResult] = await Promise.all([topologyResponse, layersResponse]);

        const topologyData = await topologyResult.json();
        const layersData = await layersResult.json();

        topologyGraph.update(topologyData, layersData);
        updateStats(topologyData);
        updateLayerFilter(topologyData);
    } catch (error) {
        console.error("加载拓扑数据失败:", error);
    }
}

function updateStats(topologyData) {
    const totalCalls = topologyData.edges.reduce((sum, e) => sum + (e.call_count || 0), 0);
    const totalErrors = topologyData.edges.reduce((sum, e) => sum + (e.error_count || 0), 0);
    const totalLatency = topologyData.edges.reduce((sum, e) => sum + (e.total_latency || 0), 0);

    document.getElementById("statServices").textContent = topologyData.services.length;
    document.getElementById("statEdges").textContent = topologyData.edges.length;
    document.getElementById("statCalls").textContent = totalCalls.toLocaleString();
    document.getElementById("statErrors").textContent = totalErrors.toLocaleString();
    document.getElementById("statErrorRate").textContent =
        totalCalls > 0 ? (totalErrors / totalCalls * 100).toFixed(2) + "%" : "0%";
    document.getElementById("statLatency").textContent =
        totalCalls > 0 ? (totalLatency / totalCalls).toFixed(0) + "μs" : "0μs";
}

function updateLayerFilter(topologyData) {
    const layers = new Set();
    topologyData.nodes.forEach(node => {
        if (node.layer) layers.add(node.layer);
    });

    const select = document.getElementById("layerFilter");
    select.innerHTML = '<option value="all">全部</option>';
    [...layers].sort().forEach(layer => {
        const option = document.createElement("option");
        option.value = layer;
        option.textContent = `L${layer}`;
        select.appendChild(option);
    });
}

function showServiceDetails(node) {
    const container = document.getElementById("serviceDetails");

    if (!node) {
        container.innerHTML = '<p class="placeholder">选择图中的服务节点查看详情</p>';
        return;
    }

    fetch(`${API_BASE}/topology?time_window=${currentTimeWindow}`)
        .then(r => r.json())
        .then(topologyData => {
            const incoming = topologyData.edges.filter(e => e.target === node.name);
            const outgoing = topologyData.edges.filter(e => e.source === node.name);

            const errorRate = node.call_count > 0
                ? (node.error_count / node.call_count * 100).toFixed(2)
                : "0";

            let html = `
                <div class="service-info">
                    <div>
                        <h3 style="color: #58a6ff; margin-bottom: 12px;">${node.name}</h3>
                        <div class="service-metrics">
                            <div class="metric-box">
                                <div class="value">${node.call_count || 0}</div>
                                <div class="label">调用次数</div>
                            </div>
                            <div class="metric-box">
                                <div class="value">${node.error_count || 0}</div>
                                <div class="label">错误次数</div>
                            </div>
                            <div class="metric-box">
                                <div class="value">${errorRate}%</div>
                                <div class="label">错误率</div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <div class="metric-box">
                            <div class="value">L${node.layer || 0}</div>
                            <div class="label">层级</div>
                        </div>
                    </div>
                </div>
            `;

            if (incoming.length > 0 || outgoing.length > 0) {
                html += '<div class="dependencies-list">';

                if (incoming.length > 0) {
                    html += '<h4 style="color: #8b949e; margin: 16px 0 8px;">⬆️ 上游依赖 (' + incoming.length + ')</h4>';
                    incoming.forEach(edge => {
                        const errorClass = edge.error_rate > 0.05 ? "error" :
                            edge.error_rate > 0.01 ? "warning" : "";
                        html += `
                            <div class="dep-item ${errorClass}">
                                <span class="service-name">${edge.source}</span>
                                <div class="metrics">
                                    <span>调用: ${edge.call_count}</span>
                                    <span>错误: ${edge.error_count}</span>
                                    <span>延迟: ${edge.avg_latency.toFixed(0)}μs</span>
                                </div>
                            </div>
                        `;
                    });
                }

                if (outgoing.length > 0) {
                    html += '<h4 style="color: #8b949e; margin: 16px 0 8px;">⬇️ 下游依赖 (' + outgoing.length + ')</h4>';
                    outgoing.forEach(edge => {
                        const errorClass = edge.error_rate > 0.05 ? "error" :
                            edge.error_rate > 0.01 ? "warning" : "";
                        html += `
                            <div class="dep-item ${errorClass}">
                                <span class="service-name">${edge.target}</span>
                                <div class="metrics">
                                    <span>调用: ${edge.call_count}</span>
                                    <span>错误: ${edge.error_count}</span>
                                    <span>延迟: ${edge.avg_latency.toFixed(0)}μs</span>
                                </div>
                            </div>
                        `;
                    });
                }

                html += "</div>";
            }

            container.innerHTML = html;
        });
}

async function importTraces() {
    const modal = document.getElementById("modal");
    const modalBody = document.getElementById("modalBody");
    const modalTitle = document.getElementById("modalTitle");

    modalTitle.textContent = "导入Trace数据";
    modalBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 12px;">
            <div>
                <label style="display: block; margin-bottom: 6px; color: #8b949e;">服务名称 (可选)</label>
                <input type="text" id="importService" placeholder="留空导入所有服务"
                    style="width: 100%; padding: 8px 12px; background: #21262d; color: #c9d1d9;
                    border: 1px solid #30363d; border-radius: 6px;">
            </div>
            <div>
                <label style="display: block; margin-bottom: 6px; color: #8b949e;">时间范围</label>
                <select id="importLookback"
                    style="width: 100%; padding: 8px 12px; background: #21262d; color: #c9d1d9;
                    border: 1px solid #30363d; border-radius: 6px;">
                    <option value="15m">最近15分钟</option>
                    <option value="1h" selected>最近1小时</option>
                    <option value="2h">最近2小时</option>
                    <option value="6h">最近6小时</option>
                    <option value="24h">最近24小时</option>
                </select>
            </div>
            <div>
                <label style="display: block; margin-bottom: 6px; color: #8b949e;">最大Trace数量</label>
                <input type="number" id="importLimit" value="100" min="1" max="1000"
                    style="width: 100%; padding: 8px 12px; background: #21262d; color: #c9d1d9;
                    border: 1px solid #30363d; border-radius: 6px;">
            </div>
            <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="closeModal()">取消</button>
                <button class="btn btn-primary" onclick="doImport()">导入</button>
            </div>
        </div>
    `;

    modal.classList.remove("hidden");
}

async function doImport() {
    const service = document.getElementById("importService").value;
    const lookback = document.getElementById("importLookback").value;
    const limit = parseInt(document.getElementById("importLimit").value);

    closeModal();

    try {
        const response = await fetch(`${API_BASE}/collect/import`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ service, lookback, limit })
        });

        const result = await response.json();
        alert(`导入成功！\n服务节点: ${result.nodes}\n依赖关系: ${result.edges}`);
        loadAllData();
    } catch (error) {
        alert("导入失败: " + error.message);
    }
}

async function createSnapshot() {
    if (!confirm("确定要创建当前拓扑的快照吗？")) return;

    try {
        const response = await fetch(`${API_BASE}/topology/snapshot`, {
            method: "POST"
        });
        const result = await response.json();
        alert(`快照创建成功！\n快照ID: ${result.snapshot_id}`);
        historyPanel.loadSnapshots();
    } catch (error) {
        alert("创建快照失败: " + error.message);
    }
}

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}

async function startAnimation(sourceName) {
    showAnimationUI();
    await topologyGraph.animateFromSource(sourceName);
    hideAnimationUI();
}

function showAnimationUI() {
    document.getElementById("animateBtn").style.display = "none";
    document.getElementById("animateCriticalBtn").style.display = "none";
    document.getElementById("stopAnimateBtn").style.display = "inline-flex";
    document.getElementById("animationStatus").style.display = "flex";
}

function hideAnimationUI() {
    document.getElementById("animateBtn").style.display = "inline-flex";
    document.getElementById("animateCriticalBtn").style.display = "inline-flex";
    document.getElementById("stopAnimateBtn").style.display = "none";
    document.getElementById("animationStatus").style.display = "none";
}

function populateVersionServiceSelect(services) {
    const select = document.getElementById("versionServiceSelect");
    if (!select) return;
    
    select.innerHTML = '<option value="">-- 选择服务 --</option>';
    services.forEach(service => {
        const option = document.createElement("option");
        option.value = service;
        option.textContent = service;
        select.appendChild(option);
    });
}

async function analyzeVersionImpact() {
    const service = document.getElementById("versionServiceSelect").value;
    const oldVersion = document.getElementById("oldVersion").value;
    const newVersion = document.getElementById("newVersion").value;

    if (!service) {
        alert("请选择要分析的服务");
        return;
    }

    const resultDiv = document.getElementById("versionResult");
    resultDiv.style.display = "block";
    resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#8b949e;">⏳ 正在分析版本影响...</div>';

    try {
        const response = await fetch(
            `${API_BASE}/version/impact?service=${encodeURIComponent(service)}&old_version=${encodeURIComponent(oldVersion)}&new_version=${encodeURIComponent(newVersion)}`
        );
        const data = await response.json();

        renderVersionImpact(data, oldVersion, newVersion);
    } catch (error) {
        resultDiv.innerHTML = `<div style="color:#f85149;padding:20px;">❌ 分析失败: ${error.message}</div>`;
    }
}

function renderVersionImpact(data, oldVersion, newVersion) {
    const resultDiv = document.getElementById("versionResult");
    
    if (!data.changed_apis || data.changed_apis.length === 0) {
        resultDiv.innerHTML = `
            <div style="text-align:center;padding:30px;color:#8b949e;">
                <div style="font-size:48px;margin-bottom:12px;">✅</div>
                <div style="font-size:16px;">从 ${oldVersion} 到 ${newVersion} 未检测到API变更</div>
            </div>
        `;
        return;
    }

    const breakingCount = data.changed_apis.filter(api => api.breaking_change).length;

    let html = `
        <div class="version-summary">
            <div class="version-summary-card">
                <div class="version-summary-value">${data.changed_apis.length}</div>
                <div class="version-summary-label">变更API总数</div>
            </div>
            <div class="version-summary-card">
                <div class="version-summary-value" style="color:#f85149;">${breakingCount}</div>
                <div class="version-summary-label">破坏性变更</div>
            </div>
            <div class="version-summary-card">
                <div class="version-summary-value" style="color:#f0883e;">${data.total_impacted}</div>
                <div class="version-summary-label">下游受影响服务</div>
            </div>
        </div>

        <div style="margin-bottom:12px;color:#8b949e;font-size:13px;">
            服务 <span style="color:#58a6ff;font-weight:600;">${data.service}</span> 
            从 <span style="color:#f0883e;">${oldVersion}</span> 升级到 
            <span style="color:#238636;">${newVersion}</span> 的影响分析
        </div>

        <div class="api-change-list">
    `;

    data.changed_apis.forEach(api => {
        const methodClass = `api-method-${api.method.toLowerCase()}`;
        const changeClass = api.breaking_change ? "api-change-breaking" : "api-change-minor";
        const changeLabel = api.breaking_change ? "⚠️ 破坏性" : "✓ 兼容";

        html += `
            <div class="api-change-item">
                <div class="api-change-header">
                    <div class="api-change-title">
                        <span class="api-method-badge ${methodClass}">${api.method}</span>
                        <span class="api-path">${api.path}</span>
                    </div>
                    <span class="api-change-badge ${changeClass}">${changeLabel}</span>
                </div>
                ${api.change_description ? `
                    <div class="api-change-description">${api.change_description}</div>
                ` : ''}
                ${api.impact_count > 0 ? `
                    <div class="api-impact-section">
                        <div class="api-impact-title">
                            <span>⚠️</span> 影响下游服务 (${api.impact_count}个)
                        </div>
                        <div class="api-impact-list">
                            ${api.impacted_downstream.map(downstream => `
                                <span class="api-impact-item">
                                    ${downstream.name}
                                    <span class="api-impact-hop">H${downstream.hop_count}</span>
                                </span>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    });

    html += "</div>";
    resultDiv.innerHTML = html;
}

async function loadVersionServices() {
    try {
        const response = await fetch(`${API_BASE}/services/list`);
        const data = await response.json();
        if (data && data.services) {
            populateVersionServiceSelect(data.services);
        }
    } catch (e) {
        console.error("Failed to load services for version analysis:", e);
    }
}

window.closeModal = closeModal;
window.selectSnapshot = selectSnapshot;
window.startAnimation = startAnimation;
