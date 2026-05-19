let movingMarker;
let markerElement;

function createMarkerElement() {
    const el = document.createElement('div');
    el.className = 'moving-marker';
    el.style.width = '24px';
    el.style.height = '24px';
    el.style.borderRadius = '50%';
    el.style.background = 'radial-gradient(circle, #fbbf24 0%, #f59e0b 50%, #d97706 100%)';
    el.style.border = '3px solid white';
    el.style.boxShadow = '0 0 0 4px rgba(251, 191, 36, 0.3), 0 4px 12px rgba(0, 0, 0, 0.3)';
    el.style.cursor = 'pointer';
    el.style.zIndex = '1000';
    el.style.transition = 'transform 0.1s ease';
    
    const pulse = document.createElement('div');
    pulse.style.position = 'absolute';
    pulse.style.top = '50%';
    pulse.style.left = '50%';
    pulse.style.transform = 'translate(-50%, -50%)';
    pulse.style.width = '40px';
    pulse.style.height = '40px';
    pulse.style.borderRadius = '50%';
    pulse.style.background = 'rgba(251, 191, 36, 0.3)';
    pulse.style.animation = 'pulse 2s infinite';
    el.appendChild(pulse);
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0% {
                transform: translate(-50%, -50%) scale(0.8);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.5);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    return el;
}

function initMarker() {
    const map = getMap();
    const coordinates = getTrailCoordinates();
    
    if (coordinates.length === 0) return;
    
    markerElement = createMarkerElement();
    
    const startCoord = coordinates[0];
    movingMarker = new mapboxgl.Marker({
        element: markerElement,
        anchor: 'center'
    })
    .setLngLat([startCoord[0], startCoord[1]])
    .addTo(map);
    
    initMarker3D();
    initTrailTail();
}

function initMarker3D() {
    const map = getMap();
    
    if (!map.getSource('marker-3d-source')) {
        map.addSource('marker-3d-source', {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [0, 0, 0]
                }
            }
        });
    }
    
    if (!map.getLayer('marker-3d-cylinder')) {
        map.addLayer({
            id: 'marker-3d-cylinder',
            type: 'fill-extrusion',
            source: 'marker-3d-source',
            paint: {
                'fill-extrusion-color': '#fbbf24',
                'fill-extrusion-height': 50,
                'fill-extrusion-base': 0,
                'fill-extrusion-opacity': 0.8
            }
        });
    }
}

function initTrailTail() {
    const map = getMap();
    
    if (!map.getSource('trail-tail-source')) {
        map.addSource('trail-tail-source', {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: []
                }
            }
        });
    }
    
    if (!map.getLayer('trail-tail-line')) {
        map.addLayer({
            id: 'trail-tail-line',
            type: 'line',
            source: 'trail-tail-source',
            paint: {
                'line-color': [
                    'interpolate',
                    ['linear'],
                    ['line-progress'],
                    0, 'rgba(251, 191, 36, 0)',
                    1, 'rgba(251, 191, 36, 1)'
                ],
                'line-width': [
                    'interpolate',
                    ['exponential', 2],
                    ['zoom'],
                    10, ['*', ['line-progress'], 2],
                    14, ['*', ['line-progress'], 8],
                    18, ['*', ['line-progress'], 32]
                ],
                'line-opacity': 0.8
            }
        });
    }
}

function updateMarkerPosition(progress) {
    const map = getMap();
    const coordinates = getTrailCoordinates();
    
    if (!movingMarker || coordinates.length === 0) return;
    
    const totalIndex = coordinates.length - 1;
    const exactIndex = progress * totalIndex;
    const floorIndex = Math.floor(exactIndex);
    const ceilIndex = Math.ceil(exactIndex);
    const fraction = exactIndex - floorIndex;
    
    let currentCoord;
    if (floorIndex === ceilIndex) {
        currentCoord = coordinates[floorIndex];
    } else {
        const from = coordinates[floorIndex];
        const to = coordinates[ceilIndex];
        currentCoord = [
            from[0] + (to[0] - from[0]) * fraction,
            from[1] + (to[1] - from[1]) * fraction,
            from[2] + (to[2] - from[2]) * fraction
        ];
    }
    
    movingMarker.setLngLat([currentCoord[0], currentCoord[1]]);
    updateMarker3DPosition(currentCoord);
    updateTrailTail(exactIndex, coordinates);
    updateInfoDisplay(currentCoord);
    
    if (progress > 0.1) {
        const cameraProgress = progress - 0.1;
        const cameraIndex = Math.floor(cameraProgress * totalIndex);
        const cameraCoord = coordinates[Math.min(cameraIndex, totalIndex)];
        
        map.easeTo({
            center: [currentCoord[0], currentCoord[1]],
            duration: 100,
            essential: true
        });
    }
}

function updateMarker3DPosition(coord) {
    const map = getMap();
    
    if (map.getSource('marker-3d-source')) {
        const circle = turf.circle([coord[0], coord[1]], 0.01, {
            steps: 32,
            units: 'kilometers'
        });
        
        map.getSource('marker-3d-source').setData(circle);
        map.setPaintProperty('marker-3d-cylinder', 'fill-extrusion-base', coord[2]);
        map.setPaintProperty('marker-3d-cylinder', 'fill-extrusion-height', 20);
    }
}

function updateTrailTail(currentIndex, coordinates) {
    const map = getMap();
    const tailLength = 30;
    const startIndex = Math.max(0, Math.floor(currentIndex) - tailLength);
    const tailCoordinates = coordinates.slice(startIndex, Math.floor(currentIndex) + 1);
    
    if (map.getSource('trail-tail-source')) {
        map.getSource('trail-tail-source').setData({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: tailCoordinates
            }
        });
    }
}

function updateInfoDisplay(coord) {
    document.getElementById('lng').textContent = coord[0].toFixed(6);
    document.getElementById('lat').textContent = coord[1].toFixed(6);
    document.getElementById('alt').textContent = Math.round(coord[2]);
}

function resetMarker() {
    const coordinates = getTrailCoordinates();
    if (movingMarker && coordinates.length > 0) {
        const startCoord = coordinates[0];
        movingMarker.setLngLat([startCoord[0], startCoord[1]]);
        updateMarker3DPosition(startCoord);
        updateInfoDisplay(startCoord);
    }
}
