class SimulationController {
    constructor(mapManager) {
        this.mapManager = mapManager;
        this.isRunning = false;
        this.isInitialized = false;
        this.intervalId = null;
        this.currentConfig = null;
        this.optimizedConfig = null;
        this.simTime = 0;
        this.setupEventListeners();
        this.loadDefaultConfig();
    }

    setupEventListeners() {
        document.getElementById('btn-init').addEventListener('click', () => this.initSimulation());
        document.getElementById('btn-step').addEventListener('click', () => this.stepSimulation());
        document.getElementById('btn-run').addEventListener('click', () => this.runSimulation());
        document.getElementById('btn-reset').addEventListener('click', () => this.resetSimulation());
        document.getElementById('btn-optimize').addEventListener('click', () => this.optimizeSignal());
        document.getElementById('btn-apply-opt').addEventListener('click', () => this.applyOptimizedConfig());
    }

    async loadDefaultConfig() {
        const response = await apiRequest('/config', 'GET');
        if (response.status === 'success' || response.network) {
            this.currentConfig = response;
            if (this.mapManager) {
                this.mapManager.loadNetwork(response.network);
            }
            this.updateRoadStatus(response.network.roads);
        }
    }

    getSimulationParams() {
        return {
            steps: parseInt(document.getElementById('sim-steps').value) || 100,
            genRate: parseFloat(document.getElementById('gen-rate').value) || 0.3,
            maxSpeed: parseInt(document.getElementById('max-speed').value) || 14
        };
    }

    async initSimulation() {
        this.setLoading(true);
        const params = this.getSimulationParams();
        const simConfig = {
            max_speed: params.maxSpeed,
            generation_rate: params.genRate
        };

        const data = {
            network: this.currentConfig?.network,
            signal: this.currentConfig?.signal,
            od_matrix: this.currentConfig?.od_matrix,
            sim_config: simConfig
        };

        const response = await apiRequest('/simulation/init', 'POST', data);
        this.setLoading(false);

        if (response.status === 'success') {
            this.isInitialized = true;
            this.simTime = 0;
            this.updateHeaderInfo({ time: 0, congestion_index: 0, avg_speed: 0 });
            this.showMessage('仿真初始化成功');
        } else {
            this.showMessage('初始化失败: ' + (response.message || '未知错误'), 'error');
        }
    }

    async stepSimulation(steps = 1) {
        if (!this.isInitialized) {
            this.showMessage('请先初始化仿真', 'error');
            return;
        }

        const response = await apiRequest('/simulation/step', 'POST', { steps: steps });

        if (response.status === 'success') {
            this.simTime = response.time;
            this.updateVisualization(response.results);
        } else {
            this.showMessage('单步运行失败: ' + (response.message || '未知错误'), 'error');
        }
    }

    async runSimulation() {
        if (this.isRunning) {
            this.stopSimulation();
            return;
        }

        if (!this.isInitialized) {
            await this.initSimulation();
            if (!this.isInitialized) return;
        }

        this.isRunning = true;
        document.getElementById('btn-run').textContent = '停止仿真';
        document.getElementById('btn-run').classList.remove('btn-success');
        document.getElementById('btn-run').classList.add('btn-warning');

        const params = this.getSimulationParams();
        let stepCount = 0;

        this.intervalId = setInterval(async () => {
            if (!this.isRunning || stepCount >= params.steps) {
                this.stopSimulation();
                return;
            }

            await this.stepSimulation(5);
            stepCount += 5;
        }, CONFIG.simulation.updateInterval);
    }

    stopSimulation() {
        this.isRunning = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        document.getElementById('btn-run').textContent = '开始仿真';
        document.getElementById('btn-run').classList.remove('btn-warning');
        document.getElementById('btn-run').classList.add('btn-success');
    }

