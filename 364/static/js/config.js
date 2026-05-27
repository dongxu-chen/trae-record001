const API_BASE = 'http://localhost:5000/api';

const CONFIG = {
    map: {
        center: [39.9042, 116.4124],
        zoom: 15,
        minZoom: 13,
        maxZoom: 18
    },
    simulation: {
        defaultSteps: 100,
        defaultGenRate: 0.3,
        defaultMaxSpeed: 14,
        updateInterval: 500
    },
    visualization: {
        heatmapRadius: 25,
        heatmapBlur: 15,
        heatmapMax: 1.0,
        vehicleMarkerSize: 8
    },
    colors: {
        freeflow: '#2ecc71',
        moderate: '#f39c12',
        heavy: '#e67e22',
        congested: '#e74c3c',
        road: '#3498db',
        node: '#9b59b6'
    }
};

function getSpeedColor(speed, maxSpeed = 14) {
    const ratio = speed / maxSpeed;
    if (ratio > 0.7) return CONFIG.colors.freeflow;
    if (ratio > 0.4) return CONFIG.colors.moderate;
    if (ratio > 0.2) return CONFIG.colors.heavy;
    return CONFIG.colors.congested;
}

function getDensityColor(density) {
    if (density < 0.3) return CONFIG.colors.freeflow;
    if (density < 0.6) return CONFIG.colors.moderate;
    if (density < 0.8) return CONFIG.colors.heavy;
    return CONFIG.colors.congested;
}

function getDensityLevel(density) {
    if (density < 0.3) return { level: '畅通', class: '' };
    if (density < 0.6) return { level: '缓行', class: 'slow' };
    if (density < 0.8) return { level: '拥堵', class: 'moderate' };
    return { level: '严重拥堵', class: 'congested' };
}

async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    if (data) {
        options.body = JSON.stringify(data);
    }
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        return { status: 'error', message: error.message };
    }
}
