class BusPredictionApp {
    constructor() {
        this.ws = null;
        this.routes = [];
        this.selectedRoute = null;
        this.gpsData = [];
        this.predictions = [];
        this.delayWarnings = [];
        this.punctualityStats = null;
        this.dispatchSuggestions = [];
        this.passengerData = [];
        
        this.voiceEnabled = true;
        this.voiceVolume = 0.8;
        this.speechSynthesis = window.speechSynthesis;
        this.lastAnnouncement = null;
        
        this.init();
    }
    
    init() {
        this.setupTabs();
        this.setupVoiceControls();
        this.connectWebSocket();
    }
    
    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panel');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                
                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanels.forEach(p => p.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.hostname}:8765`;
        
        this.updateConnectionStatus('connecting');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket连接成功');
            this.updateConnectionStatus('connected');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.updateConnectionStatus('error');
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket连接关闭');
            this.updateConnectionStatus('error');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    updateConnectionStatus(status) {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        statusDot.className = 'status-dot';
        
        switch(status) {
            case 'connecting':
                statusDot.classList.add('connecting');
                statusText.textContent = '连接中...';
                break;
            case 'connected':
                statusDot.classList.add('connected');
                statusText.textContent = '已连接';
                break;
            case 'error':
                statusDot.classList.add('error');
                statusText.textContent = '连接失败';
                break;
        }
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'initial':
                this.handleInitialData(data);
                break;
            case 'update':
                this.handleUpdateData(data);
                break;
        }
        
        document.getElementById('lastUpdate').textContent = 
            new Date(data.timestamp).toLocaleString('zh-CN');
    }
    
    handleInitialData(data) {
        this.routes = data.routes;
        this.renderRouteList();
        
        if (this.routes.length > 0) {
            this.selectRoute(this.routes[0].route_id);
        }
    }
    
    handleUpdateData(data) {
        this.gpsData = data.gps_data || [];
        this.predictions = data.predictions || [];
        this.delayWarnings = data.delay_warnings || [];
        this.punctualityStats = data.punctuality_stats;
        this.segmentStats = data.segment_stats || [];
        this.highRiskSegments = data.high_risk_segments || [];
        this.dispatchSuggestions = data.dispatch_suggestions || [];
        this.passengerData = data.passenger_data || [];
        
        this.renderDelayWarnings();
        this.renderDispatchSuggestions();
        this.renderRealTimeData();
        this.renderPunctualityStats();
        this.renderHighRiskSegments();
        this.renderSegmentPunctuality();
        
        if (data.announcements && data.announcements.length > 0) {
            this.handleAnnouncements(data.announcements);
        }
        
        if (this.selectedRoute) {
            this.renderRouteStations();
            this.renderTrafficInfo();
        }
    }
    
    setupVoiceControls() {
        const voiceToggle = document.getElementById('voiceEnabled');
        const voiceVolume = document.getElementById('voiceVolume');
        
        if (voiceToggle) {
            voiceToggle.addEventListener('change', (e) => {
                this.voiceEnabled = e.target.checked;
                if (!this.voiceEnabled && this.speechSynthesis) {
                    this.speechSynthesis.cancel();
                }
            });
        }
        
        if (voiceVolume) {
            voiceVolume.addEventListener('input', (e) => {
                this.voiceVolume = parseFloat(e.target.value);
            });
        }
    }
    
    handleAnnouncements(announcements) {
        announcements.forEach(announcement => {
            this.showAnnouncement(announcement);
            this.speakAnnouncement(announcement);
        });
    }
    
    showAnnouncement(announcement) {
        const announcementEl = document.getElementById('latestAnnouncement');
        if (announcementEl) {
            announcementEl.textContent = announcement.message;
            announcementEl.classList.add('active');
            setTimeout(() => {
                announcementEl.classList.remove('active');
            }, 5000);
        }
    }
    
    speakAnnouncement(announcement) {
        if (!this.voiceEnabled || !this.speechSynthesis) {
            return;
        }
        
        const utterance = new SpeechSynthesisUtterance(announcement.message);
        utterance.lang = 'zh-CN';
        utterance.volume = this.voiceVolume;
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        
        this.speechSynthesis.speak(utterance);
    }
    
    renderDispatchSuggestions() {
        const container = document.getElementById('dispatchSuggestions');
        if (!container) return;
        
        if (!this.dispatchSuggestions || this.dispatchSuggestions.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无调度建议</div>';
            return;
        }
        
        container.innerHTML = this.dispatchSuggestions.map(suggestion => `
            <div class="suggestion-card priority-${suggestion.priority}">
                <div class="suggestion-type">${this.getSuggestionTypeText(suggestion.suggestion_type)}</div>
                <div class="suggestion-reason">${suggestion.reason}</div>
                <div class="suggestion-extra">
                    线路: ${suggestion.route_id}路 | 
                    当前间隔: ${Math.round(suggestion.current_interval / 60)}分钟
                    ${suggestion.extra_buses_needed > 0 ? ` | 需加车: ${suggestion.extra_buses_needed}辆` : ''}
                </div>
            </div>
        `).join('');
    }
    
    getSuggestionTypeText(type) {
        const typeMap = {
            'add_bus': '🚍 建议加开班次',
            'increase_frequency': '📊 建议增加发车频率',
            'express_service': '⚡ 建议加开快车'
        };
        return typeMap[type] || type;
    }
    
    renderRouteList() {
        const routeList = document.getElementById('routeList');
        routeList.innerHTML = '';
        
        this.routes.forEach(route => {
            const item = document.createElement('div');
            item.className = 'route-item';
            if (route.route_id === this.selectedRoute) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div class="route-name">${route.name}</div>
                <div class="station-count">${route.stations.length} 个站点</div>
            `;
            
