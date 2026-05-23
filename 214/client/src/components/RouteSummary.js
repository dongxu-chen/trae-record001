import React from 'react';

function formatDistance(meters) {
  if (meters >= 1000) {
    return (meters / 1000).toFixed(2);
  }
  return meters.toString();
}

function formatDistanceUnit(meters) {
  return meters >= 1000 ? '公里' : '米';
}

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`;
  }
  return `${minutes}分钟`;
}

function getPointLabel(index, totalWaypoints) {
  if (index === 0) return '起点';
  if (index === totalWaypoints + 1) return '终点';
  return `途经点${index}`;
}

function formatCoord(lng, lat) {
  return `(${lng.toFixed(4)}, ${lat.toFixed(4)})`;
}

function RouteSummary({ routeData, multiRoutes = [], selectedRouteKey, onSelectRoute }) {
  if (!routeData) return null;

  const totalDistance = routeData.totalDistance || 0;
  const totalDuration = routeData.totalDuration || 0;
  const segments = routeData.segments || [];
  const waypoints = routeData.waypoints || [];

  return (
    <div className="summary-container">
      <h2 className="summary-title">📊 路线摘要</h2>
      
      {multiRoutes.length > 1 && (
        <>
          <h3 className="segments-title">🔄 路线方案对比</h3>
          <div className="route-compare">
            {multiRoutes.map((route) => (
              <div
                key={route.key}
                className={`route-compare-card ${route.key === selectedRouteKey ? 'selected' : ''} ${!route.success ? 'failed' : ''}`}
                style={{ color: route.color, borderColor: route.success ? route.color : '#ddd' }}
                onClick={() => route.success && onSelectRoute && onSelectRoute(route.key)}
              >
                <span className={`route-compare-status ${route.success ? 'success' : 'failed'}`}>
                  {route.success ? '成功' : '失败'}
                </span>
                <div className="route-compare-header">
                  <span 
                    style={{ 
                      display: 'inline-block', 
                      width: '10px', 
                      height: '10px', 
                      borderRadius: '50%', 
                      background: route.color 
                    }}
                  ></span>
                  {route.name}
                </div>
                {route.success ? (
                  <>
                    <div className="route-compare-value">
                      {formatDistance(route.totalDistance)}
                      <span className="route-compare-label"> {formatDistanceUnit(route.totalDistance)}</span>
                    </div>
                    <div className="route-compare-label">
                      {formatDuration(route.totalDuration)}
                    </div>
                  </>
                ) : (
                  <div className="route-compare-label" style={{ color: '#e74c3c' }}>
                    {route.error || '规划失败'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      <div className="summary-stats">
        <div className="stat-card blue">
          <div className="stat-label">总里程</div>
          <div>
            <span className="stat-value">{formatDistance(totalDistance)}</span>
            <span className="stat-unit">{formatDistanceUnit(totalDistance)}</span>
          </div>
        </div>
        
        <div className="stat-card green">
          <div className="stat-label">预计时间</div>
          <div>
            <span className="stat-value" style={{ fontSize: '20px' }}>{formatDuration(totalDuration)}</span>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">途经点</div>
          <div>
            <span className="stat-value">{waypoints.length}</span>
            <span className="stat-unit">个</span>
          </div>
        </div>
        
        <div className="stat-card orange">
          <div className="stat-label">路段数</div>
          <div>
            <span className="stat-value">{segments.length}</span>
            <span className="stat-unit">段</span>
          </div>
        </div>
      </div>

      <h3 className="segments-title">📍 各段里程详情</h3>
      <div className="segments-list">
        {segments.map((segment, idx) => (
          <div key={idx} className="segment-item">
            <span className="segment-number">{idx + 1}</span>
            <div className="segment-info">
              <div className="segment-route">
                {getPointLabel(segment.fromIndex, waypoints.length)} → {getPointLabel(segment.toIndex, waypoints.length)}
              </div>
              <div className="segment-coords">
                {formatCoord(segment.from.lng, segment.from.lat)} → {formatCoord(segment.to.lng, segment.to.lat)}
              </div>
            </div>
            <div className="segment-distance">
              <div>
                <span className="segment-distance-value">{formatDistance(segment.distance)}</span>
                <span className="segment-distance-unit">{formatDistanceUnit(segment.distance)}</span>
              </div>
              <div className="segment-duration">
                {formatDuration(segment.duration)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {segments.length > 0 && (
        <div style={{ 
          marginTop: '20px', 
          padding: '12px 16px', 
          background: '#fff8e1', 
          borderRadius: '8px',
          fontSize: '14px',
          color: '#795548'
        }}>
          💡 <strong>提示：</strong>点击地图下方的播放按钮可模拟行驶过程，拖拽左侧途经点列表调整顺序后自动重新计算。
        </div>
      )}
    </div>
  );
}

export default RouteSummary;
