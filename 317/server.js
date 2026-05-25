process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  console.error('Stack:', error.stack);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

import express from 'express';
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import cors from 'cors';

const initialTopologyData = {
  devices: [
    {
      id: 'router-1',
      name: 'Core-Router-01',
      type: 'router',
      ip: '192.168.1.1',
      mac: '00:1A:2B:3C:4D:5E',
      location: 'Data Center A - Rack 1',
      status: 'online',
      cpu: 45,
      memory: 62,
      uptime: '45 days 12:34:56',
      description: '核心路由器，负责整个网络的路由转发',
      interfaces: [
        { name: 'GigabitEthernet0/0', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:5E' },
        { name: 'GigabitEthernet0/1', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:5F' },
        { name: 'GigabitEthernet0/2', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:60' },
      ],
    },
    {
      id: 'router-2',
      name: 'Edge-Router-01',
      type: 'router',
      ip: '192.168.1.2',
      mac: '00:1A:2B:3C:4D:61',
      location: 'Data Center B - Rack 1',
      status: 'online',
      cpu: 32,
      memory: 48,
      uptime: '30 days 08:22:15',
      description: '边缘路由器，连接外部网络',
      interfaces: [
        { name: 'GigabitEthernet0/0', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:61' },
        { name: 'GigabitEthernet0/1', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:62' },
      ],
    },
    {
      id: 'switch-1',
      name: 'Core-Switch-01',
      type: 'switch',
      ip: '192.168.1.10',
      mac: '00:1A:2B:3C:4D:70',
      location: 'Data Center A - Rack 2',
      status: 'online',
      cpu: 28,
      memory: 35,
      uptime: '60 days 15:45:30',
      description: '核心交换机，连接服务器和路由器',
      interfaces: [
        { name: 'GigabitEthernet1/0/1', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:70' },
        { name: 'GigabitEthernet1/0/2', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:71' },
        { name: 'GigabitEthernet1/0/3', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:72' },
        { name: 'GigabitEthernet1/0/4', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:73' },
        { name: 'GigabitEthernet1/0/5', status: 'down', speed: '1Gbps', mac: '00:1A:2B:3C:4D:74' },
      ],
    },
    {
      id: 'switch-2',
      name: 'Access-Switch-01',
      type: 'switch',
      ip: '192.168.1.11',
      mac: '00:1A:2B:3C:4D:80',
      location: 'Data Center B - Rack 2',
      status: 'warning',
      cpu: 78,
      memory: 85,
      uptime: '15 days 03:12:45',
      description: '接入交换机，高负载警告',
      interfaces: [
        { name: 'FastEthernet0/1', status: 'up', speed: '100Mbps', mac: '00:1A:2B:3C:4D:80' },
        { name: 'FastEthernet0/2', status: 'up', speed: '100Mbps', mac: '00:1A:2B:3C:4D:81' },
        { name: 'FastEthernet0/3', status: 'up', speed: '100Mbps', mac: '00:1A:2B:3C:4D:82' },
      ],
    },
    {
      id: 'server-1',
      name: 'Web-Server-01',
      type: 'server',
      ip: '192.168.2.10',
      mac: '00:1A:2B:3C:4D:90',
      location: 'Data Center A - Rack 3',
      status: 'online',
      cpu: 55,
      memory: 72,
      uptime: '25 days 18:30:00',
      description: 'Web应用服务器，运行网站服务',
      interfaces: [
        { name: 'eth0', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:90' },
      ],
    },
    {
      id: 'server-2',
      name: 'DB-Server-01',
      type: 'server',
      ip: '192.168.2.11',
      mac: '00:1A:2B:3C:4D:91',
      location: 'Data Center A - Rack 3',
      status: 'online',
      cpu: 68,
      memory: 82,
      uptime: '25 days 18:30:00',
      description: '数据库服务器，存储业务数据',
      interfaces: [
        { name: 'eth0', status: 'up', speed: '1Gbps', mac: '00:1A:2B:3C:4D:91' },
      ],
    },
    {
      id: 'server-3',
      name: 'File-Server-01',
      type: 'server',
      ip: '192.168.2.12',
      mac: '00:1A:2B:3C:4D:92',
      location: 'Data Center B - Rack 3',
      status: 'offline',
      cpu: 0,
      memory: 0,
      uptime: '0 days 00:00:00',
      description: '文件服务器，当前离线维护中',
      interfaces: [
        { name: 'eth0', status: 'down', speed: '1Gbps', mac: '00:1A:2B:3C:4D:92' },
      ],
    },
  ],
  links: [
    {
      id: 'link-1',
      source: 'router-1',
      target: 'router-2',
      bandwidth: 1000,
      latency: 5,
      packetLoss: 0.1,
      status: 'up',
      utilization: 45,
    },
    {
      id: 'link-2',
      source: 'router-1',
      target: 'switch-1',
      bandwidth: 1000,
      latency: 2,
      packetLoss: 0.01,
      status: 'up',
      utilization: 62,
    },
    {
      id: 'link-3',
      source: 'router-2',
      target: 'switch-2',
      bandwidth: 1000,
      latency: 3,
      packetLoss: 0.05,
      status: 'up',
      utilization: 38,
    },
    {
      id: 'link-4',
      source: 'switch-1',
      target: 'server-1',
      bandwidth: 1000,
      latency: 1,
      packetLoss: 0.02,
      status: 'up',
      utilization: 55,
    },
    {
      id: 'link-5',
      source: 'switch-1',
      target: 'server-2',
      bandwidth: 1000,
      latency: 1,
      packetLoss: 0.01,
      status: 'up',
      utilization: 72,
    },
    {
      id: 'link-6',
      source: 'switch-2',
      target: 'server-3',
      bandwidth: 1000,
      latency: 0,
      packetLoss: 100,
      status: 'down',
      utilization: 0,
    },
    {
      id: 'link-7',
      source: 'switch-1',
      target: 'switch-2',
      bandwidth: 1000,
      latency: 8,
      packetLoss: 2.5,
      status: 'degraded',
      utilization: 88,
    },
  ],
};

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocketServer({ server });

let devices = JSON.parse(JSON.stringify(initialTopologyData.devices));
let links = JSON.parse(JSON.stringify(initialTopologyData.links));

const generateId = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const broadcast = (message) => {
  try {
    const data = JSON.stringify(message);
    const clients = Array.from(wss.clients);
    console.log(`Broadcasting ${message.type} to ${clients.length} clients`);
    clients.forEach((client, index) => {
      try {
        if (client.readyState === WebSocket.OPEN) {
          client.send(data, (error) => {
            if (error) {
              console.error(`Error sending to client ${index}:`, error.message);
            }
          });
        } else {
          console.log(`Client ${index} not ready, state: ${client.readyState}`);
        }
      } catch (clientError) {
        console.error(`Error sending to client ${index}:`, clientError);
      }
    });
  } catch (error) {
    console.error('Error broadcasting message:', error);
  }
};

const randomFluctuation = (value, range = 10) => {
  const change = (Math.random() - 0.5) * range;
  return Math.max(0, Math.min(100, value + change));
};

const startMetricsSimulation = () => {
  setInterval(() => {
    try {
      devices.forEach((device) => {
        try {
          if (device.status === 'online' || device.status === 'warning') {
            const cpu = randomFluctuation(device.cpu, 15);
            const memory = randomFluctuation(device.memory, 10);
            device.cpu = cpu;
            device.memory = memory;

            const metrics = {
              deviceId: device.id,
              timestamp: Date.now(),
              cpu,
              memory,
            };
            broadcast({ type: 'DEVICE_UPDATE', data: metrics });
          }
        } catch (error) {
          console.error('Error updating device metrics:', error);
        }
      });
    } catch (error) {
      console.error('Error in device metrics interval:', error);
    }
  }, 2000);

  setInterval(() => {
    try {
      links.forEach((link) => {
        try {
          if (link.status === 'up' || link.status === 'degraded') {
            const utilization = randomFluctuation(link.utilization, 20);
            const latency = Math.max(1, link.latency + (Math.random() - 0.5) * 5);
            const packetLoss = Math.max(0, Math.min(100, link.packetLoss + (Math.random() - 0.5) * 2));

            link.utilization = utilization;
            link.latency = latency;
            link.packetLoss = packetLoss;

            const metrics = {
              linkId: link.id,
              timestamp: Date.now(),
              bandwidth: link.bandwidth,
              latency,
              packetLoss,
              utilization,
            };
            broadcast({ type: 'LINK_UPDATE', data: metrics });
          }
        } catch (error) {
          console.error('Error updating link metrics:', error);
        }
      });
    } catch (error) {
      console.error('Error in link metrics interval:', error);
    }
  }, 3000);
};

const HEARTBEAT_INTERVAL = 15000;
const CLIENT_TIMEOUT = 30000;

wss.on('connection', (ws) => {
  console.log('Client connected');
  ws.isAlive = true;
  ws.lastPong = Date.now();

  try {
    ws.send(JSON.stringify({
      type: 'INIT',
      data: { devices, links },
    }), (error) => {
      if (error) {
        console.error('Error sending initial data:', error);
      }
    });
  } catch (error) {
    console.error('Error sending initial data:', error);
  }

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      if (message.type === 'PING') {
        ws.lastPong = Date.now();
        try {
          ws.send(JSON.stringify({ type: 'PONG', timestamp: Date.now() }));
        } catch (e) {
          console.error('Error sending PONG:', e);
        }
      }
      
      if (message.type === 'PONG') {
        ws.lastPong = Date.now();
        ws.isAlive = true;
      }
      
      if (message.type === 'SYNC_REQUEST') {
        try {
          ws.send(JSON.stringify({
            type: 'SYNC_RESPONSE',
            data: { devices, links },
          }));
          console.log('Sent full state sync to client');
        } catch (e) {
          console.error('Error sending sync response:', e);
        }
      }
      
      if (message.type === 'ADD_DEVICE') {
        const newDevice = {
          ...message.data,
          id: generateId(message.data.type),
          interfaces: message.data.interfaces || [],
        };
        devices.push(newDevice);
        broadcast({ type: 'DEVICE_ADDED', data: newDevice });
      }
      
      if (message.type === 'REMOVE_DEVICE') {
        const deviceId = message.data.deviceId;
        devices = devices.filter((d) => d.id !== deviceId);
        links = links.filter((l) => l.source !== deviceId && l.target !== deviceId);
        broadcast({ type: 'DEVICE_REMOVED', data: { deviceId } });
      }
      
      if (message.type === 'ADD_LINK') {
        const newLink = {
          ...message.data,
          id: generateId('link'),
        };
        links.push(newLink);
        broadcast({ type: 'LINK_ADDED', data: newLink });
      }
      
      if (message.type === 'REMOVE_LINK') {
        const linkId = message.data.linkId;
        links = links.filter((l) => l.id !== linkId);
        broadcast({ type: 'LINK_REMOVED', data: { linkId } });
      }
      
      if (message.type === 'TIME_TRAVEL_JUMP') {
        const index = message.data.index;
        if (index >= 0 && index < historySnapshots.length) {
          const snapshot = historySnapshots[index];
          try {
            ws.send(JSON.stringify({
              type: 'TIME_TRAVEL_JUMP',
              data: { index, snapshot }
            }));
            console.log(`Sent time travel snapshot at index ${index}`);
          } catch (e) {
            console.error('Error sending time travel snapshot:', e);
          }
        }
      }
      
      if (message.type === 'GET_HISTORY') {
        try {
          ws.send(JSON.stringify({
            type: 'HISTORY_SNAPSHOT',
            data: historySnapshots
          }));
        } catch (e) {
          console.error('Error sending history:', e);
        }
      }
      
      if (message.type === 'TRIGGER_FAULT') {
        const deviceId = message.data.deviceId;
        const device = devices.find(d => d.id === deviceId);
        if (device && device.status === 'online') {
          const impact = calculateFaultImpact(deviceId);
          const faultEvent = {
            id: `fault-${Date.now()}`,
            type: 'device_fault',
            targetId: deviceId,
            timestamp: Date.now(),
            severity: 'high',
            description: `${device.name} 发生手动触发的故障`,
            affectedDevices: impact.affectedDevices,
            affectedLinks: impact.affectedLinks
          };
          
          activeFaults.push(faultEvent);
          
          devices = devices.map(d => 
            impact.affectedDevices.includes(d.id) 
              ? { ...d, status: 'offline', cpu: 0, memory: 0 }
              : d
          );
          
          links = links.map(l =>
            impact.affectedLinks.includes(l.id)
              ? { ...l, status: 'down', utilization: 0, latency: 0, packetLoss: 100 }
              : l
          );
          
          broadcast({ type: 'FAULT_EVENT', data: faultEvent });
        }
      }
    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });

  ws.on('close', (code, reason) => {
    console.log('Client disconnected. Code:', code, 'Reason:', reason.toString());
    if (ws.heartbeatInterval) {
      clearInterval(ws.heartbeatInterval);
    }
  });

  ws.heartbeatInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'PING', timestamp: Date.now() }));
      } catch (e) {
        console.error('Error sending PING:', e);
      }
    }
    
    const now = Date.now();
    if (now - ws.lastPong > CLIENT_TIMEOUT) {
      console.log('Client timeout, closing connection');
      ws.terminate();
    }
  }, HEARTBEAT_INTERVAL);
});

app.get('/api/devices', (req, res) => {
  res.json(devices);
});

app.get('/api/links', (req, res) => {
  res.json(links);
});

app.post('/api/devices', (req, res) => {
  const newDevice = {
    ...req.body,
    id: generateId(req.body.type),
    interfaces: req.body.interfaces || [],
  };
  devices.push(newDevice);
  broadcast({ type: 'DEVICE_ADDED', data: newDevice });
  res.json(newDevice);
});

app.delete('/api/devices/:id', (req, res) => {
  const deviceId = req.params.id;
  devices = devices.filter((d) => d.id !== deviceId);
  links = links.filter((l) => l.source !== deviceId && l.target !== deviceId);
  broadcast({ type: 'DEVICE_REMOVED', data: { deviceId } });
  res.json({ success: true });
});

app.get('/api/health', (req, res) => {
  res.json(calculateHealthScore());
});

app.get('/api/history', (req, res) => {
  res.json(historySnapshots);
});

app.get('/api/faults', (req, res) => {
  res.json(activeFaults);
});

app.post('/api/trigger-fault', (req, res) => {
  const { deviceId } = req.body;
  const device = devices.find(d => d.id === deviceId);
  if (!device || device.status !== 'online') {
    return res.status(400).json({ error: 'Device not found or not online' });
  }
  
  const impact = calculateFaultImpact(deviceId);
  const faultEvent = {
    id: `fault-${Date.now()}`,
    type: 'device_fault',
    targetId: deviceId,
    timestamp: Date.now(),
    severity: 'high',
    description: `${device.name} 发生手动触发的故障`,
    affectedDevices: impact.affectedDevices,
    affectedLinks: impact.affectedLinks
  };
  
  activeFaults.push(faultEvent);
  
  devices = devices.map(d => 
    impact.affectedDevices.includes(d.id) 
      ? { ...d, status: 'offline', cpu: 0, memory: 0 }
      : d
  );
  
  links = links.map(l =>
    impact.affectedLinks.includes(l.id)
      ? { ...l, status: 'down', utilization: 0, latency: 0, packetLoss: 100 }
      : l
  );
  
  broadcast({ type: 'FAULT_EVENT', data: faultEvent });
  res.json(faultEvent);
});

const buildAdjacencyList = () => {
  const adj = new Map();
  devices.forEach(d => adj.set(d.id, []));
  links.forEach(l => {
    if (adj.has(l.source)) adj.get(l.source).push({ target: l.target, linkId: l.id });
    if (adj.has(l.target)) adj.get(l.target).push({ target: l.source, linkId: l.id });
  });
  return adj;
};

const findReachableNodes = (startId, adj) => {
  const visited = new Set();
  const queue = [startId];
  visited.add(startId);
  
  while (queue.length > 0) {
    const current = queue.shift();
    const neighbors = adj.get(current) || [];
    for (const { target, linkId } of neighbors) {
      const link = links.find(l => l.id === linkId);
      const targetDevice = devices.find(d => d.id === target);
      if (link && link.status !== 'down' && targetDevice && targetDevice.status !== 'offline' && !visited.has(target)) {
        visited.add(target);
        queue.push(target);
      }
    }
  }
  return visited;
};

const calculateFaultImpact = (faultyDeviceId) => {
  const adj = buildAdjacencyList();
  const allNodes = new Set(devices.map(d => d.id));
  
  const tempDevices = devices.map(d => 
    d.id === faultyDeviceId ? { ...d, status: 'offline' } : d
  );
  
  const tempLinks = links.map(l =>
    l.source === faultyDeviceId || l.target === faultyDeviceId
      ? { ...l, status: 'down' }
      : l
  );
  
  const onlineDevices = tempDevices.filter(d => d.status !== 'offline');
  if (onlineDevices.length === 0) return { affectedDevices: [], affectedLinks: [] };
  
  const reachableFromFirst = findReachableNodes(onlineDevices[0].id, adj);
  const isolatedDevices = [...allNodes].filter(id => !reachableFromFirst.has(id) && id !== faultyDeviceId);
  
  const affectedLinks = links.filter(l => 
    l.source === faultyDeviceId || l.target === faultyDeviceId ||
    isolatedDevices.includes(l.source) || isolatedDevices.includes(l.target)
  ).map(l => l.id);
  
  return {
    affectedDevices: [faultyDeviceId, ...isolatedDevices],
    affectedLinks
  };
};

const calculateHealthScore = () => {
  const onlineDevices = devices.filter(d => d.status === 'online').length;
  const totalDevices = devices.length;
  const upLinks = links.filter(l => l.status === 'up').length;
  const totalLinks = links.length;
  
  const activeLinks = links.filter(l => l.status === 'up' || l.status === 'degraded');
  const avgLatency = activeLinks.length > 0 
    ? activeLinks.reduce((sum, l) => sum + l.latency, 0) / activeLinks.length 
    : 0;
  const avgPacketLoss = activeLinks.length > 0
    ? activeLinks.reduce((sum, l) => sum + l.packetLoss, 0) / activeLinks.length
    : 0;
  const avgUtilization = activeLinks.length > 0
    ? activeLinks.reduce((sum, l) => sum + l.utilization, 0) / activeLinks.length
    : 0;
  
  const deviceScore = totalDevices > 0 ? (onlineDevices / totalDevices) * 100 : 100;
  const linkScore = totalLinks > 0 ? (upLinks / totalLinks) * 100 : 100;
  
  const latencyScore = Math.max(0, 100 - avgLatency * 2);
  const packetLossScore = Math.max(0, 100 - avgPacketLoss * 10);
  const utilizationScore = avgUtilization < 70 ? 100 : Math.max(0, 100 - (avgUtilization - 70) * 2);
  const qualityScore = (latencyScore + packetLossScore + utilizationScore) / 3;
  
  const adj = buildAdjacencyList();
  const onlineDeviceIds = devices.filter(d => d.status === 'online').map(d => d.id);
  let connectivityScore = 100;
  if (onlineDeviceIds.length > 1) {
    const reachable = findReachableNodes(onlineDeviceIds[0], adj);
    const reachableOnline = onlineDeviceIds.filter(id => reachable.has(id)).length;
    connectivityScore = (reachableOnline / onlineDeviceIds.length) * 100;
  }
  
  const availabilityScore = (deviceScore + linkScore) / 2;
  const overallScore = (availabilityScore * 0.4 + qualityScore * 0.3 + connectivityScore * 0.3);
  
  const criticalFaults = devices.filter(d => d.status === 'offline').length + 
                        links.filter(l => l.status === 'down').length;
  
  return {
    overall: Math.round(overallScore * 10) / 10,
    deviceScore: Math.round(deviceScore * 10) / 10,
    linkScore: Math.round(linkScore * 10) / 10,
    availabilityScore: Math.round(connectivityScore * 10) / 10,
    details: {
      onlineDevices,
      totalDevices,
      upLinks,
      totalLinks,
      avgLatency: Math.round(avgLatency * 100) / 100,
      avgPacketLoss: Math.round(avgPacketLoss * 100) / 100,
      avgUtilization: Math.round(avgUtilization * 10) / 10,
      activeFaults: criticalFaults
    }
  };
};

const MAX_HISTORY_SNAPSHOTS = 60;
const SNAPSHOT_INTERVAL = 5000;
const historySnapshots = [];
const activeFaults = [];

const createSnapshot = () => {
  const healthScore = calculateHealthScore();
  const snapshot = {
    timestamp: Date.now(),
    devices: JSON.parse(JSON.stringify(devices)),
    links: JSON.parse(JSON.stringify(links)),
    healthScore: healthScore.overall,
    faultEvents: JSON.parse(JSON.stringify(activeFaults))
  };
  
  historySnapshots.push(snapshot);
  if (historySnapshots.length > MAX_HISTORY_SNAPSHOTS) {
    historySnapshots.shift();
  }
  
  return snapshot;
};

const simulateFault = () => {
  if (Math.random() > 0.15) return;
  
  const onlineDevices = devices.filter(d => d.status === 'online');
  if (onlineDevices.length === 0) return;
  
  const faultyDevice = onlineDevices[Math.floor(Math.random() * onlineDevices.length)];
  const impact = calculateFaultImpact(faultyDevice.id);
  
  const severities = ['low', 'medium', 'high', 'critical'];
  const severity = severities[Math.floor(Math.random() * severities.length)];
  
  const faultEvent = {
    id: `fault-${Date.now()}`,
    type: 'device_fault',
    targetId: faultyDevice.id,
    timestamp: Date.now(),
    severity,
    description: `${faultyDevice.name} 发生${severity === 'critical' ? '严重' : severity === 'high' ? '重大' : severity === 'medium' ? '中等' : '轻微'}故障`,
    affectedDevices: impact.affectedDevices,
    affectedLinks: impact.affectedLinks
  };
  
  activeFaults.push(faultEvent);
  
  devices = devices.map(d => 
    impact.affectedDevices.includes(d.id) 
      ? { ...d, status: 'offline', cpu: 0, memory: 0 }
      : d
  );
  
  links = links.map(l =>
    impact.affectedLinks.includes(l.id)
      ? { ...l, status: 'down', utilization: 0, latency: 0, packetLoss: 100 }
      : l
  );
  
  broadcast({ type: 'FAULT_EVENT', data: faultEvent });
  
  setTimeout(() => {
    const recoveryTime = 10000 + Math.random() * 20000;
    setTimeout(() => {
      devices = devices.map(d => 
        impact.affectedDevices.includes(d.id) 
          ? { ...d, status: Math.random() > 0.2 ? 'online' : 'warning' }
          : d
      );
      
      links = links.map(l =>
        impact.affectedLinks.includes(l.id)
          ? { ...l, status: 'up' }
          : l
      );
      
      const faultIndex = activeFaults.findIndex(f => f.id === faultEvent.id);
      if (faultIndex > -1) activeFaults.splice(faultIndex, 1);
      
      broadcast({ type: 'DEVICE_ADDED', data: null });
    }, recoveryTime);
  }, 5000);
};

const startHealthMonitoring = () => {
  setInterval(() => {
    const healthScore = calculateHealthScore();
    broadcast({ type: 'HEALTH_SCORE', data: healthScore });
  }, 3000);
  
  setInterval(() => {
    const snapshot = createSnapshot();
    broadcast({ type: 'HISTORY_SNAPSHOT', data: snapshot });
  }, SNAPSHOT_INTERVAL);
  
  setInterval(() => {
    simulateFault();
  }, 15000);
};

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`WebSocket server running on ws://localhost:${PORT}`);
  startMetricsSimulation();
  startHealthMonitoring();
});
