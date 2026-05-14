import { useEffect, useState, useCallback } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import LineChart from '../components/LineChart';
import Map from '../components/Map';
import AlarmList from '../components/AlarmList';
import wsService from '../utils/websocket';
import layoutConfig from '../config';

const ResponsiveGridLayout = WidthProvider(Responsive);

const Dashboard = () => {
  const [lineData, setLineData] = useState([]);
  const [mapData, setMapData] = useState([]);
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalOrders: 0,
    revenue: 0
  });
  const [alarms, setAlarms] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [layout, setLayout] = useState(() => layoutConfig.loadLayout());
  const [showLayoutTools, setShowLayoutTools] = useState(false);

  useEffect(() => {
    const handleMessage = (data) => {
      if (data.type === 'alarm') {
        setAlarms((prev) => [data, ...prev].slice(0, 20));
      } else {
        setLineData(data.lineChart);
        setMapData(data.mapData);
        setStats(data.stats);
      }
    };

    const handleOpen = () => {
      setIsConnected(true);
    };

    const handleClose = () => {
      setIsConnected(false);
    };

    wsService.on('message', handleMessage);
    wsService.on('open', handleOpen);
    wsService.on('close', handleClose);
    
    wsService.connect();

    return () => {
      wsService.off('message', handleMessage);
      wsService.off('open', handleOpen);
      wsService.off('close', handleClose);
      wsService.disconnect();
    };
  }, []);

  const formatNumber = (num) => {
    return num.toLocaleString('zh-CN');
  };

  const handleLayoutChange = useCallback((newLayout) => {
    setLayout(newLayout);
  }, []);

  const handleSaveLayout = useCallback(() => {
    layoutConfig.saveLayout(layout);
    alert('布局已保存！');
  }, [layout]);

  const handleResetLayout = useCallback(() => {
    const resetLayout = layoutConfig.resetLayout();
    setLayout(resetLayout);
    alert('布局已重置！');
  }, []);

  const handleDismissAlarm = useCallback((alarmId) => {
    setAlarms((prev) => prev.filter((alarm) => alarm.id !== alarmId));
  }, []);

  const StatCard = ({ icon, value, label }) => (
    <div className="stat-card no-drag">
      <div className="drag-handle">
        <span className="handle-icon">⋮⋮</span>
      </div>
      <div className="stat-content">
        <div className="stat-icon">{icon}</div>
        <div className="stat-info">
          <div className="stat-value">{value}</div>
          <div className="stat-label">{label}</div>
        </div>
      </div>
    </div>
  );

  const ChartWrapper = ({ title, children }) => (
    <div className="chart-wrapper no-drag">
      <div className="drag-handle">
        <span className="handle-icon">⋮⋮</span>
        <span className="chart-title">{title}</span>
      </div>
      <div className="chart-body">
        {children}
      </div>
    </div>
  );

  const layouts = { lg: layout };

  const gridItems = [
    {
      i: 'stat1',
      content: <StatCard icon="👥" value={formatNumber(stats.totalUsers)} label="总用户数" />
    },
    {
      i: 'stat2',
      content: <StatCard icon="👤" value={formatNumber(stats.activeUsers)} label="活跃用户" />
    },
    {
      i: 'stat3',
      content: <StatCard icon="📦" value={formatNumber(stats.totalOrders)} label="总订单数" />
    },
    {
      i: 'stat4',
      content: <StatCard icon="💰" value={`¥${formatNumber(stats.revenue)}`} label="总收入" />
    },
    {
      i: 'lineChart',
      content: (
        <ChartWrapper title="实时流量趋势">
          <LineChart data={lineData} />
        </ChartWrapper>
      )
    },
    {
      i: 'map',
      content: (
        <ChartWrapper title="全国区域分布">
          <Map data={mapData} />
        </ChartWrapper>
      )
    },
    {
      i: 'alarmList',
      content: <AlarmList alarms={alarms} onDismiss={handleDismissAlarm} />
    }
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>数据可视化大屏</h1>
        <div className="header-actions">
          <div className="status-indicator">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span>{isConnected ? '已连接' : '未连接'}</span>
          </div>
          <button className="btn-layout" onClick={() => setShowLayoutTools(!showLayoutTools)}>
            📐 布局
          </button>
          {showLayoutTools && (
            <div className="layout-tools">
              <button className="btn-save" onClick={handleSaveLayout}>
                💾 保存
              </button>
              <button className="btn-reset" onClick={handleResetLayout}>
                🔄 重置
              </button>
            </div>
          )}
        </div>
      </div>

      {alarms.length > 0 && (
        <div className="alarm-banner">
          <div className="alarm-banner-content">
            <span className="alarm-banner-icon">🚨</span>
            <span className="alarm-banner-text">
              最新告警: {alarms[0].title} - {alarms[0].message}
              <span className="alarm-banner-time">
                ({new Date(alarms[0].timestamp).toLocaleTimeString('zh-CN')})
              </span>
            </span>
          </div>
        </div>
      )}

      <div className="dashboard-content">
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 12, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={layoutConfig.rowHeight}
          compactType={layoutConfig.compactType}
          preventCollision={layoutConfig.preventCollision}
          draggableCancel={layoutConfig.draggableCancel}
          draggableHandle={layoutConfig.draggableHandle}
          onLayoutChange={(currentLayout) => handleLayoutChange(currentLayout)}
          margin={[20, 20]}
          containerPadding={[20, 20]}
          isDraggable={true}
          isResizable={true}
        >
          {gridItems.map((item) => (
            <div key={item.i} data-grid={layout.find((l) => l.i === item.i) || {}}>
              {item.content}
            </div>
          ))}
        </ResponsiveGridLayout>
      </div>

      <style>{`
        .dashboard {
          min-height: 100vh;
          padding: 0;
          background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 50%, #0a1628 100%);
          position: relative;
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 15px 30px;
          background: rgba(0, 179, 255, 0.1);
          border-bottom: 1px solid rgba(0, 179, 255, 0.3);
        }

        .dashboard-header h1 {
          margin: 0;
          color: #00b3ff;
          font-size: 28px;
          font-weight: bold;
          text-shadow: 0 0 10px rgba(0, 179, 255, 0.5);
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 20px;
          position: relative;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
        }

        .status-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }

        .status-dot.connected {
          background: #00ff88;
          box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
          animation: pulse 2s infinite;
        }

        .status-dot.disconnected {
          background: #ff4444;
          box-shadow: 0 0 10px rgba(255, 68, 68, 0.5);
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(0.9); }
        }

        .btn-layout, .btn-save, .btn-reset {
          background: rgba(0, 179, 255, 0.2);
          border: 1px solid rgba(0, 179, 255, 0.5);
          color: #fff;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.3s ease;
        }

        .btn-layout:hover, .btn-save:hover, .btn-reset:hover {
          background: rgba(0, 179, 255, 0.4);
          transform: translateY(-2px);
        }

        .btn-save {
          background: rgba(0, 255, 136, 0.2);
          border-color: rgba(0, 255, 136, 0.5);
        }

        .btn-save:hover {
          background: rgba(0, 255, 136, 0.4);
        }

        .btn-reset {
          background: rgba(255, 193, 7, 0.2);
          border-color: rgba(255, 193, 7, 0.5);
        }

        .btn-reset:hover {
          background: rgba(255, 193, 7, 0.4);
        }

        .layout-tools {
          position: absolute;
          top: 100%;
          right: 0;
          display: flex;
          gap: 10px;
          padding: 10px;
          background: rgba(10, 22, 40, 0.95);
          border: 1px solid rgba(0, 179, 255, 0.3);
          border-radius: 8px;
          z-index: 100;
          margin-top: 10px;
        }

        .alarm-banner {
          background: rgba(255, 68, 68, 0.15);
          border-bottom: 1px solid rgba(255, 68, 68, 0.3);
          padding: 12px 30px;
          animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
          from { transform: translateY(-100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .alarm-banner-content {
          display: flex;
          align-items: center;
          gap: 15px;
          max-width: 100%;
        }

        .alarm-banner-icon {
          font-size: 24px;
          animation: shake 0.5s ease infinite;
        }

        @keyframes shake {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-5deg); }
          75% { transform: rotate(5deg); }
        }

        .alarm-banner-text {
          color: #fff;
          font-size: 14px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .alarm-banner-time {
          color: rgba(255, 255, 255, 0.6);
          margin-left: 10px;
        }

        .dashboard-content {
          padding: 0;
          min-height: calc(100vh - 80px);
        }

        .layout {
          min-height: calc(100vh - 80px);
        }

        .react-grid-item {
          background: rgba(0, 179, 255, 0.05);
          border: 1px solid rgba(0, 179, 255, 0.2);
          border-radius: 10px;
          overflow: hidden;
          transition: all 0.3s ease;
        }

        .react-grid-item:hover {
          border-color: rgba(0, 179, 255, 0.5);
          box-shadow: 0 10px 30px rgba(0, 179, 255, 0.15);
        }

        .react-grid-item.react-grid-placeholder {
          background: rgba(0, 179, 255, 0.3);
          border-radius: 10px;
        }

        .drag-handle {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 15px;
          background: rgba(0, 179, 255, 0.1);
          border-bottom: 1px solid rgba(0, 179, 255, 0.2);
          cursor: move;
        }

        .handle-icon {
          color: rgba(0, 179, 255, 0.6);
          font-size: 18px;
          user-select: none;
        }

        .chart-title {
          color: #00b3ff;
          font-weight: bold;
          font-size: 16px;
        }

        .chart-body {
          height: calc(100% - 45px);
          padding: 15px;
        }

        .stat-card {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .stat-card .drag-handle {
          padding: 5px 10px;
        }

        .stat-card .drag-handle .handle-icon {
          font-size: 14px;
        }

        .stat-content {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 15px 20px;
        }

        .stat-icon {
          font-size: 36px;
        }

        .stat-info {
          flex: 1;
        }

        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #00ff88;
          margin-bottom: 3px;
        }

        .stat-label {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.7);
        }

        .react-resizable-handle {
          position: absolute;
          width: 20px;
          height: 20px;
          bottom: 0;
          right: 0;
          background: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2IDYiIHN0eWxlPSJiYWNrZ3JvdW5kLWNvbG9yOiNmZmZmZmYwMCIgeD0iMHB4IiB5PSIwcHgiIHdpZHRoPSI2cHgiIGhlaWdodD0iNnB4Ij48ZyBvcGFjaXR5PSIwLjMwMiI+PHBhdGggZD0iTSA2IDYgTCAwIDYgTCAwIDQuMiBMIDQgNC4yIEwgNC4yIDQuMiBMIDQuMiAwIEwgNiAwIEwgNiA2IEwgNiA2IFoiIGZpbGw9IiMwMDAwMDAiLz48L2c+PC9zdmc+');
          background-position: bottom right;
          padding: 0 3px 3px 0;
          background-repeat: no-repeat;
          background-origin: content-box;
          box-sizing: border-box;
          cursor: se-resize;
        }

        @media (max-width: 768px) {
          .dashboard-header {
            flex-direction: column;
            gap: 10px;
            padding: 10px 20px;
          }

          .dashboard-header h1 {
            font-size: 20px;
          }

          .header-actions {
            width: 100%;
            justify-content: space-between;
          }

          .stat-value {
            font-size: 18px;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
