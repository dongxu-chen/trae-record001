import React from 'react';
import { Link, Device } from '../../types';
import { getStatusColor } from '../../utils/cytoscape';

interface LinkStatusProps {
  links: Link[];
  devices: Device[];
  selectedLinkId: string | null;
  onSelectLink: (link: Link) => void;
  onRemoveLink: (linkId: string) => void;
}

export const LinkStatus: React.FC<LinkStatusProps> = ({
  links,
  devices,
  selectedLinkId,
  onSelectLink,
  onRemoveLink,
}) => {
  const getDeviceName = (deviceId: string) => {
    const device = devices.find((d) => d.id === deviceId);
    return device ? device.name : deviceId;
  };

  const getStatusText = (status: Link['status']) => {
    switch (status) {
      case 'up':
        return '正常';
      case 'degraded':
        return '降级';
      case 'down':
        return '中断';
      default:
        return status;
    }
  };

  const getLinkCountByStatus = (status: Link['status']) =>
    links.filter((l) => l.status === status).length;

  const avgLatency = links.length > 0
    ? links.reduce((sum, l) => sum + l.latency, 0) / links.length
    : 0;

  const avgPacketLoss = links.length > 0
    ? links.reduce((sum, l) => sum + l.packetLoss, 0) / links.length
    : 0;

  const avgUtilization = links.length > 0
    ? links.reduce((sum, l) => sum + l.utilization, 0) / links.length
    : 0;

  return (
    <div className="link-status-panel">
      <div className="panel-header">
        <h3>链路状态</h3>
      </div>

      <div className="stats-summary">
        <div className="stat-item">
          <span className="stat-label">总链路</span>
          <span className="stat-value">{links.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">正常</span>
          <span className="stat-value" style={{ color: '#22c55e' }}>
            {getLinkCountByStatus('up')}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">降级</span>
          <span className="stat-value" style={{ color: '#f59e0b' }}>
            {getLinkCountByStatus('degraded')}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">中断</span>
          <span className="stat-value" style={{ color: '#ef4444' }}>
            {getLinkCountByStatus('down')}
          </span>
        </div>
      </div>

      <div className="overview-metrics">
        <div className="overview-metric">
          <span className="overview-label">平均延迟</span>
          <span className="overview-value" style={{ color: avgLatency > 50 ? '#ef4444' : avgLatency > 20 ? '#f59e0b' : '#22c55e' }}>
            {avgLatency.toFixed(1)} ms
          </span>
        </div>
        <div className="overview-metric">
          <span className="overview-label">平均丢包率</span>
          <span className="overview-value" style={{ color: avgPacketLoss > 5 ? '#ef4444' : avgPacketLoss > 1 ? '#f59e0b' : '#22c55e' }}>
            {avgPacketLoss.toFixed(2)}%
          </span>
        </div>
        <div className="overview-metric">
          <span className="overview-label">平均利用率</span>
          <span className="overview-value" style={{ color: avgUtilization > 80 ? '#ef4444' : avgUtilization > 60 ? '#f59e0b' : '#22c55e' }}>
            {avgUtilization.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="link-list">
        {links.map((link) => {
          const sourceName = getDeviceName(link.source);
          const targetName = getDeviceName(link.target);
          
          return (
            <div
              key={link.id}
              className={`link-item ${selectedLinkId === link.id ? 'selected' : ''}`}
              onClick={() => onSelectLink(link)}
            >
              <div className="link-header">
                <div className="link-endpoints">
                  <span className="device-name">{sourceName}</span>
                  <span className="link-arrow">→</span>
                  <span className="device-name">{targetName}</span>
                </div>
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(link.status) }}
                >
                  {getStatusText(link.status)}
                </span>
              </div>
              
              <div className="link-metrics">
                <div className="metric-item">
                  <span className="metric-label">带宽</span>
                  <span className="metric-value">{link.bandwidth} Mbps</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">延迟</span>
                  <span
                    className="metric-value"
                    style={{
                      color: link.latency > 50 ? '#ef4444' : link.latency > 20 ? '#f59e0b' : '#22c55e',
                    }}
                  >
                    {link.latency.toFixed(1)} ms
                  </span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">丢包率</span>
                  <span
                    className="metric-value"
                    style={{
                      color: link.packetLoss > 5 ? '#ef4444' : link.packetLoss > 1 ? '#f59e0b' : '#22c55e',
                    }}
                  >
                    {link.packetLoss.toFixed(2)}%
                  </span>
                </div>
              </div>

              <div className="link-utilization">
                <div className="utilization-header">
                  <span className="metric-label">链路利用率</span>
                  <span
                    className="metric-value"
                    style={{
                      color: link.utilization > 80 ? '#ef4444' : link.utilization > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  >
                    {link.utilization.toFixed(1)}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${link.utilization}%`,
                      backgroundColor: link.utilization > 80 ? '#ef4444' : link.utilization > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  />
                </div>
              </div>

              <button
                className="btn btn-danger btn-sm btn-link-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`确定要删除这条链路吗？`)) {
                    onRemoveLink(link.id);
                  }
                }}
              >
                删除链路
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
