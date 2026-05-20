function createHeatmapData() {
    const coordinates = getTrailCoordinates();
    const features = [];
    
    for (let i = 0; i < coordinates.length; i++) {
        const coord = coordinates[i];
        features.push({
            type: 'Feature',
            properties: {
                density: calculatePointDensity(i, coordinates),
                index: i
            },
            geometry: {
                type: 'Point',
                coordinates: [coord[0], coord[1]]
            }
        });
    }
    
    return {
        type: 'FeatureCollection',
        features: features
    };
}

function calculatePointDensity(index, coordinates, radius = 5) {
    let density = 0;
    const point = coordinates[index];
    
    const start = Math.max(0, index - radius);
    const end = Math.min(coordinates.length - 1, index + radius);
    
    for (let i = start; i <= end; i++) {
        const other = coordinates[i];
        const distance = turf.distance(turf.point(point), turf.point(other));
        if (distance < 0.01) {
            density += 1 - (distance / 0.01);
        }
    }
    
    return density;
}

function initHeatmap() {
    const map = getMap();
    
    if (!map.getSource('heatmap-source')) {
        map.addSource('heatmap-source', {
            type: 'geojson',
            data: createHeatmapData()
        });
    }
    
    if (!map.getLayer('trail-heatmap')) {
        map.addLayer({
            id: 'trail-heatmap',
            type: 'heatmap',
            source: 'heatmap-source',
            maxzoom: 18,
            paint: {
                'heatmap-weight': [
                    'interpolate',
                    ['linear'],
                    ['get', 'density'],
                    0, 0,
                    10, 1
                ],
                'heatmap-intensity': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    10, 1,
                    18, 3
                ],
                'heatmap-color': [
                    'interpolate',
                    ['linear'],
                    ['heatmap-density'],
                    0, 'rgba(0, 0, 255, 0)',
                    0.2, 'rgba(0, 255, 255, 0.5)',
                    0.4, 'rgba(0, 255, 0, 0.6)',
                    0.6, 'rgba(255, 255, 0, 0.7)',
                    0.8, 'rgba(255, 128, 0, 0.8)',
                    1, 'rgba(255, 0, 0, 0.9)'
                ],
                'heatmap-radius': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    10, 5,
                    14, 15,
                    18, 30
                ],
                'heatmap-opacity': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    10, 0.6,
                    14, 0.7,
                    18, 0.8
                ]
            }
        }, 'trail-glow');
    }
}

function updateHeatmap() {
    const map = getMap();
    if (map.getSource('heatmap-source')) {
        map.getSource('heatmap-source').setData(createHeatmapData());
    }
}

function toggleHeatmapLayer(visible) {
    const map = getMap();
    if (map.getLayer('trail-heatmap')) {
        map.setLayoutProperty('trail-heatmap', 'visibility', visible ? 'visible' : 'none');
    }
}

function initHeatmapControls() {
    const heatmapToggle = document.getElementById('heatmap-toggle');
    const trailToggle = document.getElementById('trail-toggle');
    
    if (heatmapToggle) {
        heatmapToggle.addEventListener('change', function() {
            toggleHeatmapLayer(this.checked);
        });
    }
    
    if (trailToggle) {
        trailToggle.addEventListener('change', function() {
            toggleTrailLayer(this.checked);
        });
    }
}