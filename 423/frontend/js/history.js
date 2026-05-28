class HistoryPanel {
    constructor() {
        this.snapshots = [];
        this.currentDiff = null;
    }

    async loadSnapshots() {
        try {
            const response = await fetch(`${API_BASE}/topology/snapshots?limit=20`);
            this.snapshots = await response.json();
            this.populateSnapshotSelects();
            this.renderSnapshotsList();
        } catch (error) {
            console.error("加载快照失败:", error);
        }
    }

    populateSnapshotSelects() {
        const selectA = document.getElementById("snapshotA");
        const selectB = document.getElementById("snapshotB");

        const options = '<option value="">-- 选择快照 --</option>' +
            this.snapshots.map(s =>
                `<option value="${s.snapshot_id}">${s.snapshot_id}</option>`
            ).join("");

        selectA.innerHTML = options;
        selectB.innerHTML = options;
    }

    renderSnapshotsList() {
        const container = document.getElementById("snapshotsList");

        if (!this.snapshots || this.snapshots.length === 0) {
            container.innerHTML = '<p class="placeholder">暂无快照记录</p>';
            return;
        }

        let html = "";
        this.snapshots.forEach(snapshot => {
            html += `
                <div class="snapshot-item">
                    <div class="snapshot-info">
                        <span class="snapshot-id">${snapshot.snapshot_id}</span>
                        <span class="snapshot-time">${this.formatTime(snapshot.timestamp)}</span>
                    </div>
                    <div class="snapshot-actions">
                        <button class="btn btn-secondary" onclick="selectSnapshot('${snapshot.snapshot_id}', 'A')">选作A</button>
                        <button class="btn btn-secondary" onclick="selectSnapshot('${snapshot.snapshot_id}', 'B')">选作B</button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async compareSnapshots() {
        const snapshotA = document.getElementById("snapshotA").value;
        const snapshotB = document.getElementById("snapshotB").value;

        if (!snapshotA || !snapshotB) {
            alert("请选择两个快照进行对比");
            return;
        }

        if (snapshotA === snapshotB) {
            alert("请选择不同的快照");
            return;
        }

        try {
            const response = await fetch(
                `${API_BASE}/topology/diff?snapshot_a=${snapshotA}&snapshot_b=${snapshotB}`
            );
            const diff = await response.json();
            this.currentDiff = diff;
            this.renderDiff(diff, snapshotA, snapshotB);
        } catch (error) {
            console.error("对比快照失败:", error);
        }
    }

    renderDiff(diff, snapshotA, snapshotB) {
        const totalChanges = (diff.new_services?.length || 0) +
            (diff.removed_services?.length || 0) +
            (diff.new_edges?.length || 0) +
            (diff.removed_edges?.length || 0) +
            (diff.changed_edges?.length || 0);

        let summaryHtml = `
            <div class="diff-summary">
                <div class="diff-summary-header">
                    <span class="diff-label">快照对比:</span>
                    <span class="diff-snapshot">${snapshotA}</span>
                    <span class="diff-arrow">→</span>
                    <span class="diff-snapshot">${snapshotB}</span>
                </div>
                <div class="diff-summary-stats">
                    <div class="stat-item stat-added">
                        <span class="stat-num">+${diff.new_services?.length || 0}</span>
                        <span class="stat-text">新增服务</span>
                    </div>
                    <div class="stat-item stat-removed">
                        <span class="stat-num">-${diff.removed_services?.length || 0}</span>
                        <span class="stat-text">删除服务</span>
                    </div>
                    <div class="stat-item stat-added">
                        <span class="stat-num">+${diff.new_edges?.length || 0}</span>
                        <span class="stat-text">新增依赖</span>
                    </div>
                    <div class="stat-item stat-removed">
                        <span class="stat-num">-${diff.removed_edges?.length || 0}</span>
                        <span class="stat-text">删除依赖</span>
                    </div>
                    <div class="stat-item stat-changed">
                        <span class="stat-num">~${diff.changed_edges?.length || 0}</span>
                        <span class="stat-text">变化依赖</span>
                    </div>
                    <div class="stat-item stat-total">
                        <span class="stat-num">${totalChanges}</span>
                        <span class="stat-text">总变化</span>
                    </div>
                </div>
            </div>
        `;

        document.getElementById("historyContent").innerHTML = summaryHtml + `
            <div class="history-grid">
                <div class="history-section">
                    <h3>🟢 新增服务 (${diff.new_services?.length || 0})</h3>
                    <div id="newServices" class="diff-list"></div>
                </div>
                <div class="history-section">
                    <h3>🔴 删除服务 (${diff.removed_services?.length || 0})</h3>
                    <div id="removedServices" class="diff-list"></div>
                </div>
                <div class="history-section">
                    <h3>🟢 新增依赖 (${diff.new_edges?.length || 0})</h3>
                    <div id="newEdges" class="diff-list"></div>
                </div>
                <div class="history-section">
                    <h3>🔴 删除依赖 (${diff.removed_edges?.length || 0})</h3>
                    <div id="removedEdges" class="diff-list"></div>
                </div>
                <div class="history-section full-width">
                    <h3>🟡 变化的依赖 (${diff.changed_edges?.length || 0})</h3>
                    <div id="changedEdges" class="diff-list table"></div>
                </div>
            </div>
        `;

        this.renderServicesList("newServices", diff.new_services, "added");
        this.renderServicesList("removedServices", diff.removed_services, "removed");
        this.renderEdgesList("newEdges", diff.new_edges, "added");
        this.renderEdgesList("removedEdges", diff.removed_edges, "removed");
        this.renderChangedEdges(diff.changed_edges);
    }

    renderServicesList(containerId, services, type) {
        const container = document.getElementById(containerId);

        if (!services || services.length === 0) {
            container.innerHTML = '<p class="placeholder diff-empty">无变化</p>';
            return;
        }

        let html = "";
        services.forEach(service => {
            const icon = type === "added" ? "+" : "×";
            html += `
                <div class="diff-item diff-item-${type}">
                    <span class="diff-icon">${icon}</span>
                    <span class="diff-service-name">${service.name}</span>
                    <span class="diff-layer-tag">L${service.layer || 0}</span>
                    ${type === 'added'
                        ? '<span class="diff-highlight-add">▲ NEW</span>'
                        : '<span class="diff-highlight-remove">▼ REMOVED</span>'
                    }
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderEdgesList(containerId, edges, type) {
        const container = document.getElementById(containerId);

        if (!edges || edges.length === 0) {
            container.innerHTML = '<p class="placeholder diff-empty">无变化</p>';
            return;
        }

        let html = "";
        edges.forEach(edge => {
            const icon = type === "added" ? "+" : "×";
            html += `
                <div class="diff-item diff-item-${type}">
                    <span class="diff-icon">${icon}</span>
                    <span class="diff-edge-flow">
                        <span class="diff-edge-source">${edge.source}</span>
                        <span class="diff-edge-arrow">→</span>
                        <span class="diff-edge-target">${edge.target}</span>
                    </span>
                    ${type === 'added'
                        ? '<span class="diff-highlight-add">▲ NEW</span>'
                        : '<span class="diff-highlight-remove">▼ REMOVED</span>'
                    }
                </div>
            `;
        });

        container.innerHTML = html;
    }

    renderChangedEdges(edges) {
        const container = document.getElementById("changedEdges");

        if (!edges || edges.length === 0) {
            container.innerHTML = '<p class="placeholder diff-empty">无变化</p>';
            return;
        }

        let html = `
            <div class="diff-table-container">
                <table class="diff-table diff-table-changed">
                    <thead>
                        <tr>
                            <th>依赖关系</th>
                            <th>调用量</th>
                            <th>变化</th>
                            <th>错误量</th>
                            <th>变化</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        edges.forEach(edge => {
            const countChange = edge.new_count - edge.old_count;
            const errorChange = edge.new_errors - edge.old_errors;

            const countChangeClass = countChange > 0 ? 'change-up' : countChange < 0 ? 'change-down' : 'change-same';
            const errorChangeClass = errorChange > 0 ? 'change-up' : errorChange < 0 ? 'change-down' : 'change-same';

            const countChangeSymbol = countChange > 0 ? '▲' : countChange < 0 ? '▼' : '=';
            const errorChangeSymbol = errorChange > 0 ? '▲' : errorChange < 0 ? '▼' : '=';

            html += `
                <tr class="diff-changed-row">
                    <td>
                        <span class="diff-edge-source">${edge.source}</span>
                        <span class="diff-edge-arrow">→</span>
                        <span class="diff-edge-target">${edge.target}</span>
                    </td>
                    <td class="diff-num">
                        <span class="diff-old">${edge.old_count}</span>
                        <span class="diff-arrow-mini">→</span>
                        <span class="diff-new">${edge.new_count}</span>
                    </td>
                    <td class="diff-change ${countChangeClass}">
                        ${countChangeSymbol} ${countChange >= 0 ? '+' : ''}${countChange}
                    </td>
                    <td class="diff-num">
                        <span class="diff-old">${edge.old_errors}</span>
                        <span class="diff-arrow-mini">→</span>
                        <span class="diff-new">${edge.new_errors}</span>
                    </td>
                    <td class="diff-change ${errorChangeClass}">
                        ${errorChangeSymbol} ${errorChange >= 0 ? '+' : ''}${errorChange}
                    </td>
                </tr>
            `;
        });

        html += "</tbody></table></div>";
        container.innerHTML = html;
    }

    formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString("zh-CN");
        } catch {
            return timestamp;
        }
    }
}

function selectSnapshot(snapshotId, which) {
    const select = document.getElementById(`snapshot${which}`);
    if (select) {
        select.value = snapshotId;
    }
}
