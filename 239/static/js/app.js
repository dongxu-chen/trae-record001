class VRPOptimizer {
    constructor() {
        this.map = null;
        this.markers = [];
        this.routes = [];
        this.routePolylines = [];
        this.forbiddenAreas = [];
        this.forbiddenCircles = [];
        this.locations = [];
        this.timeWindows = {};
        this.currentResult = null;
        this.editingPointIndex = null;
        this.draggedPoint = null;
        this.lockedRoutes = new Set();
        this.trafficData = {};
        this.trafficEnabled = true;

        this.init();
    }

    init() {
        this.initMap();
        this.bindEvents();
    }

    initMap() {
        this.map = L.map('map').setView([31.2304, 121.4737], 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(this.map);

        this.map.on('click', (e) => this.handleMapClick(e));
    }

    bindEvents() {
        document.getElementById('loadSample').addEventListener('click', () => this.loadSampleData());
        document.getElementById('clearPoints').addEventListener('click', () => this.clearAllPoints());
        document.getElementById('solveBtn').addEventListener('click', () => this.solveVRP());
        document.getElementById('recalculateBtn').addEventListener('click', () => this.recalculateRoutes());
        document.getElementById('addForbiddenArea').addEventListener('click', () => this.enableForbiddenAreaMode());
        document.getElementById('clearForbidden').addEventListener('click', () => this.clearForbiddenAreas());
        document.getElementById('savePoint').addEventListener('click', () => this.savePoint());
        document.getElementById('cancelPoint').addEventListener('click', () => this.hidePointModal());
        document.getElementById('refreshTraffic').addEventListener('click', () => this.refreshTrafficData());
        document.getElementById('enableTraffic').addEventListener('change', (e) => {
            this.trafficEnabled = e.target.checked;
        });
    }

    handleMapClick(e) {
        if (this.addingForbiddenArea) {
            this.addForbiddenArea(e.latlng);
            this.addingForbiddenArea = false;
            return;
        }

        this.showPointModal(e.latlng);
    }

    showPointModal(latlng, existingIndex = null) {
        this.pendingLatLng = latlng;
        this.editingPointIndex = existingIndex;
        
        const isEdit = existingIndex !== null;
        const loc = isEdit ? this.locations[existingIndex] : null;
        
        document.getElementById('pointModal').style.display = 'flex';
        document.getElementById('pointName').value = isEdit ? loc.name : (this.locations.length === 0 ? '仓库' : `配送点${this.locations.length}`);
        document.getElementById('pointDemand').value = isEdit ? loc.demand : (this.locations.length === 0 ? 0 : 10);
        document.getElementById('pointTwStart').value = isEdit ? (this.timeWindows[existingIndex]?.[0] || 8) : 8;
        document.getElementById('pointTwEnd').value = isEdit ? (this.timeWindows[existingIndex]?.[1] || 18) : 18;
        document.getElementById('pointName').focus();
    }

    hidePointModal() {
        document.getElementById('pointModal').style.display = 'none';
        this.pendingLatLng = null;
        this.editingPointIndex = null;
    }

    savePoint() {
        const name = document.getElementById('pointName').value || '未命名';
        const demand = parseFloat(document.getElementById('pointDemand').value) || 0;
        const twStart = parseFloat(document.getElementById('pointTwStart').value) || 8;
        const twEnd = parseFloat(document.getElementById('pointTwEnd').value) || 18;

        if (this.editingPointIndex !== null) {
            this.locations[this.editingPointIndex].name = name;
            this.locations[this.editingPointIndex].demand = demand;
            this.timeWindows[this.editingPointIndex] = [twStart, twEnd];
            
            if (this.pendingLatLng) {
                this.locations[this.editingPointIndex].lat = this.pendingLatLng.lat;
                this.locations[this.editingPointIndex].lng = this.pendingLatLng.lng;
            }
            
            this.markers[this.editingPointIndex].setLatLng([
                this.locations[this.editingPointIndex].lat,
                this.locations[this.editingPointIndex].lng
            ]);
        } else if (this.pendingLatLng) {
            const newIndex = this.locations.length;
            this.addLocation(this.pendingLatLng, name, demand);
            this.timeWindows[newIndex] = [twStart, twEnd];
        }

        this.updatePointsList();
        this.hidePointModal();
    }

    addLocation(latlng, name, demand) {
        const location = {
            lat: latlng.lat,
            lng: latlng.lng,
            name: name,
            demand: demand
        };

        this.locations.push(location);
        this.addMarker(location, this.locations.length - 1);
        this.updatePointsList();
        this.checkCapacity();
    }

    addMarker(location, index) {
        const isDepot = index === 0;
        const icon = L.divIcon({
            className: 'custom-marker',
            html: `<div class="marker ${isDepot ? 'depot' : 'customer'}" data-index="${index}">
                <span>${isDepot ? '仓' : index}</span>
            </div>`,
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        const marker = L.marker([location.lat, location.lng], { 
            icon: icon,
            draggable: true
        }).addTo(this.map);

        marker.on('click', (e) => {
            L.DomEvent.stopPropagation(e);
            this.showPointModal(null, index);
        });

        marker.on('dragend', (e) => {
            const newPos = e.target.getLatLng();
            this.locations[index].lat = newPos.lat;
            this.locations[index].lng = newPos.lng;
            this.updatePointsList();
        });

        this.markers.push(marker);
    }

    showEditPointModal(index) {
        this.showPointModal(null, index);
    }

    updatePointsList() {
        const list = document.getElementById('pointsList');
        list.innerHTML = '';

        this.locations.forEach((loc, index) => {
            const tw = this.timeWindows[index] || [8, 18];
            const item = document.createElement('div');
            item.className = 'point-item';
            item.innerHTML = `
                <span class="point-index ${index === 0 ? 'depot' : ''}">${index === 0 ? '仓' : index}</span>
                <span class="point-name">${loc.name}</span>
                <span class="point-demand">需求: ${loc.demand}</span>
                <span class="point-demand">${tw[0]}-${tw[1]}</span>
                <button class="btn-delete" data-index="${index}">×</button>
            `;
            list.appendChild(item);
        });

        list.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deletePoint(parseInt(btn.dataset.index));
            });
        });
    }

    deletePoint(index) {
        this.locations.splice(index, 1);
        delete this.timeWindows[index];
        this.clearMarkers();
        this.locations.forEach((loc, i) => this.addMarker(loc, i));
        this.updatePointsList();
        this.checkCapacity();
    }

    clearMarkers() {
        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];
    }

    clearAllPoints() {
        this.locations = [];
        this.timeWindows = {};
        this.lockedRoutes.clear();
        this.trafficData = {};
        this.clearMarkers();
        this.clearRoutes();
        this.updatePointsList();
        document.getElementById('resultsPanel').style.display = 'none';
        document.getElementById('capacityPanel').style.display = 'none';
        document.getElementById('suggestionsPanel').style.display = 'none';
        this.updateTrafficStatus(null);
    }

    loadSampleData() {
        this.clearAllPoints();
        this.clearForbiddenAreas();

        const sampleData = [
            { lat: 31.2304, lng: 121.4737, name: '仓库', demand: 0, tw: [8, 18] },
            { lat: 31.2450, lng: 121.4910, name: '配送点A', demand: 15, tw: [9, 12] },
            { lat: 31.2150, lng: 121.4520, name: '配送点B', demand: 20, tw: [8, 11] },
            { lat: 31.2520, lng: 121.4480, name: '配送点C', demand: 12, tw: [10, 14] },
            { lat: 31.2200, lng: 121.5000, name: '配送点D', demand: 18, tw: [9, 13] },
            { lat: 31.2600, lng: 121.4800, name: '配送点E', demand: 25, tw: [8, 10] },
            { lat: 31.2050, lng: 121.4680, name: '配送点F', demand: 10, tw: [13, 17] },
            { lat: 31.2380, lng: 121.5150, name: '配送点G', demand: 22, tw: [14, 18] },
            { lat: 31.2550, lng: 121.4250, name: '配送点H', demand: 16, tw: [9, 15] },
            { lat: 31.2100, lng: 121.5100, name: '配送点I', demand: 14, tw: [12, 16] },
            { lat: 31.2400, lng: 121.4350, name: '配送点J', demand: 19, tw: [10, 14] }
        ];

        sampleData.forEach((loc, index) => {
            this.locations.push({
                lat: loc.lat,
                lng: loc.lng,
                name: loc.name,
                demand: loc.demand
            });
            this.timeWindows[index] = loc.tw;
            this.addMarker({ lat: loc.lat, lng: loc.lng }, index);
        });

        this.updatePointsList();
        this.checkCapacity();

        const forbiddenArea = {
            type: 'circle',
            center: [31.2300, 121.4850],
            radius: 1500
        };
        this.forbiddenAreas.push(forbiddenArea);
        this.renderForbiddenArea(forbiddenArea);
        this.updateForbiddenList();

        this.map.setView([31.2304, 121.4737], 12);
        
        setTimeout(() => this.refreshTrafficData(), 500);
    }

    enableForbiddenAreaMode() {
        this.addingForbiddenArea = true;
        alert('请点击地图选择禁行区域中心点');
    }

    addForbiddenArea(latlng) {
        const radius = prompt('请输入禁行区域半径（米）:', '1000');
        if (!radius || isNaN(radius)) return;

        const area = {
            type: 'circle',
            center: [latlng.lat, latlng.lng],
            radius: parseFloat(radius)
        };

        this.forbiddenAreas.push(area);
        this.renderForbiddenArea(area);
        this.updateForbiddenList();
    }

    renderForbiddenArea(area) {
        const circle = L.circle(area.center, {
            color: '#e74c3c',
            fillColor: '#e74c3c',
            fillOpacity: 0.2,
            radius: area.radius
        }).addTo(this.map);

        this.forbiddenCircles.push(circle);
    }

    updateForbiddenList() {
        const list = document.getElementById('forbiddenList');
        list.innerHTML = '';

        this.forbiddenAreas.forEach((area, index) => {
            const item = document.createElement('div');
            item.className = 'forbidden-item';
            item.innerHTML = `
                <span>禁行区 ${index + 1}</span>
                <span>半径: ${area.radius}m</span>
                <button class="btn-delete" data-index="${index}">×</button>
            `;
            list.appendChild(item);
        });

        list.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', () => {
                this.deleteForbiddenArea(parseInt(btn.dataset.index));
            });
        });
    }

    deleteForbiddenArea(index) {
        this.forbiddenAreas.splice(index, 1);
        this.map.removeLayer(this.forbiddenCircles[index]);
        this.forbiddenCircles.splice(index, 1);
        this.updateForbiddenList();
    }

    clearForbiddenAreas() {
        this.forbiddenAreas = [];
        this.forbiddenCircles.forEach(c => this.map.removeLayer(c));
        this.forbiddenCircles = [];
        this.updateForbiddenList();
    }

    async refreshTrafficData() {
        if (this.locations.length < 2) {
            alert('请先添加配送点');
            return;
        }

        const btn = document.getElementById('refreshTraffic');
        btn.disabled = true;
        btn.textContent = '获取中...';

        try {
            const response = await fetch('/api/traffic/matrix', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    locations: this.locations
                })
            });

            const result = await response.json();
            
            if (result.status === '1') {
                this.trafficData = result.traffic_matrix || {};
                this.updateTrafficStatus(result.traffic_matrix);
                if (result.note) {
                    alert(result.note);
                }
            } else {
                alert('获取交通数据失败: ' + (result.info || '未知错误'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('获取交通数据失败，请重试');
        } finally {
            btn.disabled = false;
            btn.textContent = '刷新交通数据';
        }
    }

    updateTrafficStatus(trafficMatrix) {
        const indicator = document.querySelector('.traffic-indicator');
        const text = document.querySelector('.traffic-text');

        if (!trafficMatrix || Object.keys(trafficMatrix).length === 0) {
            indicator.className = 'traffic-indicator';
            text.textContent = '未获取交通数据';
            return;
        }

        const values = Object.values(trafficMatrix);
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const max = Math.max(...values);

        if (max >= 1.5) {
            indicator.className = 'traffic-indicator status-bad';
            text.textContent = '交通拥堵严重';
        } else if (avg >= 1.2) {
            indicator.className = 'traffic-indicator status-medium';
            text.textContent = '交通较拥堵';
        } else {
            indicator.className = 'traffic-indicator status-good';
            text.textContent = '交通整体畅通';
        }
    }

    async checkCapacity() {
        if (this.locations.length < 2) {
            return;
        }

        try {
            const response = await fetch('/api/capacity/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    locations: this.locations,
                    vehicle_capacity: parseFloat(document.getElementById('vehicleCapacity').value),
                    num_vehicles: parseInt(document.getElementById('numVehicles').value)
                })
            });

            const result = await response.json();
            
            if (!result.error) {
                this.displayCapacityAnalysis(result);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    displayCapacityAnalysis(analysis) {
        document.getElementById('capacityPanel').style.display = 'block';
        
        const container = document.getElementById('capacityAnalysis');
        container.innerHTML = `
            <div class="capacity-item">
                <div class="capacity-row">
                    <span>总需求</span>
                    <span>${analysis.total_demand}</span>
                </div>
                <div class="capacity-row">
                    <span>总运力</span>
                    <span>${analysis.total_capacity}</span>
                </div>
                <div class="capacity-bar">
                    <div class="capacity-fill" style="width: ${Math.min(analysis.capacity_ratio, 100)}%"></div>
                </div>
                <div class="capacity-row" style="margin-top: 8px;">
                    <span>运力利用率</span>
                    <span>${analysis.capacity_ratio}%</span>
                </div>
            </div>
        `;

        if (analysis.suggestions && analysis.suggestions.length > 0) {
            this.displaySuggestions(analysis.suggestions);
        }
    }

    displaySuggestions(suggestions) {
        document.getElementById('suggestionsPanel').style.display = 'block';
        
        const container = document.getElementById('suggestionsList');
        container.innerHTML = '';

        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = `suggestion-item ${suggestion.priority}`;
            
            let detailHtml = `<div class="suggestion-title">${suggestion.message}</div>`;
            
            if (suggestion.type === 'outsourcing' && suggestion.customers) {
                detailHtml += `<div class="outsourcing-list">`;
                suggestion.customers.forEach(cust => {
                    detailHtml += `<div class="outsourcing-item">• ${cust.name} (需求: ${cust.demand})</div>`;
                });
                detailHtml += `</div>`;
            }
            
            item.innerHTML = detailHtml + `<div class="suggestion-detail">优先级: ${suggestion.priority === 'high' ? '高' : '中'}</div>`;
            container.appendChild(item);
        });
    }

    async solveVRP() {
        if (this.locations.length < 2) {
            alert('请至少添加一个仓库和一个配送点');
            return;
        }

        const btn = document.getElementById('solveBtn');
        btn.disabled = true;
        btn.textContent = '计算中...';

        try {
            const lockedRoutesData = this.routes
                .filter((r, idx) => this.lockedRoutes.has(idx))
                .map(r => ({
                    vehicle_id: r.vehicle_id,
                    location_indices: r.location_indices,
                    locked: true
                }));

            const objective_weights = {
                distance: parseFloat(document.getElementById('weightDistance').value),
                vehicles: parseFloat(document.getElementById('weightVehicles').value),
                time_window: parseFloat(document.getElementById('weightTimeWindow').value),
                fairness: parseFloat(document.getElementById('weightFairness').value)
            };

            const traffic_data = this.trafficEnabled ? this.trafficData : {};

            const response = await fetch('/api/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    locations: this.locations,
                    vehicle_capacity: parseFloat(document.getElementById('vehicleCapacity').value),
                    num_vehicles: parseInt(document.getElementById('numVehicles').value),
                    population_size: parseInt(document.getElementById('populationSize').value),
                    generations: parseInt(document.getElementById('generations').value),
                    forbidden_areas: this.forbiddenAreas,
                    locked_routes: lockedRoutesData,
                    traffic_data: traffic_data,
                    time_windows: this.timeWindows,
                    objective_weights: objective_weights
                })
            });

            const result = await response.json();
            
            if (result.error) {
                alert(result.error);
                return;
            }

            this.currentResult = result;
            this.displayResults(result);
            
            if (result.capacity_analysis && result.capacity_analysis.suggestions) {
                this.displaySuggestions(result.capacity_analysis.suggestions);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('计算出错，请重试');
        } finally {
            btn.disabled = false;
            btn.textContent = '🔍 开始优化计算';
        }
    }

    displayResults(result) {
        document.getElementById('resultsPanel').style.display = 'block';
        document.getElementById('totalDistance').textContent = result.total_distance;
        document.getElementById('usedVehicles').textContent = result.used_vehicles;
        document.getElementById('loadRate').textContent = result.load_rate;
        document.getElementById('totalLoad').textContent = result.total_load;
        
        if (result.time_window) {
            document.getElementById('twSatisfaction').textContent = result.time_window.satisfaction_rate;
        }
        if (result.fairness) {
            document.getElementById('fairnessScore').textContent = result.fairness.fairness_score;
        }

        this.clearRoutes();
        this.routes = result.routes;

        result.routes.forEach((route, index) => {
            this.renderRoute(route, index);
        });

        this.updateRoutesList();
    }

    renderRoute(route, routeIndex) {
        const latlngs = route.points.map(p => [p.lat, p.lng]);
        const isLocked = this.lockedRoutes.has(routeIndex);
        
        const polyline = L.polyline(latlngs, {
            color: isLocked ? '#95a5a6' : route.color,
            weight: isLocked ? 6 : 4,
            opacity: isLocked ? 0.9 : 0.8,
            dashArray: isLocked ? '10, 5' : null,
            routeIndex: routeIndex
        }).addTo(this.map);

        const arrowColor = isLocked ? '#7f8c8d' : route.color;
        const arrowIcon = L.divIcon({
            className: 'arrow-icon',
            html: `<div style="border-left: 8px solid ${arrowColor}; border-top: 4px solid transparent; border-bottom: 4px solid transparent;"></div>`,
            iconSize: [8, 8]
        });

        for (let i = 0; i < latlngs.length - 1; i++) {
            const midPoint = [
                (latlngs[i][0] + latlngs[i+1][0]) / 2,
                (latlngs[i][1] + latlngs[i+1][1]) / 2
            ];
            const angle = Math.atan2(
                latlngs[i+1][1] - latlngs[i][1],
                latlngs[i+1][0] - latlngs[i][0]
            ) * 180 / Math.PI;
            
            L.marker(midPoint, { icon: arrowIcon, rotationAngle: angle }).addTo(this.map);
        }

        this.routePolylines.push(polyline);
    }

    clearRoutes() {
        this.routePolylines.forEach(p => this.map.removeLayer(p));
        this.routePolylines = [];
    }

    toggleRouteLock(routeIndex) {
        if (this.lockedRoutes.has(routeIndex)) {
            this.lockedRoutes.delete(routeIndex);
        } else {
            this.lockedRoutes.add(routeIndex);
        }

        this.routes[routeIndex].locked = this.lockedRoutes.has(routeIndex);

        this.clearRoutes();
        this.routes.forEach((r, idx) => this.renderRoute(r, idx));
        this.updateRoutesList();
    }

    updateRoutesList() {
        const list = document.getElementById('routesList');
        list.innerHTML = '';

        this.routes.forEach((route, index) => {
            const isLocked = this.lockedRoutes.has(index);
            const item = document.createElement('div');
            item.className = `route-item ${isLocked ? 'route-locked' : ''}`;
            item.style.borderLeftColor = isLocked ? '#95a5a6' : route.color;
            item.innerHTML = `
                <div class="route-header">
                    <span class="route-name">车辆 ${route.vehicle_id}</span>
                    <span class="route-distance">${route.distance} km</span>
                    <button class="lock-btn ${isLocked ? 'locked' : ''}" data-route-index="${index}">
                        ${isLocked ? '🔒 已锁定' : '🔓 锁定'}
                    </button>
                </div>
                <div class="route-details">
                    <span>载重: ${route.load} (${route.load_rate}%)</span>
                </div>
                <div class="route-stops" data-route-index="${index}">
                    ${this.renderRouteStops(route, index, isLocked)}
                </div>
            `;
            list.appendChild(item);
        });

        list.querySelectorAll('.lock-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleRouteLock(parseInt(btn.dataset.routeIndex));
            });
        });

        this.enableDragAndDrop();
    }

    renderRouteStops(route, routeIndex, isLocked) {
        let html = '<div class="stop-list">';
        
        route.location_indices.forEach((locIdx, stopIndex) => {
            const loc = this.locations[locIdx];
            if (loc) {
                html += `
                    <div class="stop-item" 
                         draggable="${!isLocked}" 
                         data-route-index="${routeIndex}" 
                         data-stop-index="${stopIndex}"
                         data-loc-index="${locIdx}"
                         style="${isLocked ? 'cursor: not-allowed; opacity: 0.7;' : ''}">
                        <span class="stop-handle">${isLocked ? '🔒' : '⋮⋮'}</span>
                        <span class="stop-name">${loc.name}</span>
                        ${locIdx > 0 ? `<span class="stop-demand">${loc.demand}</span>` : ''}
                    </div>
                `;
            }
        });
        
        html += '</div>';
        return html;
    }

    enableDragAndDrop() {
        const stopItems = document.querySelectorAll('.stop-item');
        
        stopItems.forEach(item => {
            const routeIndex = parseInt(item.dataset.routeIndex);
            const isLocked = this.lockedRoutes.has(routeIndex);
            
            if (isLocked) {
                return;
            }

            item.addEventListener('dragstart', (e) => {
                const itemRouteIndex = parseInt(item.dataset.routeIndex);
                if (this.lockedRoutes.has(itemRouteIndex)) {
                    e.preventDefault();
                    return;
                }
                
                e.dataTransfer.setData('text/plain', JSON.stringify({
                    routeIndex: parseInt(item.dataset.routeIndex),
                    stopIndex: parseInt(item.dataset.stopIndex),
                    locIndex: parseInt(item.dataset.locIndex)
                }));
                item.classList.add('dragging');
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
            });

            item.addEventListener('dragover', (e) => {
                const targetRouteIndex = parseInt(item.dataset.routeIndex);
                if (this.lockedRoutes.has(targetRouteIndex)) {
                    return;
                }
                e.preventDefault();
                item.classList.add('drag-over');
            });

            item.addEventListener('dragleave', () => {
                item.classList.remove('drag-over');
            });

            item.addEventListener('drop', (e) => {
                const targetRouteIndex = parseInt(item.dataset.routeIndex);
                if (this.lockedRoutes.has(targetRouteIndex)) {
                    e.preventDefault();
                    return;
                }
                
                e.preventDefault();
                item.classList.remove('drag-over');
                
                const data = JSON.parse(e.dataTransfer.getData('text/plain'));
                const targetStopIndex = parseInt(item.dataset.stopIndex);

                this.moveStop(data.routeIndex, data.stopIndex, targetRouteIndex, targetStopIndex);
            });
        });
    }

    moveStop(fromRouteIndex, fromStopIndex, toRouteIndex, toStopIndex) {
        if (this.lockedRoutes.has(fromRouteIndex) || this.lockedRoutes.has(toRouteIndex)) {
            return;
        }

        if (fromRouteIndex === toRouteIndex && fromStopIndex === toStopIndex) return;

        const route = this.routes[fromRouteIndex];
        const locIndex = route.location_indices[fromStopIndex];

        if (locIndex === 0) {
            return;
        }

        route.location_indices.splice(fromStopIndex, 1);
        route.points.splice(fromStopIndex, 1);

        const targetRoute = this.routes[toRouteIndex];
        const insertIndex = toStopIndex;
        targetRoute.location_indices.splice(insertIndex, 0, locIndex);
        targetRoute.points.splice(insertIndex, 0, {
            lat: this.locations[locIndex].lat,
            lng: this.locations[locIndex].lng
        });

        this.routes = this.routes.filter(r => r.location_indices.length > 2);
        
        this.routes.forEach((r, idx) => {
            r.vehicle_id = idx + 1;
        });

        const newLockedRoutes = new Set();
        this.routes.forEach((r, idx) => {
            if (r.locked) {
                newLockedRoutes.add(idx);
            }
        });
        this.lockedRoutes = newLockedRoutes;

        this.clearRoutes();
        this.routes.forEach((r, idx) => this.renderRoute(r, idx));
        this.updateRoutesList();
    }

    async recalculateRoutes() {
        try {
            const response = await fetch('/api/recalculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    locations: this.locations,
                    routes: this.routes.map((r, idx) => ({
                        ...r,
                        locked: this.lockedRoutes.has(idx)
                    })),
                    vehicle_capacity: parseFloat(document.getElementById('vehicleCapacity').value)
                })
            });

            const result = await response.json();
            
            if (result.error) {
                alert(result.error);
                return;
            }

            result.routes.forEach((route, index) => {
                if (this.routes[index]) {
                    this.routes[index].distance = route.distance;
                    this.routes[index].load = route.load;
                    this.routes[index].load_rate = route.load_rate;
                }
            });

            document.getElementById('totalDistance').textContent = result.total_distance;
            document.getElementById('totalLoad').textContent = result.total_load;
            document.getElementById('usedVehicles').textContent = result.used_vehicles;

            this.updateRoutesList();
        } catch (error) {
            console.error('Error:', error);
            alert('计算出错，请重试');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new VRPOptimizer();
});
