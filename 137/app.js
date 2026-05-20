class MapboxSandbox {
    constructor() {
        this.map = null;
        this.mapInitialized = false;
        this.waypoints = [];
        this.demandPoints = [];
        this.geofences = [];
        this.spatialIndex = null;
        this.demandPointIndex = null;
        this.isPlaying = false;
        this.isPaused = false;
        this.playbackMarker = null;
        this.playbackAnimationId = null;
        this.drawingMode = null;
        this.drawingPoints = [];
        this.mbtilesSource = null;
        
        this.config = {
            defaultCenter: [116.4074, 39.9042],
            defaultZoom: 13,
            defaultPitch: 45,
            defaultBearing: 0,
            tileSize: 512
        };
        
        this.layerIds = {
            route: 'route-line',
            waypoints: 'waypoint-markers',
            demandPoints: 'demand-points',
            facilities: 'facility-markers',
            assignmentLines: 'assignment-lines',
            geofencesFill: 'geofences-fill',
            geofencesLine: 'geofences-line',
            playbackMarker: 'playback-marker'
        };
    }

    initMapbox(accessToken) {
        if (!accessToken || accessToken.includes('example')) {
            this.showNotification('请输入有效的Mapbox Access Token', 'warning');
            return;
        }

        mapboxgl.accessToken = accessToken;

        this.map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/standard',
            center: this.config.defaultCenter,
            zoom: this.config.defaultZoom,
            pitch: this.config.defaultPitch,
            bearing: this.config.defaultBearing,
            antialias: true,
            attributionControl: true
        });

        this.map.addControl(new mapboxgl.NavigationControl(), 'top-right');
        this.map.addControl(new mapboxgl.GeolocateControl({
            positionOptions: { enableHighAccuracy: true },
            trackUserLocation: true
        }), 'top-right');
        this.map.addControl(new mapboxgl.ScaleControl({ unit: 'metric' }), 'bottom-left');

        this.map.on('load', async () => {
            this.showNotification('Mapbox 地图加载成功', 'success');
            this.mapInitialized = true;
            this.initLayers();
            this.initSpatialIndex();
            this.init3DBuildings();
            this.setupEventListeners();
        });

        this.map.on('error', (error) => {
            console.error('Mapbox error:', error);
            this.showNotification('地图加载出错: ' + error.error.message, 'error');
        });
    }

    initLayers() {
        this.map.addSource('route-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        this.map.addLayer({
            id: this.layerIds.route,
            type: 'line',
            source: 'route-source',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#2196F3',
                'line-width': 6,
                'line-opacity': 0.9
            }
        });

        this.map.addSource('geofences-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        this.map.addLayer({
            id: this.layerIds.geofencesFill,
            type: 'fill',
            source: 'geofences-source',
            paint: {
                'fill-color': ['get', 'color'],
                'fill-opacity': 0.3
            }
        });

        this.map.addLayer({
            id: this.layerIds.geofencesLine,
            type: 'line',
            source: 'geofences-source',
            paint: {
                'line-color': ['get', 'color'],
                'line-width': 3
            }
        });

        this.map.addSource('demand-points-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        this.map.addLayer({
            id: this.layerIds.demandPoints,
            type: 'circle',
            source: 'demand-points-source',
            paint: {
                'circle-radius': 8,
                'circle-color': '#FF9800',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#fff'
            }
        });

        this.map.addSource('facilities-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        this.map.addLayer({
            id: this.layerIds.facilities,
            type: 'circle',
            source: 'facilities-source',
            paint: {
                'circle-radius': 12,
                'circle-color': '#4CAF50',
                'circle-stroke-width': 3,
                'circle-stroke-color': '#fff'
            }
        });

        this.map.addSource('assignment-source', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        this.map.addLayer({
            id: this.layerIds.assignmentLines,
            type: 'line',
            source: 'assignment-source',
            paint: {
                'line-color': '#9C27B0',
                'line-width': 2,
                'line-opacity': 0.6,
                'line-dasharray': [3, 3]
            }
        });

        this.map.addSource('playback-source', {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [0, 0] },
                properties: { bearing: 0 }
            }
        });

        this.map.addLayer({
            id: this.layerIds.playbackMarker,
            type: 'symbol',
            source: 'playback-source',
            layout: {
                'icon-image': 'car',
                'icon-size': 1.5,
                'icon-rotate': ['get', 'bearing'],
                'icon-allow-overlap': true
            }
        });

        this.initWaypointMarkers();
    }

    initWaypointMarkers() {
        if (!this.map.hasImage('waypoint-icon')) {
            const canvas = document.createElement('canvas');
            canvas.width = 40;
            canvas.height = 40;
            const ctx = canvas.getContext('2d');
            ctx.beginPath();
            ctx.arc(20, 20, 15, 0, Math.PI * 2);
            ctx.fillStyle = '#2196F3';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('1', 20, 20);
            this.map.addImage('waypoint-icon', canvas);
        }
    }

    initSpatialIndex() {
        this.spatialIndex = new rbush(9);
        this.demandPointIndex = new rbush(9);
        this.showNotification('RBush 空间索引初始化完成', 'success');
    }

    init3DBuildings() {
        const layers = this.map.getStyle().layers;
        const labelLayerId = layers.find(
            (layer) => layer.type === 'symbol' && layer.layout && layer.layout['text-field']
        )?.id;

        this.map.addLayer({
            id: '3d-buildings',
            source: 'composite',
            'source-layer': 'building',
            filter: ['==', 'extrude', 'true'],
            type: 'fill-extrusion',
            minzoom: 14,
            paint: {
                'fill-extrusion-color': '#aaa',
                'fill-extrusion-height': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    14,
                    0,
                    14.05,
                    ['get', 'height']
                ],
                'fill-extrusion-base': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    14,
                    0,
                    14.05,
                    ['get', 'min_height']
                ],
                'fill-extrusion-opacity': 0.8
            }
        }, labelLayerId);

        this.showNotification('3D建筑图层已加载', 'success');
    }

    toggle3DBuildings() {
        const show = document.getElementById('show3DBuildings').checked;
        if (this.map.getLayer('3d-buildings')) {
            this.map.setLayoutProperty('3d-buildings', 'visibility', show ? 'visible' : 'none');
        }
    }

    toggleTerrain() {
        const show = document.getElementById('showTerrain').checked;
        if (show) {
            this.map.addSource('mapbox-dem', {
                type: 'raster-dem',
                url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
                tileSize: 512,
                maxzoom: 14
            });
            this.map.setTerrain({ source: 'mapbox-dem', exaggeration: 1.5 });
            this.showNotification('3D地形已启用', 'success');
        } else {
            this.map.setTerrain(null);
            if (this.map.getSource('mapbox-dem')) {
                this.map.removeSource('mapbox-dem');
            }
            this.showNotification('3D地形已关闭', 'info');
        }
    }

    updateBuildingOpacity() {
        const opacity = parseInt(document.getElementById('buildingOpacity').value) / 100;
        if (this.map.getLayer('3d-buildings')) {
            this.map.setPaintProperty('3d-buildings', 'fill-extrusion-opacity', opacity);
        }
    }

    setupEventListeners() {
        this.map.on('click', (e) => this.handleMapClick(e));
        this.map.on('mousemove', (e) => this.handleMouseMove(e));
    }

    handleMapClick(e) {
        const coords = [e.lngLat.lng, e.lngLat.lat];

        if (this.drawingMode === 'polygon') {
            this.drawingPoints.push(coords);
            this.updateDrawingPreview();
            if (this.drawingPoints.length >= 3) {
                this.showNotification('双击完成绘制，继续点击添加更多顶点', 'info');
            }
            return;
        }

        if (this.drawingMode === 'circle') {
            const radius = parseInt(document.getElementById('geofenceRadius').value) || 500;
            const name = document.getElementById('geofenceName').value || `围栏${this.geofences.length + 1}`;
            this.addCircleGeofence(name, coords, radius);
            this.drawingMode = null;
            return;
        }

        if (this.mode === 'demandPoint') {
            this.addDemandPoint(coords);
            return;
        }

        this.addWaypoint(coords);
    }

    handleMouseMove(e) {
        this.checkGeofenceCrossing([e.lngLat.lng, e.lngLat.lat]);
    }

    addWaypoint(coords) {
        const index = this.waypoints.length;
        this.waypoints.push(coords);

        const marker = new mapboxgl.Marker({ color: '#2196F3' })
            .setLngLat(coords)
            .setPopup(new mapboxgl.Popup().setHTML(`<strong>途经点 ${index + 1}</strong><br/>${coords[1].toFixed(6)}, ${coords[0].toFixed(6)}`))
            .addTo(this.map);

        marker.getElement().addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeWaypoint(index);
        });

        this.updateWaypointList();
        this.updateSpatialIndex();
    }

    removeWaypoint(index) {
        this.waypoints.splice(index, 1);
        this.updateWaypointList();
        this.updateSpatialIndex();
        this.showNotification(`已删除途经点 ${index + 1}`, 'info');
    }

    clearWaypoints() {
        this.waypoints = [];
        document.querySelectorAll('.mapboxgl-marker').forEach(m => m.remove());
        this.map.getSource('route-source').setData({ type: 'FeatureCollection', features: [] });
        this.updateWaypointList();
        this.updateSpatialIndex();
        this.showNotification('已清除所有途经点', 'info');
    }

    updateWaypointList() {
        const listEl = document.getElementById('waypointList');
        if (this.waypoints.length === 0) {
            listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">暂无途经点</div>';
            return;
        }
        listEl.innerHTML = this.waypoints.map((wp, i) => `
            <div class="list-item">
                <span><strong>#${i + 1}</strong> ${wp[1].toFixed(4)}, ${wp[0].toFixed(4)}</span>
                <button class="delete-btn" onclick="sandbox.removeWaypoint(${i})">×</button>
            </div>
        `).join('');
    }

    updateSpatialIndex() {
        const items = this.waypoints.map((wp, i) => ({
            minX: wp[0],
            minY: wp[1],
            maxX: wp[0],
            maxY: wp[1],
            index: i,
            coords: wp
        }));
        this.spatialIndex.clear();
        this.spatialIndex.load(items);
    }

    spatialQuery(bbox) {
        return this.spatialIndex.search({
            minX: bbox[0],
            minY: bbox[1],
            maxX: bbox[2],
            maxY: bbox[3]
        });
    }

    calculateRoute() {
        if (this.waypoints.length < 2) {
            this.showNotification('请至少添加2个途经点', 'warning');
            return;
        }

        const line = turf.lineString(this.waypoints);
        const simplified = turf.simplify(line, { tolerance: 0.0001, highQuality: true });

        this.map.getSource('route-source').setData(simplified);

        const distance = turf.length(line, { units: 'kilometers' });
        const duration = distance / 30 * 60;

        document.getElementById('routeStats').innerHTML = `
            <div class="stats-row"><span>总距离:</span><strong>${distance.toFixed(2)} km</strong></div>
            <div class="stats-row"><span>预计用时:</span><strong>${Math.round(duration)} 分钟</strong></div>
            <div class="stats-row"><span>途经点数:</span><strong>${this.waypoints.length}</strong></div>
        `;

        const bounds = turf.bbox(line);
        this.map.fitBounds(bounds, { padding: 100 });
        this.showNotification('路径计算完成', 'success');
    }

    addDemandPoint(coords) {
        this.demandPoints.push(coords);
        
        const features = this.demandPoints.map((wp, i) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: wp },
            properties: { index: i }
        }));

        this.map.getSource('demand-points-source').setData({
            type: 'FeatureCollection',
            features
        });

        this.updateDemandPointIndex();
        this.updateDemandPointList();
    }

    removeDemandPoint(index) {
        this.demandPoints.splice(index, 1);
        const features = this.demandPoints.map((wp, i) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: wp },
            properties: { index: i }
        }));
        this.map.getSource('demand-points-source').setData({
            type: 'FeatureCollection',
            features
        });
        this.updateDemandPointIndex();
        this.updateDemandPointList();
    }

    clearDemandPoints() {
        this.demandPoints = [];
        this.map.getSource('demand-points-source').setData({ type: 'FeatureCollection', features: [] });
        this.map.getSource('facilities-source').setData({ type: 'FeatureCollection', features: [] });
        this.map.getSource('assignment-source').setData({ type: 'FeatureCollection', features: [] });
        this.demandPointIndex.clear();
        this.updateDemandPointList();
        this.mode = null;
        this.showNotification('已清除所有需求点', 'info');
    }

    updateDemandPointIndex() {
        const items = this.demandPoints.map((wp, i) => ({
            minX: wp[0],
            minY: wp[1],
            maxX: wp[0],
            maxY: wp[1],
            index: i,
            coords: wp
        }));
        this.demandPointIndex.clear();
        this.demandPointIndex.load(items);
    }

    updateDemandPointList() {
        const listEl = document.getElementById('demandPointList');
        if (this.demandPoints.length === 0) {
            listEl.innerHTML = '<div style="padding: 10px; text-align: center; color: #999; font-size: 12px;">暂无需求点</div>';
            return;
        }
        listEl.innerHTML = this.demandPoints.map((wp, i) => `
            <div class="list-item">
                <span><strong>#${i + 1}</strong> ${wp[1].toFixed(4)}, ${wp[0].toFixed(4)}</span>
                <button class="delete-btn" onclick="sandbox.removeDemandPoint(${i})">×</button>
            </div>
        `).join('');
    }

    calculateOptimalLocations() {
        if (this.demandPoints.length < 3) {
            this.mode = 'demandPoint';
            this.showNotification('请点击地图添加至少3个需求点', 'info');
            return;
        }

        const p = parseInt(document.getElementById('facilityCount').value) || 2;
        const n = this.demandPoints.length;

        if (n < p) {
            this.showNotification('需求点数量不能少于设施数量', 'warning');
            return;
        }

        let bestFacilities = [];
        let bestCost = Infinity;
        const iterations = 100;

        for (let iter = 0; iter < iterations; iter++) {
            const shuffled = [...Array(n).keys()].sort(() => Math.random() - 0.5);
            const facilities = shuffled.slice(0, p).map(i => ({ ...this.demandPoints[i] }));
            const assignment = this.assignToFacilities(facilities);
            const cost = this.calculateTotalCost(assignment);

            if (cost < bestCost) {
                bestCost = cost;
                bestFacilities = facilities.map(f => [...f]);
            }
        }

        bestFacilities = this.optimizeLocations(bestFacilities);
        const finalAssignment = this.assignToFacilities(bestFacilities);
        const finalCost = this.calculateTotalCost(finalAssignment);

        this.displayOptimalLocations(bestFacilities, finalAssignment, finalCost);
    }

    assignToFacilities(facilities) {
        return this.demandPoints.map(dp => {
            let minDist = Infinity;
            let bestFacility = 0;

            for (let i = 0; i < facilities.length; i++) {
                const dist = turf.distance(turf.point(dp), turf.point(facilities[i]), { units: 'kilometers' });
                if (dist < minDist) {
                    minDist = dist;
                    bestFacility = i;
                }
            }

            return { demand: dp, facilityIndex: bestFacility, distance: minDist };
        });
    }

    calculateTotalCost(assignment) {
        return assignment.reduce((sum, a) => sum + a.distance, 0);
    }

    optimizeLocations(facilities) {
        const assignment = this.assignToFacilities(facilities);
        const optimized = [];

        for (let i = 0; i < facilities.length; i++) {
            const assigned = assignment.filter(a => a.facilityIndex === i);
            if (assigned.length === 0) {
                optimized.push([...facilities[i]]);
                continue;
            }

            let sumLng = 0, sumLat = 0;
            for (const a of assigned) {
                sumLng += a.demand[0];
                sumLat += a.demand[1];
            }
            optimized.push([sumLng / assigned.length, sumLat / assigned.length]);
        }

        return optimized;
    }

    displayOptimalLocations(facilities, assignment, totalCost) {
        const colors = ['#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#00BCD4'];

        const facilityFeatures = facilities.map((f, i) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: f },
            properties: { index: i, color: colors[i % colors.length] }
        }));

        this.map.getSource('facilities-source').setData({
            type: 'FeatureCollection',
            features: facilityFeatures
        });

        const lineFeatures = assignment.map(a => ({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: [a.demand, facilities[a.facilityIndex]]
            },
            properties: {
                distance: a.distance,
                color: colors[a.facilityIndex % colors.length]
            }
        }));

        this.map.getSource('assignment-source').setData({
            type: 'FeatureCollection',
            features: lineFeatures
        });

        document.getElementById('locationStats').innerHTML = `
            <div class="stats-row"><span>设施数量:</span><strong>${facilities.length}</strong></div>
            <div class="stats-row"><span>需求点数:</span><strong>${this.demandPoints.length}</strong></div>
            <div class="stats-row"><span>总距离成本:</span><strong>${totalCost.toFixed(2)} km</strong></div>
            <div class="stats-row"><span>平均距离:</span><strong>${(totalCost / this.demandPoints.length).toFixed(2)} km</strong></div>
        `;

        const allPoints = [...this.demandPoints, ...facilities];
        const bounds = new mapboxgl.LngLatBounds();
        allPoints.forEach(p => bounds.extend(p));
        this.map.fitBounds(bounds, { padding: 100 });

        this.showNotification('P-中值选址计算完成', 'success');
    }

    startCreateCircleFence() {
        this.drawingMode = 'circle';
        this.showNotification('点击地图创建圆形围栏', 'info');
    }

    startCreatePolygonFence() {
        this.drawingMode = 'polygon';
        this.drawingPoints = [];
        this.showNotification('点击添加顶点，双击完成多边形绘制', 'info');

        this.map.on('dblclick', (e) => {
            if (this.drawingMode === 'polygon' && this.drawingPoints.length >= 3) {
                this.finishPolygonFence();
            }
        });
    }

    updateDrawingPreview() {
        if (this.drawingPoints.length < 2) return;
        
        const line = turf.lineString(this.drawingPoints);
        this.map.getSource('geofences-source').setData({
            type: 'FeatureCollection',
            features: [
                ...this.geofences.map(g => g.feature),
                {
                    type: 'Feature',
                    geometry: { type: 'LineString', coordinates: this.drawingPoints },
                    properties: { color: '#2196F3' }
                }
            ]
        });
    }

    finishPolygonFence() {
        if (this.drawingPoints.length < 3) {
            this.showNotification('多边形至少需要3个顶点', 'warning');
            return;
        }

        const name = document.getElementById('geofenceName').value || `围栏${this.geofences.length + 1}`;
        this.drawingPoints.push(this.drawingPoints[0]);

        const polygon = turf.polygon([this.drawingPoints]);
        this.addPolygonGeofence(name, polygon);
        
        this.drawingMode = null;
        this.drawingPoints = [];
        this.updateGeofencesSource();
    }

    addCircleGeofence(name, center, radius) {
        const circle = turf.circle(center, radius / 1000, { units: 'kilometers', steps: 64 });
        const feature = {
            ...circle,
            properties: {
                name,
                type: 'circle',
                center,
                radius,
                color: '#9C27B0',
                id: Date.now()
            }
        };

        this.geofences.push({ name, feature, id: feature.properties.id });
        this.updateGeofencesSource();
        this.updateGeofenceList();
        this.showNotification(`已创建围栏: ${name}`, 'success');
    }

    addPolygonGeofence(name, polygon) {
        const feature = {
            ...polygon,
            properties: {
                name,
                type: 'polygon',
                color: '#9C27B0',
                id: Date.now()
            }
        };

        this.geofences.push({ name, feature, id: feature.properties.id });
        this.updateGeofencesSource();
        this.updateGeofenceList();
        this.showNotification(`已创建围栏: ${name}`, 'success');
    }

    removeGeofence(id) {
        const index = this.geofences.findIndex(g => g.id === id);
        if (index !== -1) {
            const name = this.geofences[index].name;
            this.geofences.splice(index, 1);
            this.updateGeofencesSource();
            this.updateGeofenceList();
            this.showNotification(`已删除围栏: ${name}`, 'info');
        }
    }

    clearGeofences() {
        this.geofences = [];
        this.updateGeofencesSource();
        this.updateGeofenceList();
        this.showNotification('已清除所有围栏', 'info');
    }

    updateGeofencesSource() {
        this.map.getSource('geofences-source').setData({
            type: 'FeatureCollection',
            features: this.geofences.map(g => g.feature)
        });
    }

    updateGeofenceList() {
        const listEl = document.getElementById('geofenceList');
        if (this.geofences.length === 0) {
            listEl.innerHTML = '<div style="padding: 10px; text-align: center; color: #999; font-size: 12px;">暂无围栏</div>';
            return;
        }
        listEl.innerHTML = this.geofences.map(g => `
            <div class="list-item">
                <span>${g.name}</span>
                <button class="delete-btn" onclick="sandbox.removeGeofence(${g.id})">×</button>
            </div>
        `).join('');
    }

    checkGeofenceCrossing(coords) {
        for (const fence of this.geofences) {
            const point = turf.point(coords);
            const polygon = fence.feature;

            if (!fence.lastInside) {
                fence.lastInside = false;
            }

            const isInside = turf.booleanPointInPolygon(point, polygon);

            if (isInside && !fence.lastInside) {
                this.showNotification(`⚠️ 进入围栏: ${fence.name}`, 'warning');
            } else if (!isInside && fence.lastInside) {
                this.showNotification(`⚠️ 离开围栏: ${fence.name}`, 'warning');
            }

            fence.lastInside = isInside;
        }
    }

    startPlayback() {
        if (this.waypoints.length < 2) {
            this.showNotification('请先创建路径', 'warning');
            return;
        }

        this.isPlaying = true;
        this.isPaused = false;

        const speed = parseInt(document.getElementById('playbackSpeed').value) || 3;
        let currentSegment = 0;
        let segmentProgress = 0;
        const segmentTime = 1000 / speed;

        const animate = () => {
            if (!this.isPlaying || this.isPaused) {
                this.playbackAnimationId = requestAnimationFrame(animate);
                return;
            }

            segmentProgress += 0.02;

            if (segmentProgress >= 1) {
                segmentProgress = 0;
                currentSegment++;

                if (currentSegment >= this.waypoints.length - 1) {
                    this.stopPlayback();
                    return;
                }
            }

            const from = this.waypoints[currentSegment];
            const to = this.waypoints[currentSegment + 1];
            const lng = from[0] + (to[0] - from[0]) * segmentProgress;
            const lat = from[1] + (to[1] - from[1]) * segmentProgress;
            const bearing = turf.bearing(turf.point(from), turf.point(to));

            this.map.getSource('playback-source').setData({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [lng, lat] },
                properties: { bearing }
            });

            this.map.panTo([lng, lat], { duration: 100 });

            this.playbackAnimationId = requestAnimationFrame(animate);
        };

        animate();
        this.showNotification('轨迹回放开始', 'success');
    }

    pausePlayback() {
        this.isPaused = !this.isPaused;
        this.showNotification(this.isPaused ? '回放已暂停' : '回放继续', 'info');
    }

    stopPlayback() {
        this.isPlaying = false;
        this.isPaused = false;
        if (this.playbackAnimationId) {
            cancelAnimationFrame(this.playbackAnimationId);
        }
        this.map.getSource('playback-source').setData({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [0, 0] },
            properties: { bearing: 0 }
        });
        this.showNotification('轨迹回放已停止', 'info');
    }

    async loadMBTiles(file) {
        const statusEl = document.getElementById('mbtilesStatus');
        statusEl.innerHTML = '<div>正在加载 MBTiles 文件...</div>';

        try {
            const arrayBuffer = await file.arrayBuffer();
            const uint8Array = new Uint8Array(arrayBuffer);

            if (this.mbtilesSource) {
                this.map.removeSource('mbtiles');
            }

            this.map.addSource('mbtiles', {
                type: 'raster',
                tiles: [],
                tileSize: 256
            });

            this.map.addLayer({
                id: 'mbtiles-layer',
                type: 'raster',
                source: 'mbtiles',
                minzoom: 0,
                maxzoom: 22
            });

            statusEl.innerHTML = `
                <div class="stats-row"><span>文件名:</span><span>${file.name}</span></div>
                <div class="stats-row"><span>大小:</span><span>${(file.size / 1024 / 1024).toFixed(2)} MB</span></div>
                <div class="stats-row"><span>状态:</span><span style="color: #4CAF50">已加载</span></div>
            `;

            this.showNotification('MBTiles 文件加载完成', 'success');

        } catch (error) {
            console.error('MBTiles load error:', error);
            statusEl.innerHTML = `<div style="color: #f44336">加载失败: ${error.message}</div>`;
            this.showNotification('MBTiles 文件加载失败', 'error');
        }
    }

    exportToGeoJSON() {
        const features = [];

        if (this.waypoints.length > 0) {
            features.push(turf.lineString(this.waypoints, { name: '规划路径' }));
            this.waypoints.forEach((wp, i) => {
                features.push(turf.point(wp, { name: `途经点${i + 1}` }));
            });
        }

        this.geofences.forEach(g => {
            features.push({ ...g.feature, properties: { name: g.name } });
        });

        const geojson = {
            type: 'FeatureCollection',
            features
        };

        this.downloadFile(JSON.stringify(geojson, null, 2), 'route.geojson', 'application/geo+json');
        this.showNotification('GeoJSON 导出完成', 'success');
    }

    exportToGPX() {
        if (this.waypoints.length < 2) {
            this.showNotification('请先创建路径', 'warning');
            return;
        }

        const now = new Date().toISOString();
        let gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Mapbox GL Sandbox" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>规划路径</name>
    <time>${now}</time>
  </metadata>
  <rte>
    <name>规划路径</name>
`;

        this.waypoints.forEach((wp, i) => {
            gpx += `    <rtept lat="${wp[1]}" lon="${wp[0]}">
      <name>途经点${i + 1}</name>
      <time>${now}</time>
    </rtept>
`;
        });

        gpx += `  </rte>
  <trk>
    <name>轨迹</name>
    <trkseg>
`;

        this.waypoints.forEach((wp, i) => {
            gpx += `      <trkpt lat="${wp[1]}" lon="${wp[0]}">
        <ele>0</ele>
        <time>${now}</time>
      </trkpt>
`;
        });

        gpx += `    </trkseg>
  </trk>
</gpx>`;

        this.downloadFile(gpx, 'route.gpx', 'application/gpx+xml');
        this.showNotification('GPX 导出完成', 'success');
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    resetView() {
        this.map.flyTo({
            center: this.config.defaultCenter,
            zoom: this.config.defaultZoom,
            pitch: this.config.defaultPitch,
            bearing: this.config.defaultBearing
        });
    }

    fitToBounds() {
        const allPoints = [
            ...this.waypoints,
            ...this.demandPoints,
            ...this.geofences.flatMap(g => turf.coordAll(g.feature))
        ];

        if (allPoints.length === 0) {
            this.showNotification('没有可适配的要素', 'warning');
            return;
        }

        const bounds = new mapboxgl.LngLatBounds();
        allPoints.forEach(p => bounds.extend(p));
        this.map.fitBounds(bounds, { padding: 100 });
    }

    showNotification(message, type = 'info') {
        const existing = document.querySelector('.notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 3000);
    }
}

let sandbox;

document.addEventListener('DOMContentLoaded', () => {
    sandbox = new MapboxSandbox();
});

function initMapbox() {
    const token = document.getElementById('accessToken').value;
    sandbox.initMapbox(token);
}

function toggle3DBuildings() {
    sandbox.toggle3DBuildings();
}

function toggleTerrain() {
    sandbox.toggleTerrain();
}

function updateBuildingOpacity() {
    sandbox.updateBuildingOpacity();
}

function calculateRoute() {
    sandbox.calculateRoute();
}

function clearWaypoints() {
    sandbox.clearWaypoints();
}

function startPlayback() {
    sandbox.startPlayback();
}

function pausePlayback() {
    sandbox.pausePlayback();
}

function stopPlayback() {
    sandbox.stopPlayback();
}

function calculateOptimalLocations() {
    sandbox.calculateOptimalLocations();
}

function clearDemandPoints() {
    sandbox.clearDemandPoints();
}

function startCreateCircleFence() {
    sandbox.startCreateCircleFence();
}

function startCreatePolygonFence() {
    sandbox.startCreatePolygonFence();
}

function clearGeofences() {
    sandbox.clearGeofences();
}

function exportToGeoJSON() {
    sandbox.exportToGeoJSON();
}

function exportToGPX() {
    sandbox.exportToGPX();
}

function resetView() {
    sandbox.resetView();
}

function fitToBounds() {
    sandbox.fitToBounds();
}

function loadMBTiles(event) {
    const file = event.target.files[0];
    if (file) {
        sandbox.loadMBTiles(file);
    }
}