    async resetSimulation() {
        this.stopSimulation();
        this.setLoading(true);

        const response = await apiRequest('/simulation/reset', 'POST');
        this.setLoading(false);

        if (response.status === 'success') {
            this.isInitialized = false;
            this.simTime = 0;
            this.mapManager.clearVehicleMarkers();
            this.mapManager.clearHeatmap();
            if (this.currentConfig) {
                this.mapManager.loadNetwork(this.currentConfig.network);
                this.updateRoadStatus(this.currentConfig.network.roads);
            }
            this.updateHeaderInfo({ time: 0, congestion_index: 0, avg_speed: 0 });
            document.getElementById('total-vehicles').textContent = '0';
            document.getElementById('completed-vehicles').textContent = '0';
            document.getElementById('avg-queue').textContent = '0';
            this.showMessage('仿真已重置');
        }
    }

    async optimizeSignal() {
        this.setLoading(true);
        const algorithm = document.getElementById('opt-algorithm').value;
        const iterations = parseInt(document.getElementById('opt-iterations').value) || 10;

        let endpoint = '/optimize/hill_climb';
        let data = {
            network: this.currentConfig?.network,
            signal: this.currentConfig?.signal,
            od_matrix: this.currentConfig?.od_matrix,
            iterations: iterations,
            method: 'ca'
        };

        if (algorithm === 'genetic') {
            endpoint = '/optimize/genetic';
            data.generations = iterations;
            data.population_size = 20;
            data.mutation_rate = 0.2;
        } else if (algorithm === 'grid_search') {
            endpoint = '/optimize/grid_search';
            data.min_duration = 10;
            data.max_duration = 60;
            data.step = 10;
        }

        try {
            const response = await apiRequest(endpoint, 'POST', data);
            this.setLoading(false);

            if (response.status === 'success' && response.result) {
                this.optimizedConfig = response.result.best_config;
                this.displayOptimizationResult(response.result);
                document.getElementById('btn-apply-opt').disabled = false;
                this.showMessage('信号配时优化完成');
            } else {
                this.showMessage('优化失败: ' + (response.message || '未知错误'), 'error');
            }
        } catch (error) {
            this.setLoading(false);
            this.showMessage('优化出错: ' + error.message, 'error');
        }
    }

    displayOptimizationResult(result) {
        const optResultDiv = document.getElementById('opt-result');
        optResultDiv.classList.add('active');

        let html = '';
        if (result.best_metrics) {
            html += `
                <div class="result-item">
                    <div class="label">最佳评分</div>
                    <div class="value">${result.best_score.toFixed(4)}</div>
                </div>
                <div class="result-item">
                    <div class="label">平均排队长度</div>
                    <div class="value">${result.best_metrics.avg_queue.toFixed(2)}</div>
                </div>
                <div class="result-item">
                    <div class="label">最大排队长度</div>
                    <div class="value">${result.best_metrics.max_queue.toFixed(2)}</div>
                </div>
                <div class="result-item">
                    <div class="label">吞吐量</div>
                    <div class="value">${result.best_metrics.throughput}</div>
                </div>
            `;
        } else if (result.final_durations) {
            html += `
                <div class="result-item">
                    <div class="label">最佳评分</div>
                    <div class="value">${result.best_score.toFixed(4)}</div>
                </div>
                <div class="result-item">
                    <div class="label">优化后相位时长</div>
                    <div class="value">${result.final_durations.join(', ')} 秒</div>
                </div>
            `;
        }

        if (result.best_config && result.best_config.signals) {
            html += '<div class="result-item"><div class="label">推荐信号配时</div><div class="value">';
            result.best_config.signals.forEach(signal => {
                html += `<div>信号 ${signal.id}:</div>`;
                signal.phases.forEach((phase, i) => {
                    html += `<div>  相位${i + 1} (${phase.name || ''}): ${phase.duration}秒</div>`;
                });
            });
            html += '</div></div>';
        }

        optResultDiv.innerHTML = html;
    }

