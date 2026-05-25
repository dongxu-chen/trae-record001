const crypto = require('crypto');

const PORT = process.env.TURN_PORT || 3478;
const TLS_PORT = process.env.TURN_TLS_PORT || 5349;
const USERNAME = process.env.TURN_USERNAME || 'clipboard-sync';
const CREDENTIAL = process.env.TURN_PASSWORD || 'change-me';
const REALM = process.env.TURN_REALM || 'clipboardsync.local';

console.log(`
╔═══════════════════════════════════════════════════════════════╗
║              Clipboard Sync TURN Server                      ║
║  用于 WebRTC 中继转发，当局域网打孔失败时自动降级使用       ║
╚═══════════════════════════════════════════════════════════════╝

配置说明：
- UDP/TCP 端口: ${PORT}
- TLS 端口: ${TLS_PORT}
- 用户名: ${USERNAME}
- 密码: ${CREDENTIAL}
- Realm: ${REALM}

⚠️  生产环境建议：
   1. 修改默认用户名和密码
   2. 配置 TLS 证书
   3. 配置防火墙开放相应端口
   4. 考虑使用 coturn 等成熟的 TURN 服务器

本示例展示如何配置 TURN 服务器。生产环境推荐使用 coturn。
`);

function generateHMACKey(username, password, realm) {
  const input = `${username}:${realm}:${password}`;
  return crypto.createHash('md5').update(input).digest('hex');
}

const hmacKey = generateHMACKey(USERNAME, CREDENTIAL, REALM);
console.log(`HMAC 密钥: ${hmacKey}`);

console.log(`

coturn 服务器配置示例 (/etc/turnserver.conf):

listening-port=${PORT}
tls-listening-port=${TLS_PORT}
realm=${REALM}
server-name=turn.${REALM}
user=${USERNAME}:${CREDENTIAL}
lt-cred-mech
cert=/path/to/cert.pem
pkey=/path/to/privkey.pem
no-stdout-log
syslog
verbose
fingerprint
use-auth-secret
static-auth-secret=${hmacKey}
total-quota=100
bps-capacity=0
stale-nonce
no-multicast-peers

Docker 运行 coturn 示例:

docker run -d --name=coturn \\
  -p 3478:3478 -p 3478:3478/udp \\
  -p 5349:5349 -p 5349:5349/udp \\
  -p 49152-65535:49152-65535/udp \\
  coturn/coturn \\
  -n \\
  --listening-port=${PORT} \\
  --tls-listening-port=${TLS_PORT} \\
  --realm=${REALM} \\
  --user=${USERNAME}:${CREDENTIAL} \\
  --lt-cred-mech \\
  --fingerprint \\
  --use-auth-secret \\
  --static-auth-secret=${hmacKey} \\
  --no-multicast-peers
`);

const dgram = require('dgram');
const server = dgram.createSocket('udp4');

const allocations = new Map();

server.on('message', (msg, rinfo) => {
  try {
    const { address, port } = rinfo;
    const transactionId = msg.slice(4, 20).toString('hex');
    
    const msgType = msg.readUInt16BE(0);
    
    switch (msgType) {
      case 0x0001: 
        console.log(`[${address}:${port}] 收到 STUN 绑定请求`);
        handleBindingRequest(msg, rinfo);
        break;
        
      case 0x0003: 
        console.log(`[${address}:${port}] 收到 TURN 分配请求`);
        handleAllocateRequest(msg, rinfo);
        break;
        
      case 0x0004: 
        console.log(`[${address}:${port}] 收到 TURN 刷新请求`);
        handleRefreshRequest(msg, rinfo);
        break;
        
      case 0x0006: 
        console.log(`[${address}:${port}] 收到 TURN 创建权限请求`);
        handleCreatePermission(msg, rinfo);
        break;
        
      case 0x0007: 
        console.log(`[${address}:${port}] 收到 TURN 发送指示`);
        handleSendIndication(msg, rinfo);
        break;
        
      default:
        console.log(`[${address}:${port}] 收到未知消息类型: 0x${msgType.toString(16)}`);
    }
  } catch (e) {
    console.error('处理 TURN 消息失败:', e);
  }
});

