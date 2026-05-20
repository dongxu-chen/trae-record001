let trailTimestamps = [];
let trailVelocities = [];
let trailDistances = [];
let trailPointData = [];
const startTime = Date.now() - 30000;

const trailData = {
    type: 'FeatureCollection',
    features: [{
        type: 'Feature',
        properties: {},
        geometry: {
            type: 'LineString',
            coordinates: generateTrailCoordinates()
        }
    }]
};

function generateTrailCoordinates() {
    const coordinates = [];
    trailTimestamps = [];
    trailVelocities = [];
    trailDistances = [];
    trailPointData = [];
    
    const startLng = 116.390;
    const startLat = 39.905;
    const points = 200;
    const intervalMs = 150;
    
    let totalDistance = 0;
    
    for (let i = 0; i < points; i++) {
        const progress = i / points;
        const baseSpeed = 30 + Math.sin(progress * Math.PI * 3) * 20 + progress * 10;
        const lng = startLng + progress * 0.015 + Math.sin(progress * Math.PI * 4) * 0.002;
        const lat = startLat + progress * 0.01 + Math.cos(progress * Math.PI * 3) * 0.0015;
        const alt = 50 + Math.sin(progress * Math.PI * 2) * 30 + progress * 100;
        
        coordinates.push([lng, lat, alt]);
        trailTimestamps.push(startTime + i * intervalMs);
        trailVelocities.push(baseSpeed);
        
        if (i > 0) {
            const from = coordinates[i - 1];
            const to = coordinates[i];
            totalDistance += turf.distance(turf.point(from), turf.point(to));
        }
        trailDistances.push(totalDistance);
        
        trailPointData.push({
            coordinates: [lng, lat, alt],
            timestamp: trailTimestamps[i],
            velocity: baseSpeed,
            distance: totalDistance
        });
    }
    
    return coordinates;
}

function calculateVelocities() {
    const coordinates = getTrailCoordinates();
    trailVelocities = [];
    trailDistances = [];
    
    let totalDistance = 0;
    
    for (let i = 0; i < coordinates.length; i++) {
        if (i === 0) {
            trailVelocities.push(0);
            trailDistances.push(0);
        } else {
            const from = coordinates[i - 1];
            const to = coordinates[i];
            const distance = turf.distance(turf.point(from), turf.point(to));
            totalDistance += distance;
            
            const timeDiff = (trailTimestamps[i] - trailTimestamps[i - 1]) / 1000 / 3600;
            const velocity = timeDiff > 0 ? distance / timeDiff : 0;
            
            trailVelocities.push(velocity);
            trailDistances.push(totalDistance);
        }
    }
    
    return trailVelocities;
}

function getVelocityColor(velocity, minVelocity, maxVelocity) {
    const normalized = (velocity - minVelocity) / (maxVelocity - minVelocity);
    
    if (normalized < 0.25) {
        return '#00ff00';
    } else if (normalized < 0.5) {
        return '#ffff00';
    } else if (normalized < 0.75) {
        return '#ff8800';
    } else {
        return '#ff0000';
    }
}

function createVelocityGradientLine() {
    const coordinates = getTrailCoordinates();
    const velocities = getTrailVelocities();
    const features = [];
    
    const maxVelocity = Math.max(...velocities);
    const minVelocity = Math.min(...velocities);
    
    for (let i = 1; i < coordinates.length; i++) {
        const from = coordinates[i - 1];
        const to = coordinates[i];
        const velocity = velocities[i];
        
        features.push({
            type: 'Feature',
            properties: {
                velocity: velocity
            },
            geometry: {
                type: 'LineString',
                coordinates: [from, to]
            }
        });
    }
    
    return {
        type: 'FeatureCollection',
        features: features
    };
}

function initTrail() {
    const map = getMap();
    
    if (!map.getSource('trail-source')) {
        map.addSource('trail-source', {
            type: 'geojson',
            data: trailData
        });
    }
    
    if (!map.getSource('trail-velocity-source')) {
        map.addSource('trail-velocity-source', {
            type: 'geojson',
            data: createVelocityGradientLine()
        });
    }
    
    if (!map.getLayer('trail-glow')) {
        map.addLayer({
            id: 'trail-glow',
            type: 'line',
            source: 'trail-source',
            paint: {
                'line-color': '#a78bfa',
                'line-width': [
                    'interpolate',
                    ['exponential', 2],
                    ['zoom'],
                    10, 4,
                    14, 12,
                    18, 48
                ],
                'line-opacity': 0.2,
                'line-blur': 8
            }
        });
    }
    
    if (!map.getLayer('trail-velocity-line')) {
        map.addLayer({
            id: 'trail-velocity-line',
            type: 'line',
            source: 'trail-velocity-source',
            paint: {
                'line-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'velocity'],
                    0, '#00ff00',
                    20, '#88ff00',
                    40, '#ffff00',
                    60, '#ff8800',
                    80, '#ff0000'
                ],
                'line-width': [
                    'interpolate',
                    ['exponential', 2],
                    ['zoom'],
                    10, 2,
                    14, 6,
                    18, 24
                ],
                'line-opacity': 0.9
            }
        });
    }
}

