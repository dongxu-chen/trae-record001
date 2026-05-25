import express from 'express';
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import cors from 'cors';
import { initialTopologyData } from '../src/mock/initialData';
import { Device, Link, WebSocketMessage, DeviceMetrics, LinkMetrics } from '../src/types';

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocketServer({ server });

let devices: Device[] = JSON.parse(JSON.stringify(initialTopologyData.devices));
let links: Link[] = JSON.parse(JSON.stringify(initialTopologyData.links));

const generateId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const broadcast = (message: WebSocketMessage) => {
  try {
    const data = JSON.stringify(message);
    wss.clients.forEach((client) => {
      try {
        if (client.readyState === WebSocket.OPEN) {
          client.send(data, (error) => {
            if (error) {
              console.error('Error sending message to client:', error);
            }
          });
        }
      } catch (clientError) {
        console.error('Error sending to client:', clientError);
      }
    });
  } catch (error) {
    console.error('Error broadcasting message:', error);
  }
};

const randomFluctuation = (value: number, range: number = 10) => {
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

            const metrics: DeviceMetrics = {
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

            const metrics: LinkMetrics = {
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

wss.on('connection', (ws) => {
  console.log('Client connected');

  try {
    ws.send(JSON.stringify({
      type: 'INIT',
      data: { devices, links },
    } as WebSocketMessage), (error) => {
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
      
      if (message.type === 'ADD_DEVICE') {
        const newDevice: Device = {
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
        const newLink: Link = {
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
    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });

  ws.on('close', (code, reason) => {
    console.log('Client disconnected. Code:', code, 'Reason:', reason.toString());
  });
});

app.get('/api/devices', (req, res) => {
  res.json(devices);
});

app.get('/api/links', (req, res) => {
  res.json(links);
});

app.post('/api/devices', (req, res) => {
  const newDevice: Device = {
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

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`WebSocket server running on ws://localhost:${PORT}`);
  startMetricsSimulation();
});
