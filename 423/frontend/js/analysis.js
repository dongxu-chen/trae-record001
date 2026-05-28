class AnalysisPanel {
    constructor() {
        this.timeWindow = 60;
    }

    async loadAnalysis() {
        try {
            const response = await fetch(`${API_BASE}/topology/analysis?time_window=${this.timeWindow}`);
            const data = await response.json();
            this.renderAnalysis(data);
        } catch (error) {
            console.error("加载分析数据失败:", error);
        }
    }

    renderAnalysis(data) {
        this.renderLayerDistribution(data.layer_info);
        this.renderDependencyMetrics(data.metrics);
        this.loadCriticalPaths();
        this.loadAnomalies();
    }

    renderLayerDistribution(layerInfo) {
        const container = document.getElementById("layerDistribution");
        const layerCounts = layerInfo.layer_counts || {};
        const maxCount = Math.max(...Object.values(layerCounts), 1);

        let html = '<div class="layer-distribution">';
        Object.entries(layerCounts)
            .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
            .forEach(([layer, count]) => {
                const width = (count / maxCount) * 100;
                const colors = ["#81c784", "#4fc3f7", "#ffb74d", "#ba68c8", "#f06292", "#4db6ac"];
                const color = colors[parseInt(layer) % colors.length];

                html += `
                    <div class="layer-bar">
                        <span class="layer-label">L${layer}</span>
                        <div class="bar-container">
                            <div class="bar-fill" style="width:${width}%;background:${color};"></div>
                        </div>
                        <span class="count">${count} 服务</span>
                    </div>
                `;
            });
        html += "</div>";

        if (Object.keys(layerCounts).length === 0) {
            html = '<p class="placeholder">暂无层级数据</p>';
        }

        container.innerHTML = html;
    }

    async loadCriticalPaths() {
        try {
            const response = await fetch(`${API_BASE}/topology/critical-paths?time_window=${this.timeWindow}`);
            const paths = await response.json();
            this.renderCriticalPaths(paths);
        } catch (error) {
            console.error("加载关键路径失败:", error);
        }
    }

    renderCriticalPaths(paths) {
        const container = document.getElementById("criticalPaths");

        if (!paths || paths.length === 0) {
            container.innerHTML = '<p class="placeholder">暂无关键路径</p>';
            return;
        }

        let html = "";
        paths.slice(0, 10).forEach(path => {
            const pathStr = path.path.join(" → ");
            const errorRate = (path.error_rate * 100).toFixed(2);

            html += `
                <div class="critical-path">
                    <span class="path-node">${pathStr.split(" → ").map((node, i) => {
                        if (i === 0) return `<span class="path-node">${node}</span>`;
                        return `<span class="path-arrow">→</span><span class="path-node">${node}</span>`;
                    }).join("")}</span>
                    <div class="path-stats">
                        <span>调用: ${path.total_calls}</span>
                        <span>错误: ${path.total_errors}</span>
                        <span>错误率: ${errorRate}%</span>
                        <span>延迟: ${path.max_latency.toFixed(0)}μs</span>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async loadDependencyMetrics() {
        try {
            const response = await fetch(`${API_BASE}/topology/metrics?time_window=${this.timeWindow}`);
            const metrics = await response.json();
            this.renderDependencyMetrics(metrics);
        } catch (error) {
            console.error("加载依赖指标失败:", error);
        }
    }

    renderDependencyMetrics(metrics) {
        const container = document.getElementById("dependencyMetrics");

        if (!metrics || Object.keys(metrics).length === 0) {
            container.innerHTML = '<p class="placeholder">暂无指标数据</p>';
            return;
        }

        let html = `
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>服务名</th>
                        <th>入度</th>
                        <th>出度</th>
                        <th>类型</th>
                    </tr>
                </thead>
                <tbody>
        `;

        Object.entries(metrics)
            .sort((a, b) => (b[1].fan_in + b[1].fan_out) - (a[1].fan_in + a[1].fan_out))
            .forEach(([name, metric]) => {
                let typeBadges = "";
                if (metric.is_hub) typeBadges += '<span class="badge badge-hub">枢纽</span> ';
                if (metric.is_entry_point) typeBadges += '<span class="badge badge-entry">入口</span> ';
                if (metric.is_leaf) typeBadges += '<span class="badge badge-leaf">叶子</span> ';

                html += `
                    <tr>
                        <td>${name}</td>
                        <td>${metric.fan_in}</td>
                        <td>${metric.fan_out}</td>
                        <td>${typeBadges || "-"}</td>
                    </tr>
                `;
            });

        html += "</tbody></table>";
        container.innerHTML = html;
    }

    async loadAnomalies() {
        try {
            const response = await fetch(`${API_BASE}/topology/anomalies?time_window=${this.timeWindow}`);
            const anomalies = await response.json();
            this.renderAnomalies(anomalies);
        } catch (error) {
            console.error("加载异常检测失败:", error);
        }
    }

    renderAnomalies(anomalies) {
        const container = document.getElementById("anomaliesList");

        if (!anomalies || anomalies.length === 0) {
            container.innerHTML = '<p class="placeholder">✅ 未检测到异常</p>';
            return;
        }

        let html = "";
        anomalies.forEach(anomaly => {
            const severityClass = anomaly.severity || "medium";
            html += `
                <div class="anomaly-item ${severityClass}">
                    <div class="severity">${anomaly.severity?.toUpperCase() || "MEDIUM"}</div>
                    <div class="message">${anomaly.message}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    setTimeWindow(minutes) {
        this.timeWindow = minutes;
    }
}
