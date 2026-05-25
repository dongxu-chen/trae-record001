import React from 'react';
import { Device, Link, DeviceMetrics, LinkMetrics } from '../../types';
import { getStatusColor, getDeviceIcon } from '../../utils/cytoscape';
import { MetricsChart } from '../Charts/MetricsChart';

interface DeviceDetailProps {
  device: Device | null;
  link: Link | null;
  devices: Device[];
  links: Link[];
  deviceMetricsHistory: Map<string, DeviceMetrics[]>;
  linkMetricsHistory: Map<string, LinkMetrics[]>;
  onClose: () => void;
  onRemoveDevice: (deviceId: string) => void;
  onRemoveLink: (linkId: string) => void;
}

export const DeviceDetail: React.FC<DeviceDetailProps> = ({
  device,
  link,
  devices,
  links,
  deviceMetricsHistory,
  linkMetricsHistory,
  onClose,
  onRemoveDevice,
  onRemoveLink,
}) => {
  if (!device && !link) return null;

  const getDeviceName = (deviceId: string) => {
    const d = devices.find((dev) => dev.id === deviceId);
    return d ? d.name : deviceId;
  };

  const getStatusText = (status: Device['status'] | Link['status']) => {
    switch (status) {
      case 'online':
      case 'up':
        return '在线/正常';
      case 'warning':
      case 'degraded':
        return '警告/降级';
      case 'offline':
      case 'down':
        return '离线/中断';
      default:
        return status;
    }
  };

  if (device) {
    const deviceLinks = links.filter(
      (l) => l.source === device.id || l.target === device.id
    );
    const metricsHistory = deviceMetricsHistory.get(device.id) || [];

    return (
      <div className="detail-panel">
        <div className="panel-header">
          <h3>设备详情</h3>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-content">
          <div className="detail-header">
            <div className="detail-icon" style={{ borderColor: getStatusColor(device.status) }}>
              {getDeviceIcon(device.type)}
            </div>
            <div className="detail-title">
              <h4>{device.name}</h4>
              <span
                className="status-badge"
                style={{ backgroundColor: getStatusColor(device.status) }}
              >
                {getStatusText(device.status)}
              </span>
            </div>
          </div>

          <div className="detail-section">
            <h5>基本信息</h5>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">设备类型</span>
                <span className="info-value">
                  {device.type === 'router' ? '路由器' : device.type === 'switch' ? '交换机' : '服务器'}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">IP 地址</span>
                <span className="info-value">{device.ip}</span>
              </div>
              <div className="info-item">
                <span className="info-label">MAC 地址</span>
                <span className="info-value">{device.mac}</span>
              </div>
              <div className="info-item">
                <span className="info-label">位置</span>
                <span className="info-value">{device.location}</span>
              </div>
              <div className="info-item">
                <span className="info-label">运行时间</span>
                <span className="info-value">{device.uptime}</span>
              </div>
            </div>
            <p className="description">{device.description}</p>
          </div>

          <div className="detail-section">
            <h5>实时性能</h5>
            <div className="performance-metrics">
              <div className="performance-item">
                <div className="performance-header">
                  <span className="metric-label">CPU 使用率</span>
                  <span
                    className="metric-value"
                    style={{
                      color: device.cpu > 80 ? '#ef4444' : device.cpu > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  >
                    {device.cpu.toFixed(1)}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${device.cpu}%`,
                      backgroundColor: device.cpu > 80 ? '#ef4444' : device.cpu > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  />
                </div>
              </div>
              <div className="performance-item">
                <div className="performance-header">
                  <span className="metric-label">内存使用率</span>
                  <span
                    className="metric-value"
                    style={{
                      color: device.memory > 80 ? '#ef4444' : device.memory > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  >
                    {device.memory.toFixed(1)}%
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${device.memory}%`,
                      backgroundColor: device.memory > 80 ? '#ef4444' : device.memory > 60 ? '#f59e0b' : '#22c55e',
                    }}
                  />
                </div>
              </div>
            </div>

            {metricsHistory.length > 0 && (
              <div className="chart-container">
                <MetricsChart
                  data={metricsHistory.map((m) => ({
                    timestamp: m.timestamp,
                    value: m.cpu,
                  }))}
                  label="CPU 使用率 (%)"
                  color="#3b82f6"
                />
                <MetricsChart
                  data={metricsHistory.map((m) => ({
                    timestamp: m.timestamp,
                    value: m.memory,
                  }))}
                  label="内存使用率 (%)"
                  color="#8b5cf6"
                />
              </div>
            )}
          </div>

          <div className="detail-section">
            <h5>接口列表 ({device.interfaces.length})</h5>
            <div className="interface-list">
              {device.interfaces.map((iface, idx) => (
                <div key={idx} className="interface-item">
                  <div className="interface-status">
                    <span
                      className="status-dot"
                      style={{ backgroundColor: iface.status === 'up' ? '#22c55e' : '#ef4444' }}
                    />
                    <span className="interface-name">{iface.name}</span>
                  </div>
                  <div className="interface-details">
                    <span>{iface.speed}</span>
                    <span>{iface.mac}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="detail-section">
            <h5>关联链路 ({deviceLinks.length})</h5>
            <div className="related-links">
              {deviceLinks.map((l) => (
                <div key={l.id} className="related-link-item">
                  <div className="link-path">
                    <span>{getDeviceName(l.source)}</span>
                    <span className="link-arrow">→</span>
                    <span>{getDeviceName(l.target)}</span>
                  </div>
                  <span
                    className="status-badge small"
                    style={{ backgroundColor: getStatusColor(l.status) }}
                  >
                    {getStatusText(l.status)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="detail-actions">
            <button
              className="btn btn-danger"
              onClick={() => {
                if (confirm(`确定要删除设备 ${device.name} 吗？`)) {
                  onRemoveDevice(device.id);
                  onClose();
                }
              }}
            >
              删除设备
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (link) {
    const metricsHistory = linkMetricsHistory.get(link.id) || [];
    const sourceDevice = devices.find((d) => d.id === link.source);
    const targetDevice = devices.find((d) => d.id === link.target);

    return (
      <div className="detail-panel">
        <div className="panel-header">
          <h3>链路详情</h3>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="detail-content">
          <div className="detail-header">
            <div className="link-detail-path">
              <div className="link-device">
                <div
                  className="link-device-icon"
                  style={{ borderColor: getStatusColor(sourceDevice?.status || 'offline') }}
                >
                  {sourceDevice && getDeviceIcon(sourceDevice.type)}
                </div>
                <span>{sourceDevice?.name || link.source}</span>
              </div>
              <div
                className="link-line"
                style={{ backgroundColor: getStatusColor(link.status) }}
              >
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(link.status) }}
                >
                  {getStatusText(link.status)}
                </span>
              </div>
              <div className="link-device">
                <div
                  className="link-device-icon"
                  style={{ borderColor: getStatusColor(targetDevice?.status || 'offline') }}
                >
                  {targetDevice && getDeviceIcon(targetDevice.type)}
                </div>
                <span>{targetDevice?.name || link.target}</span>
              </div>
            </div>
          </div>

          <div className="detail-section">
            <h5>链路指标</h5>
            <div className="link-metrics-grid">
              <div className="link-metric-card">
                <span className="metric-label">带宽</span>
                <span className="metric-value large">{link.bandwidth} Mbps</span>
              </div>
              <div className="link-metric-card">
                <span className="metric-label">当前延迟</span>
                <span
                  className="metric-value large"
                  style={{
                    color: link.latency > 50 ? '#ef4444' : link.latency > 20 ? '#f59e0b' : '#22c55e',
                  }}
                >
                  {link.latency.toFixed(1)} ms
                </span>
              </div>
              <div className="link-metric-card">
                <span className="metric-label">丢包率</span>
                <span
                  className="metric-value large"
                  style={{
                    color: link.packetLoss > 5 ? '#ef4444' : link.packetLoss > 1 ? '#f59e0b' : '#22c55e',
                  }}
                >
                  {link.packetLoss.toFixed(2)}%
                </span>
              </div>
              <div className="link-metric-card">
                <span className="metric-label">利用率</span>
                <span
                  className="metric-value large"
                  style={{
                    color: link.utilization > 80 ? '#ef4444' : link.utilization > 60 ? '#f59e0b' : '#22c55e',
                  }}
                >
                  {link.utilization.toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="utilization-full">
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
              <div className="progress-bar large">
                <div
                  className="progress-fill"
                  style={{
                    width: `${link.utilization}%`,
                    backgroundColor: link.utilization > 80 ? '#ef4444' : link.utilization > 60 ? '#f59e0b' : '#22c55e',
                  }}
                />
              </div>
            </div>
          </div>

          {metricsHistory.length > 0 && (
            <div className="detail-section">
              <h5>历史趋势</h5>
              <div className="chart-container">
                <MetricsChart
                  data={metricsHistory.map((m) => ({
                    timestamp: m.timestamp,
                    value: m.latency,
                  }))}
                  label="延迟 (ms)"
                  color="#ef4444"
                />
                <MetricsChart
                  data={metricsHistory.map((m) => ({
                    timestamp: m.timestamp,
                    value: m.packetLoss,
                  }))}
                  label="丢包率 (%)"
                  color="#f59e0b"
                />
                <MetricsChart
                  data={metricsHistory.map((m) => ({
                    timestamp: m.timestamp,
                    value: m.utilization,
                  }))}
                  label="利用率 (%)"
                  color="#22c55e"
                />
              </div>
            </div>
          )}

          <div className="detail-actions">
            <button
              className="btn btn-danger"
              onClick={() => {
                if (confirm('确定要删除这条链路吗？')) {
                  onRemoveLink(link.id);
                  onClose();
                }
              }}
            >
              删除链路
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};
