import { useState } from 'react';
import { useTopology } from './hooks/useTopology';
import { TopologyGraph } from './components/TopologyGraph/TopologyGraph';
import { DevicePanel } from './components/DevicePanel/DevicePanel';
import { LinkStatus } from './components/LinkStatus/LinkStatus';
import { DeviceDetail } from './components/DeviceDetail/DeviceDetail';
import { HealthScore } from './components/HealthScore/HealthScore';
import { TimeTravel } from './components/TimeTravel/TimeTravel';
import './App.css';

function App() {
  const {
    devices,
    links,
    selectedDevice,
    selectedLink,
    isConnected,
    linkMetricsHistory,
    deviceMetricsHistory,
    healthScore,
    historySnapshots,
    timeTravel,
    faultEvents,
    setSelectedDevice,
    setSelectedLink,
    addDevice,
    removeDevice,
    addLink,
    removeLink,
    requestSync,
    enableTimeTravel,
    jumpToSnapshot,
    playHistory,
    pauseHistory,
    setPlaybackSpeed,
    triggerFault,
  } = useTopology();

  const [activeTab, setActiveTab] = useState<'devices' | 'links' | 'health'>('devices');

  const handleCloseDetail = () => {
    setSelectedDevice(null);
    setSelectedLink(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>
            <span className="logo-icon">🌐</span>
            网络拓扑可视化工具
          </h1>
          <span className="subtitle">Network Topology Visualization</span>
        </div>
        <div className="header-right">
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            <span>{isConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'}</span>
          </div>
          <div className="stats-header">
            <div className="stat-badge">
              <span className="stat-icon">📡</span>
              <span>{devices.length} 设备</span>
            </div>
            <div className="stat-badge">
              <span className="stat-icon">🔗</span>
              <span>{links.length} 链路</span>
            </div>
          </div>
        </div>
      </header>

      <div className="app-body">
        <aside className="side-panel">
          <div className="panel-tabs">
            <button
              className={`tab-btn ${activeTab === 'devices' ? 'active' : ''}`}
              onClick={() => setActiveTab('devices')}
            >
              📡 设备管理
            </button>
            <button
              className={`tab-btn ${activeTab === 'links' ? 'active' : ''}`}
              onClick={() => setActiveTab('links')}
            >
              🔗 链路状态
            </button>
            <button
              className={`tab-btn ${activeTab === 'health' ? 'active' : ''}`}
              onClick={() => setActiveTab('health')}
            >
              ❤️ 健康监控
            </button>
          </div>

          <div className="panel-content">
            {activeTab === 'devices' ? (
              <DevicePanel
                devices={devices}
                links={links}
                selectedDeviceId={selectedDevice?.id || null}
                onAddDevice={addDevice}
                onRemoveDevice={removeDevice}
                onAddLink={addLink}
                onSelectDevice={setSelectedDevice}
              />
            ) : activeTab === 'links' ? (
              <LinkStatus
                links={links}
                devices={devices}
                selectedLinkId={selectedLink?.id || null}
                onSelectLink={setSelectedLink}
                onRemoveLink={removeLink}
              />
            ) : (
              <HealthScore healthScore={healthScore} />
            )}
          </div>
        </aside>

        <main className="main-content">
          {timeTravel.isEnabled && (
            <div className="time-travel-banner">
              <span className="banner-icon">⏰</span>
              <span className="banner-text">时间旅行模式已启用 - 正在查看历史状态</span>
              <button className="banner-close" onClick={() => enableTimeTravel(false)}>
                ✕ 退出
              </button>
            </div>
          )}
          
          <TopologyGraph
            devices={devices}
            links={links}
            selectedDeviceId={selectedDevice?.id || null}
            selectedLinkId={selectedLink?.id || null}
            onDeviceSelect={setSelectedDevice}
            onLinkSelect={setSelectedLink}
          />
          
          <TimeTravel
            timeTravel={timeTravel}
            historySnapshots={historySnapshots}
            onEnable={enableTimeTravel}
            onJump={jumpToSnapshot}
            onPlay={playHistory}
            onPause={pauseHistory}
            onSpeedChange={setPlaybackSpeed}
          />
        </main>

        {(selectedDevice || selectedLink) && (
          <aside className="detail-panel-wrapper">
            <DeviceDetail
              device={selectedDevice}
              link={selectedLink}
              devices={devices}
              links={links}
              deviceMetricsHistory={deviceMetricsHistory}
              linkMetricsHistory={linkMetricsHistory}
              onClose={handleCloseDetail}
              onRemoveDevice={removeDevice}
              onRemoveLink={removeLink}
            />
          </aside>
        )}
      </div>
    </div>
  );
}

export default App;
