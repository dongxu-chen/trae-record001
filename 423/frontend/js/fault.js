class FaultPanel {
    constructor() {
        this.timeWindow = 60;
        this.serviceOptions = [];
    }

    async loadServices() {
        try {
            const response = await fetch(`${API_BASE}/topology?time_window=${this.timeWindow}`);
            const data = await response.json();
            this.serviceOptions = data.services || [];
            this.populateServiceSelect();
        } catch (error) {
            console.error("加载服务列表失败:", error);
        }
    }

    populateServiceSelect() {
        const select = document.getElementById("faultServiceSelect");
        select.innerHTML = '<option value="">-- 选择服务 --</option>';

        this.serviceOptions.sort().forEach(service => {
            const option = document.createElement("option");
            option.value = service;
            option.textContent = service;
            select.appendChild(option);
        });
    }

    async analyzeFault() {
        const serviceName = document.getElementById("faultServiceSelect").value;
        const depth = document.getElementById("faultDepth").value;

        if (!serviceName) {
            alert("请选择一个服务");
            return;
        }

        try {
            const [impactResponse, pathsResponse] = await Promise.all([
                fetch(`${API_BASE}/fault/impact/${encodeURIComponent(serviceName)}?depth=${depth}`),
                fetch(`${API_BASE}/fault/cascading-paths/${encodeURIComponent(serviceName)}?time_window=${this.timeWindow}&max_depth=${depth}`)
            ]);

            const impactData = await impactResponse.json();
            const pathsData = await pathsResponse.json();

            this.renderFaultImpact(serviceName, impactData, pathsData);
        } catch (error) {
            console.error("分析故障失败:", error);
            document.getElementById("faultContent").innerHTML =
                '<p class="placeholder">分析失败，请重试</p>';
        }
    }

    renderFaultImpact(serviceName, impactData, pathsData) {
        const container = document.getElementById("faultContent");

        let html = `
            <div class="fault-summary">
                <div class="fault-summary-item">
                    <span class="summary-label">故障源:</span>
                    <span class="summary-value fault-name">${serviceName}</span>
                </div>
                <div class="fault-summary-item">
                    <span class="summary-label">下游影响:</span>
                    <span class="summary-value">${impactData.total_downstream || 0} 个服务</span>
                </div>
                <div class="fault-summary-item">
                    <span class="summary-label">上游依赖:</span>
                    <span class="summary-value">${impactData.total_upstream || 0} 个服务</span>
                </div>
            </div>
            <div class="fault-tree">
        `;

        if (impactData.downstream_impact && impactData.downstream_impact.length > 0) {
            html += `
                <div class="fault-section">
                    <h3>⬇️ 下游影响服务 (BFS 遍历, 深度=${document.getElementById('faultDepth').value})</h3>
                    <div class="impact-table-wrapper">
                        <table class="impact-table">
                            <thead>
                                <tr>
                                    <th>服务名</th>
                                    <th>类型</th>
                                    <th>层级</th>
                                    <th>跳数</th>
                                    <th>路径调用</th>
                                    <th>路径错误</th>
                                    <th>错误率</th>
                                    <th>影响分数</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            const byHop = {};
            impactData.downstream_impact.forEach(item => {
                if (!byHop[item.hop_count]) byHop[item.hop_count] = [];
                byHop[item.hop_count].push(item);
            });

            Object.keys(byHop).sort((a, b) => a - b).forEach(hop => {
                byHop[hop]
                    .sort((a, b) => b.impact_score - a.impact_score)
                    .forEach(item => {
                        const errorRate = (item.error_rate * 100).toFixed(2);
                        const errorClass = item.error_rate > 0.05 ? "high-error" :
                            item.error_rate > 0.01 ? "mid-error" : "";

                        html += `
                            <tr class="${errorClass}" data-service="${item.name}">
                                <td class="service-cell">
                                    <span class="hop-indicator" style="background:${this.getHopColor(parseInt(hop))}">H${hop}</span>
                                    <span class="service-name-link">${item.name}</span>
                                </td>
                                <td>${item.service_type || '-'}</td>
                                <td>L${item.layer || 0}</td>
                                <td><span class="hop-badge">${hop}</span></td>
                                <td>${item.total_calls}</td>
                                <td>${item.total_errors}</td>
                                <td class="${item.error_rate > 0.05 ? 'error-rate-high' : item.error_rate > 0.01 ? 'error-rate-mid' : ''}">
                                    ${errorRate}%
                                </td>
                                <td><span class="impact-score">${item.impact_score}</span></td>
                            </tr>
                        `;
                    });
            });

            html += "</tbody></table></div></div>";
        }

        if (impactData.upstream_dependencies && impactData.upstream_dependencies.length > 0) {
            html += `
                <div class="fault-section">
                    <h3>⬆️ 上游依赖服务</h3>
                    <div class="upstream-list">
            `;

            const byHop = {};
            impactData.upstream_dependencies.forEach(item => {
                if (!byHop[item.hop_count]) byHop[item.hop_count] = [];
                byHop[item.hop_count].push(item);
            });

            Object.keys(byHop).sort((a, b) => a - b).forEach(hop => {
                byHop[hop].forEach(item => {
                    html += `
                        <div class="upstream-item" style="margin-left: ${(hop - 1) * 16}px;">
                            <span class="up-hop" style="background:${this.getHopColor(parseInt(hop))}">H${hop}</span>
                            <span class="up-name">${item.name}</span>
                            <span class="up-type">${item.service_type || '-'}</span>
                        </div>
                    `;
                });
            });

            html += "</div></div>";
        }

        if (pathsData && pathsData.length > 0) {
            html += `
                <div class="fault-section" style="flex-basis: 100%;">
                    <h3>🔗 级联故障路径 (Top 5, BFS限深)</h3>
            `;

            pathsData.slice(0, 5).forEach((path, index) => {
                const errorRate = (path.error_rate * 100).toFixed(2);
                const riskClass = path.error_rate > 0.05 ? "path-high-risk" :
                    path.error_rate > 0.01 ? "path-mid-risk" : "path-low-risk";

                html += `
                    <div class="cascading-path ${riskClass}">
                        <div class="path-header">
                            <span class="path-index">路径 ${index + 1}</span>
                            <span class="path-error">错误率: ${errorRate}%</span>
                        </div>
                        <div class="path-flow">
                            ${path.path.map((node, i) => {
                                if (i === 0) return `<span class="path-node path-fault">${node}</span>`;
                                const arrowColor = path.error_rate > 0.05 ? '#f85149' :
                                    path.error_rate > 0.01 ? '#d29922' : '#3fb950';
                                return `<span class="path-arrow" style="color:${arrowColor}">→</span><span class="path-node">${node}</span>`;
                            }).join("")}
                        </div>
                    </div>
                `;
            });

            html += "</div>";
        }

        html += "</div>";

        if ((!impactData.downstream_impact || impactData.downstream_impact.length === 0) &&
            (!impactData.upstream_dependencies || impactData.upstream_dependencies.length === 0)) {
            html = `
                <div class="fault-summary">
                    <div class="fault-summary-item">
                        <span class="summary-label">故障源:</span>
                        <span class="summary-value fault-name">${serviceName}</span>
                    </div>
                    <div class="fault-summary-item">
                        <span class="summary-label">下游影响:</span>
                        <span class="summary-value">0 个服务</span>
                    </div>
                    <div class="fault-summary-item">
                        <span class="summary-label">上游依赖:</span>
                        <span class="summary-value">0 个服务</span>
                    </div>
                </div>
                <div class="fault-tree">
                    <div class="fault-section">
                        <p class="placeholder">该服务无上下游依赖</p>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;

        document.querySelectorAll(".service-cell").forEach(cell => {
            cell.addEventListener("click", () => {
                const serviceName = cell.dataset.service;
                if (topologyGraph) {
                    topologyGraph.highlightNode(serviceName);
                }
            });
        });
    }

    getHopColor(hop) {
        const colors = ["#f85149", "#d29922", "#58a6ff", "#3fb950", "#ba68c8", "#4db6ac"];
        return colors[(hop - 1) % colors.length];
    }

    async loadBroadcastRisk() {
        try {
            const response = await fetch(`${API_BASE}/fault/broadcast-risk?time_window=${this.timeWindow}`);
            const data = await response.json();
            this.renderBroadcastRisk(data);
        } catch (error) {
            console.error("加载传播风险失败:", error);
        }
    }

    renderBroadcastRisk(data) {
        const container = document.getElementById("broadcastRisk");

        if (!data || !data.risk_scores) {
            container.innerHTML = '<p class="placeholder">暂无风险数据</p>';
            return;
        }

        const risks = Object.entries(data.risk_scores)
            .sort((a, b) => b[1].broadcast_risk - a[1].broadcast_risk);

        let html = "";
        if (data.high_risk_services && data.high_risk_services.length > 0) {
            html = `
                <div class="risk-alert">
                    <strong style="color: #f85149;">⚠️ 高风险服务 (${data.high_risk_services.length}):</strong>
                    <div class="high-risk-list">
                        ${data.high_risk_services.map(s => `<span class="risk-tag">${s}</span>`).join("")}
                    </div>
                </div>
            `;
        }

        html += '<div class="risk-grid">';
        risks.forEach(([service, risk]) => {
            html += `
                <div class="risk-card risk-${risk.risk_level}">
                    <div class="risk-header">
                        <span class="risk-service">${service}</span>
                        <span class="risk-level-badge level-${risk.risk_level}">${this.getRiskLabel(risk.risk_level)}</span>
                    </div>
                    <div class="risk-metrics">
                        <div class="risk-metric">
                            <span class="metric-label">出度</span>
                            <span class="metric-value">${risk.fan_out}</span>
                        </div>
                        <div class="risk-metric">
                            <span class="metric-label">调用</span>
                            <span class="metric-value">${risk.total_calls}</span>
                        </div>
                        <div class="risk-metric">
                            <span class="metric-label">错误率</span>
                            <span class="metric-value">${(risk.error_rate * 100).toFixed(2)}%</span>
                        </div>
                        <div class="risk-metric">
                            <span class="metric-label">传播分</span>
                            <span class="metric-value">${risk.broadcast_risk.toFixed(1)}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += "</div>";

        container.innerHTML = html;
    }

    getRiskLabel(level) {
        const labels = {
            high: "高风险",
            medium: "中风险",
            low: "低风险"
        };
        return labels[level] || level;
    }

    setTimeWindow(minutes) {
        this.timeWindow = minutes;
    }
}
