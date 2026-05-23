class ODVisualization {
    constructor() {
        this.currentView = '2d';
        this.selectedEvent = null;
        this.events = [];
        
        this.charts = {};
        this.maps = {};
        this.mapLayers = {};
        
        this.gridSize = 10;
        this.numGrids = 100;
        this.currentHour = 8;
        this.granularity = '1h';
        this.isPlaying = false;
        this.playInterval = null;
        
        this.initCharts();
        this.initEventListeners();
        this.initModal();
        this.loadEvents();
        this.loadData();
        this.loadTrendData();
    }

    initCharts() {
        const chartIds = [
            'heatmapChart', 'trendChart', 'originBarChart', 'destBarChart',
            'supplyDemandChart', 'supplyDemandCompareChart',
            'eventHeatmapChart', 'eventStatsChart', 'chart3d'
        ];
        
        chartIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                this.charts[id] = echarts.init(el);
            }
        });

        window.addEventListener('resize', () => {
            Object.values(this.charts).forEach(chart => {
                if (chart && chart.resize) chart.resize();
            });
        });
    }

    initEventListeners() {
        document.getElementById('dateSelect').addEventListener('change', () => {
            this.loadData();
            this.loadTrendData();
        });
        
        document.getElementById('modeSelect').addEventListener('change', () => this.loadData());
        
        document.getElementById('granularitySelect').addEventListener('change', (e) => {
            this.granularity = e.target.value;
            const labels = { '5min': '5分钟', '15min': '15分钟', '1h': '1小时' };
            document.getElementById('trendGranularityHint').textContent = `粒度: ${labels[this.granularity]}`;
            this.loadTrendData();
        });
        
        document.getElementById('viewSelect').addEventListener('change', (e) => {
            this.switchView(e.target.value);
        });
        
        const hourSlider = document.getElementById('hourSlider');
        hourSlider.addEventListener('input', (e) => {
            this.currentHour = parseInt(e.target.value);
            document.getElementById('hourDisplay').textContent = 
                String(this.currentHour).padStart(2, '0') + ':00';
            this.loadData();
        });

        document.getElementById('playBtn').addEventListener('click', () => this.togglePlay());
        
        document.getElementById('simulateBtn').addEventListener('click', () => this.runEventSimulation());
        
        const resetCameraBtn = document.getElementById('resetCamera');
        if (resetCameraBtn) {
            resetCameraBtn.addEventListener('click', () => this.reset3DCamera());
        }
        
        const autoRotateBtn = document.getElementById('autoRotate');
        if (autoRotateBtn) {
            autoRotateBtn.addEventListener('click', () => this.toggleAutoRotate());
        }
    }

    initModal() {
        const modal = document.getElementById('similarGridModal');
        const closeBtn = document.getElementById('closeModal');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.remove('show');
            });
        }
        
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });
    }

    switchView(viewName) {
        this.currentView = viewName;
        
        document.querySelectorAll('.view-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        
        const targetPanel = document.getElementById(`view-${viewName}`);
        if (targetPanel) {
            targetPanel.classList.add('active');
        }
        
        setTimeout(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart && chart.resize) chart.resize();
            });
        }, 100);
        
        if (viewName === '3d') {
            this.load3DData();
        } else if (viewName === 'supply_demand') {
            this.loadSupplyDemandData();
        } else if (viewName === '2d') {
            this.initMap();
        } else if (viewName === 'event') {
            this.initEventMap();
        }
    }

    async loadData() {
        const date = document.getElementById('dateSelect').value;
        const mode = document.getElementById('modeSelect').value;
        const hour = this.currentHour;

        const matrixEndpoint = mode === 'prediction' ? '/api/pred_od_matrix' : '/api/od_matrix';
        const flowEndpoint = '/api/flow_data';

        try {
            const [matrixRes, flowRes] = await Promise.all([
                fetch(`${matrixEndpoint}?date=${date}&hour=${hour}`),
                fetch(`${flowEndpoint}?date=${date}&hour=${hour}&top_k=50&pred=${mode === 'prediction'}`)
            ]);

            const matrixData = await matrixRes.json();
            const flowData = await flowRes.json();

            this.updateHeatmap(matrixData);
            this.updateStats(matrixData);
            this.updateBarCharts(matrixData);
            this.updateMap(flowData);
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    async loadTrendData() {
        const date = document.getElementById('dateSelect').value;
        
        try {
            const res = await fetch(`/api/trend?date=${date}&start_hour=0&hours=24&granularity=${this.granularity}`);
            const data = await res.json();
            this.updateTrendChart(data);
        } catch (error) {
            console.error('Error loading trend data:', error);
        }
    }

    async loadSupplyDemandData() {
        const date = document.getElementById('dateSelect').value;
        const mode = document.getElementById('modeSelect').value;
        const hour = this.currentHour;

        try {
            const res = await fetch(`/api/supply_demand?date=${date}&hour=${hour}&pred=${mode === 'prediction'}`);
            const data = await res.json();
            this.updateSupplyDemandCharts(data);
            this.updateGapMap(data);
        } catch (error) {
            console.error('Error loading supply-demand data:', error);
        }
    }

    async load3DData() {
        const date = document.getElementById('dateSelect').value;
        const mode = document.getElementById('modeSelect').value;
        const hour = this.currentHour;

        try {
            const res = await fetch(`/api/3d_flow_data?date=${date}&hour=${hour}&top_k=30&pred=${mode === 'prediction'}`);
            const data = await res.json();
            this.update3DChart(data);
        } catch (error) {
            console.error('Error loading 3D data:', error);
        }
    }

    async loadEvents() {
        try {
            const res = await fetch('/api/available_events');
            const data = await res.json();
            this.events = data.events;
            this.renderEventButtons();
        } catch (error) {
            console.error('Error loading events:', error);
        }
    }

    renderEventButtons() {
        const container = document.getElementById('eventButtons');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.events.forEach((event, index) => {
            const btn = document.createElement('button');
            btn.className = 'event-btn';
            btn.innerHTML = `<span class="event-btn-icon">${event.icon}</span>${event.name}`;
            btn.addEventListener('click', () => this.selectEvent(event, btn));
            container.appendChild(btn);
            
            if (index === 0) {
                this.selectEvent(event, btn);
            }
        });
    }

    selectEvent(event, btnElement) {
        this.selectedEvent = event;
        
        document.querySelectorAll('.event-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        btnElement.classList.add('active');
        
        this.renderEventParams(event);
    }

    renderEventParams(event) {
        const container = document.getElementById('eventParams');
        if (!container) return;
        
        container.innerHTML = '';
        
        event.params.forEach(param => {
            const group = document.createElement('div');
            group.className = 'param-group';
            
            const label = document.createElement('label');
            label.textContent = param.label;
            label.htmlFor = `param-${param.name}`;
            group.appendChild(label);
            
            let input;
            if (param.type === 'select') {
                input = document.createElement('select');
                param.options.forEach((opt, idx) => {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = param.labels ? param.labels[idx] : opt;
                    if (opt === param.default) option.selected = true;
                    input.appendChild(option);
                });
            } else {
                input = document.createElement('input');
                input.type = param.type === 'grid' ? 'number' : param.type;
                input.value = param.default;
                if (param.type === 'grid') {
                    input.min = 0;
                    input.max = this.numGrids - 1;
                }
            }
            
            input.id = `param-${param.name}`;
            input.dataset.paramName = param.name;
            group.appendChild(input);
            
            container.appendChild(group);
        });
    }

    async runEventSimulation() {
        if (!this.selectedEvent) return;
        
        const date = document.getElementById('dateSelect').value;
        const mode = document.getElementById('modeSelect').value;
        const hour = this.currentHour;
        
        const params = {};
        document.querySelectorAll('#eventParams input, #eventParams select').forEach(input => {
            params[input.dataset.paramName] = input.value;
        });
        
        try {
            const res = await fetch('/api/simulate_event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_type: this.selectedEvent.type,
                    params: params,
                    date: date,
                    hour: hour,
                    use_pred: mode === 'prediction'
                })
            });
            
            const data = await res.json();
            this.updateEventSimulationResults(data);
        } catch (error) {
            console.error('Error running event simulation:', error);
        }
    }

    updateEventSimulationResults(data) {
        this.updateEventHeatmap(data);
        this.updateEventStatsChart(data);
        this.updateEventMap(data);
        
        document.getElementById('baseDemand').textContent = Math.round(data.base_total_demand).toLocaleString();
        document.getElementById('affectedDemand').textContent = Math.round(data.affected_total_demand).toLocaleString();
        
        const changeRate = ((data.affected_total_demand - data.base_total_demand) / data.base_total_demand * 100);
        const changeRateEl = document.getElementById('changeRate');
        changeRateEl.textContent = `${changeRate > 0 ? '+' : ''}${changeRate.toFixed(1)}%`;
        changeRateEl.className = `event-stat-value ${changeRate > 0 ? 'positive' : 'negative'}`;
        
        document.getElementById('eventImpactLabel').textContent = 
            `${this.selectedEvent.icon} ${this.selectedEvent.name} 影响已显示`;
    }

    updateHeatmap(data) {
        if (!this.charts.heatmapChart) return;
        
        const gridLabels = Array.from({length: this.numGrids}, (_, i) => `G${i}`);

        const option = {
            tooltip: {
                position: 'top',
                formatter: (params) => {
                    return `出发: G${params.data[0]}<br/>到达: G${params.data[1]}<br/>需求量: ${params.data[2].toFixed(1)}`;
                }
            },
            grid: { left: 60, right: 20, top: 40, bottom: 60 },
            xAxis: {
                type: 'category',
                data: gridLabels,
                splitArea: { show: true },
                axisLabel: { rotate: 45, fontSize: 10, interval: 4 },
                name: '目的地网格',
                nameLocation: 'middle',
                nameGap: 45
            },
            yAxis: {
                type: 'category',
                data: gridLabels,
                splitArea: { show: true },
                axisLabel: { fontSize: 10, interval: 4 },
                name: '出发地网格',
                nameLocation: 'middle',
                nameGap: 50
            },
            visualMap: {
                min: 0,
                max: Math.max(...data.heatmap_data.map(d => d[2])) || 10,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: 0,
                inRange: {
                    color: ['#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695']
                }
            },
            series: [{
                name: 'OD需求',
                type: 'heatmap',
                data: data.heatmap_data,
                label: { show: false },
                emphasis: {
                    itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
                }
            }]
        };

        this.charts.heatmapChart.setOption(option);
        
        this.charts.heatmapChart.off('click');
        this.charts.heatmapChart.on('click', (params) => {
            if (params.componentType === 'series') {
                const gridIdx = params.data[0];
                this.showSimilarGrids(gridIdx);
            }
        });
    }

    async showSimilarGrids(gridIdx) {
        const modal = document.getElementById('similarGridModal');
        const content = document.getElementById('similarGridContent');
        
        content.innerHTML = '<div class="loading">加载中...</div>';
        modal.classList.add('show');
        
        try {
            const res = await fetch(`/api/similar_grids?grid_idx=${gridIdx}`);
            const data = await res.json();
            
            if (data.similar_grids && data.similar_grids.length > 0) {
                let html = `<p>网格 <strong>G${gridIdx}</strong> 的Top-5相似网格（知识迁移来源）:</p>`;
                html += '<div class="similar-grid-list">';
                
                data.similar_grids.forEach((item) => {
                    const simPercent = (item.similarity * 100).toFixed(1);
                    html += `
                        <div class="similar-grid-item">
                            <div class="similar-grid-info">
                                <div class="similar-grid-name">G${item.grid_idx}</div>
                                <div class="similar-grid-sim">相似度: ${simPercent}%</div>
                            </div>
                            <div class="similar-grid-bar">
                                <div class="similar-grid-fill" style="width: ${simPercent}%"></div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                content.innerHTML = html;
            } else {
                content.innerHTML = '<p>暂无可迁移知识的相似网格</p>';
            }
        } catch (error) {
            content.innerHTML = '<p>加载失败，请重试</p>';
            console.error('Error loading similar grids:', error);
        }
    }

    updateTrendChart(data) {
        if (!this.charts.trendChart) return;
        
        const option = {
            tooltip: {
                trigger: 'axis',
                formatter: (params) => `${params[0].name}<br/>总需求量: ${params[0].value.toFixed(0)}`
            },
            grid: { left: 50, right: 20, top: 30, bottom: 30 },
            xAxis: {
                type: 'category',
                data: data.trend.map(t => t.time),
                axisLabel: { 
                    fontSize: 9,
                    rotate: data.trend.length > 48 ? 45 : 0,
                    interval: Math.floor(data.trend.length / 12)
                }
            },
            yAxis: {
                type: 'value',
                name: '总需求量',
                axisLabel: { fontSize: 10 }
            },
            dataZoom: data.trend.length > 24 ? [{ type: 'inside', start: 0, end: 100 }] : [],
            series: [{
                name: '总需求量',
                type: 'line',
                smooth: true,
                data: data.trend.map(t => t.total_demand),
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(102, 126, 234, 0.6)' },
                        { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
                    ])
                },
                lineStyle: { color: '#667eea', width: 3 },
                itemStyle: { color: '#667eea' },
                markPoint: { data: [{ type: 'max', name: '峰值' }, { type: 'min', name: '谷值' }] }
            }]
        };

        this.charts.trendChart.setOption(option);
    }

    updateStats(data) {
        document.getElementById('totalDemand').textContent = 
            Math.round(data.total_demand).toLocaleString();
        
        const peakOrigin = data.row_sums.indexOf(Math.max(...data.row_sums));
        const peakDest = data.col_sums.indexOf(Math.max(...data.col_sums));
        
        document.getElementById('peakOrigin').textContent = `G${peakOrigin}`;
        document.getElementById('peakDest').textContent = `G${peakDest}`;
        
        const avgFlow = data.heatmap_data.length > 0 
            ? (data.total_demand / data.heatmap_data.length).toFixed(1)
            : 0;
        document.getElementById('avgFlow').textContent = avgFlow;
    }

    updateBarCharts(data) {
        const gridLabels = Array.from({length: this.numGrids}, (_, i) => `G${i}`);

        if (this.charts.originBarChart) {
            const originOption = {
                tooltip: {
                    trigger: 'axis',
                    formatter: (params) => `网格 ${params[0].name}<br/>出发需求: ${params[0].value.toFixed(0)}`
                },
                grid: { left: 50, right: 20, top: 20, bottom: 30 },
                xAxis: {
                    type: 'category',
                    data: gridLabels,
                    axisLabel: { fontSize: 9, interval: 4, rotate: 45 }
                },
                yAxis: { type: 'value', name: '出发需求', axisLabel: { fontSize: 10 } },
                series: [{
                    type: 'bar',
                    data: data.row_sums,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#667eea' },
                            { offset: 1, color: '#764ba2' }
                        ])
                    }
                }]
            };
            this.charts.originBarChart.setOption(originOption);
        }

        if (this.charts.destBarChart) {
            const destOption = {
                tooltip: {
                    trigger: 'axis',
                    formatter: (params) => `网格 ${params[0].name}<br/>到达需求: ${params[0].value.toFixed(0)}`
                },
                grid: { left: 50, right: 20, top: 20, bottom: 30 },
                xAxis: {
                    type: 'category',
                    data: gridLabels,
                    axisLabel: { fontSize: 9, interval: 4, rotate: 45 }
                },
                yAxis: { type: 'value', name: '到达需求', axisLabel: { fontSize: 10 } },
                series: [{
                    type: 'bar',
                    data: data.col_sums,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#ee6666' },
                            { offset: 1, color: '#fc8181' }
                        ])
                    }
                }]
            };
            this.charts.destBarChart.setOption(destOption);
        }
    }

    initMap() {
        if (this.maps.main) return;
        
        this.maps.main = L.map('mapChart').setView([31.2304, 121.4737], 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.maps.main);
        
        this.mapLayers.main = { polylines: [], markers: [] };
    }

    updateMap(data) {
        if (!this.maps.main) return;
        
        this.mapLayers.main.polylines.forEach(line => this.maps.main.removeLayer(line));
        this.mapLayers.main.markers.forEach(marker => this.maps.main.removeLayer(marker));
        this.mapLayers.main = { polylines: [], markers: [] };

        if (!data.flows || data.flows.length === 0) return;

        const demands = data.flows.map(f => f.demand);
        const minDemand = Math.min(...demands);
        const maxDemand = Math.max(...demands);
        
        const logMin = Math.log1p(minDemand);
        const logMax = Math.log1p(maxDemand);
        const logRange = logMax - logMin || 1;

        data.flows.forEach(flow => {
            const logDemand = Math.log1p(flow.demand);
            const normalizedDemand = (logDemand - logMin) / logRange;
            
            let color;
            if (normalizedDemand < 0.33) {
                color = '#5470c6';
            } else if (normalizedDemand < 0.66) {
                color = '#91cc75';
            } else {
                color = '#ee6666';
            }

            const minWidth = 2;
            const maxWidth = 10;
            const weight = minWidth + normalizedDemand * (maxWidth - minWidth);
            const opacity = 0.4 + normalizedDemand * 0.5;

            const pointA = [flow.from[1], flow.from[0]];
            const pointB = [flow.to[1], flow.to[0]];
            
            const midLat = (pointA[0] + pointB[0]) / 2;
            const midLng = (pointA[1] + pointB[1]) / 2 + 0.01 * normalizedDemand;
            const midPoint = [midLat, midLng];

            const polyline = L.polyline([pointA, midPoint, pointB], {
                color: color,
                weight: weight,
                opacity: opacity,
                smoothFactor: 1
            }).addTo(this.maps.main);

            polyline.bindPopup(`
                <b>OD流量</b><br/>
                出发网格: G${flow.origin_grid}<br/>
                到达网格: G${flow.dest_grid}<br/>
                需求量: ${flow.demand.toFixed(1)}
            `);

            this.mapLayers.main.polylines.push(polyline);

            const originMarker = L.circleMarker(pointA, {
                radius: 4 + normalizedDemand * 4,
                fillColor: '#667eea',
                color: '#fff',
                weight: 2,
                fillOpacity: 0.8
            }).addTo(this.maps.main);

            const destMarker = L.circleMarker(pointB, {
                radius: 4 + normalizedDemand * 4,
                fillColor: '#ee6666',
                color: '#fff',
                weight: 2,
                fillOpacity: 0.8
            }).addTo(this.maps.main);

            this.mapLayers.main.markers.push(originMarker, destMarker);
        });
    }

    updateSupplyDemandCharts(data) {
        if (!this.charts.supplyDemandChart) return;
        
        const gridLabels = Array.from({length: this.numGrids}, (_, i) => `G${i}`);
        const balance = data.balance_analysis;
        
        const heatmapData = balance.gap.map((gap, idx) => [idx, 0, gap]);
        
        const option = {
            tooltip: {
                formatter: (params) => {
                    const idx = params.data[0];
                    const gap = params.data[2];
                    return `网格 G${idx}<br/>供需缺口: ${gap > 0 ? '+' : ''}${gap.toFixed(1)}<br/>${gap > 20 ? '严重缺口' : gap > 10 ? '高缺口' : gap > 0 ? '中等缺口' : gap < -20 ? '运力过剩' : '供需平衡'}`;
                }
            },
            grid: { left: 60, right: 40, top: 40, bottom: 60 },
            xAxis: {
                type: 'category',
                data: gridLabels,
                axisLabel: { rotate: 45, fontSize: 10, interval: 2 }
            },
            yAxis: { type: 'category', data: ['供需缺口'], axisLabel: { fontSize: 10 } },
            visualMap: {
                min: -30,
                max: 30,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: 0,
                inRange: {
                    color: ['#1a9850', '#91cf60', '#d9ef8b', '#fee08b', '#fc8d59', '#d73027']
                }
            },
            series: [{
                name: '供需缺口',
                type: 'heatmap',
                data: heatmapData,
                label: { show: false }
            }]
        };
        
        this.charts.supplyDemandChart.setOption(option);
        
        if (this.charts.supplyDemandCompareChart) {
            const compareOption = {
                tooltip: { trigger: 'axis' },
                legend: { data: ['需求', '供给'], top: 0 },
                grid: { left: 50, right: 20, top: 30, bottom: 30 },
                xAxis: {
                    type: 'category',
                    data: gridLabels,
                    axisLabel: { fontSize: 9, interval: 4, rotate: 45 }
                },
                yAxis: { type: 'value', name: '数量', axisLabel: { fontSize: 10 } },
                series: [
                    {
                        name: '需求',
                        type: 'bar',
                        data: balance.demand,
                        itemStyle: { color: '#ee6666' }
                    },
                    {
                        name: '供给',
                        type: 'bar',
                        data: balance.supply,
                        itemStyle: { color: '#667eea' }
                    }
                ]
            };
            this.charts.supplyDemandCompareChart.setOption(compareOption);
        }
        
        document.getElementById('criticalCount').textContent = balance.critical_grids.length;
        document.getElementById('surplusCount').textContent = balance.surplus_grids.length;
        document.getElementById('totalGap').textContent = Math.round(balance.total_gap).toLocaleString();
        
        this.renderSuggestions(data.relocation_suggestions);
    }

    renderSuggestions(suggestions) {
        const container = document.getElementById('suggestionsList');
        if (!container) return;
        
        if (!suggestions || suggestions.length === 0) {
            container.innerHTML = '<div class="suggestion-item"><span class="loading-text">暂无调度建议</span></div>';
            return;
        }
        
        container.innerHTML = suggestions.map(s => `
            <div class="suggestion-item">
                <div class="suggestion-header">
                    G${s.from_grid} → G${s.to_grid}
                </div>
                <div class="suggestion-details">
                    <span>预计缺口: ${Math.round(s.estimated_gap)}</span>
                    <span>可调度: ${Math.round(s.available_supply)}</span>
                    <span>距离: ${s.distance.toFixed(1)} 格</span>
                </div>
            </div>
        `).join('');
    }

    initEventMap() {
        if (this.maps.event) return;
        
        this.maps.event = L.map('eventMapChart').setView([31.2304, 121.4737], 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.maps.event);
        
        this.mapLayers.event = { polylines: [], markers: [] };
    }

    updateGapMap(data) {
        if (!this.maps.gap) {
            this.maps.gap = L.map('gapMapChart').setView([31.2304, 121.4737], 12);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.maps.gap);
            
            this.mapLayers.gap = { circles: [], lines: [] };
        }
        
        this.mapLayers.gap.circles.forEach(c => this.maps.gap.removeLayer(c));
        this.mapLayers.gap.lines.forEach(l => this.maps.gap.removeLayer(l));
        this.mapLayers.gap = { circles: [], lines: [] };
        
        const centers = data.grid_centers;
        const balance = data.balance_analysis;
        
        centers.forEach(grid => {
            const gap = balance.gap[grid.grid_idx];
            
            let color, radius;
            if (gap > 20) {
                color = '#d73027';
                radius = 15;
            } else if (gap > 10) {
                color = '#fc8d59';
                radius = 12;
            } else if (gap > 0) {
                color = '#fee08b';
                radius = 8;
            } else if (gap < -20) {
                color = '#1a9850';
                radius = 15;
            } else if (gap < -10) {
                color = '#91cf60';
                radius = 12;
            } else {
                color = '#d9ef8b';
                radius = 6;
            }
            
            const circle = L.circleMarker([grid.lat, grid.lon], {
                radius: radius,
                fillColor: color,
                color: '#fff',
                weight: 2,
                fillOpacity: 0.7
            }).addTo(this.maps.gap);
            
            circle.bindPopup(`
                <b>网格 G${grid.grid_idx}</b><br/>
                供需缺口: ${gap > 0 ? '+' : ''}${gap.toFixed(1)}<br/>
                需求: ${balance.demand[grid.grid_idx].toFixed(0)}<br/>
                供给: ${balance.supply[grid.grid_idx].toFixed(0)}
            `);
            
            this.mapLayers.gap.circles.push(circle);
        });
        
        data.relocation_suggestions.forEach(s => {
            const fromGrid = centers.find(g => g.grid_idx === s.from_grid);
            const toGrid = centers.find(g => g.grid_idx === s.to_grid);
            
            if (fromGrid && toGrid) {
                const line = L.polyline(
                    [[fromGrid.lat, fromGrid.lon], [toGrid.lat, toGrid.lon]],
                    {
                        color: '#4299e1',
                        weight: 3,
                        opacity: 0.8,
                        dashArray: '10, 10'
                    }
                ).addTo(this.maps.gap);
                
                this.mapLayers.gap.lines.push(line);
            }
        });
    }

    updateEventMap(data) {
        if (!this.maps.event || !data.affected_flows) return;
        
        this.mapLayers.event.polylines.forEach(line => this.maps.event.removeLayer(line));
        this.mapLayers.event.markers.forEach(marker => this.maps.event.removeLayer(marker));
        this.mapLayers.event = { polylines: [], markers: [] };

        data.affected_flows.forEach(flow => {
            const diff = flow.diff;
            const normalizedDiff = Math.min(1, Math.abs(diff) / 20);
            
            const color = diff > 0 ? '#d73027' : '#1a9850';
            const weight = 2 + normalizedDiff * 6;
            const opacity = 0.4 + normalizedDiff * 0.4;

            const pointA = [flow.from[1], flow.from[0]];
            const pointB = [flow.to[1], flow.to[0]];
            
            const midLat = (pointA[0] + pointB[0]) / 2;
            const midLng = (pointA[1] + pointB[1]) / 2 + 0.01 * normalizedDiff;
            const midPoint = [midLat, midLng];

            const polyline = L.polyline([pointA, midPoint, pointB], {
                color: color,
                weight: weight,
                opacity: opacity,
                smoothFactor: 1,
                dashArray: diff > 0 ? '' : '5, 5'
            }).addTo(this.maps.event);

            polyline.bindPopup(`
                <b>OD变化</b><br/>
                出发: G${flow.origin_grid}<br/>
                到达: G${flow.dest_grid}<br/>
                基准需求: ${flow.base_demand.toFixed(1)}<br/>
                变化: ${diff > 0 ? '+' : ''}${diff.toFixed(1)}
            `);

            this.mapLayers.event.polylines.push(polyline);
        });
    }

    updateEventHeatmap(data) {
        if (!this.charts.eventHeatmapChart || !data.diff_stats) return;
        
        const gridLabels = Array.from({length: this.numGrids}, (_, i) => `G${i}`);
        const diff = data.diff_stats.diff_matrix;
        
        const heatmapData = [];
        for (let i = 0; i < this.numGrids; i++) {
            for (let j = 0; j < this.numGrids; j++) {
                if (Math.abs(diff[i][j]) > 0.1) {
                    heatmapData.push([i, j, diff[i][j]]);
                }
            }
        }
        
        const option = {
            tooltip: {
                position: 'top',
                formatter: (params) => {
                    const d = params.data[2];
                    return `出发: G${params.data[0]}<br/>到达: G${params.data[1]}<br/>变化: ${d > 0 ? '+' : ''}${d.toFixed(1)}`;
                }
            },
            grid: { left: 60, right: 20, top: 40, bottom: 60 },
            xAxis: {
                type: 'category',
                data: gridLabels,
                splitArea: { show: true },
                axisLabel: { rotate: 45, fontSize: 10, interval: 4 },
                name: '目的地网格',
                nameLocation: 'middle',
                nameGap: 45
            },
            yAxis: {
                type: 'category',
                data: gridLabels,
                splitArea: { show: true },
                axisLabel: { fontSize: 10, interval: 4 },
                name: '出发地网格',
                nameLocation: 'middle',
                nameGap: 50
            },
            visualMap: {
                min: data.diff_stats.max_decrease,
                max: data.diff_stats.max_increase,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: 0,
                inRange: {
                    color: ['#313695', '#4575b4', '#74add1', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027']
                }
            },
            series: [{
                name: 'OD变化',
                type: 'heatmap',
                data: heatmapData,
                label: { show: false }
            }]
        };
        
        this.charts.eventHeatmapChart.setOption(option);
    }

    updateEventStatsChart(data) {
        if (!this.charts.eventStatsChart || !data.diff_stats) return;
        
        const option = {
            tooltip: { trigger: 'item' },
            grid: { left: 50, right: 20, top: 30, bottom: 30 },
            xAxis: {
                type: 'category',
                data: ['总增加量', '总减少量', '净变化'],
                axisLabel: { fontSize: 12 }
            },
            yAxis: { type: 'value', name: '需求量', axisLabel: { fontSize: 10 } },
            series: [{
                type: 'bar',
                data: [
                    { value: data.diff_stats.total_increase, itemStyle: { color: '#d73027' } },
                    { value: -data.diff_stats.total_decrease, itemStyle: { color: '#1a9850' } },
                    { value: data.diff_stats.net_change, itemStyle: { color: data.diff_stats.net_change > 0 ? '#fc8d59' : '#91cf60' } }
                ],
                label: {
                    show: true,
                    position: 'top',
                    formatter: (params) => {
                        const val = params.value;
                        return val > 0 ? `+${Math.round(val)}` : Math.round(val);
                    }
                }
            }]
        };
        
        this.charts.eventStatsChart.setOption(option);
    }

    update3DChart(data) {
        if (!this.charts.chart3d) return;
        
        const lines3d = data.flows_3d.map(flow => {
            return [
                [flow.from.x, flow.from.y, flow.from.z],
                [flow.to.x, flow.to.y, flow.to.z]
            ];
        });
        
        const gridPoints = data.grid_points.map(g => [g.x, g.y, g.z, g.grid_idx, g.total_outflow, g.total_inflow]);
        
        const option = {
            tooltip: {
                formatter: (params) => {
                    if (params.seriesType === 'lines3D') {
                        const d = data.flows_3d[params.dataIndex];
                        return `G${d.from.grid_idx} → G${d.to.grid_idx}<br/>需求: ${d.demand.toFixed(1)}`;
                    } else {
                        const g = params.data;
                        return `网格 G${g[3]}<br/>流出: ${g[4].toFixed(1)}<br/>流入: ${g[5].toFixed(1)}`;
                    }
                }
            },
            visualMap: {
                show: true,
                min: 0,
                max: 1,
                dimension: 2,
                inRange: {
                    color: ['#5470c6', '#91cc75', '#ee6666']
                },
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: 10
            },
            xAxis3D: {
                type: 'value',
                name: '经度',
                min: 121.35,
                max: 121.60
            },
            yAxis3D: {
                type: 'value',
                name: '纬度',
                min: 31.15,
                max: 31.30
            },
            zAxis3D: {
                type: 'value',
                name: '高度',
                min: 0,
                max: 60
            },
            grid3D: {
                viewControl: {
                    autoRotate: false,
                    autoRotateSpeed: 10,
                    distance: 150,
                    maxDistance: 300,
                    minDistance: 50
                },
                light: {
                    main: {
                        intensity: 1.2,
                        shadow: true
                    },
                    ambient: {
                        intensity: 0.3
                    }
                }
            },
            series: [
                {
                    type: 'scatter3D',
                    data: gridPoints,
                    symbolSize: 8,
                    itemStyle: {
                        color: '#667eea',
                        opacity: 0.8
                    },
                    emphasis: {
                        itemStyle: {
                            color: '#ff6b6b'
                        }
                    }
                },
                {
                    type: 'lines3D',
                    data: lines3d,
                    effect: {
                        show: true,
                        period: 4,
                        trailWidth: 2,
                        trailLength: 0.5,
                        symbol: 'arrow',
                        symbolSize: 8
                    },
                    lineStyle: {
                        width: 3,
                        opacity: 0.7,
                        curveness: 0.3
                    },
                    blendMode: 'lighter'
                }
            ]
        };
        
        this.charts.chart3d.setOption(option);
    }

    reset3DCamera() {
        if (!this.charts.chart3d) return;
        
        const option = this.charts.chart3d.getOption();
        if (option.grid3D && option.grid3D[0]) {
            option.grid3D[0].viewControl.distance = 150;
            option.grid3D[0].viewControl.alpha = 30;
            option.grid3D[0].viewControl.beta = 40;
            option.grid3D[0].viewControl.autoRotate = false;
            this.charts.chart3d.setOption(option);
        }
    }

    toggleAutoRotate() {
        if (!this.charts.chart3d) return;
        
        const option = this.charts.chart3d.getOption();
        if (option.grid3D && option.grid3D[0]) {
            const current = option.grid3D[0].viewControl.autoRotate;
            option.grid3D[0].viewControl.autoRotate = !current;
            this.charts.chart3d.setOption(option);
            
            const btn = document.getElementById('autoRotate');
            if (btn) {
                btn.textContent = !current ? '停止旋转' : '自动旋转';
            }
        }
    }

    togglePlay() {
        const btn = document.getElementById('playBtn');
        
        if (this.isPlaying) {
            this.stopPlay();
            btn.textContent = '▶ 播放趋势';
            btn.classList.remove('playing');
        } else {
            this.startPlay();
            btn.textContent = '⏸ 暂停';
            btn.classList.add('playing');
        }
    }

    startPlay() {
        this.isPlaying = true;
        const interval = this.granularity === '5min' ? 200 : 
                         this.granularity === '15min' ? 300 : 1000;
        
        this.playInterval = setInterval(() => {
            this.currentHour = (this.currentHour + 1) % 24;
            document.getElementById('hourSlider').value = this.currentHour;
            document.getElementById('hourDisplay').textContent = 
                String(this.currentHour).padStart(2, '0') + ':00';
            this.loadData();
            
            if (this.currentView === '3d') {
                this.load3DData();
            } else if (this.currentView === 'supply_demand') {
                this.loadSupplyDemandData();
            }
        }, interval);
    }

    stopPlay() {
        this.isPlaying = false;
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.odViz = new ODVisualization();
});