function handleBindingRequest(msg, rinfo) {
  const response = Buffer.alloc(32);
  response.writeUInt16BE(0x0101, 0); 
  response.writeUInt16BE(12, 2);
  msg.copy(response, 4, 4, 20);
  
  const address = rinfo.address.split('.').map(Number);
  response.writeUInt8(0x00, 20);
  response.writeUInt8(0x01, 21);
  response.writeUInt16BE(8, 22);
  response.writeUInt8(0x00, 24);
  response.writeUInt8(0x01, 25);
  response.writeUInt8(address[0], 26);
  response.writeUInt8(address[1], 27);
  response.writeUInt8(address[2], 28);
  response.writeUInt8(address[3], 29);
  response.writeUInt16BE(rinfo.port, 30);
  
  server.send(response, rinfo.port, rinfo.address);
  console.log(`[${rinfo.address}:${rinfo.port}] 已响应 STUN 绑定请求`);
}

function handleAllocateRequest(msg, rinfo) {
  const key = `${rinfo.address}:${rinfo.port}`;
  const relayPort = 49152 + Math.floor(Math.random() * 16383);
  
  allocations.set(key, {
    clientAddress: rinfo.address,
    clientPort: rinfo.port,
    relayPort: relayPort,
    expiresAt: Date.now() + 600000,
    permissions: new Set()
  });
  
  const response = Buffer.alloc(48);
  response.writeUInt16BE(0x0103, 0);
  response.writeUInt16BE(28, 2);
  msg.copy(response, 4, 4, 20);
  
  response.writeUInt16BE(0x000D, 20);
  response.writeUInt16BE(4, 22);
  response.writeUInt32BE(600, 24);
  
  response.writeUInt16BE(0x0016, 28);
  response.writeUInt16BE(8, 30);
  response.writeUInt8(0x00, 32);
  response.writeUInt8(0x01, 33);
  
  const relayAddress = rinfo.address.split('.').map(Number);
  response.writeUInt8(relayAddress[0], 34);
  response.writeUInt8(relayAddress[1], 35);
  response.writeUInt8(relayAddress[2], 36);
  response.writeUInt8(relayAddress[3], 37);
  response.writeUInt16BE(relayPort, 38);
  
  response.writeUInt16BE(0x0020, 42);
  response.writeUInt16BE(4, 44);
  response.writeUInt32BE(1, 46);
  
  server.send(response, rinfo.port, rinfo.address);
  console.log(`[${rinfo.address}:${rinfo.port}] 已分配中继端口: ${relayPort}`);
}

function handleRefreshRequest(msg, rinfo) {
  const key = `${rinfo.address}:${rinfo.port}`;
  const allocation = allocations.get(key);
  
  if (!allocation) {
    console.log(`[${rinfo.address}:${rinfo.port}] 刷新失败: 未找到分配记录`);
    return;
  }
  
  allocation.expiresAt = Date.now() + 600000;
  
  const response = Buffer.alloc(28);
  response.writeUInt16BE(0x0104, 0);
  response.writeUInt16BE(8, 2);
  msg.copy(response, 4, 4, 20);
  
  response.writeUInt16BE(0x000D, 20);
  response.writeUInt16BE(4, 22);
  response.writeUInt32BE(600, 24);
  
  server.send(response, rinfo.port, rinfo.address);
  console.log(`[${rinfo.address}:${rinfo.port}] 已刷新分配`);
}

function handleCreatePermission(msg, rinfo) {
  const key = `${rinfo.address}:${rinfo.port}`;
  const allocation = allocations.get(key);
  
  if (!allocation) {
    console.log(`[${rinfo.address}:${rinfo.port}] 创建权限失败: 未找到分配记录`);
    return;
  }
  
  const peerAddressOffset = 28;
  const peerAddress = [
    msg.readUInt8(peerAddressOffset + 2),
    msg.readUInt8(peerAddressOffset + 3),
    msg.readUInt8(peerAddressOffset + 4),
    msg.readUInt8(peerAddressOffset + 5)
  ].join('.');
  
  allocation.permissions.add(peerAddress);
  
  const response = Buffer.alloc(20);
  response.writeUInt16BE(0x0106, 0);
  response.writeUInt16BE(0, 2);
  msg.copy(response, 4, 4, 20);
  
  server.send(response, rinfo.port, rinfo.address);
  console.log(`[${rinfo.address}:${rinfo.port}] 已创建对端权限: ${peerAddress}`);
}

