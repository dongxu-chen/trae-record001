class MapManager {
    constructor() {
        this.map = null;
        this.roadLayers = {};
        this.nodeLayers = {};
        this.vehicleMarkers = {};
        this.heatmapLayer = null;
        this.networkConfig = null;
        this.init();
    }

    init() {
        this.map = L.map('map', {
            center: CONFIG.map.center,
            zoom: CONFIG.map.zoom,
            minZoom: CONFIG.map.minZoom,
            maxZoom: CONFIG.map.maxZoom
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        this.setupLayerControls();
    }

    setupLayerControls() {
        document.getElementById('show-heatmap').addEventListener('change', (e) => {
            this.toggleHeatmap(e.target.checked);
        });
        document.getElementById('show-vehicles').addEventListener('change', (e) => {
            this.toggleVehicles(e.target.checked);
        });
        document.getElementById('show-roads').addEventListener('change', (e) => {
            this.toggleRoads(e.target.checked);
        });
    }

    loadNetwork(networkConfig) {
        this.networkConfig = networkConfig;
        this.clearLayers();
        this.drawRoads(networkConfig.roads);
        this.drawNodes(networkConfig.nodes);
        this.fitToBounds();
    }

    clearLayers() {
        Object.values(this.roadLayers).forEach(layer => {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        });
        Object.values(this.nodeLayers).forEach(layer => {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        });
        this.clearVehicleMarkers();
        this.clearHeatmap();
        this.roadLayers = {};
        this.nodeLayers = {};
    }

    drawRoads(roads) {
        roads.forEach(road => {
            const coords = road.coordinates || this.generateCoords(road);
            const polyline = L.polyline(coords, {
                color: CONFIG.colors.road,
                weight: 4,
                opacity: 0.8,
                smoothFactor: 1
            }).bindTooltip(road.name || road.id, {
                permanent: false,
                direction: 'top'
            });

            polyline.addTo(this.map);
            this.roadLayers[road.id] = polyline;
        });
    }

    drawNodes(nodes) {
        nodes.forEach(node => {
            const marker = L.circleMarker([node.lat, node.lng], {
                radius: 6,
                fillColor: CONFIG.colors.node,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            }).bindPopup(`<strong>节点 ${node.id}</strong><br>坐标: ${node.lat}, ${node.lng}`);

            marker.addTo(this.map);
            this.nodeLayers[node.id] = marker;
        });
    }

    generateCoords(road) {
        if (!this.networkConfig) return [[0, 0], [0, 0]];
        const startNode = this.networkConfig.nodes.find(n => n.id === road.start_node);
        const endNode = this.networkConfig.nodes.find(n => n.id === road.end_node);
        if (startNode && endNode) {
            return [[startNode.lat, startNode.lng], [endNode.lat, endNode.lng]];
        }
        return [[0, 0], [0, 0]];
    }

    updateRoadColors(roadDetails) {
        Object.entries(roadDetails).forEach(([roadId, details]) => {
            if (this.roadLayers[roadId]) {
                const color = details.color || CONFIG.colors.road;
                this.roadLayers[roadId].setStyle({
                    color: color,
                    weight: details.density > 0.7 ? 6 : 4
                });
            }
        });
    }

    updateVehiclePositions(vehicles) {
        const currentIds = new Set(vehicles.map(v => v.id));

        Object.keys(this.vehicleMarkers).forEach(id => {
            if (!currentIds.has(parseInt(id))) {
                if (this.map.hasLayer(this.vehicleMarkers[id])) {
                    this.map.removeLayer(this.vehicleMarkers[id]);
                }
                delete this.vehicleMarkers[id];
            }
        });

        vehicles.forEach(vehicle => {
            const color = getSpeedColor(vehicle.speed);
            const markerContent = `<div class="marker-content" style="background: ${color};"></div>`;

            if (this.vehicleMarkers[vehicle.id]) {
                this.vehicleMarkers[vehicle.id].setLatLng([vehicle.lat, vehicle.lng]);
                this.vehicleMarkers[vehicle.id].getElement().innerHTML = markerContent;
            } else {
                const icon = L.divIcon({
                    className: 'vehicle-marker',
                    html: markerContent,
                    iconSize: [CONFIG.visualization.vehicleMarkerSize, CONFIG.visualization.vehicleMarkerSize],
                    iconAnchor: [CONFIG.visualization.vehicleMarkerSize / 2, CONFIG.visualization.vehicleMarkerSize / 2]
                });

                const marker = L.marker([vehicle.lat, vehicle.lng], { icon: icon })
                    .bindTooltip(`ID: ${vehicle.id}<br>速度: ${vehicle.speed} m/s<br>路段: ${vehicle.road_id}`, {
                        offset: [10, 0]
                    });

                if (document.getElementById('show-vehicles').checked) {
                    marker.addTo(this.map);
                }
                this.vehicleMarkers[vehicle.id] = marker;
            }
        });
    }

    updateHeatmap(heatmapData) {
        this.clearHeatmap();

        if (!heatmapData || heatmapData.length === 0) return;

        this.heatmapLayer = L.heatLayer(heatmapData, {
            radius: CONFIG.visualization.heatmapRadius,
            blur: CONFIG.visualization.heatmapBlur,
            max: CONFIG.visualization.heatmapMax,
            gradient: {
                0.2: '#2ecc71',
                0.4: '#f1c40f',
                0.6: '#e67e22',
                0.8: '#e74c3c',
                1.0: '#c0392b'
            }
        });

        if (document.getElementById('show-heatmap').checked) {
            this.heatmapLayer.addTo(this.map);
        }
    }

    updateRoadHeatmap(roadHeatmapData) {
        const allPoints = [];
        Object.values(roadHeatmapData).forEach(points => {
            allPoints.push(...points);
        });
        this.updateHeatmap(allPoints);
    }

    clearVehicleMarkers() {
        Object.values(this.vehicleMarkers).forEach(marker => {
            if (this.map.hasLayer(marker)) {
                this.map.removeLayer(marker);
            }
        });
        this.vehicleMarkers = {};
    }

    clearHeatmap() {
        if (this.heatmapLayer && this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
        }
        this.heatmapLayer = null;
    }

    toggleHeatmap(show) {
        if (this.heatmapLayer) {
            if (show) {
                this.heatmapLayer.addTo(this.map);
            } else {
                this.map.removeLayer(this.heatmapLayer);
            }
        }
    }

    toggleVehicles(show) {
        Object.values(this.vehicleMarkers).forEach(marker => {
            if (show) {
                marker.addTo(this.map);
            } else if (this.map.hasLayer(marker)) {
                this.map.removeLayer(marker);
            }
        });
    }

    toggleRoads(show) {
        Object.values(this.roadLayers).forEach(layer => {
            if (show) {
                layer.addTo(this.map);
            } else if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        });
    }

    fitToBounds() {
        const coords = [];
        if (this.networkConfig && this.networkConfig.nodes) {
            this.networkConfig.nodes.forEach(node => {
                coords.push([node.lat, node.lng]);
            });
        }
        if (coords.length > 0) {
            this.map.fitBounds(coords, { padding: [50, 50] });
        }
    }

    signalUpdate(signalStates) {
        Object.entries(signalStates || {}).forEach(([signalId, state]) => {
            const greenRoads = state.green_roads || [];
            const redRoads = state.red_roads || [];

            greenRoads.forEach(roadId => {
                if (this.roadLayers[roadId]) {
                    const originalColor = this.roadLayers[roadId].options.color;
                    this.roadLayers[roadId].setStyle({ dashArray: '10, 10' });
                }
            });
        });
    }
}
