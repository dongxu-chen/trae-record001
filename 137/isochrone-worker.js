importScripts('https://unpkg.com/@turf/turf@6.5.0/turf.min.js');

const TOLERANCE = 1e-6;

function approxEqual(a, b, tolerance = TOLERANCE) {
    return Math.abs(a - b) < tolerance;
}

function approxEqualCoords(coord1, coord2, tolerance = TOLERANCE) {
    return approxEqual(coord1[0], coord2[0], tolerance) && 
           approxEqual(coord1[1], coord2[1], tolerance);
}

self.onmessage = function(e) {
    const { center, timeMinutes, speedKmh } = e.data;
    
    try {
        const distanceKm = speedKmh * (timeMinutes / 60);
        const distanceMeters = distanceKm * 1000;

        const centerPoint = turf.point([center.lng, center.lat]);
        
        const steps = 64;
        const polygonCoords = [];
        
        for (let i = 0; i < steps; i++) {
            const bearing = (i / steps) * 360;
            const destination = turf.destination(centerPoint, distanceMeters, bearing, {
                units: 'meters'
            });
            polygonCoords.push(destination.geometry.coordinates);
        }
        
        polygonCoords.push(polygonCoords[0]);
        
        const isochrone = turf.polygon([polygonCoords]);
        const simplified = turf.simplify(isochrone, {
            tolerance: 0.0001,
            highQuality: true
        });
        
        const area = turf.area(simplified);
        
        const coords = simplified.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
        
        self.postMessage({
            success: true,
            coords: coords,
            distanceKm: distanceKm,
            area: area,
            center: center
        });
        
    } catch (error) {
        self.postMessage({
            success: false,
            error: error.message
        });
    }
};
