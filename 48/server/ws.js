const WebSocket = require('ws');
const http = require('http');

const PORT = 8080;
const server = http.createServer();
const wss = new WebSocket.Server({ server, path: '/ws' });

let broadcastInterval = null;
let alarmInterval = null;
const clients = new Set();

const alarmTypes = [
  { type: 'error', title: '服务器异常', messages: ['CPU 使用率超过 90%', '内存溢出警告', '数据库连接失败', '服务响应超时'] },
  { type: 'warning', title: '性能告警', messages: ['接口响应时间超过 2s', '队列堆积警告', '磁盘空间不足 10%', '连接数接近上限'] },
  { type: 'info', title: '系统通知', messages: ['新用户注册高峰', '订单量异常增长', '流量峰值预警', '定时任务执行完成'] }
];

const regions = [
  { name: '北京', value: 0 },
  { name: '上海', value: 0 },
  { name: '广东', value: 0 },
  { name: '浙江', value: 0 },
  { name: '四川', value: 0 },
  { name: '湖北', value: 0 },
  { name: '陕西', value: 0 },
  { name: '江苏', value: 0 }
];

let lineData = Array(12).fill(0).map((_, i) => ({
  time: `${i}:00`,
  value: Math.floor(Math.random() * 1000) + 100
}));

function generateRandomNumber(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function updateLineData() {
  const newValue = Math.floor(Math.random() * 1000) + 100;
  const now = new Date();
  const timeStr = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
  
  lineData.shift();
  lineData.push({ time: timeStr, value: newValue });
  
  return lineData;
}

function updateRegionData() {
  return regions.map(region => ({
    ...region,
    value: generateRandomNumber(100, 5000)
  }));
}

function generateDashboardData() {
  return {
    type: 'data',
    timestamp: Date.now(),
    lineChart: updateLineData(),
    mapData: updateRegionData(),
    stats: {
      totalUsers: generateRandomNumber(10000, 50000),
      activeUsers: generateRandomNumber(5000, 20000),
      totalOrders: generateRandomNumber(1000, 10000),
      revenue: generateRandomNumber(100000, 500000)
    }
  };
}

function generateAlarm() {
  const alarmType = alarmTypes[generateRandomNumber(0, alarmTypes.length - 1)];
  const message = alarmType.messages[generateRandomNumber(0, alarmType.messages.length - 1)];
  
  return {
    type: 'alarm',
    id: `alarm_${Date.now()}_${generateRandomNumber(1000, 9999)}`,
    level: alarmType.type,
    title: alarmType.title,
    message: message,
    timestamp: Date.now(),
    region: regions[generateRandomNumber(0, regions.length - 1)].name
  };
}

function broadcast(data) {
  const jsonStr = JSON.stringify(data);
  
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(jsonStr, (error) => {
        if (error) {
          console.error('发送消息失败:', error);
          clients.delete(client);
        }
      });
    } else {
      clients.delete(client);
    }
  }
}

function startBroadcast() {
  if (!broadcastInterval && clients.size > 0) {
    broadcastInterval = setInterval(() => {
      broadcast(generateDashboardData());
    }, 3000);
    console.log('开始广播数据');
  }
  
  if (!alarmInterval && clients.size > 0) {
    alarmInterval = setInterval(() => {
      if (Math.random() > 0.5) {
        broadcast(generateAlarm());
      }
    }, 5000);
    console.log('开始告警事件推送');
  }
}

function stopBroadcast() {
  if (broadcastInterval && clients.size === 0) {
    clearInterval(broadcastInterval);
    broadcastInterval = null;
    console.log('停止广播数据');
  }
  
  if (alarmInterval && clients.size === 0) {
    clearInterval(alarmInterval);
    alarmInterval = null;
    console.log('停止告警事件推送');
  }
}

wss.on('connection', (ws, req) => {
  console.log('新客户端连接，当前连接数:', clients.size + 1);
  
  clients.add(ws);
  
  ws.send(JSON.stringify(generateDashboardData()));
  
  startBroadcast();
  
  ws.on('message', (message) => {
    console.log('收到消息:', message);
  });
  
  ws.on('close', () => {
    clients.delete(ws);
    console.log('客户端断开连接，当前连接数:', clients.size);
    stopBroadcast();
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket 错误:', error);
    clients.delete(ws);
    stopBroadcast();
  });
});

server.listen(PORT, () => {
  console.log(`WebSocket 服务器运行在 ws://localhost:${PORT}/ws`);
});