            item.addEventListener('click', () => this.selectRoute(route.route_id));
            routeList.appendChild(item);
        });
    }
    
    selectRoute(routeId) {
        this.selectedRoute = routeId;
        this.renderRouteList();
        this.renderRouteStations();
        this.renderTrafficInfo();
    }
    
    renderRouteStations() {
        const route = this.routes.find(r => r.route_id === this.selectedRoute);
        if (!route) return;
        
        const container = document.getElementById('routeStations');
        container.innerHTML = '';
        
        route.stations.forEach((station, index) => {
            const stationBuses = this.predictions.filter(p => 
                p.route_id === this.selectedRoute && 
                p.station_id === station.id
            );
            
            const line = document.createElement('div');
            line.className = 'station-line';
            
            const hasBus = stationBuses.length > 0;
            const dotClass = hasBus ? 'has-bus' : '';
            
            let busesHtml = '';
            let arrivalHtml = '<div class="arrival-time">-</div>';
            
            if (stationBuses.length > 0) {
                const bus = stationBuses[0];
                const etaDate = new Date(bus.predicted_arrival);
                const now = new Date();
                const minutes = Math.max(0, Math.round((etaDate - now) / 1000 / 60));
                
                let delayClass = 'on-time';
                let delayText = '准点';
                if (bus.delay_seconds > 180) {
                    delayClass = 'delayed';
                    delayText = `晚点 ${Math.round(bus.delay_seconds / 60)} 分`;
                } else if (bus.delay_seconds < -60) {
                    delayText = `早点 ${Math.round(Math.abs(bus.delay_seconds) / 60)} 分`;
                }
                
                arrivalHtml = `
                    <div class="arrival-time">
                        <div class="eta">${minutes} 分钟</div>
                        <div class="delay ${delayClass}">${delayText}</div>
                    </div>
                `;
                
                busesHtml = stationBuses.map(b => `
                    <span class="bus-tag ${b.is_delayed ? 'delayed' : ''}">
                        ${b.bus_id}
                    </span>
                `).join('');
            }
            
            line.innerHTML = `
                <div class="station-dot ${dotClass}">${index + 1}</div>
                <div class="station-info">
                    <div class="station-name">${station.name}</div>
                    <div class="station-buses">${busesHtml}</div>
                </div>
                ${arrivalHtml}
            `;
            
            container.appendChild(line);
        });
        
        this.renderBusList();
    }
    
    renderBusList() {
        const container = document.getElementById('busList');
        const routeBuses = this.predictions.filter(p => p.route_id === this.selectedRoute);
        
        if (routeBuses.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无车辆数据</div>';
            return;
        }
        
        const uniqueBuses = {};
        routeBuses.forEach(p => {
            if (!uniqueBuses[p.bus_id] || new Date(p.predicted_arrival) < new Date(uniqueBuses[p.bus_id].predicted_arrival)) {
                uniqueBuses[p.bus_id] = p;
            }
        });
        
        container.innerHTML = '';
        
        Object.values(uniqueBuses).forEach(prediction => {
            const gps = this.gpsData.find(g => g.bus_id === prediction.bus_id);
            const passenger = this.passengerData.find(p => p.bus_id === prediction.bus_id);
            const etaDate = new Date(prediction.predicted_arrival);
            const now = new Date();
            const progress = Math.min(100, Math.max(0, 100 - ((etaDate - now) / 1000 / 60 / 15 * 100)));
            
            const card = document.createElement('div');
            card.className = `bus-card ${prediction.is_delayed ? 'delayed' : ''}`;
            
            let passengerHtml = '';
            if (passenger) {
                const loadLevel = passenger.load_factor < 0.5 ? 'low' : passenger.load_factor < 0.8 ? 'medium' : 'high';
                const loadText = passenger.load_factor < 0.5 ? '空闲' : passenger.load_factor < 0.8 ? '适中' : '拥挤';
                passengerHtml = `
                    <div class="bus-passenger-info">
                        <span class="passenger-indicator ${loadLevel}">${loadText}</span>
                        载客: ${passenger.current_load}/${passenger.max_capacity}人
                    </div>
                `;
            }
            
            card.innerHTML = `
                <div class="bus-id">🚌 ${prediction.bus_id}</div>
                <div class="next-station">下一站: ${prediction.station_name}</div>
                <div class="eta-bar">
                    <div class="eta-progress" style="width: ${progress}%"></div>
                </div>
                <div style="margin-top: 10px; display: flex; justify-content: space-between; font-size: 12px;">
                    <span>速度: ${gps ? gps.speed.toFixed(1) : '-'} km/h</span>
                    <span>置信度: ${(prediction.confidence * 100).toFixed(0)}%</span>
                </div>
                ${passengerHtml}
            `;
            
            container.appendChild(card);
        });
    }
    
    renderDelayWarnings() {
        const container = document.getElementById('delayWarnings');
        
        if (this.delayWarnings.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无预警</div>';
            return;
        }
        
        container.innerHTML = '';
        
        this.delayWarnings.slice(0, 10).forEach(warning => {
            const item = document.createElement('div');
            item.className = `warning-item ${warning.severity}`;
            
            item.innerHTML = `
                <div class="bus-info">${warning.route_name} - ${warning.bus_id}</div>
                <div class="delay-info">预计晚点 ${Math.round(warning.delay_seconds / 60)} 分钟</div>
                <div class="station-info">下一站: ${warning.station}</div>
            `;
            
            container.appendChild(item);
        });
    }
    
    renderPunctualityStats() {
        if (!this.punctualityStats) return;
        
        document.getElementById('totalTrips').textContent = this.punctualityStats.total;
        document.getElementById('onTimeRate').textContent = 
            (this.punctualityStats.on_time_rate * 100).toFixed(1) + '%';
        document.getElementById('delayedCount').textContent = this.punctualityStats.delayed;
        document.getElementById('avgDelay').textContent = 
            Math.abs(Math.round(this.punctualityStats.avg_delay)) + 's';
        
        this.renderPunctualityBars();
    }
    
    renderHighRiskSegments() {
        const container = document.getElementById('highRiskSegments');
        
        if (!this.highRiskSegments || this.highRiskSegments.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无延误高发区间数据</div>';
            return;
        }
        
        container.innerHTML = '';
        
        this.highRiskSegments.forEach(segment => {
            const item = document.createElement('div');
            item.className = 'risk-item';
            
            const onTimeRate = (segment.on_time_rate * 100).toFixed(1);
            const avgDelayMin = Math.abs(Math.round(segment.avg_delay / 60));
            
            item.innerHTML = `
                <div class="segment-name">🚍 ${segment.from_station} → ${segment.to_station}</div>
                <div class="risk-details">
                    <span>📊 准点率: <strong>${onTimeRate}%</strong></span>
                    <span>⏱️ 平均延误: <span class="delay-value">${avgDelayMin} 分钟</span></span>
                    <span>🚦 总班次: ${segment.total_trips}</span>
                </div>
            `;
            
            container.appendChild(item);
        });
    }
    
    renderSegmentPunctuality() {
        const container = document.getElementById('segmentPunctualityBars');
        
        if (!this.selectedRoute) {
            container.innerHTML = '<div class="empty-state">请选择线路查看路段分析</div>';
            return;
        }
        
        const routeSegments = this.segmentStats.filter(s => s.route_id === this.selectedRoute);
        
        if (routeSegments.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无该路段数据</div>';
            return;
        }
        
        container.innerHTML = '';
        
        routeSegments.forEach(segment => {
            const onTimeRate = segment.on_time_rate * 100;
            
            let barColor = 'linear-gradient(90deg, #27ae60, #2ecc71)';
            if (onTimeRate < 70) {
                barColor = 'linear-gradient(90deg, #e74c3c, #c0392b)';
            } else if (onTimeRate < 85) {
                barColor = 'linear-gradient(90deg, #f39c12, #e67e22)';
            }
            
            const item = document.createElement('div');
            item.className = 'chart-bar-item';
            
            item.innerHTML = `
                <div class="chart-bar-label" style="width: 180px; font-size: 12px;">
                    ${segment.from_station.slice(0, 4)} → ${segment.to_station.slice(0, 4)}
                </div>
                <div class="chart-bar-container">
                    <div class="chart-bar-fill" style="width: ${onTimeRate}%; background: ${barColor};">
                        ${onTimeRate.toFixed(1)}%
                    </div>
                </div>
            `;
            
            container.appendChild(item);
        });
    }
    
    renderPunctualityBars() {
        const container = document.getElementById('punctualityBars');
        container.innerHTML = '';
        
        this.routes.forEach(route => {
            const stats = this.calculateRouteStats(route.route_id);
            const onTimeRate = stats ? (stats.on_time_rate * 100) : 85;
            
            const item = document.createElement('div');
            item.className = 'chart-bar-item';
            
            item.innerHTML = `
                <div class="chart-bar-label">${route.name}</div>
                <div class="chart-bar-container">
                    <div class="chart-bar-fill" style="width: ${onTimeRate}%">
                        ${onTimeRate.toFixed(1)}%
                    </div>
                </div>
            `;
            
            container.appendChild(item);
        });
    }
    
    calculateRouteStats(routeId) {
        if (!this.punctualityStats) return null;
        return this.punctualityStats;
    }
    
    renderRealTimeData() {
    }
    
    renderTrafficInfo() {
        const route = this.routes.find(r => r.route_id === this.selectedRoute);
        if (!route) return;
        
        const container = document.getElementById('trafficMap');
        container.innerHTML = '';
        
        for (let i = 0; i < route.stations.length - 1; i++) {
            const trafficLevel = Math.floor(Math.random() * 4);
            const levelNames = ['畅通', '轻度拥堵', '中度拥堵', '严重拥堵'];
            
            const routeInfo = Config.BUS_ROUTES ? Config.BUS_ROUTES[route.route_id] : null;
            const stopLightDensities = routeInfo ? routeInfo.stop_light_density || [] : [];
            const stopLightDensity = i < stopLightDensities.length ? stopLightDensities[i] : 1.0;
            
            const segmentStats = this.segmentStats ? 
                this.segmentStats.find(s => s.route_id === route.route_id && 
                    s.from_station === route.stations[i].name) : null;
            
            const segment = document.createElement('div');
            segment.className = 'traffic-segment';
            
            let statsInfo = '';
            if (segmentStats && segmentStats.total_trips > 0) {
                const onTimeRate = (segmentStats.on_time_rate * 100).toFixed(0);
                statsInfo = `<span class="stop-light-info">📊 准点率: ${onTimeRate}%</span>`;
            }
            
            segment.innerHTML = `
                <div class="segment-name">
                    ${route.stations[i].name} → ${route.stations[i + 1].name}
                </div>
                <div class="segment-info">
                    <span class="stop-light-info">🚦 信号灯密度: ${stopLightDensity}/km</span>
                    ${statsInfo}
                    <div class="traffic-level level-${trafficLevel}">
                        ${levelNames[trafficLevel]}
                    </div>
                </div>
            `;
            
            container.appendChild(segment);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new BusPredictionApp();
});
