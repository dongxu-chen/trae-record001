import React, { useRef, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';

const createCustomIcon = (color, label, size = 32) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background: ${color};
        color: white;
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: ${size > 32 ? '14px' : '12px'};
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        border: 2px solid white;
        z-index: 1000;
      ">${label}</div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2]
  });
};

const createVehicleIcon = () => {
  return L.divIcon({
    className: 'vehicle-marker',
    html: `
      <div style="
        background: linear-gradient(135deg, #f39c12, #e67e22);
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        box-shadow: 0 4px 12px rgba(243, 156, 18, 0.4);
        border: 3px solid white;
        z-index: 1001;
      ">🚚</div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18]
  });
};

const originIcon = createCustomIcon('#27ae60', '起', 36);
const destinationIcon = createCustomIcon('#e74c3c', '终', 36);
const waypointIcons = [
  createCustomIcon('#3498db', '1'),
  createCustomIcon('#9b59b6', '2'),
  createCustomIcon('#f39c12', '3'),
  createCustomIcon('#1abc9c', '4'),
  createCustomIcon('#e67e22', '5'),
  createCustomIcon('#34495e', '6'),
  createCustomIcon('#16a085', '7'),
  createCustomIcon('#8e44ad', '8'),
  createCustomIcon('#c0392b', '9'),
  createCustomIcon('#2c3e50', '10'),
];

function ChangeView({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center && zoom) {
      map.flyTo(center, zoom, { duration: 0.8 });
    }
  }, [center, zoom, map]);
  return null;
}

function MapView({ routeData, waypoints, loading, playbackPosition, isPlaying, onPlayback, routeColor }) {
  const mapRef = useRef(null);
  const vehicleIcon = useRef(null);

  if (!vehicleIcon.current) {
    vehicleIcon.current = createVehicleIcon();
  }

  const getCenter = () => {
    if (routeData) {
      const coords = routeData.pathCoordinates;
      if (coords && coords.length > 0) {
        const lats = coords.map(c => c[0]);
        const lngs = coords.map(c => c[1]);
        return [(Math.max(...lats) + Math.min(...lats)) / 2, (Math.max(...lngs) + Math.min(...lngs)) / 2];
      }
    }
    return [35.8617, 104.1954];
  };

  const getZoom = () => {
    if (routeData) {
      const coords = routeData.pathCoordinates;
      if (coords && coords.length > 0) {
        const lats = coords.map(c => c[0]);
        const lngs = coords.map(c => c[1]);
        const latDiff = Math.max(...lats) - Math.min(...lats);
        const lngDiff = Math.max(...lngs) - Math.min(...lngs);
        const maxDiff = Math.max(latDiff, lngDiff);
        if (maxDiff > 20) return 4;
        if (maxDiff > 10) return 5;
        if (maxDiff > 5) return 6;
        if (maxDiff > 2) return 7;
        if (maxDiff > 1) return 8;
        return 10;
      }
    }
    return 4;
  };

  const center = getCenter();
  const zoom = getZoom();

  const segmentColors = [routeColor || '#2a5298', '#3498db', '#9b59b6', '#f39c12', '#1abc9c'];

  const progress = playbackPosition && routeData?.pathCoordinates?.length > 0
    ? (playbackPosition.index / playbackPosition.total) * 100
    : 0;

  return (
    <div className="map-container">
      {loading && (
        <div className="map-loading">
          <span className="loading"></span>
          正在计算最优路线...
        </div>
      )}

      {routeData && !loading && (
        <div className="playback-controls">
          <button 
            className="playback-btn"
            onClick={() => onPlayback(!isPlaying)}
            disabled={!routeData.pathCoordinates || routeData.pathCoordinates.length === 0}
          >
            {isPlaying ? '⏸' : '▶'}
          </button>
          <button 
            className="playback-btn"
            onClick={() => {
              onPlayback(false);
              if (mapRef.current) {
                mapRef.current.flyTo(center, zoom, { duration: 0.5 });
              }
            }}
            disabled={!routeData.pathCoordinates || routeData.pathCoordinates.length === 0}
          >
            ⌂
          </button>
          <div className="playback-progress">
            <div className="progress-bar">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${progress}%` }}
              />
            </div>
            <span>
              {playbackPosition 
                ? `${Math.floor(progress)}%` 
                : '0%'
              }
            </span>
          </div>
        </div>
      )}

      <MapContainer
        ref={mapRef}
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
      >
        <ChangeView center={center} zoom={zoom} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {!routeData && !loading && (
          <div className="map-placeholder">
            <div className="map-placeholder-icon">🗺️</div>
            <div className="map-placeholder-text">输入起点和终点开始规划路线</div>
            <div className="map-placeholder-hint">支持最多10个途经点，可拖拽调整顺序</div>
          </div>
        )}

        {routeData && (
          <>
            {routeData.segments && routeData.segments.map((segment, idx) => {
              const segmentCoords = [];
              const start = segment.from;
              const end = segment.to;
              
              if (routeData.pathCoordinates && routeData.pathCoordinates.length > 0) {
                const allCoords = routeData.pathCoordinates;
                let minDistStart = Infinity;
                let minDistEnd = Infinity;
                let startIdx = 0;
                let endIdx = allCoords.length - 1;

                allCoords.forEach((coord, i) => {
                  const distStart = Math.sqrt(
                    Math.pow(coord[0] - start.lat, 2) + Math.pow(coord[1] - start.lng, 2)
                  );
                  const distEnd = Math.sqrt(
                    Math.pow(coord[0] - end.lat, 2) + Math.pow(coord[1] - end.lng, 2)
                  );
                  if (distStart < minDistStart) {
                    minDistStart = distStart;
                    startIdx = i;
                  }
                  if (distEnd < minDistEnd) {
                    minDistEnd = distEnd;
                    endIdx = i;
                  }
                });

                if (startIdx < endIdx) {
                  for (let i = startIdx; i <= endIdx; i++) {
                    segmentCoords.push(allCoords[i]);
                  }
                } else {
                  segmentCoords.push([start.lat, start.lng], [end.lat, end.lng]);
                }
              } else {
                segmentCoords.push([start.lat, start.lng], [end.lat, end.lng]);
              }

              return (
                <Polyline
                  key={`segment-${idx}`}
                  positions={segmentCoords}
                  color={segmentColors[idx % segmentColors.length]}
                  weight={6}
                  opacity={0.8}
                  smoothFactor={1}
                >
                  <Popup>
                    <strong>路段 {idx + 1}</strong><br />
                    里程: {(segment.distance / 1000).toFixed(2)} 公里<br />
                    预计时间: {Math.floor(segment.duration / 60)} 分钟
                  </Popup>
                </Polyline>
              );
            })}

            {routeData.pathCoordinates && routeData.pathCoordinates.length > 0 && (
              <Polyline
                positions={routeData.pathCoordinates}
                color={routeColor || '#2a5298'}
                weight={4}
                opacity={0.3}
                dashArray="10, 10"
              />
            )}

            {playbackPosition && (
              <Marker
                position={[playbackPosition.lat, playbackPosition.lng]}
                icon={vehicleIcon.current}
              >
                <Popup>
                  <strong>🚚 模拟行驶中</strong><br />
                  进度: {Math.floor(progress)}%
                </Popup>
              </Marker>
            )}

            <Marker
              position={[routeData.origin.lat, routeData.origin.lng]}
              icon={originIcon}
            >
              <Popup>
                <strong>🚩 起点</strong><br />
                经度: {routeData.origin.lng.toFixed(4)}<br />
                纬度: {routeData.origin.lat.toFixed(4)}
              </Popup>
            </Marker>

            {routeData.waypoints && routeData.waypoints.map((wp, idx) => (
              <Marker
                key={`waypoint-${idx}`}
                position={[wp.lat, wp.lng]}
                icon={waypointIcons[idx % waypointIcons.length]}
              >
                <Popup>
                  <strong>📍 途经点 {idx + 1}</strong><br />
                  经度: {wp.lng.toFixed(4)}<br />
                  纬度: {wp.lat.toFixed(4)}
                </Popup>
              </Marker>
            ))}

            <Marker
              position={[routeData.destination.lat, routeData.destination.lng]}
              icon={destinationIcon}
            >
              <Popup>
                <strong>🏁 终点</strong><br />
                经度: {routeData.destination.lng.toFixed(4)}<br />
                纬度: {routeData.destination.lat.toFixed(4)}
              </Popup>
            </Marker>
          </>
        )}
      </MapContainer>
    </div>
  );
}

export default MapView;
