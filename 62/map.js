let map;
let mapLoaded = false;
let customLayersInitialized = false;

const MAPBOX_TOKEN = 'xxx';

function initMap() {
    mapboxgl.accessToken = MAPBOX_TOKEN;
    
    map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/satellite-streets-v12',
        center: [116.397, 39.908],
        zoom: 14,
        pitch: 60,
        bearing: 0,
        antialias: true
    });

    map.addControl(new mapboxgl.NavigationControl({
        visualizePitch: true
    }), 'top-left');

    map.addControl(new mapboxgl.FullscreenControl(), 'top-left');

    map.on('load', function() {
        mapLoaded = true;
        
        map.setFog({
            range: [0.8, 8],
            color: '#dc9f39',
            'high-color': '#1898c9',
            'space-color': '#020b13',
            'horizon-blend': 0.5
        });

        initializeCustomLayers();
        initAnimation();
    });

    map.on('style.load', function() {
        if (mapLoaded) {
            customLayersInitialized = false;
            setTimeout(() => {
                if (mapLoaded && map.isStyleLoaded()) {
                    initializeCustomLayers();
                }
            }, 100);
        }
    });

    map.on('error', function(e) {
        console.error('Map error:', e.error);
    });
}

function initializeCustomLayers() {
    if (customLayersInitialized) return;
    
    try {
        initTrail();
        initMarker();
        initHeatmap();
        customLayersInitialized = true;
        console.log('Custom layers initialized successfully');
    } catch (error) {
        console.error('Failed to initialize custom layers:', error);
        customLayersInitialized = false;
    }
}

function getMap() {
    return map;
}

function isMapLoaded() {
    return mapLoaded;
}
