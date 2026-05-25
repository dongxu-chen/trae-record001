const WebSocket = require('ws');
const http = require('http');
const { URL } = require('url');

const PORT = process.env.PORT || 33446;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Clipboard Sync Signaling Server is running');
});

const wss = new WebSocket.Server({ server });

const devices = new Map();

function isPrivateIP(ip) {
  const privateRanges = [
    /^10\./,
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
    /^192\.168\./,
    /^127\./,
    /^localhost$/,
    /^::1$/,
    /^fc00:/,
    /^fe80:/
  ];
  return privateRanges.some(range => range.test(ip));
}

function getClientIP(req) {
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  const ip = req.socket.remoteAddress || '';
  return ip.replace('::ffff:', '');
}

function broadcastDeviceList() {
  const deviceList = Array.from(devices.values()).map(device => ({
    id: device.id,
    name: device.name,
    type: device.type,
    isOnline: device.ws.readyState === WebSocket.OPEN,
    isLocal: device.isLocal,
    lastSeen: device.lastSeen
  }));

  const message = JSON.stringify({
    type: 'devices',
    from: 'server',
    payload: { devices: deviceList },
    timestamp: Date.now()
  });

  for (const device of devices.values()) {
    if (device.ws.readyState === WebSocket.OPEN) {
      device.ws.send(message);
    }
  }
}

function sendTo(ws, message) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

wss.on('connection', (ws, req) => {
  const clientIP = getClientIP(req);
  const isLocal = isPrivateIP(clientIP);
  
  console.log(`新连接: ${clientIP} (局域网: ${isLocal})`);
  
  let currentDeviceId = null;

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      switch (message.type) {
        case 'join': {
          currentDeviceId = message.from;
          devices.set(currentDeviceId, {
            id: currentDeviceId,
            name: message.payload?.deviceName || 'Unknown Device',
            type: message.payload?.deviceType || 'desktop',
            ws: ws,
            isLocal: isLocal,
            ip: clientIP,
            lastSeen: Date.now()
          });
          console.log(`设备加入: ${message.payload?.deviceName} (${currentDeviceId})`);
          broadcastDeviceList();
          break;
        }
        
        case 'offer':
        case 'answer':
        case 'candidate': {
          const targetDevice = devices.get(message.to);
          if (targetDevice) {
            targetDevice.lastSeen = Date.now();
            sendTo(targetDevice.ws, message);
          }
          break;
        }
        
        case 'ping': {
          const device = devices.get(message.from);
          if (device) {
            device.lastSeen = Date.now();
          }
          break;
        }
        
        case 'leave': {
          if (message.from) {
            devices.delete(message.from);
            console.log(`设备离开: ${message.from}`);
            broadcastDeviceList();
          }
          break;
        }
      }
    } catch (e) {
      console.error('处理消息失败:', e);
    }
  });

  ws.on('close', () => {
    console.log(`连接关闭: ${clientIP}`);
    if (currentDeviceId) {
      devices.delete(currentDeviceId);
      broadcastDeviceList();
    }
  });

  ws.on('error', (error) => {
    console.error(`WebSocket 错误 (${clientIP}):`, error);
  });
});

setInterval(() => {
  const now = Date.now();
  const timeout = 60000;
  
  for (const [id, device] of devices.entries()) {
    if (now - device.lastSeen > timeout) {
      console.log(`设备超时: ${device.name} (${id})`);
      device.ws.terminate();
      devices.delete(id);
      broadcastDeviceList();
    }
  }
}, 30000);

server.listen(PORT, () => {
  console.log(`信令服务器运行在端口 ${PORT}`);
  console.log(`WebSocket 地址: ws://localhost:${PORT}`);
  console.log(`HTTP 地址: http://localhost:${PORT}`);
});