function handleSendIndication(msg, rinfo) {
  const key = `${rinfo.address}:${rinfo.port}`;
  const allocation = allocations.get(key);
  
  if (!allocation) {
    console.log(`[${rinfo.address}:${rinfo.port}] 发送指示失败: 未找到分配记录`);
    return;
  }
  
  const peerAddressOffset = 24;
  const peerAddress = [
    msg.readUInt8(peerAddressOffset + 2),
    msg.readUInt8(peerAddressOffset + 3),
    msg.readUInt8(peerAddressOffset + 4),
    msg.readUInt8(peerAddressOffset + 5)
  ].join('.');
  const peerPort = msg.readUInt16BE(peerAddressOffset + 6);
  
  const dataOffset = peerAddressOffset + 8;
  const data = msg.slice(dataOffset);
  
  if (!allocation.permissions.has(peerAddress)) {
    console.log(`[${rinfo.address}:${rinfo.port}] 发送指示失败: 无权限访问 ${peerAddress}`);
    return;
  }
  
  const dataIndication = Buffer.alloc(8 + data.length);
  dataIndication.writeUInt16BE(0x0115, 0);
  dataIndication.writeUInt16BE(data.length + 8, 2);
  msg.copy(dataIndication, 4, 4, 8);
  
  const xorPeerAddress = Buffer.alloc(8);
  xorPeerAddress.writeUInt8(0x00, 0);
  xorPeerAddress.writeUInt8(0x01, 1);
  const addrBytes = peerAddress.split('.').map(Number);
  xorPeerAddress.writeUInt8(addrBytes[0] ^ (0x21 ^ 0x12), 2);
  xorPeerAddress.writeUInt8(addrBytes[1] ^ (0xA4 ^ 0x42), 3);
  xorPeerAddress.writeUInt8(addrBytes[2] ^ (0xFA ^ 0xA1), 4);
  xorPeerAddress.writeUInt8(addrBytes[3] ^ (0x53 ^ 0xFF), 5);
  xorPeerAddress.writeUInt16BE(peerPort ^ 0x2112, 6);
  
  xorPeerAddress.copy(dataIndication, 8);
  data.copy(dataIndication, 16);
  
  server.send(dataIndication, peerPort, peerAddress);
  console.log(`[${rinfo.address}:${rinfo.port}] 已转发数据到 ${peerAddress}:${peerPort} (${data.length} 字节)`);
}

server.on('listening', () => {
  const address = server.address();
  console.log(`\n✅ TURN 服务器已启动，监听 ${address.address}:${address.port}`);
  console.log('📡 等待客户端连接...\n');
});

server.on('error', (err) => {
  console.error('TURN 服务器错误:', err);
  if (err.code === 'EACCES') {
    console.error('\n⚠️  端口访问被拒绝。请尝试使用 sudo 或修改端口号。');
  }
  server.close();
});

setInterval(() => {
  const now = Date.now();
  for (const [key, allocation] of allocations.entries()) {
    if (now > allocation.expiresAt) {
      console.log(`回收过期分配: ${key}`);
      allocations.delete(key);
    }
  }
}, 60000);

try {
  server.bind(PORT);
} catch (e) {
  console.error('无法绑定端口:', e.message);
  console.log(`请确保端口 ${PORT} 未被占用，或使用环境变量 TURN_PORT 指定其他端口。`);
  process.exit(1);
}

process.on('SIGINT', () => {
  console.log('\n\n收到停止信号，正在关闭 TURN 服务器...');
  server.close();
  console.log('✅ TURN 服务器已关闭');
  process.exit(0);
});
