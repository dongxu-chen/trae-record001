import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import * as L from 'leaflet';

function MapController({ bounds }) {
  const map = useMap();
  
  useEffect(() => {
    if (bounds) {
      const leafletBounds = L.latLngBounds(
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      );
      map.fitBounds(leafletBounds, { padding: [50, 50] });
    }
  }, [bounds, map]);

  return null;
}

function MapComponent({ contours, bounds, settings }) {
  const geoJsonRef = useRef(null);

  const getContourColor = (elevation) => {
    const colors = [
      { max: 0, color: '#1a9850' },
      { max: 200, color: '#66bd63' },
      { max: 500, color: '#a6d96a' },
      { max: 1000, color: '#d9ef8b' },
      { max: 1500, color: '#fee08b' },
      { max: 2000, color: '#fdae61' },
      { max: 2500, color: '#f46d43' },
      { max: 3000, color: '#d73027' },
      { max: Infinity, color: '#a50026' }
    ];
    
    for (const range of colors) {
      if (elevation <= range.max) {
        return range.color;
      }
    }
    return '#a50026';
  };

  const styleContour = (feature) => {
    const elevation = feature?.properties?.elevation || 0;
    const isMajor = elevation % (settings.interval * 5) === 0;
    
    return {
      color: getContourColor(elevation),
      weight: isMajor ? 2 : 1,
      opacity: 0.8
    };
  };

  const calculateLabelPositions = (coords, interval = 5) => {
    const positions = [];
    const step = Math.max(interval, Math.floor(coords.length / 4));
    
    for (let i = step; i < coords.length - step; i += step) {
      const startIdx = Math.max(0, i - 2);
      const endIdx = Math.min(coords.length - 1, i + 2);
      const start = coords[startIdx];
      const end = coords[endIdx];
      const mid = coords[i];
      
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      let angle = Math.atan2(dy, dx) * (180 / Math.PI);
      
      if (angle > 90) angle -= 180;
      if (angle < -90) angle += 180;
      
      positions.push({ point: mid, angle });
    }
    
    return positions;
  };

  const onEachFeature = (feature, layer) => {
    const elevation = feature?.properties?.elevation;
    const lineAngle = feature?.properties?.angle || 0;
    const gradient = feature?.properties?.gradient;
    const adaptiveSmoothing = feature?.properties?.adaptiveSmoothing;
    
    if (elevation !== undefined) {
      let popupContent = `<strong>高程: ${elevation} m</strong><br/>`;
      popupContent += `线段角度: ${lineAngle.toFixed(1)}°<br/>`;
      popupContent += `点数: ${feature.properties.pointCount || feature.geometry.coordinates.length}`;
      if (gradient !== undefined) {
        popupContent += `<br/>地形梯度: ${gradient.toFixed(2)}`;
      }
      if (adaptiveSmoothing !== undefined) {
        popupContent += `<br/>平滑级别: ${adaptiveSmoothing}`;
      }
      layer.bindPopup(popupContent);
      
      if (settings.enableLabels) {
        const isLabelLine = elevation % (settings.interval * settings.labelInterval) === 0;
        if (isLabelLine && feature.geometry.type === 'LineString') {
          const coords = feature.geometry.coordinates;
          if (coords.length > 4) {
            const labelPositions = calculateLabelPositions(coords, settings.labelInterval * 3);
            
            labelPositions.forEach(({ point, angle }, idx) => {
              const displayAngle = feature.properties.angle !== undefined ? feature.properties.angle : angle;
              
              const label = L.marker([point[1], point[0]], {
                icon: L.divIcon({
                  className: 'contour-label',
                  html: `
                    <div style="
                      background: white;
                      padding: 2px 8px;
                      border-radius: 3px;
                      font-size: 10px;
                      font-weight: 500;
                      white-space: nowrap;
                      box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                      transform: rotate(${displayAngle}deg);
                      transform-origin: center center;
                      color: #333;
                      border: 1px solid rgba(0,0,0,0.1);
                    ">
                      ${elevation}m
                    </div>
                  `,
                  iconSize: [0, 0],
                  iconAnchor: [0, 0]
                }),
                interactive: false
              });
              layer.addLayer(label);
            });
          }
        }
      }
    }
  };

  return (
    <MapContainer
      center={[35, 105]}
      zoom={4}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {contours && (
        <GeoJSON
          ref={geoJsonRef}
          data={contours}
          style={styleContour}
          onEachFeature={onEachFeature}
        />
      )}
      <MapController bounds={bounds} />
    </MapContainer>
  );
}

export default MapComponent;
