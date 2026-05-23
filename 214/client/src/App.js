import React, { useState, useRef, useCallback, useEffect } from 'react';
import RouteForm from './components/RouteForm';
import MapView from './components/MapView';
import RouteSummary from './components/RouteSummary';
import ShareModal from './components/ShareModal';
import axios from 'axios';
import './App.css';

const DEBOUNCE_DELAY = 800;

const ROUTE_STRATEGIES = {
  time_shortest: { strategy: 10, name: '时间最短', color: '#27ae60' },
  distance_shortest: { strategy: 12, name: '距离最短', color: '#3498db' },
  no_highway: { strategy: 11, name: '避开高速', color: '#e67e22' }
};

function App() {
  const [routeData, setRouteData] = useState(null);
  const [multiRoutes, setMultiRoutes] = useState([]);
  const [selectedRouteKey, setSelectedRouteKey] = useState('time_shortest');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [waypoints, setWaypoints] = useState([]);
  const [usingCache, setUsingCache] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareUrl, setShareUrl] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackPosition, setPlaybackPosition] = useState(null);

  const debounceTimer = useRef(null);
  const lastRouteCache = useRef(null);
  const requestIdRef = useRef(0);
  const playbackTimer = useRef(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const routeId = params.get('r');
    
    if (routeId) {
      loadSharedRoute(routeId);
    }
  }, []);

  const loadSharedRoute = async (id) => {
    try {
      const response = await axios.get(`/api/share/${id}`);
      if (response.data.success) {
        const { origin, destination, waypoints: wp, strategy } = response.data.route;
        
        setLoading(true);
        setError('');
        
        setWaypoints(wp || []);
        setSelectedRouteKey(strategy || 'time_shortest');
        
        const multiResponse = await axios.post('/api/route/multi', {
          origin,
          destination,
          waypoints: wp || []
        });
        
        if (multiResponse.data.success) {
          const routes = multiResponse.data.routes;
          setMultiRoutes(routes);
          
          const selected = routes.find(r => r.key === strategy) || routes.find(r => r.success);
          if (selected && selected.success) {
            setRouteData(selected);
            setUsingCache(false);
          }
        }
      }
    } catch (err) {
      console.error('加载分享路线失败:', err);
      setError('分享链接加载失败，请手动输入路线');
    } finally {
      setLoading(false);
    }
  };

  const calculateRoute = async (origin, destination, wp, showLoading = true) => {
    if (showLoading) {
      setLoading(true);
    }
    setError('');

    const currentRequestId = ++requestIdRef.current;

    try {
      const response = await axios.post('/api/route/multi', {
        origin,
        destination,
        waypoints: wp
      });

      if (currentRequestId !== requestIdRef.current) {
          return;
      }

      if (response.data.success) {
        const routes = response.data.routes;
        setMultiRoutes(routes);
        
        const successfulRoute = routes.find(r => r.success && r.key === selectedRouteKey) 
          || routes.find(r => r.success);
        
        if (successfulRoute) {
          lastRouteCache.current = {
            route: successfulRoute,
            allRoutes: routes,
            origin,
            destination,
            waypoints: wp,
            timestamp: Date.now()
          };
          setRouteData(successfulRoute);
          setSelectedRouteKey(successfulRoute.key);
          setWaypoints(wp);
          setUsingCache(false);
        } else {
          handleRouteError('路线规划失败', origin, destination, wp);
        }
      } else {
        handleRouteError(response.data.error || '路线规划失败', origin, destination, wp);
      }
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) {
        return;
      }
      handleRouteError(err.response?.data?.error || '网络错误，请稍后重试', origin, destination, wp);
    } finally {
      if (currentRequestId === requestIdRef.current && showLoading) {
        setLoading(false);
      }
    }
  };

  const handleRouteError = (errorMessage, origin, destination, wp) => {
    if (lastRouteCache.current && 
        lastRouteCache.current.origin.lng === origin.lng &&
        lastRouteCache.current.origin.lat === origin.lat &&
        lastRouteCache.current.destination.lng === destination.lng &&
        lastRouteCache.current.destination.lat === destination.lat) {
      
      const cacheAge = Date.now() - lastRouteCache.current.timestamp;
      if (cacheAge < 5 * 60 * 1000) {
        setRouteData(lastRouteCache.current.route);
        setMultiRoutes(lastRouteCache.current.allRoutes || []);
        setWaypoints(wp);
        setUsingCache(true);
        setError(`${errorMessage}（已使用5分钟内的缓存路线结果）`);
        return;
      }
    }
    setRouteData(null);
    setMultiRoutes([]);
    setError(errorMessage);
  };

  const debouncedCalculateRoute = useCallback((origin, destination, wp) => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = setTimeout(() => {
      calculateRoute(origin, destination, wp, false);
    }, DEBOUNCE_DELAY);
  }, [selectedRouteKey]);

  const handleWaypointsReorder = (newWaypoints) => {
    setWaypoints(newWaypoints);
    if (routeData) {
      setLoading(true);
      debouncedCalculateRoute(routeData.origin, routeData.destination, newWaypoints);
    }
  };

  const handleManualCalculate = (origin, destination, wp) => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    calculateRoute(origin, destination, wp, true);
  };

  const handleSelectRoute = (routeKey) => {
    const route = multiRoutes.find(r => r.key === routeKey);
    if (route && route.success) {
      setSelectedRouteKey(routeKey);
      setRouteData(route);
      setPlaybackPosition(null);
      setIsPlaying(false);
    }
  };

  const handleGenerateShare = async () => {
    if (!routeData) return;
    
    try {
      const response = await axios.post('/api/share/generate', {
        origin: routeData.origin,
        destination: routeData.destination,
        waypoints: routeData.waypoints,
        strategy: selectedRouteKey
      });
      
      if (response.data.success) {
        setShareUrl(response.data.shortUrl);
        setShowShareModal(true);
      }
    } catch (err) {
      setError('生成分享链接失败');
    }
  };

  const handlePlayback = (isPlaying) => {
    setIsPlaying(isPlaying);
    
    if (!isPlaying) {
      if (playbackTimer.current) {
        clearInterval(playbackTimer.current);
        playbackTimer.current = null;
      }
      return;
    }
    
    if (routeData && routeData.pathCoordinates && routeData.pathCoordinates.length > 0) {
      let currentIndex = 0;
      const coords = routeData.pathCoordinates;
      
      playbackTimer.current = setInterval(() => {
        if (currentIndex < coords.length) {
          setPlaybackPosition({
            lat: coords[currentIndex][0],
            lng: coords[currentIndex][1],
            index: currentIndex,
            total: coords.length
          });
          currentIndex++;
        } else {
          clearInterval(playbackTimer.current);
          playbackTimer.current = null;
          setIsPlaying(false);
        }
      }, 50);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚚 货运路线规划工具</h1>
        <p className="subtitle">基于高德地图API的智能路线规划与可视化</p>
        {routeData && multiRoutes.length > 0 && (
          <div className="route-selector">
            {multiRoutes.map(route => (
              <button
                key={route.key}
                className={`route-tab ${selectedRouteKey === route.key ? 'active' : ''} ${!route.success ? 'disabled' : ''}`}
                onClick={() => route.success && handleSelectRoute(route.key)}
                style={{ borderColor: route.color }}
              >
                <span className="route-tab-color" style={{ background: route.color }}></span>
                {route.name}
                {route.success && (
                  <span className="route-tab-info">
                    {(route.totalDistance / 1000).toFixed(1)}km · {Math.floor(route.totalDuration / 60)}分
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </header>

      <div className="app-container">
        <div className="sidebar">
          <RouteForm
            onCalculate={handleManualCalculate}
            loading={loading}
            waypoints={waypoints}
            onWaypointsReorder={handleWaypointsReorder}
            routeData={routeData}
            onGenerateShare={handleGenerateShare}
          />
        </div>

        <div className="main-content">
          {usingCache && routeData && (
            <div className="cache-warning">
              ⚠️ 当前显示的是缓存路线结果，最新API请求失败
            </div>
          )}
          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          <MapView
            routeData={routeData}
            waypoints={waypoints}
            loading={loading}
            playbackPosition={playbackPosition}
            isPlaying={isPlaying}
            onPlayback={handlePlayback}
            routeColor={routeData ? (ROUTE_STRATEGIES[selectedRouteKey]?.color || '#2a5298') : '#2a5298'}
          />

          {routeData && (
            <RouteSummary 
              routeData={routeData} 
              multiRoutes={multiRoutes}
              selectedRouteKey={selectedRouteKey}
              onSelectRoute={handleSelectRoute}
            />
          )}
        </div>
      </div>

      {showShareModal && (
        <ShareModal 
          url={shareUrl} 
          onClose={() => setShowShareModal(false)} 
        />
      )}
    </div>
  );
}

export default App;
