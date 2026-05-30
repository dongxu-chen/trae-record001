import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as L from 'leaflet';

function AnimationComponent({ contours, bounds, settings }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const animationRef = useRef(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [animProgress, setAnimProgress] = useState(0);
  const [animSpeed, setAnimSpeed] = useState(2);
  const [animMode, setAnimMode] = useState('sequential');

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
      if (elevation <= range.max) return range.color;
    }
    return '#a50026';
  };

  const initMap = useCallback(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [39.75, 116.25],
      zoom: 10,
      zoomControl: false,
      attributionControl: false
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    if (bounds) {
      map.fitBounds(L.latLngBounds(
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      ), { padding: [20, 20] });
    }

    mapRef.current = map;
  }, [bounds]);

  useEffect(() => {
    initMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [initMap]);

  const clearAnimation = useCallback(() => {
    if (animationRef.current) {
      if (animationRef.current.timeoutIds) {
        animationRef.current.timeoutIds.forEach(id => clearTimeout(id));
      }
      if (animationRef.current.animFrameId) {
        cancelAnimationFrame(animationRef.current.animFrameId);
      }
      if (animationRef.current.layers) {
        animationRef.current.layers.forEach(layer => {
          if (mapRef.current) mapRef.current.removeLayer(layer);
        });
      }
    }
    animationRef.current = { layers: [], timeoutIds: [], animFrameId: null };
  }, []);

  const startAnimation = useCallback(() => {
    if (!contours || !contours.features || !mapRef.current) return;

    clearAnimation();
    setIsAnimating(true);
    setAnimProgress(0);

    const map = mapRef.current;
    const features = contours.features;
    const layers = [];
    const timeoutIds = [];

    animationRef.current = { layers, timeoutIds, animFrameId: null };

    const totalFeatures = features.length;

    if (animMode === 'sequential') {
      features.forEach((feature, featureIdx) => {
        const tid = setTimeout(() => {
          if (!mapRef.current) return;

          const elevation = feature.properties.elevation;
          const isMajor = elevation % (settings.interval * 5) === 0;
          const coords = feature.geometry.coordinates;
          const color = getContourColor(elevation);

          if (animMode === 'sequential') {
            const drawPoints = [];
            const drawSteps = Math.max(1, Math.ceil(coords.length / animSpeed));
            const stepSize = Math.max(1, Math.floor(coords.length / drawSteps));
            let currentStep = 0;

            const drawNextSegment = () => {
              if (!mapRef.current) return;

              const endIdx = Math.min(currentStep + stepSize, coords.length);
              const segment = coords.slice(0, endIdx);

              if (drawPoints.length > 0) {
                map.removeLayer(drawPoints[drawPoints.length - 1]);
              }

              const polyline = L.polyline(
                segment.map(c => [c[1], c[0]]),
                {
                  color: color,
                  weight: isMajor ? 2.5 : 1.2,
                  opacity: 0.9,
                  lineCap: 'round',
                  lineJoin: 'round'
                }
              ).addTo(map);

              drawPoints.push(polyline);
              layers.push(polyline);
              currentStep = endIdx;

              const progress = ((featureIdx + endIdx / coords.length) / totalFeatures) * 100;
              setAnimProgress(Math.min(100, progress));

              if (currentStep < coords.length) {
                const aid = requestAnimationFrame(drawNextSegment);
                animationRef.current.animFrameId = aid;
              } else if (isMajor && settings.enableLabels) {
                const midIdx = Math.floor(coords.length / 2);
                const mid = coords[midIdx];
                L.marker([mid[1], mid[0]], {
                  icon: L.divIcon({
                    className: 'contour-label',
                    html: `<div style="background:white;padding:1px 6px;border-radius:2px;font-size:10px;font-weight:600;color:${color};box-shadow:0 1px 2px rgba(0,0,0,0.3);">${elevation}m</div>`,
                    iconSize: [0, 0]
                  }),
                  interactive: false
                }).addTo(map);
              }
            };

            drawNextSegment();
          }
        }, featureIdx * (200 / animSpeed));

        timeoutIds.push(tid);
      });

      const endTid = setTimeout(() => {
        setIsAnimating(false);
        setAnimProgress(100);
      }, totalFeatures * (200 / animSpeed) + 500);
      timeoutIds.push(endTid);

    } else if (animMode === 'elevation') {
      const byElevation = {};
      features.forEach(f => {
        const e = f.properties.elevation;
        if (!byElevation[e]) byElevation[e] = [];
        byElevation[e].push(f);
      });

      const elevations = Object.keys(byElevation).map(Number).sort((a, b) => a - b);
      let globalDelay = 0;

      elevations.forEach((elev, elevIdx) => {
        const featuresAtElev = byElevation[elev];
        const tid = setTimeout(() => {
          if (!mapRef.current) return;

          featuresAtElev.forEach(feature => {
            const isMajor = elev % (settings.interval * 5) === 0;
            const color = getContourColor(elev);

            const polyline = L.polyline(
              feature.geometry.coordinates.map(c => [c[1], c[0]]),
              {
                color: color,
                weight: isMajor ? 2.5 : 1.2,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round'
              }
            ).addTo(map);

            layers.push(polyline);
          });

          setAnimProgress(Math.round(((elevIdx + 1) / elevations.length) * 100));
        }, globalDelay);

        timeoutIds.push(tid);
        globalDelay += 300 / animSpeed;
      });

      const endTid = setTimeout(() => {
        setIsAnimating(false);
        setAnimProgress(100);
      }, globalDelay + 500);
      timeoutIds.push(endTid);

    } else if (animMode === 'radial') {
      const centerLat = bounds ? (bounds.north + bounds.south) / 2 : 39.75;
      const centerLon = bounds ? (bounds.east + bounds.west) / 2 : 116.25;

      const sorted = [...features].sort((a, b) => {
        const ca = a.geometry.coordinates[Math.floor(a.geometry.coordinates.length / 2)];
        const cb = b.geometry.coordinates[Math.floor(b.geometry.coordinates.length / 2)];
        const da = Math.sqrt(Math.pow(ca[0] - centerLon, 2) + Math.pow(ca[1] - centerLat, 2));
        const db = Math.sqrt(Math.pow(cb[0] - centerLon, 2) + Math.pow(cb[1] - centerLat, 2));
        return da - db;
      });

      sorted.forEach((feature, idx) => {
        const tid = setTimeout(() => {
          if (!mapRef.current) return;

          const elevation = feature.properties.elevation;
          const isMajor = elevation % (settings.interval * 5) === 0;
          const color = getContourColor(elevation);

          const polyline = L.polyline(
            feature.geometry.coordinates.map(c => [c[1], c[0]]),
            {
              color: color,
              weight: isMajor ? 2.5 : 1.2,
              opacity: 0.9
            }
          ).addTo(map);

          layers.push(polyline);
          setAnimProgress(Math.round(((idx + 1) / sorted.length) * 100));
        }, idx * (150 / animSpeed));

        timeoutIds.push(tid);
      });

      const endTid = setTimeout(() => {
        setIsAnimating(false);
        setAnimProgress(100);
      }, sorted.length * (150 / animSpeed) + 500);
      timeoutIds.push(endTid);
    }
  }, [contours, settings, animMode, animSpeed, clearAnimation]);

  const stopAnimation = useCallback(() => {
    clearAnimation();
    setIsAnimating(false);
  }, [clearAnimation]);

  useEffect(() => {
    if (mapRef.current && bounds) {
      mapRef.current.fitBounds(L.latLngBounds(
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      ), { padding: [20, 20] });
    }
  }, [bounds]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="animation-controls">
        <select
          value={animMode}
          onChange={(e) => setAnimMode(e.target.value)}
          className="anim-select"
          disabled={isAnimating}
        >
          <option value="sequential">逐步绘制</option>
          <option value="elevation">按高程层</option>
          <option value="radial">从中心向外</option>
        </select>
        <label style={{ fontSize: '12px', color: '#666', display: 'flex', alignItems: 'center', gap: '4px' }}>
          速度:
          <input
            type="range"
            min="0.5"
            max="5"
            step="0.5"
            value={animSpeed}
            onChange={(e) => setAnimSpeed(Number(e.target.value))}
            style={{ width: '80px' }}
          />
          ×{animSpeed.toFixed(1)}
        </label>
        {!isAnimating ? (
          <button className="btn-anim" onClick={startAnimation} disabled={!contours}>
            ▶ 播放
          </button>
        ) : (
          <button className="btn-anim stop" onClick={stopAnimation}>
            ⏹ 停止
          </button>
        )}
        {animProgress > 0 && (
          <div className="anim-progress">
            <div className="anim-progress-bar" style={{ width: `${animProgress}%` }} />
            <span className="anim-progress-text">{Math.round(animProgress)}%</span>
          </div>
        )}
      </div>
      <div ref={containerRef} style={{ flex: 1, minHeight: 0 }} />
    </div>
  );
}

export default AnimationComponent;