    async applyOptimizedConfig() {
        if (!this.optimizedConfig) {
            this.showMessage('没有可用的优化结果', 'error');
            return;
        }

        this.currentConfig.signal = this.optimizedConfig;
        this.showMessage('已应用优化后的信号配时方案');

        if (this.isInitialized) {
            await this.resetSimulation();
        }
    }

    async updateVisualization(results) {
        const queueResponse = await apiRequest('/simulation/queue_lengths', 'GET');
        const heatmapResponse = await apiRequest('/simulation/heatmap', 'GET');

        this.updateHeaderInfo({
            time: this.simTime,
            congestion_index: results.congestion_index,
            avg_speed: results.avg_speed
        });

        this.updateMetrics(results);

        if (queueResponse.status === 'success') {
            this.updateRoadStatusDetails(queueResponse.road_details);
            this.mapManager.updateRoadColors(queueResponse.road_details);
        }

        if (heatmapResponse.status === 'success') {
            this.mapManager.updateHeatmap(heatmapResponse.vehicle_heatmap);
        }

        if (results.vehicle_positions) {
            this.mapManager.updateVehiclePositions(results.vehicle_positions);
        }
    }

    updateHeaderInfo(info) {
        document.getElementById('sim-time').textContent = `时间: ${info.time}`;
        document.getElementById('congestion-index').textContent = `拥堵指数: ${info.congestion_index.toFixed(2)}`;
        document.getElementById('avg-speed').textContent = `平均车速: ${info.avg_speed.toFixed(1)} m/s`;
    }

    updateMetrics(results) {
        document.getElementById('total-vehicles').textContent = results.vehicle_positions?.length || 0;
        document.getElementById('completed-vehicles').textContent = results.total_completed || 0;

        const queues = results.queue_lengths || {};
        const avgQueue = Object.values(queues).reduce((a, b) => a + b, 0) / Math.max(1, Object.keys(queues).length);
        document.getElementById('avg-queue').textContent = avgQueue.toFixed(1);
    }

    updateRoadStatus(roads) {
        const container = document.getElementById('road-status');
        container.innerHTML = '';

        roads.forEach(road => {
            const item = document.createElement('div');
            item.className = 'road-status-item';
            item.id = `road-status-${road.id}`;
            item.innerHTML = `
                <span class="road-name">${road.name || road.id}</span>
                <span class="road-queue">0</span>
                <span class="road-level" style="background: ${CONFIG.colors.freeflow};">畅通</span>
            `;
            container.appendChild(item);
        });
    }

    updateRoadStatusDetails(roadDetails) {
        Object.entries(roadDetails).forEach(([roadId, details]) => {
            const item = document.getElementById(`road-status-${roadId}`);
            if (item) {
                item.className = `road-status-item ${getDensityLevel(details.density).class}`;
                item.querySelector('.road-queue').textContent = details.queue_length;
                const levelSpan = item.querySelector('.road-level');
                levelSpan.textContent = details.congestion_level;
                levelSpan.style.background = details.color;
            }
        });
    }

    setLoading(loading) {
        if (loading) {
            document.body.classList.add('loading');
        } else {
            document.body.classList.remove('loading');
        }
    }

    showMessage(message, type = 'success') {
        const existingMessage = document.querySelector('.floating-message');
        if (existingMessage) {
            existingMessage.remove();
        }

        const msg = document.createElement('div');
        msg.className = `floating-message ${type}`;
        msg.style.cssText = `
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            background: ${type === 'error' ? '#e74c3c' : '#2ecc71'};
            color: white;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-weight: 500;
            animation: slideDown 0.3s ease-out;
        `;
        msg.textContent = message;
        document.body.appendChild(msg);

        setTimeout(() => {
            msg.style.animation = 'slideUp 0.3s ease-in';
            setTimeout(() => msg.remove(), 300);
        }, 2500);
    }
}
