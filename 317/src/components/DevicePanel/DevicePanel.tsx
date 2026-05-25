import React, { useState } from 'react';
import { Device, DeviceType, Link } from '../../types';
import { getStatusColor, getDeviceIcon } from '../../utils/cytoscape';

interface DevicePanelProps {
  devices: Device[];
  links: Link[];
  selectedDeviceId: string | null;
  onAddDevice: (device: Omit<Device, 'id'>) => void;
  onRemoveDevice: (deviceId: string) => void;
  onAddLink: (link: Omit<Link, 'id'>) => void;
  onSelectDevice: (device: Device) => void;
}

export const DevicePanel: React.FC<DevicePanelProps> = ({
  devices,
  links,
  selectedDeviceId,
  onAddDevice,
  onRemoveDevice,
  onAddLink,
  onSelectDevice,
}) => {
  const [showAddDevice, setShowAddDevice] = useState(false);
  const [showAddLink, setShowAddLink] = useState(false);
  const [deviceFilter, setDeviceFilter] = useState<DeviceType | 'all'>('all');
  const [newDevice, setNewDevice] = useState({
    name: '',
    type: 'router' as DeviceType,
    ip: '',
    mac: '',
    location: '',
    description: '',
  });
  const [newLink, setNewLink] = useState({
    source: '',
    target: '',
    bandwidth: 1000,
  });

  const filteredDevices = deviceFilter === 'all'
    ? devices
    : devices.filter((d) => d.type === deviceFilter);

  const handleAddDevice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDevice.name || !newDevice.ip) return;

    onAddDevice({
      ...newDevice,
      status: 'online',
      cpu: 0,
      memory: 0,
      uptime: '0 days 00:00:00',
      interfaces: [],
    });

    setNewDevice({
      name: '',
      type: 'router',
      ip: '',
      mac: '',
      location: '',
      description: '',
    });
    setShowAddDevice(false);
  };

  const handleAddLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLink.source || !newLink.target) return;

    onAddLink({
      ...newLink,
      latency: 0,
      packetLoss: 0,
      status: 'up',
      utilization: 0,
    });

    setNewLink({ source: '', target: '', bandwidth: 1000 });
    setShowAddLink(false);
  };

  const getDeviceCountByType = (type: DeviceType) =>
    devices.filter((d) => d.type === type).length;

  const getDeviceCountByStatus = (status: Device['status']) =>
    devices.filter((d) => d.status === status).length;

  return (
    <div className="device-panel">
      <div className="panel-header">
        <h3>网络设备</h3>
        <div className="panel-actions">
          <button
            className="btn btn-primary btn-sm"
            onClick={() => setShowAddDevice(true)}
          >
            + 添加设备
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowAddLink(true)}
          >
            + 添加链路
          </button>
        </div>
      </div>

      <div className="stats-summary">
        <div className="stat-item">
          <span className="stat-label">总计</span>
          <span className="stat-value">{devices.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">在线</span>
          <span className="stat-value" style={{ color: '#22c55e' }}>
            {getDeviceCountByStatus('online')}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">警告</span>
          <span className="stat-value" style={{ color: '#f59e0b' }}>
            {getDeviceCountByStatus('warning')}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">离线</span>
          <span className="stat-value" style={{ color: '#ef4444' }}>
            {getDeviceCountByStatus('offline')}
          </span>
        </div>
      </div>

      <div className="type-filters">
        <button
          className={`filter-btn ${deviceFilter === 'all' ? 'active' : ''}`}
          onClick={() => setDeviceFilter('all')}
        >
          全部 ({devices.length})
        </button>
        <button
          className={`filter-btn ${deviceFilter === 'router' ? 'active' : ''}`}
          onClick={() => setDeviceFilter('router')}
        >
          📡 路由器 ({getDeviceCountByType('router')})
        </button>
        <button
          className={`filter-btn ${deviceFilter === 'switch' ? 'active' : ''}`}
          onClick={() => setDeviceFilter('switch')}
        >
          🔌 交换机 ({getDeviceCountByType('switch')})
        </button>
        <button
          className={`filter-btn ${deviceFilter === 'server' ? 'active' : ''}`}
          onClick={() => setDeviceFilter('server')}
        >
          🖥️ 服务器 ({getDeviceCountByType('server')})
        </button>
      </div>

      <div className="device-list">
        {filteredDevices.map((device) => (
          <div
            key={device.id}
            className={`device-item ${selectedDeviceId === device.id ? 'selected' : ''}`}
            onClick={() => onSelectDevice(device)}
          >
            <div className="device-icon" style={{ borderColor: getStatusColor(device.status) }}>
              {getDeviceIcon(device.type)}
            </div>
            <div className="device-info">
              <div className="device-name">{device.name}</div>
              <div className="device-ip">{device.ip}</div>
              <div className="device-metrics">
                <div className="metric-mini">
                  <span className="metric-label">CPU</span>
                  <div className="progress-bar mini">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${device.cpu}%`,
                        backgroundColor: device.cpu > 80 ? '#ef4444' : device.cpu > 60 ? '#f59e0b' : '#22c55e',
                      }}
                    />
                  </div>
                  <span className="metric-value">{device.cpu.toFixed(0)}%</span>
                </div>
                <div className="metric-mini">
                  <span className="metric-label">内存</span>
                  <div className="progress-bar mini">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${device.memory}%`,
                        backgroundColor: device.memory > 80 ? '#ef4444' : device.memory > 60 ? '#f59e0b' : '#22c55e',
                      }}
                    />
                  </div>
                  <span className="metric-value">{device.memory.toFixed(0)}%</span>
                </div>
              </div>
            </div>
            <button
              className="btn btn-danger btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`确定要删除设备 ${device.name} 吗？`)) {
                  onRemoveDevice(device.id);
                }
              }}
            >
              删除
            </button>
          </div>
        ))}
      </div>

      {showAddDevice && (
        <div className="modal-overlay" onClick={() => setShowAddDevice(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h4>添加新设备</h4>
            <form onSubmit={handleAddDevice}>
              <div className="form-group">
                <label>设备名称 *</label>
                <input
                  type="text"
                  value={newDevice.name}
                  onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
                  placeholder="例如：Router-01"
                  required
                />
              </div>
              <div className="form-group">
                <label>设备类型</label>
                <select
                  value={newDevice.type}
                  onChange={(e) => setNewDevice({ ...newDevice, type: e.target.value as DeviceType })}
                >
                  <option value="router">路由器</option>
                  <option value="switch">交换机</option>
                  <option value="server">服务器</option>
                </select>
              </div>
              <div className="form-group">
                <label>IP 地址 *</label>
                <input
                  type="text"
                  value={newDevice.ip}
                  onChange={(e) => setNewDevice({ ...newDevice, ip: e.target.value })}
                  placeholder="例如：192.168.1.100"
                  required
                />
              </div>
              <div className="form-group">
                <label>MAC 地址</label>
                <input
                  type="text"
                  value={newDevice.mac}
                  onChange={(e) => setNewDevice({ ...newDevice, mac: e.target.value })}
                  placeholder="例如：00:1A:2B:3C:4D:5E"
                />
              </div>
              <div className="form-group">
                <label>位置</label>
                <input
                  type="text"
                  value={newDevice.location}
                  onChange={(e) => setNewDevice({ ...newDevice, location: e.target.value })}
                  placeholder="例如：Data Center A - Rack 1"
                />
              </div>
              <div className="form-group">
                <label>描述</label>
                <textarea
                  value={newDevice.description}
                  onChange={(e) => setNewDevice({ ...newDevice, description: e.target.value })}
                  placeholder="设备描述信息"
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddDevice(false)}
                >
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  添加
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAddLink && (
        <div className="modal-overlay" onClick={() => setShowAddLink(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h4>添加新链路</h4>
            <form onSubmit={handleAddLink}>
              <div className="form-group">
                <label>源设备 *</label>
                <select
                  value={newLink.source}
                  onChange={(e) => setNewLink({ ...newLink, source: e.target.value })}
                  required
                >
                  <option value="">请选择源设备</option>
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.ip})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>目标设备 *</label>
                <select
                  value={newLink.target}
                  onChange={(e) => setNewLink({ ...newLink, target: e.target.value })}
                  required
                >
                  <option value="">请选择目标设备</option>
                  {devices
                    .filter((d) => d.id !== newLink.source)
                    .map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.ip})
                      </option>
                    ))}
                </select>
              </div>
              <div className="form-group">
                <label>带宽 (Mbps)</label>
                <input
                  type="number"
                  value={newLink.bandwidth}
                  onChange={(e) => setNewLink({ ...newLink, bandwidth: Number(e.target.value) })}
                  min={1}
                  max={100000}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddLink(false)}
                >
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  添加
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