function getTrailCoordinates() {
    return trailData.features[0].geometry.coordinates;
}

function getTrailTimestamps() {
    return trailTimestamps;
}

function getTrailVelocities() {
    if (trailVelocities.length === 0) {
        calculateVelocities();
    }
    return trailVelocities;
}

function getTrailDistances() {
    return trailDistances;
}

function getTrailPointData() {
    return trailPointData;
}

function getStartTime() {
    return trailTimestamps.length > 0 ? trailTimestamps[0] : Date.now();
}

function getEndTime() {
    return trailTimestamps.length > 0 ? trailTimestamps[trailTimestamps.length - 1] : Date.now();
}

function getTotalDuration() {
    return getEndTime() - getStartTime();
}

function getTrailLength() {
    const coordinates = getTrailCoordinates();
    let length = 0;
    for (let i = 1; i < coordinates.length; i++) {
        const from = coordinates[i - 1];
        const to = coordinates[i];
        length += turf.distance(turf.point(from), turf.point(to));
    }
    return length;
}

function getVelocityAtProgress(progress) {
    const velocities = getTrailVelocities();
    const index = Math.floor(progress * (velocities.length - 1));
    return velocities[Math.min(index, velocities.length - 1)] || 0;
}

function updateTrailProgress(progress) {
    const map = getMap();
    const coordinates = getTrailCoordinates();
    const endIndex = Math.floor(progress * coordinates.length);
    
    const activeCoordinates = coordinates.slice(0, endIndex + 1);
    
    const activeTrailData = {
        type: 'FeatureCollection',
        features: [{
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'LineString',
                coordinates: activeCoordinates
            }
        }]
    };
    
    if (map.getSource('trail-active-source')) {
        map.getSource('trail-active-source').setData(activeTrailData);
    } else {
        map.addSource('trail-active-source', {
            type: 'geojson',
            data: activeTrailData
        });
        
        map.addLayer({
            id: 'trail-active-line',
            type: 'line',
            source: 'trail-active-source',
            paint: {
                'line-color': '#fbbf24',
                'line-width': [
                    'interpolate',
                    ['exponential', 2],
                    ['zoom'],
                    10, 3,
                    14, 8,
                    18, 32
                ],
                'line-opacity': 1
            }
        }, 'trail-velocity-line');
    }
    
    updateInfoDisplay(progress);
}

function updateInfoDisplay(progress) {
    const coordinates = getTrailCoordinates();
    const velocities = getTrailVelocities();
    const distances = getTrailDistances();
    
    const index = Math.floor(progress * (coordinates.length - 1));
    const coord = coordinates[Math.min(index, coordinates.length - 1)];
    
    if (coord) {
        document.getElementById('lng').textContent = coord[0].toFixed(6);
        document.getElementById('lat').textContent = coord[1].toFixed(6);
        document.getElementById('alt').textContent = Math.round(coord[2]);
        document.getElementById('speed').textContent = velocities[index]?.toFixed(1) || '0';
        document.getElementById('distance').textContent = distances[index]?.toFixed(2) || '0';
    }
}

function toggleTrailLayer(visible) {
    const map = getMap();
    if (map.getLayer('trail-velocity-line')) {
        map.setLayoutProperty('trail-velocity-line', 'visibility', visible ? 'visible' : 'none');
    }
    if (map.getLayer('trail-glow')) {
        map.setLayoutProperty('trail-glow', 'visibility', visible ? 'visible' : 'none');
    }
}

function updateTrailData(newCoordinates, newTimestamps) {
    trailData.features[0].geometry.coordinates = newCoordinates;
    trailTimestamps = newTimestamps;
    
    calculateVelocities();
    
    trailPointData = [];
    for (let i = 0; i < newCoordinates.length; i++) {
        trailPointData.push({
            coordinates: newCoordinates[i],
            timestamp: newTimestamps[i],
            velocity: trailVelocities[i],
            distance: trailDistances[i]
        });
    }
    
    const map = getMap();
    
    if (map.getSource('trail-source')) {
        map.getSource('trail-source').setData(trailData);
    }
    
    if (map.getSource('trail-velocity-source')) {
        map.getSource('trail-velocity-source').setData(createVelocityGradientLine());
    }
}